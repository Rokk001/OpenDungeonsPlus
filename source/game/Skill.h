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

#ifndef RESEARCH_H
#define RESEARCH_H

#include <cstdint>
#include <vector>

class ODPacket;
class Player;

enum class SkillType;

class Skill
{
public:
    //! \brief Creates a skill.
    //! \param type The skill type
    //! \param neededSkillPoints Research points of level 1 (level 2 costs twice, level 3 four times that value)
    //! \param skillDepends The parents: each one is needed at level 1 (a parent the level does not allow counts as fulfilled)
    //! \param freeLevelOne True if every seat starts with level 1 of this skill, so level 1 costs no points
    Skill(SkillType type, int32_t neededSkillPoints, const std::vector<const Skill*>& skillDepends, bool freeLevelOne = false);
    virtual ~Skill()
    {}

    //! \brief Research points needed to reach the given level: level 1 is the tier cost (0 for a free level-one skill),
    //! level 2 is twice and level 3 four times the tier cost.
    int32_t getNeededSkillPoints(uint32_t level = 1) const;

    //! \brief True if every seat starts with level 1 of this skill
    inline bool isFreeLevelOne() const
    { return mFreeLevelOne; }

    inline SkillType getType() const
    { return mType; }

    //! \brief Returns the skills that must be done before this one, without the skills
    //! they depend on themselves.
    const std::vector<const Skill*>& getDependencies() const
    { return mSkillDepends; }

    //! \brief True if every parent is done or not allowed by the level (a parent the level does not allow counts as fulfilled)
    bool canBeSkilled(const std::vector<SkillType>& skillsDone, const std::vector<SkillType>& skillsNotAllowed) const;

    //! \brief Builds the dependency tree in dependencies with the skills required for this skill
    //! excluding skills already done in skillsDone including the skill itself. Note that the returned vector
    //! will contain needed skills ordered by feasible skills (the first one will have no needed dependencies,
    //! the second none other than the first, ...)
    //! Note 1: dependencies will not be added twice in dependencies even if there are 2 dependencies that depends
    //! on the same skill
    //! Note 2: if dependencies is not empty when calling this function, its content will be used like skills already
    //! done and not checked if available or correctly ordered. This function will only append additional required dependencies.
    //! Note 3: parents the level does not allow (skillsNotAllowed) count as fulfilled and are not added
    void buildDependencies(const std::vector<SkillType>& skillsDone, const std::vector<SkillType>& skillsNotAllowed,
        std::vector<SkillType>& dependencies) const;

    //! \brief Calls dependsOn for each SkillType
    bool dependsOn(const std::vector<SkillType>& skills) const;

    //! \brief Returns true if the skill is or depends on the given type and false otherwise
    bool dependsOn(SkillType type) const;

private:
    SkillType mType;

    int32_t mNeededSkillPoints;

    //! \brief List of the parents of this skill. All of them are needed (at level 1) before the Skill can be searched;
    //! a parent that the level does not allow counts as fulfilled.
    std::vector<const Skill*> mSkillDepends;

    //! \brief True if every seat starts with level 1 of this skill (level 1 costs no points)
    bool mFreeLevelOne;
};

#endif // RESEARCH_H
