"""Render a moving production magic projectile for 60 frames in a hidden Ogre window."""
from pathlib import Path
import os
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[2]
prefix = Path(os.environ['CMAKE_PREFIX_PATH'])
probe = r'''
#include <Ogre.h>
#include <RTShaderSystem/OgreShaderGenerator.h>
#include <Bites/OgreSGTechniqueResolverListener.h>
#include <iostream>
int main(int argc,char** argv){try{
 Ogre::Root root("","","magic-projectile.log");root.loadPlugin("RenderSystem_GL3Plus");root.loadPlugin("Codec_STBI");root.loadPlugin("Plugin_ParticleFX");
 root.setRenderSystem(root.getAvailableRenderers().front());root.initialise(false);
 Ogre::NameValuePairList options;options["hidden"]="true";options["vsync"]="false";
 auto* window=root.createRenderWindow("Projectile check",256,128,false,&options);
 auto& groups=Ogre::ResourceGroupManager::getSingleton();groups.createResourceGroup("Graphics");
 std::string repo=argv[1],prefix=argv[2];
 for(const auto& path:{repo+"/materials/textures",prefix+"/Media/Main",prefix+"/Media/RTShaderLib/GLSL"})groups.addResourceLocation(path,"FileSystem","Graphics");
 Ogre::RTShader::ShaderGenerator::initialize();groups.initialiseAllResourceGroups();
 groups.addResourceLocation(repo+"/materials/scripts","FileSystem","Graphics");groups.addResourceLocation(repo+"/particles","FileSystem","Graphics");
 auto& materials=Ogre::MaterialManager::getSingleton();materials.parseScript(groups.openResource("MissileMagic.material","Graphics"),"Graphics");
 Ogre::ParticleSystemManager::getSingleton().parseScript(groups.openResource("MissileMagic.particle","Graphics"),"Graphics");
 auto* shaders=Ogre::RTShader::ShaderGenerator::getSingletonPtr();OgreBites::SGTechniqueResolverListener resolver(shaders);materials.addListener(&resolver);
 auto* scene=root.createSceneManager();shaders->addSceneManager(scene);
 auto* camera=scene->createCamera("Camera");camera->setNearClipDistance(.01f);camera->setAspectRatio(2);camera->setProjectionType(Ogre::PT_ORTHOGRAPHIC);camera->setOrthoWindow(4,2);
 auto* cameraNode=scene->getRootSceneNode()->createChildSceneNode(Ogre::Vector3(0,0,4));cameraNode->attachObject(camera);
 auto* viewport=window->addViewport(camera);viewport->setBackgroundColour(Ogre::ColourValue(.1f,.08f,.06f));viewport->setMaterialScheme(Ogre::RTShader::ShaderGenerator::DEFAULT_SCHEME_NAME);
 auto* node=scene->getRootSceneNode()->createChildSceneNode();auto* particles=scene->createParticleSystem("Bolt","MissileMagic");node->attachObject(particles);
 int checks=0,failures=0;
 auto check=[&](bool v,const char* reason){++checks;if(!v){++failures;std::cout<<"FAIL "<<reason<<'\n';}};
 for(int frame=0;frame<60;++frame){
    const float x=-1.3f+frame*2.6f/59;
    node->setPosition(x,0,0);node->_update(true,false);particles->_update(1.f/60);
    window->update(false);
    Ogre::Image pixels;pixels.create(Ogre::PF_BYTE_RGBA,256,128);window->copyContentsToMemory(pixels.getPixelBox(),Ogre::RenderTarget::FB_BACK);
    int bright=0;const int center=int(128+x*64);
    for(int px=center-7;px<=center+7;++px)for(int py=57;py<=71;++py){auto c=pixels.getColourAt(px,py,0);if(c.b>.5f && c.g>.35f)++bright;}
    check(particles->getNumParticles()>0,"continuous emission never disappears");
    check(bright>=2,"bright projectile remains visible at its current position");
    window->swapBuffers();
 }
 node->detachObject(particles);scene->destroyParticleSystem(particles);scene->destroySceneNode(node);
 shaders->removeSceneManager(scene);root.destroySceneManager(scene);materials.removeListener(&resolver);Ogre::RTShader::ShaderGenerator::destroy();
 std::cout<<"CHECKS="<<checks<<" FAILURES="<<failures<<'\n';return failures?1:0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
'''
with tempfile.TemporaryDirectory(prefix='odp-magic-projectile-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(probe)
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/std:c++14', f'/I{prefix / "include/OGRE"}',
                    f'/I{prefix / "include/OGRE/RTShaderSystem"}', 'check.cpp', '/Fecheck.exe', '/link',
                    f'/LIBPATH:{prefix / "lib"}', 'OgreMain.lib', 'OgreRTShaderSystem.lib', 'OgreBites.lib'], cwd=work, check=True)
    result = subprocess.run([str(work / 'check.exe'), str(repo), str(prefix)], cwd=work, capture_output=True, text=True)
    print('\n'.join(line for line in result.stdout.splitlines() if 'CHECKS=' in line or 'FAIL ' in line))
    if result.returncode:
        print(result.stderr)
        result.check_returncode()
