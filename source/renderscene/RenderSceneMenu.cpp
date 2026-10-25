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
#include <OgreLight.h>
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
//! Firelight timing is separate from native render groups and camera metadata.
static const std::string FIRE_LIGHT_SECTION = "[MenuFireLights]";
static const std::string FIRE_LIGHT_SECTION_END = "[/MenuFireLights]";
//! Menu fill is parsed separately from native commands so world ambient can be restored.
static const std::string LIGHTING_SECTION = "[MenuLighting]";
static const std::string LIGHTING_SECTION_END = "[/MenuLighting]";
//! Two smooth waves avoid synchronized, rigid pulses while retaining positive light intensity.
static const Ogre::Real FIRE_PRIMARY_WEIGHT = 0.7f;
static const Ogre::Real FIRE_SECONDARY_WEIGHT = 0.3f;
static const Ogre::Real FIRE_SECONDARY_FREQUENCY = 2.37f;
static const Ogre::Real FIRE_SECONDARY_PHASE = 1.73f;
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

//! \brief Instantiates native groups with configured ambient, captures firelight and selects the overview.
void RenderSceneMenu::resetMenu(CameraManager& cameraManager, RenderManager& renderManager)
{
    if(mActive)
        freeMenu(cameraManager, renderManager);
    if(cameraManager.getActiveCamera() == nullptr || cameraManager.getActiveCameraNode() == nullptr)
        return;
    if(!renderManager.isKeeperHandVisible())
        renderManager.rrToggleHandSelectorVisibility();
    mSavedAmbient = renderManager.getSceneManager()->getAmbientLight();
    renderManager.getSceneManager()->setAmbientLight(mMenuAmbient);
    getBackgroundRectangle(renderManager)->setVisible(false);
    mActive = true;
    for(RenderSceneGroup* sceneGroup : mSceneGroups)
        sceneGroup->reset(cameraManager, renderManager);
    mFireTime = 0.0f;
    for(FireLight& fire : mFireLights)
    {
        fire.mLight = nullptr;
        if(!renderManager.getSceneManager()->hasLight(fire.mName))
        {
            OD_LOG_ERR("Missing configured menu firelight: " + fire.mName);
            continue;
        }
        fire.mLight = renderManager.getSceneManager()->getLight(fire.mName);
        fire.mDiffuse = fire.mLight->getDiffuseColour();
        fire.mSpecular = fire.mLight->getSpecularColour();
    }
    mCurrentPlace = OVERVIEW_PLACE;
    std::map<std::string, CameraPose>::const_iterator overview = mCameraPoses.find(OVERVIEW_PLACE);
    if(overview != mCameraPoses.end())
        applyCameraPose(cameraManager, overview->second);
    updateMenu(cameraManager, renderManager, 0.0f);
}

//! \brief Restores firelight baselines, frees native commands and restores the world background and lighting.
void RenderSceneMenu::freeMenu(CameraManager& cameraManager, RenderManager& renderManager)
{
    mFlight.reset();
    mFlightPoses.clear();
    mFlightPlace.clear();
    mCurrentPlace.clear();
    renderManager.rrSetHandPose(false, false);
    for(FireLight& fire : mFireLights)
    {
        if(fire.mLight == nullptr)
            continue;
        fire.mLight->setDiffuseColour(fire.mDiffuse);
        fire.mLight->setSpecularColour(fire.mSpecular);
        fire.mLight = nullptr;
    }
    mFireTime = 0.0f;
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

//! \brief Advances native animation, independent firelight and paths while preserving the hand hover rules.
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
    updateFireLights(timeSinceLastFrame);
    if(!mFlight.isActive())
        return;
    const bool arrived = mFlight.advance(timeSinceLastFrame);
    applyCameraPose(cameraManager, samplePath(mFlight.getProgress()));
    if(arrived)
        mCurrentPlace = mFlightPlace;
}

//! \brief Scales authored firelight colours by a bounded smooth waveform in interface time.
void RenderSceneMenu::updateFireLights(Ogre::Real elapsed)
{
    if(std::isfinite(elapsed) && elapsed > 0.0f)
        mFireTime += elapsed;
    for(const FireLight& fire : mFireLights)
    {
        if(fire.mLight == nullptr)
            continue;
        const Ogre::Real primary = fire.mFrequency * mFireTime + fire.mPhase;
        const Ogre::Real secondary = FIRE_SECONDARY_FREQUENCY * fire.mFrequency * mFireTime
            + FIRE_SECONDARY_PHASE * fire.mPhase;
        const Ogre::Real scale = 1.0f + fire.mAmplitude * (FIRE_PRIMARY_WEIGHT * std::sin(primary)
            + FIRE_SECONDARY_WEIGHT * std::sin(secondary));
        fire.mLight->setDiffuseColour(fire.mDiffuse * scale);
        fire.mLight->setSpecularColour(fire.mSpecular * scale);
    }
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

//! \brief Reads camera, ambient and firelight metadata while retaining the native scene group parser.
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
    bool fireSection = false;
    bool lightingSection = false;
    while(Helper::readNextLineNotEmpty(definition, line))
    {
        if(line == CAMERA_SECTION || line == CAMERA_SECTION_END)
        {
            cameraSection = (line == CAMERA_SECTION);
            continue;
        }
        if(line == FIRE_LIGHT_SECTION || line == FIRE_LIGHT_SECTION_END)
        {
            fireSection = (line == FIRE_LIGHT_SECTION);
            continue;
        }
        if(line == LIGHTING_SECTION || line == LIGHTING_SECTION_END)
        {
            lightingSection = (line == LIGHTING_SECTION);
            continue;
        }
        if(lightingSection)
        {
            std::stringstream command(line);
            std::string kind;
            Ogre::ColourValue ambient = Ogre::ColourValue::Black;
            if(!(command >> kind >> ambient.r >> ambient.g >> ambient.b) || kind != "Ambient"
                || !std::isfinite(ambient.r) || !std::isfinite(ambient.g) || !std::isfinite(ambient.b)
                || ambient.r < 0.0f || ambient.g < 0.0f || ambient.b < 0.0f)
            {
                OD_LOG_ERR("Invalid menu ambient definition: " + line);
                return;
            }
            mMenuAmbient = ambient;
            continue;
        }
        if(fireSection)
        {
            std::stringstream command(line);
            std::string kind;
            FireLight fire;
            if(!(command >> kind >> fire.mName >> fire.mAmplitude >> fire.mFrequency >> fire.mPhase)
                || kind != "Flicker" || !std::isfinite(fire.mAmplitude) || !std::isfinite(fire.mFrequency)
                || !std::isfinite(fire.mPhase) || fire.mAmplitude < 0.0f || fire.mAmplitude > 1.0f
                || fire.mFrequency <= 0.0f)
            {
                OD_LOG_ERR("Invalid menu firelight definition: " + line);
                return;
            }
            mFireLights.push_back(fire);
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
