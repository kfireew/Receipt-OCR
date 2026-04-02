import sys, json, pathlib, time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'C:\Users\Kfir Ezer\Desktop\Receipt OCR')

from stages.preprocess.image_processor import preprocess_image
from stages.recognition.tesseract_client import recognize_boxes
from stages.parsing.receipt_parser import parse_receipt

# Define test files
sample_dir = pathlib.Path(r'C:\Users\Kfir Ezer\Desktop\Receipt OCR\sample_images')
files_to_test = [f.name for f in sample_dir.glob('*.pdf')]

for fname in files_to_test:
    img_path = str(sample_dir / fname)
    print(f"\n=========================")
    print(f"Testing {fname}")
    start_t = time.time()
    try:
        pages = preprocess_image(img_path)
        all_boxes = []
        for pi, pg in enumerate(pages):
            boxes = recognize_boxes(
                pg.preprocessed,
                tesseract_executable=r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                confusion_map=str(pathlib.Path(r'C:\Users\Kfir Ezer\Desktop\Receipt OCR') / 'confusion_map.json'),
                lang='heb+eng',
                page_idx=pi,
            )
            all_boxes.extend(boxes)
            
        receipt = parse_receipt(all_boxes)
        result_dict = receipt.to_gdocument_dict()
        
        # Save output for review
        out_path = sample_dir / fname.replace('.pdf', '.pred.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)
            
        print(f"Parsed Vendor: {receipt.merchant.value if receipt.merchant else 'None'}")
        
        # Check items for 'empty slots'
        items = receipt.items
        num_items = len(items)
        missing_qty = sum(1 for item in items if item.quantity == 1.0) # 1.0 is default, might mean missing if real qty usually differs, but let's check None/zeros
        empty_lines = sum(1 for item in items if not item.description or not item.unit_price)
        
        print(f"Items found: {num_items}. Empty slots (missing desc/price): {empty_lines}")
        if items:
            print(f" First item: Desc: '{items[0].description[:30]}', Qty: {items[0].quantity}, Price: {items[0].unit_price}")
        
    except Exception as e:
        print(f"Error processing {fname}: {str(e)}")
        
    print(f"Time: {time.time() - start_t:.2f}s")
