"""Verify the navigation catalog against the shipped Ogre room meshes."""
from pathlib import Path
import os
import re
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[2]
prefix = Path(os.environ['CMAKE_PREFIX_PATH'])
catalog = (repo / 'source/gamemap/RoomObjectBounds.h').read_text()
names = set(re.findall(r'\{"([^"]+)"', catalog))
required = set()
for path in (repo / 'source/rooms').glob('*.cpp'):
    required.update(re.findall(r'new (?:BuildingObject|PersistentObject)\(getGameMap\(\), \*this, "([^"]+)"', path.read_text()))
required.update(re.findall(r'^\s*BedMeshName\s+(\S+)', (repo / 'config/creatures.cfg').read_text(), re.M))
required.update(re.findall(r'return "(Goldstack[^"]+)"', (repo / 'source/entities/TreasuryObject.cpp').read_text()))
assert required <= names, f'Missing room furniture: {sorted(required - names)}'
probe = r'''
#include <Ogre.h>
#include "gamemap/RoomObjectBounds.h"
#include <iostream>
int main(int argc,char** argv){try{
 Ogre::Root root("","","bounds.log");root.loadPlugin("RenderSystem_GL3Plus");
 root.setRenderSystem(root.getAvailableRenderers().front());root.initialise(false);
 Ogre::NameValuePairList opts;opts["hidden"]="true";root.createRenderWindow("Bounds",64,64,false,&opts);
 auto& groups=Ogre::ResourceGroupManager::getSingleton();groups.createResourceGroup("Graphics");
 groups.addResourceLocation(std::string(argv[1])+"/models","FileSystem","Graphics",true);groups.initialiseAllResourceGroups();
 int checks=0,failures=0;
 for(const auto& row:RoomObjectPath::meshBounds){
  const auto mesh=Ogre::MeshManager::getSingleton().load(std::string(row.name)+".mesh","Graphics");
  const auto& b=mesh->getBounds();
  for(float delta:{row.minX-b.getMinimum().x,row.minY-b.getMinimum().y,row.maxX-b.getMaximum().x,row.maxY-b.getMaximum().y}){
   ++checks;if(std::abs(delta)>.00002f){++failures;std::cout<<"FAIL "<<row.name<<" stale asset bounds\n";}
  }
 }
 // These decorations are attached high on a wall, not standing on the floor.
 for(const char* name:{"WeaponShield1.mesh","WeaponShield2.mesh"}){
  const auto mesh=Ogre::MeshManager::getSingleton().load(name,"Graphics");++checks;
  if(mesh->getBounds().getMinimum().z<.8f){++failures;std::cout<<"FAIL wall decoration now occupies ground\n";}
 }
 std::cout<<"CHECKS="<<checks<<" FAILURES="<<failures<<'\n';return failures?1:0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
'''
with tempfile.TemporaryDirectory(prefix='odp-room-bounds-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(probe)
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/std:c++14', f'/I{repo / "source"}',
                    f'/I{prefix / "include/OGRE"}', 'check.cpp', '/Fecheck.exe', '/link',
                    f'/LIBPATH:{prefix / "lib"}', 'OgreMain.lib'], cwd=work, check=True)
    result = subprocess.run([str(work / 'check.exe'), str(repo)], cwd=work, capture_output=True, text=True)
    print('\n'.join(line for line in result.stdout.splitlines() if 'CHECKS=' in line or 'FAIL ' in line))
    if result.returncode:
        print(result.stderr)
        result.check_returncode()
