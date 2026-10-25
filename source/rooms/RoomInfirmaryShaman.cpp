#include "rooms/RoomInfirmary.h"

#include "entities/InfirmaryShamanEntity.h"
#include "entities/Tile.h"
#include "gamemap/GameMap.h"

#include <iomanip>
#include <istream>
#include <limits>
#include <ostream>

//! \brief Creates one harmless figure at the saved position or the room's instrument table.
void RoomInfirmary::updateShaman()
{
    if(!getIsOnServerMap())
        return;
    if(mShaman != nullptr)
    {
        mShaman->setRoomName(getName());
        mShaman->setSeat(getSeat());
        return;
    }
    Tile* tile = getShamanSpawnTile();
    if(tile == nullptr)
        return;
    mShaman = new InfirmaryShamanEntity(getGameMap(), getName());
    mShaman->setSeat(getSeat());
    mShaman->addToGameMap();
    mShaman->createMesh();
    const Ogre::Vector2 position = mHasLoadedShamanPosition ? mLoadedShamanPosition
        : Ogre::Vector2(tile->getX(), tile->getY());
    mShaman->setPosition(Ogre::Vector3(position.x, position.y, 0.0));
    mShaman->setAnimationState("Idle", true);
    mHasLoadedShamanPosition = false;
}

//! \brief Removes the figure without affecting a creature or its treatment.
void RoomInfirmary::removeShaman()
{
    if(mShaman == nullptr)
        return;
    mShaman->removeFromGameMap();
    mShaman->deleteYourself();
    mShaman = nullptr;
}

//! \brief Plays the freely licensed rattle sound at the active pose.
void RoomInfirmary::playShamanRattle(Tile& tile)
{
    fireRoomSound(tile, "Infirmary/Rattle");
}

//! \brief Retains the figure position using enough digits for a lossless coordinate round-trip.
void RoomInfirmary::exportShamanToStream(std::ostream& stream) const
{
    if(mShaman == nullptr)
        return;
    const std::streamsize precision = stream.precision();
    stream << std::setprecision(std::numeric_limits<Ogre::Real>::max_digits10)
        << "InfirmaryShaman\t" << mShaman->getPosition().x << '\t' << mShaman->getPosition().y << '\n';
    stream.precision(precision);
}

//! \brief Accepts older room records without a figure and leaves following cot tags unread.
bool RoomInfirmary::importShamanFromStream(std::istream& stream)
{
    const std::istream::pos_type position = stream.tellg();
    std::string tag;
    if(!(stream >> tag) || tag != "InfirmaryShaman")
    {
        stream.clear();
        stream.seekg(position);
        return true;
    }
    if(!(stream >> mLoadedShamanPosition.x >> mLoadedShamanPosition.y))
        return false;
    mHasLoadedShamanPosition = true;
    return true;
}
