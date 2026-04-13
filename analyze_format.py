import json
import sys

# Analyze ABBYY format
with open('sample_images/Tnuva_20.01.2025_Tnuva 20-01-25 B.JSON', encoding='utf-8') as f:
    data = json.load(f)

gdoc = data.get('GDocument', {})
print('GDocument keys:', list(gdoc.keys()))

# Get structure info
groups = gdoc.get('groups', [])
print(f'Groups: {len(groups)}')
for g in groups:
    print(f'  Group: {g.get("name")}')
    subgroups = g.get('groups', [])
    print(f'    Subgroups: {len(subgroups)}')
    if subgroups:
        fields = subgroups[0].get('fields', [])
        print(f'    Fields in first subgroup: {len(fields)}')
        for f in fields[:6]:
            print(f'      {f.get("name")}: {f.get("value")}')