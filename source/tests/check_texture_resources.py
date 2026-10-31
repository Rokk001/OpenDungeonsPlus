#!/usr/bin/env python3
"""Check that material textures and GUI images are in registered resource folders."""

import re
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


# Check every referenced texture against the non-recursive resource directories.
def main():
    config = (ROOT / 'cmake/config/resources.cfg.in').read_text(encoding='utf-8')
    folders = [ROOT / value.strip() for value in re.findall(r'^\s*FileSystem\s*=\s*(.+?)\s*$', config, re.MULTILINE)
               if '@' not in value]
    references = []
    for material in sorted((ROOT / 'materials/scripts').glob('*.material')):
        for number, line in enumerate(material.read_text(encoding='utf-8').splitlines(), 1):
            match = re.match(r'^\s*texture\s+(\S+)', line)
            if match:
                references.append((material.relative_to(ROOT), number, match.group(1).strip('"')))
    for imageset in sorted((ROOT / 'gui').glob('*.imageset')):
        root = ET.parse(imageset).getroot()
        for element in root.iter():
            if 'Imagefile' in element.attrib:
                references.append((imageset.relative_to(ROOT), 0, element.attrib['Imagefile']))
    missing = [(source, line, name) for source, line, name in references
               if not any((folder / name).is_file() for folder in folders)]
    for source, line, name in missing:
        print(f'{source}:{line}: missing registered texture {name}')
    print(f'{len(references)} references checked; {len(missing)} missing')
    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main())
