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

#ifndef RENDERSCENEMENU_H
#define RENDERSCENEMENU_H

class CameraManager;
class RenderManager;
class RenderSceneGroup;

#include "render/MenuFlight.h"
#include "renderscene/RenderScene.h"

#include <OgrePrerequisites.h>
#include <OgreColourValue.h>
#include <OgreQuaternion.h>
#include <OgreVector3.h>

#include <map>
#include <string>
#include <vector>

//! \brief Stores a menu scene with its configured lighting, animation and camera paths.
class RenderSceneMenu : public RenderSceneListener
{
public:
    //! \brief Creates an inactive menu scene.
    RenderSceneMenu();
    //! \brief Deletes the parsed scene commands after their owner has freed the active scene.
    virtual ~RenderSceneMenu();

    //! \brief Sends a scripted synchronization event to every scene group.
    void dispatchSyncPost(const std::string& event) override;

    //! \brief Instantiates the configured scene and ambient lighting at the overview camera.
    void resetMenu(CameraManager& cameraManager, RenderManager& renderManager);
    //! \brief Releases active scene commands in reverse order and restores the world background.
    void freeMenu(CameraManager& cameraManager, RenderManager& renderManager);
    //! \brief Advances native scene animations, firelight, camera paths and the unchanged hand hover pose.
    void updateMenu(CameraManager& cameraManager, RenderManager& renderManager,
        Ogre::Real timeSinceLastFrame);
    //! \brief Loads scripted groups, camera paths, firelight timing and menu ambient from one file.
    void readSceneMenu(const std::string& fileName);

    //! \brief Starts the configured arrival from outside the fortress; rejects overlapping flights.
    bool startFlight(CameraManager& cameraManager);
    //! \brief Flies to a named menu place, reversing its entry route when returning to the overview.
    bool flyTo(CameraManager& cameraManager, const std::string& place);
    //! \brief Returns whether an arrival, outward or return flight is active.
    bool isFlightActive() const
    { return mFlight.isActive(); }
    //! \brief Returns the last settled menu place; it changes only after a flight completes.
    const std::string& getCurrentPlace() const
    { return mCurrentPlace; }
    //! \brief Returns a configured endpoint for the existing offscreen menu probe.
    bool getCameraPose(const std::string& name, Ogre::Vector3& position, Ogre::Quaternion& orientation) const;

private:
    //! \brief One authored camera position and its local view orientation.
    struct CameraPose
    {
        //! Location in the scene's existing coordinate system.
        Ogre::Vector3 mPosition = Ogre::Vector3::ZERO;
        //! View rotation, matching CameraMove's local X/Y/Z rotation order.
        Ogre::Quaternion mOrientation = Ogre::Quaternion::IDENTITY;
    };

    //! \brief A named path with its duration and ordered waypoint names.
    struct CameraPath
    {
        //! Duration in interface seconds.
        Ogre::Real mDuration = MenuFlightSettings::DURATION;
        //! Pose names in travel order, excluding the current camera position.
        std::vector<std::string> mWaypoints;
    };

    //! \brief One configured firelight waveform and the native light's unmodulated colours.
    struct FireLight
    {
        //! Name of the point light created by the native scene commands.
        std::string mName = std::string();
        //! Maximum fractional change around the authored light intensity.
        Ogre::Real mAmplitude = 0.0f;
        //! Angular frequency in radians per interface second.
        Ogre::Real mFrequency = 1.0f;
        //! Independent waveform phase in radians.
        Ogre::Real mPhase = 0.0f;
        //! Native light, valid only between scene reset and resource release.
        Ogre::Light* mLight = nullptr;
        //! Authored diffuse colour, never replaced by a previously modulated value.
        Ogre::ColourValue mDiffuse = Ogre::ColourValue::Black;
        //! Authored specular colour, scaled by the same waveform as diffuse lighting.
        Ogre::ColourValue mSpecular = Ogre::ColourValue::Black;
    };

    //! \brief Applies a pose to the existing camera hierarchy without gameplay movement or map clamping.
    void applyCameraPose(CameraManager& cameraManager, const CameraPose& pose);
    //! \brief Begins a validated path from the actual current camera position.
    bool beginPath(CameraManager& cameraManager, const CameraPath& path, const std::string& destination);
    //! \brief Samples the active curved path with eased time and quaternion interpolation.
    CameraPose samplePath(Ogre::Real progress) const;
    //! \brief Advances configured firelight without multiplying the previous frame's result.
    void updateFireLights(Ogre::Real elapsed);
    //! Parsed native scene commands, in authored activation order.
    std::vector<RenderSceneGroup*> mSceneGroups;
    //! Named camera endpoints read from the scene configuration.
    std::map<std::string, CameraPose> mCameraPoses;
    //! Authored routes for the destinations and the outside arrival.
    std::map<std::string, CameraPath> mCameraPaths;
    //! Configured firelights; green and other steady lights are not included.
    std::vector<FireLight> mFireLights;
    //! Interface seconds since the native menu scene was reset.
    Ogre::Real mFireTime = 0.0f;
    //! Actual start pose followed by the current path's authored waypoints.
    std::vector<CameraPose> mFlightPoses;
    //! Place last reached without an active transition.
    std::string mCurrentPlace;
    //! Destination to publish only when the active flight finishes.
    std::string mFlightPlace;
    //! Timer shared by native arrival, destination and return flights.
    MenuFlight mFlight;
    //! Whether parsed groups currently own live render objects.
    bool mActive = false;
    //! Parsed menu fill, independent of the game ambient restored on exit.
    Ogre::ColourValue mMenuAmbient = Ogre::ColourValue::Black;
    //! World ambient lighting restored when the menu releases its scene.
    Ogre::ColourValue mSavedAmbient = Ogre::ColourValue::Black;
};

#endif // RENDERSCENEMENU_H
