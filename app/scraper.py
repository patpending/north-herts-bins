"""
North Hertfordshire District Council Bin Collection Scraper

Uses the Cloud9 mobile API that powers the official North Herts Council app.
Based on the approach from https://github.com/robbrad/UKBinCollectionData
"""

import re
import requests
from datetime import datetime
from typing import Optional
from dataclasses import dataclass


# Cloud9 mobile API endpoints (from official North Herts app)
ADDRESS_LOOKUP_URL = "https://apps.cloud9technologies.com/northherts/citizenmobile/mobileapi/addresses"
WASTE_COLLECTIONS_URL = "https://apps.cloud9technologies.com/northherts/citizenmobile/mobileapi/wastecollections"

# API credentials extracted from the mobile app (from UKBinCollectionData project)
API_HEADERS = {
    "Accept": "application/json",
    "Authorization": "Basic Y2xvdWQ5OmlkQmNWNGJvcjU=",  # cloud9:idBcV4bor5
    "X-Api-Version": "2",
    "X-App-Version": "3.0.56",
    "X-Platform": "android",
    "User-Agent": "okhttp/4.9.2",
}


@dataclass
class BinCollection:
    """Represents a single bin collection event."""
    bin_type: str
    collection_date: datetime

    def to_dict(self) -> dict:
        return {
            "bin_type": self.bin_type,
            "collection_date": self.collection_date.isoformat(),
            "collection_date_formatted": self.collection_date.strftime("%A, %d %B %Y"),
            "days_until": (self.collection_date.date() - datetime.now().date()).days
        }


@dataclass
class Address:
    """Represents an address from the lookup."""
    uprn: str
    address: str
    postcode: str

    def to_dict(self) -> dict:
        return {
            "uprn": self.uprn,
            "address": self.address,
            "postcode": self.postcode
        }


class NorthHertsBinCollectionError(Exception):
    """Custom exception for bin collection errors."""
    pass


class NorthHertsBinCollection:
    """
    Fetches bin collection schedules for North Hertfordshire properties.

    Usage:
        # With UPRN directly
        client = NorthHertsBinCollection()
        collections = client.get_collections(uprn="100080882674")

        # With postcode and house number
        collections = client.get_collections(postcode="SG6 1JF", house_number="1")
    """

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(API_HEADERS)

    def lookup_addresses(self, postcode: str) -> list[Address]:
        """
        Look up addresses by postcode.

        Args:
            postcode: UK postcode (e.g., "SG6 1JF")

        Returns:
            List of Address objects matching the postcode
        """
        postcode = self._normalize_postcode(postcode)

        try:
            response = self.session.get(
                ADDRESS_LOOKUP_URL,
                params={"postcode": postcode},
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise NorthHertsBinCollectionError(f"Failed to lookup addresses: {e}")

        addresses = []
        for item in data.get("addresses", []):
            addresses.append(Address(
                uprn=str(item.get("uprn", "")),
                address=item.get("fullAddress", "") or item.get("addressLine1", ""),
                postcode=item.get("postcode", postcode)
            ))

        return addresses

    def find_uprn(self, postcode: str, house_number: str) -> Optional[str]:
        """
        Find UPRN for a specific address.

        Args:
            postcode: UK postcode
            house_number: House number or name

        Returns:
            UPRN if found, None otherwise
        """
        addresses = self.lookup_addresses(postcode)
        house_number = house_number.lower().strip()

        for addr in addresses:
            # Check if the house number appears at the start of the address
            addr_lower = addr.address.lower()
            if addr_lower.startswith(house_number + " ") or addr_lower.startswith(house_number + ","):
                return addr.uprn

        return None

    def get_collections(
        self,
        uprn: Optional[str] = None,
        postcode: Optional[str] = None,
        house_number: Optional[str] = None
    ) -> list[BinCollection]:
        """
        Get bin collection schedule for an address.

        Args:
            uprn: Direct UPRN if known
            postcode: UK postcode (required if UPRN not provided)
            house_number: House number or name (required if UPRN not provided)

        Returns:
            List of BinCollection objects sorted by date
        """
        # Resolve UPRN if not provided
        if not uprn:
            if not postcode or not house_number:
                raise NorthHertsBinCollectionError(
                    "Either UPRN or both postcode and house_number must be provided"
                )
            uprn = self.find_uprn(postcode, house_number)
            if not uprn:
                raise NorthHertsBinCollectionError(
                    f"Could not find address: {house_number}, {postcode}"
                )

        # Validate UPRN format
        if not re.match(r"^\d+$", uprn):
            raise NorthHertsBinCollectionError(f"Invalid UPRN format: {uprn}")

        # Fetch collection data
        try:
            response = self.session.get(
                f"{WASTE_COLLECTIONS_URL}/{uprn}",
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise NorthHertsBinCollectionError(f"Failed to fetch collections: {e}")

        # Parse collections - API returns container1CollectionDetails through container8CollectionDetails
        collections = []
        waste_data = data.get("wasteCollectionDates", {})

        # Bin types to exclude from results
        excluded_bins = {"food caddy"}

        for i in range(1, 9):
            container_key = f"container{i}CollectionDetails"
            container = waste_data.get(container_key)

            if container is None:
                continue

            try:
                date_str = container.get("collectionDate", "")
                if not date_str:
                    continue

                bin_type = container.get("containerDescription", "Unknown")

                # Skip excluded bin types
                if bin_type.lower() in excluded_bins:
                    continue

                collection_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")

                collections.append(BinCollection(
                    bin_type=bin_type,
                    collection_date=collection_date
                ))
            except (ValueError, TypeError):
                continue

        # Sort by date
        collections.sort(key=lambda x: x.collection_date)

        return collections

    def get_next_collection(
        self,
        uprn: Optional[str] = None,
        postcode: Optional[str] = None,
        house_number: Optional[str] = None
    ) -> Optional[BinCollection]:
        """Get the next upcoming collection."""
        collections = self.get_collections(uprn, postcode, house_number)
        now = datetime.now()

        for collection in collections:
            if collection.collection_date >= now:
                return collection

        return None

    def get_collections_by_type(
        self,
        uprn: Optional[str] = None,
        postcode: Optional[str] = None,
        house_number: Optional[str] = None
    ) -> dict[str, list[BinCollection]]:
        """Get collections grouped by bin type."""
        collections = self.get_collections(uprn, postcode, house_number)

        grouped = {}
        for collection in collections:
            if collection.bin_type not in grouped:
                grouped[collection.bin_type] = []
            grouped[collection.bin_type].append(collection)

        return grouped

    @staticmethod
    def _normalize_postcode(postcode: str) -> str:
        """Normalize postcode format."""
        return postcode.upper().strip().replace(" ", "")


# Convenience function for simple usage
def get_bin_collections(
    uprn: Optional[str] = None,
    postcode: Optional[str] = None,
    house_number: Optional[str] = None
) -> list[dict]:
    """
    Simple function to get bin collections.

    Returns list of dicts with bin_type, collection_date, etc.
    """
    client = NorthHertsBinCollection()
    collections = client.get_collections(uprn, postcode, house_number)
    return [c.to_dict() for c in collections]
