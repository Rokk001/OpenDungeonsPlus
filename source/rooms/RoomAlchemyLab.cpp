#include "rooms/RoomAlchemyLab.h"
#include "ODApplication.h"
#include "creatureaction/CreatureActionUseRoom.h"
#include "creatureaction/CreatureActionWalkToTile.h"
#include "entities/BuildingObject.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/GameEntityType.h"
#include "entities/HerbBundleEntity.h"
#include "entities/ItemBagEntity.h"
#include "entities/ItemInstance.h"
#include "entities/PotionDefinition.h"
#include "entities/RenderedMovableEntity.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "game/SkillManager.h"
#include "game/SkillType.h"
#include "gamemap/RoomObjectNavigation.h"
#include "gamemap/GameMap.h"
#include "network/CosmeticEvent.h"
#include "network/ODServer.h"
#include "network/ServerNotification.h"
#include "rooms/RoomManager.h"
#include "rooms/RoomMerchant.h"
#include "rooms/RoomType.h"
#include "utils/ConfigManager.h"
#include <iterator>
#include "utils/MakeUnique.h"
#include "utils/Random.h"
#include <algorithm>
#include <cmath>
#include <istream>
#include <limits>
#include <ostream>

const RoomType RoomAlchemyLab::mRoomType = RoomType::alchemyLab;
const TileVisual RoomAlchemyLab::mRoomVisual = TileVisual::alchemyLabRoom;
namespace
{
//! \brief Registers the standard building, editor and save paths for this production room.
class RoomAlchemyLabFactory : public RoomFactory
{
    //! \brief Returns the appended room type.
    RoomType getRoomType() const override { return RoomAlchemyLab::mRoomType; }
    //! \brief Returns its tile visual.
    TileVisual getVisualType() const override { return RoomAlchemyLab::mRoomVisual; }
    //! \brief Returns the configuration name.
    const std::string& getName() const override { static const std::string name = "AlchemyLab"; return name; }
    //! \brief Returns the approved room label.
    const std::string& getNameReadable() const override { static const std::string name = "Alchemy lab"; return name; }
    //! \brief Reads the configured tile price.
    int getCostPerTile() const override { return ConfigManager::getSingleton().getRoomConfigInt32("AlchemyLabCostPerTile"); }
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
    { return buildRoomDefaultEditor(map, new RoomAlchemyLab(map), packet); }
    //! \brief Restores the room through its virtual stream reader.
    Room* getRoomFromStream(GameMap* map, std::istream& stream) const override
    {
        RoomAlchemyLab* room = new RoomAlchemyLab(map);
        if(!Room::importRoomFromStream(*room, stream))
        {
            delete room;
            return nullptr;
        }
        return room;
    }
    //! \brief Creates an empty room for splitting and takeover.
    Room* createRoom(GameMap* map) const override { return new RoomAlchemyLab(map); }
    //! \brief Builds from the AI's tiles, charging only when requested.
    bool buildRoomOnTiles(GameMap* map, Player* player, const std::vector<Tile*>& tiles, bool noFee) const override
    {
        const int32_t price = static_cast<int32_t>(tiles.size()) * getCostPerTile();
        if(!noFee && !map->withdrawFromTreasuries(price, player->getSeat()))
            return false;
        return buildRoomDefault(map, new RoomAlchemyLab(map), player->getSeat(), tiles);
    }
};
static RoomRegister registration(new RoomAlchemyLabFactory);
}

namespace
{
static const double BANG_MIN_SECONDS = 60.0;
static const double BANG_MAX_SECONDS = 120.0;
static const uint32_t LARGE_LEVEL = 20;
static const uint32_t MEDIUM_LEVEL = 10;

//! \brief Chooses only the recipe sizes allowed by at least one creature of this seat.
bool usableSize(const PotionDefinition& potion, uint32_t highestLevel)
{
    if(potion.getLevelMin() > highestLevel)
        return false;
    if(potion.getSize() == "Single")
        return true;
    if(highestLevel >= LARGE_LEVEL)
        return potion.getSize() == "Large";
    if(highestLevel >= MEDIUM_LEVEL)
        return potion.getSize() == "Medium";
    return potion.getSize() == "Small";
}
}

//! \brief Creates the empty laboratory without introducing any ingredient or recipe defaults.
RoomAlchemyLab::RoomAlchemyLab(GameMap* map) : Room(map),
    mBangSeconds(Random::Double(BANG_MIN_SECONDS, BANG_MAX_SECONDS))
{ setMeshName("AlchemyLab"); }

//! \brief Creates a fresh cauldron's persisted fields.
TileData* RoomAlchemyLab::createTileData(Tile* tile) { return new AlchemyLabTileData; }

//! \brief Uses the project's centre and wall furniture convention.
BuildingObject* RoomAlchemyLab::notifyActiveSpotCreated(ActiveSpotPlace place, Tile* tile)
{
    if(place == activeSpotCenter)
        return new BuildingObject(getGameMap(), *this, "Cauldron", *tile, 0.0f, false);
    Ogre::Real angle = 0.0f;
    if(place == activeSpotLeft)
        angle = 90.0f;
    else if(place == activeSpotRight)
        angle = 270.0f;
    else if(place == activeSpotBottom)
        angle = 180.0f;
    return new BuildingObject(getGameMap(), *this, "StillShelf", *tile, angle, false);
}

//! \brief Releases the brewer and preserves a departing cauldron's reserved batch.
void RoomAlchemyLab::notifyActiveSpotRemoved(ActiveSpotPlace place, Tile* tile)
{
    std::vector<Creature*> stopped;
    for(const std::pair<Creature* const, Tile*>& brewer : mBrewers)
        if(brewer.second == tile)
            stopped.push_back(brewer.first);
    for(Creature* creature : stopped)
        creature->clearActionQueue();
    if(place == activeSpotCenter)
        preserveBatch(tile);
    Room::notifyActiveSpotRemoved(place, tile);
}

//! \brief Sums real stored bundles, including all four herb kinds.
uint32_t RoomAlchemyLab::herbCount() const
{
    uint32_t count = 0;
    for(const std::pair<const std::string, uint32_t>& herb : mHerbs)
        count += herb.second;
    return count;
}

//! \brief Checks every ingredient against the unreserved stock.
bool RoomAlchemyLab::canBrew(const PotionDefinition& potion) const
{
    for(const std::pair<const std::string, uint32_t>& herb : potion.getHerbs())
    {
        std::map<std::string, uint32_t>::const_iterator found = mHerbs.find(herb.first);
        if(found == mHerbs.end() || found->second < herb.second)
            return false;
    }
    return true;
}

//! \brief Counts waiting finished potions on the laboratory floor for its fixed capacity.
uint32_t RoomAlchemyLab::finishedCount() const
{
    uint32_t count = 0;
    for(RenderedMovableEntity* entity : getGameMap()->getRenderedMovableEntities())
    {
        if(entity->getObjectType() != GameEntityType::itemBagEntity || !entity->getIsOnMap())
            continue;
        const ItemBagEntity* bag = static_cast<const ItemBagEntity*>(entity);
        Tile* tile = bag->getPositionTile();
        if(bag->getItem() != nullptr && !bag->getItem()->mPotionId.empty() &&
           tile != nullptr && tile->getCoveringRoom() == this)
            ++count;
    }
    return count;
}

//! \brief Counts only the seat's waiting lab and treasury bags, excluding merchant stock counted separately.
uint32_t RoomAlchemyLab::countWaitingPotion(GameMap& map, const Seat* seat, const std::string& id)
{
    uint32_t count = 0;
    for(RenderedMovableEntity* entity : map.getRenderedMovableEntities())
    {
        if(entity->getObjectType() != GameEntityType::itemBagEntity || !entity->getIsOnMap())
            continue;
        const ItemBagEntity* bag = static_cast<const ItemBagEntity*>(entity);
        Tile* tile = bag->getPositionTile();
        Room* room = tile == nullptr ? nullptr : tile->getCoveringRoom();
        if(room != nullptr && room->getSeat() == seat &&
           (room->getType() == RoomType::alchemyLab || room->getType() == RoomType::treasury) &&
           bag->getItem() != nullptr && bag->getItem()->mPotionId == id)
            ++count;
    }
    return count;
}

//! \brief Selects by lowest stock, most recent sales, then unchanged recipe-file order.
const PotionDefinition* RoomAlchemyLab::choosePotion() const
{
    uint32_t highestLevel = 0;
    for(Creature* creature : getGameMap()->getCreatures())
        if(creature->getSeat() == getSeat() && creature->isAlive())
            highestLevel = std::max(highestLevel, creature->getLevel());
    const PotionDefinition* chosen = nullptr;
    uint32_t lowestStock = std::numeric_limits<uint32_t>::max();
    uint32_t greatestSales = 0;
    for(const PotionDefinition& potion : ConfigManager::getSingleton().getPotions())
    {
        if(!usableSize(potion, highestLevel) || !canBrew(potion))
            continue;
        const std::string& kind = potion.getKind();
        if(getSeat()->getLabMode() == 1 && kind != "HealPercent" && kind != "ManaPercent")
            continue;
        if(getSeat()->getLabMode() == 2 && (kind == "HealPercent" || kind == "ManaPercent" ||
            kind == "FullRestore" || kind == "EndFreeze"))
            continue;
        const uint32_t stock = RoomMerchant::countPotion(*getGameMap(), getSeat(), potion.getId()) +
            countWaitingPotion(*getGameMap(), getSeat(), potion.getId());
        const uint32_t sold = RoomMerchant::recentPotionSales(*getGameMap(), getSeat(), potion.getId());
        if(chosen == nullptr || stock < lowestStock || (stock == lowestStock && sold > greatestSales))
        {
            chosen = &potion;
            lowestStock = stock;
            greatestSales = sold;
        }
    }
    return chosen;
}

//! \brief Applies only the configured laboratory brewing-time research.
double RoomAlchemyLab::brewSeconds(const PotionDefinition& potion) const
{
    return SkillManager::getResearchValue(getSeat(), SkillType::roomAlchemyLab, potion.getBrewSeconds(), "BrewTime");
}

//! \brief Finds a free or paused cauldron without overbooking a brewer.
Tile* RoomAlchemyLab::findCauldron() const
{
    if(finishedCount() >= ConfigManager::getSingleton().getRoomConfigUInt32("AlchemyLabPotionCapacity"))
        return nullptr;
    for(Tile* tile : mCentralActiveSpotTiles)
    {
        bool assigned = false;
        for(const std::pair<Creature* const, Tile*>& brewer : mBrewers)
            assigned = assigned || brewer.second == tile;
        if(assigned)
            continue;
        const AlchemyLabTileData& data = *static_cast<const AlchemyLabTileData*>(mTileData.at(tile));
        if(data.mReserved || choosePotion() != nullptr)
            return tile;
    }
    return nullptr;
}

//! \brief Enforces room affinity and actual ingredient/work availability.
bool RoomAlchemyLab::hasOpenCreatureSpot(Creature* creature)
{
    return creature != nullptr && creature->getSeat() == getSeat() &&
        creature->getDefinition()->getRoomAffinity(getType()).getEfficiency() > 0.0 && findCauldron() != nullptr;
}

//! \brief Assigns one cauldron through the engine's standard room-work action.
bool RoomAlchemyLab::addCreatureUsingRoom(Creature* creature)
{
    if(!hasOpenCreatureSpot(creature))
        return false;
    Tile* tile = findCauldron();
    if(tile == nullptr || !Room::addCreatureUsingRoom(creature))
        return false;
    mBrewers[creature] = tile;
    static_cast<AlchemyLabTileData*>(mTileData[tile])->mBrewer = creature->getName();
    return true;
}

//! \brief Pauses progress when a brewer leaves and releases its physical standing reservation.
void RoomAlchemyLab::removeCreatureUsingRoom(Creature* creature)
{
    std::map<Creature*, Tile*>::iterator found = mBrewers.find(creature);
    if(found != mBrewers.end())
    {
        static_cast<AlchemyLabTileData*>(mTileData[found->second])->mBrewer.clear();
        BuildingObject* object = getBuildingObjectFromTile(found->second);
        if(object != nullptr)
            object->setAnimationState("Triggered", false);
        mBrewers.erase(found);
    }
    Room::removeCreatureUsingRoom(creature);
}

//! \brief Consumes herbs when work actually starts and advances only an attending brewer.
bool RoomAlchemyLab::useRoom(Creature& creature, bool forced)
{
    std::map<Creature*, Tile*>::iterator found = mBrewers.find(&creature);
    if(found == mBrewers.end())
    {
        creature.popAction();
        return false;
    }
    Tile* tile = found->second;
    BuildingObject* cauldron = getBuildingObjectFromTile(tile);
    if(cauldron == nullptr || tile->getCoveringRoom() != this)
    {
        creature.popAction();
        return false;
    }
    std::vector<Ogre::Vector2> approach;
    if(!RoomObjectNavigation::workApproach(creature, *cauldron, Ogre::Vector2(tile->getX(), tile->getY()),
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
    if(finishedCount() >= ConfigManager::getSingleton().getRoomConfigUInt32("AlchemyLabPotionCapacity"))
        return false;
    AlchemyLabTileData& data = *static_cast<AlchemyLabTileData*>(mTileData[tile]);
    if(!data.mReserved)
    {
        const PotionDefinition* selected = choosePotion();
        if(selected == nullptr)
        {
            creature.popAction();
            return false;
        }
        data.mPotion = selected->getId();
        for(const std::pair<const std::string, uint32_t>& herb : selected->getHerbs())
            mHerbs[herb.first] -= herb.second;
        data.mReserved = true;
    }
    const PotionDefinition* potion = ConfigManager::getSingleton().getPotion(data.mPotion);
    if(potion == nullptr)
        return false;
    creature.setAnimationState(EntityAnimation::attack_anim, true);
    cauldron->setAnimationState("Triggered", true);
    data.mDone += 1.0/ODApplication::turnsPerSecond;
    // One work turn gives experience on the training hall level
    creature.receiveExp(ConfigManager::getSingleton().getRoomConfigDouble("JobXpPerTurn")
        * SkillManager::getResearchValue(getSeat(), SkillType::roomTrainingHall, 1.0, ResearchEffect::XpPerHit) * getDirtOutputFactor());
    if(data.mDone < brewSeconds(*potion))
        return false;
    ItemBagEntity* bag = new ItemBagEntity(getGameMap(), ItemInstance::createPotion(data.mPotion));
    bag->setSeat(getSeat());
    bag->addToGameMap();
    bag->createMesh();
    bag->setPosition(Ogre::Vector3(tile->getX(), tile->getY(), 0.0f));
    fireRoomSound(*tile, "AlchemyLab/Hiss");
    data.mPotion.clear();
    data.mDone = 0.0;
    data.mReserved = false;
    creature.popAction();
    return false;
}

//! \brief Accepts bundles from this seat's carriers while real herb storage has space.
bool RoomAlchemyLab::hasCarryEntitySpot(GameEntity* carried)
{
    return carried != nullptr && carried->getObjectType() == GameEntityType::herbBundleEntity &&
        herbCount() < ConfigManager::getSingleton().getRoomConfigUInt32("AlchemyLabHerbCapacity") &&
        !mCoveredTiles.empty();
}

//! \brief Uses the first covered laboratory tile as the normal carrier delivery destination.
Tile* RoomAlchemyLab::askSpotForCarriedEntity(GameEntity* carried)
{
    return hasCarryEntitySpot(carried) ? mCoveredTiles.front() : nullptr;
}

//! \brief Transfers accepted units, retaining a full laboratory's excess as a loose bundle.
void RoomAlchemyLab::notifyCarryingStateChanged(Creature* carrier, GameEntity* carried)
{
    if(carried == nullptr || carried->getObjectType() != GameEntityType::herbBundleEntity || carrier == nullptr ||
       carrier->getSeat() != getSeat() || !carried->getIsOnMap())
        return;
    Tile* delivered = carried->getPositionTile();
    if(delivered == nullptr || delivered->getCoveringRoom() != this)
        return;
    HerbBundleEntity& bundle = *static_cast<HerbBundleEntity*>(carried);
    const uint32_t capacity = ConfigManager::getSingleton().getRoomConfigUInt32("AlchemyLabHerbCapacity");
    const uint32_t available = capacity > herbCount() ? capacity-herbCount() : 0;
    mHerbs[bundle.getHerb()] += bundle.take(available);
    if(bundle.getCount() == 0)
    {
        bundle.removeFromGameMap();
        bundle.deleteYourself();
    }
}

//! \brief Keeps paused recipes intact and chooses the next recipe only from current state.
void RoomAlchemyLab::doUpkeep()
{
    Room::doUpkeep();
    resumeBatches();
    if(mCoveredTiles.empty())
        return;
    for(Tile* tile : mCentralActiveSpotTiles)
    {
        AlchemyLabTileData& data = *static_cast<AlchemyLabTileData*>(mTileData[tile]);
        if(!data.mReserved && data.mBrewer.empty())
        {
            const PotionDefinition* potion = choosePotion();
            data.mPotion = potion == nullptr ? "" : potion->getId();
        }
    }
    mBangSeconds -= 1.0/ODApplication::turnsPerSecond;
    if(mBangSeconds <= 0.0)
    {
        showBang();
        mBangSeconds = Random::Double(BANG_MIN_SECONDS, BANG_MAX_SECONDS);
    }
    Player* player = getSeat()->getPlayer();
    const std::vector<Room*> rooms = getGameMap()->getRoomsByTypeAndSeat(getType(), getSeat());
    if(player != nullptr && player->getIsHuman() && player->getLabWindowOpen() &&
       !rooms.empty() && rooms.front() == this)
        sendWindow(*getGameMap(), *player);
}

//! \brief Reports a visual accident without changing herbs, recipe progress or health.
void RoomAlchemyLab::showBang()
{
    std::vector<std::pair<Creature*, Tile*>> busy;
    for(const std::pair<Creature* const, Tile*>& brewer : mBrewers)
    {
        const AlchemyLabTileData& data = *static_cast<const AlchemyLabTileData*>(mTileData[brewer.second]);
        if(data.mReserved && data.mDone > 0.0)
            busy.push_back(std::make_pair(brewer.first, brewer.second));
    }
    if(busy.empty())
        return;
    const std::pair<Creature*, Tile*>& chosen = busy[Random::Uint(0, static_cast<unsigned int>(busy.size()-1))];
    CosmeticEvent event(CosmeticEventType::cauldronBang);
    event.mSubject = chosen.first->getName();
    event.mPosition = Ogre::Vector3(chosen.second->getX(), chosen.second->getY(), 0.0f);
    for(Seat* seat : getGameMap()->getSeats())
        if(seat->getPlayer() != nullptr && seat->getPlayer()->getIsHuman() && seat->hasVisionOnTile(chosen.second))
            ODServer::getSingleton().sendCosmeticEvent(seat->getPlayer(), event);
    fireRoomSound(*chosen.second, "AlchemyLab/Bang");
}

//! \brief Builds one complete owner-seat snapshot of all cauldrons and stored or loose herbs.
void RoomAlchemyLab::sendWindow(GameMap& map, Player& player)
{
    Seat* seat = player.getSeat();
    if(seat == nullptr)
        return;
    LabWindowData data;
    data.mMode = seat->getLabMode();
    for(Room* room : map.getRoomsByTypeAndSeat(RoomType::alchemyLab, seat))
    {
        RoomAlchemyLab* lab = static_cast<RoomAlchemyLab*>(room);
        for(const std::pair<const std::string, uint32_t>& herb : lab->mHerbs)
            data.mHerbs[herb.first] += herb.second;
        for(Tile* tile : lab->mCentralActiveSpotTiles)
        {
            const AlchemyLabTileData& state = *static_cast<const AlchemyLabTileData*>(lab->mTileData[tile]);
            LabCauldronRow row;
            const PotionDefinition* potion = ConfigManager::getSingleton().getPotion(state.mPotion);
            row.mPotion = potion == nullptr ? "-" : potion->getDisplay();
            row.mBrewer = state.mBrewer.empty() ? "-" : state.mBrewer;
            row.mRemaining = potion == nullptr ? 0.0 : std::max(0.0, lab->brewSeconds(*potion)-state.mDone);
            data.mCauldrons.push_back(row);
        }
    }
    for(RenderedMovableEntity* entity : map.getRenderedMovableEntities())
    {
        if(entity->getObjectType() != GameEntityType::herbBundleEntity || !entity->getIsOnMap())
            continue;
        const HerbBundleEntity* bundle = static_cast<const HerbBundleEntity*>(entity);
        Tile* tile = bundle->getPositionTile();
        Room* room = tile == nullptr ? nullptr : tile->getCoveringRoom();
        if(room != nullptr && room->getSeat() == seat && room->getType() == RoomType::herbGarden)
            data.mHerbs[bundle->getHerb()] += bundle->getCount();
    }
    ServerNotification notification(ServerNotificationType::labWindow, &player);
    notification.mPacket << data.mMode << static_cast<uint32_t>(data.mHerbs.size());
    for(const std::pair<const std::string, uint32_t>& herb : data.mHerbs)
        notification.mPacket << herb.first << herb.second;
    notification.mPacket << static_cast<uint32_t>(data.mCauldrons.size());
    for(const LabCauldronRow& row : data.mCauldrons)
        notification.mPacket << row.mPotion << row.mBrewer << row.mRemaining;
    ODServer::getSingleton().sendAsyncMsg(notification);
}

//! \brief Saves herb storage and paused batches after the room record; active batches stay on tile lines.
void RoomAlchemyLab::exportToStream(std::ostream& stream) const
{
    Room::exportToStream(stream);
    stream << "[HerbStock] " << mHerbs.size();
    for(const std::pair<const std::string, uint32_t>& herb : mHerbs)
        stream << ' ' << herb.first << ' ' << herb.second;
    stream << " [/HerbStock]\n";
    stream << "[PausedBrews] " << mPausedBatches.size();
    for(const std::pair<std::string, double>& batch : mPausedBatches)
        stream << ' ' << batch.first << ' ' << batch.second;
    stream << " [/PausedBrews]\n";
}

//! \brief Reads optional herb storage and paused batches without consuming the following room in older saves.
bool RoomAlchemyLab::importFromStream(std::istream& stream)
{
    if(!Room::importFromStream(stream))
        return false;
    const std::streampos position = stream.tellg();
    std::string tag;
    if(!(stream >> tag) || tag != "[HerbStock]")
    {
        stream.clear();
        stream.seekg(position);
        return true;
    }
    uint32_t count = 0;
    std::map<std::string, uint32_t> herbs;
    if(!(stream >> count) || count > ConfigManager::getSingleton().getHerbs().size())
        return false;
    for(uint32_t index = 0; index < count; ++index)
    {
        std::string herb;
        uint32_t amount = 0;
        if(!(stream >> herb >> amount) || ConfigManager::getSingleton().getHerb(herb) == nullptr)
            return false;
        herbs[herb] = amount;
    }
    if(!(stream >> tag) || tag != "[/HerbStock]")
        return false;
    mHerbs = herbs;
    const std::streampos pausedPosition = stream.tellg();
    if(!(stream >> tag) || tag != "[PausedBrews]")
    {
        stream.clear();
        stream.seekg(pausedPosition);
        return true;
    }
    if(!(stream >> count))
        return false;
    std::vector<std::pair<std::string, double>> batches;
    for(uint32_t index = 0; index < count; ++index)
    {
        std::string potion;
        double done = 0.0;
        if(!(stream >> potion >> done) || !std::isfinite(done) || done < 0.0 ||
           ConfigManager::getSingleton().getPotion(potion) == nullptr)
            return false;
        batches.push_back(std::make_pair(potion, done));
    }
    if(!(stream >> tag) || tag != "[/PausedBrews]")
        return false;
    mPausedBatches.insert(mPausedBatches.end(), batches.begin(), batches.end());
    resumeBatches();
    return true;
}

//! \brief Stores a cauldron's recipe, fractional seconds and brewer on its tile record.
void RoomAlchemyLab::exportTileDataToStream(std::ostream& stream, Tile* tile, TileData* tileData) const
{
    Room::exportTileDataToStream(stream, tile, tileData);
    const AlchemyLabTileData& data = *static_cast<const AlchemyLabTileData*>(tileData);
    stream << "\t[Cauldron] " << (data.mPotion.empty() ? "none" : data.mPotion) << ' ' << data.mDone
        << ' ' << (data.mBrewer.empty() ? "none" : data.mBrewer) << ' ' << data.mReserved << " [/Cauldron]";
}

//! \brief Loads cauldron progress and releases saved brewer names until a new work action reserves them.
bool RoomAlchemyLab::importTileDataFromStream(std::istream& stream, Tile* tile, TileData* tileData)
{
    if(!Room::importTileDataFromStream(stream, tile, tileData))
        return false;
    std::string tag;
    if(!(stream >> tag))
    {
        stream.clear();
        return true;
    }
    AlchemyLabTileData data;
    std::string end;
    if(tag != "[Cauldron]" || !(stream >> data.mPotion >> data.mDone >> data.mBrewer >> data.mReserved >> end) ||
       end != "[/Cauldron]" || data.mDone < 0.0 ||
       (data.mPotion != "none" && ConfigManager::getSingleton().getPotion(data.mPotion) == nullptr))
        return false;
    AlchemyLabTileData& destination = *static_cast<AlchemyLabTileData*>(tileData);
    destination.mPotion = data.mPotion == "none" ? "" : data.mPotion;
    destination.mBrewer.clear();
    destination.mDone = data.mDone;
    destination.mReserved = data.mReserved;
    return true;
}

//! \brief Keeps every ingredient and paused batch when laboratories merge, including storage overflow.
void RoomAlchemyLab::absorbRoom(Room* room)
{
    RoomAlchemyLab* lab = static_cast<RoomAlchemyLab*>(room);
    for(const std::pair<const std::string, uint32_t>& herb : lab->mHerbs)
        mHerbs[herb.first] += herb.second;
    lab->mHerbs.clear();
    mPausedBatches.insert(mPausedBatches.end(), lab->mPausedBatches.begin(), lab->mPausedBatches.end());
    lab->mPausedBatches.clear();
    Room::absorbRoom(room);
}

//! \brief Retains reserved ingredients and completed work when a cauldron or its tile disappears.
void RoomAlchemyLab::preserveBatch(Tile* tile)
{
    std::map<Tile*, TileData*>::iterator found = mTileData.find(tile);
    if(found == mTileData.end())
        return;
    AlchemyLabTileData& data = *static_cast<AlchemyLabTileData*>(found->second);
    if(!data.mReserved)
        return;
    mPausedBatches.push_back(std::make_pair(data.mPotion, data.mDone));
    data.mPotion.clear();
    data.mDone = 0.0;
    data.mReserved = false;
    data.mBrewer.clear();
}

//! \brief Resumes reserved batches on the next free cauldrons without charging their herbs twice.
void RoomAlchemyLab::resumeBatches()
{
    for(Tile* tile : mCentralActiveSpotTiles)
    {
        if(mPausedBatches.empty())
            break;
        BuildingObject* object = getBuildingObjectFromTile(tile);
        if(tile->getCoveringRoom() != this || object == nullptr || object->getMeshName() != "Cauldron")
            continue;
        AlchemyLabTileData& data = *static_cast<AlchemyLabTileData*>(mTileData[tile]);
        if(data.mReserved || !data.mBrewer.empty())
            continue;
        data.mPotion = mPausedBatches.front().first;
        data.mDone = mPausedBatches.front().second;
        data.mReserved = true;
        mPausedBatches.erase(mPausedBatches.begin());
    }
}

//! \brief Rehomes batches after the inherited layout rebuild leaves only the real current cauldrons.
void RoomAlchemyLab::updateActiveSpots(GameMap* map)
{
    Room::updateActiveSpots(map);
    if(!getIsOnServerMap())
        return;
    for(Tile* tile : mCoveredTiles)
        if(std::find(mCentralActiveSpotTiles.begin(), mCentralActiveSpotTiles.end(), tile) == mCentralActiveSpotTiles.end())
            preserveBatch(tile);
    resumeBatches();
}

//! \brief Saves a disappearing tile's batch before the inherited removal retires its tile data.
bool RoomAlchemyLab::removeCoveredTile(Tile* tile)
{
    if(std::find(mCoveredTiles.begin(), mCoveredTiles.end(), tile) == mCoveredTiles.end())
        return false;
    preserveBatch(tile);
    return Room::removeCoveredTile(tile);
}

//! \brief Uses the same original stock and tile denominator for every piece in a multi-part split.
void RoomAlchemyLab::checkForSplit()
{
    mSplitHerbs = mHerbs;
    mSplitTiles = mCoveredTiles.size();
    Room::checkForSplit();
    mSplitHerbs.clear();
    mSplitTiles = 0;
}

//! \brief Shares herbs by tile count and removes old copies of the batches that moved with cloned tiles.
void RoomAlchemyLab::splitRoom(Room& room, const std::vector<Tile*>& tiles)
{
    RoomAlchemyLab& lab = static_cast<RoomAlchemyLab&>(room);
    const size_t totalTiles = mSplitTiles == 0 ? mCoveredTiles.size()+tiles.size() : mSplitTiles;
    const std::map<std::string, uint32_t>& stock = mSplitTiles == 0 ? mHerbs : mSplitHerbs;
    if(totalTiles != 0)
        for(const std::pair<const std::string, uint32_t>& herb : stock)
        {
            const uint32_t share = static_cast<uint32_t>(static_cast<uint64_t>(herb.second)*tiles.size()/totalTiles);
            lab.mHerbs[herb.first] += share;
            mHerbs[herb.first] -= share;
        }
    std::vector<Creature*> stopped;
    for(const std::pair<Creature* const, Tile*>& brewer : mBrewers)
        if(std::find(tiles.begin(), tiles.end(), brewer.second) != tiles.end())
            stopped.push_back(brewer.first);
    for(Creature* creature : stopped)
        creature->clearActionQueue();
    for(Tile* tile : tiles)
    {
        AlchemyLabTileData& old = *static_cast<AlchemyLabTileData*>(mTileData[tile]);
        old.mPotion.clear();
        old.mBrewer.clear();
        old.mDone = 0.0;
        old.mReserved = false;
        static_cast<AlchemyLabTileData*>(lab.mTileData[tile])->mBrewer.clear();
    }
    if(mCoveredTiles.empty())
    {
        lab.mPausedBatches.insert(lab.mPausedBatches.end(), mPausedBatches.begin(), mPausedBatches.end());
        mPausedBatches.clear();
    }
}
