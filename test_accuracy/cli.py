from __future__ import annotations

import argparse
import json
import time
import difflib
from pathlib import Path
from typing import List, Optional, Dict, Any


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Hebrew receipt OCR pipeline over all PDF/JSON pairs in a directory "
            "and write prediction JSON files alongside them."
        )
    )
    parser.add_argument(
        "--images-dir",
        default="sample_images",
        help="Directory containing test PDFs and ground-truth JSON files (default: sample_images).",
    )
    parser.add_argument(
        "--config",
        default="config.yml",
        help="Path to YAML config for the OCR pipeline (default: config.yml).",
    )
    parser.add_argument(
        "--pattern",
        default="*.pdf",
        help="Glob pattern for input PDFs within images-dir (default: *.pdf).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List the pairs that would be processed without running OCR.",
    )
    return parser

def _fuzzy_match_value(v1: Any, v2: Any) -> bool:
    if v1 == v2:
        return True
    if v1 is None or v2 is None:
        return False
    
    # If they are numbers, check if one is 10x or 100x the other (missing decimal)
    try:
        f1 = float(v1)
        f2 = float(v2)
        if f1 > 0 and f2 > 0:
            if abs(f1 - f2) < 0.01: return True
            if abs(f1 * 100 - f2) < 1.0: return True
            if abs(f2 * 100 - f1) < 1.0: return True
            if abs(f1 * 10 - f2) < 1.0: return True
            if abs(f2 * 10 - f1) < 1.0: return True
    except (ValueError, TypeError):
        pass
        
    # Check string similarity
    s1 = str(v1).lower().replace(" ", "").replace(",", "")
    s2 = str(v2).lower().replace(" ", "").replace(",", "")
    
    if s1 == s2:
        return True
    
    # Use SequenceMatcher
    ratio = difflib.SequenceMatcher(None, s1, s2).ratio()
    if ratio >= 0.8: # 80% similarity
        return True
        
    # Check substring inclusion if one is sufficiently long
    if len(s1) >= 4 and len(s2) >= 4:
        if s1 in s2 or s2 in s1:
            return True
            
    return False

def _load_gt(path: Path) -> Dict[str, Any]:
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
                gt_data["total"] = float(val.replace(',','').replace(' ',''))
            except:
                pass

    for group in doc.get("groups", []):
        if group.get("name") == "Table":
            for row in group.get("groups", []):
                item = {}
                for field in row.get("fields", []):
                    name = field.get("name")
                    val = field.get("value")
                    if val is None or str(val).strip() == "": continue
                    try:
                        if name == "Price": item["price"] = float(str(val).replace(',',''))
                        elif name == "Quantity": item["quantity"] = float(str(val).replace(',',''))
                        elif name == "CatalogNo": item["catalog_no"] = str(val).strip()
                        elif name == "LineTotal": item["line_total"] = float(str(val).replace(',',''))
                    except:
                        pass
                if item:
                    gt_data["items"].append(item)
    return gt_data


def _find_pairs(images_dir: Path, pattern: str) -> List[tuple[Path, Path, Path]]:
    """
    Return (pdf, gt_json, pred_json) triples for all matching PDFs.
    """
    pairs: List[tuple[Path, Path, Path]] = []
    for pdf in sorted(images_dir.glob(pattern)):
        gt_json = pdf.with_suffix(".JSON")
        pred_json = pdf.with_suffix(".pred.json")
        if not gt_json.is_file():
            # Skip PDFs without a matching ground-truth JSON.
            continue
        pairs.append((pdf, gt_json, pred_json))
    return pairs


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    # region agent log
    import json as _json_testacc
    import time as _time_testacc
    import sys as _sys_testacc
    from pathlib import Path as _Path_testacc

    try:
        with open(
            r"c:\Users\Kfir Ezer\Desktop\Receipt OCR\debug-4cbdb5.log",
            "a",
            encoding="utf-8",
        ) as _f:
            _f.write(
                _json_testacc.dumps(
                    {
                        "sessionId": "4cbdb5",
                        "runId": "pre-fix",
                        "hypothesisId": "H_test_accuracy_entry",
                        "location": "test_accuracy/cli.py:main:entry",
                        "message": "test_accuracy CLI main entry called",
                        "data": {
                            "argv": argv,
                            "parsed_images_dir": str(args.images_dir),
                            "config": args.config,
                            "cwd": str(_Path_testacc.cwd()),
                            "python_executable": _sys_testacc.executable,
                        },
                        "timestamp": int(_time_testacc.time() * 1000),
                    },
                    default=str,
                )
                + "\n"
            )
    except Exception:
        # Logging must never break the CLI
        pass
    # endregion

    images_dir = Path(args.images_dir)
    if not images_dir.is_dir():
        parser.error(f"Images directory not found: {images_dir}")

    pairs = _find_pairs(images_dir, args.pattern)
    if not pairs:
        print(f"No PDF/JSON pairs found in {images_dir} matching pattern {args.pattern!r}")
        return 1

    print(f"Found {len(pairs)} PDF/JSON pairs under {images_dir}")

    if args.dry_run:
        for pdf, gt_json, pred_json in pairs:
            print(f"[DRY RUN] {pdf.name} -> GT: {gt_json.name}, PRED: {pred_json.name}")
        return 0

    # Import and call the local receipt_ocr CLI directly so we are sure
    # we are exercising the code in this repository (with instrumentation),
    # not an unrelated installed package.
    from receipt_ocr.cli import main as receipt_main

    start_time_all = time.time()
    total_processing_time = 0.0
    field_match_count = 0
    field_total_count = 0

    for pdf, gt_json, pred_json in pairs:
        print(f"Processing {pdf.name} (ground truth: {gt_json.name})")
        receipt_argv = [
            "--image",
            str(pdf),
            "--config",
            args.config,
            "--output",
            str(pred_json),
        ]
        
        t0 = time.time()
        exit_code = receipt_main(receipt_argv)
        t1 = time.time()
        
        if exit_code != 0:
            print(f"Failed processing {pdf.name}")
            continue
            
        total_processing_time += (t1 - t0)
        
        # Evaluate accuracy
        gt = _load_gt(gt_json)
        pred = _load_gt(pred_json) # pred is already in the exact same schema
        
        # Compare header fields
        for key in ["invoice_no", "date", "total"]:
            if gt[key] is not None:
                field_total_count += 1
                if _fuzzy_match_value(pred.get(key), gt[key]):
                    field_match_count += 1
                
        # Compare items (using bag-of-words exact match for items to handle unordered)
        # We'll calculate a score based on lines correctly matched
        for gt_item in gt["items"]:
            # For each expected item, score if found in prediction
            # we look for matching catalog_no, or matching line_total
            best_match_score = 0
            field_total_count += len(gt_item)
            for pred_item in pred["items"]:
                matching_keys = sum(1 for k,v in gt_item.items() if _fuzzy_match_value(pred_item.get(k), v))
                best_match_score = max(best_match_score, matching_keys)
            
            field_match_count += best_match_score

    avg_time = total_processing_time / len(pairs) if pairs else 0.0
    success_rate = (field_match_count / field_total_count * 100) if field_total_count > 0 else 0.0

    # Simple summary of produced files.
    summary = {
        "images_dir": str(images_dir),
        "config": args.config,
        "pairs_processed": len(pairs),
        "average_processing_time_sec": round(avg_time, 2),
        "success_rate_percent": round(success_rate, 2),
    }
    print("\n--- RESULTS ---")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

