"""Read-only contract and provenance checks; does not grant visual acceptance."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageChops

ROOT = Path(__file__).resolve().parents[2]
CAT = json.loads((ROOT/'tools/portraits/feature-catalog.json').read_text(encoding='utf-8-sig'))
OUT = ROOT/'materials/portraits/neutral-variants'
count = 0
portraits = 0
canonical = 0
provenance_path = OUT/'base-provenance.json'
if provenance_path.exists():
    for provenance in json.loads(provenance_path.read_text()):
        source = ROOT/provenance['source']
        assert hashlib.sha256(source.read_bytes()).hexdigest()==provenance['source_sha256']
        original = Image.open(source).convert('RGBA')
        delivery = Image.open(OUT/provenance['id']/'base.png').convert('RGBA')
        assert delivery.size==(887,1774)
        assert all(band.getbbox() is None for band in ImageChops.difference(original,delivery.crop((0,0,*original.size))).split())
        if provenance['bottom_rows_repeated']:
            assert all(band.getbbox() is None for band in ImageChops.difference(delivery.crop((0,1773,887,1774)),original.crop((0,1772,887,1773))).split())
        canonical += 1
for creature in CAT:
    folder = OUT/creature['id']
    if not (folder/'manifest.cfg').exists():
        continue
    portraits += 1
    base = Image.open(folder/'base.png').convert('RGBA')
    assert base.size==(887,1774)
    provenance = json.loads((folder/'base-provenance.json').read_text())
    source = ROOT/provenance['source']
    assert hashlib.sha256(source.read_bytes()).hexdigest()==provenance['source_sha256']
    original = Image.open(source).convert('RGBA')
    assert all(band.getbbox() is None for band in ImageChops.difference(original,base.crop((0,0,*original.size))).split())
    if provenance['bottom_rows_repeated']:
        assert all(band.getbbox() is None for band in ImageChops.difference(base.crop((0,1773,887,1774)),original.crop((0,1772,887,1773))).split())
    records = json.loads((folder/'placement.json').read_text())
    expected = {f"{j['slot']}-{j['n']}-{j['name']}.png" for j in creature['jobs']}
    helmet_folder = ROOT/'materials/portraits/helmet-variants'/creature['id']
    if any(r['file'].startswith('helmet-') for r in records):
        expected.update(r['file'] for r in json.loads((helmet_folder/'placement.json').read_text()))
    fitted_files = set()
    if (folder/'outfit-placement.json').exists():
        outfits = json.loads((folder/'outfit-placement.json').read_text())
        expected.update(r['file'] for r in outfits if not r['build'])
        fitted_files.update(r['file'] for r in outfits if r['build'])
        for record in outfits:
            assert hashlib.sha256((ROOT/record['source']).read_bytes()).hexdigest()==record['source_sha256']
            patch = Image.open(folder/record['file'])
            assert patch.mode=='RGBA' and patch.size==(887,1774)
    assert {r['file'] for r in records}==expected
    manifest = [line.split('\t') for line in (folder/'manifest.cfg').read_text().splitlines() if line and not line.startswith('#')]
    assert manifest[0][0] in ['Base','Image'] and manifest[0][1]=='base.png'
    slots = {line[1]:list(map(int,line[2:])) for line in manifest if line[0]=='Slot'}
    order = ['build','outfit','hair','ears','eyes','nose','mouth','chin','helmet','scar','neck']
    assert list(slots)==[slot for slot in order if slot in slots]
    assert all(row[0] in ['Base','Slot','Option'] for row in manifest)
    options = {line[4] for line in manifest if line[0]=='Option'}
    assert options==expected
    for record in records:
        source = ROOT/record['source']
        assert hashlib.sha256(source.read_bytes()).hexdigest()==record['source_sha256']
        assert hashlib.sha256((ROOT/provenance['source']).read_bytes()).hexdigest()==record['base_sha256']
        x,y,w,h = record['rect']
        assert slots[record['file'].split('-')[0]]==[x,y,w,h]
        assert 0<=x and 0<=y and x+w<=887 and y+h<=1774
        patch = Image.open(folder/record['file'])
        assert patch.mode=='RGBA' and patch.size==(w,h)
        assert Image.open(folder/'review'/record['file']).size==(887,1774)
        assert Image.open(folder/'review'/('small-'+record['file'])).size==(50,100)
        count += 1
    choices = json.loads((folder/'review/choices.json').read_text())
    assert len(choices)==12
    assert expected<=set().union(*(set(choice.values()) for choice in choices)), 'Every part must appear in a composite'
    for number,choice in enumerate(choices,1):
        assert set(choice.values())<=expected|fitted_files
        assert Image.open(folder/'review'/f'combined-{number}.png').size==(887,1774)
        assert Image.open(folder/'review'/f'combined-small-{number}.png').size==(50,100)
acceptance_path = OUT/'visual-acceptance.json'
accepted = 0
if acceptance_path.exists():
    for identifier,record in json.loads(acceptance_path.read_text())['portraits'].items():
        delivery = ROOT/'materials/portraits/variants'/identifier
        for filename,expected_hash in record['sha256'].items():
            assert hashlib.sha256((delivery/filename).read_bytes()).hexdigest()==expected_hash, f'Stale visual acceptance: {identifier}/{filename}'
        base_source = ROOT/'materials/portraits/neutral-bases'/(identifier+'.png')
        if record.get('base_sha256'):
            assert hashlib.sha256(base_source.read_bytes()).hexdigest()==record['base_sha256']
        coverage = json.loads((delivery/record['coverage']).read_text())
        assert coverage['all_options_covered'] and coverage['options']==record['options']
        accepted += 1
print(json.dumps(dict(portraits=portraits,patches=count,source_hashes_verified=count,canonical_bases_verified=canonical,
    visual_acceptance_records_verified=accepted,neutral_source_pixels_preserved=True,technical_validation='passed',visual_acceptance='separate'),indent=2))
