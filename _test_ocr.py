import sys, json, pathlib
sys.path.insert(0, r'C:\Users\Kfir Ezer\Desktop\Receipt OCR')

from stages.preprocess.image_processor import preprocess_image
from stages.recognition.tesseract_client import recognize_boxes
from stages.parsing.receipt_parser import parse_receipt

img_path = r'C:\Users\Kfir Ezer\Desktop\Receipt OCR\sample_images\Avikam_10.03.2025_Avikam 11-03-25.jpg'

# Check if image exists, try pdf fallback
img = pathlib.Path(img_path)
if not img.exists():
    # Try to find the file
    sample_dir = pathlib.Path(r'C:\Users\Kfir Ezer\Desktop\Receipt OCR\sample_images')
    matches = list(sample_dir.glob('Avikam_10.03.2025*.pdf'))
    print('Available PDFs:', [f.name for f in matches])
    if not matches:
        print('ERROR: No Avikam image found!')
        sys.exit(1)
    img_path = str(matches[0])
    print(f'Using: {img_path}')

print('Preprocessing...')
pages = preprocess_image(img_path)
print(f'  {len(pages)} page(s)')

all_boxes = []
for pi, pg in enumerate(pages):
    print(f'Recognizing page {pi}...')
    boxes = recognize_boxes(
        pg.preprocessed,
        tesseract_executable=r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        confusion_map=str(pathlib.Path(r'C:\Users\Kfir Ezer\Desktop\Receipt OCR') / 'confusion_map.json'),
        lang='heb+eng',
        page_idx=pi,
    )
    print(f'  Got {len(boxes)} boxes')
    all_boxes.extend(boxes)

print('Parsing...')
receipt = parse_receipt(all_boxes)
result = receipt.to_gdocument_dict()

out_path = r'C:\Users\Kfir Ezer\Desktop\Receipt OCR\sample_images\Avikam_10.03.2025_Avikam 11-03-25.pred.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f'Saved to {out_path}')

print()
print('=== TOP FIELDS ===')
for fld in result['GDocument']['fields']:
    print(f"  {fld['name']}: {fld['value']}")

print()
print('=== FIRST 5 LINE ITEMS ===')
for grp in result['GDocument']['groups'][0]['groups'][:5]:
    print(' ', {f['name']: f['value'] for f in grp['fields']})
