"""
OBSOLETE - NOT USED BY MAIN PIPELINE
=====================================
PHASE 5: PRODUCT LIST INTEGRATION - AND LOGIC VERSION

NEW "AND" LOGIC:
1. ALWAYS fuzzy match → Get קוד פריט for CatalogNo
2. ALSO check if 729xxxxxxxxxx exists in matched product's row
3. Include Barcode field if exists in product list
"""

import re
import os
import pandas as pd
import sys
import json
from typing import List, Dict, Any, Optional
from rapidfuzz import fuzz


class Phase5ProductList:
    """
    Phase 5: Product list integration - AND LOGIC VERSION

    NEW: Always fuzzy match for CatalogNo, optionally include barcode if exists
    """

    def __init__(self, excel_path: str = None):
        self.excel_path = excel_path or "C:/Users/Kfir Ezer/Downloads/prices_rimon_03-02-25.xlsx"
        self.product_df = None
        self.loaded = False
        self.fuzzy_threshold = 70
        self.merchants_mapping = self._load_merchants_mapping()
        self.column_mapping = {}

        # Column references
        self.product_code_col = None      # קוד פריט
        self.description_col = None       # תאור פריט
        self.supplier_name_col = None     # שם ספק ראשי
        self.barcode_col = None           # ברקוד (optional)

    def _load_merchants_mapping(self) -> Dict[str, List[str]]:
        mapping_path = "merchants_mapping.json"
        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _print(self, message: str):
        try:
            print(message)
        except UnicodeEncodeError:
            print(message.encode('utf-8', 'ignore').decode('utf-8', 'ignore'))

    def load_product_list(self) -> bool:
        if not os.path.exists(self.excel_path):
            self._print(f"Phase 5: Product list not found at {self.excel_path}")
            return False

        try:
            self._print(f"Phase 5: Loading product list from {self.excel_path}")
            self.product_df = pd.read_excel(self.excel_path, engine='openpyxl')
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

            # Check for barcode column (optional)
            if 'ברקוד' in self.column_mapping:
                self.barcode_col = self.column_mapping['ברקוד']
                self._print(f"Phase 5: Found barcode column: '{self.barcode_col}'")
            else:
                self._print(f"Phase 5: No barcode column found")

            # Clean data
            self._clean_product_data()

            self.loaded = True
            self._print(f"Phase 5: Loaded {len(self.product_df)} products")
            return True

        except Exception as e:
            self._print(f"Phase 5: Failed to load: {e}")
            return False

    def _clean_product_data(self):
        # Ensure string columns
        self.product_df[self.product_code_col] = self.product_df[self.product_code_col].astype(str)
        self.product_df[self.description_col] = self.product_df[self.description_col].fillna('').astype(str)
        self.product_df[self.supplier_name_col] = self.product_df[self.supplier_name_col].fillna('').astype(str)

        # Handle barcode column if exists
        if self.barcode_col:
            self.product_df[self.barcode_col] = self.product_df[self.barcode_col].fillna('').astype(str)

        # Create normalized description for matching
        self.product_df['תאור מנורמל'] = self.product_df[self.description_col].apply(self._normalize_hebrew)

        # Filter empty product codes
        self.product_df = self.product_df[self.product_df[self.product_code_col].str.strip() != '']

    def _normalize_hebrew(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        text = re.sub(r'[^\u0590-\u05FF\d\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text.lower()

    def _get_merchant_keywords(self, hebrew_vendor: str) -> List[str]:
        if not hebrew_vendor or not self.merchants_mapping:
            return []

        normalized_vendor = self._normalize_hebrew(hebrew_vendor)
        keywords = []

        for english_name, hebrew_keywords in self.merchants_mapping.items():
            for keyword in hebrew_keywords:
                if normalized_vendor in self._normalize_hebrew(keyword):
                    keywords.extend(hebrew_keywords)
                    keywords.append(english_name)
                    return list(set(keywords))

        return []

    def _filter_by_merchant(self, hebrew_vendor: str) -> Optional[pd.DataFrame]:
        if not hebrew_vendor or not self.loaded:
            return None

        keywords = self._get_merchant_keywords(hebrew_vendor)
        if not keywords:
            self._print(f"Phase 5: No keywords found for vendor '{hebrew_vendor}'")
            return None

        # Search for ANY keyword in supplier column
        mask = pd.Series(False, index=self.product_df.index)

        for keyword in keywords:
            keyword_mask = self.product_df[self.supplier_name_col].str.contains(
                keyword, case=False, na=False, regex=False
            )
            mask = mask | keyword_mask

        filtered_df = self.product_df[mask]

        if len(filtered_df) > 0:
            self._print(f"Phase 5: Filtered to {len(filtered_df)} products for merchant '{hebrew_vendor}'")
            return filtered_df

        self._print(f"Phase 5: No products found for merchant '{hebrew_vendor}'")
        return None

    def _extract_product_code(self, description: str) -> Optional[str]:
        if not description:
            return None

        numbers = re.findall(r'\b(\d+)\b', description)

        for num in numbers:
            if not (2 <= len(num) <= 8):
                continue
            if len(num) >= 12 and num.startswith('729'):
                continue
            if len(num) == 4 and 1900 <= int(num) <= 2100:
                continue
            pattern = re.escape(num) + r'%\s*\d+'
            if re.search(pattern, description):
                continue
            return num

        return None

    def _exact_code_match(self, code: str, search_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Exact code match with barcode extraction."""
        if not code or search_df is None or len(search_df) == 0:
            return None

        matches = search_df[search_df[self.product_code_col] == code]

        if len(matches) > 0:
            product = matches.iloc[0]
            result = {
                'product_code': str(product[self.product_code_col]),
                'canonical_description': str(product[self.description_col]),
                'supplier_name': str(product[self.supplier_name_col]),
                'match_score': 100.0
            }

            # ADDITION: Check for barcode in this product's row
            if self.barcode_col:
                barcode = str(product[self.barcode_col]).strip()
                # Check if it's a real 13-digit barcode starting with 729
                if barcode and len(barcode) == 13 and barcode.startswith('729'):
                    result['barcode'] = barcode

            return result

        return None

    def _fuzzy_name_match(self, description: str, search_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Fuzzy name match with barcode extraction."""
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
            result = {
                'product_code': str(best_product[self.product_code_col]),
                'canonical_description': str(best_product[self.description_col]),
                'supplier_name': str(best_product[self.supplier_name_col]),
                'match_score': best_score
            }

            # ADDITION: Check for barcode in this product's row
            if self.barcode_col:
                barcode = str(best_product[self.barcode_col]).strip()
                # Check if it's a real 13-digit barcode starting with 729
                if barcode and len(barcode) == 13 and barcode.startswith('729'):
                    result['barcode'] = barcode

            return result

        return None

    def enrich_items(self, items: List[Dict[str, Any]], vendor_name: str = None) -> List[Dict[str, Any]]:
        """
        NEW "AND" LOGIC:
        1. ALWAYS try to get product match (code or fuzzy)
        2. ALWAYS use קוד פריט for CatalogNo from match
        3. OPTIONALLY include barcode if exists in product row
        """
        if not self.loaded:
            if not self.load_product_list():
                self._print("Phase 5: Cannot enrich items, product list not loaded")
                return items

        self._print(f"Phase 5: Enriching {len(items)} items (vendor: {vendor_name or 'unknown'})")

        # Get filtered products if vendor known
        filtered_df = None
        if vendor_name:
            filtered_df = self._filter_by_merchant(vendor_name)

        enriched_items = []

        for i, item in enumerate(items):
            self._print(f"\n  Item {i+1}: {item.get('description', 'N/A')[:50]}...")

            enriched_item = item.copy()
            description = item.get('description', '')

            # Step 1: Try exact code match first
            extracted_code = self._extract_product_code(description)
            match = None
            match_type = 'no_match'

            if extracted_code:
                self._print(f"    Extracted code: {extracted_code}")

                # Try filtered products first
                if filtered_df is not None:
                    match = self._exact_code_match(extracted_code, filtered_df)
                    if match:
                        match_type = 'exact_code'
                        self._print(f"    ✓ Exact code match in merchant products")

                # Try global search
                if not match:
                    match = self._exact_code_match(extracted_code, self.product_df)
                    if match:
                        match_type = 'exact_code'
                        self._print(f"    ✓ Exact code match in global search")

            # Step 2: If no code match, try fuzzy name match
            if not match:
                self._print(f"    Trying fuzzy name match...")

                # Try filtered products first
                if filtered_df is not None:
                    match = self._fuzzy_name_match(description, filtered_df)
                    if match:
                        match_type = 'fuzzy_name'
                        self._print(f"    ✓ Fuzzy match in merchant products (score: {match['match_score']:.1f})")

                # Try global search
                if not match:
                    match = self._fuzzy_name_match(description, self.product_df)
                    if match:
                        match_type = 'fuzzy_name'
                        self._print(f"    ✓ Fuzzy match in global search (score: {match['match_score']:.1f})")

            # Apply match if found
            if match:
                self._apply_match(enriched_item, match, match_type)
            else:
                self._print(f"    ✗ No match found")
                enriched_item['product_match'] = {'type': 'no_match', 'score': 0}

            enriched_items.append(enriched_item)

        successful = sum(1 for item in enriched_items if item.get('catalog_no'))
        self._print(f"\nPhase 5: Successfully enriched {successful}/{len(items)} items")

        return enriched_items

    def _apply_match(self, item: Dict[str, Any], match: Dict[str, Any], match_type: str):
        """Apply product match with NEW barcode field."""
        item['description'] = match['canonical_description']
        item['catalog_no'] = match['product_code']  # ALWAYS from קוד פריט

        # NEW: Include barcode if exists in match
        if 'barcode' in match:
            item['barcode'] = match['barcode']
            self._print(f"    Included barcode: {match['barcode']}")

        item['product_match'] = {
            'type': match_type,
            'score': match['match_score'],
            'supplier_name': match['supplier_name']
        }


# Test the new AND logic
def test_and_logic():
    print("PHASE 5 (FIVE) MACHINE - TESTING AND LOGIC")
    print("="*60)

    phase5 = Phase5ProductList()
    phase5.load_product_list()

    print(f"\n✅ Loaded {len(phase5.product_df)} products")
    if phase5.barcode_col:
        print(f"✅ Barcode column: '{phase5.barcode_col}'")
    else:
        print(f"❌ No barcode column")

    # Test items
    test_items = [
        {"description": "קוטג 5% 250 גרם", "unit_price": 4.97},
        {"description": "גבינה לבנה 5% עם קרקרים", "unit_price": 8.90},
    ]

    print(f"\nTesting {len(test_items)} items with vendor 'גלוברנדס':")
    results = phase5.enrich_items(test_items, "גלוברנדס")

    print(f"\nResults (NEW AND LOGIC):")
    for i, item in enumerate(results):
        catalog_no = item.get('catalog_no', '')
        barcode = item.get('barcode', 'NO BARCODE')
        match_type = item.get('product_match', {}).get('type', 'none')

        print(f"\nItem {i+1}:")
        print(f"  CatalogNo: {catalog_no} (from קוד פריט)")
        print(f"  Barcode: {barcode} (from ברקוד if exists)")
        print(f"  Match type: {match_type}")

    print("\n" + "="*60)
    print("AND LOGIC IMPLEMENTATION READY")


if __name__ == "__main__":
    test_and_logic()