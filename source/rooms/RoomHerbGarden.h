#ifndef ROOMHERBGARDEN_H
#define ROOMHERBGARDEN_H

#include "rooms/Room.h"
#include <map>
#include <string>
#include <vector>

//! \brief A bed's persistent herb and growth, retained when room tiles change owner.
class HerbGardenTileData : public TileData
{
public:
    //! \brief Starts an empty bed with no work or rendered growth stage.
    HerbGardenTileData() : mGrowth(0.0), mHarvest(0.0), mStage(-1) {}
    //! \brief Copies the persistent state when the engine clones a room tile.
    explicit HerbGardenTileData(const HerbGardenTileData* data) : TileData(data),
        mHerb(data->mHerb), mGrowth(data->mGrowth), mHarvest(data->mHarvest), mStage(-1) {}
    //! \brief Preserves the bed's state while cloning.
    TileData* cloneTileData() const override { return new HerbGardenTileData(this); }
    //! \brief Herb definition and elapsed growth/harvest seconds; stage is presentation only.
    std::string mHerb;
    double mGrowth, mHarvest;
    int32_t mStage;
};

//! \brief Grows herbs on non-centre tiles and lets permitted gardeners harvest ripe beds.
class RoomHerbGarden : public Room
{
public:
    //! \brief Creates an empty garden.
    explicit RoomHerbGarden(GameMap* map);
    //! \brief Returns the appended garden room type.
    RoomType getType() const override { return mRoomType; }
    //! \brief Updates growing plants with the garden and Sunthorn research factors.
    void doUpkeep() override;
    //! \brief Reconciles beds and troughs after the existing active-spot calculation.
    void updateActiveSpots(GameMap* map = nullptr) override;
    //! \brief Releases supplementary plant visuals before removing the room.
    void removeFromGameMap(GameMap* map = nullptr) override;
    //! \brief Moves plant visuals along with absorbed bed tile data.
    void absorbRoom(Room* room) override;
    //! \brief Transfers plants with split or taken-over bed tiles.
    void splitRoom(Room& room, const std::vector<Tile*>& tiles) override;
    //! \brief Accepts only a permitted gardener when an unreserved ripe bed exists.
    bool hasOpenCreatureSpot(Creature* creature) override;
    //! \brief Reserves one ripe bed through the existing room-job mechanism.
    bool addCreatureUsingRoom(Creature* creature) override;
    //! \brief Releases the gardener's reservation without discarding plant growth.
    void removeCreatureUsingRoom(Creature* creature) override;
    //! \brief Harvests at the bed for the configured number of seconds.
    bool useRoom(Creature& creature, bool forced) override;
    static const RoomType mRoomType;
    static const TileVisual mRoomVisual;
protected:
    //! \brief Creates the bed state for a covered tile.
    TileData* createTileData(Tile* tile) override;
    //! \brief Places troughs only at centre spots.
    BuildingObject* notifyActiveSpotCreated(ActiveSpotPlace place, Tile* tile) override;
    //! \brief Saves the herb and growth on the corresponding room tile line.
    void exportTileDataToStream(std::ostream& stream, Tile* tile, TileData* data) const override;
    //! \brief Accepts old tile records without a herb-growth tag.
    bool importTileDataFromStream(std::istream& stream, Tile* tile, TileData* data) override;
private:
    //! \brief Returns the research-adjusted growth duration of a bed's herb.
    double growthSeconds(const HerbGardenTileData& data) const;
    //! \brief Returns an unreserved fully grown bed, or null.
    Tile* findRipeBed() const;
    //! \brief Picks uniformly among the herbs whose research gate is open.
    void chooseHerb(HerbGardenTileData& data);
    //! \brief Replaces only this tile's plant visual when its growth stage changes.
    void syncPlant(Tile* tile, HerbGardenTileData& data);
    //! \brief Removes the supplementary plant object of one bed.
    void removePlant(Tile* tile);
    //! \brief Rebuilds ground lamps between adjacent beds with two-tile spacing.
    void syncLamps();
    //! \brief Removes supplementary lamps before the garden changes ownership or disappears.
    void removeLamps();
    //! \brief Ground lamps are presentation only and are recreated from the covered beds.
    std::vector<BuildingObject*> mLamps;
    //! \brief Supplementary plant objects and gardener reservations, keyed by their actual tiles.
    std::map<Tile*, BuildingObject*> mPlants;
    std::map<Creature*, Tile*> mGardeners;
};

#endif
