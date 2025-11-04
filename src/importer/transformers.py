"""
Data Transformation Utilities for CSV to MongoDB Import

This module handles all data transformations including:
- Date parsing
- Currency conversion
- Location extraction (GeoJSON)
- Text normalization
- Missing value handling
"""

import re
import math
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DataTransformer:
    """Handles transformation of CSV data to MongoDB format."""

    @staticmethod
    def safe_convert_value(value: Any) -> Any:
        """
        Safely convert a value, handling pandas NaN, numpy NaN, and infinity.

        Converts NaN and inf values to None (which becomes null in MongoDB).

        Args:
            value: Any value from pandas DataFrame

        Returns:
            Cleaned value or None
        """
        # Check for pandas NA, numpy NaN, or math.nan
        if pd.isna(value) or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
            return None
        return value

    @staticmethod
    def parse_date(date_str: str) -> Optional[datetime]:
        """
        Parse date string in MM/DD/YYYY format to datetime object.

        Args:
            date_str: Date string from CSV

        Returns:
            datetime object or None if parsing fails
        """
        if not date_str or not isinstance(date_str, str):
            return None

        if date_str.strip() == "":
            return None

        try:
            # Handle MM/DD/YYYY format
            return datetime.strptime(date_str.strip(), "%m/%d/%Y")
        except ValueError:
            try:
                # Try alternative formats
                return datetime.strptime(date_str.strip(), "%Y-%m-%d")
            except ValueError:
                logger.warning(f"Failed to parse date: {date_str}")
                return None

    @staticmethod
    def parse_currency(currency_str: str) -> Optional[float]:
        """
        Parse currency string ($XX,XXX.XX) to float.

        Args:
            currency_str: Currency string from CSV

        Returns:
            Float value or None if parsing fails
        """
        # Handle NaN/None first
        currency_str = DataTransformer.safe_convert_value(currency_str)
        if currency_str is None:
            return None

        # Handle if already a number
        if isinstance(currency_str, (int, float)):
            val = float(currency_str)
            # Double-check for NaN/inf after conversion
            if math.isnan(val) or math.isinf(val):
                return None
            return val

        if not isinstance(currency_str, str):
            return None

        if currency_str.strip() == "":
            return None

        try:
            # Remove $, commas, and whitespace
            cleaned = currency_str.strip().replace("$", "").replace(",", "")
            val = float(cleaned)
            # Check for NaN/inf
            if math.isnan(val) or math.isinf(val):
                return None
            return val
        except (ValueError, AttributeError):
            logger.warning(f"Failed to parse currency: {currency_str}")
            return None

    @staticmethod
    def parse_number(num_str: str) -> Optional[float]:
        """
        Parse numeric string to float.

        Args:
            num_str: Numeric string from CSV

        Returns:
            Float value or None if parsing fails
        """
        # Handle NaN/None first
        num_str = DataTransformer.safe_convert_value(num_str)
        if num_str is None:
            return None

        # Handle if already a number
        if isinstance(num_str, (int, float)):
            val = float(num_str)
            # Double-check for NaN/inf after conversion
            if math.isnan(val) or math.isinf(val):
                return None
            return val

        if not isinstance(num_str, str):
            return None

        if num_str.strip() == "":
            return None

        try:
            # Remove commas
            cleaned = num_str.strip().replace(",", "")
            val = float(cleaned)
            # Check for NaN/inf
            if math.isnan(val) or math.isinf(val):
                return None
            return val
        except (ValueError, AttributeError):
            logger.warning(f"Failed to parse number: {num_str}")
            return None

    @staticmethod
    def parse_location(location_str: str) -> Optional[Dict[str, Any]]:
        """
        Parse location string to GeoJSON Point format and extract zip code.

        Expected format: "zipcode\\n(latitude, longitude)"
        Example: "95814\\n(38.5816, -121.4944)"

        Args:
            location_str: Location string from CSV

        Returns:
            Dict with GeoJSON Point and zip code, or None if parsing fails
            Format: {"type": "Point", "coordinates": [lon, lat], "zip_code": "95814"}
        """
        if not location_str or not isinstance(location_str, str):
            return None

        if location_str.strip() == "":
            return None

        try:
            # Split by newline or backslash-n
            parts = re.split(r'\\n|\n', location_str.strip())
            if len(parts) < 2:
                return None

            # Extract zip code from first part
            zip_code = parts[0].strip()

            # Extract coordinates from second part
            coord_part = parts[1].strip()
            # Match pattern: (latitude, longitude)
            match = re.search(r'\(([-\d.]+),\s*([-\d.]+)\)', coord_part)

            if match:
                lat = float(match.group(1))
                lon = float(match.group(2))

                # Validate coordinate ranges
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    # GeoJSON format: [longitude, latitude] with embedded zip
                    return {
                        "type": "Point",
                        "coordinates": [lon, lat],
                        "zip_code": zip_code if zip_code else None
                    }
                else:
                    logger.warning(f"Coordinates out of range: lat={lat}, lon={lon}")
                    return None
            else:
                return None

        except (ValueError, AttributeError, IndexError) as e:
            logger.warning(f"Failed to parse location: {location_str} - {e}")
            return None

    @staticmethod
    def parse_qualifications(qual_str: str) -> List[str]:
        """
        Parse supplier qualifications string to list.

        Args:
            qual_str: Space-separated qualifications (e.g., "CA-MB CA-SB CA-DVBE")

        Returns:
            List of qualification codes
        """
        if not qual_str or not isinstance(qual_str, str):
            return []

        if qual_str.strip() == "":
            return []

        # Split by whitespace and filter empty strings
        quals = [q.strip() for q in qual_str.split() if q.strip()]
        return quals

    @staticmethod
    def parse_classification_codes(codes_str: str) -> List[str]:
        """
        Parse classification codes (may be multi-line).

        Args:
            codes_str: Classification codes string

        Returns:
            List of classification codes
        """
        if not codes_str or not isinstance(codes_str, str):
            return []

        if codes_str.strip() == "":
            return []

        # Split by newline or comma
        codes = re.split(r'[\\n\n,]', codes_str.strip())
        # Clean and filter
        codes = [c.strip() for c in codes if c.strip()]
        return codes

    @staticmethod
    def parse_boolean(bool_str: str) -> Optional[bool]:
        """
        Parse YES/NO string to boolean.

        Args:
            bool_str: YES/NO string

        Returns:
            Boolean or None
        """
        if not bool_str or not isinstance(bool_str, str):
            return None

        if bool_str.strip() == "":
            return None

        cleaned = bool_str.strip().upper()
        if cleaned == "YES":
            return True
        elif cleaned == "NO":
            return False
        else:
            return None

    @staticmethod
    def normalize_department_name(dept_name: str) -> Optional[str]:
        """
        Normalize department name by removing common prefixes/suffixes.

        Args:
            dept_name: Full department name

        Returns:
            Normalized name
        """
        if not dept_name or not isinstance(dept_name, str):
            return None

        if dept_name.strip() == "":
            return None

        # Remove common patterns
        normalized = dept_name.strip()
        patterns = [
            r',?\s*Department of\s*$',
            r',?\s*Office of\s*$',
            r',?\s*State of\s*$',
            r'^\s*The\s+',
        ]

        for pattern in patterns:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)

        return normalized.strip()

    @staticmethod
    def parse_fiscal_year(fiscal_year_str: str) -> Optional[int]:
        """
        Parse fiscal year string to extract the starting year as an integer.

        Handles formats like "2013-2014" and extracts 2013 as an integer.

        Args:
            fiscal_year_str: Fiscal year string (e.g., "2013-2014")

        Returns:
            Starting year as integer, or None if parsing fails
        """
        if not fiscal_year_str or not isinstance(fiscal_year_str, str):
            return None

        cleaned = fiscal_year_str.strip()
        if cleaned == "":
            return None

        try:
            # Try to extract the first year from formats like "2013-2014"
            match = re.search(r'(\d{4})', cleaned)
            if match:
                year = int(match.group(1))
                # Validate year is within expected range
                if 2000 <= year <= 2100:
                    return year
                else:
                    logger.warning(f"Year out of range: {year}")
                    return None
            else:
                return None
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse fiscal year: {fiscal_year_str} - {e}")
            return None

    @staticmethod
    def clean_string(value: str) -> Optional[str]:
        """
        Clean and normalize string values.

        Args:
            value: Raw string value

        Returns:
            Cleaned string or None
        """
        if not value or not isinstance(value, str):
            return None

        cleaned = value.strip()
        if cleaned == "" or cleaned.upper() in ["NULL", "N/A", "NA", "NONE"]:
            return None

        return cleaned

    @staticmethod
    def transform_row(row: Dict[str, Any], source_file: str = None) -> Dict[str, Any]:
        """
        Transform a CSV row to MongoDB document format.

        Args:
            row: Dictionary containing raw CSV data
            source_file: Source filename for metadata

        Returns:
            Transformed dictionary ready for MongoDB insertion
        """
        # Clean helper - also handles NaN
        def get_clean(key: str) -> Optional[str]:
            value = DataTransformer.safe_convert_value(row.get(key))
            return DataTransformer.clean_string(value)

        # Safe get helper for raw values
        def get_safe(key: str) -> Any:
            return DataTransformer.safe_convert_value(row.get(key, ""))

        transformed = {
            # Identifiers
            "purchase_order_number": get_clean("Purchase Order Number"),
            "requisition_number": get_clean("Requisition Number"),
            "lpa_number": get_clean("LPA Number"),

            # Dates
            "creation_date": DataTransformer.parse_date(get_safe("Creation Date")),
            "purchase_date": DataTransformer.parse_date(get_safe("Purchase Date")),
            "fiscal_year": get_clean("Fiscal Year"),  # Keep original string format "2013-2014"
            "fiscal_year_start": DataTransformer.parse_fiscal_year(get_safe("Fiscal Year")),  # Extract starting year as integer

            # Acquisition
            "acquisition_type": get_clean("Acquisition Type"),
            "sub_acquisition_type": get_clean("Sub-Acquisition Type"),
            "acquisition_method": get_clean("Acquisition Method"),
            "sub_acquisition_method": get_clean("Sub-Acquisition Method"),

            # Department
            "department_name": get_clean("Department Name"),
            "department_normalized": DataTransformer.normalize_department_name(
                get_safe("Department Name")
            ),

            # Supplier
            "supplier_code": get_clean("Supplier Code"),
            "supplier_name": get_clean("Supplier Name"),
            "supplier_qualifications": DataTransformer.parse_qualifications(
                get_safe("Supplier Qualifications")
            ),
        }

        # Parse location and extract zip code
        location_data = DataTransformer.parse_location(get_safe("Location"))
        transformed["supplier_location"] = location_data

        # Use zip from location if Supplier Zip Code column is empty
        supplier_zip = get_clean("Supplier Zip Code")
        if not supplier_zip and location_data and location_data.get("zip_code"):
            transformed["supplier_zip_code"] = location_data["zip_code"]
        else:
            transformed["supplier_zip_code"] = supplier_zip

        # Continue with remaining fields
        transformed.update({
            # Item
            "item_name": get_clean("Item Name"),
            "item_description": get_clean("Item Description"),
            "quantity": DataTransformer.parse_number(get_safe("Quantity")),
            "unit_price": DataTransformer.parse_currency(get_safe("Unit Price")),
            "total_price": DataTransformer.parse_currency(get_safe("Total Price")),

            # Payment
            "cal_card": DataTransformer.parse_boolean(get_safe("CalCard")),

            # Classification
            "classification_codes": DataTransformer.parse_classification_codes(
                get_safe("Classification Codes")
            ),
            "normalized_unspsc": get_clean("Normalized UNSPSC"),
            "commodity_code": get_clean("Normalized UNSPSC"),  # Same as normalized
            "commodity_title": get_clean("Commodity Title"),
            "class_code": get_clean("Class"),
            "class_title": get_clean("Class Title"),
            "family_code": get_clean("Family"),
            "family_title": get_clean("Family Title"),
            "segment_code": get_clean("Segment"),
            "segment_title": get_clean("Segment Title"),

            # Metadata
            "source_file": source_file or "purchase_orders_2012_2015.csv"
        })

        return transformed


class DataValidator:
    """Validates transformed data before insertion."""

    @staticmethod
    def validate_document(doc: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a document before insertion.

        Args:
            doc: Transformed document

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Critical fields that should exist
        if not doc.get("purchase_order_number") and not doc.get("requisition_number"):
            errors.append("Missing both PO number and requisition number")

        # Date validation
        creation_date = doc.get("dates", {}).get("creation")
        if creation_date and not isinstance(creation_date, datetime):
            errors.append("Invalid creation date type")

        # Price validation (allow negative prices for credits/returns/refunds)
        total_price = doc.get("item", {}).get("total_price")
        if total_price is not None and abs(total_price) > 1e12:
            errors.append(f"Invalid total price: {total_price}")

        # Location validation
        location = doc.get("supplier", {}).get("location")
        if location is not None:
            if not isinstance(location, dict) or location.get("type") != "Point":
                errors.append("Invalid GeoJSON location format")
            coords = location.get("coordinates", [])
            if len(coords) != 2:
                errors.append("Invalid GeoJSON coordinates")

        is_valid = len(errors) == 0
        return is_valid, errors
