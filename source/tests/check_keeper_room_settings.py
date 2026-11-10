"""Keeper room settings: source contracts and a probe using production C++ methods.

Run --source-only during plan work (no compilation). FINAL runs without that flag
in a developer shell to compile and execute the extracted production methods.
Legacy tavern/spa importers are also exercised by their existing stream probes.
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]


def read(path):
    """Read a tracked source file as text."""
    return (root / path).read_text(encoding='utf-8')


def extract(text, signature):
    """Extract a production function, including its outer braces."""
    start = text.index(signature)
    return text[start:text.index('\n}\n', start) + 2]


seat_h = read('source/game/Seat.h')
seat_cpp = read('source/game/Seat.cpp')
settings = ('TavernPayer', 'SpaPayer', 'CasinoPayout')
enum_text = []
methods = []
room_methods = []
room_classes = []
for kind, setting in zip(('Tavern', 'Spa', 'Casino'), settings):
    header = read('source/rooms/Room' + kind + '.h')
    source = read('source/rooms/Room' + kind + '.cpp')
    start = header.index('enum class ' + setting)
    enum_text.append(header[start:header.index('};', start) + 2])
    assert re.search(r'\b' + setting + r' m' + setting + r';', seat_h)
    assert not re.search(r'\b' + setting + r' m(?:Payer|Payout);', header), kind
    # These source assertions bind the runtime checks to production construction,
    # capture and payment paths, rather than an independent settings model.
    accessor = 'Payout' if kind == 'Casino' else 'Payer'
    getter = extract(source, setting + ' Room' + kind + '::get' + accessor + '(')
    setter = extract(source, 'void Room' + kind + '::set' + accessor + '(')
    assert 'getSeat()->get' + setting + '()' in getter
    assert 'getSeat()->set' + setting + '(' in setter
    assert not re.search(r'\bmPayer\b|\bmPayout\b', source)
    for action in ('setupRoom', 'absorbRoom', 'splitRoom'):
        signature = 'void Room' + kind + '::' + action + '('
        if signature in source:
            body = extract(source, signature)
            assert 'set' + setting not in body and 'set' + accessor not in body
    importer = extract(source, 'bool Room' + kind + '::importFromStream(')
    assert 'getSeat()->loadLegacy' + setting + '(' in importer
    if kind == 'Tavern':
        assert 'TavernPayer legacyPayer = TavernPayer::keeper;' in importer
        assert importer.index('loadLegacyTavernPayer') > importer.index('while(true)')
    if kind == 'Spa':
        assert 'if(!payerRead)' in importer and '!getSeat()->getPlayer()->getIsHuman()' in importer
        assert importer.index('loadLegacySpaPayer') > importer.index('if(!payerRead)')
    guard = extract(seat_cpp, 'void Seat::loadLegacy' + setting + '(')
    assert 'if(!m' + setting + 'Set)' in guard
    for signature in (setting + ' Seat::get' + setting + '(',
                      'void Seat::set' + setting + '(',
                      'void Seat::loadLegacy' + setting + '('):
        methods.append(extract(seat_cpp, signature))
    room_methods.extend((getter, setter))
    extra = ''
    if kind == 'Casino':
        extra = 'void exportToStream(std::ostream&) const; bool importFromStream(std::istream&);'
        room_methods.extend((extract(source, 'void RoomCasino::exportToStream('), importer))
    room_classes.append('class Room' + kind + ' : public Room { public: using Room::Room; ' +
                        setting + ' get' + accessor + '() const; void set' + accessor + '(' + setting + '); ' + extra + ' };')

# New seat blocks are authoritative and optional, and serialize all three settings
# even if a keeper currently owns no room of a given type.
load_start = seat_cpp.index('    if(str == "[PleasureRoomSettings]")')
load_end = seat_cpp.index('\n    if(str == "[SpellCooldowns]")', load_start)
load_block = seat_cpp[load_start:load_end]
assert 'str == "[PleasureRoomSettings]"' in seat_cpp[seat_cpp.index('// Optional seat blocks'):load_start]
assert 'tavern > 1 || spa > 1 || casino > 1' in load_block
write_start = seat_cpp.index('    os << "[PleasureRoomSettings]')
write_end = seat_cpp.index(';', write_start) + 1
write_block = seat_cpp[write_start:write_end]
for setting in settings:
    assert 'set' + setting + '(static_cast<' + setting + '>' in load_block
    assert 'get' + setting + '()' in write_block

# Production constructor values, declarations and method bodies are inserted into
# the probe; expected values below are fixed, not derived from the source.
fields = '\n'.join(re.findall(r'^    (?:TavernPayer|SpaPayer|CasinoPayout|bool) m(?:TavernPayer|SpaPayer|CasinoPayout)(?:Set)?;', seat_h, re.M))
initializers = ', '.join(re.findall(r'^    (m(?:TavernPayer|SpaPayer|CasinoPayout)(?:Set)?\([^\n]+\)),?$', seat_cpp, re.M))
declarations = '\n'.join(setting + ' get' + setting + '() const; void set' + setting + '(' + setting + '); void loadLegacy' + setting + '(' + setting + ');' for setting in settings)
probe = r'''
#include <iostream>
#include <sstream>
#include <string>
#include <cstdint>
@@ENUMS@@
struct Player { bool human; bool getIsHuman() const { return human; } };
//! \brief Provides only the dependencies needed by the production keeper settings.
class Seat { public:
    Player* player;
    Seat(Player* p = nullptr) : player(p), @@INITIALIZERS@@ {}
    Player* getPlayer() const { return player; }
    @@FIELDS@@
    @@DECLARATIONS@@
    bool load(std::istream& is);
    void save(std::ostream& os) const;
};
@@METHODS@@
//! \brief Exercises the production optional-block parser without unrelated seat state.
bool Seat::load(std::istream& is)
{
    std::string str;
    if(!(is >> str)) return false;
    while(str == "[PleasureRoomSettings]")
    {
@@LOAD@@
    }
    return str == "Tail";
}
//! \brief Exercises the production keeper-setting serialization statement.
void Seat::save(std::ostream& os) const
{
@@WRITE@@
}
//! \brief A room's owner may change without copying any payer or payout state.
struct Room {
    Seat* owner;
    Room(Seat* seat) : owner(seat) {}
    Seat* getSeat() const { return owner; }
    void exportToStream(std::ostream& os) const { os << "RoomHead\n"; }
    bool importFromStream(std::istream& is) { std::string head; return (is >> head) && head == "RoomHead"; }
};
@@ROOM_CLASSES@@
@@ROOM_METHODS@@
int failures = 0;
//! \brief Records a fixed expected outcome of a keeper settings scenario.
void expect(bool ok, const char* message) { if(!ok) { ++failures; std::cerr << message << '\n'; } }
//! \brief Checks defaults, shared changes, construction, capture, migration and persistence.
int main()
{
    Player human{true}, ai{false};
    Seat h(&human), a(&ai), unbound;
    expect(h.getTavernPayer() == TavernPayer::keeper && h.getSpaPayer() == SpaPayer::keeper, "human defaults");
    expect(a.getTavernPayer() == TavernPayer::creature && a.getSpaPayer() == SpaPayer::creature, "AI defaults");
    expect(h.getCasinoPayout() == CasinoPayout::smiles && a.getCasinoPayout() == CasinoPayout::smiles, "casino defaults");
    unbound.player = &ai;
    expect(unbound.getTavernPayer() == TavernPayer::creature && unbound.getSpaPayer() == SpaPayer::creature, "late player assignment");
    RoomTavern t1(&h), t2(&h); RoomSpa s1(&h), s2(&h); RoomCasino c1(&h), c2(&h);
    t1.setPayer(TavernPayer::creature); s1.setPayer(SpaPayer::creature); c1.setPayout(CasinoPayout::money);
    expect(t2.getPayer() == TavernPayer::creature && s2.getPayer() == SpaPayer::creature && c2.getPayout() == CasinoPayout::money, "all existing rooms share changes");
    RoomTavern laterT(&h); RoomSpa laterS(&h); RoomCasino laterC(&h);
    expect(laterT.getPayer() == TavernPayer::creature && laterS.getPayer() == SpaPayer::creature && laterC.getPayout() == CasinoPayout::money, "later construction");
    a.setTavernPayer(TavernPayer::keeper); a.setSpaPayer(SpaPayer::keeper); a.setCasinoPayout(CasinoPayout::smiles);
    t1.owner = &a; s1.owner = &a; c1.owner = &a;
    expect(t1.getPayer() == TavernPayer::keeper && s1.getPayer() == SpaPayer::keeper && c1.getPayout() == CasinoPayout::smiles, "capture uses receiving keeper settings");
    t1.setPayer(TavernPayer::creature); s1.setPayer(SpaPayer::creature); c1.setPayout(CasinoPayout::money);
    expect(a.getTavernPayer() == TavernPayer::creature && a.getSpaPayer() == SpaPayer::creature && a.getCasinoPayout() == CasinoPayout::money, "AI settings can change");
    t1.setPayer(TavernPayer::keeper);
    expect(t2.getPayer() == TavernPayer::creature, "different keepers remain independent");
    Seat legacy(&human);
    legacy.loadLegacyTavernPayer(TavernPayer::creature); legacy.loadLegacyTavernPayer(TavernPayer::keeper);
    legacy.loadLegacySpaPayer(SpaPayer::keeper); legacy.loadLegacySpaPayer(SpaPayer::creature);
    legacy.loadLegacyCasinoPayout(CasinoPayout::money); legacy.loadLegacyCasinoPayout(CasinoPayout::smiles);
    expect(legacy.getTavernPayer() == TavernPayer::creature && legacy.getSpaPayer() == SpaPayer::keeper && legacy.getCasinoPayout() == CasinoPayout::money, "first room wins independently per type");
    Seat missing(&ai);
    missing.loadLegacyTavernPayer(TavernPayer::keeper); missing.loadLegacyTavernPayer(TavernPayer::creature);
    missing.loadLegacySpaPayer(SpaPayer::creature); missing.loadLegacySpaPayer(SpaPayer::keeper);
    expect(missing.getTavernPayer() == TavernPayer::keeper && missing.getSpaPayer() == SpaPayer::creature, "historical absent payer defaults win");
    // Every possible saved combination, with and without rooms, survives load.
    const unsigned expected[8][3] = {{0,0,0}, {1,0,0}, {0,1,0}, {1,1,0}, {0,0,1}, {1,0,1}, {0,1,1}, {1,1,1}};
    for(unsigned bits = 0; bits < 8; ++bits)
    {
        Seat before(&human);
        before.setTavernPayer(static_cast<TavernPayer>(expected[bits][0]));
        before.setSpaPayer(static_cast<SpaPayer>(expected[bits][1]));
        before.setCasinoPayout(static_cast<CasinoPayout>(expected[bits][2]));
        std::ostringstream out; before.save(out); out << "Tail";
        Seat after(&ai); std::istringstream in(out.str());
        expect(after.load(in), "keeper block loads");
        after.loadLegacyTavernPayer(TavernPayer::keeper); after.loadLegacyTavernPayer(TavernPayer::creature);
        after.loadLegacySpaPayer(SpaPayer::keeper); after.loadLegacySpaPayer(SpaPayer::creature);
        after.loadLegacyCasinoPayout(CasinoPayout::money); after.loadLegacyCasinoPayout(CasinoPayout::smiles);
        expect(static_cast<unsigned>(after.getTavernPayer()) == expected[bits][0] && static_cast<unsigned>(after.getSpaPayer()) == expected[bits][1] && static_cast<unsigned>(after.getCasinoPayout()) == expected[bits][2], "keeper block wins over legacy rooms");
        RoomTavern t(&after); RoomSpa s(&after); RoomCasino c(&after);
        expect(static_cast<unsigned>(t.getPayer()) == expected[bits][0] && static_cast<unsigned>(s.getPayer()) == expected[bits][1] && static_cast<unsigned>(c.getPayout()) == expected[bits][2], "rooms built after load");
    }
    Seat empty(&ai); std::istringstream oldSeat("Tail");
    expect(empty.load(oldSeat) && empty.getTavernPayer() == TavernPayer::creature && empty.getSpaPayer() == SpaPayer::creature && empty.getCasinoPayout() == CasinoPayout::smiles, "old save without rooms uses defaults");
    const char* bad[] = {"[PleasureRoomSettings] 2 0 0 [/PleasureRoomSettings] Tail", "[PleasureRoomSettings] 0 2 0 [/PleasureRoomSettings] Tail", "[PleasureRoomSettings] 0 0 2 [/PleasureRoomSettings] Tail", "[PleasureRoomSettings] 0 0 [/PleasureRoomSettings] Tail", "[PleasureRoomSettings] x 0 0 [/PleasureRoomSettings] Tail", "[PleasureRoomSettings] 0 0 0 [/Other] Tail"};
    for(const char* text : bad) { Seat broken; std::istringstream in(text); expect(!broken.load(in), "invalid block rejected"); }
    for(unsigned oldValue = 0; oldValue < 3; ++oldValue)
    {
        Seat owner; RoomCasino first(&owner), second(&owner);
        std::ostringstream text; text << "RoomHead\nCasinoPayout " << oldValue << "\nTail";
        std::istringstream in(text.str()), later("RoomHead\nCasinoPayout 0\nTail");
        expect(first.importFromStream(in) && second.importFromStream(later), "old casino loads");
        expect(first.getPayout() == (oldValue == 0 ? CasinoPayout::money : CasinoPayout::smiles), "first casino maps former three values");
    }
    Seat casinoMissing; RoomCasino first(&casinoMissing), second(&casinoMissing);
    std::istringstream absent("RoomHead\nTail"), later("RoomHead\nCasinoPayout 0\nTail");
    expect(first.importFromStream(absent) && second.importFromStream(later) && second.getPayout() == CasinoPayout::smiles, "missing first casino line wins");
    std::string tail; absent >> tail; expect(tail == "Tail", "missing casino line preserves next token");
    return failures == 0 ? 0 : 1;
}
'''
for token, value in {
    '@@ENUMS@@': '\n'.join(enum_text), '@@INITIALIZERS@@': initializers,
    '@@FIELDS@@': fields, '@@DECLARATIONS@@': declarations, '@@METHODS@@': '\n'.join(methods),
    '@@LOAD@@': load_block, '@@WRITE@@': write_block,
    '@@ROOM_CLASSES@@': '\n'.join(room_classes), '@@ROOM_METHODS@@': '\n'.join(room_methods),
}.items():
    probe = probe.replace(token, value)
assert '@@' not in probe

if '--source-only' in sys.argv:
    print('keeper room settings source contracts passed; runtime probe deferred to FINAL')
else:
    with tempfile.TemporaryDirectory(prefix='odp-keeper-settings-') as directory:
        work = Path(directory)
        (work / 'check.cpp').write_text(probe, encoding='utf-8')
        subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/O2', '/W3', 'check.cpp', '/Fecheck.exe'], cwd=work, check=True)
        subprocess.run([str(work / 'check.exe')], cwd=work, check=True)
    print('keeper room settings runtime passed')
