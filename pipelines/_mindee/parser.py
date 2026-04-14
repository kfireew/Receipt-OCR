"""
Mindee response parser - extracts fields and items from API response.
"""
from typing import List, Dict, Any
from collections import defaultdict
import re


class MindeeParser:
    """Parser for Mindee API responses."""

    def parse_fields(self, fields) -> Dict[str, Any]:
        """Parse fields dict from Mindee response."""
        if isinstance(fields, list):
            fields_dict = {}
            for f in fields:
                if hasattr(f, 'name') and hasattr(f, 'value'):
                    fields_dict[f.name] = f
            return fields_dict
        return fields

    def extract_header(self, fields: Dict[str, Any]) -> Dict[str, str]:
        """Extract vendor, date, invoice_no, total from fields."""
        vendor_field = fields.get('supplier_name') or fields.get('merchant_name')
        date_field = fields.get('date')
        invoice_field = fields.get('invoice_number')
        total_field = fields.get('total_amount')

        return {
            'vendor': vendor_field.value if vendor_field and vendor_field.value else "",
            'date': date_field.value if date_field and date_field.value else "",
            'invoice_no': invoice_field.value if invoice_field and invoice_field.value else "",
            'total': total_field.value if total_field and total_field.value else 0.0,
        }

    def extract_items(self, fields: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract line items from fields."""
        line_items_field = fields.get('line_items')
        if line_items_field is None:
            return []
        elif hasattr(line_items_field, 'items'):
            items = line_items_field.items
        elif isinstance(line_items_field, list):
            items = line_items_field
        else:
            return []

        return self._items_to_dicts(items)

    def parse_raw_ocr(self, ocr_response) -> List[Dict[str, Any]]:
        """Parse raw OCR to extract items using X-position column detection."""
        words = self._extract_words(ocr_response)
        if not words:
            return []

        rows = self._group_by_y(words)
        return self._parse_rows(rows)

    def _items_to_dicts(self, items: list) -> list:
        """Convert Mindee items to dict format."""
        result = []
        for item in items:
            if isinstance(item, dict):
                result.append({
                    'description': item.get('description', item.get('Description', '')),
                    'quantity': float(item.get('quantity', item.get('Quantity', 1))),
                    'unit_price': float(item.get('unit_price', item.get('UnitPrice', 0))),
                    'line_total': float(item.get('line_total', item.get('total', item.get('total_price', 0)))),
                })
            elif hasattr(item, 'fields'):
                item_fields = item.fields
                desc = item_fields.get('description')
                qty = item_fields.get('quantity')
                unit_price = item_fields.get('unit_price')
                total_price = item_fields.get('total_price')
                result.append({
                    'description': desc.value if desc and desc.value else '',
                    'quantity': float(qty.value) if qty and qty.value else 1.0,
                    'unit_price': float(unit_price.value) if unit_price and unit_price.value else 0.0,
                    'line_total': float(total_price.value) if total_price and total_price.value else 0.0,
                })
        return result

    def _extract_words(self, ocr_response) -> list:
        """Extract words with positions from OCR response."""
        words = []
        if hasattr(ocr_response, 'pages'):
            for page in ocr_response.pages:
                if hasattr(page, 'words'):
                    for word in page.words:
                        if hasattr(word, 'polygon') and word.polygon:
                            polygon = word.polygon
                            words.append({
                                'content': word.content if hasattr(word, 'content') else str(word),
                                'x': polygon[0][0],
                                'y': polygon[0][1],
                            })
        return words

    def _group_by_y(self, words: list) -> defaultdict:
        """Group words by Y position (rows)."""
        rows = defaultdict(list)
        for w in words:
            rows[w['y']].append({'x': w['x'], 'content': w['content']})
        return rows

    def _parse_rows(self, rows: defaultdict) -> list:
        """Parse rows to extract items."""
        skip_keywords = ['ךיראת', 'הלבק', 'םולשת', 'החנה', 'מ"עמ', 'כהס']
        items = []

        for y in sorted(rows.keys()):
            row_words = rows[y]
            row_text = ' '.join([w['content'] for w in row_words])

            if any(skip in row_text for skip in skip_keywords):
                continue
            if len(row_text) < 3:
                continue

            numbers = self._extract_numbers(row_words)
            if len(numbers) >= 2:
                item = self._parse_item_row(row_words, numbers)
                if item:
                    items.append(item)

        return items

    def _extract_numbers(self, row_words: list) -> list:
        """Extract numbers with X positions from row words."""
        numbers = []
        for w in row_words:
            nums = re.findall(r'[\d,]+\.?\d*', w['content'])
            for n in nums:
                try:
                    val = float(n.replace(',', ''))
                    if 0 < val < 1000000:
                        numbers.append((w['x'], val))
                except ValueError:
                    pass
        return sorted(numbers, key=lambda x: x[0])

    def _parse_item_row(self, row_words: list, numbers: list) -> Dict[str, Any]:
        """Parse a row of words into an item."""
        total = numbers[-1][1]
        unit_price = numbers[-2][1]
        qty = round(total / unit_price) if unit_price > 0 else 1

        desc_parts = []
        for w in row_words:
            if w['x'] >= 0.4 and not re.match(r'^[\d,\.]+$', w['content']):
                desc_parts.append(w['content'])

        desc = ' '.join(desc_parts[:5])
        if not desc or len(desc) <= 1:
            return None

        return {
            'description': desc[:50],
            'quantity': qty,
            'unit_price': round(unit_price, 2),
            'line_total': round(total, 2),
        }