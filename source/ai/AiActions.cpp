#include "ai/AiActions.h"
#include "ai/KeeperAI.h"
#include "entities/Creature.h"
#include "entities/Tile.h"
#include "entities/GiftBoxEntity.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "gamemap/LevelScript.h"
#include "network/ODPacket.h"
#include "network/ClientNotification.h"
#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include "rooms/RoomManager.h"
#include "rooms/RoomMerchant.h"
#include "rooms/RoomCasino.h"
#include "rooms/RoomTavern.h"
#include "rooms/RoomSpa.h"
#include "spells/Spell.h"
#include "spells/SpellManager.h"
#include "spells/SpellType.h"
#include "traps/TrapManager.h"
#include "traps/TrapType.h"
#include "utils/ConfigManager.h"
#include "utils/Helper.h"
#include "game/SkillManager.h"
#include "game/SkillType.h"

#include <sstream>
#include <set>

namespace
{
//! \brief Encodes arbitrary names and action arguments as a whitespace-free save token.
std::string encode(const std::string& value)
{
    static const char digits[] = "0123456789abcdef";
    std::string result;
    for(unsigned char ch : value)
    {
        result += digits[ch >> 4];
        result += digits[ch & 15];
    }
    return result.empty() ? "-" : result;
}

//! \brief Restores encoded arguments, rejecting malformed save tokens.
std::string decode(const std::string& value)
{
    if(value == "-") return "";
    if(value.size() % 2 != 0) return "";
    std::string result;
    for(std::size_t i = 0; i < value.size(); i += 2)
    {
        unsigned int ch = 0;
        std::istringstream input(value.substr(i, 2));
        if(!(input >> std::hex >> ch)) return "";
        result += static_cast<char>(ch);
    }
    return result;
}

//! \brief Writes tile coordinates rather than retaining pointers until execution.
void writeTiles(std::ostream& output, const std::vector<Tile*>& tiles)
{
    std::vector<std::pair<int, int>> positions;
    std::set<std::pair<int, int>> seen;
    for(Tile* tile : tiles)
        if(tile != nullptr && seen.insert(std::make_pair(tile->getX(), tile->getY())).second)
            positions.push_back(std::make_pair(tile->getX(), tile->getY()));
    output << positions.size();
    for(const std::pair<int, int>& position : positions)
        output << ' ' << position.first << ' ' << position.second;
}

//! \brief Resolves saved coordinates against the current map.
std::vector<Tile*> readTiles(GameMap& map, std::istream& input)
{
    std::size_t count = 0;
    std::vector<Tile*> result;
    if(!(input >> count)) return result;
    for(std::size_t i = 0; i < count; ++i)
    {
        int x, y;
        if(!(input >> x >> y)) return std::vector<Tile*>();
        Tile* tile = map.getTile(x, y);
        if(tile != nullptr) result.push_back(tile);
    }
    return result;
}

//! \brief Applies the room setting with the same ownership and value gates as the server handler.
void roomSetting(KeeperAI& ai, std::istream& input)
{
    GameMap& map = ai.getGameMap();
    Player& player = ai.getControlledPlayer();
    Seat* seat = player.getSeat();
    std::string name;
    int type;
    if(!(input >> name >> type) || seat == nullptr) return;
    Room* room = nullptr;
    for(Room* candidate : map.getRoomsByTypeAndSeat(static_cast<RoomType>(type), seat))
        if(candidate->getName() == decode(name)) room = candidate;
    if(room == nullptr) return;
    int32_t first = 0, second = 0;
    bool flag = false, isSet = false;
    uint32_t value = 0;
    int x = 0, y = 0;
    switch(room->getType())
    {
        case RoomType::merchant:
        {
            std::string mode;
            if(!(input >> first >> mode) || player.getHasLost() || map.isInEditorMode()) return;
            RoomMerchant::applySettings(map, *seat, first, mode);
            break;
        }
        case RoomType::alchemyLab:
            if(input >> first && !player.getHasLost() && first >= 0 && first <= 2)
                seat->setLabMode(first);
            break;
        case RoomType::infirmary:
        {
            if(!(input >> first >> second >> flag) || player.getHasLost()) return;
            const ConfigManager& cfg = ConfigManager::getSingleton();
            const int32_t minimum = cfg.getRoomConfigInt32("InfirmaryDischargeMinPercent");
            const int32_t maximum = cfg.getRoomConfigInt32("InfirmaryDischargeMaxPercent");
            const int32_t step = cfg.getRoomConfigInt32("InfirmaryDischargeStepPercent");
            if((first != 0 && first != 1) || second < minimum || second > maximum || (second - minimum) % step != 0) return;
            seat->setInfirmaryPayer(first);
            seat->setInfirmaryThreshold(second);
            seat->setInfirmaryHealOn(flag);
            break;
        }
        case RoomType::ghostRoom:
            if(input >> x >> y >> value >> flag >> isSet && isSet && value <= static_cast<uint32_t>(GhostProduct::crystal)
                && map.getTile(x, y) != nullptr && map.getTile(x, y)->getCoveringRoom() == room)
            {
                seat->setGhostProduct(static_cast<GhostProduct>(value));
                seat->setGhostRevive(flag);
            }
            break;
        case RoomType::casino:
            if(input >> x >> y >> value >> isSet && isSet && value < static_cast<uint32_t>(CasinoPayout::nbValues)
                && map.getTile(x, y) != nullptr && map.getTile(x, y)->getCoveringRoom() == room)
                static_cast<RoomCasino*>(room)->setPayout(static_cast<CasinoPayout>(value));
            break;
        case RoomType::tavern:
            if(input >> x >> y >> value && value <= static_cast<uint32_t>(TavernPayer::creature)
                && map.getTile(x, y) != nullptr && map.getTile(x, y)->getCoveringRoom() == room)
                static_cast<RoomTavern*>(room)->setPayer(static_cast<TavernPayer>(value));
            break;
        case RoomType::spa:
            if(input >> x >> y >> value >> isSet && isSet && value <= static_cast<uint32_t>(SpaPayer::creature)
                && map.getTile(x, y) != nullptr && map.getTile(x, y)->getCoveringRoom() == room)
                static_cast<RoomSpa*>(room)->setPayer(static_cast<SpaPayer>(value));
            break;
        default: break;
    }
}

//! \brief Rechecks current legality and dispatches both live and restored actions to server paths.
void perform(KeeperAI& ai, const std::string& target)
{
    std::istringstream input(decode(target));
    std::string action;
    if(!(input >> action)) return;
    GameMap& map = ai.getGameMap();
    Player& player = ai.getControlledPlayer();
    Seat* seat = player.getSeat();
    if(seat == nullptr) return;
    if(action == "dig" || action == "room" || action == "trap" || action == "sellRoom" || action == "sellTrap")
    {
        int value = 0;
        if(!(input >> value)) return;
        std::vector<Tile*> tiles = readTiles(map, input);
        if(action == "dig") player.markTilesForDigging(value != 0, tiles, true);
        else if(action == "room" || action == "trap")
        {
            if(player.getHasLost()) return;
            const RoomType roomType = static_cast<RoomType>(value);
            if(action == "room" && (roomType == RoomType::bridgeWooden || roomType == RoomType::bridgeStone))
            {
                if(!SkillManager::isRoomAvailable(roomType, seat)) return;
                ODPacket packet;
                packet << static_cast<uint32_t>(tiles.size());
                for(Tile* tile : tiles) map.tileToPacket(packet, tile);
                RoomManager::buildRoom(&map, roomType, &player, packet);
                return;
            }
            const TrapType trapType = static_cast<TrapType>(value);
            const bool door = trapType == TrapType::doorWooden || trapType == TrapType::doorIronbound
                || trapType == TrapType::doorSteel || trapType == TrapType::doorBarricade
                || trapType == TrapType::doorSecret || trapType == TrapType::doorRuned;
            if(action == "trap" && door)
            {
                if(tiles.size() != 1 || !SkillManager::isTrapAvailable(trapType, seat)) return;
                ODPacket packet;
                map.tileToPacket(packet, tiles.front());
                TrapManager::buildTrap(&map, trapType, &player, packet);
                return;
            }
            std::vector<Tile*> legal;
            for(Tile* tile : tiles)
                if(tile->isBuildableUpon(seat)) legal.push_back(tile);
            if(legal.empty()) return;
            if(action == "room" && SkillManager::isRoomAvailable(static_cast<RoomType>(value), seat))
                RoomManager::buildRoomOnTiles(&map, static_cast<RoomType>(value), &player, legal, false);
            else if(action == "trap" && SkillManager::isTrapAvailable(static_cast<TrapType>(value), seat))
                TrapManager::buildTrapOnTiles(&map, static_cast<TrapType>(value), &player, legal, false);
        }
        else
        {
            ODPacket packet;
            packet << static_cast<uint32_t>(tiles.size());
            for(Tile* tile : tiles) map.tileToPacket(packet, tile);
            if(action == "sellRoom") RoomManager::sellRoomTiles(&map, &player, packet);
            else TrapManager::sellTrapTiles(&map, seat, packet);
        }
        return;
    }
    if(action == "setting") { roomSetting(ai, input); return; }
    if(action == "research")
    {
        uint32_t count;
        if(!(input >> count) || count >= static_cast<uint32_t>(SkillType::countSkill)) return;
        std::vector<SkillType> skills;
        bool stale = false;
        for(uint32_t i = 0; i < count; ++i)
        {
            int type;
            uint32_t level;
            if(!(input >> type >> level) || type <= static_cast<int>(SkillType::nullSkillType)
                || type >= static_cast<int>(SkillType::countSkill) || level < 1 || level > 3) return;
            SkillType skill = static_cast<SkillType>(type);
            stale = stale || level != seat->getSkillLevel(skill) + 1;
            skills.push_back(skill);
        }
        seat->setSkillTree(stale ? seat->getSkillPending() : skills);
        return;
    }
    if(action == "special")
    {
        int type;
        if(input >> type && !player.getHasLost() && type > static_cast<int>(GiftBoxType::skill)
            && type < static_cast<int>(GiftBoxType::item)) seat->useStoredSpecial(static_cast<GiftBoxType>(type));
        return;
    }
    if(action == "merchant")
    {
        uint32_t index;
        if(!(input >> index) || map.isInEditorMode() || player.getHasLost()) return;
        for(Room* base : map.getRoomsByTypeAndSeat(RoomType::merchant, seat))
        {
            RoomMerchant* merchant = static_cast<RoomMerchant*>(base);
            Tile* table = nullptr;
            if(merchant->findGood(index, table) != nullptr)
            {
                merchant->sellToKeeper(player, index);
                break;
            }
        }
        return;
    }
    if(action == "drop" || action == "banner")
    {
        int x, y;
        std::string name;
        if(!(input >> x >> y >> name)) return;
        Tile* tile = map.getTile(x, y);
        if(tile == nullptr) return;
        if(action == "drop")
        {
            const unsigned int index = name == "-" ? 0 : player.getHandIndex(GameEntityType::creature, decode(name));
            if(player.isDropHandPossible(tile, index)) player.dropHand(tile, index);
        }
        else
            for(Spell* banner : map.getSpellsBySeatAndType(seat, SpellType::callToWar))
                if(banner->getPositionTile() == tile && banner->canSlap(seat)
                    && map.getLevelScript().registerSlap(seat->getId())) banner->slap();
        return;
    }
    if(action == "pickup" || action == "slap")
    {
        std::string name;
        if(!(input >> name)) return;
        Creature* creature = map.getCreature(decode(name));
        if(creature == nullptr) return;
        if(action == "pickup")
        {
            if(creature->tryPickup(seat)) player.pickUpEntity(creature);
        }
        else if(creature->canSlap(seat) && map.getLevelScript().registerSlap(seat->getId())) creature->slap();
        return;
    }
    if(action == "spell")
    {
        int type, x, y;
        std::string name;
        if(!(input >> type >> x >> y >> name) || type <= static_cast<int>(SpellType::nullSpellType)
            || type >= static_cast<int>(SpellType::nbSpells) || player.getHasLost()) return;
        SpellType spell = static_cast<SpellType>(type);
        if(!SkillManager::isSpellAvailable(spell, seat) || player.getSpellCooldownTurns(spell) > 0) return;
        const bool tileTarget = spell == SpellType::summonWorker || spell == SpellType::callToWar
            || spell == SpellType::eyeEvil || spell == SpellType::createGold || spell == SpellType::inferno
            || spell == SpellType::tremor || spell == SpellType::summonChampion;
        if(tileTarget != (name == "-")) return;
        ODPacket packet;
        if(name != "-")
        {
            Creature* creature = map.getCreature(decode(name));
            if(creature == nullptr) return;
            if(spell == SpellType::creatureHeal || spell == SpellType::creatureExplosion) packet << uint32_t(1);
            packet << creature->getName();
        }
        else
        {
            Tile* tile = map.getTile(x, y);
            if(tile == nullptr) return;
            if(spell == SpellType::summonWorker) packet << uint32_t(1);
            map.tileToPacket(packet, tile);
        }
        if(!SpellManager::castSpell(&map, spell, &player, packet)) return;
        map.getLevelScript().recordEvent("Seat" + Helper::toString(seat->getId()), "cast:" + SpellManager::getSpellNameFromSpellType(spell));
        player.setSpellCooldownTurns(spell, SpellManager::getSpellCooldown(spell));
    }
}

//! \brief Schedules encoded arguments without keeping target entity or tile pointers alive.
void schedule(KeeperAI& ai, const std::string& key, const std::string& arguments)
{
    const std::string target = encode(arguments);
    ai.getMind().exec(key, 1, ai.getMind().now(), "-", nullptr, target, [&ai, target]() { perform(ai, target); });
}

//! \brief Schedules one rectangular selection as one hand action.
void scheduleTiles(KeeperAI& ai, const std::string& key, const std::string& action, int value, const std::vector<Tile*>& tiles)
{
    if(tiles.empty()) return;
    std::ostringstream arguments;
    arguments << action << ' ' << value << ' ';
    writeTiles(arguments, tiles);
    schedule(ai, key, arguments.str());
}
}

//! \brief Registers saved-action resolution before a loaded mind resumes.
void ACTS::bind(KeeperAI& ai)
{
    const char* keys[] = {"dig", "build", "sell", "trap", "spell", "possess", "pickup", "drop", "slap", "setting", "research"};
    for(const char* key : keys)
        ai.getMind().onAction(key, "-", [&ai](Tile*, const std::string& target) { perform(ai, target); });
}

//! \brief Schedules the human dig-marking path.
void ACTS::markDig(KeeperAI& ai, const std::vector<Tile*>& tiles, bool marked)
{ scheduleTiles(ai, "dig", "dig", marked ? 1 : 0, tiles); }
//! \brief Schedules a normally paid room build without level resource bonuses.
void ACTS::buildRoom(KeeperAI& ai, RoomType type, const std::vector<Tile*>& tiles)
{
    // AI row L04: ordinary prices and normal scheduling; no bonus gold, mana or speed.
    scheduleTiles(ai, "build", "room", static_cast<int>(type), tiles);
}
//! \brief Schedules selling only room tiles the seat may sell.
void ACTS::sellRoomTiles(KeeperAI& ai, const std::vector<Tile*>& tiles)
{ scheduleTiles(ai, "sell", "sellRoom", 0, tiles); }
//! \brief Schedules a normally paid, available trap build.
void ACTS::buildTrap(KeeperAI& ai, TrapType type, const std::vector<Tile*>& tiles)
{ scheduleTiles(ai, "trap", "trap", static_cast<int>(type), tiles); }
//! \brief Schedules selling only trap tiles the seat may sell.
void ACTS::sellTrapTiles(KeeperAI& ai, const std::vector<Tile*>& tiles)
{ scheduleTiles(ai, "sell", "sellTrap", 0, tiles); }
//! \brief Schedules the tile-target spell packet through the normal cast handler.
void ACTS::castSpell(KeeperAI& ai, SpellType type, Tile* tile)
{
    if(tile == nullptr) return;
    std::ostringstream args;
    args << "spell " << static_cast<int>(type) << ' ' << tile->getX() << ' ' << tile->getY() << " -";
    schedule(ai, type == SpellType::possess ? "possess" : "spell", args.str());
}
//! \brief Schedules the named-creature spell packet through the normal cast handler.
void ACTS::castSpell(KeeperAI& ai, SpellType type, Creature* creature)
{
    if(creature == nullptr) return;
    std::ostringstream args;
    args << "spell " << static_cast<int>(type) << " -1 -1 " << encode(creature->getName());
    schedule(ai, type == SpellType::possess ? "possess" : "spell", args.str());
}
//! \brief Schedules pickup with the creature's current pickup permission.
void ACTS::pickUp(KeeperAI& ai, Creature* creature)
{ if(creature != nullptr) schedule(ai, "pickup", "pickup " + encode(creature->getName())); }
//! \brief Schedules a legal drop of the front held object.
void ACTS::drop(KeeperAI& ai, Tile* tile)
{
    if(tile == nullptr) return;
    std::ostringstream args;
    args << "drop " << tile->getX() << ' ' << tile->getY() << " -";
    schedule(ai, "drop", args.str());
}
//! \brief Schedules pickup then an identity-checked drop so a failed pickup cannot drop another object.
void ACTS::moveCreature(KeeperAI& ai, Creature* creature, Tile* tile)
{
    if(creature == nullptr || tile == nullptr) return;
    pickUp(ai, creature);
    std::ostringstream args;
    args << "drop " << tile->getX() << ' ' << tile->getY() << ' ' << encode(creature->getName());
    schedule(ai, "drop", args.str());
}
//! \brief Schedules a slap subject to the entity permission and level-script limit.
void ACTS::slap(KeeperAI& ai, Creature* creature)
{ if(creature != nullptr) schedule(ai, "slap", "slap " + encode(creature->getName())); }
//! \brief Schedules removing an owned, slappable banner at the tile.
void ACTS::removeBanner(KeeperAI& ai, Tile* tile)
{
    if(tile == nullptr) return;
    std::ostringstream args;
    args << "banner " << tile->getX() << ' ' << tile->getY() << " -";
    schedule(ai, "slap", args.str());
}
//! \brief Saves each room type's existing server payload as typed arguments.
void ACTS::setRoomSetting(KeeperAI& ai, Room* room, ODPacket& packet)
{
    if(room == nullptr) return;
    std::ostringstream args;
    args << "setting " << encode(room->getName()) << ' ' << static_cast<int>(room->getType()) << ' ';
    int32_t first = 0, second = 0;
    uint32_t value = 0;
    bool flag = false, isSet = false;
    int x = 0, y = 0;
    switch(room->getType())
    {
        case RoomType::merchant:
        {
            std::string mode;
            if(!(packet >> first >> mode)) return;
            args << first << ' ' << mode;
            break;
        }
        case RoomType::alchemyLab:
            if(!(packet >> first)) return;
            args << first;
            break;
        case RoomType::infirmary:
            if(!(packet >> first >> second >> flag)) return;
            args << first << ' ' << second << ' ' << flag;
            break;
        case RoomType::ghostRoom:
            if(!(packet >> x >> y >> value >> flag >> isSet)) return;
            args << x << ' ' << y << ' ' << value << ' ' << flag << ' ' << isSet;
            break;
        case RoomType::casino:
        case RoomType::spa:
            if(!(packet >> x >> y >> value >> isSet)) return;
            args << x << ' ' << y << ' ' << value << ' ' << isSet;
            break;
        case RoomType::tavern:
            if(!(packet >> x >> y >> value)) return;
            args << x << ' ' << y << ' ' << value;
            break;
        default: return;
    }
    schedule(ai, "setting", args.str());
}
//! \brief Saves research levels so stale queue edits receive the human handler's gates.
void ACTS::setResearch(KeeperAI& ai, const std::vector<SkillType>& skills)
{
    std::ostringstream args;
    args << "research " << skills.size();
    for(SkillType skill : skills)
        args << ' ' << static_cast<int>(skill) << ' ' << ai.getControlledPlayer().getSeat()->getSkillLevel(skill) + 1;
    schedule(ai, "research", args.str());
}
//! \brief Schedules consumption of an owned stored special.
void ACTS::useSpecial(KeeperAI& ai, GiftBoxType type)
{
    std::ostringstream args;
    args << "special " << static_cast<int>(type);
    schedule(ai, "spell", args.str());
}
//! \brief Saves the merchant stock identity and schedules the existing purchase handler.
void ACTS::merchantBuy(KeeperAI& ai, ODPacket& packet)
{
    uint32_t index;
    if(!(packet >> index)) return;
    std::ostringstream args;
    args << "merchant " << index;
    schedule(ai, "setting", args.str());
}
