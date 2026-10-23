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

#include "renderscene/RenderSceneMenu.h"

#include "camera/CameraManager.h"
#include "render/RenderManager.h"
#include "renderscene/RenderSceneGroup.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"

#include <OgreMaterialManager.h>
#include <OgreNode.h>
#include <OgreRectangle2D.h>
#include <OgreSceneManager.h>
#include <OgreSceneNode.h>

#include <CEGUI/System.h>
#include <CEGUI/GUIContext.h>
#include <CEGUI/MouseCursor.h>
#include <CEGUI/widgets/ButtonBase.h>
#include <CEGUI/widgets/FrameWindow.h>

#include <algorithm>
#include <cmath>
#include <sstream>

//! Scene node holding the full screen background rectangle created by the render manager.
static const std::string BACKGROUND_NODE_NAME = "Background";
//! Material used by the background rectangle outside of the menus.
static const std::string DEFAULT_BACKGROUND_MATERIAL = "Background";
//! Resource group shared by the world background and menu assets.
static const std::string BACKGROUND_RESOURCE_GROUP = "Graphics";
//! Configured overview destination and outside-arrival path names.
static const std::string OVERVIEW_PLACE = "overview";
static const std::string ARRIVAL_PATH = "arrival";
//! Camera metadata is kept outside the existing native scene groups.
static const std::string CAMERA_SECTION = "[MenuCamera]";
static const std::string CAMERA_SECTION_END = "[/MenuCamera]";
//! Permitted authored flight durations in interface seconds.
static const Ogre::Real MIN_FLIGHT_DURATION = 1.5f;
static const Ogre::Real MAX_FLIGHT_DURATION = 2.5f;

//! \brief Returns the full screen background rectangle of the scene.
static Ogre::Rectangle2D* getBackgroundRectangle(RenderManager& renderManager)
{
    return static_cast<Ogre::Rectangle2D*>(
        renderManager.getSceneManager()->getSceneNode(BACKGROUND_NODE_NAME)->getAttachedObject(0));
}

//! \brief Creates an inactive parsed menu with no settled destination.
RenderSceneMenu::RenderSceneMenu()
{
}

//! \brief Deletes parsed commands after their owner has released the live scene.
RenderSceneMenu::~RenderSceneMenu()
{
    for(RenderSceneGroup* sceneGroup : mSceneGroups)
        delete sceneGroup;

    mSceneGroups.clear();
}

//! \brief Broadcasts a scripted synchronization event to all scene groups.
void RenderSceneMenu::dispatchSyncPost(const std::string& event)
{
    for(RenderSceneGroup* sceneGroup : mSceneGroups)
        sceneGroup->notifySyncPost(event);
}

//! \brief Instantiates native scene groups and selects the authored overview without picture overlays.
void RenderSceneMenu::resetMenu(CameraManager& cameraManager, RenderManager& renderManager)
{
    if(mActive)
        freeMenu(cameraManager, renderManager);
    if(cameraManager.getActiveCamera() == nullptr || cameraManager.getActiveCameraNode() == nullptr)
        return;
    if(!renderManager.isKeeperHandVisible())
        renderManager.rrToggleHandSelectorVisibility();
    mSavedAmbient = renderManager.getSceneManager()->getAmbientLight();
    renderManager.getSceneManager()->setAmbientLight(Ogre::ColourValue::Black);
    getBackgroundRectangle(renderManager)->setVisible(false);
    mActive = true;
    for(RenderSceneGroup* sceneGroup : mSceneGroups)
        sceneGroup->reset(cameraManager, renderManager);
    mCurrentPlace = OVERVIEW_PLACE;
    std::map<std::string, CameraPose>::const_iterator overview = mCameraPoses.find(OVERVIEW_PLACE);
    if(overview != mCameraPoses.end())
        applyCameraPose(cameraManager, overview->second);
    updateMenu(cameraManager, renderManager, 0.0f);
}

//! \brief Frees animations before their entities and restores world lighting and the background rectangle.
void RenderSceneMenu::freeMenu(CameraManager& cameraManager, RenderManager& renderManager)
{
    mFlight.reset();
    mFlightPoses.clear();
    mFlightPlace.clear();
    mCurrentPlace.clear();
    renderManager.rrSetHandPose(false, false);
    if(mActive)
    {
        for(std::vector<RenderSceneGroup*>::reverse_iterator group = mSceneGroups.rbegin();
            group != mSceneGroups.rend(); ++group)
            (*group)->freeGroup(cameraManager, renderManager);
        renderManager.getSceneManager()->setAmbientLight(mSavedAmbient);
        mActive = false;
    }
    Ogre::Rectangle2D* background = getBackgroundRectangle(renderManager);
    background->setMaterial(Ogre::MaterialManager::getSingleton().getByName(DEFAULT_BACKGROUND_MATERIAL,
        BACKGROUND_RESOURCE_GROUP));
    background->setCorners(-1.0f, 1.0f, 1.0f, -1.0f);
    background->setVisible(true);
}

//! \brief Advances native scene animation and camera paths while preserving the existing hand hover rules.
void RenderSceneMenu::updateMenu(CameraManager& cameraManager, RenderManager& renderManager,
        Ogre::Real timeSinceLastFrame)
{
    if(!mActive)
        return;
    bool pointing = false;
    for(CEGUI::Window* window = CEGUI::System::getSingleton().getDefaultGUIContext().getWindowContainingMouse();
        window != nullptr; window = window->getParent())
    {
        if(window->isDisabled())
            break;
        if(CEGUI::ButtonBase* button = dynamic_cast<CEGUI::ButtonBase*>(window))
        {
            pointing = button->isHovering();
            break;
        }
        if(dynamic_cast<CEGUI::FrameWindow*>(window) != nullptr)
        {
            pointing = window->isHit(window->getGUIContext().getMouseCursor().getPosition());
            break;
        }
    }
    renderManager.rrSetHandPose(pointing, false);

    for(RenderSceneGroup* sceneGroup : mSceneGroups)
        sceneGroup->update(cameraManager, renderManager, timeSinceLastFrame);
    if(!mFlight.isActive())
        return;
    const bool arrived = mFlight.advance(timeSinceLastFrame);
    applyCameraPose(cameraManager, samplePath(mFlight.getProgress()));
    if(arrived)
        mCurrentPlace = mFlightPlace;
}

//! \brief Applies a pose in CameraMove's hierarchy without gameplay movement or map clamping.
void RenderSceneMenu::applyCameraPose(CameraManager& cameraManager, const CameraPose& pose)
{
    Ogre::SceneNode* node = cameraManager.getActiveCameraNode();
    if(cameraManager.getActiveCamera() == nullptr || node == nullptr || node->numChildren() == 0)
        return;
    cameraManager.move(CameraManager::fullStop);
    node->setPosition(pose.mPosition);
    node->resetOrientation();
    node->getChild(0)->setOrientation(pose.mOrientation);
}

//! \brief Samples the curved position path and interpolates adjacent authored view rotations.
RenderSceneMenu::CameraPose RenderSceneMenu::samplePath(Ogre::Real progress) const
{
    if(progress >= 1.0f)
        return mFlightPoses.back();
    const Ogre::Real coordinate = std::max(0.0f, progress) * (mFlightPoses.size() - 1);
    const size_t index = std::min(static_cast<size_t>(coordinate), mFlightPoses.size() - 2);
    const Ogre::Real fraction = coordinate - static_cast<Ogre::Real>(index);
    const Ogre::Real squared = fraction * fraction;
    const Ogre::Real cubed = squared * fraction;
    const CameraPose& first = mFlightPoses[index];
    const CameraPose& second = mFlightPoses[index + 1];
    const Ogre::Vector3& before = mFlightPoses[index == 0 ? 0 : index - 1].mPosition;
    const Ogre::Vector3& after = mFlightPoses[std::min(index + 2, mFlightPoses.size() - 1)].mPosition;
    CameraPose result;
    result.mPosition = 0.5f * ((2.0f * first.mPosition) + (-before + second.mPosition) * fraction
        + (2.0f * before - 5.0f * first.mPosition + 4.0f * second.mPosition - after) * squared
        + (-before + 3.0f * first.mPosition - 3.0f * second.mPosition + after) * cubed);
    result.mOrientation = Ogre::Quaternion::Slerp(fraction, first.mOrientation, second.mOrientation, true);
    return result;
}

//! \brief Validates every waypoint before starting a path from the actual current camera pose.
bool RenderSceneMenu::beginPath(CameraManager& cameraManager, const CameraPath& path,
    const std::string& destination)
{
    Ogre::SceneNode* node = cameraManager.getActiveCameraNode();
    if(!mActive || mFlight.isActive() || node == nullptr || node->numChildren() == 0
        || cameraManager.getActiveCamera() == nullptr || path.mWaypoints.empty())
        return false;
    std::vector<CameraPose> poses;
    CameraPose start;
    start.mPosition = node->getPosition();
    start.mOrientation = node->getOrientation() * node->getChild(0)->getOrientation();
    poses.push_back(start);
    for(const std::string& waypoint : path.mWaypoints)
    {
        std::map<std::string, CameraPose>::const_iterator pose = mCameraPoses.find(waypoint);
        if(pose == mCameraPoses.end())
            return false;
        poses.push_back(pose->second);
    }
    if(!mFlight.start(path.mDuration))
        return false;
    mFlightPoses.swap(poses);
    mFlightPlace = destination;
    return true;
}

//! \brief Starts the authored outside arrival, rejecting concurrent menu transitions.
bool RenderSceneMenu::startFlight(CameraManager& cameraManager)
{
    std::map<std::string, CameraPose>::const_iterator start = mCameraPoses.find(ARRIVAL_PATH);
    std::map<std::string, CameraPath>::const_iterator path = mCameraPaths.find(ARRIVAL_PATH);
    if(!mActive || mFlight.isActive() || start == mCameraPoses.end() || path == mCameraPaths.end())
        return false;
    applyCameraPose(cameraManager, start->second);
    return beginPath(cameraManager, path->second, OVERVIEW_PLACE);
}

//! \brief Starts a destination path or reverses its entry path when returning to the overview.
bool RenderSceneMenu::flyTo(CameraManager& cameraManager, const std::string& place)
{
    std::map<std::string, CameraPath>::const_iterator path = mCameraPaths.find(place);
    if(path == mCameraPaths.end() || mFlight.isActive() || !mActive)
        return false;
    CameraPath route = path->second;
    if(place == OVERVIEW_PLACE && mCurrentPlace != OVERVIEW_PLACE)
    {
        std::map<std::string, CameraPath>::const_iterator outward = mCameraPaths.find(mCurrentPlace);
        if(outward != mCameraPaths.end())
        {
            route.mWaypoints.clear();
            route.mDuration = outward->second.mDuration;
            const std::vector<std::string>& points = outward->second.mWaypoints;
            for(size_t index = points.size(); index > 1; --index)
                route.mWaypoints.push_back(points[index - 2]);
            route.mWaypoints.push_back(OVERVIEW_PLACE);
        }
    }
    return beginPath(cameraManager, route, place);
}

//! \brief Returns a named authored endpoint for the existing menu probe.
bool RenderSceneMenu::getCameraPose(const std::string& name, Ogre::Vector3& position,
    Ogre::Quaternion& orientation) const
{
    std::map<std::string, CameraPose>::const_iterator pose = mCameraPoses.find(name);
    if(pose == mCameraPoses.end())
        return false;
    position = pose->second.mPosition;
    orientation = pose->second.mOrientation;
    return true;
}

//! \brief Reads named camera metadata separately while retaining the native scene group parser.
void RenderSceneMenu::readSceneMenu(const std::string& fileName)
{
    if(!mSceneGroups.empty())
    {
        OD_LOG_ERR("Scene already loaded. Cannot read " + fileName);
        return;
    }

    std::stringstream definition;
    if(!Helper::readFile(fileName, definition, true))
    {
        OD_LOG_ERR("Couldn't read " + fileName);
        return;
    }

    std::stringstream groups;
    std::string line;
    bool cameraSection = false;
    while(Helper::readNextLineNotEmpty(definition, line))
    {
        if(line == CAMERA_SECTION || line == CAMERA_SECTION_END)
        {
            cameraSection = (line == CAMERA_SECTION);
            continue;
        }
        if(!cameraSection)
        {
            groups << line << '\n';
            continue;
        }
        std::stringstream command(line);
        std::string kind;
        std::string name;
        command >> kind >> name;
        if(kind == "Pose")
        {
            CameraPose pose;
            Ogre::Vector3 rotation = Ogre::Vector3::ZERO;
            if(!(command >> pose.mPosition.x >> pose.mPosition.y >> pose.mPosition.z
                >> rotation.x >> rotation.y >> rotation.z))
            {
                OD_LOG_ERR("Invalid menu camera pose: " + line);
                return;
            }
            pose.mOrientation = Ogre::Quaternion(Ogre::Degree(rotation.x), Ogre::Vector3::UNIT_X)
                * Ogre::Quaternion(Ogre::Degree(rotation.y), Ogre::Vector3::UNIT_Y)
                * Ogre::Quaternion(Ogre::Degree(rotation.z), Ogre::Vector3::UNIT_Z);
            mCameraPoses[name] = pose;
        }
        else if(kind == "Flight")
        {
            CameraPath path;
            if(!(command >> path.mDuration) || !std::isfinite(path.mDuration)
                || path.mDuration < MIN_FLIGHT_DURATION || path.mDuration > MAX_FLIGHT_DURATION)
            {
                OD_LOG_ERR("Invalid menu camera duration: " + line);
                return;
            }
            std::string waypoint;
            while(command >> waypoint)
                path.mWaypoints.push_back(waypoint);
            mCameraPaths[name] = path;
        }
        else
        {
            OD_LOG_ERR("Unknown menu camera command: " + line);
            return;
        }
    }
    while(groups.good())
    {
        RenderSceneGroup* group = RenderSceneGroup::load(groups);
        if(group == nullptr)
            break;

        group->setRenderSceneListener(this);
        mSceneGroups.emplace_back(group);
    }
}
