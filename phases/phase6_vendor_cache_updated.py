"""
OBSOLETE - NOT USED BY MAIN PIPELINE
=====================================
PHASE 6: VENDOR CACHE (GUI-Friendly Version)

Implements Phase 6 with GUI-friendly schema while maintaining backward compatibility.

NEW CACHE STRUCTURE (v2.0):
{
  "version": "2.0",
  "vendors": {
    "tnuva": {
      "basics": {
        "display_name": "תנובה",
        "user_created": false,
        "creation_date": "2026-04-23",
        "last_modified": "2026-04-23",
        "modified_by": "auto"
      },
      "confidence": {
        "trust_score": 0.95,
        "source": "auto_detected",
        "parses_since_verification": 7,
        "user_verified": true,
        "verification_date": "2026-04-23"
      },
      "columns_gui": [
        {
          "index": 1,
          "hebrew_header": "תאור",
          "english_name": "description",
          "type": "text",
          "width_percent": 50,
          "examples": ["חלב 3% 1 ליטר", "קוטג 5% 250 גרם"]
        },
        {
          "index": 2,
          "hebrew_header": "כמות",
          "english_name": "quantity",
          "type": "number",
          "width_percent": 15,
          "examples": ["2", "1", "60"]
        }
      ],
      "validation_rules": {
        "quantity_calculation": "quantity × unit_price = line_net_total",
        "tolerance_percent": 1.0,
        "auto_validate": true
      },
      "legacy_fields": {
        "parse_count": 7,
        "last_seen": "2026-04-23",
        "confirmed_by_user": true,
        "confidence": 0.95,
        "row_format": "single_line",
        "quantity_pattern": 1,
        "column_assignments": {
          "תאור": "description",
          "כמות": "quantity"
        }
      }
    }
  }
}

BACKWARD COMPATIBILITY:
- Old cache entries are automatically upgraded on load
- All existing method signatures remain unchanged
- Pipeline continues to work exactly as before
"""

import json
import os
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from rapidfuzz import fuzz


class Phase6VendorCache:
    """
    Phase 6: Vendor cache for storing and reusing receipt layout patterns.

    Caches vendor-specific layout information to avoid re-detection
    on subsequent receipts from the same vendor.

    NEW: GUI-friendly schema with backward compatibility.
    """

    def __init__(self, cache_path: str = None):
        """
        Args:
            cache_path: Path to cache file. Default: data/vendor_cache.json
        """
        if cache_path:
            self.cache_path = cache_path
        else:
            # Default path: data/vendor_cache.json
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(project_root, "data")
            os.makedirs(data_dir, exist_ok=True)
            self.cache_path = os.path.join(data_dir, "vendor_cache.json")

        self.cache = self._load_and_upgrade_cache()
        self.vendor_keywords = self._load_vendor_keywords()
        self.merchants_mapping = self._load_merchants_mapping()

    def _load_and_upgrade_cache(self) -> Dict[str, Any]:
        """Load cache from file and upgrade old entries to new schema."""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

                # Check if this is old format (no version field)
                if "version" not in cache_data:
                    print("Phase 6: Upgrading old cache format to v2.0...")
                    cache_data = self._upgrade_old_cache(cache_data)

                return cache_data

            except (json.JSONDecodeError, IOError) as e:
                print(f"Phase 6: Failed to load cache: {e}, starting fresh")
                return self._create_empty_cache()
        else:
            print(f"Phase 6: Cache file not found, will create: {self.cache_path}")
            return self._create_empty_cache()

    def _create_empty_cache(self) -> Dict[str, Any]:
        """Create empty cache with version 2.0 structure."""
        return {
            "version": "2.0",
            "vendors": {}
        }

    def _upgrade_old_cache(self, old_cache: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upgrade old cache format to new v2.0 format.

        Old format: {vendor_slug: {display_name, parse_count, confidence, ...}}
        New format: {version: "2.0", vendors: {vendor_slug: {...}}}
        """
        new_cache = self._create_empty_cache()

        for vendor_slug, old_entry in old_cache.items():
            if vendor_slug == "version":
                continue

            # Create new entry structure
            new_entry = {
                "basics": {
                    "display_name": old_entry.get("display_name", vendor_slug),
                    "user_created": False,
                    "creation_date": old_entry.get("last_seen", datetime.now().strftime('%Y-%m-%d')),
                    "last_modified": old_entry.get("last_seen", datetime.now().strftime('%Y-%m-%d')),
                    "modified_by": "auto_upgrade"
                },
                "confidence": {
                    "trust_score": old_entry.get("confidence", 0.5),
                    "source": "auto_detected",
                    "parses_since_verification": old_entry.get("parse_count", 0),
                    "user_verified": old_entry.get("confirmed_by_user", False),
                    "verification_date": old_entry.get("last_seen", datetime.now().strftime('%Y-%m-%d')) if old_entry.get("confirmed_by_user", False) else None
                },
                "columns_gui": [],
                "validation_rules": {
                    "quantity_calculation": "unknown",
                    "tolerance_percent": 5.0,
                    "auto_validate": True
                },
                "legacy_fields": old_entry.copy()  # Preserve all old fields for compatibility
            }

            # Convert column_assignments to columns_gui format
            column_assignments = old_entry.get("column_assignments", {})
            detected_columns = old_entry.get("detected_columns", [])

            if column_assignments:
                for i, (hebrew_header, english_name) in enumerate(column_assignments.items(), 1):
                    new_entry["columns_gui"].append({
                        "index": i,
                        "hebrew_header": hebrew_header,
                        "english_name": english_name,
                        "type": self._guess_column_type(english_name),
                        "width_percent": 100 // len(column_assignments) if column_assignments else 25,
                        "examples": []
                    })
            elif detected_columns:
                for i, col in enumerate(detected_columns, 1):
                    new_entry["columns_gui"].append({
                        "index": i,
                        "hebrew_header": col.get("hebrew_text", ""),
                        "english_name": col.get("assigned_field", f"column_{i}"),
                        "type": self._guess_column_type(col.get("assigned_field", "")),
                        "width_percent": 100 // len(detected_columns) if detected_columns else 25,
                        "examples": []
                    })

            new_cache["vendors"][vendor_slug] = new_entry

        print(f"Phase 6: Upgraded {len(old_cache)} vendor entries to v2.0 format")
        return new_cache

    def _guess_column_type(self, english_name: str) -> str:
        """Guess column type based on English name."""
        english_name = english_name.lower()
        if "price" in english_name or "amount" in english_name or "total" in english_name:
            return "price"
        elif "quantity" in english_name or "qty" in english_name or "amount" in english_name:
            return "number"
        elif "code" in english_name or "barcode" in english_name or "id" in english_name:
            return "code"
        else:
            return "text"

    def _save_cache(self):
        """Save cache to file."""
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"Phase 6: Failed to save cache: {e}")

    # === EXISTING METHODS (preserved exactly) ===

    def _load_vendor_keywords(self) -> List[str]:
        """Load vendor keywords from merchants_mapping.json."""
        mapping = self._load_merchants_mapping()
        if not mapping:
            # Fallback to hardcoded list if mapping fails to load
            return [
                'תנובה', 'רמי לוי', 'שופרסל', 'יינות ביתן', 'זכרונית',
                'אושר עד', 'מחסני השוק', 'יגואר', 'טיב טעם',
                'מגה', 'חצי חינם', 'ויקטורי', 'יוחננוף'
            ]

        # Extract all Hebrew keywords from mapping
        hebrew_keywords = []
        for vendor_keywords in mapping.values():
            for keyword in vendor_keywords:
                # Check if contains Hebrew letters (Unicode range 0590-05FF)
                if any('\u0590' <= c <= '\u05FF' for c in keyword):
                    hebrew_keywords.append(keyword)

        # Also include English versions for vendors that might appear in English
        for vendor_keywords in mapping.values():
            for keyword in vendor_keywords:
                # Include English keywords (lowercase letters only)
                if keyword and all(c.islower() or c in '.-_ ' for c in keyword):
                    hebrew_keywords.append(keyword)

        if not hebrew_keywords:
            print("Phase 6: No vendor keywords loaded, using fallback")
            return self._load_vendor_keywords()  # Return fallback

        print(f"Phase 6: Loaded {len(hebrew_keywords)} vendor keywords from merchants_mapping.json")
        return hebrew_keywords

    def _load_merchants_mapping(self) -> Dict[str, List[str]]:
        """Load merchants mapping from JSON file."""
        mapping_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "merchants_mapping.json"
        )

        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
                print(f"Phase 6: Loaded merchants_mapping.json with {len(mapping)} vendors")
                return mapping
            except (json.JSONDecodeError, IOError) as e:
                print(f"Phase 6: Failed to load merchants_mapping.json: {e}")
                return {}
        else:
            print(f"Phase 6: merchants_mapping.json not found at {mapping_path}")
            return {}

    def detect_vendor_from_text(self, raw_text: str) -> Dict[str, Any]:
        """
        Detect vendor name from raw text (first 10 lines).

        Args:
            raw_text: Raw OCR text from receipt

        Returns:
            Dict with success, vendor_name, match_score, etc.
        """
        if not raw_text:
            return {'success': False, 'error': 'No raw text provided'}

        lines = raw_text.split('\n')
        # Search in first 10 lines (increased from 2 for better detection)
        lines_to_search = lines[:10]
        text_to_search = '\n'.join(lines_to_search)

        best_score = 0
        best_vendor = None
        matched_keyword = None
        match_type = None

        text_lower = text_to_search.lower()

        for keyword in self.vendor_keywords:
            keyword_lower = keyword.lower()

            # 1. EXACT MATCH (highest priority)
            if keyword in text_to_search:
                best_score = 100
                best_vendor = keyword
                matched_keyword = keyword
                match_type = 'exact'
                break

            # 2. REVERSED EXACT MATCH (for Hebrew text that might be reversed)
            if self._contains_reversed(keyword, text_to_search):
                best_score = 95
                best_vendor = keyword
                matched_keyword = keyword
                match_type = 'reversed_exact'
                break

            # 3. FUZZY MATCH (lower priority, higher threshold)
            # Use token_sort_ratio for better Hebrew matching
            score = fuzz.token_sort_ratio(keyword_lower, text_lower)

            # Higher threshold for fuzzy matching
            fuzzy_threshold = 75  # Increased from 60

            if score > best_score and score >= fuzzy_threshold:
                best_score = score
                best_vendor = keyword
                matched_keyword = keyword
                match_type = 'fuzzy'

        result = {
            'success': best_vendor is not None,
            'vendor_name': best_vendor,
            'match_score': best_score,
            'matched_keyword': matched_keyword,
            'match_type': match_type,
            'text_searched': text_to_search[:100] + '...' if len(text_to_search) > 100 else text_to_search
        }

        if result['success']:
            print(f"  ✓ Vendor detected: {best_vendor} (score: {best_score}, type: {match_type})")
        else:
            print(f"  ✗ No vendor detected in first {len(lines)} lines")

        return result

    def _contains_reversed(self, keyword: str, text: str) -> bool:
        """Check if text contains reversed version of Hebrew keyword."""
        # Simple reversal check for Hebrew text
        if not any('\u0590' <= c <= '\u05FF' for c in keyword):
            return False

        # Hebrew text might appear reversed in OCR
        reversed_keyword = keyword[::-1]
        return reversed_keyword in text

    def find_vendor(self, vendor_name: str) -> Optional[Dict[str, Any]]:
        """
        Fuzzy match vendor name against cache.

        Args:
            vendor_name: Detected vendor name

        Returns:
            Cache entry if found and meets confidence threshold, else None
        """
        if not vendor_name or not self.cache.get("vendors"):
            return None

        # Normalize to slug
        vendor_slug = self._hebrew_to_slug(vendor_name)
        print(f"Phase 6: Looking for vendor '{vendor_name}' (slug: '{vendor_slug}') in cache")

        # First try exact slug match in new format
        if vendor_slug in self.cache.get("vendors", {}):
            entry = self.cache["vendors"][vendor_slug]
            # Return legacy format for compatibility with existing pipeline
            return self._convert_to_legacy_format(entry, vendor_slug)

        # Try fuzzy match against all vendor slugs
        best_match = None
        best_score = 0

        for cached_slug in self.cache.get("vendors", {}).keys():
            score = fuzz.ratio(vendor_slug, cached_slug)
            if score > best_score and score >= 75:  # 75% similarity threshold
                best_score = score
                best_match = cached_slug

        if best_match:
            print(f"  ✓ Fuzzy cache match: {best_match} (score: {best_score})")
            entry = self.cache["vendors"][best_match]
            return self._convert_to_legacy_format(entry, best_match)

        print(f"  ✗ No cache match found for '{vendor_name}'")
        return None

    def _convert_to_legacy_format(self, new_entry: Dict[str, Any], vendor_slug: str) -> Dict[str, Any]:
        """Convert new cache entry to legacy format for compatibility."""
        # First check if legacy_fields exists
        if "legacy_fields" in new_entry:
            legacy_entry = new_entry["legacy_fields"].copy()
            # Update with latest confidence/trust_score
            legacy_entry["confidence"] = new_entry["confidence"]["trust_score"]
            legacy_entry["confirmed_by_user"] = new_entry["confidence"]["user_verified"]
            return legacy_entry

        # Create legacy format from new format
        legacy_entry = {
            "display_name": new_entry["basics"]["display_name"],
            "parse_count": new_entry["confidence"].get("parses_since_verification", 1),
            "last_seen": datetime.now().strftime('%Y-%m-%d'),
            "confirmed_by_user": new_entry["confidence"]["user_verified"],
            "confidence": new_entry["confidence"]["trust_score"],
            "row_format": "single_line",  # Default
            "quantity_pattern": 1,  # Default
            "has_discount_lines": False,
            "discount_keywords": [],
            "barcode_position": "unknown"
        }

        # Convert columns_gui to column_assignments
        column_assignments = {}
        for col in new_entry.get("columns_gui", []):
            if col["hebrew_header"] and col["english_name"]:
                column_assignments[col["hebrew_header"]] = col["english_name"]

        if column_assignments:
            legacy_entry["column_assignments"] = column_assignments

        return legacy_entry

    def _hebrew_to_slug(self, text: str) -> str:
        """
        Convert Hebrew text to lowercase slug.

        Examples:
            "תנובה" → "tnuva"
            "שופרסל" → "shufersal"
        """
        if not text:
            return ""

        # Transliterate Hebrew to approximate English
        hebrew_to_english = {
            'א': 'a', 'ב': 'b', 'ג': 'g', 'ד': 'd', 'ה': 'h',
            'ו': 'v', 'ז': 'z', 'ח': 'ch', 'ט': 't', 'י': 'y',
            'כ': 'k', 'ל': 'l', 'מ': 'm', 'נ': 'n', 'ס': 's',
            'ע': 'a', 'פ': 'p', 'צ': 'ts', 'ק': 'k', 'ר': 'r',
            'ש': 'sh', 'ת': 't'
        }

        slug = ""
        for char in text:
            if '\u0590' <= char <= '\u05FF':  # Hebrew Unicode range
                slug += hebrew_to_english.get(char, char)
            elif char.isalpha():
                slug += char.lower()
            elif char.isdigit():
                slug += char
            elif char in ' -_':
                slug += '_'

        # Remove consecutive underscores and trim
        slug = re.sub(r'_+', '_', slug)
        slug = slug.strip('_')

        return slug

    def _is_cache_entry_valid(self, entry: Dict[str, Any]) -> bool:
        """
        Check if cache entry is valid for use.

        Args:
            entry: Cache entry (legacy format)

        Returns:
            True if entry is valid and meets minimum confidence
        """
        if not entry:
            return False

        # Check required fields
        required_fields = ['display_name', 'confidence']
        for field in required_fields:
            if field not in entry:
                print(f"Phase 6: Cache entry missing required field: {field}")
                return False

        # Check confidence threshold
        confidence = entry.get('confidence', 0)
        confirmed = entry.get('confirmed_by_user', False)

        # Same logic as before
        if confirmed or confidence >= 0.75:
            return True

        print(f"Phase 6: Cache entry below confidence threshold (confidence: {confidence}, confirmed: {confirmed})")
        return False

    def add_or_update_vendor(
        self,
        vendor_name: str,
        column_info: Dict[str, Any] = None,
        quantity_pattern: str = None,
        row_format: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Add or update vendor in cache.

        Args:
            vendor_name: Vendor name
            column_info: Column detection results
            quantity_pattern: Detected quantity pattern
            row_format: 'multiline' or 'single_line'
            **kwargs: Additional vendor properties

        Returns:
            Updated cache entry (legacy format)
        """
        vendor_slug = self._hebrew_to_slug(vendor_name)

        # Ensure cache structure exists
        if "vendors" not in self.cache:
            self.cache["vendors"] = {}

        if vendor_slug in self.cache["vendors"]:
            # Update existing entry
            entry = self.cache["vendors"][vendor_slug]

            # Update basics
            entry["basics"]["last_modified"] = datetime.now().strftime('%Y-%m-%d')
            entry["basics"]["modified_by"] = "auto_update"

            # Update confidence
            entry["confidence"]["parses_since_verification"] = entry["confidence"].get("parses_since_verification", 0) + 1
            entry["confidence"]["trust_score"] = self._calculate_trust_score(entry)

            # Update legacy fields
            if "legacy_fields" not in entry:
                entry["legacy_fields"] = {}

            legacy_entry = entry["legacy_fields"]
            legacy_entry["parse_count"] = legacy_entry.get("parse_count", 0) + 1
            legacy_entry["last_seen"] = datetime.now().strftime('%Y-%m-%d')

            # Update properties if provided
            if column_info and column_info.get('success'):
                legacy_entry["column_assignments"] = column_info.get('column_assignments', {})
                legacy_entry["detected_columns"] = column_info.get('detected_columns', [])

                # Also update columns_gui
                entry["columns_gui"] = []
                for i, (hebrew_header, english_name) in enumerate(column_info.get('column_assignments', {}).items(), 1):
                    entry["columns_gui"].append({
                        "index": i,
                        "hebrew_header": hebrew_header,
                        "english_name": english_name,
                        "type": self._guess_column_type(english_name),
                        "width_percent": 100 // len(column_info.get('column_assignments', {})) if column_info.get('column_assignments', {}) else 25,
                        "examples": []
                    })

            if quantity_pattern:
                legacy_entry["quantity_pattern"] = quantity_pattern

            if row_format:
                legacy_entry["row_format"] = row_format

            # Update confidence in legacy entry
            legacy_entry["confidence"] = entry["confidence"]["trust_score"]

            print(f"Phase 6: Updated cache entry for {vendor_slug} (parse_count: {legacy_entry['parse_count']})")
        else:
            # Create new entry
            entry = {
                "basics": {
                    "display_name": vendor_name,
                    "user_created": False,
                    "creation_date": datetime.now().strftime('%Y-%m-%d'),
                    "last_modified": datetime.now().strftime('%Y-%m-%d'),
                    "modified_by": "auto_create"
                },
                "confidence": {
                    "trust_score": 0.33,  # Initial low confidence
                    "source": "auto_detected",
                    "parses_since_verification": 1,
                    "user_verified": False,
                    "verification_date": None
                },
                "columns_gui": [],
                "validation_rules": {
                    "quantity_calculation": "unknown",
                    "tolerance_percent": 5.0,
                    "auto_validate": True
                },
                "legacy_fields": {
                    "display_name": vendor_name,
                    "parse_count": 1,
                    "last_seen": datetime.now().strftime('%Y-%m-%d'),
                    "confirmed_by_user": False,
                    "confidence": 0.33,
                    "row_format": row_format or 'unknown',
                    "quantity_pattern": quantity_pattern or 'unknown',
                    "has_discount_lines": kwargs.get('has_discount_lines', False),
                    "discount_keywords": kwargs.get('discount_keywords', []),
                    "barcode_position": kwargs.get('barcode_position', 'unknown')
                }
            }

            if column_info and column_info.get('success'):
                entry["legacy_fields"]["column_assignments"] = column_info.get('column_assignments', {})
                entry["legacy_fields"]["detected_columns"] = column_info.get('detected_columns', [])

                # Create columns_gui
                for i, (hebrew_header, english_name) in enumerate(column_info.get('column_assignments', {}).items(), 1):
                    entry["columns_gui"].append({
                        "index": i,
                        "hebrew_header": hebrew_header,
                        "english_name": english_name,
                        "type": self._guess_column_type(english_name),
                        "width_percent": 100 // len(column_info.get('column_assignments', {})) if column_info.get('column_assignments', {}) else 25,
                        "examples": []
                    })

            self.cache["vendors"][vendor_slug] = entry
            print(f"Phase 6: Created new cache entry for {vendor_slug}")

        # Save cache
        self._save_cache()

        # Return legacy format for compatibility
        return self._convert_to_legacy_format(entry, vendor_slug)

    def _calculate_trust_score(self, entry: Dict[str, Any]) -> float:
        """
        Calculate trust score based on multiple metrics.

        Formula: trust_score = 0.3×column_confidence + 0.4×validation_rate + 0.2×pattern_consistency + 0.1×user_verification

        For now, simplified to maintain compatibility.
        """
        legacy_entry = entry.get("legacy_fields", {})
        parse_count = legacy_entry.get("parse_count", 1)
        confirmed = legacy_entry.get("confirmed_by_user", False)

        # Simplified version matching existing behavior
        if confirmed:
            return 0.95  # High confidence for user-verified entries

        # Same formula as before: min(0.95, parse_count/(parse_count+2))
        confidence = min(0.95, parse_count / (parse_count + 2))
        return confidence

    def update_confidence(self, entry: Dict[str, Any]) -> float:
        """
        Update confidence score based on parse count.

        Maintains exact same behavior as before for compatibility.
        """
        parse_count = entry.get('parse_count', 1)
        # Same formula as before
        confidence = min(0.95, parse_count / (parse_count + 2))
        return confidence

    def apply_cached_column_assignments(
        self,
        cache_entry: Dict[str, Any],
        raw_text: str
    ) -> Tuple[Optional[Dict[str, Any]], bool]:
        """
        Apply cached column assignments to raw text.

        Args:
            cache_entry: Cache entry (legacy format)
            raw_text: Raw OCR text

        Returns:
            Tuple of (column_info_dict, success_bool)
        """
        if not cache_entry or not raw_text:
            return None, False

        column_assignments = cache_entry.get('column_assignments', {})
        if not column_assignments:
            print("Phase 6: No column assignments in cache entry")
            return None, False

        # Convert to column_info format expected by pipeline
        detected_columns = []
        for hebrew_text, assigned_field in column_assignments.items():
            detected_columns.append({
                'hebrew_text': hebrew_text,
                'assigned_field': assigned_field,
                'confidence': cache_entry.get('confidence', 0.5)
            })

        column_info = {
            'success': True,
            'column_mapping': column_assignments,
            'vendor_cache_used': True,
            'cache_entry': cache_entry,
            'detected_columns': detected_columns,
            'fallback_used': False,
            'net_total_column': None,
            'net_total_found': False,
            'lines_range': None
        }

        print(f"Phase 6: Applied cached column assignments for {len(column_assignments)} columns")
        return column_info, True

    def should_skip_column_detection(self, cache_entry: Dict[str, Any]) -> bool:
        """
        Determine whether to skip column detection based on cache entry.

        Args:
            cache_entry: Cache entry (legacy format)

        Returns:
            True if should skip column detection
        """
        if not cache_entry:
            return False

        confidence = cache_entry.get('confidence', 0)
        confirmed = cache_entry.get('confirmed_by_user', False)
        parse_count = cache_entry.get('parse_count', 0)

        should_skip = confirmed or confidence >= 0.75

        print(f"Phase 6: Skipping column detection (confirmed: {confirmed}, confidence: {confidence:.2f}, parses: {parse_count}) → skip={should_skip}")
        return should_skip

    # === NEW GUI METHODS (added functionality) ===

    def create_vendor_template_from_gui(self, vendor_name: str, columns_data: List[Dict], validation_rules: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create vendor template from GUI input.

        Args:
            vendor_name: Vendor name (Hebrew)
            columns_data: List of column definitions from GUI
            validation_rules: Validation rules from GUI

        Returns:
            New cache entry (new format)
        """
        vendor_slug = self._hebrew_to_slug(vendor_name)

        # Create new entry with user_created flag
        entry = {
            "basics": {
                "display_name": vendor_name,
                "user_created": True,
                "creation_date": datetime.now().strftime('%Y-%m-%d'),
                "last_modified": datetime.now().strftime('%Y-%m-%d'),
                "modified_by": "user"
            },
            "confidence": {
                "trust_score": 1.0,  # User-created = 100% trust
                "source": "user_created",
                "parses_since_verification": 0,
                "user_verified": True,
                "verification_date": datetime.now().strftime('%Y-%m-%d')
            },
            "columns_gui": columns_data,
            "validation_rules": validation_rules,
            "legacy_fields": {
                "display_name": vendor_name,
                "parse_count": 1,
                "last_seen": datetime.now().strftime('%Y-%m-%d'),
                "confirmed_by_user": True,
                "confidence": 1.0,
                "row_format": "single_line",  # Default, can be updated
                "quantity_pattern": 1,  # Default
                "has_discount_lines": False,
                "discount_keywords": [],
                "barcode_position": "unknown",
                "column_assignments": {}
            }
        }

        # Convert columns_gui to column_assignments
        column_assignments = {}
        for col in columns_data:
            if col.get("hebrew_header") and col.get("english_name"):
                column_assignments[col["hebrew_header"]] = col["english_name"]

        if column_assignments:
            entry["legacy_fields"]["column_assignments"] = column_assignments

        # Store in cache
        if "vendors" not in self.cache:
            self.cache["vendors"] = {}

        self.cache["vendors"][vendor_slug] = entry
        self._save_cache()

        print(f"Phase 6: Created user template for {vendor_name} with {len(columns_data)} columns")
        return entry

    def get_vendor_template_for_gui(self, vendor_slug: str) -> Optional[Dict[str, Any]]:
        """
        Get vendor template in GUI-friendly format.

        Args:
            vendor_slug: Vendor slug

        Returns:
            Template in GUI format or None if not found
        """
        if vendor_slug in self.cache.get("vendors", {}):
            return self.cache["vendors"][vendor_slug]
        return None

    def update_template_from_gui(self, vendor_slug: str, updates: Dict[str, Any]) -> bool:
        """
        Update vendor template from GUI edits.

        Args:
            vendor_slug: Vendor slug
            updates: Dictionary of updates

        Returns:
            True if successful
        """
        if vendor_slug not in self.cache.get("vendors", {}):
            return False

        entry = self.cache["vendors"][vendor_slug]

        # Apply updates
        for key, value in updates.items():
            if key in ["basics", "confidence", "columns_gui", "validation_rules"]:
                if isinstance(value, dict) and key in entry:
                    entry[key].update(value)
                else:
                    entry[key] = value

        # Mark as user-modified
        entry["basics"]["last_modified"] = datetime.now().strftime('%Y-%m-%d')
        entry["basics"]["modified_by"] = "user"
        entry["confidence"]["user_verified"] = True
        entry["confidence"]["verification_date"] = datetime.now().strftime('%Y-%m-%d')
        entry["confidence"]["trust_score"] = 1.0

        # Update legacy fields for compatibility
        if "legacy_fields" in entry:
            entry["legacy_fields"]["confirmed_by_user"] = True
            entry["legacy_fields"]["confidence"] = 1.0
            entry["legacy_fields"]["last_seen"] = datetime.now().strftime('%Y-%m-%d')

        self._save_cache()
        print(f"Phase 6: Updated template for {vendor_slug} from GUI")
        return True

    def get_vendor_stats(self) -> Dict[str, Any]:
        """
        Get statistics about vendor cache.

        Returns:
            Dictionary with cache statistics
        """
        vendors = self.cache.get("vendors", {})

        stats = {
            "total_vendors": len(vendors),
            "user_created": sum(1 for v in vendors.values() if v.get("basics", {}).get("user_created", False)),
            "auto_detected": sum(1 for v in vendors.values() if not v.get("basics", {}).get("user_created", False)),
            "user_verified": sum(1 for v in vendors.values() if v.get("confidence", {}).get("user_verified", False)),
            "high_trust": sum(1 for v in vendors.values() if v.get("confidence", {}).get("trust_score", 0) >= 0.9),
            "version": self.cache.get("version", "unknown")
        }

        return stats