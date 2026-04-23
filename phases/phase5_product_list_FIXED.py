"""
OBSOLETE - NOT USED BY MAIN PIPELINE
=====================================
PHASE 5: PRODUCT LIST INTEGRATION - FIXED VERSION

FIXES APPLIED (per TODO.md with AGENT_GUIDE.md corrections):
1. ✅ Load merchants_mapping.json for vendor filtering
2. ✅ Filter product list by vendor before matching
3. ✅ Handle trailing spaces in column names
4. ✅ Add proper match_type tracking
5. ✅ Ignore ברקוד column (per AGENT_GUIDE.md)
6. ✅ Use קוד פריט for CatalogNo (not ברקוד)

NOTE: TODO.md says to use ברקוד column, but AGENT_GUIDE.md says "ברקוד → EMPTY COLUMN - IGNORE COMPLETELY"
Following AGENT_GUIDE.md (authoritative) and user confirmation.
"""

import re
import os
import pandas as pd
import sys
import json
from typing import List, Dict, Any, Optional, Tuple
from rapidfuzz import fuzz, process


class Phase5ProductList:
    """
    Phase 5: Product list integration - FIXED VERSION

    Matches receipt items against master product list with vendor filtering.
    """

    def __init__(self, excel_path: str = None):
        """
        Args:
            excel_path: Path to Excel file. If None, uses default path.
        """
        self.excel_path = excel_path or "C:/Users/Kfir Ezer/Downloads/prices_rimon_03-02-25.xlsx"
        self.product_df = None
        self.loaded = False
        self.fuzzy_threshold = 70

        # Load merchants mapping for vendor filtering
        self.merchants_mapping = self._load_merchants_mapping()

        # Column name mapping (actual column names with trailing spaces)
        self.column_mapping = {}

        # Cache for filtered dataframes by vendor
        self.vendor_filter_cache = {}

    def _load_merchants_mapping(self) -> Dict[str, List[str]]:
        """Load merchants_mapping.json for vendor filtering."""
        mapping_path = "merchants_mapping.json"
        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self._safe_print(f"Phase 5: Warning - Could not load {mapping_path}: {e}")
                return {}
        else:
            self._safe_print(f"Phase 5: Warning - {mapping_path} not found")
            return {}

    def _safe_print(self, message: str):
        """Safely print messages that may contain Hebrew characters."""
        try:
            print(message)
        except (UnicodeEncodeError, UnicodeDecodeError) as e:
            try:
                safe_message = message.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
                if not safe_message.strip():
                    safe_message = "[Message contained non-UTF-8 characters]"
                print(safe_message)
            except:
                print(f"[Could not print message due to encoding error: {type(e).__name__}]")

    def load_product_list(self) -> bool:
        """
        Load product list from Excel file.

        Returns:
            True if loaded successfully, False otherwise
        """
        if not os.path.exists(self.excel_path):
            self._safe_print(f"Phase 5: Product list not found at {self.excel_path}")
            return False

        try:
            self._safe_print(f"Phase 5: Loading product list from {self.excel_path}")
            self.product_df = pd.read_excel(self.excel_path, engine='openpyxl')

            # Map stripped column names to actual column names (handles trailing spaces)
            self.column_mapping = {str(col).strip(): col for col in self.product_df.columns}

            # Required columns (after stripping spaces)
            required_columns = ['קוד פריט', 'תאור פריט']
            missing = []

            for req_col in required_columns:
                if req_col in self.column_mapping:
                    self._safe_print(f"Phase 5: Column '{req_col}' found as '{self.column_mapping[req_col]}'")
                else:
                    missing.append(req_col)

            if missing:
                self._safe_print(f"Phase 5: Missing required columns: {missing}")
                self._safe_print(f"Available columns (stripped): {list(self.column_mapping.keys())}")
                return False

            self._safe_print(f"Phase 5: Loaded {len(self.product_df)} products")

            # Clean data
            self._clean_product_data()

            self.loaded = True
            return True

        except Exception as e:
            error_msg = str(e)
            self._safe_print(f"Phase 5: Failed to load product list: {error_msg}")
            return False

    def _clean_product_data(self):
        """Clean and prepare product data for matching."""
        # Get actual column names (with trailing spaces)
        product_code_col = self.column_mapping['קוד פריט']
        description_col = self.column_mapping['תאור פריט']

        # Store for easy access
        self.product_code_col = product_code_col
        self.description_col = description_col

        # Ensure קוד פריט is string
        self.product_df[product_code_col] = self.product_df[product_code_col].astype(str)

        # Ensure תאור פריט is string, handle NaN
        self.product_df[description_col] = self.product_df[description_col].fillna('').astype(str)

        # Create normalized Hebrew column for fuzzy matching
        self.product_df['תאור מנורמל'] = self.product_df[description_col].apply(self._normalize_hebrew)

        # Filter out empty product codes
        self.product_df = self.product_df[self.product_df[product_code_col].str.strip() != '']

        self._safe_print(f"Phase 5: After cleaning, {len(self.product_df)} products remain")

    def _get_vendor_keywords(self, vendor_name: str) -> List[str]:
        """Get vendor keywords from merchants_mapping.json."""
        if not vendor_name or not self.merchants_mapping:
            return []

        # Try exact match first
        for key, keywords in self.merchants_mapping.items():
            if vendor_name.lower() == key.lower():
                return keywords

        # Try partial match in keywords
        normalized_vendor = self._normalize_hebrew(vendor_name)
        for key, keywords in self.merchants_mapping.items():
            for keyword in keywords:
                if normalized_vendor in self._normalize_hebrew(keyword):
                    return keywords

        return []

    def _filter_by_vendor(self, vendor_name: str) -> pd.DataFrame:
        """
        Filter product list by vendor/supplier.

        Uses merchants_mapping.json to find vendor keywords,
        then filters by supplier name columns.
        """
        if not vendor_name or not self.loaded:
            return self.product_df

        # Check cache
        cache_key = vendor_name.lower()
        if cache_key in self.vendor_filter_cache:
            return self.vendor_filter_cache[cache_key]

        # Get vendor keywords
        vendor_keywords = self._get_vendor_keywords(vendor_name)
        if not vendor_keywords:
            self._safe_print(f"Phase 5: No keywords found for vendor '{vendor_name}'")
            self.vendor_filter_cache[cache_key] = self.product_df
            return self.product_df

        # Normalize keywords for matching
        normalized_keywords = [self._normalize_hebrew(kw) for kw in vendor_keywords]

        # Check supplier columns
        supplier_cols = []
        for col in self.product_df.columns:
            stripped = str(col).strip()
            if stripped in ['שם ספק ראשי', 'supplier', 'ספק']:
                supplier_cols.append(col)

        if not supplier_cols:
            self._safe_print(f"Phase 5: No supplier columns found")
            self.vendor_filter_cache[cache_key] = self.product_df
            return self.product_df

        # Create mask for any supplier column containing any vendor keyword
        mask = pd.Series(False, index=self.product_df.index)

        for col in supplier_cols:
            # Normalize supplier names for matching
            supplier_series = self.product_df[col].fillna('').astype(str)
            normalized_suppliers = supplier_series.apply(self._normalize_hebrew)

            # Check each keyword
            for keyword in normalized_keywords:
                if keyword:  # Skip empty keywords
                    col_mask = normalized_suppliers.str.contains(keyword, na=False)
                    mask = mask | col_mask

        filtered_df = self.product_df[mask]

        self._safe_print(f"Phase 5: Filtered to {len(filtered_df)} products from vendor '{vendor_name}'")

        # Cache result
        self.vendor_filter_cache[cache_key] = filtered_df
        return filtered_df

    def enrich_items(
        self,
        items: List[Dict[str, Any]],
        vendor_name: str = None
    ) -> List[Dict[str, Any]]:
        """
        Main entry point: Enrich items with product list data.

        FIXED: Filters products by vendor before matching.

        Args:
            items: List of receipt items
            vendor_name: Hebrew vendor name for filtering (optional)

        Returns:
            Enriched items with CatalogNo and canonical descriptions
        """
        if not self.loaded:
            if not self.load_product_list():
                self._safe_print("Phase 5: Cannot enrich items, product list not loaded")
                return items

        self._safe_print(f"Phase 5: Enriching {len(items)} items (vendor: {vendor_name or 'unknown'})")

        # Filter product list by vendor if vendor name provided
        search_df = self._filter_by_vendor(vendor_name) if vendor_name else self.product_df

        enriched_items = []

        for i, item in enumerate(items):
            self._safe_print(f"\n  Item {i+1}: {item.get('description', 'N/A')[:50]}...")

            enriched_item = item.copy()

            # Step 1: Extract code from description
            extracted_code = self._extract_code_from_description(item.get('description', ''))
            if extracted_code:
                self._safe_print(f"    Extracted code: {extracted_code}")

                # Step 1a: Exact code match
                matched_product = self._exact_code_match(extracted_code, search_df)
                if matched_product is not None:
                    self._safe_print(f"    ✓ Exact code match found")
                    self._apply_product_match(enriched_item, matched_product, 'exact_code')
                    enriched_items.append(enriched_item)
                    continue

            # Step 2: Fuzzy name match (on filtered dataframe)
            self._safe_print(f"    Trying fuzzy name match...")
            matched_product = self._fuzzy_name_match(
                item.get('description', ''),
                search_df
            )

            if matched_product is not None:
                self._safe_print(f"    ✓ Fuzzy name match found (score: {matched_product.get('match_score', 0)})")
                self._apply_product_match(enriched_item, matched_product, 'fuzzy_name')
            else:
                self._safe_print(f"    ✗ No match found")
                # Keep original item, CatalogNo will be empty
                enriched_item['product_match'] = {'type': 'no_match', 'score': 0}

            enriched_items.append(enriched_item)

        # Count successful matches
        successful = sum(1 for item in enriched_items if item.get('catalog_no'))
        self._safe_print(f"\nPhase 5: Successfully enriched {successful}/{len(items)} items")

        return enriched_items

    def _extract_code_from_description(self, description: str) -> Optional[str]:
        """Find 6+ digit product codes in description."""
        if not description:
            return None

        # Look for sequences of 6 or more digits
        matches = re.findall(r'\b(\d{6,})\b', description)

        for match in matches:
            # Check if it's not a price (prices usually have decimals or are smaller)
            if len(match) >= 6:
                # Check if it looks like a product code, not a price
                # Product codes are often 6-13 digits, no decimal point
                if '.' not in match and not re.match(r'^\d{1,3}(,\d{3})*$', match):
                    return match

        return None

    def _exact_code_match(self, code: str, search_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Match extracted code against קוד פריט column."""
        if not code or search_df is None or len(search_df) == 0:
            return None

        # Exact match on קוד פריט using actual column name
        product_code_col = self.product_code_col

        matches = search_df[search_df[product_code_col] == code]

        if len(matches) > 0:
            product = matches.iloc[0]
            return {
                'product_code': str(product[product_code_col]),
                'canonical_description': str(product[self.description_col]),
                'supplier_name': str(product.get(self.column_mapping.get('שם ספק ראשי', ''), '')),
                'match_score': 100.0
            }

        return None

    def _fuzzy_name_match(
        self,
        description: str,
        search_df: pd.DataFrame
    ) -> Optional[Dict[str, Any]]:
        """
        Fuzzy match description against תאור פריט column.

        FIXED: Uses pre-filtered dataframe (by vendor).
        """
        if not description or search_df is None or len(search_df) == 0:
            return None

        normalized_desc = self._normalize_hebrew(description)
        if not normalized_desc:
            return None

        # Get list of normalized product names
        product_names = search_df['תאור מנורמל'].tolist()
        product_indices = search_df.index.tolist()

        # Find best match using fuzzywuzzy
        best_match = None
        best_score = 0
        best_idx = -1

        for idx, product_name in zip(product_indices, product_names):
            if not product_name:
                continue

            score = fuzz.token_sort_ratio(normalized_desc, product_name)
            if score > best_score and score >= self.fuzzy_threshold:
                best_score = score
                best_idx = idx

        if best_idx == -1:
            return None

        product = search_df.loc[best_idx]

        return {
            'product_code': str(product[self.product_code_col]),
            'canonical_description': str(product[self.description_col]),
            'supplier_name': str(product.get(self.column_mapping.get('שם ספק ראשי', ''), '')),
            'match_score': best_score
        }

    def _normalize_hebrew(self, text: str) -> str:
        """Normalize Hebrew text for matching."""
        if not isinstance(text, str):
            return ""

        # Remove non-Hebrew letters/digits/spaces
        text = re.sub(r'[^\u0590-\u05FF\d\s]', ' ', text)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text.lower()

    def _apply_product_match(
        self,
        item: Dict[str, Any],
        product_match: Dict[str, Any],
        match_type: str
    ):
        """
        Apply product match to item.

        Updates:
        - description with canonical description
        - catalog_no with product code (from קוד פריט)
        - Adds match metadata
        """
        item['description'] = product_match.get('canonical_description', item.get('description', ''))
        item['catalog_no'] = product_match.get('product_code', '')
        item['product_match'] = {
            'type': match_type,
            'score': product_match.get('match_score', 100.0),
            'supplier_name': product_match.get('supplier_name', '')
        }


# Test the fixed implementation
def test_fixed_phase5():
    """Test the fixed Phase 5 implementation."""
    print("\n" + "="*60)
    print("TESTING FIXED PHASE 5 IMPLEMENTATION")
    print("="*60)

    phase5 = Phase5ProductList()

    if not phase5.load_product_list():
        print("❌ Failed to load product list")
        return

    print(f"✅ Loaded {len(phase5.product_df)} products")
    print(f"✅ Loaded merchants mapping: {len(phase5.merchants_mapping)} vendors")

    # Test vendor filtering
    vendor_name = "גלוברנדס"
    filtered = phase5._filter_by_vendor(vendor_name)
    print(f"\nVendor filtering test for '{vendor_name}':")
    print(f"  Original: {len(phase5.product_df)} products")
    print(f"  Filtered: {len(filtered)} products")

    # Test with sample items
    sample_items = [
        {
            "description": "קוטג 5% 250 גרם",
            "barcode": "7290011194246",
            "unit_price": 4.97,
            "quantity": 1.0
        }
    ]

    print(f"\nTesting enrichment with {len(sample_items)} sample items:")
    results = phase5.enrich_items(sample_items, vendor_name)

    for i, item in enumerate(results):
        print(f"\nItem {i+1} result:")
        print(f"  Description: {item.get('description', 'N/A')[:40]}...")
        print(f"  CatalogNo: {item.get('catalog_no', 'EMPTY')}")
        match_info = item.get('product_match', {})
        print(f"  Match type: {match_info.get('type', 'NONE')}")
        print(f"  Match score: {match_info.get('score', 'N/A')}")

    print("\n" + "="*60)
    print("FIXED IMPLEMENTATION TEST COMPLETE")


if __name__ == "__main__":
    test_fixed_phase5()