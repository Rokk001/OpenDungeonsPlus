#ifndef AIACTIONS_H
#define AIACTIONS_H

#include <string>
#include <vector>

class Creature;
class KeeperAI;
class ODPacket;
class Room;
class Tile;
enum class GiftBoxType;
enum class RoomType;
enum class SkillType;
enum class SpellType;
enum class TrapType;

namespace ACTS
{
//! \brief Registers the saved-action handlers before the mind resumes.
void bind(KeeperAI& ai);
//! \brief Schedules marking tiles for digging.
void markDig(KeeperAI& ai, const std::vector<Tile*>& tiles, bool marked);
//! \brief Schedules building a room on the selected tiles.
void buildRoom(KeeperAI& ai, RoomType type, const std::vector<Tile*>& tiles);
//! \brief Schedules selling room tiles.
void sellRoomTiles(KeeperAI& ai, const std::vector<Tile*>& tiles);
//! \brief Schedules building a trap on the selected tiles.
void buildTrap(KeeperAI& ai, TrapType type, const std::vector<Tile*>& tiles);
//! \brief Schedules selling trap tiles.
void sellTrapTiles(KeeperAI& ai, const std::vector<Tile*>& tiles);
//! \brief Schedules casting a spell on a tile.
void castSpell(KeeperAI& ai, SpellType type, Tile* tile);
//! \brief Schedules casting a spell on a creature.
void castSpell(KeeperAI& ai, SpellType type, Creature* creature);
//! \brief Schedules picking up a creature.
void pickUp(KeeperAI& ai, Creature* creature);
//! \brief Schedules dropping the held creature on a tile.
void drop(KeeperAI& ai, Tile* tile);
//! \brief Schedules picking up and dropping a creature.
void moveCreature(KeeperAI& ai, Creature* creature, Tile* tile);
//! \brief Schedules slapping a creature.
void slap(KeeperAI& ai, Creature* creature);
//! \brief Schedules removing a call-to-war banner.
void removeBanner(KeeperAI& ai, Tile* tile);
//! \brief Schedules changing a room setting using its server request.
void setRoomSetting(KeeperAI& ai, Room* room, ODPacket& packet);
//! \brief Schedules changing the research queue.
void setResearch(KeeperAI& ai, const std::vector<SkillType>& skills);
//! \brief Schedules using a stored special.
void useSpecial(KeeperAI& ai, GiftBoxType type);
//! \brief Schedules a merchant purchase using its server request.
void merchantBuy(KeeperAI& ai, ODPacket& packet);
}

#endif // AIACTIONS_H
