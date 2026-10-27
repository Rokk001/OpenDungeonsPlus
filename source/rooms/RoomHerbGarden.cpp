#include "rooms/RoomHerbGarden.h"
#include "ODApplication.h"
#include "creatureaction/CreatureActionWalkToTile.h"
#include "entities/BuildingObject.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/HerbBundleEntity.h"
#include "entities/PotionDefinition.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "game/SkillManager.h"
#include "game/SkillType.h"
#include "gamemap/RoomObjectNavigation.h"
#include "gamemap/GameMap.h"
#include "rooms/RoomManager.h"
#include "utils/ConfigManager.h"
#include "utils/MakeUnique.h"
#include "utils/Random.h"
#include <algorithm>
#include <istream>
#include <ostream>

const RoomType RoomHerbGarden::mRoomType = RoomType::herbGarden;
const TileVisual RoomHerbGarden::mRoomVisual = TileVisual::herbGardenRoom;
namespace
{
//! \brief Registers the standard building, editor and save paths for this production room.
class RoomHerbGardenFactory : public RoomFactory
{
    //! \brief Returns the appended room type.
    RoomType getRoomType() const override { return RoomHerbGarden::mRoomType; }
    //! \brief Returns its tile visual.
    TileVisual getVisualType() const override { return RoomHerbGarden::mRoomVisual; }
    //! \brief Returns the configuration name.
    const std::string& getName() const override { static const std::string name = "HerbGarden"; return name; }
    //! \brief Returns the approved room label.
    const std::string& getNameReadable() const override { static const std::string name = "Herb garden"; return name; }
    //! \brief Reads the configured tile price.
    int getCostPerTile() const override { return ConfigManager::getSingleton().getRoomConfigInt32("HerbGardenCostPerTile"); }
    //! \brief Uses the existing room-placement validation.
    void checkBuildRoom(GameMap* map, const InputManager& input, InputCommand& command) const override
    { checkBuildRoomDefault(map, getRoomType(), input, command); }
    //! \brief Charges the existing treasury API and builds the selected tiles.
    bool buildRoom(GameMap* map, Player* player, ODPacket& packet) const override
    {
        std::vector<Tile*> tiles;
        if(!getRoomTilesDefault(tiles, map, player, packet))
            return false;
        return buildRoomOnTiles(map, player, tiles, false);
    }
    //! \brief Uses the editor's normal room validation.
    void checkBuildRoomEditor(GameMap* map, const InputManager& input, InputCommand& command) const override
    { checkBuildRoomDefaultEditor(map, getRoomType(), input, command); }
    //! \brief Builds the room through the editor's existing packet format.
    bool buildRoomEditor(GameMap* map, ODPacket& packet) const override
    { return buildRoomDefaultEditor(map, new RoomHerbGarden(map), packet); }
    //! \brief Restores the room through its virtual stream reader.
    Room* getRoomFromStream(GameMap* map, std::istream& stream) const override
    {
        RoomHerbGarden* room = new RoomHerbGarden(map);
        if(!Room::importRoomFromStream(*room, stream))
        {
            delete room;
            return nullptr;
        }
        return room;
    }
    //! \brief Creates an empty room for splitting and takeover.
    Room* createRoom(GameMap* map) const override { return new RoomHerbGarden(map); }
    //! \brief Builds from the AI's tiles, charging only when requested.
    bool buildRoomOnTiles(GameMap* map, Player* player, const std::vector<Tile*>& tiles, bool noFee) const override
    {
        const int32_t price = static_cast<int32_t>(tiles.size()) * getCostPerTile();
        if(!noFee && !map->withdrawFromTreasuries(price, player->getSeat()))
            return false;
        return buildRoomDefault(map, new RoomHerbGarden(map), player->getSeat(), tiles);
    }
};
static RoomRegister registration(new RoomHerbGardenFactory);
}

namespace
{
static const double HALF_GROWTH = 0.5;
static const Ogre::Real PLANT_HEIGHT = 0.09f;
static const std::string STAGES[] = {"Sprout", "Sapling", "Ripe"};
}

//! \brief Creates the garden's standard building state.
RoomHerbGarden::RoomHerbGarden(GameMap* map) : Room(map) { setMeshName("HerbGarden"); }

//! \brief Starts a room tile with persistent bed fields.
TileData* RoomHerbGarden::createTileData(Tile* tile) { return new HerbGardenTileData; }

//! \brief Replaces a former bed frame with the centre's trough.
BuildingObject* RoomHerbGarden::notifyActiveSpotCreated(ActiveSpotPlace place, Tile* tile)
{
    if(place != activeSpotCenter)
        return nullptr;
    removePlant(tile);
    removeBuildingObject(tile);
    return new BuildingObject(getGameMap(), *this, "WaterTrough", *tile, 0.0f, false);
}

//! \brief Removes only the additional plant entity, leaving the bed frame to the room.
void RoomHerbGarden::removePlant(Tile* tile)
{
    std::map<Tile*, BuildingObject*>::iterator found = mPlants.find(tile);
    if(found == mPlants.end())
        return;
    found->second->removeFromGameMap();
    found->second->deleteYourself();
    mPlants.erase(found);
}

//! \brief Maintains beds on non-centre tiles and rebuilds ground lamps between the beds.
void RoomHerbGarden::updateActiveSpots(GameMap* map)
{
    Room::updateActiveSpots(map);
    if(!getIsOnServerMap())
        return;
    std::vector<Tile*> removed;
    for(const std::pair<Tile* const, BuildingObject*>& plant : mPlants)
        if(std::find(mCoveredTiles.begin(), mCoveredTiles.end(), plant.first) == mCoveredTiles.end() ||
           std::find(mCentralActiveSpotTiles.begin(), mCentralActiveSpotTiles.end(), plant.first) != mCentralActiveSpotTiles.end())
            removed.push_back(plant.first);
    for(Tile* tile : removed)
        removePlant(tile);
    for(Tile* tile : mCoveredTiles)
    {
        HerbGardenTileData& data = *static_cast<HerbGardenTileData*>(mTileData[tile]);
        if(std::find(mCentralActiveSpotTiles.begin(), mCentralActiveSpotTiles.end(), tile) != mCentralActiveSpotTiles.end())
        {
            data.mHerb.clear();
            data.mGrowth = 0.0;
            data.mHarvest = 0.0;
            data.mStage = -1;
            continue;
        }
        if(getBuildingObjectFromTile(tile) == nullptr)
        {
            BuildingObject* bed = new BuildingObject(getGameMap(), *this, "HerbBed", *tile, 0.0f, false);
            addBuildingObject(tile, bed);
            bed->createMesh();
        }
        if(data.mHerb.empty())
            chooseHerb(data);
        syncPlant(tile, data);
    }
    syncLamps();
}

//! \brief Removes all supplementary ground lamps without affecting beds or their growth.
void RoomHerbGarden::removeLamps()
{
    for(BuildingObject* lamp : mLamps)
    {
        lamp->removeFromGameMap();
        lamp->deleteYourself();
    }
    mLamps.clear();
}

//! \brief Places floor lamps between adjacent beds, keeping at least two tiles between lamps.
void RoomHerbGarden::syncLamps()
{
    removeLamps();
    static const double LAMP_SPACING_SQUARED = 4.0;
    static const int OFFSETS[][2] = {{1, 0}, {0, 1}};
    for(Tile* tile : mCoveredTiles)
    {
        if(std::find(mCentralActiveSpotTiles.begin(), mCentralActiveSpotTiles.end(), tile) != mCentralActiveSpotTiles.end())
            continue;
        for(const int* offset : OFFSETS)
        {
            Tile* neighbour = getGameMap()->getTile(tile->getX()+offset[0], tile->getY()+offset[1]);
            if(neighbour == nullptr || neighbour->getCoveringRoom() != this ||
               std::find(mCentralActiveSpotTiles.begin(), mCentralActiveSpotTiles.end(), neighbour) != mCentralActiveSpotTiles.end())
                continue;
            const Ogre::Vector3 position(tile->getX()+offset[0]*0.5f, tile->getY()+offset[1]*0.5f, 0.0f);
            bool clear = true;
            for(BuildingObject* lamp : mLamps)
                if((lamp->getPosition()-position).squaredLength() < LAMP_SPACING_SQUARED)
                    clear = false;
            if(!clear)
                continue;
            BuildingObject* lamp = new BuildingObject(getGameMap(), *this, "MushroomLamp", tile,
                position.x, position.y, position.z, 0.0f, false);
            lamp->setSeat(getSeat());
            lamp->addToGameMap();
            lamp->createMesh();
            lamp->setPosition(position);
            mLamps.push_back(lamp);
        }
    }
}

//! \brief Chooses one legal herb uniformly, retaining the exact configured growth values.
void RoomHerbGarden::chooseHerb(HerbGardenTileData& data)
{
    std::vector<const HerbDefinition*> choices;
    for(const HerbDefinition& herb : ConfigManager::getSingleton().getHerbs())
        if(herb.mResearch == "none" || getSeat()->getSkillLevel(Skills::fromString(herb.mResearch)) > 0)
            choices.push_back(&herb);
    if(choices.empty())
        return;
    data.mHerb = choices[Random::Uint(0, static_cast<unsigned int>(choices.size()-1))]->mId;
    data.mGrowth = 0.0;
    data.mHarvest = 0.0;
    data.mStage = -1;
}

//! \brief Multiplies the herb's duration by the two applicable research entries.
double RoomHerbGarden::growthSeconds(const HerbGardenTileData& data) const
{
    const HerbDefinition* herb = ConfigManager::getSingleton().getHerb(data.mHerb);
    if(herb == nullptr)
        return 0.0;
    double duration = SkillManager::getResearchValue(getSeat(), SkillType::roomHerbGarden, herb->mGrowSeconds, "GrowTime");
    if(data.mHerb == "Sunthorn")
        duration = SkillManager::getResearchValue(getSeat(), SkillType::spellSunthornCultivation, duration, "GrowTime");
    return duration;
}

//! \brief Swaps the plant's actual mesh only at the configured half-grown and ripe boundaries.
void RoomHerbGarden::syncPlant(Tile* tile, HerbGardenTileData& data)
{
    const double duration = growthSeconds(data);
    int32_t stage = 0;
    if(duration > 0.0 && data.mGrowth >= duration)
        stage = 2;
    else if(duration > 0.0 && data.mGrowth >= duration*HALF_GROWTH)
        stage = 1;
    if(data.mHerb.empty() || (data.mStage == stage && mPlants.find(tile) != mPlants.end()))
    {
        if(mPlants.find(tile) != mPlants.end())
            mPlants[tile]->setSeat(getSeat());
        return;
    }
    removePlant(tile);
    BuildingObject* plant = new BuildingObject(getGameMap(), *this, data.mHerb+STAGES[stage],
        tile, static_cast<Ogre::Real>(tile->getX()), static_cast<Ogre::Real>(tile->getY()), PLANT_HEIGHT, 0.0f, false);
    plant->setSeat(getSeat());
    plant->addToGameMap();
    plant->createMesh();
    plant->setPosition(plant->getPosition());
    mPlants[tile] = plant;
    data.mStage = stage;
}

//! \brief Advances fractional growth seconds once per server turn, leaving ripe herbs intact.
void RoomHerbGarden::doUpkeep()
{
    Room::doUpkeep();
    if(mCoveredTiles.empty())
        return;
    for(Tile* tile : mCoveredTiles)
    {
        HerbGardenTileData& data = *static_cast<HerbGardenTileData*>(mTileData[tile]);
        if(data.mHerb.empty())
            continue;
        const double duration = growthSeconds(data);
        if(duration > 0.0)
            data.mGrowth = std::min(duration, data.mGrowth+1.0/ODApplication::turnsPerSecond);
        syncPlant(tile, data);
    }
}

//! \brief Finds a ripe bed that is not already assigned to another gardener.
Tile* RoomHerbGarden::findRipeBed() const
{
    for(Tile* tile : mCoveredTiles)
    {
        const HerbGardenTileData& data = *static_cast<const HerbGardenTileData*>(mTileData.at(tile));
        if(data.mHerb.empty() || growthSeconds(data) <= 0.0 || data.mGrowth < growthSeconds(data))
            continue;
        bool reserved = false;
        for(const std::pair<Creature* const, Tile*>& gardener : mGardeners)
            reserved = reserved || gardener.second == tile;
        if(!reserved)
            return tile;
    }
    return nullptr;
}

//! \brief Enforces the existing missing/zero-affinity work prohibition.
bool RoomHerbGarden::hasOpenCreatureSpot(Creature* creature)
{
    return creature != nullptr && creature->getSeat() == getSeat() &&
        creature->getDefinition()->getRoomAffinity(getType()).getEfficiency() > 0.0 && findRipeBed() != nullptr;
}

//! \brief Reserves one ripe bed before the standard job action starts approaching it.
bool RoomHerbGarden::addCreatureUsingRoom(Creature* creature)
{
    if(!hasOpenCreatureSpot(creature))
        return false;
    Tile* bed = findRipeBed();
    if(bed == nullptr || !Room::addCreatureUsingRoom(creature))
        return false;
    mGardeners[creature] = bed;
    return true;
}

//! \brief Releases work reservation while preserving the growing plant.
void RoomHerbGarden::removeCreatureUsingRoom(Creature* creature)
{
    Room::removeCreatureUsingRoom(creature);
    mGardeners.erase(creature);
}

//! \brief Works beside the actual bed and produces a bundle after the exact harvesting duration.
bool RoomHerbGarden::useRoom(Creature& creature, bool forced)
{
    std::map<Creature*, Tile*>::iterator found = mGardeners.find(&creature);
    if(found == mGardeners.end())
    {
        creature.popAction();
        return false;
    }
    Tile* tile = found->second;
    BuildingObject* bed = getBuildingObjectFromTile(tile);
    if(bed == nullptr || tile->getCoveringRoom() != this ||
       static_cast<const HerbGardenTileData*>(mTileData[tile])->mHerb.empty())
    {
        creature.popAction();
        return false;
    }
    std::vector<Ogre::Vector2> approach;
    if(!RoomObjectNavigation::workApproach(creature, *bed, Ogre::Vector2(tile->getX(), tile->getY()),
        Ogre::Vector2::ZERO, approach))
    {
        creature.popAction();
        return false;
    }
    if(!approach.empty())
    {
        creature.setWalkPath(EntityAnimation::walk_anim, EntityAnimation::idle_anim, true, true, approach, false, true);
        creature.pushAction(Utils::make_unique<CreatureActionWalkToTile>(creature));
        return false;
    }
    creature.setAnimationState(EntityAnimation::attack_anim, true);
    HerbGardenTileData& data = *static_cast<HerbGardenTileData*>(mTileData[tile]);
    data.mHarvest += 1.0/ODApplication::turnsPerSecond;
    // One work turn gives experience on the training hall level
    creature.receiveExp(ConfigManager::getSingleton().getRoomConfigDouble("JobXpPerTurn")
        * SkillManager::getResearchValue(getSeat(), SkillType::roomTrainingHall, 1.0, ResearchEffect::XpPerHit) * getDirtOutputFactor());
    if(data.mHarvest < ConfigManager::getSingleton().getRoomConfigDouble("HerbGardenHarvestSeconds"))
        return false;
    const uint32_t count = ConfigManager::getSingleton().getRoomConfigUInt32("HerbGardenBundlesPerBed");
    HerbBundleEntity* bundle = new HerbBundleEntity(getGameMap(), data.mHerb, count);
    bundle->setSeat(getSeat());
    bundle->addToGameMap();
    bundle->createMesh();
    bundle->setPosition(Ogre::Vector3(tile->getX(), tile->getY(), 0.0f));
    fireRoomSound(*tile, "HerbGarden/Rustle");
    chooseHerb(data);
    syncPlant(tile, data);
    creature.popAction();
    return false;
}

//! \brief Writes per-bed identity and fractional growth after the existing room-tile data.
void RoomHerbGarden::exportTileDataToStream(std::ostream& stream, Tile* tile, TileData* tileData) const
{
    Room::exportTileDataToStream(stream, tile, tileData);
    const HerbGardenTileData& data = *static_cast<const HerbGardenTileData*>(tileData);
    stream << "\t[Herb] " << (data.mHerb.empty() ? "none" : data.mHerb) << ' ' << data.mGrowth << " [/Herb]";
}

//! \brief Reads optional herb data, allowing existing room tile records without it.
bool RoomHerbGarden::importTileDataFromStream(std::istream& stream, Tile* tile, TileData* tileData)
{
    if(!Room::importTileDataFromStream(stream, tile, tileData))
        return false;
    std::string tag;
    if(!(stream >> tag))
    {
        stream.clear();
        return true;
    }
    if(tag != "[Herb]")
        return false;
    HerbGardenTileData& data = *static_cast<HerbGardenTileData*>(tileData);
    std::string herb;
    double growth = 0.0;
    std::string end;
    if(!(stream >> herb >> growth >> end) || end != "[/Herb]" || growth < 0.0)
        return false;
    if(herb != "none" && ConfigManager::getSingleton().getHerb(herb) == nullptr)
        return false;
    data.mHerb = herb == "none" ? "" : herb;
    data.mGrowth = growth;
    return true;
}

//! \brief Transfers plant visuals and recreates ground lamps when the absorbed beds change rooms.
void RoomHerbGarden::absorbRoom(Room* room)
{
    RoomHerbGarden* garden = static_cast<RoomHerbGarden*>(room);
    garden->removeLamps();
    mPlants.insert(garden->mPlants.begin(), garden->mPlants.end());
    garden->mPlants.clear();
    Room::absorbRoom(room);
}

//! \brief Moves plants with split bed tile data and rebuilds lamps for the resulting gardens.
void RoomHerbGarden::splitRoom(Room& room, const std::vector<Tile*>& tiles)
{
    RoomHerbGarden& garden = static_cast<RoomHerbGarden&>(room);
    removeLamps();
    for(Tile* tile : tiles)
    {
        std::map<Tile*, BuildingObject*>::iterator found = mPlants.find(tile);
        if(found == mPlants.end())
            continue;
        garden.mPlants[tile] = found->second;
        mPlants.erase(found);
    }
}

//! \brief Removes supplementary plants and ground lamps before the base room removes its furniture.
void RoomHerbGarden::removeFromGameMap(GameMap* map)
{
    removeLamps();
    while(!mPlants.empty())
        removePlant(mPlants.begin()->first);
    Room::removeFromGameMap(map);
}
