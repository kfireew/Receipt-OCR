from __future__ import annotations

from dataclasses import dataclass, asdict
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
        if self.invoice_no and self.invoice_no.value:
            fields.append({"name": "InvoiceNo", "value": self.invoice_no.value})
        if self.date and self.date.value:
            try:
                dt = datetime.fromisoformat(self.date.value)
                fields.append({"name": "Date", "value": dt.strftime(r"%d.%m.%Y")})
            except:
                fields.append({"name": "Date", "value": self.date.value})
        if self.total and self.total.value is not None:
            fields.append({"name": "Total", "value": f"{self.total.value:.2f}"})
        if self.merchant and self.merchant.value:
            fields.append({"name": "VendorName", "value": self.merchant.value})
            fields.append({"name": "VendorNameS", "value": self.merchant.value})

        table_groups = []
        for it in self.items:
            item_fields = []
            if it.unit_price is not None: item_fields.append({"name": "Price", "value": f"{it.unit_price:.2f}"})
            if it.quantity is not None: item_fields.append({"name": "Quantity", "value": f"{it.quantity:.2f}"})
            if it.catalog_no: item_fields.append({"name": "CatalogNo", "value": it.catalog_no})
            if it.line_total is not None: item_fields.append({"name": "LineTotal", "value": f"{it.line_total:.2f}"})
            table_groups.append({"name": "Table", "fields": item_fields, "groups": []})

        return {"GDocument": {"fields": fields, "groups": [{"name": "Table", "groups": table_groups, "fields": []}]}}
