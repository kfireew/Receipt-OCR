"""
Mindee output formatter - converts to GDocument format.
"""
import os
import json
import re
from typing import Dict, Any, List
from utils.format_converter import mindee_to_abbey


OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")


class MindeeFormatter:
    """Formatter for Mindee output."""

    def __init__(self):
        self.skip_keywords = ['ךיראת', 'הלבק', 'םולשת', 'החנה', 'מ"עמ', 'כהס']

    def format(self, items: List[Dict], vendor: str = "", date: str = "",
               receipt_name: str = None) -> Dict[str, Any]:
        """Convert items to GDocument format."""
        return mindee_to_abbey(items, receipt_name or "Receipt", vendor=vendor, date=date)

    def save_to_output(self, gdoc: Dict, receipt_name: str):
        """Save output to output/ folder."""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        json_path = os.path.join(OUTPUT_DIR, f"{receipt_name}.JSON")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(gdoc, f, indent=2, ensure_ascii=False)

    def generate_receipt_name(self, vendor: str, date: str, image_path: str) -> str:
        """Generate receipt filename from vendor/date or filename."""
        if vendor and date:
            parts = date.split('.')
            if len(parts) == 3:
                date_dash = f"{parts[0]}-{parts[1]}-{parts[2][-2:]}"
            else:
                date_dash = date.replace('.', '-')
            return f"{vendor}_{date}_{vendor} {date_dash}"
        return self._normalize_filename(image_path)

    def _normalize_filename(self, image_path: str) -> str:
        """Normalize filename to standard format."""
        filename = os.path.splitext(os.path.basename(image_path))[0]
        filename = re.sub(r'_page-\d+$', '', filename)

        patterns = [
            (r'^(\w+)_(\d{2}\.\d{2}\.\d{4})_(\w+)\s+(\d{2}-\d{2}-\d{2})$', 0),
            (r'^(\w+)\s+(\d{2}\.\d{2}\.\d{4})_(\w+)\s+(\d{2}-\d{2}-\d{2})$', 1),
            (r'^(\w+)_(\d{2}\.\d{2}\.\d{4})_(\w+)_(\d{2}-\d{2}-\d{2})$', 2),
        ]

        for pattern, mode in patterns:
            match = re.match(pattern, filename)
            if match:
                if mode == 0:
                    return filename
                elif mode == 1:
                    return f"{match.group(1)}_{match.group(2)}_{match.group(3)} {match.group(4)}"
                elif mode == 2:
                    return f"{match.group(1)}_{match.group(2)}_{match.group(3)} {match.group(4)}"

        return filename.replace(' ', '_')