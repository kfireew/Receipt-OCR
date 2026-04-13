from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from stages.grouping.line_assembler import RawLine

@dataclass
class LineItem:
    description: str
    quantity: float
    unit_price: float
    line_total: float
    confidence: float
    line_index: int
    catalog_no: Optional[str] = None

@dataclass
class ExtractedItem:
    """A single table row extracted from ReceiptTable structure."""
    description: str
    quantity: float
    unit_price: float
    line_total: float
    catalog_no: Optional[str] = None
    column_mapping: Dict[str, int] = field(default_factory=dict)
    confidence: float = 0.0
    line_index: int = 0

@dataclass
class ParsedAmountField:
    value: Optional[float]
    raw_text: Optional[str]
    confidence: Optional[float]
    line_index: Optional[int]

@dataclass
class ParsedStringField:
    value: Optional[str]
    confidence: Optional[float]
    line_index: Optional[int]

@dataclass
class ParsedReceipt:
    merchant: ParsedStringField
    date: ParsedStringField
    subtotal: ParsedAmountField
    vat: ParsedAmountField
    total: ParsedAmountField
    currency: ParsedStringField
    items: List[LineItem]
    raw_lines: List[RawLine]
    invoice_no: Optional[ParsedStringField] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "merchant": asdict(self.merchant),
            "date": asdict(self.date),
            "subtotal": asdict(self.subtotal),
            "vat": asdict(self.vat),
            "total": asdict(self.total),
            "currency": asdict(self.currency),
            "invoice_no": asdict(self.invoice_no) if self.invoice_no else None,
            "items": [asdict(it) for it in self.items],
            "raw_lines": [asdict(ln) for ln in self.raw_lines],
        }

    def to_gdocument_dict(self) -> Dict[str, Any]:
        fields = []

        # indices 0, 1: InvoiceNo
        invoice_val = self.invoice_no.value if (self.invoice_no and self.invoice_no.value) else ""
        fields.append({"name": "InvoiceNo", "value": invoice_val})
        fields.append({"name": "InvoiceNo", "value": invoice_val})

        # indices 2, 3: VendorNameS
        merchant_val = self.merchant.value if (self.merchant and self.merchant.value) else ""
        fields.append({"name": "VendorNameS", "value": merchant_val})
        fields.append({"name": "VendorNameS", "value": merchant_val})

        # indices 4, 5: Date
        date_val = ""
        if self.date and self.date.value:
            try:
                dt = datetime.fromisoformat(self.date.value)
                date_val = dt.strftime(r"%d.%m.%Y")
            except:
                date_val = self.date.value
        fields.append({"name": "Date", "value": date_val})
        fields.append({"name": "Date", "value": date_val})

        # indices 6, 7: Total
        total_val = f"{self.total.value:.2f}" if (self.total and self.total.value is not None) else ""
        fields.append({"name": "Total", "value": total_val})
        fields.append({"name": "Total", "value": total_val})

        table_groups = []
        for it in self.items:
            item_fields = []

            # Price - always output
            if it.unit_price is not None:
                val = f"{it.unit_price:.2f}"
            else:
                val = "0.00"
            item_fields.append({"name": "Price", "value": val})
            fields.append({"name": "Price", "value": val})

            # Quantity - always output
            if it.quantity is not None:
                val = f"{it.quantity:.2f}"
            else:
                val = "1.00"
            item_fields.append({"name": "Quantity", "value": val})
            fields.append({"name": "Quantity", "value": val})

            # CatalogNo - always output
            val = str(it.catalog_no) if it.catalog_no else ""
            item_fields.append({"name": "CatalogNo", "value": val})
            fields.append({"name": "CatalogNo", "value": val})

            # LineTotal - always output
            if it.line_total is not None:
                val = f"{it.line_total:.2f}"
            else:
                val = "0.00"
            item_fields.append({"name": "LineTotal", "value": val})
            fields.append({"name": "LineTotal", "value": val})

            table_groups.append({"name": "Table", "fields": item_fields, "groups": []})

        return {"GDocument": {"fields": fields, "groups": [{"name": "Table", "groups": table_groups, "fields": []}]}}
