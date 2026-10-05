/*
 *  Copyright (C) 2011-2016  OpenDungeons Team
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef ROOMHATCHERY_H
#define ROOMHATCHERY_H

#include "entities/ChickenEntity.h"
#include "rooms/HatcheryCycle.h"
#include "rooms/HatcheryRooster.h"
#include "rooms/Room.h"
#include "rooms/RoomType.h"

#include <map>

class Creature;
enum class TileVisual;

class RoomHatchery: public Room
{
public:
    RoomHatchery(GameMap* gameMap);

    ~RoomHatchery()
    {}

    RoomType getType() const override
    { return mRoomType; }

    void doUpkeep() override;
    bool hasOpenCreatureSpot(Creature* c) override;
    bool shouldStopUseIfHungrySleepy(Creature& creature, bool forced) override
    { return false; }
    bool shouldNotUseIfBadMood(Creature& creature, bool forced) override
    { return false; }

    bool useRoom(Creature& creature, bool forced) override;
    void handleCreatureUsingAbsorbedRoom(Creature& creature) override;

    void creatureDropped(Creature& creature) override;

    //! The rooster protests loudly (picked up by the keeper's hand): plays the angry cackle where he was.
    static void fireProtest(Tile& tile);

    void exportToStream(std::ostream& os) const override;
    bool importFromStream(std::istream& is) override;

    static const RoomType mRoomType;
    static const TileVisual mRoomVisual;
    
protected:
    BuildingObject* notifyActiveSpotCreated(ActiveSpotPlace place, Tile* tile) override;
    void notifyActiveSpotRemoved(ActiveSpotPlace place, Tile* tile) override;
private:
    //! Plays a hatchery animal sound (family below Rooms/, e.g. "Hatchery/Crow") where the animal is.
    void fireAnimalSound(const ChickenEntity& animal, const std::string& family);
    //! Creatures of the hatchery that are after a chicken (hungry, on their way to eat).
    void collectHungry(std::vector<Creature*>& hungry) const;
    //! Hens that peck, scratch and flutter now and then; they scatter cackling when a hungry creature comes close.
    void updateFlock(const std::vector<ChickenEntity*>& hens, bool night);
    //! Creatures of an enemy seat that stand on a tile of the hatchery.
    void collectEnemies(std::vector<Creature*>& enemies) const;
    //! True if a map light is within HatcheryCareLightRadius tiles of the hatchery.
    bool isLit() const;
    //! Claimed by the keeper, lit and free of enemies (see HatcheryCycle::wellCared).
    HatcheryCare getCare(const std::vector<Creature*>& enemies) const;
    //! Settings of the life cycle from the config, laying times scaled by the research.
    HatcheryCycleSettings getCycleSettings() const;
    //! Creates a hatchery animal at the given position.
    ChickenEntity* spawnAnimal(ChickenKind kind, const Ogre::Vector3& position, const HatcheryCycleSettings& settings);
    //! Lets a hen or a rooster come out of a coop. Returns false if no coop has a free place.
    bool spawnFromCoop(ChickenKind kind, const HatcheryCycleSettings& settings, uint32_t count = 1);

    //! Settings of the rooster, the day and the chick line from the config.
    RoosterSettings getRoosterSettings() const;
    //! Moves the rooster: perching, crowing, chasing a hen, guarding the flock, leading the chicks, sleeping.
    void updateRooster(ChickenEntity* rooster, const std::vector<ChickenEntity*>& hens,
        const std::vector<ChickenEntity*>& chicks, const RoosterSettings& settings);
    void beginRoosterMood(ChickenEntity* rooster, const RoosterPlan& plan);
    void actRoosterMood(ChickenEntity* rooster, const std::vector<ChickenEntity*>& hens,
        const RoosterSettings& settings, const Ogre::Vector2& threat);
    //! Sits the rooster on the roof of the nearest coop with the pose. Without coop he stays on the ground.
    void roostOnRoof(ChickenEntity* rooster, const std::string& pose, bool hopFromFar);
    void climbDown(ChickenEntity* rooster);
    //! The chicks follow the hen (or the rooster when he leads) in a line, at night they huddle under the hen.
    void updateChickLine(const std::vector<ChickenEntity*>& hens, const std::vector<ChickenEntity*>& chicks,
        ChickenEntity* rooster, bool night);
    //! A creature inside the hatchery that wants to eat chickens or is an enemy, close to the rooster.
    bool findThreat(const ChickenEntity& rooster, double radius, Ogre::Vector2& position) const;
    Tile* getNearestCoop(const Ogre::Vector2& position) const;
    Ogre::Vector2 getPerchSpot(const Tile& coopTile) const;
    //! A free place next to a coop, where an animal can stand after jumping down.
    bool getGroundSpot(const Tile& coopTile, Ogre::Vector2& spot) const;

    //! Grain on the floor: how full a tile is (0 = bare to HatcheryGrainLevels = full). Only tiles that are not full
    //! are kept, a tile that is not in the map is full. Hens that scratch take grain, it grows back over time.
    int32_t getGrainLevel(const Tile* tile) const;
    //! A hen scratches on the tile: with the chance HatcheryGrainEatPercent one level of grain is gone.
    void eatGrain(Tile* tile);
    //! Lets bare tiles grow grain again and tells the clients that see the hatchery how full its tiles are.
    void updateGrain();
    //! Sends the grain levels (cosmetic event hatcheryGrain) to every human player with sight on a tile of the room.
    void sendGrain();

    //! Grain on the floor: how full a tile is (0 = bare to HatcheryGrainLevels = full). Only tiles that are not full
    //! are kept, a tile that is not in the map is full. Hens that scratch take grain, it grows back over time.
    int32_t getGrainLevel(const Tile* tile) const;
    //! A hen scratches on the tile: with the chance HatcheryGrainEatPercent one level of grain is gone.
    void eatGrain(Tile* tile);
    //! Lets bare tiles grow grain again and tells the clients that see the hatchery how full its tiles are.
    void updateGrain();
    //! Sends the grain levels (cosmetic event hatcheryGrain) to every human player with sight on a tile of the room.
    void sendGrain();

    //! Turns until the rooster crows next
    uint32_t mCrowInterval;
    //! Turns the hatchery has been empty (no hen, chick or egg)
    uint32_t mCoopHenWait;
    //! Turns the hatchery has been without rooster
    uint32_t mCoopRoosterWait;
    //! Grain level of the tiles that are not full
    std::map<Tile*, int32_t> mGrain;
    //! The grain changed since the last message to the clients
    bool mGrainDirty;
    //! Turns since the last message because of a change, and since the last message of any kind
    uint32_t mGrainSyncWait;
    uint32_t mGrainResyncWait;
};

#endif // ROOMHATCHERY_H
