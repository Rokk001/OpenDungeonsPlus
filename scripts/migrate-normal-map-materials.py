#!/usr/bin/env python3
"""One-off migration of the material scripts to the per-texture-unit normal map syntax.

    python scripts/migrate-normal-map-materials.py [--dry-run]

The pass-level line

    rtshader_system { lighting_stage normal_map <tex> [object_space|tangent_space] }

is removed from the pass (the rtshader_system block is deleted if nothing else is left in it) and
replaced by

    texture_unit { texture <tex> rtshader_system { normal_map [object_space|tangent_space] } }

inside the same pass. If the pass already has a texture_unit whose texture is <tex>, the
rtshader_system block is appended to that texture_unit; otherwise a new texture_unit is appended
as the last texture_unit of the pass. The space keyword is carried over exactly as written (a missing
keyword stays missing). Line endings, encoding and every other line of a file are kept byte for byte.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATERIAL_DIR = os.path.join(ROOT, 'materials', 'scripts')

STAGE_RE = re.compile(r'^(\s*)lighting_stage\s+normal_map\s+(\S+)(?:\s+(object_space|tangent_space))?\s*$')
RTSS_RE = re.compile(r'^\s*rtshader_system\s*$')
TEXTURE_RE = re.compile(r'^\s*texture\s+(\S+)\s*$')
INDENT = '    '


def strip_code(line):
    """Return the line without its // comment and line ending."""
    return line.split('//', 1)[0].strip()


def eol_of(line):
    """Return the line ending of a line ('' if it has none)."""
    if line.endswith('\r\n'):
        return '\r\n'
    if line.endswith('\n'):
        return '\n'
    return ''


def block_end(lines, open_idx):
    """Return the index of the line that closes the block whose '{' is on or after open_idx."""
    depth = 0
    started = False
    for i in range(open_idx, len(lines)):
        code = strip_code(lines[i])
        depth += code.count('{') - code.count('}')
        if code.count('{'):
            started = True
        if started and depth == 0:
            return i
    raise ValueError('unbalanced braces')


def enclosing_open(lines, idx, keyword_re):
    """Return the index of the nearest line before idx matching keyword_re whose block contains idx."""
    for i in range(idx - 1, -1, -1):
        if keyword_re.match(strip_code(lines[i])):
            if lines[i + 1].strip() == '{' or strip_code(lines[i]).endswith('{'):
                if block_end(lines, i) > idx:
                    return i
    raise ValueError('no enclosing block')


def migrate_one(lines, stage_idx):
    """Rewrite one lighting_stage line in place; lines is changed and the new text is returned."""
    match = STAGE_RE.match(lines[stage_idx].rstrip('\r\n'))
    lead, tex, mode = match.group(1), match.group(2), match.group(3)
    eol = eol_of(lines[stage_idx]) or '\n'
    normal_map = 'normal_map' + (' ' + mode if mode else '')

    rtss_open = enclosing_open(lines, stage_idx, RTSS_RE)
    pass_open = enclosing_open(lines, rtss_open, re.compile(r'^pass(\s|$)'))
    rtss_close = block_end(lines, rtss_open)
    pass_close = block_end(lines, pass_open)

    # Find the direct texture_unit children of the pass and the one that uses the texture.
    units = []
    i = pass_open + 2
    while i < pass_close:
        if re.match(r'^texture_unit(\s|$)', strip_code(lines[i])):
            end = block_end(lines, i)
            units.append((i, end))
            i = end + 1
        else:
            i += 1
    target = None
    for start, end in units:
        for j in range(start, end):
            tm = TEXTURE_RE.match(strip_code(lines[j]))
            if tm and tm.group(1) == tex:
                target = (start, end, j)
                break
        if target:
            break

    # Pass-level indentation, copied verbatim from the rtshader_system line.
    pass_ind = re.match(r'\s*', lines[rtss_open]).group(0)
    if target:
        start, end, tex_line = target
        ind = re.match(r'\s*', lines[tex_line]).group(0)
        new = [ind + 'rtshader_system', ind + '{', ind + INDENT + normal_map, ind + '}']
        at = end
    else:
        new = [pass_ind + 'texture_unit', pass_ind + '{', pass_ind + INDENT + 'texture ' + tex,
               pass_ind + INDENT + 'rtshader_system', pass_ind + INDENT + '{',
               pass_ind + INDENT * 2 + normal_map, pass_ind + INDENT + '}', pass_ind + '}']
        at = units[-1][1] + 1 if units else pass_close
    new_lines = [n + eol for n in new]

    # Is the rtshader_system block empty once the stage line is gone? (Comments count as content.)
    rest = [k for k in range(rtss_open + 2, rtss_close) if k != stage_idx and lines[k].strip()]
    removal = (stage_idx, stage_idx) if rest else (rtss_open, rtss_close)
    assert removal[1] < at or removal[0] > at, 'insert point inside removed range'

    # Remove first, then insert at the shifted position.
    del lines[removal[0]:removal[1] + 1]
    # A whole removed block can leave a blank line directly in front of the closing brace of the pass.
    if not rest and lines[removal[0] - 1].strip() == '' and lines[removal[0]].strip() == '}':
        del lines[removal[0] - 1]
        removal = (removal[0] - 1, removal[1])
    if removal[1] < at:
        at -= removal[1] - removal[0] + 1
    if not target and lines[at - 1].strip() not in ('', '{') and not lines[at - 1].strip().startswith('//'):
        new_lines.insert(0, eol)
    lines[at:at] = new_lines
    return tex


def main():
    dry = '--dry-run' in sys.argv
    changed = 0
    for dirpath, _, names in os.walk(MATERIAL_DIR):
        for name in sorted(names):
            if not name.endswith('.material'):
                continue
            path = os.path.join(dirpath, name)
            with open(path, 'rb') as f:
                text = f.read().decode('latin-1')
            if 'lighting_stage normal_map' not in text:
                continue
            lines = text.splitlines(True)
            count = 0
            while True:
                idx = next((k for k in range(len(lines) - 1, -1, -1)
                            if STAGE_RE.match(lines[k].rstrip('\r\n'))), None)
                if idx is None:
                    break
                migrate_one(lines, idx)
                count += 1
            if count > 1:
                print('%s: %d lighting_stage normal_map lines migrated' % (os.path.relpath(path, ROOT), count))
            if not dry:
                with open(path, 'wb') as f:
                    f.write(''.join(lines).encode('latin-1'))
            changed += 1
    print('%d files migrated' % changed)


if __name__ == '__main__':
    main()
