"""Check game asset references in configuration, levels and production C++.

OGRE references use declared, case-sensitive names, not script filenames. Meshes
are file resources; sounds use the folder families loaded by SoundEffectsManager.
The check also follows literal C++ constants, wrapper calls and generated resource
names. Run --self-test for the parser's positive and missing-resource fixtures.
"""
from dataclasses import dataclass
from pathlib import Path
import argparse
import ast
import json
import re
import sys
import tempfile

STRING = r'"(?:\\.|[^"\\])*"'
CPP_TOKEN = re.compile(STRING + r'|\b[A-Za-z_]\w*(?:::\w+)*\b|[^\s]')
EMPTY = {'', 'none', "''", '-', 'null'}


@dataclass(frozen=True)
class Reference:
    """An asset name and the exact source location that supplies it."""
    path: str
    line: int
    kind: str
    name: str


def read(path):
    """Read the project's text resources without depending on the OS locale."""
    return path.read_text(encoding='utf-8-sig')


def without_comments(text):
    """Remove C++ comments while preserving strings, offsets and line numbers."""
    pattern = re.compile(STRING + r'|//[^\n]*|/\*.*?\*/', re.S)
    return pattern.sub(lambda m: m[0] if m[0].startswith('"') else
                       ''.join('\n' if c == '\n' else ' ' for c in m[0]), text)


def script_names(path, kind):
    """Read the root-level named declarations of OGRE particle/material scripts."""
    text = without_comments(read(path))
    depth = 0
    pending = ''
    names = set()
    for line in text.splitlines():
        if depth == 0:
            if line.strip().startswith(('import ', 'export ')):
                continue
            pending += ' ' + line.strip()
            if '{' in pending:
                header = pending.split('{', 1)[0].strip()
                if kind == 'particle':
                    match = re.fullmatch(r'(?:particle_system\s+)?([^\s:]+)(?:\s*:\s*\S+)?', header)
                else:
                    match = re.fullmatch(r'(?:abstract\s+)?material\s+([^\s:]+)(?:\s*:\s*\S+)?', header)
                if match:
                    names.add(match[1].strip('"'))
                pending = ''
        depth += line.count('{') - line.count('}')
        if depth == 0 and '}' in line:
            pending = ''
    return names


# Resolve flat sound families only when the loader both opens and registers them.
def registered_flat_sound_families(root):
    """Follow literal array registrations and require exact existing sound paths."""
    source = root / 'source/sound/SoundEffectsManager.cpp'
    if not source.is_file():
        return set()
    text = without_comments(read(source))
    paths = set(re.findall(
        r'const\s+std::string\s*&\s*(\w+)\s*=\s*'
        r'ResourceManager::getSingleton\(\)\.getSoundPath\(\)\s*;', text))
    files = {p.relative_to(root / 'sounds').as_posix()
             for p in (root / 'sounds').rglob('*.ogg') if p.is_file()}
    families = set()
    arrays = re.finditer(r'(?:static\s+)?const\s+char\s*\*\s*(?:const\s+)?'
                         r'(\w+)\s*\[\s*\]\s*=\s*\{([^{}]*)\}\s*;', text)
    for array in arrays:
        if not re.fullmatch(r'\s*' + STRING + r'(?:\s*,\s*' + STRING + r')*\s*,?\s*', array[2]):
            continue
        loop = re.compile(r'for\s*\(\s*const\s+char\s*\*\s*(\w+)\s*:\s*'
                          + re.escape(array[1]) + r'\s*\)\s*\{([^{}]*)\}', re.S)
        for match in loop.finditer(text, array.end()):
            body = match[2]
            family = re.search(r'const\s+std::string\s+(\w+)\s*=\s*std::string\(('
                               + STRING + r')\)\s*\+\s*' + re.escape(match[1]) + r'\s*;', body)
            if not family:
                continue
            load = re.search(r'GameSound\s*\*\s*(\w+)\s*=\s*getGameSound\(\s*(\w+)\s*\+\s*'
                             + re.escape(family[1]) + r'\s*\+\s*"\.ogg"\s*,\s*true\s*\)\s*;',
                             body[family.end():])
            if not load or load[2] not in paths:
                continue
            registration = (r'mSpatialSounds\s*\[\s*' + re.escape(family[1])
                            + r'\s*\]\s*\.push_back\(\s*' + re.escape(load[1]) + r'\s*\)\s*;')
            if not re.search(registration, body[family.end() + load.end():]):
                continue
            prefix = ast.literal_eval(family[2])
            for literal in re.findall(STRING, array[2]):
                name = prefix + ast.literal_eval(literal)
                if name + '.ogg' in files:
                    families.add(name)
    return families


# Index the resources accepted by the production loaders.
def inventory(root):
    """Index logical script names, exact mesh filenames and loaded sound families."""
    assets = {'particle': set(), 'material': set(), 'mesh': set(), 'sound': set(), 'relative_sound': set()}
    for path in (root / 'particles').rglob('*.particle'):
        assets['particle'].update(script_names(path, 'particle'))
    for path in (root / 'materials').rglob('*.material'):
        assets['material'].update(script_names(path, 'material'))
    assets['mesh'].update(path.name for path in (root / 'models').rglob('*.mesh'))
    for path in (root / 'sounds/Spatial').rglob('*.ogg'):
        assets['sound'].add(path.parent.relative_to(root / 'sounds/Spatial').as_posix())
    assets['sound'].update(registered_flat_sound_families(root))
    # Incomplete voices fall back to Default in SoundEffectsManager::playRelativeSound.
    config_source = root / 'source/utils/ConfigManager.cpp'
    default_voice = 'Default'
    if config_source.is_file():
        declaration = re.search(r'DEFAULT_KEEPER_VOICE\s*=\s*"([^"]+)"', read(config_source))
        assert declaration, 'cannot resolve the keeper voice fallback'
        default_voice = declaration[1]
    default = root / 'sounds/Relative' / default_voice
    assets['relative_sound'] = {path.parent.relative_to(default).as_posix() for path in default.rglob('*.ogg')}
    return assets


def add(refs, path, line, kind, name):
    """Record non-empty runtime asset names, retaining case and source locations."""
    if name in EMPTY:
        return
    if kind == 'mesh' and not name.endswith('.mesh'):
        name += '.mesh'
    refs.add(Reference(path, line, kind, name))


def data_references(root):
    """Read named and positional asset fields of configuration and saved levels."""
    refs = set()
    paths = sorted(set((root / 'config').rglob('*.cfg')) |
                   {p for p in (root / 'levels').rglob('*') if p.is_file() and p.suffix in {'.level', '.cfg'}})
    for path in paths:
        relative = path.relative_to(root).as_posix()
        sections = []
        for line_no, original in enumerate(read(path).splitlines(), 1):
            line = original.split('#', 1)[0].strip()
            if not line:
                continue
            if line.startswith('['):
                if line.startswith('[/'):
                    if sections:
                        sections.pop()
                elif line.endswith(']'):
                    sections.append(line[1:-1])
                continue
            words = line.split()
            key = words[0]
            values = words[1:]
            if not values:
                continue
            # GameEntity stream prefix: SeatId, Name, MeshName. Three entity types prepend their type.
            if sections and sections[-1] in {'Creatures', 'TreasuryObject', 'Chickens', 'CraftedTraps', 'SkillEntity', 'Spells', 'GiftBoxEntity', 'Missiles'}:
                mesh_index = 3 if sections[-1] in {'Spells', 'GiftBoxEntity', 'Missiles'} else 2
                if len(words) > mesh_index:
                    add(refs, relative, line_no, 'mesh', words[mesh_index])
            # Explicit file resources occur both in named fields and positional saved entities.
            for word in words:
                if word.endswith('.mesh'):
                    add(refs, relative, line_no, 'mesh', word)
                elif word.endswith(('.ogg', '.wav', '.flac')):
                    add(refs, relative, line_no, 'music_file' if key in {'Music', 'FightMusic', 'MenuMusic', 'MainMenuMusic'} else 'sound_file', word)
            if key in {'System', 'EndSystem', 'Effect', 'LateEffect'} and not (
                    key == 'Effect' and path.name == 'items.cfg' and sections and sections[-1] == 'Quality'):
                add(refs, relative, line_no, 'particle', values[0])
            elif key in {'AddParticleEffect', 'AddParticleEffectBone'} and len(values) >= 2:
                add(refs, relative, line_no, 'particle', values[1])
            elif key == 'AddEntity' and len(values) >= 2:
                add(refs, relative, line_no, 'mesh', values[1])
            elif key in {'MeshName', 'BedMeshName'}:
                add(refs, relative, line_no, 'mesh', values[0])
            elif key == 'Mesh':
                # Portrait entries are cache keys formed by CreatureAppearance from mesh + gender.
                mesh = re.sub(r'(?<=\.mesh)-(?:female|male)$', '', values[0]) if path.name == 'portrait-tints.cfg' else values[0]
                add(refs, relative, line_no, 'mesh', mesh)
            elif key.startswith('SoundFamily') and values[0] not in EMPTY:
                add(refs, relative, line_no, 'sound', 'Creatures/' + values[0])
            elif key in {'Family', 'Sound'} and path.name.startswith('roomAmbience'):
                add(refs, relative, line_no, 'sound', values[0])
            elif key in {'Material', 'MaterialName'}:
                add(refs, relative, line_no, 'material', values[0])
            elif key in {'Emote', 'LateEmote'}:
                add(refs, relative, line_no, 'material', 'CreatureEmote_' + values[0])
            elif key == 'Prop' and len(values) >= 2 and not values[1].endswith('.mesh'):
                add(refs, relative, line_no, 'material', 'CreatureProp_' + values[1])
            # Tileset rows carry mesh/material/rotation, including entries inside [oneOf].
            if path.name == 'tilesets.cfg':
                mesh_index = 1 if re.fullmatch('[01]{4}', key) else 0
                if len(words) > mesh_index + 1 and words[mesh_index].endswith('.mesh'):
                    add(refs, relative, line_no, 'material', words[mesh_index + 1])
            skill = words[1:] if key in {'BaseLine', 'LegacySkill'} else words
            if skill and skill[0] in {'GasCloud', 'HailStorm', 'AreaDamage'} and len(skill) > 8:
                add(refs, relative, line_no, 'particle', skill[8])
            if skill and skill[0] in {'MissileLaunch', 'GuidedBolt', 'Grenade'} and len(skill) > 7:
                add(refs, relative, line_no, 'mesh', skill[6])
                add(refs, relative, line_no, 'particle', skill[7])
            if sections and sections[-1] == 'CreatureEffects' and len(words) > 2:
                add(refs, relative, line_no, 'particle', words[2])
    return refs


def split_arguments(tokens, start):
    """Split a C++ call's arguments without splitting nested expressions."""
    args, current, depth = [], [], 0
    for index in range(start + 1, len(tokens)):
        token = tokens[index][0]
        if token == ')' and depth == 0:
            if current or args:
                args.append(current)
            return args, index
        if token == ',' and depth == 0:
            args.append(current)
            current = []
            continue
        if token in {'(', '[', '{'}:
            depth += 1
        elif token in {')', ']', '}'}:
            depth -= 1
        current.append(tokens[index])
    return [], start


def expression_values(tokens, constants, seen=frozenset()):
    """Resolve literal expressions and named string constants, including alternatives."""
    if not tokens:
        return set()
    parts = [token[0] for token in tokens]
    if len(parts) == 1:
        value = parts[0]
        if re.fullmatch(STRING, value):
            return {ast.literal_eval(value)}
        if value in constants and value not in seen:
            return set().union(*(expression_values(expr, constants, seen | {value}) for expr in constants[value]))
        return set()
    if parts[0] == '{' and parts[-1] == '}':
        result = set()
        for token in tokens[1:-1]:
            if token[0].startswith(chr(34)):
                result.update(expression_values([token], constants, seen))
        return result
    if len(parts) >= 3 and parts[1] == '[' and parts[-1] == ']':
        return expression_values(tokens[:1], constants, seen)
    if len(parts) >= 3 and parts[1] == '(' and parts[-1] == ')':
        return expression_values([('@return:' + parts[0], tokens[0][1])], constants, seen)
    # A conditional contributes each branch, not the strings in its condition.
    if '?' in parts and ':' in parts:
        question = parts.index('?')
        colon = parts.index(':', question)
        return expression_values(tokens[question + 1:colon], constants, seen) | expression_values(tokens[colon + 1:], constants, seen)
    if '+' in parts:
        split = parts.index('+')
        left = expression_values(tokens[:split], constants, seen)
        right = expression_values(tokens[split + 1:], constants, seen)
        if left and right:
            return {a + b for a in left for b in right}
        return set()
    return set()


def cpp_references(root, assets):
    """Follow literal C++ resource consumers, constants and direct helper arguments."""
    refs = set()
    sources = []
    global_constants = {}
    for path in sorted((root / 'source').rglob('*')):
        if path.suffix not in {'.cpp', '.h', '.hpp'}:
            continue
        text = without_comments(read(path))
        tokens = [(match[0], match.start()) for match in CPP_TOKEN.finditer(text)]
        constants = {}
        for match in re.finditer(r'\b([A-Za-z_]\w*(?:::\w+)*)(?:\s*\[[^\]]*\])?\s*=\s*([^;]+)', text):
            constants.setdefault(match[1], []).append([(token[0], match.start(2) + token.start()) for token in CPP_TOKEN.finditer(match[2])])
        sources.append((path, text, tokens, constants))
        # Qualified constants from headers (e.g. relative sound names) resolve across compilation units.
        for match in re.finditer(r'namespace\s+(\w+)\s*\{([^{}]*)\}', text, re.S):
            for definition in re.finditer(r'\b(?:string|char\s*\*)\s+(\w+)\s*=\s*("[^"\n]*")', match[2]):
                global_constants.setdefault(match[1] + '::' + definition[1], []).append([(definition[2], 0)])
    # Room constructor names label tiled room geometry, rather than a rendered mesh resource.
    room_classes = set()
    for path, text, tokens, local in sources:
        room_classes.update(re.findall(r'class\s+(\w+)\s*:\s*public\s+Room\b', text))
    room_constructor_spans = {}
    for path, text, tokens, local in sources:
        spans = []
        for constructor in re.finditer(r'\b(\w+)::\1\s*\([^{}]*\)\s*:[^{]+\{', text):
            if constructor[1] not in room_classes:
                continue
            end, depth = constructor.end(), 1
            while end < len(text) and depth:
                depth += (text[end] == '{') - (text[end] == '}')
                end += 1
            spans.append((constructor.end(), end))
        room_constructor_spans[path] = spans
    consumers = {
        'createParticleSystem': ('particle', 1, ''),
        'getTemplate': ('particle', 0, ''),
        'setMaterialName': ('material', 0, ''),
        'setMaterial': ('material', 0, ''),
        'setMeshName': ('mesh', 0, ''),
        'createEntity': ('mesh', 1, ''),
        'playSpatialSound': ('sound', 0, ''),
        'startSpatialLoop': ('sound', 0, ''),
        'playRelativeSound': ('relative_sound', 0, ''),
        'fireRelativeSound': ('relative_sound', 1, ''),
        'fireGameSound': ('sound', 1, 'Game/'),
        'fireTrapSound': ('sound', 1, 'Traps/'),
        'fireSpellSound': ('sound', 1, 'Spells/'),
        'fireRoomSound': ('sound', 1, 'Rooms/'),
        'fireSpellEffect': ('sound', 2, 'Spells/'),
        'createChickenFeatherEffect': ('particle', 1, ''),
    }
    # Named string parameters define the resource-bearing arguments of project helpers and constructors.
    consumers = {name: [rule] for name, rule in consumers.items()}
    fixed_consumers = set(consumers)
    for path, text, tokens, local in sources:
        for declaration in re.finditer(r'\b(\w+)\s*\(([^;{}]*)\)\s*(?:const\s*)?(?:override\s*)?[;{]', text):
            name, parameters = declaration[1], declaration[2]
            if name in fixed_consumers:
                continue
            for index, parameter in enumerate(parameters.split(',')):
                if not re.search(r'(?:string|String)\s*[&*]?', parameter):
                    continue
                words = re.findall(r'\w+', parameter.split('=')[0])
                argument = words[-1] if words else ''
                kind = ('mesh' if re.fullmatch(r'(?:m)?(?:[a-zA-Z]*[Mm]esh(?:Name)?|mesh)', argument) else
                        'material' if argument in {'materialName', 'material', 'baseMaterial'} else
                        'particle' if re.search(r'(?:[Pp]article.*(?:Script|System)|effectScript)', argument) else
                        'sound' if argument in {'soundFamily', 'familySound'} else None)
                if kind:
                    rule = (kind, index, '')
                    if rule not in consumers.setdefault(name, []):
                        consumers[name].append(rule)
    # Follow a helper which converts a mesh name argument to a generated mesh.
    providers = {}
    returned_constants = {}
    for path, text, tokens, local in sources:
        for definition in re.finditer(r'\b((?:\w+::)*\w+)\s*\(([^;{}]*)\)\s*\{', text):
            if definition[1] in {'if', 'for', 'while', 'switch', 'catch'}:
                continue
            start = definition.end()
            depth, end = 1, start
            while end < len(text) and depth:
                depth += (text[end] == '{') - (text[end] == '}')
                end += 1
            body = text[start:end]
            function_constants = dict(global_constants)
            function_constants.update(local)
            body_constants = {}
            for assigned in re.finditer(r'\b([A-Za-z_]\w*)(?:\s*\[[^\]]*\])?\s*=\s*([^;]+)', body):
                body_constants.setdefault(assigned[1], []).append(
                    [(token[0], start + assigned.start(2) + token.start()) for token in CPP_TOKEN.finditer(assigned[2])])
            function_constants.update(body_constants)
            for returned in re.finditer(r'\breturn\s+([^;]+);', body):
                expression = [(token[0], start + returned.start(1) + token.start())
                              for token in CPP_TOKEN.finditer(returned[1])]
                for value in expression_values(expression, function_constants):
                    returned_constants.setdefault('@return:' + definition[1], []).append([(json.dumps(value, ensure_ascii=False), start + returned.start(1))])
            for parameter_index, parameter in enumerate(definition[2].split(',')):
                words = re.findall(r'\w+', parameter.split('=')[0])
                if not words:
                    continue
                parameter_name = words[-1]
                if re.search(r'convertToMesh\(\s*' + re.escape(parameter_name) + r'\s*\+\s*"\.mesh"', body):
                    providers[definition[1]] = parameter_index
    global_constants.update(returned_constants)
    # A uniquely named class helper can also be called unqualified from another method of that class.
    short_names = {}
    for name in returned_constants:
        short_names.setdefault(name.split('::')[-1], []).append(name)
    for short, names in short_names.items():
        if len(names) == 1:
            global_constants['@return:' + short] = returned_constants[names[0]]
    for path, text, tokens, local in sources:
        relative = path.relative_to(root).as_posix()
        constants = dict(global_constants)
        constants.update(local)
        # Resources produced in memory are proven from actual creation calls, not an allowlist.
        for index, (name, position) in enumerate(tokens[:-1]):
            if tokens[index + 1][0] != '(':
                continue
            args, end = split_arguments(tokens, index + 1)
            if name in {'createPlane', 'convertToMesh'} and args:
                assets['mesh'].update(value + ('' if value.endswith('.mesh') else '.mesh')
                                      for value in expression_values(args[0], constants))
            if name == 'create' and 'MaterialManager' in text[max(0, position - 85):position] and args:
                assets['material'].update(expression_values(args[0], constants))
            if name in providers and len(args) > providers[name]:
                assets['mesh'].update(value + ('' if value.endswith('.mesh') else '.mesh')
                                      for value in expression_values(args[providers[name]], constants))
            if name == 'getByName' and 'MaterialManager' in text[max(0, position - 85):position] and args:
                for value in expression_values(args[0], constants):
                    add(refs, relative, text.count('\n', 0, position) + 1, 'material', value)
            if name not in consumers:
                continue
            for kind, argument, prefix in consumers[name]:
                receiver = text[max(0, position - 50):position].rstrip()
                if name == 'setMeshName' and not receiver.endswith(('->', '.')) and any(
                        start <= position < end for start, end in room_constructor_spans[path]):
                    continue
                if name == 'createParticleSystem' and not receiver.endswith('->'):
                    argument = 0
                if name == 'setMaterialName' and receiver.endswith('mMovableTextOverlay->'):
                    argument = 1
                if argument >= len(args):
                    continue
                for value in expression_values(args[argument], constants):
                    if value not in EMPTY:
                        add(refs, relative, text.count('\n', 0, position) + 1, kind, prefix + value)
        for match in re.finditer(STRING, text):
            value = match[0][1:-1]
            line = text.count('\n', 0, match.start()) + 1
            # Unit-test catalog keys are deliberately synthetic; only real typed resource consumers count there.
            if value.endswith('.mesh') and value != '.mesh' and 'tests' not in path.relative_to(root / 'source').parts:
                add(refs, relative, line, 'mesh', value)
            elif value.endswith(('.ogg', '.wav', '.flac')) and not value.startswith('.'):
                statement = text[text.rfind(';', 0, match.start()) + 1:text.find(';', match.end())]
                kind = 'music_file' if re.search(r'\b\w*[Mm]usic\w*', statement) else 'sound_file'
                add(refs, relative, line, kind, value)
        # Constants identify additional resources consumed through variable-valued wrappers.
        for key, expressions in local.items():
            if re.search('PREFIX|GROUP|SUBPATH|SUFFIX', key, re.I):
                continue
            kind = ('mesh' if re.search('mesh', key, re.I) else
                    'material' if re.search('material', key, re.I) else
                    'sound' if key in {'soundComplete'} else None)
            if kind:
                for expr in expressions:
                    for value in expression_values(expr, constants):
                        if re.fullmatch(r'[\w/.-]+', value):
                            add(refs, relative, text.count('\n', 0, expr[0][1]) + 1, kind, value)
    return refs



def finite_name_references(root):
    """Expand the game's class, density and mood-bit resource-name families."""
    refs = set()
    pile_source = root / 'source/entities/DirtPileEntity.cpp'
    if pile_source.is_file():
        text = read(pile_source)
        match = re.search(r'PILE_MESH_PREFIX\s*=\s*"([^"]+)"', text)
        assert match, 'cannot resolve the pile mesh prefix'
        prefix = match[1]
        for path in list((root / 'config').rglob('*.cfg')) + list((root / 'levels').rglob('*.level')):
            content = read(path)
            for creature in re.finditer(r'\[Creature\](.*?)\[/Creature\]', content, re.S):
                name = re.search(r'^\s*Name\s+(\S+)', creature[1], re.M)
                if name:
                    position = creature.start(1) + name.start(1)
                    add(refs, path.relative_to(root).as_posix(), content.count('\n', 0, position) + 1,
                        'mesh', prefix + name[1])
    render = root / 'source/render/RenderManager.cpp'
    tile = root / 'source/entities/Tile.cpp'
    if render.is_file() and tile.is_file():
        text = read(render)
        base = re.search(r'GOLD_WALL_MATERIAL\s*=\s*"([^"]+)"', text)
        if base and 'goldWallMaterialName' in text:
            line = text.count('\n', 0, text.index('std::string RenderManager::goldWallMaterialName')) + 1
            add(refs, render.relative_to(root).as_posix(), line, 'material', base[1])
            for density in re.finditer(r'GOLD_DENSITY_(?:LOW|HIGH)\s*=\s*(\d+)', read(tile)):
                add(refs, render.relative_to(root).as_posix(), line, 'material', base[1] + density[1])
    overlay = root / 'source/render/CreatureOverlayStatus.cpp'
    mood = root / 'source/entities/CreatureMoodValues.h'
    if overlay.is_file() and mood.is_file():
        text = read(overlay)
        prefix = re.search(r'CREATURE_OVERLAY_STATUS_PREFIX\s*=\s*"([^"]+)"', text)
        assert prefix, 'cannot resolve the mood material prefix'
        line = text.count('\n', 0, text.index('CREATURE_OVERLAY_STATUS_PREFIX')) + 1
        for bit in re.finditer(r'const\s+uint32_t\s+\w+\s*=\s*(0x[0-9a-fA-F]+|\d+)\s*;', read(mood)):
            value = int(bit[1], 0)
            if value and (value & (value - 1)) == 0:
                add(refs, overlay.relative_to(root).as_posix(), line, 'material', prefix[1] + str(value))
    return refs


def missing_references(root, refs, assets):
    """Return unresolved exact, case-sensitive names and file paths."""
    missing = []
    sound_files = {p.relative_to(root / 'sounds').as_posix() for p in (root / 'sounds').rglob('*') if p.is_file()}
    music_files = {p.relative_to(root / 'music').as_posix() for p in (root / 'music').rglob('*') if p.is_file()}
    for ref in sorted(refs, key=lambda r: (r.path, r.line, r.kind, r.name)):
        if ref.kind == 'music_file':
            found = ref.name.removeprefix('music/') in music_files
        elif ref.kind == 'sound_file':
            name = ref.name.removeprefix('sounds/')
            found = name in sound_files
        else:
            names = assets[ref.kind]
            found = ref.name in names
        if not found:
            missing.append(ref)
    return missing


def audit(root):
    """Collect all supported game references and check them against real resources."""
    assets = inventory(root)
    refs = data_references(root) | cpp_references(root, assets) | finite_name_references(root)
    return refs, missing_references(root, refs, assets)



# Exercise supported registrations and reject missing or unregistered resources.
def self_test():
    """Exercise real parser paths, flat registrations and missing-name mutations."""
    with tempfile.TemporaryDirectory(prefix='odp-asset-refs-') as directory:
        root = Path(directory)
        files = {
            'models/Valid.mesh': '',
            'models/Pile_ValidClass.mesh': '',
            'config/creatures.cfg': '[Creature]\nName ValidClass\nMeshName Valid.mesh\n[/Creature]\n',
            'source/entities/DirtPileEntity.cpp': 'const std::string DirtPileEntity::PILE_MESH_PREFIX = "Pile_";\n',
            'source/render/RenderManager.cpp': 'const std::string GOLD_WALL_MATERIAL = "Gold";\nstd::string RenderManager::goldWallMaterialName(int density) { return ""; }\n',
            'source/entities/Tile.cpp': 'const uint32_t Tile::GOLD_DENSITY_LOW = 50;\nconst uint32_t Tile::GOLD_DENSITY_HIGH = 150;\n',
            'source/render/CreatureOverlayStatus.cpp': 'const std::string CREATURE_OVERLAY_STATUS_PREFIX = "Mood_";\n',
            'source/entities/CreatureMoodValues.h': 'const uint32_t Angry = 0x0001;\nconst uint32_t Upset = 0x0400;\n',
            'materials/scripts/families.material': 'material Gold { }\nmaterial Gold50 { }\nmaterial Gold150 { }\nmaterial Mood_1 { }\nmaterial Mood_1024 { }\n',
            'particles/valid.particle': 'BaseParticle\n{\n}\nparticle_system ValidParticle : BaseParticle\n{\n material ValidMaterial\n}\n',
            'materials/scripts/valid.material': 'import Base from "external.material"\nmaterial ValidMaterial\n{\n}\n',
            'sounds/Spatial/Test/Valid/sound.ogg': '',
            'sounds/Flat/Valid.ogg': '',
            'sounds/Flat/Undeclared.ogg': '',
            'config/roomAmbienceFlat.cfg': 'Family Flat/Valid\n',
            'source/sound/SoundEffectsManager.cpp': (
                '//! \\brief Registers the literal flat sound fixture.\n'
                'SoundEffectsManager::SoundEffectsManager() {\n'
                'const std::string& folder = ResourceManager::getSingleton().getSoundPath();\n'
                'static const char* const names[] = {"Valid"};\n'
                'for(const char* name : names) {\n'
                'const std::string family = std::string("Flat/") + name;\n'
                'GameSound* sound = getGameSound(folder + family + ".ogg", true);\n'
                'if(sound != nullptr) mSpatialSounds[family].push_back(sound);\n}\n}\n'),

            'sounds/Relative/Default/Interface/Click/click.ogg': '',
            'music/Song.ogg': '',
            'config/roomAmbienceFixture.cfg': 'System ValidParticle\nMeshName Valid.mesh\nMaterial ValidMaterial\nFamily Test/Valid\nMusic Song.ogg\nBaseLine HailStorm 1 1 1 1 1 1 1 ValidParticle\nBaseLine GuidedBolt 1 1 1 1 1 Valid ValidParticle 1\n',
            'levels/Fixture.level': '[TreasuryObject]\n0 Saved Valid 0 0 0\n[/TreasuryObject]\n',
            'config/items.cfg': '[Item]\n[Quality]\nEffect GameplayRule 1\n[/Quality]\n[/Item]\n',
            'config/creatureReactions.cfg': 'Effect ValidParticle 1\nLateEffect ValidParticle 1 1\n',
            'source/rooms/RoomFixture.h': '//! \\brief Identifies the tiled-room fixture for constructor classification.\nclass RoomFixture : public Room {};\n',
            'source/rooms/RoomFixture.cpp': '//! \\brief Labels the tiled room while retaining a real furniture mesh consumer.\nRoomFixture::RoomFixture(GameMap* map) : Room(map) { setMeshName("RoomLabel"); object->setMeshName("Valid"); }\n',
            'levels/Effects.level': '[CreatureEffects]\nBurn 2 ValidParticle 1.0\n[/CreatureEffects]\n',
            'source/Fixture.cpp': 'const std::string MeshId = "Valid.mesh";\nconst char* systems[] = {"ValidParticle"};\nvoid shape(const std::string& meshName) { object->convertToMesh(meshName + ".mesh", "Graphics"); }\nvoid create() {\n shape("Generated");\n scene->createEntity("runtime", "Generated.mesh");\n scene->createEntity("static", MeshId);\n scene->createParticleSystem("p", systems[0]);\n entity->setMaterialName("ValidMaterial");\n playSpatialSound("Test/Valid", 0, 0);\n playRelativeSound("Interface/Click");\n sound->loadFromFile("Spatial/Test/Valid/sound.ogg");\n setLevelMusicFile("Song.ogg");\n scene->createParticleSystem("helper", particleFor(true));\n}\nconst std::string& particleFor(bool b) { static const std::string selected = "ValidParticle"; return selected; }\nconst std::string& unrelated() { static const std::string selected = "NotAnAsset"; return selected; }\n',
            'source/tests/test_Fixture.cpp': 'void fixture() {\n setCatalogId("Missing.mesh");\n scene->createEntity("test", "Valid.mesh");\n}\n',
        }
        for filename, text in files.items():
            path = root / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8')
        refs, missing = audit(root)
        assert not missing, missing
        assert any(r.name == 'Generated.mesh' for r in refs), 'runtime mesh consumer missing'
        assert any(r.name == 'ValidParticle' and r.path == 'source/Fixture.cpp' for r in refs), 'constant array not followed'
        cases = [
            ('config/creatureReactions.cfg', 'Effect ValidParticle', 'Effect MissingReaction', 'particle', 'MissingReaction', 1),
            ('config/creatureReactions.cfg', 'LateEffect ValidParticle', 'LateEffect MissingLateReaction', 'particle', 'MissingLateReaction', 2),
            ('source/rooms/RoomFixture.cpp', 'object->setMeshName("Valid")', 'object->setMeshName("MissingFurniture")', 'mesh', 'MissingFurniture.mesh', 2),
            ('config/roomAmbienceFixture.cfg', 'System ValidParticle', 'System MissingParticle', 'particle', 'MissingParticle', 1),
            ('config/roomAmbienceFixture.cfg', 'MeshName Valid.mesh', 'MeshName Missing.mesh', 'mesh', 'Missing.mesh', 2),
            ('config/roomAmbienceFixture.cfg', 'Material ValidMaterial', 'Material validmaterial', 'material', 'validmaterial', 3),
            ('config/roomAmbienceFixture.cfg', 'Family Test/Valid', 'Family Test/Missing', 'sound', 'Test/Missing', 4),
            ('config/roomAmbienceFixture.cfg', 'Music Song.ogg', 'Music song.ogg', 'music_file', 'song.ogg', 5),
            ('config/roomAmbienceFixture.cfg', '1 ValidParticle\n', '1 MissingHail\n', 'particle', 'MissingHail', 6),
            ('config/roomAmbienceFixture.cfg', 'Valid ValidParticle 1', 'Valid MissingBolt 1', 'particle', 'MissingBolt', 7),
            ('config/creatures.cfg', 'Name ValidClass', 'Name MissingClass', 'mesh', 'Pile_MissingClass.mesh', 2),
            ('source/entities/Tile.cpp', 'HIGH = 150', 'HIGH = 175', 'material', 'Gold175', 2),
            ('source/entities/CreatureMoodValues.h', '0x0400', '0x0800', 'material', 'Mood_2048', 1),
            ('levels/Effects.level', 'Burn 2 ValidParticle', 'Burn 2 MissingEffect', 'particle', 'MissingEffect', 2),
            ('levels/Fixture.level', '0 Saved Valid ', '0 Saved MissingSaved ', 'mesh', 'MissingSaved.mesh', 2),
            ('source/Fixture.cpp', '"Valid.mesh";', '"MissingConstant.mesh";', 'mesh', 'MissingConstant.mesh', 1),
            ('source/Fixture.cpp', '{"ValidParticle"}', '{"MissingArray"}', 'particle', 'MissingArray', 8),
            ('source/Fixture.cpp', 'setMaterialName("ValidMaterial")', 'setMaterialName("MissingMaterial")', 'material', 'MissingMaterial', 9),
            ('source/Fixture.cpp', 'playSpatialSound("Test/Valid"', 'playSpatialSound("Test/Missing"', 'sound', 'Test/Missing', 10),
            ('source/Fixture.cpp', 'Spatial/Test/Valid/sound.ogg', 'Spatial/Wrong/sound.ogg', 'sound_file', 'Spatial/Wrong/sound.ogg', 12),
            ('source/Fixture.cpp', 'setLevelMusicFile("Song.ogg")', 'setLevelMusicFile("song.ogg")', 'music_file', 'song.ogg', 13),
            ('source/Fixture.cpp', 'selected = "ValidParticle"', 'selected = "MissingReturned"', 'particle', 'MissingReturned', 14),
            ('source/tests/test_Fixture.cpp', 'createEntity("test", "Valid.mesh")', 'createEntity("test", "MissingActual.mesh")', 'mesh', 'MissingActual.mesh', 3),
        ]
        for filename, old, new, kind, name, line in cases:
            path = root / filename
            original = read(path)
            assert old in original, old
            path.write_text(original.replace(old, new, 1), encoding='utf-8')
            _, missing = audit(root)
            expected_path = ('source/render/RenderManager.cpp' if name == 'Gold175' else
                             'source/render/CreatureOverlayStatus.cpp' if name == 'Mood_2048' else filename)
            assert any(r.path == expected_path and r.line == line and r.kind == kind and r.name == name for r in missing), (filename, kind, name, line, missing)
            path.write_text(original, encoding='utf-8')
        # Flat files need an exact source registration as well as the actual recording.
        assert 'Flat/Valid' in inventory(root)['sound'], 'registered flat sound was omitted'
        flat_config = root / 'config/roomAmbienceFlat.cfg'
        for name in ('Undeclared', 'valid'):
            flat_config.write_text('Family Flat/' + name + '\n', encoding='utf-8')
            _, missing = audit(root)
            assert any(r.kind == 'sound' and r.name == 'Flat/' + name for r in missing), missing
        flat_config.write_text(files['config/roomAmbienceFlat.cfg'], encoding='utf-8')
        recording = root / 'sounds/Flat/Valid.ogg'
        original_recording = recording.read_bytes()
        recording.unlink()
        _, missing = audit(root)
        assert any(r.kind == 'sound' and r.name == 'Flat/Valid' for r in missing), missing
        recording.write_bytes(original_recording)
        loader = root / 'source/sound/SoundEffectsManager.cpp'
        for old, new in (('getGameSound(', 'notAProducer('),
                         ('mSpatialSounds[family].push_back(sound);', 'notARegistration(sound);')):
            loader.write_text(files['source/sound/SoundEffectsManager.cpp'].replace(old, new, 1), encoding='utf-8')
            _, missing = audit(root)
            assert any(r.kind == 'sound' and r.name == 'Flat/Valid' for r in missing), missing
            loader.write_text(files['source/sound/SoundEffectsManager.cpp'], encoding='utf-8')
        # A runtime mesh is accepted only while a real producer creates that same name.
        path = root / 'source/Fixture.cpp'
        path.write_text(files['source/Fixture.cpp'].replace('object->convertToMesh', 'object->notAProducer'), encoding='utf-8')
        _, missing = audit(root)
        assert any(r.name == 'Generated.mesh' for r in missing), 'unproven runtime mesh was accepted'
    print(f'asset reference self-test: {len(cases) + 8} cases passed')


def main():
    """Print missing names with file/line diagnostics and fail until every name exists."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    refs, missing = audit(args.root)
    for ref in missing:
        print(f'{ref.path}:{ref.line}: missing {ref.kind}: {ref.name}')
    print(f'Asset references: {len(refs)} checked, {len(missing)} missing')
    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main())
