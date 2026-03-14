import json
from pathlib import Path
from test_accuracy.cli import _load_gt

def compare(file_prefix):
    gt = _load_gt(Path(f"sample_images/{file_prefix}.JSON"))
    pred = _load_gt(Path(f"sample_images/{file_prefix}.pred.json"))
    
    print("--- HEADER FIELDS ---")
    for key in ["invoice_no", "date", "total"]:
        print(f"[{key}] GT: {gt.get(key)} | PRED: {pred.get(key)}")
        
    print("\n--- ITEMS ---")
    print(f"GT Items: {len(gt['items'])}")
    print(f"PRED Items: {len(pred['items'])}")
    
    # Try greedy matching
    matched = 0
    total = sum(len(x) for x in gt['items'])
    
    for gt_i, gti in enumerate(gt['items']):
        best = 0
        best_p = None
        for p_i, pti in enumerate(pred['items']):
            score = sum(1 for k,v in gti.items() if pti.get(k) == v)
            if score > best:
                best = score
                best_p = pti
        print(f"GT Item {gt_i}: {gti}")
        if best_p:
            print(f"  Best Pred (Score {best}): {best_p}")
        else:
            print("  No matching predicted item found.")

if __name__ == "__main__":
    compare("Avikam_10.03.2025_Avikam 11-03-25")
