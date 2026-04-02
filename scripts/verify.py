import json, pathlib
sys_dir = pathlib.Path('sample_images')
for f in sorted(sys_dir.glob('*.pred.json')):
    try:
        d = json.load(open(f, encoding='utf-8'))
        vendor = [field['value'] for field in d['GDocument']['fields'] if field['name'] == 'VendorNameS']
        num_items = len(d['GDocument']['groups'][0]['groups'])
        print(f'\n==================')
        print(f'{f.name}:')
        print(f'  Vendor: {vendor[0] if vendor else "MISSING"}')
        print(f'  Total Items: {num_items}')
        if num_items > 0:
            print('  First 3 Items:')
            for i in range(min(3, num_items)):
                grp = d['GDocument']['groups'][0]['groups'][i]['fields']
                print(f'    Item {i+1}: {grp}')
    except Exception as e:
        print(f'{f.name}: Error - {e}')
