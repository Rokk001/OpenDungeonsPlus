/*
 * Copyright (C) 2026 OpenDungeons Team
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef SHADOWCASTERSCENEMANAGER_H
#define SHADOWCASTERSCENEMANAGER_H

#include <OgreSceneManager.h>

//! The game's scene manager: Ogre's default scene manager, except that the shadow texture pass visits
//! only shadow casters. Ogre's own traversal also processes every shadow receiver in that pass (camera
//! notification, bounds and receiver bounds), although nothing of a receiver is drawn into the shadow
//! texture and the receiver bounds are read by no shadow camera setup or material of the game.
class ShadowCasterSceneManager : public Ogre::SceneManager
{
public:
    //! The scene manager type name for Ogre::Root::createSceneManager.
    static const Ogre::String TYPE_NAME;

    //! Creates an empty scene, as Ogre's default scene manager does.
    explicit ShadowCasterSceneManager(const Ogre::String& name);

    //! Returns TYPE_NAME, which Ogre uses to find this type's factory when it destroys the scene.
    const Ogre::String& getTypeName() const override;

    //! Uses Ogre's traversal for normal views; the shadow texture pass queues the same shadow casters
    //! as Ogre would, but skips objects that do not cast shadows.
    void _findVisibleObjects(Ogre::Camera* cam, Ogre::VisibleObjectsBoundsInfo* visibleBounds,
        bool onlyShadowCasters) override;

    //! Registers this type's factory with Root once and returns TYPE_NAME. The factory is a static object,
    //! so it outlives Root, which destroys the remaining scene managers through it at shutdown.
    static const Ogre::String& registerFactory();

private:
    //! Visits one scene node of the shadow texture pass and its children, as SceneNode::_findVisibleObjects
    //! does, handing only shadow casters to the render queue.
    void findShadowCasters(Ogre::SceneNode* node, Ogre::Camera* cam, Ogre::VisibleObjectsBoundsInfo* visibleBounds);
};

#endif // SHADOWCASTERSCENEMANAGER_H
