#!/usr/bin/env python3
"""Build website JSON data from the daily Shopify-style CSV export."""
from pathlib import Path
import csv, json, re, hashlib, html
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
MAPPING_FILE = ROOT / 'tools' / 'mappings.json'
INPUT_CANDIDATES = [ROOT / 'All Products.csv', ROOT / 'All Products(1).csv', ROOT / 'All_Products.csv']

def read_csv(path):
    # utf-8-sig handles Excel/Shopify BOM; fallback for common Windows exports.
    for enc in ('utf-8-sig', 'utf-8', 'cp1252'):
        try:
            with path.open('r', encoding=enc, newline='') as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    raise RuntimeError('Could not decode CSV. Save it as UTF-8 CSV and retry.')

def clean(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip()

def parse_categories(raw, mapping):
    raw = clean(raw)
    if not raw:
        return ['Other Medicines']
    # Known comma-joined compound tags must be resolved before splitting.
    if raw.upper() in mapping.get('compound_categories', {}):
        return mapping['compound_categories'][raw.upper()]
    pieces = [clean(x) for x in raw.split(',') if clean(x)]
    out=[]
    for piece in pieces:
        canonical = mapping.get('category_aliases', {}).get(piece.lower(), piece)
        if canonical.lower() == 'others': canonical = 'Other Medicines'
        # Display labels in title case, preserving common acronyms only when already short.
        if canonical == 'Other Medicines': label = canonical
        else: label = canonical.title().replace("'S", "'s").replace('Anti-Bacterial','Anti-Bacterial').replace('Anti-Fungal','Anti-Fungal')
        if label not in out: out.append(label)
    return out or ['Other Medicines']

def as_num(v):
    try:
        n=float(str(v).replace(',','').strip())
        return round(n, 4) if n >= 0 else 0
    except Exception: return 0

def main():
    src = next((p for p in INPUT_CANDIDATES if p.exists()), None)
    if not src:
        raise SystemExit('Put All Products.csv in the repository root, then run UPDATE_PRODUCTS.bat')
    mapping=json.loads(MAPPING_FILE.read_text(encoding='utf-8'))
    rows=read_csv(src)
    catalogue=[]; details=[]; vendor_counts=Counter(); category_counts=Counter(); missing_desc=[]
    aliases=mapping.get('vendor_aliases',{})
    for i,row in enumerate(rows,1):
        title=clean(row.get('Title'))
        if not title: continue
        original_vendor=clean(row.get('Vendor')) or 'Unspecified'
        vendor=aliases.get(original_vendor, original_vendor)
        tags=parse_categories(row.get('Tags') or row.get('Product Category') or row.get('Type'), mapping)
        price=as_num(row.get('Variant Price'))
        mrp=as_num(row.get('Variant Compare At Price'))
        image=clean(row.get('Image Src'))
        body=str(row.get('Body (HTML)') or '').strip()
        # Stable ID: identical title/vendor rows stay stable between daily exports.
        pid=hashlib.sha1((title+'|'+vendor).encode('utf-8')).hexdigest()[:14]
        p={
          'id':pid,'title':title,'name':title,'vendor':vendor,'vendorOriginal':original_vendor,
          'categories':tags,'type':clean(row.get('Type')),'price':price,'mrp':mrp,
          'image':image,'hasDetails':bool(body),'searchText':clean(title+' '+vendor+' '+row.get('Type',''))
        }
        catalogue.append(p)
        details.append({'id':pid,'bodyHtml':body})
        vendor_counts[vendor]+=1
        for t in tags: category_counts[t]+=1
        if not body: missing_desc.append({'title':title,'vendor':original_vendor})
    DATA.mkdir(exist_ok=True)
    (DATA/'catalogue.json').write_text(json.dumps(catalogue,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    (DATA/'details.json').write_text(json.dumps(details,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    report={
      'source':src.name,'products':len(catalogue),'vendors':len(vendor_counts),'categories':len(category_counts),
      'zero_or_invalid_price':sum(1 for p in catalogue if p['price']<=0),
      'missing_medicine_description':len(missing_desc),
      'vendor_counts':dict(sorted(vendor_counts.items())),
      'category_counts':dict(sorted(category_counts.items())),
      'missing_description_products':missing_desc
    }
    (DATA/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('DATA BUILD COMPLETE')
    print(f"Source: {src.name}\nProducts: {len(catalogue)}\nCompanies: {len(vendor_counts)}\nCategories: {len(category_counts)}")
    print(f"Zero/invalid prices: {report['zero_or_invalid_price']}\nMissing descriptions: {len(missing_desc)}")
    print('Generated: data/catalogue.json, data/details.json, data/build-report.json')

if __name__=='__main__': main()
