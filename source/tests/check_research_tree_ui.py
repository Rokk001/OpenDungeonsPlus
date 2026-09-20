"""Run production research-button and dependency rendering against installed CEGUI."""
from pathlib import Path
import os
import re
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[2]
prefix = Path(os.environ['CMAKE_PREFIX_PATH'])
game = (repo / 'source/modes/GameMode.cpp').read_text()
manager = (repo / 'source/game/SkillManager.cpp').read_text()

def function(signature):
    start = game.index(signature)
    end = game.index('{', start) + 1
    depth = 1
    while depth:
        depth += (game[end] == '{') - (game[end] == '}')
        end += 1
    return game[start:end]

# Read the actual constructor's ordered dependency lists, not diagram row guesses.
dependencies = {'emptyDepends': []}
model = {}
for line in manager[manager.index('SkillManager::SkillManager()'):manager.index('SkillManager::~SkillManager()')].splitlines():
    if match := re.search(r'(lvl\ddepends)\.clear\(\)', line):
        dependencies[match[1]] = []
    if match := re.search(r'resType = SkillType::(\w+);', line):
        current = match[1]
    if match := re.search(r'new Skill\(resType, .*, (\w+)\)', line):
        parents = list(dependencies.get(match[1], []))
    if match := re.search(r'new SkillDef\w+\("([^"]+)", "([^"]+)"', line):
        model[current] = (match[1] + match[2], parents)
    if match := re.search(r'(lvl\ddepends)\.push_back\(skill\)', line):
        dependencies.setdefault(match[1], []).append(current)
assert len(model) == 27
initializers = '\n'.join('data[SkillType::%s] = {SkillType::%s, "%s", {%s}};' %
    (key, key, path, ','.join('&data[SkillType::'+parent+']' for parent in parents))
    for key, (path, parents) in model.items())
probe = r'''
#include <CEGUI/CEGUI.h>
#include <CEGUI/RendererModules/Null/Renderer.h>
#include <CEGUI/RendererModules/Ogre/ResourceProvider.h>
#include <CEGUI/RendererModules/Ogre/ImageCodec.h>
#include <OgreRoot.h>
#include <OgreResourceGroupManager.h>
#include "game/SkillType.h"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <map>
namespace Helper {template<class T>std::string toString(T v){return std::to_string(v);}}
struct CreatureDefinition {std::string getMeshName()const{return "Kobold.mesh";}};
const CEGUI::Image& getCreatureHandIconImage(const std::string&){return CEGUI::ImageManager::getSingleton().get("OpenDungeonsIcons/WorkerButton");}
struct Seat {uint32_t level=0,queue=0;bool current=false;std::vector<SkillType> denied;
 uint32_t getSkillLevel(SkillType)const{return level;}
 const CreatureDefinition* getWorkerClassToSpawn(){return nullptr;}
 std::string getFaction(){return "Keeper";}
 const std::vector<SkillType>& getSkillNotAllowed()const{return denied;}
 uint32_t isSkillPending(SkillType)const{return queue;}
 bool getCurrentSkillProgress(SkillType& t,float& p){t=SkillType::roomTrainingHall;p=.5f;return current;}};
struct Player {Seat seat;Seat* getSeat(){return &seat;}};
struct GameMap {Player player;Player* getLocalPlayer(){return &player;}
 const CreatureDefinition* getClassDescription(const std::string&){static CreatureDefinition worker;return &worker;}};
struct ConfigManager {static ConfigManager& getSingleton(){static ConfigManager config;return config;}
 std::string getFactionWorkerClass(const std::string&){return "Kobold";}};
struct Skill {SkillType type;std::string path;std::vector<const Skill*> parents;
 SkillType getType()const{return type;}const std::vector<const Skill*>& getDependencies()const{return parents;}
 int getNeededSkillPoints(uint32_t level)const{return 100*level;}};
struct SkillManager {static std::map<SkillType,Skill> data;
 static const Skill* getSkill(SkillType t){return &data.at(t);}
 static std::string getResearchDescription(SkillType,uint32_t){return "Test research description";}
 template<class F>static void listAllSkills(F f){for(auto& p:data)f(p.second.path,"cast"+std::to_string(int(p.first)),p.second.path+"/"+p.second.path.substr(p.second.path.find('/')+1)+"ProgressBar",p.first);}};
std::map<SkillType,Skill> SkillManager::data;
namespace Skills {std::string skillTypeToPlayerVisibleString(SkillType t){return SkillManager::data.at(t).path;}}
struct GameMode {CEGUI::Window* mRootWindow;GameMap* mGameMap;bool mIsSkillWindowOpen=false;std::vector<SkillType> mSkillPending;
 struct Progress {CEGUI::ProgressBar* mProgressBar=nullptr;float mCompleteness=0;void setValue(CEGUI::ProgressBar* b,float p){mProgressBar=b;mCompleteness=p;}}mSkillCurrentCompletion;
 void refreshSkillButtonState(const std::string&,const std::string&,const std::string&,SkillType);
 void refreshSkillConnections();};
METHODS
int main(int argc,char** argv){try{
 Ogre::Root ogre("","","research-tree-Ogre.log");ogre.loadPlugin(std::string(argv[2])+"/bin/Codec_STBI");
 auto& resources=Ogre::ResourceGroupManager::getSingleton();
 for(const char* path:{"gui","gui/fonts","gui/schemas"})resources.addResourceLocation(std::string(argv[1])+"/"+path,"FileSystem","GUI");
 CEGUI::OgreResourceProvider provider;provider.setDefaultResourceGroup("GUI");CEGUI::OgreImageCodec codec;codec.setImageFileDataType("png");
 auto& renderer=CEGUI::NullRenderer::create();renderer.setDisplaySize(CEGUI::Sizef(1920,1200));
 auto& system=CEGUI::System::create(renderer,&provider,nullptr,&codec,nullptr,"","research-tree-CEGUI.log");
 CEGUI::SchemeManager::getSingleton().createFromFile("ODSkin.scheme");
 auto& windows=CEGUI::WindowManager::getSingleton();auto* root=windows.createWindow("DefaultWindow","Root");
 root->addChild(windows.loadLayoutFromFile("WindowSkillTree.layout"));system.getDefaultGUIContext().setRootWindow(root);
 auto& data=SkillManager::data;INITIALIZERS
 GameMap map;GameMode game{root,&map};int checks=0,failures=0;
 auto check=[&](bool ok,const char* why){++checks;if(!ok){++failures;std::cout<<"FAIL "<<why<<'\n';}};
 for(const auto& pair:data)root->addChild(windows.createWindow("OD/GameTabButton","cast"+std::to_string(int(pair.first))));
 for(uint32_t level=0;level<=3;++level){
  map.player.seat.level=level;map.player.seat.queue=2;map.player.seat.current=level<3;
  SkillManager::listAllSkills([&](const std::string& name,const std::string& cast,const std::string& bar,SkillType type){
   game.refreshSkillButtonState(name,cast,bar,type);auto* b=root->getChild("SkillTreeWindow/Skills/"+name);
   check(b->getText().empty(),"no confusing numeric overlay");
   check(b->getProperty("ButtonImageColour")== (level==0?"FF666666":"FFFFFFFF"),"unresearched icons are greyed and researched icons retain colour");
   check(b->getProperty("ResearchLevelColour")== (level==3?"FFFFC947":level==2?"FFD5DFE8":"00FFFFFF"),"level has no, silver or gold frame");
   check(b->isDisabled()==(level==3),"max-level selection rule preserved");
   check(root->getChild(cast)->isVisible()==(level>0),"unlocked actions stay available during upgrades");
   check(b->getTooltipText().find(level==3?"Maximum level":"Queue position: 2")!=CEGUI::String::npos,"queue and level information remains accessible");
   check(b->getTooltipText().find("Requires all:")!=CEGUI::String::npos || data.at(type).parents.empty(),"prerequisites are explicitly all required");
  });
  game.refreshSkillConnections();game.refreshSkillConnections();
  for(const auto& p:data){auto* button=root->getChild("SkillTreeWindow/Skills/"+p.second.path);auto* parent=button->getParent();
   for(auto* dependency:p.second.parents)for(int part=0;part<3;++part){
    auto* line=parent->getChild("ResearchLink_"+std::to_string(int(dependency->type))+"_"+std::to_string(int(p.first))+"_"+std::to_string(part));
    check(line->isMousePassThroughEnabled(),"connections do not intercept clicks");
    check(line->getPixelSize().d_width>0&&line->getPixelSize().d_height>0,"each immediate edge has positive geometry");
    check(line->getProperty("ImageColours").find(level>0?"FFC8AE6E":"FF626262")!=CEGUI::String::npos,"edge reflects prerequisite completion");
   }
  }
  system.getDefaultGUIContext().draw();
 }
 windows.destroyWindow(root);CEGUI::System::destroy();CEGUI::NullRenderer::destroy(renderer);
 std::cout<<"CHECKS="<<checks<<" FAILURES="<<failures<<'\n';return failures?1:0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
'''.replace('METHODS', function('void GameMode::refreshSkillButtonState(')+'\n'+function('void GameMode::refreshSkillConnections(')).replace('INITIALIZERS', initializers)
with tempfile.TemporaryDirectory(prefix='odp-research-tree-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(probe)
    cegui_source = prefix.parent / 'src/cegui/cegui'
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/std:c++14', '/DCEGUINULLRENDERER_EXPORTS',
        f'/I{repo / "source"}', f'/I{prefix / "include/cegui-0"}', f'/I{cegui_source / "include"}', f'/I{prefix / "include/OGRE"}',
        'check.cpp', *[str(cegui_source / 'src/RendererModules/Null' / (name+'.cpp')) for name in ('Renderer','GeometryBuffer','Texture','TextureTarget')],
        '/Fecheck.exe', '/link', f'/LIBPATH:{prefix / "lib"}', 'CEGUIBase-0.lib', 'CEGUIOgreRenderer-0.lib', 'OgreMain.lib'], cwd=work, check=True)
    subprocess.run([str(work / 'check.exe'), str(repo), str(prefix)], cwd=work, check=True)
