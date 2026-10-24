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

#ifndef CREATUREEFFECT_H
#define CREATUREEFFECT_H

#include <cstdint>
#include <istream>
#include <string>

class Creature;

class CreatureEffect
{
    friend class Creature;
public:
    // If particleEffectName is not empty, the corresponding particle effect will be
    // sent when the effect is added to the creature for nbTurnsEffect turns.
    CreatureEffect(double nbTurnsEffect, const std::string& particleEffectScript) :
        mNbTurnsEffect(nbTurnsEffect),
        mTurnFraction(1.0),
        mParticleEffectScript(particleEffectScript)
    {}

    virtual ~CreatureEffect()
    {}

    virtual const std::string& getEffectName() const = 0;

    //! \brief Turns the effect still lasts (may be a fraction of a turn, negative means it lasts until released)
    inline double getNbTurnsEffect() const
    { return mNbTurnsEffect; }

    //! \brief Share of the current turn that the effect is active, 1 except in its last turn when only a fraction of
    //! a turn was left. Per-turn amounts (damage, healing) are multiplied by it while the effect is applied.
    inline double getTurnFraction() const
    { return mTurnFraction; }

    inline const std::string& getParticleEffectScript() const
    { return mParticleEffectScript; }

    //! \brief Sets the id of the source of the effect (the id of the skill or spell that made it). A strength, speed or
    //! defense effect that is cast again by the same source while it still runs only refreshes the running one.
    inline void setSourceId(const std::string& sourceId)
    { mSourceId = sourceId; }

    //! \brief Returns the id of the source of the effect (see setSourceId), empty if it has none.
    inline const std::string& getSourceId() const
    { return mSourceId; }

    //! This function will be called when the effect is added to the creature
    virtual void startEffect(Creature& creature)
    {}

    //! This function will be called during the creature upkeep
    bool upkeepEffect(Creature& creature);

    //! This function will be called when the effect is released
    //!
    //! Note that this will not be called when a creature object is deleted.
    virtual void releaseEffect(Creature& creature)
    {}

    static void write(const CreatureEffect& effect, std::ostream& os);
    //! loads a CreatureEffect from the given stream. Note that the stream might contain
    //! more data than just the CreatureEffect. Thus, we should not use optional data
    //! by reading the stream and expecting an EOF. If the data may vary, we should
    //! write how many data there is and read them accordingly
    static CreatureEffect* load(std::istream& is);

    //! Writes the CreatureEffect to the stream
    virtual void exportToStream(std::ostream& os) const;
    virtual bool importFromStream(std::istream& is);

protected:
    //! This function will be called during the creature upkeep and should apply
    //! the wanted effect
    virtual void applyEffect(Creature& creature) = 0;
    CreatureEffect() :
        mNbTurnsEffect(0),
        mTurnFraction(1.0)
    {}

    //! Number of turns the effect lasts (a fraction of a turn is possible). Protected so that derived effects
    //! (Defector, Hexen Hen) can check the remaining time and end themselves early.
    double mNbTurnsEffect;

    //! Share of the current turn the effect is active (see getTurnFraction)
    double mTurnFraction;

private:
    std::string mParticleEffectScript;
    //! \brief Id of the skill or spell that made the effect (empty when unknown)
    std::string mSourceId;
};

#endif // CREATUREEFFECT_H
