#ifndef GHOSTENTITY_H
#define GHOSTENTITY_H

#include "entities/RenderedMovableEntity.h"
#include <set>

class Creature;

//! \brief The persisted capture and lifetime phase of a ghost.
enum class GhostState : uint32_t
{
    rising, floating, beamed, boxed, dissolving
};

//! \brief An untouchable spirit that floats over open terrain and frightens timid creatures.
class GhostEntity : public RenderedMovableEntity
{
public:
    //! \brief Creates an unpublished ghost with all corpse identity, seat and position fields set.
    GhostEntity(GameMap* map, const Creature& corpse);
    //! \brief Creates an unpublished ghost for stream or packet loading.
    explicit GhostEntity(GameMap* map);
    //! \brief Releases any remaining server-side presentation effect records.
    ~GhostEntity() override;
    //! \brief Registers through the existing movable path and restores saved movement endpoints.
    void addToGameMap(GameMap* map = nullptr) override;
    //! \brief Returns the synchronized ghost entity type.
    GameEntityType getObjectType() const override;
    //! \brief Advances lifetime, presentation phases, wandering and fear on the server.
    void doUpkeep() override;
    //! \brief Advances movement and the client fade without removing entities in a frame callback.
    void update(Ogre::Real elapsed) override;
    //! \brief Converts configured tiles per second to the movement system's tiles per turn.
    double getMoveSpeed() const override;
    //! \brief Plays the dead class's Walk at half its authored rate.
    double getAnimationSpeedFactor() const override;
    //! \brief Moves a released boxed ghost and synchronizes the authoritative position.
    void teleport(const Ogre::Vector3& position);
    //! \brief Returns the dead creature's class.
    const std::string& getClassName() const { return mClassName; }
    //! \brief Returns the corpse identity used for revival.
    const std::string& getCreatureName() const { return mCreatureName; }
    //! \brief Returns the whole level contributed to ectoplasm or revival.
    uint32_t getLevel() const { return mLevel; }
    //! \brief Returns the lifetime left in fractional turns.
    double getLifeLeft() const { return mLifeLeft; }
    //! \brief Returns the current lifetime and capture phase.
    GhostState getState() const { return mState; }
    //! \brief Sets capture state, stopping autonomous movement and hiding boxed ghosts.
    void setState(GhostState state);
    //! \brief Applies the hunter's client-only shrink into its thrown capture box.
    void setCaptureProgress(double progress) { mCaptureProgress = progress; }
    //! \brief Returns the name of the hunter that reserved this ghost.
    const std::string& getAssignedHunter() const { return mAssignedHunter; }
    //! \brief Stores or releases the hunter reservation.
    void setAssignedHunter(const std::string& name);
    //! \brief Writes the exact ghost record followed by persisted presentation and movement counters.
    void exportToStream(std::ostream& stream) const override;
    //! \brief Restores the exact ghost phase, lifetime and optional runtime continuation.
    bool importFromStream(std::istream& stream) override;
    //! \brief Sends all identity and presentation fields to newly observing clients.
    void exportToPacket(ODPacket& packet, const Seat* seat) const override;
    //! \brief Restores the complete creation packet.
    void importFromPacket(ODPacket& packet) override;
    //! \brief Sends current phase, lifetime and hunter reservation through entity refresh.
    void exportToPacketForUpdate(ODPacket& packet, Seat* seat) override;
    //! \brief Applies a phase refresh to the existing client entity.
    void updateFromPacket(ODPacket& packet) override;
    //! \brief Creates a validated ghost from one saved record.
    static GhostEntity* loadFromStream(GameMap* map, std::istream& stream);
    //! \brief Creates a ghost from an entity creation packet.
    static GhostEntity* loadFromPacket(GameMap* map, ODPacket& packet);
protected:
    //! \brief Creates the creature-shaped mesh and restores its current ghost presentation.
    void createMeshLocal(NodeType type = NodeType::MTILES_NODE) override;
private:
    //! \brief Chooses a reachable non-full tile inside the configured Chebyshev square.
    void wander();
    //! \brief Scares eligible visible creatures once per flight.
    void scareCreatures();
    //! \brief Sends changed lifetime and state to current observers.
    void refresh();
    //! \brief Applies fade, rise, capture shrinking and boxed visibility to the client node.
    void updateLook();
    std::string mClassName;
    std::string mCreatureName;
    uint32_t mLevel;
    double mLifeLeft;
    GhostState mState;
    std::string mAssignedHunter;
    std::set<std::string> mScaredCreatures;
    double mStateTurns;
    double mHowlTurns;
    double mCaptureProgress = 0.0;
};
#endif
