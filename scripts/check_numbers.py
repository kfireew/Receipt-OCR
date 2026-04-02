import sys, json, pathlib
sys.path.insert(0, r'C:\Users\Kfir Ezer\Desktop\Receipt OCR')

from stages.preprocess.image_processor import preprocess_image
from stages.recognition.tesseract_client import recognize_boxes
from stages.parsing.receipt_parser import parse_receipt

# Define test files
sample_dir = pathlib.Path(r'C:\Users\Kfir Ezer\Desktop\Receipt OCR\sample_images')
files_to_test = [
    'Wisso_03.03.2025_Wisso 13-03-25 A.pdf',
    'Tnuva_16.04.2025_Tnuva 21-04-25.pdf'
]

import sys
sys.stdout.reconfigure(encoding='utf-8')

for fname in files_to_test:
    img_path = str(sample_dir / fname)
    print(f"\n=========================")
    print(f"Testing {fname}")
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
        
        print(f"\nVendor: {receipt.merchant.value if receipt.merchant else 'None'}")
        
        items = receipt.items
        print(f"Items found: {len(items)}")
        
        for i, item in enumerate(items[:20]):
            print(f" {i+1}: DESC: '{item.description}'")
            print(f"    QTY: {item.quantity} | PRICE: {item.unit_price} | TOTAL: {item.line_total} | CAT: {item.catalog_no}")
            
    except Exception as e:
        print(f"Error processing {fname}: {str(e)}")
