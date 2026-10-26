#ifndef MERCHANTENTITY_H
#define MERCHANTENTITY_H

#include "entities/RenderedMovableEntity.h"

//! \brief The seat's untargetable merchant figure, restricted to its merchant rooms.
class MerchantEntity : public RenderedMovableEntity
{
public:
    //! \brief Creates the figure for one seat, at its first table.
    MerchantEntity(GameMap* map, Seat* seat, const Ogre::Vector3& position);
    //! \brief Creates a client figure before its normal rendered packet is read.
    MerchantEntity(GameMap* map);
    //! \brief Clears the seat's weak figure reference on removal.
    ~MerchantEntity() override;
    //! \brief Returns the merchant entity type used for picking and packet loading.
    GameEntityType getObjectType() const override;
    //! \brief Adds the figure to normal rendered, movement and server-upkeep lists.
    void addToGameMap(GameMap* map = nullptr) override;
    //! \brief Removes the figure from all lists and its owner's reference.
    void removeFromGameMap(GameMap* map = nullptr) override;
    //! \brief Walks within its room, counts gold at tables and reacts to deals.
    void doUpkeep() override;
    //! \brief Plays the fixed two-second rubbing-hands pose after a deal.
    void onDeal();
    //! \brief Returns the standard rendered entity walking speed.
    double getMoveSpeed() const override;
    //! \brief Loads a client merchant from its existing rendered packet fields.
    static MerchantEntity* loadFromPacket(GameMap* map, ODPacket& packet);
    //! \brief The figure cannot be attacked.
    bool isAttackable(Tile* tile, Seat* seat) const override;
    //! \brief The figure cannot be picked up by the keeper.
    bool tryPickup(Seat* seat) override;

private:
    double mIdleTurns;
    double mDealTurns;
};

#endif // MERCHANTENTITY_H
