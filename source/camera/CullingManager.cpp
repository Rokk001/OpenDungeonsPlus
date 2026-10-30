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

#include "camera/CullingManager.h"
#include "camera/CameraManager.h"
#include "entities/Tile.h"
#include "gamemap/GameMap.h"
#include "utils/VectorInt64.h"
#include "utils/LogManager.h"

#include <Ogre.h>
#include <OgreCamera.h>
#include <OgreRay.h>

#include <sstream>
#include <algorithm>

static const Ogre::Plane GROUND_PLANE(0, 0, 1, 0);

const double zoomFactorValue = 1.0565;

//! Height of the highest earth wall top (Dirt_fl_1111C.mesh reaches z = 1.543). At a steep view the
//! ground point below a visible wall top lies outside the ground footprint of the screen.
static const Ogre::Real WALL_TOP_HEIGHT = 1.55;
//! Half the diagonal of a tile: a tile with a visible part has its centre at most this far outside.
static const Ogre::Real TILE_HALF_DIAGONAL = 0.7072;

CullingManager::CullingManager(GameMap* gameMap, uint32_t cullingMask):
    mFirstIter(false),
    mGameMap(gameMap),
    mCullingMask(cullingMask),
    mCullTilesFlag(false)
{
}

void CullingManager::cullTiles(const std::vector<Ogre::Vector3>& ogreVectors)
{
    mOldWalk = mWalk;
    mWalk.mVertices.mMyArray.clear();
    for (int ii = 0 ; ii < 4 ; ++ii)
        mWalk.mVertices.mMyArray.push_back(VectorInt64(ogreVectors[ii]));

    // create a slope -- a set of left and right path

    const double zoomFactorValue = 1.0565;
    mWalk.mVertices.zoom(zoomFactorValue);
    mWalk.buildSlopes();
#ifdef DEBUG_CULLING
    OD_LOG_DBG(mOldWalk.debug());
    OD_LOG_DBG(mWalk.debug());
#endif // DEBUG_CULLING
    // reset index pointers to the begging of collections
    mOldWalk.prepareWalk();
    mWalk.prepareWalk();

    newBashAndSplashTiles(SHOW | HIDE);
}

void CullingManager::startTileCulling(Ogre::Camera* camera, const std::vector<Ogre::Vector3>& ogreVectors)
{
    showAllTiles(mGameMap);

    const std::vector<Ogre::Vector3> footprint = computeCullingFootprint(camera, ogreVectors);
    mWalk.mVertices.mMyArray.clear();
    for (int ii = 0 ; ii < 4 ; ++ii)
        mWalk.mVertices.mMyArray.push_back(VectorInt64(footprint[ii]));
    mWalk.mVertices.zoom(zoomFactorValue);    
    mWalk.buildSlopes();
    mOldWalk = mWalk;
    mOldWalk.prepareWalk();
    mWalk.prepareWalk();
    hideAllTiles();
    newBashAndSplashTiles(SHOW);

    mCullTilesFlag = true;
}


void CullingManager::stopTileCulling(const std::vector<Ogre::Vector3>& ogreVectors)
{
    mCullTilesFlag = false;
    mOldWalk = mWalk;
    mWalk.mVertices.mMyArray.clear();
    for (int ii = 0 ; ii < 4 ; ++ii)
        mWalk.mVertices.mMyArray.push_back(VectorInt64(ogreVectors[ii]));

    // create a slope -- a set of left and rigth path

    mWalk.mVertices.zoom(zoomFactorValue);    
    mWalk.buildSlopes();

    OD_LOG_DBG(mOldWalk.debug());
    OD_LOG_DBG(mWalk.debug());

    // reset index pointers to the begging of collections
    mOldWalk.prepareWalk();
    mWalk.prepareWalk();

    newBashAndSplashTiles(HIDE);
    showAllTiles(mGameMap);
}

void CullingManager::hideAllTiles(void)
{
    OD_LOG_INF("starting to hide all game tiles"); 
    for (int jj = 0; jj < mGameMap->getMapSizeY() ; ++jj)
    {
        for (int ii = 0; ii < mGameMap->getMapSizeX(); ++ii)
        {
            Tile* tile = mGameMap->getTile(ii, jj);
            tile->setTileCullingFlags(mCullingMask, false);
        }
    }
    OD_LOG_INF("done hiding all game tiles");
}

void CullingManager::showAllTiles(GameMap* gameMap)
{
    for (int jj = 0; jj < gameMap->getMapSizeY() ; ++jj)
    {
        for (int ii = 0; ii < gameMap->getMapSizeX(); ++ii)
        {
            Tile* tile = gameMap->getTile(ii, jj);
            tile->setTileCullingFlags(mCullingMask, true);
        }
    }
}

void CullingManager::newBashAndSplashTiles(uint32_t mode)
{
    int64_t xxLeftOld = mOldWalk.getTopLeftVertex().x;
    int64_t xxRightOld = mOldWalk.getTopRightVertex().x;
    int64_t xxLeft = mWalk.getTopLeftVertex().x;
    int64_t xxRight = mWalk.getTopRightVertex().x;
    int64_t xxp, yyp;
    std::stringstream ss;
    int64_t bb = ((std::min(mWalk.getBottomLeftVertex().y, mOldWalk.getBottomRightVertex().y) >> VectorInt64::PRECISION_DIGITS) - 2) << VectorInt64::PRECISION_DIGITS;    

    for (int64_t yy = ((std::max(mWalk.getTopLeftVertex().y, mOldWalk.getTopRightVertex().y  ) >> VectorInt64::PRECISION_DIGITS) + 2) << VectorInt64::PRECISION_DIGITS; yy >= bb; yy -= VectorInt64::UNIT)
    {
        mOldWalk.notifyOnMoveDown(yy);
        mWalk.notifyOnMoveDown(yy);
        xxLeft = mWalk.getCurrentXLeft(yy);
        xxLeftOld = mOldWalk.getCurrentXLeft(yy);
        xxRight = mWalk.getCurrentXRight(yy);
        xxRightOld = mOldWalk.getCurrentXRight(yy);
        int64_t mm = ((std::min(xxLeft, xxLeftOld) >> VectorInt64::PRECISION_DIGITS) << VectorInt64::PRECISION_DIGITS) ;

        if(std::min(xxLeft, xxLeftOld) < std::max(xxRight,xxRightOld))
        {
            for (int64_t xx = mm ; xx <= std::max(xxRight,xxRightOld); xx += VectorInt64::UNIT)
            {
                bool bash = (xx >= xxLeftOld && xx <= xxRightOld && (yy >= mOldWalk.getBottomLeftVertex().y) && yy <= mOldWalk.getTopLeftVertex().y);
                bool splash = (xx >= xxLeft && xx <= xxRight && (yy >= mWalk.getBottomLeftVertex().y) && yy <= mWalk.getTopLeftVertex().y);

                xxp = (xx >> VectorInt64::PRECISION_DIGITS);
                yyp = (yy >> VectorInt64::PRECISION_DIGITS);
                Tile* tile = mGameMap->getTile(xxp, yyp);
                if(bash && splash && (mode & HIDE) && (mode & SHOW))
                {
                    // Nothing
                }

                else if (bash && (mode & HIDE) && (tile != nullptr))
                {
                    tile->setTileCullingFlags(mCullingMask, false);
                }
                else if (splash && (mode & SHOW) && (tile != nullptr))
                {
                    tile->setTileCullingFlags(mCullingMask, true);
                }
            }
        }
    }
}

bool CullingManager::computeIntersectionPoints(Ogre::Camera* camera, std::vector<Ogre::Vector3>& ogreVectors)
{
    if(ogreVectors.size() != 4)
    {
        OD_LOG_ERR("Unexpected size for ogreVectors size=" + Helper::toString(ogreVectors.size()));
        return false;
    }

    const Ogre::Vector3* cameraVector = camera->getWorldSpaceCorners();
    for(int ii = 0 ; ii < 4; ++ii)
    {
        Ogre::Ray ray(cameraVector[ii], cameraVector[ii+4] - cameraVector[ii]);
        std::pair<bool, Ogre::Real> intersectionResult =  ray.intersects(GROUND_PLANE);
        if(intersectionResult.first)
            ogreVectors[ii]= (ray.getPoint(intersectionResult.second));
        else
        {
            // The ray points above the horizon (possession view, defeat view): use the floor point below
            // the far clip corner, so the culled area stays a superset of what is visible.
            ogreVectors[ii] = Ogre::Vector3(cameraVector[ii+4].x, cameraVector[ii+4].y, 0.0);
        }
    }
    return true;
}

void CullingManager::update(Ogre::Camera* camera, const std::vector<Ogre::Vector3>& ogreVectors)
{
    if(mCullTilesFlag)
        cullTiles(computeCullingFootprint(camera, ogreVectors));
}

std::vector<Ogre::Vector3> CullingManager::computeCullingFootprint(Ogre::Camera* camera,
    const std::vector<Ogre::Vector3>& groundVectors) const
{
    if(groundVectors.size() != 4)
        return groundVectors;

    // Points of the screen corners on the ground and on the wall top plane, seen from above.
    const Ogre::Plane wallTopPlane(Ogre::Vector3::UNIT_Z, WALL_TOP_HEIGHT);
    const Ogre::Vector3* cameraVector = camera->getWorldSpaceCorners();
    std::vector<Ogre::Vector2> points;
    Ogre::Vector2 centre = Ogre::Vector2::ZERO;
    for(int ii = 0; ii < 4; ++ii)
    {
        Ogre::Vector2 groundPoint(groundVectors[ii].x, groundVectors[ii].y);
        points.push_back(groundPoint);
        centre += groundPoint * 0.25f;
        Ogre::Ray ray(cameraVector[ii], cameraVector[ii+4] - cameraVector[ii]);
        std::pair<bool, Ogre::Real> intersectionResult = ray.intersects(wallTopPlane);
        if(intersectionResult.first)
        {
            Ogre::Vector3 wallTopPoint = ray.getPoint(intersectionResult.second);
            points.push_back(Ogre::Vector2(wallTopPoint.x, wallTopPoint.y));
        }
    }

    // Each side keeps the direction of the ground footprint and moves outwards until it passes
    // every ground and wall top point plus the tile margin.
    Ogre::Vector2 normals[4];
    Ogre::Real offsets[4];
    for(int ii = 0; ii < 4; ++ii)
    {
        Ogre::Vector2 start(groundVectors[ii].x, groundVectors[ii].y);
        Ogre::Vector2 side = Ogre::Vector2(groundVectors[(ii + 1) % 4].x, groundVectors[(ii + 1) % 4].y) - start;
        if(side.squaredLength() < 1e-8f)
            return groundVectors;
        Ogre::Vector2 normal = Ogre::Vector2(side.y, -side.x).normalisedCopy();
        if(normal.dotProduct(start - centre) < 0.0f)
            normal = -normal;
        Ogre::Real offset = normal.dotProduct(start);
        for(const Ogre::Vector2& point : points)
            offset = std::max(offset, normal.dotProduct(point));
        normals[ii] = normal;
        offsets[ii] = offset + TILE_HALF_DIAGONAL;
    }

    // Corner ii is where the side ending at it meets the side starting at it.
    std::vector<Ogre::Vector3> footprint(4);
    for(int ii = 0; ii < 4; ++ii)
    {
        const Ogre::Vector2& n1 = normals[(ii + 3) % 4];
        const Ogre::Vector2& n2 = normals[ii];
        Ogre::Real det = n1.x * n2.y - n1.y * n2.x;
        if(std::abs(det) < 1e-6f)
            return groundVectors;
        Ogre::Real o1 = offsets[(ii + 3) % 4];
        Ogre::Real o2 = offsets[ii];
        footprint[ii] = Ogre::Vector3((o1 * n2.y - o2 * n1.y) / det, (n1.x * o2 - n2.x * o1) / det, 0.0f);
    }
    return footprint;
}

/*! \brief Sort two VectorInt64 p1 and p2  to satisfy p1 <= p2 according to
 * the value of X or Y coordinate, which depends on sortByX param.
 */
void CullingManager::sort(VectorInt64& p1, VectorInt64& p2, bool sortByX)
{
    if (sortByX)
    {
        if (p1.x > p2.x)
            std::swap(p1, p2);
    }
    else
    {
        if (p1.y > p2.y)
            std::swap(p1, p2);
    }
}

