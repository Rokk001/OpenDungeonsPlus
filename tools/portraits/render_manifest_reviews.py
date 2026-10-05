"""Render the frozen manifest literally, without undocumented conditional rules."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--portrait',action='append',required=True)
args = parser.parse_args()
for identifier in args.portrait:
    folder = ROOT/'materials/portraits/variants'/identifier
    rows = [line.split('\t') for line in (folder/'manifest.cfg').read_text().splitlines()
            if line and not line.startswith('#')]
    base = Image.open(folder/next(r[1] for r in rows if r[0]=='Base')).convert('RGBA')
    slots = {r[1]:tuple(map(int,r[2:])) for r in rows if r[0]=='Slot'}
    allowed = {r[4] for r in rows if r[0] in ['Option','Fitted']}
    clips = [(r[1],r[2]) for r in rows if r[0]=='Clip']
    choices = json.loads((ROOT/'materials/portraits/neutral-variants'/identifier/'review/choices.json').read_text())
    review = folder/'review'
    review.mkdir(exist_ok=True)
    small_sheet = Image.new('RGB',(200,300))
    full_sheet = Image.new('RGB',(4*887,3*1774))
    for number,selected in enumerate(choices,1):
        assert set(selected.values())<=allowed
        composite = base.copy()
        for slot,rect in slots.items():
            if slot not in selected:
                continue
            patch = Image.open(folder/selected[slot]).convert('RGBA')
            x,y,w,h = rect
            for source,target in clips:
                if source!=slot:
                    continue
                target_alpha = Image.new('L',base.size)
                if target in selected:
                    target_alpha.paste(Image.open(folder/selected[target]).getchannel('A'),slots[target][:2])
                patch.putalpha(ImageChops.multiply(patch.getchannel('A'),target_alpha.crop((x,y,x+w,y+h))))
            composite.alpha_composite(patch,(x,y))
        composite.save(review/f'combined-{number}.png',compress_level=1)
        small = composite.resize((50,100),Image.Resampling.LANCZOS)
        small.save(review/f'combined-small-{number}.png')
        small_sheet.paste(small,((number-1)%4*50,(number-1)//4*100))
        full_sheet.paste(composite,((number-1)%4*887,(number-1)//4*1774))
    small_sheet.save(review/'combined-small-sheet.png')
    full_sheet.save(review/'combined-native-sheet.jpg',quality=95)
    (review/'choices.json').write_text(json.dumps(choices,indent=2)+'\n')
    print(identifier,'12 literal-manifest composites; visual acceptance pending')
