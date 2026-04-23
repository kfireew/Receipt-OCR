"""
OBSOLETE - NOT USED BY MAIN PIPELINE
=====================================
PHASE 5: PRODUCT LIST INTEGRATION - CORRECTED VERSION

EXACT implementation per user specification:
1. קוד פריט → CatalogNo (most important)
2. ברקוד → IGNORE completely (empty column)
3. תאור פריט → Canonical Hebrew name (replace OCR)
4. שם ספק ראשי → Filter by merchant (from merchants_mapping.json)
5. Matching order: Code exact → Fuzzy name (with vendor filtering)
"""

import re
import os
import pandas as pd
import sys
import json
from typing import List, Dict, Any, Optional, Tuple
from rapidfuzz import fuzz


class Phase5ProductList:
    """
    Phase 5: Product list integration - CORRECTED VERSION
    """

    def __init__(self, excel_path: str = None):
        self.excel_path = excel_path or "C:/Users/Kfir Ezer/Downloads/prices_rimon_03-02-25.xlsx"
        self.product_df = None
        self.loaded = False
        self.fuzzy_threshold = 70

        # Load merchants mapping
        self.merchants_mapping = self._load_merchants_mapping()

        # Column mapping (handle trailing spaces)
        self.column_mapping = {}
        self.product_code_col = None
        self.description_col = None
        self.supplier_name_col = None

    def _load_merchants_mapping(self) -> Dict[str, List[str]]:
        """Load merchants_mapping.json."""
        mapping_path = "merchants_mapping.json"
        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self._print(f"Phase 5: Warning - Could not load {mapping_path}: {e}")
                return {}
        return {}

    def _print(self, message: str):
        """Safe print with Hebrew."""
        try:
            print(message)
        except UnicodeEncodeError:
            print(message.encode('utf-8', 'ignore').decode('utf-8', 'ignore'))

    def load_product_list(self) -> bool:
        """Load product list from Excel."""
        if not os.path.exists(self.excel_path):
            self._print(f"Phase 5: Product list not found at {self.excel_path}")
            return False

        try:
            self._print(f"Phase 5: Loading product list from {self.excel_path}")
            self.product_df = pd.read_excel(self.excel_path, engine='openpyxl')

            # Map stripped column names
            self.column_mapping = {str(col).strip(): col for col in self.product_df.columns}

            # Required columns
            required = ['קוד פריט', 'תאור פריט', 'שם ספק ראשי']
            missing = [col for col in required if col not in self.column_mapping]

            if missing:
                self._print(f"Phase 5: Missing columns: {missing}")
                return False

            # Store column references
            self.product_code_col = self.column_mapping['קוד פריט']
            self.description_col = self.column_mapping['תאור פריט']
            self.supplier_name_col = self.column_mapping['שם ספק ראשי']

            # Clean data
            self._clean_product_data()

            self.loaded = True
            self._print(f"Phase 5: Loaded {len(self.product_df)} products")
            return True

        except Exception as e:
            self._print(f"Phase 5: Failed to load: {e}")
            return False

    def _clean_product_data(self):
        """Clean product data."""
        # Ensure string columns
        self.product_df[self.product_code_col] = self.product_df[self.product_code_col].astype(str)
        self.product_df[self.description_col] = self.product_df[self.description_col].fillna('').astype(str)
        self.product_df[self.supplier_name_col] = self.product_df[self.supplier_name_col].fillna('').astype(str)

        # Create normalized description for matching
        self.product_df['תאור מנורמל'] = self.product_df[self.description_col].apply(self._normalize_hebrew)

        # Filter empty product codes
        self.product_df = self.product_df[self.product_df[self.product_code_col].str.strip() != '']

    def _normalize_hebrew(self, text: str) -> str:
        """Normalize Hebrew text."""
        if not isinstance(text, str):
            return ""
        # Keep Hebrew, digits, spaces
        text = re.sub(r'[^\u0590-\u05FF\d\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text.lower()

    def _get_english_merchant_name(self, hebrew_vendor: str) -> Optional[str]:
        """Get English merchant name from merchants_mapping.json."""
        if not hebrew_vendor or not self.merchants_mapping:
            return None

        normalized_vendor = self._normalize_hebrew(hebrew_vendor)

        # Look for merchant in mapping
        for english_name, hebrew_keywords in self.merchants_mapping.items():
            for keyword in hebrew_keywords:
                if normalized_vendor in self._normalize_hebrew(keyword):
                    return english_name

        return None

    def _filter_by_merchant(self, hebrew_vendor: str) -> Optional[pd.DataFrame]:
        """
        Filter products by merchant.

        Steps:
        1. Get English merchant name from merchants_mapping.json
        2. Filter products where supplier_name_col contains English name
        """
        if not hebrew_vendor or not self.loaded:
            return None

        english_name = self._get_english_merchant_name(hebrew_vendor)
        if not english_name:
            self._print(f"Phase 5: No English name found for vendor '{hebrew_vendor}'")
            return None

        # Filter products by supplier name
        mask = self.product_df[self.supplier_name_col].str.contains(english_name, case=False, na=False)
        filtered_df = self.product_df[mask]

        if len(filtered_df) > 0:
            self._print(f"Phase 5: Filtered to {len(filtered_df)} products for merchant '{english_name}'")
            return filtered_df

        self._print(f"Phase 5: No products found for merchant '{english_name}'")
        return None

    def _extract_product_code(self, description: str) -> Optional[str]:
        """
        Extract 1-8 digit product code from description.

        Rules:
        - 1-8 digits
        - Not a decimal (no .)
        - Not a price (not like 123.45)
        - Not a barcode (not like 7290011194246)
        """
        if not description:
            return None

        # Find all number sequences
        numbers = re.findall(r'\b(\d+)\b', description)

        for num in numbers:
            # Check length 1-8
            if not (1 <= len(num) <= 8):
                continue

            # Check if it's a barcode (starts with 729 and 12-13 digits)
            if len(num) >= 12 and num.startswith('729'):
                continue

            # Check if it looks like a price (would have . in original)
            if '.' in description:
                # Check if this number is near a decimal point
                pattern = re.escape(num) + r'\.\d{2}'
                if re.search(pattern, description):
                    continue

            return num

        return None

    def _exact_code_match(self, code: str, search_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Exact match code against קוד פריט."""
        if not code or search_df is None or len(search_df) == 0:
            return None

        matches = search_df[search_df[self.product_code_col] == code]

        if len(matches) > 0:
            product = matches.iloc[0]
            return {
                'product_code': str(product[self.product_code_col]),
                'canonical_description': str(product[self.description_col]),
                'supplier_name': str(product[self.supplier_name_col]),
                'match_score': 100.0
            }

        return None

    def _fuzzy_name_match(self, description: str, search_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Fuzzy match description against תאור פריט."""
        if not description or search_df is None or len(search_df) == 0:
            return None

        normalized_desc = self._normalize_hebrew(description)
        if not normalized_desc:
            return None

        best_score = 0
        best_product = None

        for idx, row in search_df.iterrows():
            product_desc = row[self.description_col]
            normalized_product = self._normalize_hebrew(product_desc)

            score = fuzz.token_sort_ratio(normalized_desc, normalized_product)

            if score > best_score and score >= self.fuzzy_threshold:
                best_score = score
                best_product = row

        if best_product is not None:
            return {
                'product_code': str(best_product[self.product_code_col]),
                'canonical_description': str(best_product[self.description_col]),
                'supplier_name': str(best_product[self.supplier_name_col]),
                'match_score': best_score
            }

        return None

    def enrich_items(self, items: List[Dict[str, Any]], vendor_name: str = None) -> List[Dict[str, Any]]:
        """
        Main entry point: Enrich items with product list data.

        Matching order:
        1. Code exact match
        2. Fuzzy name match (filtered by merchant if vendor known)
        3. Fuzzy name match (global search if filtered fails)
        """
        if not self.loaded:
            if not self.load_product_list():
                self._print("Phase 5: Cannot enrich items, product list not loaded")
                return items

        self._print(f"Phase 5: Enriching {len(items)} items (vendor: {vendor_name or 'unknown'})")

        enriched_items = []

        # Get filtered products if vendor known
        filtered_df = None
        if vendor_name:
            filtered_df = self._filter_by_merchant(vendor_name)

        for i, item in enumerate(items):
            self._print(f"\n  Item {i+1}: {item.get('description', 'N/A')[:50]}...")

            enriched_item = item.copy()
            description = item.get('description', '')

            # Step 1: Extract and match product code
            extracted_code = self._extract_product_code(description)
            if extracted_code:
                self._print(f"    Extracted code: {extracted_code}")

                # Try exact code match in filtered products first
                if filtered_df is not None:
                    match = self._exact_code_match(extracted_code, filtered_df)
                    if match:
                        self._print(f"    ✓ Exact code match in merchant products")
                        self._apply_match(enriched_item, match, 'exact_code')
                        enriched_items.append(enriched_item)
                        continue

                # Try exact code match in all products
                match = self._exact_code_match(extracted_code, self.product_df)
                if match:
                    self._print(f"    ✓ Exact code match in global search")
                    self._apply_match(enriched_item, match, 'exact_code')
                    enriched_items.append(enriched_item)
                    continue

            # Step 2: Fuzzy name match
            self._print(f"    Trying fuzzy name match...")

            # Try filtered products first (if vendor known)
            match = None
            if filtered_df is not None:
                match = self._fuzzy_name_match(description, filtered_df)
                if match:
                    self._print(f"    ✓ Fuzzy match in merchant products (score: {match['match_score']:.1f})")

            # If no match in filtered, try global search
            if not match:
                match = self._fuzzy_name_match(description, self.product_df)
                if match:
                    self._print(f"    ✓ Fuzzy match in global search (score: {match['match_score']:.1f})")

            if match:
                self._apply_match(enriched_item, match, 'fuzzy_name')
            else:
                self._print(f"    ✗ No match found")
                enriched_item['product_match'] = {'type': 'no_match', 'score': 0}

            enriched_items.append(enriched_item)

        # Count successes
        successful = sum(1 for item in enriched_items if item.get('catalog_no'))
        self._print(f"\nPhase 5: Successfully enriched {successful}/{len(items)} items")

        return enriched_items

    def _apply_match(self, item: Dict[str, Any], match: Dict[str, Any], match_type: str):
        """Apply product match to item."""
        item['description'] = match['canonical_description']
        item['catalog_no'] = match['product_code']
        item['product_match'] = {
            'type': match_type,
            'score': match['match_score'],
            'supplier_name': match['supplier_name']
        }


# Test function
def test_correct_phase5():
    """Test the corrected Phase 5."""
    print("\n" + "="*60)
    print("TESTING CORRECTED PHASE 5")
    print("="*60)

    phase5 = Phase5ProductList()

    if not phase5.load_product_list():
        print("❌ Failed to load product list")
        return

    print(f"✅ Loaded {len(phase5.product_df)} products")
    print(f"✅ merchants_mapping: {len(phase5.merchants_mapping)} merchants")

    # Test merchant lookup
    test_vendors = ["גלוברנדס", "תנובה", "שטראוס"]
    for vendor in test_vendors:
        english = phase5._get_english_merchant_name(vendor)
        print(f"  '{vendor}' → '{english}'")

    # Test filtering
    vendor = "גלוברנדס"
    filtered = phase5._filter_by_merchant(vendor)
    if filtered is not None:
        print(f"\n✅ Filtered '{vendor}': {len(filtered)} products")
        print(f"   Sample suppliers: {filtered[phase5.supplier_name_col].unique()[:3]}")
    else:
        print(f"\n❌ No filtering for '{vendor}'")

    # Test code extraction
    test_descriptions = [
        "קוטג 5% 250 גרם 12345",
        "חלב 3% 1 ליטר קוד 789",
        "גבינה 9% 7290011194246",
        "משהו עם מחיר 12.99"
    ]

    print("\nCode extraction tests:")
    for desc in test_descriptions:
        code = phase5._extract_product_code(desc)
        print(f"  '{desc[:20]}...' → '{code}'")

    # Test enrichment
    sample_items = [
        {"description": "קוטג 5% 250 גרם", "unit_price": 4.97},
        {"description": "חלב 3% 1 ליטר", "unit_price": 6.50}
    ]

    print(f"\nTesting enrichment with vendor '{vendor}':")
    results = phase5.enrich_items(sample_items, vendor)

    for i, item in enumerate(results):
        print(f"\nItem {i+1}:")
        print(f"  Original: {sample_items[i]['description']}")
        print(f"  Result: {item.get('description', 'N/A')[:40]}...")
        print(f"  CatalogNo: {item.get('catalog_no', 'EMPTY')}")
        print(f"  Match: {item.get('product_match', {}).get('type', 'NONE')}")
        print(f"  Score: {item.get('product_match', {}).get('score', 0)}")

    print("\n" + "="*60)
    print("CORRECTED IMPLEMENTATION READY")


if __name__ == "__main__":
    test_correct_phase5()