"""
PHASE 6: VENDOR CACHE

Implements Phase 6 from AGENT_GUIDE.md:

CACHE FILE: data/vendor_cache.json
STRUCTURE:
{
  "tnuva": {
    "display_name": "תנובה",
    "last_seen": "2025-04-19",
    "parse_count": 7,
    "confirmed_by_user": false,
    "confidence": 0.92,
    "row_format": "multiline",
    "quantity_pattern": 3,
    "has_discount_lines": true,
    "discount_keywords": ["החנה", "תחנה"],
    "barcode_position": "same_line",
    "column_assignments": {
      "ברקוד": "product_code",
      "תאור": "description",
      "תומכ": "quantity",
      "ריחמ": "unit_price",
      "נטו שורה": "line_net_total"
    }
  }
}

VENDOR DETECTION:
1. Scan first 10 lines of raw text
2. Look for store names using merchants_mapping.json
3. Convert to English key: "תנובה" → "tnuva" (from merchants_mapping.json)
4. Fuzzy match against existing cache (threshold 80)

CACHE USAGE:
- If vendor in cache AND (confirmed_by_user=true OR confidence ≥0.75):
  - Skip column detection loop
  - Apply cached column_assignments directly
  - Apply cached quantity_pattern directly
- Else: Run full detection, update cache after successful parse

CACHE IS OPTIONAL OPTIMIZATION:
- Pipeline MUST work without cache
- If cache missing/corrupted, fall back to full detection
- Cache updates: confidence = min(0.95, parse_count/(parse_count+2))
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
    """

    def __init__(self, cache_path: str = None, gui_callbacks: dict = None):
        """
        Args:
            cache_path: Path to cache file. Default: data/vendor_cache.json
            gui_callbacks: Optional dict of GUI callback functions for user interaction
        """
        if cache_path:
            self.cache_path = cache_path
        else:
            # Default path: data/vendor_cache.json
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(project_root, "data")
            os.makedirs(data_dir, exist_ok=True)
            self.cache_path = os.path.join(data_dir, "vendor_cache.json")

        self.cache = self._load_cache()
        self.merchants_mapping, self.blacklist = self._load_merchants_mapping_with_blacklist()
        self.vendor_keywords = self._get_vendor_keywords()

        # GUI callbacks for user interaction
        self.gui_callbacks = gui_callbacks or {}
        self.pending_actions = []  # Actions to be handled by GUI

    def _trigger_gui_callback(self, callback_name: str, *args, **kwargs):
        """
        Trigger a GUI callback if available.

        Args:
            callback_name: Name of the callback function
            *args, **kwargs: Arguments to pass to callback
        """
        print(f"Phase 6: Triggering GUI callback '{callback_name}'")
        print(f"  Available callbacks: {list(self.gui_callbacks.keys()) if self.gui_callbacks else 'None'}")

        if callback_name in self.gui_callbacks:
            print(f"  Callback found, executing...")
            try:
                result = self.gui_callbacks[callback_name](*args, **kwargs)
                print(f"  Callback returned: {result}")
                return result
            except Exception as e:
                print(f"GUI callback '{callback_name}' failed: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"TODO: GUI callback '{callback_name}' not available")

            # For trust score comparison, we need to decide what to do
            # By default, auto-update if better score for auto-made cache
            if callback_name == 'ask_replace_schema':
                vendor_name, current_score, new_score = args[:3]
                print(f"  Would ask user: Better schema for {vendor_name}? ({current_score:.2f} → {new_score:.2f})")
                # Return True to auto-update for now (will be changed when GUI is integrated)
                return True

            elif callback_name == 'on_mapping_missing':
                hebrew_text = args[0] if args else ''
                print(f"  Would ask user to add merchant mapping for: {hebrew_text}")
                # Return a default key for now
                return f"_gui_todo_{hebrew_text}"

            elif callback_name == 'create_cache_entry':
                vendor_name, trust_score, column_info, quantity_pattern = args[:4]
                print(f"  Would ask user: Create cache entry for {vendor_name}? (trust_score: {trust_score:.2f})")
                # By default, create cache for now (will be changed when GUI is integrated)
                return True

        return None

    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from file, handling v1.0 and v2.0 structures."""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

                # Handle different cache versions
                if "version" in cache_data:
                    # v2.0+ cache with version field
                    version = cache_data.get("version", "1.0")
                    if version == "2.0":
                        print(f"Phase 6: Loaded v2.0 cache")
                        # For now, return the full cache structure
                        # We'll handle vendor access differently
                        return cache_data
                    else:
                        print(f"Phase 6: Unknown cache version {version}, treating as v1.0")
                        return cache_data
                else:
                    # v1.0 cache (no version field)
                    print(f"Phase 6: Loaded v1.0 cache (no version field)")
                    return cache_data

            except (json.JSONDecodeError, IOError) as e:
                print(f"Phase 6: Failed to load cache: {e}, starting fresh")
                return {"version": "2.0", "vendors": {}}
        else:
            print(f"Phase 6: Cache file not found, will create v2.0: {self.cache_path}")
            return {"version": "2.0", "vendors": {}}

    def _load_merchants_mapping(self) -> Dict[str, List[str]]:
        """Load merchants mapping from JSON file."""
        mapping_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "merchants_mapping.json"
        )

        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _load_merchants_mapping_with_blacklist(self) -> Tuple[Dict[str, List[str]], List[str]]:
        """
        Load merchants mapping and extract blacklist.

        Returns:
            Tuple of (merchants_mapping_dict, blacklist_list)
        """
        mapping_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "merchants_mapping.json"
        )

        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    all_data = json.load(f)

                # Extract blacklist (if exists) and remove it from mappings
                blacklist = []
                merchants_mapping = {}

                for key, value in all_data.items():
                    if key == "__blacklist__":
                        blacklist = value if isinstance(value, list) else []
                    else:
                        merchants_mapping[key] = value

                print(f"Phase 6: Loaded merchants mapping with {len(merchants_mapping)} vendors")
                if blacklist:
                    print(f"Phase 6: Loaded blacklist with {len(blacklist)} entries: {blacklist}")

                return merchants_mapping, blacklist

            except (json.JSONDecodeError, IOError) as e:
                print(f"Phase 6: Failed to load merchants mapping: {e}")
                return {}, []

        print("Phase 6: merchants_mapping.json not found")
        return {}, []

    def _get_vendor_keywords(self) -> List[str]:
        """Get vendor keywords from merchants_mapping, excluding blacklisted words."""
        if not self.merchants_mapping:
            print("WARNING: merchants_mapping.json not loaded or empty")
            return []

        keywords = []
        for hebrew_names in self.merchants_mapping.values():
            for name in hebrew_names:
                # Skip if this name is in blacklist
                if hasattr(self, 'blacklist') and self.blacklist and name in self.blacklist:
                    print(f"  Skipping blacklisted keyword: '{name}'")
                    continue
                keywords.append(name)

        if hasattr(self, 'blacklist') and self.blacklist:
            print(f"Phase 6: Vendor keywords filtered, {len(keywords)} keywords (blacklisted {len(self.blacklist)} words)")
        else:
            print(f"Phase 6: Vendor keywords: {len(keywords)} keywords")

        return keywords

    def _save_cache(self):
        """Save cache to file in v2.0 format."""
        try:
            # Ensure we have v2.0 structure
            if "version" not in self.cache:
                self.cache = {"version": "2.0", "vendors": self.cache}
            elif self.cache.get("version") != "2.0":
                self.cache["version"] = "2.0"

            if "vendors" not in self.cache:
                # Move existing vendors into vendors dict
                vendors = {}
                for key, value in list(self.cache.items()):
                    if key not in ["version", "vendors"] and isinstance(value, dict):
                        vendors[key] = value
                        del self.cache[key]
                self.cache["vendors"] = vendors

            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"Phase 6: Failed to save cache: {e}")

    def _get_vendor_entry(self, vendor_slug: str) -> Optional[Dict[str, Any]]:
        """Get vendor entry from cache, handling v1.0 and v2.0 structures."""
        if "version" in self.cache and self.cache.get("version") == "2.0":
            # v2.0: vendors are under "vendors" key
            return self.cache.get("vendors", {}).get(vendor_slug)
        else:
            # v1.0: vendors are at top level
            return self.cache.get(vendor_slug)

    def _set_vendor_entry(self, vendor_slug: str, entry: Dict[str, Any]):
        """Set vendor entry in cache, handling v1.0 and v2.0 structures."""
        if "version" in self.cache and self.cache.get("version") == "2.0":
            # v2.0: vendors are under "vendors" key
            if "vendors" not in self.cache:
                self.cache["vendors"] = {}
            self.cache["vendors"][vendor_slug] = entry
        else:
            # v1.0: vendors are at top level
            self.cache[vendor_slug] = entry

    def _is_user_made_schema(self, entry: Dict[str, Any]) -> bool:
        """Check if schema is user-made (created or modified by user)."""
        if "basics" in entry:
            # v2.0 entry
            basics = entry.get("basics", {})
            return basics.get("user_created", False) or basics.get("modified_by", "") == "user"
        else:
            # v1.0 entry - check legacy fields
            return entry.get("confirmed_by_user", False)

    def detect_vendor_from_text(self, raw_text: str) -> Dict[str, Any]:
        """
        Extract vendor from raw text.

        Args:
            raw_text: Raw text from scan B

        Returns:
            Dictionary with vendor detection results
        """
        lines = raw_text.splitlines()[:10]  # First 10 lines
        text_to_search = ' '.join(lines)

        print(f"Phase 6: Detecting vendor in first {len(lines)} lines")
        print(f"Phase 6: First 10 lines preview: {text_to_search[:200]}...")

        best_vendor = None
        best_score = 0
        matched_keyword = None

        for keyword in self.vendor_keywords:
            # Search for keyword in text
            score = fuzz.partial_ratio(keyword.lower(), text_to_search.lower())
            if score > best_score and score >= 60:  # Reasonable match threshold
                best_score = score
                best_vendor = keyword
                matched_keyword = keyword
                print(f"  Potential match: '{keyword}' score: {score}")

        if best_vendor:
            print(f"  Best vendor match: '{best_vendor}' score: {best_score}")

        # BLACKLIST CHECK: If we have a match, check if it might be a false positive due to blacklisted words
        if best_vendor and hasattr(self, 'blacklist') and self.blacklist:
            text_lower = text_to_search.lower()
            for blacklisted_word in self.blacklist:
                blacklisted_lower = blacklisted_word.lower()
                if blacklisted_lower in text_lower:
                    # Text contains blacklisted word
                    print(f"  Text contains blacklisted word: '{blacklisted_word}'")

                    # Check if the matched vendor is similar to the blacklisted word
                    # Example: "אסם" (Osem) is similar to "קסם" (part of Kfar Qasem)
                    similarity = fuzz.ratio(best_vendor.lower(), blacklisted_lower)
                    if similarity >= 70:  # If vendor name is similar to blacklisted word
                        print(f"  WARNING: Potential false positive! Matched '{best_vendor}' is {similarity}% similar to blacklisted '{blacklisted_word}'")
                        print(f"  Original match score: {best_score}, rejecting match")

                        # Check if there's a better match (second best)
                        second_best_vendor = None
                        second_best_score = 0
                        second_matched_keyword = None

                        for keyword in self.vendor_keywords:
                            if keyword == best_vendor:
                                continue  # Skip the already matched one
                            score = fuzz.partial_ratio(keyword.lower(), text_lower)
                            if score > second_best_score and score >= 60:
                                second_best_score = score
                                second_best_vendor = keyword
                                second_matched_keyword = keyword

                        if second_best_vendor:
                            print(f"  Using second best match: '{second_best_vendor}' (score: {second_best_score})")
                            best_vendor = second_best_vendor
                            best_score = second_best_score
                            matched_keyword = second_matched_keyword
                        else:
                            print(f"  No alternative match found, rejecting completely")
                            best_vendor = None
                            best_score = 0
                            matched_keyword = None

                    break  # Only check first blacklisted word found

        # Get English key for vendor
        vendor_english_key = None
        if best_vendor and self.merchants_mapping:
            for english_key, hebrew_names in self.merchants_mapping.items():
                if best_vendor in hebrew_names:
                    vendor_english_key = english_key
                    break

        result = {
            'success': best_vendor is not None,
            'vendor_name': best_vendor,
            'vendor_english_key': vendor_english_key,
            'match_score': best_score,
            'matched_keyword': matched_keyword,
            'text_searched': text_to_search[:100] + '...' if len(text_to_search) > 100 else text_to_search
        }

        if result['success']:
            print(f"  ✓ Vendor detected: {best_vendor} (score: {best_score})")
        else:
            print(f"  ✗ No vendor detected in first {len(lines)} lines")

        return result

    def find_vendor(self, vendor_name: str, vendor_english_key: str = None) -> Optional[Dict[str, Any]]:
        """
        Fuzzy match vendor name against cache.

        Args:
            vendor_name: Detected vendor name
            vendor_english_key: English vendor key from merchants_mapping (optional)

        Returns:
            Cache entry if found and meets confidence threshold, else None
        """
        if not vendor_name or not self.cache:
            return None

        # Use English key if available
        if vendor_english_key:
            vendor_slug = vendor_english_key.lower()
        else:
            vendor_slug = self._hebrew_to_english_key(vendor_name)

        print(f"Phase 6: Looking for vendor '{vendor_name}' (key: '{vendor_slug}') in cache")

        # First try exact key match using helper
        entry = self._get_vendor_entry(vendor_slug)
        if entry and self._is_cache_entry_valid(entry):
            print(f"  ✓ Exact cache match found: {vendor_slug}")
            return entry

        # Try fuzzy match against display names
        best_match = None
        best_score = 0

        # Get vendors to iterate over (handling v1.0 and v2.0)
        vendors_dict = self.cache
        if "version" in self.cache and self.cache.get("version") == "2.0":
            vendors_dict = self.cache.get("vendors", {})

        for slug, entry in vendors_dict.items():
            # Get display name from appropriate location
            display_name = ""
            if "basics" in entry:
                # v2.0: display_name in basics
                display_name = entry.get("basics", {}).get("display_name", "")
            else:
                # v1.0: display_name directly
                display_name = entry.get('display_name', '')

            if display_name:
                score = fuzz.token_sort_ratio(vendor_name.lower(), display_name.lower())
                if score > best_score and score >= 80:  # Threshold from AGENT_GUIDE
                    best_score = score
                    best_match = entry
                    best_match['matched_slug'] = slug

        if best_match and self._is_cache_entry_valid(best_match):
            print(f"  ✓ Fuzzy cache match found: {best_match.get('display_name')} (score: {best_score})")
            return best_match

        print(f"  ✗ No cache match found for '{vendor_name}'")
        return None

    def _hebrew_to_english_key(self, text: str) -> str:
        """
        Convert Hebrew text to English key using merchants_mapping.json ONLY.

        Example: "תנובה" → "tnuva" (from merchants_mapping.json)

        If not found in mapping: TODO - GUI should ask user to add merchant.
        This is for merchant mapping (merchants_mapping.json), not vendor cache.
        For now, returns text with '_todo_no_mapping_' prefix.
        """
        if not text:
            return ""

        if not self.merchants_mapping:
            print(f"ERROR: merchants_mapping.json not loaded for text: {text}")
            # GUI should handle this case
            self._trigger_gui_callback('on_mapping_missing', text)
            return f"_todo_no_mapping_{text}"

        # Search for Hebrew text in merchants_mapping using FUZZY matching
        best_match = None
        best_score = 0
        best_length = 0
        matched_hebrew = ""

        for english_key, hebrew_names in self.merchants_mapping.items():
            for hebrew_name in hebrew_names:
                # Use partial_ratio like detect_vendor_from_text does
                score = fuzz.partial_ratio(hebrew_name.lower(), text.lower())

                # Check if this is a better match
                if score > best_score and score >= 80:  # Threshold similar to find_vendor
                    best_score = score
                    best_match = english_key.lower()
                    best_length = len(hebrew_name)
                    matched_hebrew = hebrew_name
                elif score == best_score and score >= 80 and len(hebrew_name) > best_length:
                    # Tie-break: longer match wins (keeping existing longest-match logic)
                    best_match = english_key.lower()
                    best_length = len(hebrew_name)
                    matched_hebrew = hebrew_name

        # Return best match if found
        if best_match:
            print(f"Phase 6: Fuzzy matched '{matched_hebrew}' (score: {best_score}, length: {best_length}) → '{best_match}'")
            return best_match

        # Hebrew text not found in merchants_mapping
        # TODO: GUI should ask user to add this merchant to merchants_mapping.json
        # KEEP EXISTING TODO - This is correct for merchant mapping, not cache
        print(f"TODO: Hebrew text '{text}' not found in merchants_mapping.json")
        print(f"  → GUI should ask user to add this merchant")

        # Create simple key for cache (remove non-alphanumeric Hebrew chars)
        # This is temporary until GUI adds merchant to mapping
        simple_text = re.sub(r'[^\u0590-\u05FF]', '', text)  # Keep only Hebrew letters
        if not simple_text:
            simple_text = text[:20]  # Fallback to first 20 chars

        return f"_todo_no_mapping_{simple_text}"

    def _is_cache_entry_valid(self, entry: Dict[str, Any]) -> bool:
        """
        Check if cache entry is valid for use.

        According to AGENT_GUIDE:
        - confirmed_by_user=true OR confidence ≥0.75
        Handles v1.0 and v2.0 structures.
        """
        # Check for v2.0 structure first
        if "confidence" in entry and isinstance(entry["confidence"], dict):
            # v2.0: confidence is a dict with trust_score
            confidence_data = entry.get("confidence", {})
            trust_score = confidence_data.get("trust_score", 0.0)
            user_verified = confidence_data.get("user_verified", False)

            if user_verified:
                return True
            if trust_score >= 0.75:
                return True
        else:
            # v1.0: direct fields
            confirmed = entry.get('confirmed_by_user', False)
            confidence = entry.get('confidence', 0.0)

            if confirmed:
                return True
            if confidence >= 0.75:
                return True

        return False

    def _calculate_trust_score(self, validation_metrics: Dict[str, float]) -> float:
        """
        Calculate trust score from validation metrics.

        Formula: 0.3×column_confidence + 0.4×validation_rate + 0.2×pattern_consistency + 0.1×user_verification

        Args:
            validation_metrics: Dictionary with validation metrics

        Returns:
            trust_score: Calculated trust score (0.0 to 1.0)
        """
        if not validation_metrics:
            return 0.5  # Default starting trust

        # Get metrics with defaults
        column_confidence = validation_metrics.get('column_confidence', 0.5)
        validation_rate = validation_metrics.get('validation_rate', 0.5)
        pattern_consistency = validation_metrics.get('pattern_consistency', 0.5)
        user_verification = validation_metrics.get('user_verification', 0.5)

        # Calculate weighted sum
        trust_score = (
            0.3 * column_confidence +
            0.4 * validation_rate +
            0.2 * pattern_consistency +
            0.1 * user_verification
        )

        # Ensure within bounds
        trust_score = max(0.0, min(1.0, trust_score))

        # Round to 2 decimal places
        return round(trust_score, 2)

    def _get_current_trust_score(self, entry: Dict[str, Any]) -> float:
        """
        Get current trust score from cache entry.

        Handles v1.0 and v2.0 structures.

        Args:
            entry: Vendor cache entry (can be None if no cache was created)

        Returns:
            Current trust score (0.0 to 1.0)
        """
        if not entry:
            return 0.5  # Default if no cache entry

        # Check for v2.0 structure first
        if "confidence" in entry and isinstance(entry["confidence"], dict):
            # v2.0: confidence is a dict with trust_score
            return entry["confidence"].get("trust_score", 0.5)
        else:
            # v1.0: direct confidence field
            return entry.get("confidence", 0.5)

    def _reload_cache_from_file(self):
        """Reload cache from file (e.g., after SchemaEditorWindow saves)."""
        print(f"Phase 6: Reloading cache from file")
        try:
            new_cache = self._load_cache()
            self.cache = new_cache
            print(f"  Cache reloaded successfully")
        except Exception as e:
            print(f"  WARNING: Failed to reload cache: {e}")

    def _get_english_vendor_name(self, vendor_slug: str) -> str:
        """Get English vendor name from merchants_mapping.json using vendor_slug."""
        if not hasattr(self, 'merchants_mapping') or not self.merchants_mapping:
            return vendor_slug.replace("_", " ").title()

        vendor_slug_lower = vendor_slug.lower()
        for english_key, hebrew_names in self.merchants_mapping.items():
            if english_key.lower() == vendor_slug_lower:
                return english_key  # Return proper English name (e.g., "Ridan")

        return vendor_slug.replace("_", " ").title()

    def _prepare_schema_editor_data(self, vendor_slug: str, entry: Dict[str, Any] = None,
                                    column_info: Dict[str, Any] = None,
                                    quantity_pattern: str = None,
                                    row_format: str = None) -> Dict[str, Any]:
        """
        Prepare schema data for SchemaEditorWindow pre-filling.

        Args:
            vendor_slug: Vendor slug/identifier
            entry: Existing cache entry (None for new detection)
            column_info: Column detection results (if entry is None)
            quantity_pattern: Detected quantity pattern (if entry is None)
            row_format: Row format (if entry is None)

        Returns:
            Normalized schema data for SchemaEditorWindow
        """
        # Start with basic structure
        schema_data = {
            "display_name": self._get_english_vendor_name(vendor_slug),
            "trust_score": 0.5,
            "user_verified": False,
            "column_mapping": {},
            "validation_rules": {
                "tolerance_percent": 5.0,
                "quantity_calculation": "auto"
            },
            "parsing_rules": {
                "skip_lines": []
            }
        }

        if entry:
            # Use existing cache entry
            # Keep English display_name from _get_english_vendor_name()
            # (Cache stores Hebrew, we want English for SchemaEditorWindow)

            # Get trust score
            if "confidence" in entry and isinstance(entry["confidence"], dict):
                schema_data["trust_score"] = entry["confidence"].get("trust_score", 0.5)
            else:
                schema_data["trust_score"] = entry.get("confidence", 0.5)

            # Get column mappings from legacy_fields
            if "legacy_fields" in entry:
                legacy = entry["legacy_fields"]

                # Priority 1: column_assignments dict (if has data)
                if "column_assignments" in legacy and legacy["column_assignments"]:
                    schema_data["column_mapping"] = legacy.get("column_assignments", {})
                # Priority 2: detected_columns array (convert to dict)
                elif "detected_columns" in legacy and legacy["detected_columns"]:
                    column_mapping = {}
                    for col in legacy["detected_columns"]:
                        hebrew = col.get("hebrew_text", "").strip()
                        assigned = col.get("assigned_field", "").strip()
                        if hebrew and assigned:  # Skip empty hebrew_text entries
                            column_mapping[hebrew] = assigned
                    if column_mapping:
                        schema_data["column_mapping"] = column_mapping
            elif "column_assignments" in entry and entry["column_assignments"]:
                schema_data["column_mapping"] = entry.get("column_assignments", {})

            # Merge existing validation rules
            if "validation_rules" in entry:
                existing_validation = entry["validation_rules"]
                # Preserve existing quantity_calculation if not default "unknown"
                if existing_validation.get("quantity_calculation") and existing_validation["quantity_calculation"] != "unknown":
                    schema_data["validation_rules"]["quantity_calculation"] = existing_validation["quantity_calculation"]
                # Merge other validation rules
                schema_data["validation_rules"].update(existing_validation)

            # Include parsing rules (skip_lines, etc.)
            if "parsing_rules" in entry:
                schema_data["parsing_rules"] = entry.get("parsing_rules", schema_data["parsing_rules"])
        else:
            # Use new detection data
            # Trust score will be calculated separately, use default for now
            schema_data["trust_score"] = 0.5  # Default, will be updated by caller

            # Get column mappings from column_info
            if column_info and column_info.get('success'):
                # Phase3 returns column_mapping, Phase6 expects column_assignments
                # Try column_mapping first, then column_assignments
                column_mapping_data = column_info.get('column_mapping', column_info.get('column_assignments', {}))
                schema_data["column_mapping"] = column_mapping_data

            # Add quantity pattern and row format to parsing rules if available
            if quantity_pattern:
                schema_data["parsing_rules"]["quantity_pattern"] = quantity_pattern
            if row_format:
                schema_data["parsing_rules"]["row_format"] = row_format

        return schema_data

    def add_or_update_vendor(
        self,
        vendor_name: str,
        column_info: Dict[str, Any] = None,
        quantity_pattern: str = None,
        row_format: str = None,
        vendor_english_key: str = None,
        validation_metrics: Dict[str, float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Add or update vendor in cache with trust score calculation.

        Args:
            vendor_name: Vendor name
            column_info: Column detection results
            quantity_pattern: Detected quantity pattern
            row_format: 'multiline' or 'single_line'
            vendor_english_key: English vendor key from merchants_mapping
            validation_metrics: Dictionary with validation metrics:
                - column_confidence: Confidence from column detection (Phase 3)
                - validation_rate: Quantity validation rate (Phase 4: qty × price ≈ total)
                - pattern_consistency: Pattern consistency score (Phase 4)
                - user_verification: User verification score (default 0.5 if never verified)
            **kwargs: Additional vendor properties

        Returns:
            Updated cache entry
        """
        # Use English key if available
        if vendor_english_key:
            vendor_slug = vendor_english_key.lower()
        else:
            vendor_slug = self._hebrew_to_english_key(vendor_name)

        entry = self._get_vendor_entry(vendor_slug)

        if entry:
            # UPDATE EXISTING ENTRY (v2.0 globrands schema only)

            # All entries should be v2.0 globrands schema
            if "basics" not in entry:
                print(f"ERROR: Entry for {vendor_slug} missing basics - initializing v2.0 structure")
                today = datetime.now().strftime('%Y-%m-%d')
                entry = {
                    'basics': {
                        'display_name': vendor_name,
                        'user_created': False,
                        'creation_date': today,
                        'last_modified': today,
                        'modified_by': 'auto_update',
                        'document_type': 'receipt'
                    },
                    'confidence': {
                        'trust_score': 0.5,
                        'source': 'auto_detected',
                        'parses_since_verification': 0,
                        'user_verified': False
                    },
                    'columns_gui': [],
                    'validation_rules': {
                        'quantity_calculation': 'auto',
                        'tolerance_percent': 5.0,
                        'auto_validate': True
                    },
                    'parsing_rules': {
                        'document_type': 'receipt',
                        'skip_lines': []
                    },
                    'legacy_fields': {}
                }

            # v2.0 entry - ensure legacy_fields exists for column data
            if 'legacy_fields' not in entry:
                entry['legacy_fields'] = {}
            legacy = entry['legacy_fields']

            # Update parse count and last seen
            legacy['parse_count'] = legacy.get('parse_count', 0) + 1
            legacy['last_seen'] = datetime.now().strftime('%Y-%m-%d')

            # Update basics
            entry['basics']['last_modified'] = datetime.now().strftime('%Y-%m-%d')
            entry['basics']['modified_by'] = 'auto_update'

            # Calculate trust score from validation metrics
            trust_score = self._calculate_trust_score(validation_metrics)
            current_trust_score = self._get_current_trust_score(entry)

            # Check if schema is user-made
            is_user_made = self._is_user_made_schema(entry)

            # REVISED IMPLEMENTATION: Trust score comparison for auto-made caches only
            # User-made cache → Always use (no questions)
            # Auto-made cache exists + New auto-made has better score → Ask user if they want to switch
            if not is_user_made:  # Only for auto-made caches
                skip_save_cache = False  # Flag to skip _save_cache if editor already saved
                print(f"Phase 6: Auto-made schema for {vendor_slug}")
                print(f"  Current trust score: {current_trust_score:.2f}")
                print(f"  New trust score: {trust_score:.2f}")

                # Check if both scores are low confidence (<0.6)
                both_low_confidence = (current_trust_score < 0.6 and trust_score < 0.6)

                if trust_score > current_trust_score:
                    # Better schema detected - ask user via GUI
                    print(f"  Better schema detected ({current_trust_score:.2f} → {trust_score:.2f})")
                    print(f"  Asking user via GUI: 'Better schema detected for {vendor_name}. Replace?'")

                    # Ask user via GUI callback
                    should_replace = self._trigger_gui_callback('ask_replace_schema', vendor_name, current_trust_score, trust_score)

                    if should_replace:
                        # User approved - update with better schema
                        entry['confidence']['trust_score'] = trust_score

                        # Update properties with better schema
                        if column_info and column_info.get('success'):
                            # Try column_mapping first (Phase3), then column_assignments
                            column_assignments = column_info.get('column_mapping', column_info.get('column_assignments', {}))
                            if not column_assignments and 'detected_columns' in column_info:
                                # Convert detected_columns to column_assignments for cache
                                column_assignments = {}
                                for col in column_info['detected_columns']:
                                    hebrew = col.get('hebrew_text', '')
                                    assigned = col.get('assigned_field', '')
                                    if hebrew and assigned:
                                        column_assignments[hebrew] = assigned

                            entry['legacy_fields']['column_assignments'] = column_assignments
                            entry['legacy_fields']['detected_columns'] = column_info.get('detected_columns', [])

                        if quantity_pattern:
                            entry['legacy_fields']['quantity_pattern'] = quantity_pattern

                        if row_format:
                            entry['legacy_fields']['row_format'] = row_format

                        print(f"  ✓ User approved: Updated with better schema (score: {trust_score:.2f})")
                    else:
                        # User declined - keep existing schema
                        print(f"  ✗ User declined: Keeping existing schema (score: {current_trust_score:.2f})")
                        entry['confidence']['trust_score'] = current_trust_score

                elif both_low_confidence:
                    # BOTH scores are low - ask user what to do
                    print(f"  Both scores are low (current: {current_trust_score:.2f}, new: {trust_score:.2f})")
                    print(f"  Asking user via GUI: 'Edit cache for {vendor_name}?'")

                    # Determine which schema is better (higher score)
                    better_score = max(current_trust_score, trust_score)

                    # Prepare schema data for editor
                    if better_score == current_trust_score:
                        # Current cache is better
                        better_schema_data = self._prepare_schema_editor_data(vendor_slug, entry)
                    else:
                        # New detection is better
                        better_schema_data = self._prepare_schema_editor_data(vendor_slug, None,
                            column_info, quantity_pattern, row_format)
                        # Update trust score in schema data
                        better_schema_data["trust_score"] = trust_score

                    # Call new callback with three options: Edit, Replace, Keep
                    user_choice = self._trigger_gui_callback('edit_schema_low_confidence',
                        vendor_name, current_trust_score, trust_score, better_schema_data)

                    # Handle three return types
                    if user_choice is None or user_choice is False:
                        # "Keep Current" - do nothing
                        print(f"  ✗ User chose to keep current schema (score: {current_trust_score:.2f})")
                        entry['confidence']['trust_score'] = current_trust_score
                    elif user_choice is True:
                        # "Replace Anyway" - update cache with better schema
                        entry['confidence']['trust_score'] = trust_score

                        # Update with current schema (might have different column detection, etc.)
                        if column_info and column_info.get('success'):
                            # Try column_mapping first (Phase3), then column_assignments
                            column_assignments = column_info.get('column_mapping', column_info.get('column_assignments', {}))
                            if not column_assignments and 'detected_columns' in column_info:
                                # Convert detected_columns to column_assignments for cache
                                column_assignments = {}
                                for col in column_info['detected_columns']:
                                    hebrew = col.get('hebrew_text', '')
                                    assigned = col.get('assigned_field', '')
                                    if hebrew and assigned:
                                        column_assignments[hebrew] = assigned

                            entry['legacy_fields']['column_assignments'] = column_assignments
                            entry['legacy_fields']['detected_columns'] = column_info.get('detected_columns', [])

                        if quantity_pattern:
                            entry['legacy_fields']['quantity_pattern'] = quantity_pattern

                        if row_format:
                            entry['legacy_fields']['row_format'] = row_format

                        print(f"  ✓ User chose to replace anyway (new: {trust_score:.2f})")
                    elif isinstance(user_choice, dict) and user_choice.get("edited"):
                        # "Edit Cache" - user edited schema in SchemaEditorWindow
                        # SchemaEditorWindow already saved with user_created: true
                        print(f"  ✓ User edited schema - saved with user_created: true")

                        # Reload cache from file to get updated schema
                        self._reload_cache_from_file()

                        # Get the updated entry
                        updated_entry = self._get_vendor_entry(vendor_slug)
                        if updated_entry:
                            entry = updated_entry
                            print(f"  Reloaded updated schema from file")
                        else:
                            print(f"  WARNING: Could not find updated schema for {vendor_slug}")

                        # Skip saving cache (already saved by editor)
                        # Set a flag to skip _save_cache() at the end
                        skip_save_cache = True
                    else:
                        # Fallback: keep current
                        print(f"  ✗ Unknown choice, keeping current schema (score: {current_trust_score:.2f})")
                        entry['confidence']['trust_score'] = current_trust_score

                else:
                    # No improvement and not both low
                    print(f"  No improvement (current: {current_trust_score:.2f}, new: {trust_score:.2f}) - keeping existing schema")
                    # Keep existing confidence
                    entry['confidence']['trust_score'] = current_trust_score
            else:
                # User-made schema - always keep as is
                print(f"Phase 6: User-made schema for {vendor_slug} - always using existing schema")
                print(f"  Current trust score: {current_trust_score:.2f}")
                # Do not update user-made schema automatically
                entry['confidence']['trust_score'] = current_trust_score
        else:
            # CREATE NEW ENTRY (v2.0 globrands-style)
            today = datetime.now().strftime('%Y-%m-%d')

            # Create v2.0 entry with globrands structure
            entry = {
                'basics': {
                    'display_name': vendor_name,
                    'user_created': False,  # Auto-detected
                    'creation_date': today,
                    'last_modified': today,
                    'modified_by': 'auto_create',
                    'document_type': 'receipt'  # Default, could be invoice
                },
                'confidence': {
                    'trust_score': 0.5,  # Starting trust - TODO: calculate from validation metrics
                    'source': 'auto_detected',
                    'parses_since_verification': 0,
                    'user_verified': False,
                    'verification_date': None,
                    'verification_method': None
                },
                'columns_gui': [],
                'validation_rules': {
                    'quantity_calculation': 'auto',
                    'tolerance_percent': 5.0,
                    'auto_validate': True,
                    'barcode_format': None,
                    'invoice_specific': False
                },
                'parsing_rules': {
                    'document_type': 'receipt',
                    'skip_lines': []
                },
                'legacy_fields': {  # For backward compatibility with current code
                    'parse_count': 1,
                    'last_seen': today,
                    'confirmed_by_user': False,
                    'row_format': row_format or 'unknown',
                    'quantity_pattern': quantity_pattern or 'unknown',
                    'has_discount_lines': kwargs.get('has_discount_lines', False),
                    'discount_keywords': kwargs.get('discount_keywords', []),
                    'barcode_position': kwargs.get('barcode_position', 'unknown'),
                    'column_assignments': column_info.get('column_mapping', column_info.get('column_assignments', {})) if column_info and column_info.get('success') else {},
                    'detected_columns': column_info.get('detected_columns', []) if column_info and column_info.get('success') else []
                }
            }
            # Calculate trust score from validation metrics
            trust_score = self._calculate_trust_score(validation_metrics)
            entry['confidence']['trust_score'] = trust_score

            # Update legacy confidence to match (for backward compatibility)
            entry['legacy_fields']['confidence'] = trust_score

            print(f"Phase 6: Calculated trust score for new entry: {trust_score:.2f}")
            if validation_metrics:
                print(f"  Metrics: column_confidence={validation_metrics.get('column_confidence', 0.5):.2f}, "
                      f"validation_rate={validation_metrics.get('validation_rate', 0.5):.2f}, "
                      f"pattern_consistency={validation_metrics.get('pattern_consistency', 0.5):.2f}, "
                      f"user_verification={validation_metrics.get('user_verification', 0.5):.2f}")

            # NEW LOGIC: Ask user to create cache for low-confidence new vendors
            # Threshold: trust_score < 0.6 (low confidence)
            should_create_cache = True  # Default: create cache

            print(f"Phase 6: New vendor '{vendor_name}', trust_score: {trust_score:.2f}")

            if trust_score < 0.6:
                print(f"Phase 6: LOW confidence ({trust_score:.2f} < 0.6) - Should show cache creation dialog")
                print(f"  Asking user via GUI: 'Create cache entry for {vendor_name}?'")

                # Ask user via GUI callback
                should_create_cache = self._trigger_gui_callback(
                    'create_cache_entry',
                    vendor_name,
                    trust_score,
                    column_info,
                    quantity_pattern or 'unknown'
                )
                print(f"Phase 6: GUI callback returned: {should_create_cache}")
            else:
                print(f"Phase 6: HIGH confidence ({trust_score:.2f} ≥ 0.6) - Auto-creating cache")

            # Only create cache entry if user approved or score is high enough
            if should_create_cache:
                self._set_vendor_entry(vendor_slug, entry)
                print(f"Phase 6: Created new v2.0 cache entry for {vendor_slug}")
                return entry
            else:
                print(f"Phase 6: Not creating cache entry for {vendor_name} (user declined or error)")
                # Return None to indicate no cache was created
                return None

        # Save cache
        self._save_cache()

        return entry

    def update_confidence(self, entry: Dict[str, Any]) -> float:
        """
        Update confidence based on parse count.

        Formula: confidence = min(0.95, parse_count/(parse_count+2))
        """
        parse_count = entry.get('parse_count', 1)
        confidence = min(0.95, parse_count / (parse_count + 2))
        return round(confidence, 2)

    
    def should_skip_column_detection(self, cache_entry: Dict[str, Any]) -> bool:
        """
        Determine if column detection should be skipped based on cache.

        According to AGENT_GUIDE:
        - If vendor in cache AND (confirmed_by_user=true OR confidence ≥0.75)

        Handles v1.0 and v2.0 structures.
        """
        if not cache_entry:
            return False

        # Handle v2.0 structure first
        if "confidence" in cache_entry and isinstance(cache_entry["confidence"], dict):
            # v2.0: confidence is a dict with trust_score and user_verified
            confidence_data = cache_entry.get("confidence", {})
            trust_score = confidence_data.get("trust_score", 0.0)
            user_verified = confidence_data.get("user_verified", False)

            # Check legacy_fields for backward compatibility
            legacy = cache_entry.get("legacy_fields", {})
            confirmed_by_user = legacy.get("confirmed_by_user", False)

            if user_verified or confirmed_by_user or trust_score >= 0.75:
                print(f"Phase 6: Skipping column detection (user_verified: {user_verified}, confirmed_by_user: {confirmed_by_user}, trust_score: {trust_score})")
                return True
        else:
            # v1.0: direct fields
            confirmed = cache_entry.get('confirmed_by_user', False)
            confidence = cache_entry.get('confidence', 0.0)

            if confirmed or confidence >= 0.75:
                print(f"Phase 6: Skipping column detection (confirmed: {confirmed}, confidence: {confidence})")
                return True

        return False

    def get_column_info_from_cache(
        self,
        cache_entry: Dict[str, Any],
        raw_text: str
    ) -> tuple:
        """
        Get column info from cache entry (for pipeline compatibility).

        Args:
            cache_entry: Cache entry
            raw_text: Raw OCR text

        Returns:
            Tuple of (column_info_dict, success_bool)
        """
        if not cache_entry or not raw_text:
            return None, False

        # Handle v1.0 and v2.0 structures
        if "legacy_fields" in cache_entry:
            # v2.0: get column data from legacy_fields, confidence from proper v2.0 field
            legacy = cache_entry.get("legacy_fields", {})
            column_assignments = legacy.get('column_assignments', {})
            detected_columns = legacy.get('detected_columns', [])

            # If column_assignments is empty but detected_columns has data, convert it
            if not column_assignments and detected_columns:
                column_assignments = {}
                for col in detected_columns:
                    hebrew = col.get('hebrew_text', '').strip()
                    assigned = col.get('assigned_field', '').strip()
                    if hebrew and assigned:
                        column_assignments[hebrew] = assigned

            # Get confidence from proper v2.0 field if available
            if 'confidence' in cache_entry and isinstance(cache_entry['confidence'], dict):
                confidence = cache_entry['confidence'].get('trust_score', 0.5)
            else:
                confidence = legacy.get('confidence', 0.5)
        else:
            # v1.0: direct fields
            column_assignments = cache_entry.get('column_assignments', {})
            confidence = cache_entry.get('confidence', 0.5)

        if not column_assignments:
            print("Phase 6: No column assignments in cache entry")
            return None, False

        # Convert to column_info format expected by pipeline
        detected_columns = []
        for hebrew_text, assigned_field in column_assignments.items():
            detected_columns.append({
                'hebrew_text': hebrew_text,
                'assigned_field': assigned_field,
                'confidence': confidence
            })

        # Try to find header lines in raw text
        lines = raw_text.splitlines()
        lines_range = None

        # Search for header lines containing column headers
        for i in range(min(20, len(lines))):  # Check first 20 lines
            line_text = lines[i]
            # Count how many column headers appear in this line
            headers_found = sum(1 for header in column_assignments.keys()
                              if header and header in line_text)

            if headers_found >= 2:  # At least 2 headers found
                lines_range = (i, i + 1)
                break

        column_info = {
            'success': True,
            'detected_columns': detected_columns,
            'column_assignments': column_assignments,
            'lines_range': lines_range,
            'source': 'vendor_cache',
            'vendor_slug': next((k for k, v in self.cache.items()
                               if v == cache_entry), None)
        }

        return column_info, True

# End of Phase6VendorCache class