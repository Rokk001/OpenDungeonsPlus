"""Check body clearance against 121 skinned Walk poses of every creature model."""
from pathlib import Path
import argparse
import os
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--height-profile', action='store_true', help='Measure triangle-clipped walking envelopes below furniture heights without changing collision policy')
args = parser.parse_args()

repo = Path(__file__).resolve().parents[2]
prefix = Path(os.environ['CMAKE_PREFIX_PATH'])
models = set(re.findall(r'^\s*MeshName\s+(\S+)', (repo / 'config/creatures.cfg').read_text(), re.M))
catalog = set(re.findall(r'\{"([^"\n]+\.mesh)"', (repo / 'source/gamemap/RoomObjectBounds.h').read_text()))
assert models == catalog, f'Walking bounds catalog mismatch: {models ^ catalog}'
probe = r'''
#include <Ogre.h>
#include "gamemap/RoomObjectBounds.h"
#include <iostream>
Ogre::AxisAlignedBox poseBounds;
const float heights[]={.05f,.1f,.15f,.2f,.3f};
Ogre::AxisAlignedBox heightBounds[5];
bool profile=false;
float radius(Ogre::Entity* entity){
 entity->addSoftwareAnimationRequest(false);entity->_updateAnimation();entity->removeSoftwareAnimationRequest(false);
 float result=0;poseBounds.setNull();
 for(unsigned sub=0;sub<entity->getNumSubEntities();++sub){
  auto* part=entity->getSubEntity(sub);
  auto* data=part->getSubMesh()->useSharedVertices?entity->_getSkelAnimVertexData():part->_getSkelAnimVertexData();
  auto* position=data->vertexDeclaration->findElementBySemantic(Ogre::VES_POSITION);
  auto buffer=data->vertexBufferBinding->getBuffer(position->getSource());
  Ogre::HardwareBufferLockGuard lock(buffer,Ogre::HardwareBuffer::HBL_READ_ONLY);
  auto* bytes=static_cast<unsigned char*>(lock.pData);
  for(size_t i=0;i<data->vertexCount;++i){float* vertex;position->baseVertexPointerToElement(bytes+(data->vertexStart+i)*buffer->getVertexSize(),&vertex);result=std::max(result,std::hypot(vertex[0],vertex[1]));poseBounds.merge(Ogre::Vector3(vertex));}
  if(profile){
   if(part->getSubMesh()->operationType!=Ogre::RenderOperation::OT_TRIANGLE_LIST)
    throw std::runtime_error("Height profiling requires triangle-list meshes");
   auto* indices=part->getSubMesh()->indexData;
   Ogre::HardwareBufferLockGuard indexLock(indices->indexBuffer,Ogre::HardwareBuffer::HBL_READ_ONLY);
   const bool wide=indices->indexBuffer->getType()==Ogre::HardwareIndexBuffer::IT_32BIT;
   for(size_t triangle=0;triangle+2<indices->indexCount;triangle+=3){
    Ogre::Vector3 points[3];
    for(int corner=0;corner<3;++corner){
     const auto offset=indices->indexStart+triangle+corner;
     const auto index=wide?static_cast<const uint32_t*>(indexLock.pData)[offset]:static_cast<const uint16_t*>(indexLock.pData)[offset];
     if(index>=data->vertexCount)throw std::runtime_error("Height profile vertex index outside animated data");
     float* vertex;position->baseVertexPointerToElement(bytes+(data->vertexStart+index)*buffer->getVertexSize(),&vertex);points[corner]=Ogre::Vector3(vertex);
    }
    for(int band=0;band<5;++band)for(int corner=0;corner<3;++corner){
     const auto& a=points[corner];const auto& b=points[(corner+1)%3];
     if(a.z<=heights[band])heightBounds[band].merge(a);
     if((a.z<heights[band]&&b.z>heights[band])||(a.z>heights[band]&&b.z<heights[band]))
      heightBounds[band].merge(a+(b-a)*((heights[band]-a.z)/(b.z-a.z)));
    }
   }
  }
 }
 return result;
}
int main(int argc,char** argv){try{
 Ogre::Root root("","","walking-bounds.log");root.loadPlugin("RenderSystem_GL3Plus");
 root.setRenderSystem(root.getAvailableRenderers().front());root.initialise(false);
 Ogre::NameValuePairList opts;opts["hidden"]="true";root.createRenderWindow("Walking bounds",64,64,false,&opts);
 auto& groups=Ogre::ResourceGroupManager::getSingleton();groups.createResourceGroup("Graphics");
 groups.addResourceLocation(std::string(argv[1])+"/models","FileSystem","Graphics",true);groups.initialiseAllResourceGroups();
 auto* scene=root.createSceneManager();int checks=0,failures=0;
 profile=argc>2;
 if(profile)for(const auto& furniture:RoomObjectPath::meshBounds){
  const std::string name=furniture.name;
  if(name.find("Bed")==std::string::npos&&name.find("Coffin")==std::string::npos)continue;
  const auto mesh=Ogre::MeshManager::getSingleton().load(name+".mesh","Graphics");
  std::cout<<"FURNITURE_HEIGHT "<<name<<" min="<<mesh->getBounds().getMinimum().z<<" max="<<mesh->getBounds().getMaximum().z<<'\n';
 }
 for(const auto& model:RoomObjectPath::walkingRadii){
  for(auto& bounds:heightBounds)bounds.setNull();
  auto* entity=scene->createEntity(model.name,model.name,"Graphics");
  auto* node=scene->getRootSceneNode()->createChildSceneNode();node->attachObject(entity);
  auto* walk=entity->getAnimationState("Walk");walk->setEnabled(true);
  for(int frame=0;frame<=120;++frame){
   walk->setTimePosition(walk->getLength()*frame/120);root._fireFrameStarted();root._fireFrameRenderingQueued();
   float actual=radius(entity);++checks;
   if(actual>model.radius||poseBounds.getMinimum().x<model.minX||poseBounds.getMinimum().y<model.minY||poseBounds.getMaximum().x>model.maxX||poseBounds.getMaximum().y>model.maxY){++failures;std::cout<<"FAIL "<<model.name<<" pose "<<frame<<" exceeds walking bounds "<<poseBounds<<'\n';}
   root._fireFrameEnded();
  }
  if(profile)for(int band=0;band<5;++band)
   std::cout<<"HEIGHT_PROFILE "<<model.name<<" z="<<heights[band]<<" bounds="<<heightBounds[band]<<'\n';
  node->detachAllObjects();scene->destroyEntity(entity);scene->destroySceneNode(node);
 }
 root.destroySceneManager(scene);std::cout<<"CHECKS="<<checks<<" FAILURES="<<failures<<'\n';return failures?1:0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
'''
with tempfile.TemporaryDirectory(prefix='odp-walking-bounds-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(probe)
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/std:c++14', f'/I{repo / "source"}',
                    f'/I{prefix / "include/OGRE"}', 'check.cpp', '/Fecheck.exe', '/link',
                    f'/LIBPATH:{prefix / "lib"}', 'OgreMain.lib'], cwd=work, check=True)
    result = subprocess.run([str(work / 'check.exe'), str(repo)] + (['profile'] if args.height_profile else []), cwd=work, capture_output=True, text=True)
    print('\n'.join(line for line in result.stdout.splitlines() if any(marker in line for marker in ('CHECKS=', 'FAIL ', 'HEIGHT_PROFILE ', 'FURNITURE_HEIGHT '))))
    if result.returncode:
        if 'FAIL ' not in result.stdout:
            print(result.stderr)
        result.check_returncode()
