"""Exercise the real hand poses, tool attachments and transitions with Ogre.

Run from the Windows compiler environment; this starts an isolated hidden render
fixture, not a game session. Optional --compile-only prepares a blocked fixture.
"""
import argparse
import os
import re
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--compile-only', action='store_true')
args = parser.parse_args()
source = (root / 'source/render/RenderManager.cpp').read_text(encoding='utf-8')
controller = (root / 'source/modes/GameMode.cpp').read_text(encoding='utf-8')
building = re.search(r'const bool building = (.*?);', controller, re.S)[1]
building = building.replace('mGameMap->getGamePaused()', 'paused').replace(
    'mPlayerSelection.getCurrentAction()', 'action')


def function(signature):
    start = source.index(signature)
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


helpers = '\n'.join(function(name) for name in [
    'void createKeeperHandPoses(', 'void createKeeperHandDigAnimation(',
    'void createKeeperHandBuildAnimation(', 'Ogre::Vector3 getHammerStrikePoint(',
    'void alignKeeperHandPointer(',
    'void addPickaxePrism('])
methods = '\n'.join(function(name) for name in [
    'void RenderManager::rrSetHandPose(', 'void RenderManager::rrPlayDigAnimation(',
    'void RenderManager::rrPlayBuildAnimation(',
    'Ogre::AnimationState* RenderManager::setEntityAnimation('])
start = source.index('    mHandPickaxe = mSceneManager->createManualObject(')
end = source.index('    mHandHammer->setVisible(false);', start) + len('    mHandHammer->setVisible(false);')
factory = source[start:end]
probe = r'''
#include <Ogre.h>
#include <OgreBone.h>
#include <OgreTagPoint.h>
#include <OgreKeyFrame.h>
#include <OgreSubMesh.h>
#include <limits>
#include <OgreRTShaderSystem.h>
#include <Bites/OgreSGTechniqueResolverListener.h>
#include <iostream>
#define OD_LOG_ERR(message) ((void)0)
const Ogre::uint8 OD_RENDER_QUEUE_ID_GUI = 101;
HELPERS
struct RenderManager {
    Ogre::SceneManager* mSceneManager = nullptr;
    Ogre::SceneNode* mHeldCreatureGrip = nullptr;
    bool mHeldCreatureDisplayEnabled = false;
    unsigned mHandKeeperHandVisibility = 0;
    Ogre::AnimationState* mHandAnimationState = nullptr;
    Ogre::ManualObject* mHandPickaxe = nullptr;
    Ogre::Entity* mHandHammer = nullptr;
    Ogre::Vector3 mHammerStrikePoint = Ogre::Vector3::ZERO;
    std::string mHandPose = "Idle";
    void rrSetHandPose(bool, bool, bool = false);
    void rrPlayDigAnimation();
    void rrPlayBuildAnimation();
    Ogre::AnimationState* setEntityAnimation(Ogre::Entity*, const std::string&, bool);
    void createTools(Ogre::Entity* keeperHandEnt) { FACTORY }
};
METHODS
int checks = 0;
void check(bool value, const char* label) {
    ++checks;
    if(!value) throw std::runtime_error(label);
}
int main() {
    try {
        enum class SelectedAction { buildRoom, buildTrap, selectTile, none, castSpell, sellRoom };
        const auto selectingBuild = [](bool overGui, bool holding, bool paused, bool validTile, SelectedAction action) {
            int value = 0; int* tile = validTile ? &value : nullptr;
            return BUILDING;
        };
        for(bool gui:{false,true})for(bool holding:{false,true})for(bool paused:{false,true})for(bool tile:{false,true})
            for(auto action:{SelectedAction::buildRoom,SelectedAction::buildTrap,SelectedAction::selectTile,
                SelectedAction::none,SelectedAction::castSpell,SelectedAction::sellRoom})
                check(selectingBuild(gui,holding,paused,tile,action) ==
                    (!gui&&!holding&&!paused&&tile&&(action==SelectedAction::buildRoom||action==SelectedAction::buildTrap)),
                    "construction input respects GUI, holding, pause, map and action precedence");
        Ogre::Root engine("", "", "hammer-Ogre.log");
        engine.loadPlugin("RenderSystem_GL3Plus.dll");
        engine.loadPlugin("Codec_STBI.dll");
        auto* renderer = engine.getAvailableRenderers().front();
        engine.setRenderSystem(renderer);
        renderer->setConfigOption("Full Screen", "No");
        engine.initialise(false);
        Ogre::NameValuePairList options; options["hidden"] = "true";
        auto* window = engine.createRenderWindow("ConstructionHammerCheck", 640, 640, false, &options);
        auto& resources = Ogre::ResourceGroupManager::getSingleton();
        resources.addResourceLocation("../../models", "FileSystem", "Graphics");
        resources.addResourceLocation("../../materials/textures", "FileSystem", "Graphics");
        resources.addResourceLocation("C:/Users/mario/od-deps/install/Media/Main", "FileSystem", "OgreInternal");
        resources.addResourceLocation("C:/Users/mario/od-deps/install/Media/Main", "FileSystem", "Graphics");
        resources.addResourceLocation("C:/Users/mario/od-deps/install/Media/RTShaderLib/GLSL", "FileSystem", "Graphics");
        Ogre::RTShader::ShaderGenerator::initialize();
        resources.initialiseAllResourceGroups();
        resources.addResourceLocation("../../materials/scripts", "FileSystem", "Graphics");
        auto& materials = Ogre::MaterialManager::getSingleton();
        for(const char* name : {"Keeperhand.material", "HandTool.material", "BasicHammer.material"})
            materials.parseScript(resources.openResource(name, "Graphics"), "Graphics");
        auto* hammerPass = materials.getByName("HandTool/Hammer", "Graphics")->getTechnique(0)->getPass(0);
        check(hammerPass->getVertexColourTracking() == Ogre::TVC_NONE, "authored mesh needs no vertex colour stream");
        check(hammerPass->getDepthCheckEnabled() && hammerPass->getDepthWriteEnabled(), "hammer obeys grip occlusion");
        check(hammerPass->getTextureUnitState(0)->getTextureName() == "BasicHammer.png", "authored diffuse atlas retained");
        auto* shaders = Ogre::RTShader::ShaderGenerator::getSingletonPtr();
        OgreBites::SGTechniqueResolverListener listener(shaders); materials.addListener(&listener);
        RenderManager r;
        r.mSceneManager = engine.createSceneManager("DefaultSceneManager");
        shaders->addSceneManager(r.mSceneManager);
        auto* hand = r.mSceneManager->createEntity("keeperHandEnt", "Keeperhand.mesh", "Graphics");
        auto* node = r.mSceneManager->getRootSceneNode()->createChildSceneNode();
        node->setOrientation(Ogre::Quaternion(Ogre::Degree(65), Ogre::Vector3::UNIT_Z) *
            Ogre::Quaternion(Ogre::Degree(35), Ogre::Vector3::UNIT_Y));
        node->attachObject(hand);
        r.mHeldCreatureGrip = r.mSceneManager->createSceneNode();
        createKeeperHandPoses(hand); createKeeperHandDigAnimation(hand);
        createKeeperHandBuildAnimation(hand); r.createTools(hand);
        auto* camera = r.mSceneManager->createCamera("Camera");
        auto* cameraNode = r.mSceneManager->getRootSceneNode()->createChildSceneNode();
        cameraNode->attachObject(camera); cameraNode->setPosition(0, -.02f, .45f);
        cameraNode->lookAt(Ogre::Vector3(0, -.02f, 0), Ogre::Node::TS_WORLD);
        camera->setNearClipDistance(.001f);
        auto* viewport = window->addViewport(camera);
        viewport->setMaterialScheme(Ogre::RTShader::ShaderGenerator::DEFAULT_SCHEME_NAME);
        r.mHandAnimationState = r.setEntityAnimation(hand, "Idle", true);
        r.rrSetHandPose(false, false, true);
        check(r.mHandPose == "Build" && r.mHandHammer->isVisible() && !r.mHandPickaxe->isVisible(), "building shows only hammer");
        check(hand->getSubEntity(0)->getMaterialName() == "Keeperhand/ToolGrip", "closed hand obscures shaft");
        check(r.mHandHammer->getMesh()->getName() == "BasicHammer.mesh", "existing hammer mesh reused");
        check(r.mHandHammer->getSubEntity(0)->getMaterialName() == "HandTool/Hammer", "isolated hand material");
        auto* attachment = static_cast<Ogre::TagPoint*>(r.mHandHammer->getParentNode());
        check(attachment->getPosition().positionEquals(Ogre::Vector3(0,.030f,-.009f)), "shaft uses accepted grasp position");
        const auto oldHammerGrip=Ogre::Quaternion(Ogre::Degree(90),Ogre::Vector3::UNIT_Z)*
            Ogre::Quaternion(Ogre::Degree(-90),Ogre::Vector3::UNIT_X)*Ogre::Quaternion(Ogre::Degree(90),Ogre::Vector3::UNIT_Z);
        check((attachment->getOrientation()*Ogre::Vector3::UNIT_Z).positionEquals(oldHammerGrip*Ogre::Vector3::UNIT_Z),
            "head roll leaves the shaft axis in the existing grip");
        std::cout << "HAMMER_FACE=" << r.mHammerStrikePoint << '\n';
        check(r.mHammerStrikePoint.x < 0 && r.mHammerStrikePoint.z > 0, "strike anchor belongs to the head rather than the shaft");
        for(float scale : {.8f, 1.f, 1.2f}) {
            node->setScale(scale, scale, scale);
            engine._fireFrameStarted(); engine._fireFrameRenderingQueued(); hand->_updateAnimation(); node->_update(true, true);
            alignKeeperHandPointer(hand, r.mHandAnimationState);
            const auto oldFace = node->_getFullTransform() * (attachment->_getFullLocalTransform() * r.mHammerStrikePoint);
            check(oldFace.length() > .02f, "old model-origin alignment reproduces the off-target head");
            alignKeeperHandPointer(hand, r.mHandAnimationState, r.mHandHammer, r.mHammerStrikePoint);
            node->_update(true,true);
            const auto face = node->_getFullTransform() * (attachment->_getFullLocalTransform() * r.mHammerStrikePoint);
            check(face.length() < .00001f, "hammer striking face matches pointer origin at each scale");
            window->update();
            window->writeContentsToFile("hammer-" + std::to_string(int(scale * 100)) + ".png");
            engine._fireFrameEnded();
        }
        for(float scale:{.8f,1.f,1.2f}) {
            node->setScale(scale,scale,scale);r.rrPlayBuildAnimation();
            Ogre::Quaternion windupWrist;
            Ogre::Vector3 previousFace;
            check(!r.mHandAnimationState->getLoop() && r.mHandHammer->isVisible() && !r.mHandPickaxe->isVisible(),
                "build strike is one shot with only its hammer visible");
            for(int sample=0;sample<=16;++sample) {
                r.mHandAnimationState->setTimePosition(r.mHandAnimationState->getLength()*sample/16.f);
                for(int settle=0;settle<2;++settle) {
                    engine._fireFrameStarted(); engine._fireFrameRenderingQueued();
                    alignKeeperHandPointer(hand,r.mHandAnimationState,r.mHandHammer,r.mHammerStrikePoint);
                    node->_update(true,true);window->update();engine._fireFrameEnded();
                }
                const auto wrist=hand->getSkeleton()->getBone("Hand1")->getOrientation();
                if(sample==4)windupWrist=wrist;
                if(sample==8)check(std::abs(windupWrist.Dot(wrist))<.96f,"strike rotates the wrist from windup into impact");
                const auto face=node->_getFullTransform()*(attachment->_getFullLocalTransform()*r.mHammerStrikePoint);
                const auto hammerTransform=node->_getFullTransform()*attachment->_getFullLocalTransform();
                const auto normal=(hammerTransform*(r.mHammerStrikePoint-Ogre::Vector3::UNIT_X)-face).normalisedCopy();
                if(scale==1.f && sample%4==0)std::cout<<"STRIKE_NORMAL sample="<<sample<<" value="<<normal<<'\n';
                if(sample==8) {
                    check(normal.x<-.99f&&std::abs(normal.y)<.02f&&std::abs(normal.z)<.02f,"flat hammer face points left at impact");
                    check(normal.dotProduct((face-previousFace).normalisedCopy())>.99f,"incoming leftward motion hits with the flat face, not the side");
                }
                check(std::abs(face.y)<.00001f&&std::abs(face.z)<.00001f,"leftward strike stays at the target height and depth");
                if(sample==0||sample>=8)check(face.length()<.00001f,"impact and recovery return precisely to pointer");
                if(sample==4)check(face.x>.04f,"windup draws the head right before the leftward strike");
                if(sample>4&&sample<=8)check(face.x<previousFace.x,"striking head travels left throughout impact approach");
                previousFace=face;
                check(hand->getSubEntity(0)->getMaterialName()=="Keeperhand/ToolGrip","strike retains solid closed grip");
                if(scale==1.f && sample%4==0)window->writeContentsToFile("hammer-strike-"+std::to_string(sample)+".png");
            }
            r.rrPlayBuildAnimation();check(r.mHandAnimationState->getTimePosition()==0,"next build restarts strike");
            r.mHandAnimationState=r.setEntityAnimation(hand,r.mHandPose,true);
            check(r.mHandAnimationState->getAnimationName()=="Build","strike returns to construction pose");
        }
        node->setScale(1,1,1);node->setPosition(Ogre::Vector3::ZERO);
        for(const std::string pose : {"Dig", "Point", "Idle", "Build"}) {
            r.rrSetHandPose(pose == "Point", pose == "Dig", pose == "Build");
            check(r.mHandHammer->isVisible() == (pose == "Build"), "hammer follows selected contextual pose");
            check(r.mHandPickaxe->isVisible() == (pose == "Dig"), "pickaxe remains exclusive to digging");
        }
        for(const std::string action : {"Pickup", "Drop", "Slap"}) {
            r.mHandAnimationState = r.setEntityAnimation(hand, action, false);
            r.rrSetHandPose(false, false, true);
            check(!r.mHandHammer->isVisible() && !r.mHandPickaxe->isVisible(), "one-shot hides tools");
            r.mHandAnimationState = r.setEntityAnimation(hand, r.mHandPose, true);
            check(r.mHandHammer->isVisible(), "latest construction pose restored");
        }
        r.rrPlayDigAnimation();
        check(r.mHandPickaxe->isVisible() && !r.mHandHammer->isVisible(), "dig strike retains pickaxe");
        r.mHandAnimationState = r.setEntityAnimation(hand, "Build", true);
        r.mHandKeeperHandVisibility = 1; r.rrSetHandPose(false, false, true);
        check(!r.mHandHammer->isVisible(), "hidden hand hides hammer");
        r.mHandKeeperHandVisibility = 0; r.rrSetHandPose(false, false, true);
        check(r.mHandHammer->isVisible(), "reshown hand restores hammer");
        hand->detachAllObjectsFromBone();
        r.mSceneManager->destroyEntity(r.mHandHammer);
        r.mSceneManager->destroyManualObject(r.mHandPickaxe);
        r.mSceneManager->destroyEntity(hand);
        shaders->removeSceneManager(r.mSceneManager); engine.destroySceneManager(r.mSceneManager);
        materials.removeListener(&listener); Ogre::RTShader::ShaderGenerator::destroy();
        std::cout << "CHECKS=" << checks << " FAILURES=0\n";
    } catch(const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
'''
probe = probe.replace('HELPERS', helpers).replace('FACTORY', factory).replace('METHODS', methods).replace('BUILDING', building)
out = root / 'build/construction-hammer-check'
out.mkdir(parents=True, exist_ok=True)
cpp = out / 'check.cpp'
cpp.write_text(probe, encoding='utf-8')
prefix = Path(os.environ['CMAKE_PREFIX_PATH'])
command = ['cl', '/nologo', '/EHsc', '/MD', '/std:c++14', f'/I{prefix / "include/OGRE"}',
           f'/I{prefix / "include/OGRE/RTShaderSystem"}', str(cpp), '/Fe:check.exe', '/link',
           f'/LIBPATH:{prefix / "lib"}', 'OgreMain.lib', 'OgreRTShaderSystem.lib', 'OgreBites.lib']
with (out / 'compile.log').open('w') as log:
    subprocess.run(command, cwd=out, stdout=log, stderr=subprocess.STDOUT, check=True)
if not args.compile_only:
    with (out / 'result.log').open('w') as log:
        subprocess.run([str(out / 'check.exe')], cwd=out, stdout=log, stderr=subprocess.STDOUT, check=True)
    result = (out / 'result.log').read_text(errors='replace')
    assert 'Error: ScriptCompiler' not in result and "Can't assign material" not in result, result
    print(next(line for line in result.splitlines() if line.startswith('CHECKS=')))
