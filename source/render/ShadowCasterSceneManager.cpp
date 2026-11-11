/*
 * Copyright (C) 2026 OpenDungeons Team
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "render/ShadowCasterSceneManager.h"

#include <OgreCamera.h>
#include <OgreMovableObject.h>
#include <OgreRenderQueue.h>
#include <OgreRoot.h>
#include <OgreSceneNode.h>

namespace
{
//! Creates the game's scene managers for Ogre::Root and destroys them again.
class ShadowCasterSceneManagerFactory : public Ogre::SceneManagerFactory
{
public:
    //! Returns the type name the game passes to Ogre::Root::createSceneManager.
    const Ogre::String& getTypeName() const override
    {
        return ShadowCasterSceneManager::TYPE_NAME;
    }

    //! Creates one scene manager, as Ogre's default factory does.
    Ogre::SceneManager* createInstance(const Ogre::String& instanceName) override
    {
        return OGRE_NEW ShadowCasterSceneManager(instanceName);
    }
};
}

//! The type name shared by the scene manager and its factory.
const Ogre::String ShadowCasterSceneManager::TYPE_NAME = "ShadowCasterSceneManager";

//! Creates an empty scene, as Ogre's default scene manager does.
ShadowCasterSceneManager::ShadowCasterSceneManager(const Ogre::String& name) :
    Ogre::SceneManager(name)
{
}

//! Returns the type name Ogre uses to find the factory of this scene manager.
const Ogre::String& ShadowCasterSceneManager::getTypeName() const
{
    return TYPE_NAME;
}

//! Keeps Ogre's traversal for normal views and visits only shadow casters in the shadow texture pass.
void ShadowCasterSceneManager::_findVisibleObjects(Ogre::Camera* cam, Ogre::VisibleObjectsBoundsInfo* visibleBounds,
    bool onlyShadowCasters)
{
    if(!onlyShadowCasters)
    {
        Ogre::SceneManager::_findVisibleObjects(cam, visibleBounds, onlyShadowCasters);
        return;
    }
    findShadowCasters(getRootSceneNode(), cam, visibleBounds);
}

//! Mirrors SceneNode::_findVisibleObjects (node culling, children, debug drawer) for the shadow texture
//! pass, but hands only shadow casters to the render queue.
void ShadowCasterSceneManager::findShadowCasters(Ogre::SceneNode* node, Ogre::Camera* cam,
    Ogre::VisibleObjectsBoundsInfo* visibleBounds)
{
    if(!cam->isVisible(node->_getWorldAABB()))
        return;

    Ogre::RenderQueue* queue = getRenderQueue();
    const Ogre::SceneNode::ObjectMap& objects = node->getAttachedObjects();
    for(Ogre::MovableObject* object : objects)
    {
        // For a non-caster, RenderQueue::processVisibleObject queues nothing in this pass; it would only
        // add receiver bounds to the shadow camera's information. Casters take Ogre's unchanged path.
        if(object->getCastShadows())
            queue->processVisibleObject(object, cam, true, visibleBounds);
    }

    const Ogre::Node::ChildNodeMap& children = node->getChildren();
    for(Ogre::Node* child : children)
        findShadowCasters(static_cast<Ogre::SceneNode*>(child), cam, visibleBounds);

    if(getDebugDrawer() != nullptr)
        getDebugDrawer()->drawSceneNode(node);
}

//! Registers the static factory with Root once; the factory outlives Root, which destroys the remaining
//! scene managers through it at shutdown.
const Ogre::String& ShadowCasterSceneManager::registerFactory()
{
    static ShadowCasterSceneManagerFactory factory;
    static bool registered = false;
    if(!registered)
    {
        Ogre::Root::getSingleton().addSceneManagerFactory(&factory);
        registered = true;
    }
    return TYPE_NAME;
}
