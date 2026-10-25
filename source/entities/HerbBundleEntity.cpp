#include "entities/HerbBundleEntity.h"

#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/GameEntityType.h"
#include "entities/PotionDefinition.h"
#include "gamemap/GameMap.h"
#include "network/ODPacket.h"
#include "render/RenderManager.h"
#include "utils/ConfigManager.h"

#include <OgreEntity.h>
#include <OgreSceneNode.h>
#include <OgreSubEntity.h>
#include <algorithm>
#include <iomanip>
#include <istream>
#include <ostream>
#include <sstream>

namespace
{
static const std::string BUNDLE_MESH = "HerbBundle";
static const double COLOUR_CHANNEL = 255.0;
}

//! \brief Creates an original loose bundle on the authoritative map.
HerbBundleEntity::HerbBundleEntity(GameMap* map, const std::string& herb, uint32_t count) :
    RenderedMovableEntity(map, "HerbBundle_", BUNDLE_MESH, 0.0f, false), mHerb(herb), mCount(count) {}

//! \brief Creates an empty bundle for the existing entity factories.
HerbBundleEntity::HerbBundleEntity(GameMap* map) : RenderedMovableEntity(map), mCount(0) {}

//! \brief Returns the serialised herb-bundle entity kind.
GameEntityType HerbBundleEntity::getObjectType() const { return GameEntityType::herbBundleEntity; }

//! \brief Takes no more units than storage can accept, leaving any remainder on the floor.
uint32_t HerbBundleEntity::take(uint32_t maximum)
{
    const uint32_t taken = std::min(maximum, mCount);
    mCount -= taken;
    return taken;
}

//! \brief Lets own and enemy workers carry free bundles into their own available laboratory.
EntityCarryType HerbBundleEntity::getEntityCarryType(Creature* carrier)
{
    if(carrier == nullptr || !carrier->getDefinition()->isWorker() || !getIsOnMap() || mCount == 0 || getCarryLock(*carrier))
        return EntityCarryType::notCarryable;
    return EntityCarryType::herbBundle;
}

//! \brief Detaches a worker-carried bundle from the ground's entity list.
void HerbBundleEntity::notifyEntityCarryOn(Creature* carrier)
{
    removeEntityFromPositionTile();
    setIsOnMap(false);
}

//! \brief Reattaches a released bundle even when its carrier drops it on the original tile.
void HerbBundleEntity::notifyEntityCarryOff(const Ogre::Vector3& position)
{
    setPosition(position);
    addEntityToPositionTile();
}

//! \brief Releases a bundle only after its recipe units were transferred to storage.
void HerbBundleEntity::doUpkeep()
{
    if(mCount != 0)
        return;
    removeFromGameMap();
    deleteYourself();
}

//! \brief Saves recipe data in addition to the standard movable entity record.
void HerbBundleEntity::exportToStream(std::ostream& stream) const
{
    RenderedMovableEntity::exportToStream(stream);
    stream << mHerb << '\t' << mCount << '\t';
}

//! \brief Restores a known herb definition and a positive recipe-unit count.
bool HerbBundleEntity::importFromStream(std::istream& stream)
{
    if(!RenderedMovableEntity::importFromStream(stream))
        return false;
    std::string herb;
    uint32_t count = 0;
    if(!(stream >> herb >> count) || count == 0 || ConfigManager::getSingleton().getHerb(herb) == nullptr)
        return false;
    mHerb = herb;
    mCount = count;
    return true;
}

//! \brief Transfers the same recipe identity and count used by saves.
void HerbBundleEntity::exportToPacket(ODPacket& packet, const Seat* seat) const
{
    RenderedMovableEntity::exportToPacket(packet, seat);
    packet << mHerb << mCount;
}

//! \brief Adopts bundle-specific fields only when their entire payload is present.
void HerbBundleEntity::importFromPacket(ODPacket& packet)
{
    RenderedMovableEntity::importFromPacket(packet);
    std::string herb;
    uint32_t count = 0;
    if(packet >> herb >> count)
    {
        mHerb = herb;
        mCount = count;
    }
}

//! \brief Uses the existing tinted-material cache for the definition's exact RGB colour.
void HerbBundleEntity::createMeshLocal(NodeType type)
{
    RenderedMovableEntity::createMeshLocal(type);
    if(getIsOnServerMap() || getEntityNode() == nullptr || getEntityNode()->numAttachedObjects() == 0)
        return;
    const HerbDefinition* herb = ConfigManager::getSingleton().getHerb(mHerb);
    if(herb == nullptr)
        return;
    uint32_t rgb = 0;
    std::istringstream colour(herb->mColour);
    if(!(colour >> std::hex >> rgb))
        return;
    const Ogre::ColourValue tint((rgb >> 16) / COLOUR_CHANNEL,
        ((rgb >> 8) & 255) / COLOUR_CHANNEL, (rgb & 255) / COLOUR_CHANNEL);
    Ogre::Entity* entity = dynamic_cast<Ogre::Entity*>(getEntityNode()->getAttachedObject(0));
    if(entity == nullptr)
        return;
    for(unsigned int index = 0; index < entity->getNumSubEntities(); ++index)
    {
        Ogre::SubEntity* part = entity->getSubEntity(index);
        part->setMaterialName(RenderManager::getSingleton().rrBuildTintedMaterial(part->getMaterialName(), tint));
    }
}
