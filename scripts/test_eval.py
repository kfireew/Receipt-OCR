import json
import time
from pathlib import Path

def load_gt(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    doc = data.get("GDocument", {})
    gt_data = {
        "invoice_no": None,
        "date": None,
        "total": None,
        "items": []
    }
    
    for field in doc.get("fields", []):
        name = field.get("name")
        val = field.get("value")
        if name == "InvoiceNo" and val:
            gt_data["invoice_no"] = val
        elif name == "Date" and val:
            gt_data["date"] = val
        elif name == "Total" and val:
            try:
                gt_data["total"] = float(val)
            except:
                pass

    for group in doc.get("groups", []):
        if group.get("name") == "Table":
            for row in group.get("groups", []):
                item = {}
                for field in row.get("fields", []):
                    name = field.get("name")
                    val = field.get("value")
                    if val is None or val == "": continue
                    if name == "Price": item["price"] = float(val)
                    elif name == "Quantity": item["quantity"] = float(val)
                    elif name == "CatalogNo": item["catalog_no"] = val
                    elif name == "LineTotal": item["line_total"] = float(val)
                if item:
                    gt_data["items"].append(item)
    return gt_data

def load_pred(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

if __name__ == "__main__":
    gt = load_gt("sample_images/Avikam_10.03.2025_Avikam 11-03-25.JSON")
    print("GT:", json.dumps(gt, indent=2, ensure_ascii=False))
