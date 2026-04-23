"""
OBSOLETE - NOT USED BY MAIN PIPELINE
=====================================
PHASE 5: PRODUCT LIST INTEGRATION - FINAL FIXED VERSION

FIXED ISSUES:
1. Code extraction: Ignore 1-digit numbers (percentages)
2. Merchant filtering: Search for Hebrew in supplier column
3. Better code validation
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
    Phase 5: Product list integration - FINAL FIXED VERSION
    """

    def __init__(self, excel_path: str = None):
        self.excel_path = excel_path or "C:/Users/Kfir Ezer/Downloads/prices_rimon_03-02-25.xlsx"
        self.product_df = None
        self.loaded = False
        self.fuzzy_threshold = 70
        self.merchants_mapping = self._load_merchants_mapping()
        self.column_mapping = {}
        self.product_code_col = None
        self.description_col = None
        self.supplier_name_col = None

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

            required = ['קוד פריט', 'תאור פריט', 'שם ספק ראשי']
            missing = [col for col in required if col not in self.column_mapping]

            if missing:
                self._print(f"Phase 5: Missing columns: {missing}")
                return False

            self.product_code_col = self.column_mapping['קוד פריט']
            self.description_col = self.column_mapping['תאור פריט']
            self.supplier_name_col = self.column_mapping['שם ספק ראשי']

            self._clean_product_data()
            self.loaded = True
            self._print(f"Phase 5: Loaded {len(self.product_df)} products")
            return True

        except Exception as e:
            self._print(f"Phase 5: Failed to load: {e}")
            return False

    def _clean_product_data(self):
        self.product_df[self.product_code_col] = self.product_df[self.product_code_col].astype(str)
        self.product_df[self.description_col] = self.product_df[self.description_col].fillna('').astype(str)
        self.product_df[self.supplier_name_col] = self.product_df[self.supplier_name_col].fillna('').astype(str)
        self.product_df['תאור מנורמל'] = self.product_df[self.description_col].apply(self._normalize_hebrew)
        self.product_df = self.product_df[self.product_df[self.product_code_col].str.strip() != '']

    def _normalize_hebrew(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        text = re.sub(r'[^\u0590-\u05FF\d\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text.lower()

    def _get_merchant_keywords(self, hebrew_vendor: str) -> List[str]:
        """Get all keywords for a merchant (English + Hebrew)."""
        if not hebrew_vendor or not self.merchants_mapping:
            return []

        normalized_vendor = self._normalize_hebrew(hebrew_vendor)
        keywords = []

        for english_name, hebrew_keywords in self.merchants_mapping.items():
            # Check if vendor matches any Hebrew keyword
            for keyword in hebrew_keywords:
                if normalized_vendor in self._normalize_hebrew(keyword):
                    # Add ALL keywords for this merchant
                    keywords.extend(hebrew_keywords)
                    keywords.append(english_name)
                    return list(set(keywords))  # Remove duplicates

        return []

    def _filter_by_merchant(self, hebrew_vendor: str) -> Optional[pd.DataFrame]:
        """Filter products by merchant using ALL keywords."""
        if not hebrew_vendor or not self.loaded:
            return None

        keywords = self._get_merchant_keywords(hebrew_vendor)
        if not keywords:
            self._print(f"Phase 5: No keywords found for vendor '{hebrew_vendor}'")
            return None

        # Search for ANY keyword in supplier column
        mask = pd.Series(False, index=self.product_df.index)

        for keyword in keywords:
            # Search for Hebrew or English keywords
            keyword_mask = self.product_df[self.supplier_name_col].str.contains(
                keyword, case=False, na=False, regex=False
            )
            mask = mask | keyword_mask

        filtered_df = self.product_df[mask]

        if len(filtered_df) > 0:
            self._print(f"Phase 5: Filtered to {len(filtered_df)} products for merchant '{hebrew_vendor}'")
            unique_suppliers = filtered_df[self.supplier_name_col].unique()[:3]
            self._print(f"  Suppliers: {list(unique_suppliers)}")
            return filtered_df

        self._print(f"Phase 5: No products found for merchant '{hebrew_vendor}'")
        return None

    def _extract_product_code(self, description: str) -> Optional[str]:
        """
        Extract 1-8 digit product code from description.
        FIXED: Ignore 1-digit numbers (likely percentages).
        """
        if not description:
            return None

        # Find all number sequences
        numbers = re.findall(r'\b(\d+)\b', description)

        for num in numbers:
            # Check length 2-8 (ignore 1-digit percentages)
            if not (2 <= len(num) <= 8):
                continue

            # Check if it's a barcode (starts with 729 and 12-13 digits)
            if len(num) >= 12 and num.startswith('729'):
                continue

            # Check if it looks like a year (1900-2100)
            if len(num) == 4 and 1900 <= int(num) <= 2100:
                continue

            # Check if it's likely a percentage followed by unit
            # e.g., "5% 250 גרם" - "5" is percentage, not product code
            pattern = re.escape(num) + r'%\s*\d+'
            if re.search(pattern, description):
                continue

            return num

        return None

    def _exact_code_match(self, code: str, search_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
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

            # Step 1: Extract and match product code (FIXED: 2-8 digits)
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

        successful = sum(1 for item in enriched_items if item.get('catalog_no'))
        self._print(f"\nPhase 5: Successfully enriched {successful}/{len(items)} items")

        return enriched_items

    def _apply_match(self, item: Dict[str, Any], match: Dict[str, Any], match_type: str):
        item['description'] = match['canonical_description']
        item['catalog_no'] = match['product_code']
        item['product_match'] = {
            'type': match_type,
            'score': match['match_score'],
            'supplier_name': match['supplier_name']
        }


# Quick test
def quick_test():
    print("PHASE 5 (FIVE) MACHINE - FINAL VERSION QUICK TEST")
    print("="*60)

    phase5 = Phase5ProductList()
    phase5.load_product_list()

    # Test code extraction (FIXED)
    tests = [
        ("קוטג 5% 250 גרם", None),  # Should ignore "5" (percentage)
        ("חלב 3% 1 ליטר", None),    # Should ignore "3" (percentage)
        ("פריט 12345", "12345"),     # Should extract
        ("גבינה 500 גרם", None),     # No code
    ]

    print("\nCode extraction (FIXED):")
    for desc, expected in tests:
        code = phase5._extract_product_code(desc)
        status = "✅" if code == expected else "❌"
        print(f"{status} '{desc}' → '{code}'")

    # Test merchant filtering
    vendor = "גלוברנדס"
    filtered = phase5._filter_by_merchant(vendor)
    if filtered is not None:
        print(f"\nMerchant filtering: {len(filtered)} products for '{vendor}'")
    else:
        print(f"\nNo filtering for '{vendor}'")

    # Test enrichment
    items = [
        {"description": "קוטג 5% 250 גרם", "unit_price": 4.97},
        {"description": "חלב 3% 1 ליטר", "unit_price": 6.50},
    ]

    print(f"\nEnrichment test with {len(items)} items:")
    results = phase5.enrich_items(items, vendor)

    for i, item in enumerate(results):
        print(f"Item {i+1}: CatalogNo='{item.get('catalog_no', '')}', match='{item.get('product_match', {}).get('type', 'none')}'")


if __name__ == "__main__":
    quick_test()