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

#include "render/TreasuryGoldMesh.h"

#include "rooms/TreasuryGoldLayer.h"

#include <OgreColourValue.h>
#include <OgreManualObject.h>
#include <OgreMeshManager.h>
#include <OgreSceneManager.h>
#include <OgreVector3.h>

#include <algorithm>
#include <cmath>
#include <map>
#include <utility>

namespace TreasuryGoldMesh
{
namespace
{
const std::string PileMaterial = "TreasuryGoldPile";
// Coins, gems and spilled coins lie in a second section of the pile mesh that takes its colour from the vertices
const std::string DetailMaterial = "TreasuryGoldDetail";
const std::string ReducedSuffix = "_r";
// Texture repeats per tile, so the coins stay small
const float TextureRepeat = 2.0f;
// Corners of a coin lying on top (a flat fan) and of a coin spilled at the edge
const int CoinSides = 6;
const int SpillSides = 4;
// Faces of a gem (an octahedron)
const int GemFaces = 8;

Detail currentDetail = Detail::full;

struct RegisteredPile
{
    std::string mEntityName;
    TreasuryGoldLayer::PileShape mShape;
    const void* mRoom;
    bool mReplacesClassicStack;
};

std::map<std::pair<int, int>, RegisteredPile> registeredPiles;
//! The level a tile had when its pile was last built, kept when the pile is removed so that the pile that
//! replaces it can tell whether gold was added or taken
std::map<std::pair<int, int>, int> lastLevels;

std::pair<int, int> tileOf(float x, float y)
{
    return std::make_pair(static_cast<int>(std::floor(x + 0.5f)), static_cast<int>(std::floor(y + 0.5f)));
}

//! A dent where gold was taken: the middle (u, v across the tile), the radius in tile units and the depth below
//! the surface at the middle
struct Dent
{
    float mU;
    float mV;
    float mRadius;
    float mDepth;
};

//! Surface height of the pile at (u, v), lowered by the dent (a smooth bowl, none outside its radius) and never
//! lower than the floor layer
float dentedHeight(const TreasuryGoldLayer::PileShape& shape, float u, float v, const Dent* dent)
{
    const float height = TreasuryGoldLayer::heightAt(shape, u, v);
    if(dent == nullptr || dent->mDepth <= 0.0f || dent->mRadius <= 0.0f)
        return height;

    const float du = u - dent->mU;
    const float dv = v - dent->mV;
    const float distance = std::sqrt(du * du + dv * dv);
    if(distance >= dent->mRadius)
        return height;

    const float bowl = 0.5f * (1.0f + std::cos(3.1415927f * distance / dent->mRadius));
    const float lowered = height - dent->mDepth * bowl;
    return lowered < 0.004f ? 0.004f : lowered;
}

Ogre::Vector3 pilePoint(const TreasuryGoldLayer::PileShape& shape, float u, float v, const Dent* dent = nullptr)
{
    return Ogre::Vector3(u - 0.5f, v - 0.5f, dentedHeight(shape, u, v, dent));
}

//! Normal of the pile surface from the neighbouring heights
Ogre::Vector3 pileNormal(const TreasuryGoldLayer::PileShape& shape, float u, float v, const Dent* dent = nullptr)
{
    const float step = 0.02f;
    const float dx = dentedHeight(shape, u + step, v, dent) - dentedHeight(shape, u - step, v, dent);
    const float dy = dentedHeight(shape, u, v + step, dent) - dentedHeight(shape, u, v - step, dent);
    Ogre::Vector3 normal(-dx / (2.0f * step), -dy / (2.0f * step), 1.0f);
    normal.normalise();
    return normal;
}

Ogre::ColourValue goldColour(float a, float b)
{
    const float shade = 0.8f + 0.3f * TreasuryGoldLayer::hash01(static_cast<int>(a * 1000.0f),
        static_cast<int>(b * 1000.0f));
    return Ogre::ColourValue(std::min(1.0f, shade), std::min(1.0f, 0.8f * shade), 0.3f * shade, 1.0f);
}

//! A flat disc (a fan of the given number of sides) lying on the surface
void addCoin(Ogre::ManualObject* object, const Ogre::Vector3& centre, const Ogre::Vector3& up, float radius,
    int sides, const Ogre::ColourValue& colour)
{
    Ogre::Vector3 axisA = up.crossProduct(Ogre::Vector3::UNIT_Y);
    if(axisA.squaredLength() < 0.0001f)
        axisA = up.crossProduct(Ogre::Vector3::UNIT_X);
    axisA.normalise();
    const Ogre::Vector3 axisB = up.crossProduct(axisA);

    const int baseIndex = static_cast<int>(object->getCurrentVertexCount());
    object->position(centre);
    object->normal(up);
    object->textureCoord(0.0f, 0.0f);
    object->colour(colour);
    for(int i = 0; i < sides; ++i)
    {
        const float angle = 6.2831853f * static_cast<float>(i) / static_cast<float>(sides);
        object->position(centre + (axisA * std::cos(angle) + axisB * std::sin(angle)) * radius);
        object->normal(up);
        object->textureCoord(0.0f, 0.0f);
        object->colour(colour);
    }
    for(int i = 0; i < sides; ++i)
        object->triangle(baseIndex, baseIndex + 1 + i, baseIndex + 1 + (i + 1) % sides);
}

//! A small cut gem (an octahedron)
void addGem(Ogre::ManualObject* object, const Ogre::Vector3& centre, float size, const Ogre::ColourValue& colour)
{
    const Ogre::Vector3 corners[6] = {
        Ogre::Vector3(0.0f, 0.0f, 1.3f), Ogre::Vector3(0.0f, 0.0f, -0.6f),
        Ogre::Vector3(1.0f, 0.0f, 0.0f), Ogre::Vector3(0.0f, 1.0f, 0.0f),
        Ogre::Vector3(-1.0f, 0.0f, 0.0f), Ogre::Vector3(0.0f, -1.0f, 0.0f)};
    const int baseIndex = static_cast<int>(object->getCurrentVertexCount());
    for(int i = 0; i < 6; ++i)
    {
        Ogre::Vector3 normal = corners[i];
        normal.normalise();
        object->position(centre + corners[i] * size);
        object->normal(normal);
        object->textureCoord(0.0f, 0.0f);
        object->colour(colour);
    }
    // Top, bottom, then the four side corners; counter-clockwise seen from outside
    const int top = baseIndex;
    const int bottom = baseIndex + 1;
    for(int i = 0; i < 4; ++i)
    {
        const int current = baseIndex + 2 + i;
        const int next = baseIndex + 2 + (i + 1) % 4;
        object->triangle(top, current, next);
        object->triangle(bottom, next, current);
    }
}

Ogre::ColourValue gemColour(int variant, int index)
{
    switch((variant + index) % 4)
    {
        case 0:
            return Ogre::ColourValue(0.9f, 0.1f, 0.15f, 1.0f);
        case 1:
            return Ogre::ColourValue(0.15f, 0.8f, 0.3f, 1.0f);
        case 2:
            return Ogre::ColourValue(0.2f, 0.4f, 0.95f, 1.0f);
        default:
            return Ogre::ColourValue(0.7f, 0.3f, 0.9f, 1.0f);
    }
}

//! Whether the shape carries any coins or gems (the detail section is left out when it does not)
bool hasDetail(const TreasuryGoldLayer::PileShape& shape)
{
    if(shape.mLevel == 0)
        return true;
    return TreasuryGoldLayer::topCoinCount(shape) > 0 || TreasuryGoldLayer::gemCount(shape) > 0
        || TreasuryGoldLayer::spillCoinsPerEdge(shape) > 0;
}

//! Single coins on top of the heap, scattered gems, coins spilled at the open edges; for a tile without
//! gold only a few coins on the bare floor
void addDetail(Ogre::ManualObject* object, const TreasuryGoldLayer::PileShape& shape, const Dent* dent = nullptr)
{
    const int seed = shape.mVariant * 17 + shape.mLevel;
    if(shape.mLevel == 0)
    {
        for(int i = 0; i < TreasuryGoldLayer::scatterCoins; ++i)
        {
            const float u = 0.15f + 0.7f * TreasuryGoldLayer::hash01(seed, 31 * i + 1);
            const float v = 0.15f + 0.7f * TreasuryGoldLayer::hash01(seed, 31 * i + 2);
            addCoin(object, Ogre::Vector3(u - 0.5f, v - 0.5f, 0.008f), Ogre::Vector3::UNIT_Z, 0.04f, CoinSides,
                goldColour(u, v));
        }
        return;
    }

    for(int i = 0; i < TreasuryGoldLayer::topCoinCount(shape); ++i)
    {
        const float u = 0.22f + 0.56f * TreasuryGoldLayer::hash01(seed, 7 * i + 3);
        const float v = 0.22f + 0.56f * TreasuryGoldLayer::hash01(seed, 7 * i + 4);
        Ogre::Vector3 up = pileNormal(shape, u, v, dent);
        // Each coin leans a little differently
        const float lean = 6.2831853f * TreasuryGoldLayer::hash01(seed, 7 * i + 5);
        up += Ogre::Vector3(std::cos(lean), std::sin(lean), 0.0f) * 0.35f;
        up.normalise();
        Ogre::Vector3 centre = pilePoint(shape, u, v, dent);
        centre.z += 0.014f;
        addCoin(object, centre, up, 0.045f, CoinSides, goldColour(u, v));
    }

    for(int i = 0; i < TreasuryGoldLayer::gemCount(shape); ++i)
    {
        const float u = 0.25f + 0.5f * TreasuryGoldLayer::hash01(seed, 11 * i + 8);
        const float v = 0.25f + 0.5f * TreasuryGoldLayer::hash01(seed, 11 * i + 9);
        Ogre::Vector3 centre = pilePoint(shape, u, v, dent);
        centre.z += 0.02f;
        addGem(object, centre, 0.028f, gemColour(shape.mVariant, i));
    }

    // Overflow: coins that rolled down to the foot of the pile at the open edges
    const int perEdge = TreasuryGoldLayer::spillCoinsPerEdge(shape);
    for(int edge = 0; edge < 4; ++edge)
    {
        if(perEdge == 0 || !TreasuryGoldLayer::edgeOpen(shape, edge))
            continue;
        for(int i = 0; i < perEdge; ++i)
        {
            const float along = (i == 0) ? 0.3f + 0.1f * TreasuryGoldLayer::hash01(seed, edge) :
                0.6f + 0.1f * TreasuryGoldLayer::hash01(seed, edge + 4);
            const float across = 0.92f;
            float u = along;
            float v = along;
            if(edge == 0)
                v = across;
            else if(edge == 1)
                u = across;
            else if(edge == 2)
                v = 1.0f - across;
            else
                u = 1.0f - across;
            Ogre::Vector3 centre = pilePoint(shape, u, v, dent);
            centre.z += 0.01f;
            addCoin(object, centre, pileNormal(shape, u, v, dent), 0.035f, SpillSides, goldColour(u, v));
        }
    }
}

//! Fills the sections of a pile: the surface (none for a tile without gold, which only has scattered coins) and
//! the coins and gems. With update the sections of a dynamic object are rewritten, the layout stays the same.
void fillPile(Ogre::ManualObject* object, const TreasuryGoldLayer::PileShape& shape, int divisions, bool withDetail,
    const Dent* dent, bool update)
{
    int section = 0;
    if(shape.mLevel > 0)
    {
        if(update)
            object->beginUpdate(section);
        else
            object->begin(PileMaterial, Ogre::RenderOperation::OT_TRIANGLE_LIST, "Graphics");
        ++section;

        for(int j = 0; j <= divisions; ++j)
        {
            for(int i = 0; i <= divisions; ++i)
            {
                const float u = static_cast<float>(i) / static_cast<float>(divisions);
                const float v = static_cast<float>(j) / static_cast<float>(divisions);
                object->position(pilePoint(shape, u, v, dent));
                object->normal(pileNormal(shape, u, v, dent));
                object->textureCoord(u * TextureRepeat, (1.0f - v) * TextureRepeat);
            }
        }

        const int row = divisions + 1;
        for(int j = 0; j < divisions; ++j)
        {
            for(int i = 0; i < divisions; ++i)
            {
                const int a = j * row + i;
                const int b = a + 1;
                const int c = a + row + 1;
                const int d = a + row;
                // Counter-clockwise seen from above
                object->triangle(a, b, c);
                object->triangle(a, c, d);
            }
        }

        object->end();
    }

    if(withDetail && hasDetail(shape))
    {
        if(update)
            object->beginUpdate(section);
        else
            object->begin(DetailMaterial, Ogre::RenderOperation::OT_TRIANGLE_LIST, "Graphics");
        addDetail(object, shape, dent);
        object->end();
    }
}

void buildPileMesh(Ogre::SceneManager* sceneManager, const std::string& resourceName,
    const TreasuryGoldLayer::PileShape& shape, int divisions, bool withDetail)
{
    Ogre::ManualObject* object = sceneManager->createManualObject();
    fillPile(object, shape, divisions, withDetail, nullptr, false);
    object->convertToMesh(resourceName, "Graphics");
    sceneManager->destroyManualObject(object);
}

// Divisions of the surface of a pile that is drawn with a dent (the same as the full mesh)
const int DentDivisions = 6;
}

Detail detailFromString(const std::string& text)
{
    if(text == "reduced")
        return Detail::reduced;
    if(text == "off")
        return Detail::off;
    return Detail::full;
}

const char* detailToString(Detail detail)
{
    switch(detail)
    {
        case Detail::reduced:
            return "reduced";
        case Detail::off:
            return "off";
        default:
            return "full";
    }
}

void setDetail(Detail detail)
{
    currentDetail = detail;
}

Detail getDetail()
{
    return currentDetail;
}

std::string prepareMesh(Ogre::SceneManager* sceneManager, const std::string& meshName)
{
    TreasuryGoldLayer::PileShape shape;
    if(!TreasuryGoldLayer::parseMeshName(meshName, shape))
        return meshName;

    // Without gold there is nothing but a few coins on the floor, and those only at the full detail
    if(shape.mLevel == 0 && currentDetail != Detail::full)
        return std::string();

    if(currentDetail == Detail::off)
        return TreasuryGoldLayer::classicMeshForLevel(shape.mLevel);

    const bool reduced = (currentDetail == Detail::reduced);
    const std::string name = reduced ? meshName + ReducedSuffix : meshName;
    if(!Ogre::MeshManager::getSingleton().resourceExists(name + ".mesh", "Graphics"))
        buildPileMesh(sceneManager, name + ".mesh", shape, reduced ? 2 : 6, !reduced);

    return name;
}

Ogre::ManualObject* createDentedPile(Ogre::SceneManager* sceneManager, const std::string& meshName, float u, float v,
    float radius)
{
    TreasuryGoldLayer::PileShape shape;
    if(sceneManager == nullptr || currentDetail != Detail::full || !TreasuryGoldLayer::parseMeshName(meshName, shape)
        || shape.mLevel <= 0)
        return nullptr;

    Ogre::ManualObject* object = sceneManager->createManualObject();
    object->setDynamic(true);
    Dent dent;
    dent.mU = u;
    dent.mV = v;
    dent.mRadius = radius;
    dent.mDepth = 0.0f;
    fillPile(object, shape, DentDivisions, true, &dent, false);
    return object;
}

void updateDentedPile(Ogre::ManualObject* object, const std::string& meshName, float u, float v, float radius,
    float depth)
{
    TreasuryGoldLayer::PileShape shape;
    if(object == nullptr || !TreasuryGoldLayer::parseMeshName(meshName, shape) || shape.mLevel <= 0)
        return;

    Dent dent;
    dent.mU = u;
    dent.mV = v;
    dent.mRadius = radius;
    dent.mDepth = depth;
    fillPile(object, shape, DentDivisions, true, &dent, true);
}

std::string pileNameForClassicStack(const std::string& meshName, float x, float y)
{
    if(currentDetail == Detail::off)
        return meshName;

    const int level = TreasuryGoldLayer::levelForClassicName(meshName);
    if(level <= 0)
        return meshName;

    // A plateau a little below the tile level: the ring tiles lie next to each other, so the edges stay low
    // enough to look like a heap and the lumps of the neighbours do not show a gap
    const std::pair<int, int> tile = tileOf(x, y);
    TreasuryGoldLayer::PileShape shape;
    shape.mLevel = level;
    shape.mVariant = (tile.first * 7 + tile.second * 13) % TreasuryGoldLayer::variantCount;
    for(int i = 0; i < 4; ++i)
        shape.mCorner[i] = level - 1;
    return TreasuryGoldLayer::meshName(shape);
}

int registerPile(const std::string& entityName, float x, float y, const std::string& meshName, const void* room,
    bool replacesClassicStack)
{
    if(currentDetail == Detail::off)
        return -1;

    RegisteredPile pile;
    if(!TreasuryGoldLayer::parseMeshName(meshName, pile.mShape))
        return -1;

    pile.mEntityName = entityName;
    pile.mRoom = room;
    pile.mReplacesClassicStack = replacesClassicStack;
    const std::pair<int, int> tile = tileOf(x, y);
    registeredPiles[tile] = pile;

    int previous = -1;
    std::map<std::pair<int, int>, int>::iterator last = lastLevels.find(tile);
    if(last != lastLevels.end())
        previous = last->second;
    lastLevels[tile] = pile.mShape.mLevel;
    return previous;
}

void unregisterPile(const std::string& entityName, float x, float y)
{
    std::map<std::pair<int, int>, RegisteredPile>::iterator it = registeredPiles.find(tileOf(x, y));
    if(it != registeredPiles.end() && it->second.mEntityName == entityName)
        registeredPiles.erase(it);
}

void clearPiles()
{
    registeredPiles.clear();
    lastLevels.clear();
}

bool replacesClassicStack(float x, float y)
{
    std::map<std::pair<int, int>, RegisteredPile>::const_iterator it = registeredPiles.find(tileOf(x, y));
    return it != registeredPiles.end() && it->second.mReplacesClassicStack;
}

void collectPiles(std::vector<FullPile>& piles, int minLevel)
{
    piles.clear();
    for(std::map<std::pair<int, int>, RegisteredPile>::const_iterator it = registeredPiles.begin();
        it != registeredPiles.end(); ++it)
    {
        if(it->second.mShape.mLevel < minLevel)
            continue;

        FullPile pile;
        pile.mX = it->first.first;
        pile.mY = it->first.second;
        pile.mRoom = it->second.mRoom;
        pile.mLevel = it->second.mShape.mLevel;
        piles.push_back(pile);
    }
}

void collectFullPiles(std::vector<FullPile>& piles)
{
    collectPiles(piles, TreasuryGoldLayer::maxLevel);
}

Glow glowOfPatch(int originX, int originY, int size)
{
    Glow glow;
    glow.mStrength = 0.0f;
    glow.mX = 0.0f;
    glow.mY = 0.0f;
    glow.mRoom = nullptr;
    if(currentDetail == Detail::off)
        return glow;

    float total = 0.0f;
    float strongest = 0.0f;
    for(int x = originX; x < originX + size; ++x)
    {
        for(int y = originY; y < originY + size; ++y)
        {
            std::map<std::pair<int, int>, RegisteredPile>::const_iterator it =
                registeredPiles.find(std::make_pair(x, y));
            if(it == registeredPiles.end())
                continue;

            // At the reduced detail only completely filled piles glow
            if(currentDetail == Detail::reduced && it->second.mShape.mLevel < TreasuryGoldLayer::maxLevel)
                continue;

            const float weight = TreasuryGoldLayer::glowWeight(it->second.mShape.mLevel);
            if(weight <= 0.0f)
                continue;
            total += weight;
            if(weight > strongest)
            {
                strongest = weight;
                glow.mRoom = it->second.mRoom;
            }
            glow.mX += weight * static_cast<float>(x);
            glow.mY += weight * static_cast<float>(y);
        }
    }

    if(total <= 0.0f)
        return glow;

    glow.mX /= total;
    glow.mY /= total;
    glow.mStrength = std::min(1.0f, total / static_cast<float>(size * size));
    return glow;
}

float surfaceHeight(float x, float y, int& level)
{
    level = 0;
    const std::pair<int, int> tile = tileOf(x, y);
    std::map<std::pair<int, int>, RegisteredPile>::const_iterator it = registeredPiles.find(tile);
    if(it == registeredPiles.end())
        return 0.0f;

    level = it->second.mShape.mLevel;
    const float u = x - static_cast<float>(tile.first) + 0.5f;
    const float v = y - static_cast<float>(tile.second) + 0.5f;
    return TreasuryGoldLayer::heightAt(it->second.mShape, u, v);
}
}
