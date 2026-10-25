"""Run production research-button and dependency rendering against installed CEGUI."""
from pathlib import Path
import argparse
import os
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--render', action='store_true', help='Save an isolated Ogre/CEGUI graph preview without launching the game')
args = parser.parse_args()
repo = Path(__file__).resolve().parents[2]
prefix = Path(os.environ['CMAKE_PREFIX_PATH'])
game = (repo / 'source/modes/GameMode.cpp').read_text()
manager = (repo / 'source/game/SkillManager.cpp').read_text()
skill_names = (repo / 'source/game/SkillType.cpp').read_text()
names_start = skill_names.index('std::string skillTypeToPlayerVisibleString(')
names_end = skill_names.index('\n}\n}', names_start) + 2

def function(signature):
    start = game.index(signature)
    end = game.index('{', start) + 1
    depth = 1
    while depth:
        depth += (game[end] == '{') - (game[end] == '}')
        end += 1
    return game[start:end]

# The named colours and helper functions of the research tree that the production methods use.
research_colours = game[game.index('//! Colours of the research tree'):game.index('//! '+chr(92)+'brief Whether the window under the mouse')]

# Read the actual constructor: tab prefix, tier, button and parents of every entry, in registration order.
constructor = manager[manager.index('SkillManager::SkillManager()'):manager.index('SkillManager::~SkillManager()')]
prefixes = {match[1]: match[2] for match in re.finditer(r'static const std::string (TREE_PREFIX_\w+) = "([^"]+)";', manager)}
tab_of_prefix = {'SkillTabs/Rooms/': 0, 'SkillTabs/Traps/': 1, 'SkillTabs/Spells/': 2}
model = {}
order = []
current = None
parents = []
for line in constructor.splitlines():
    if match := re.search(r'createSkill\(mSkills, SkillType::(\w+), (NO_PARENTS|std::vector<SkillType>\{([^}]*)\})\)', line):
        current = match[1]
        parents = re.findall(r'SkillType::(\w+)', match[3] or '')
    if re.search(r'new Skill\(SkillType::spellSummonChampion', line):
        current = 'spellSummonChampion'
    if match := re.search(r'new SkillDef\w+\((TREE_PREFIX_\w+), "([^"]+)", skill, (\d)', line):
        if current != 'spellSummonChampion':  # the reward skill has no node in the tree
            model[current] = (prefixes[match[1]] + match[2], parents, int(match[3]), tab_of_prefix[prefixes[match[1]]])
            order.append(current)
assert len(model) == 60
initializers = '\n'.join('data[SkillType::%s] = {SkillType::%s, "%s", {%s}, %d, %d};' %
    (key, key, path, ','.join('&data[SkillType::'+parent+']' for parent in parents), tier, tab)
    for key, (path, parents, tier, tab) in model.items())
initializers += '\n' + '\n'.join('SkillManager::order.push_back(SkillType::%s);' % key for key in order)
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
#include <functional>
#include <iostream>
#include <map>
const std::string SKILL_BADGE_FONT_NORMAL="MedievalSharp-10";const std::string SKILL_BADGE_FONT_SMALL="MedievalSharp-8";const float SKILL_BADGE_NODE_GAP=16.0f;const float SKILL_BADGE_WIDTH_PADDING=8.0f;
namespace Helper {template<class T>std::string toString(T v){return std::to_string(v);}}
struct CreatureDefinition {std::string getMeshName()const{return "Kobold.mesh";}};
const CEGUI::Image& getCreatureHandIconImage(const std::string&){return CEGUI::ImageManager::getSingleton().get("OpenDungeonsIcons/WorkerButton");}
struct Seat {bool gate=true;uint32_t level=0,queue=0;bool current=false;std::vector<SkillType> denied;std::map<SkillType,uint32_t> levels;SkillType currentType=SkillType::roomTrainingHall;
 uint32_t getSkillLevel(SkillType t)const{auto i=levels.find(t);return i==levels.end()?level:i->second;}
 const CreatureDefinition* getWorkerClassToSpawn(){return nullptr;}
 const std::vector<SkillType>& getSkillNotAllowed()const{return denied;}
 uint32_t isSkillPending(SkillType)const{return queue;}
 bool isSkillNotAllowed(SkillType t)const{return std::find(denied.begin(),denied.end(),t)!=denied.end();}
 bool canResearchLevel(SkillType,int,const std::vector<std::pair<SkillType,int> >&)const{return gate;}
 bool getCurrentSkillProgress(SkillType& t,float& p){t=currentType;p=.5f;return current;}};
struct Player {Seat seat;Seat* getSeat(){return &seat;}};
struct GameMap {Player player;Player* getLocalPlayer(){return &player;}};
enum class SkillTab {rooms,traps,spells,nb};
//! \brief Identifies the original four keeper entries without absorbing appended research types.
bool isKeeper(SkillType t){return t>=SkillType::keeperDominion&&t<=SkillType::keeperManaFlow;}
//! \brief Keeps the appended research-only tool and cultivation entries out of the cast-button fixture.
bool hasCastButton(SkillType t){return !isKeeper(t)&&t!=SkillType::trapFineTools&&t!=SkillType::trapMasterTools&&t!=SkillType::spellSunthornCultivation;}
struct Skill {SkillType type;std::string path;std::vector<const Skill*> parents;int tier=1;int tab=0;
 SkillType getType()const{return type;}const std::vector<const Skill*>& getDependencies()const{return parents;}
 int getNeededSkillPoints(uint32_t level)const{return 100*level;}};
struct SkillManager {static std::map<SkillType,Skill> data;
 static const Skill* getSkill(SkillType t){return &data.at(t);}
 static std::string getResearchDescription(SkillType,uint32_t){return "Test research description";}
 static bool isLockedByLostLibrary(SkillType,const Seat*){return false;}
 static std::vector<SkillType> order;
 static SkillTab getSkillTab(SkillType t){return static_cast<SkillTab>(data.at(t).tab);}
 static uint32_t getSkillTier(SkillType t){return data.at(t).tier;}
 static const std::string& getTabTitle(SkillTab t){static const std::string titles[3]={"Rooms","Traps and doors","Spells"};return titles[static_cast<int>(t)];}
 static std::string getTreeButtonPath(SkillType t){return data.at(t).path;}
 static void listTabSkills(SkillTab tab,std::vector<SkillType>& out){out.clear();for(size_t i=0;i<order.size();++i)if(data.at(order[i]).tab==static_cast<int>(tab))out.push_back(order[i]);}
 template<class F>static void listAllSkills(F f){for(std::map<SkillType,Skill>::iterator it=data.begin();it!=data.end();++it){const std::string cast=hasCastButton(it->first)?"cast"+std::to_string(int(it->first)):std::string();f(it->second.path,cast,it->second.path+"/"+it->second.path.substr(it->second.path.find_last_of('/')+1)+"ProgressBar",it->first);}}};
std::map<SkillType,Skill> SkillManager::data;
std::vector<SkillType> SkillManager::order;
namespace Skills {NAMES}
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
 std::map<CEGUI::Window*,CEGUI::URect> authored;
 std::function<void(CEGUI::Window*)> remember=[&](CEGUI::Window* w){authored[w]=w->getArea();for(size_t i=0;i<w->getChildCount();++i)remember(w->getChildAtIdx(i));};
 remember(root->getChild("SkillTreeWindow"));
 auto& data=SkillManager::data;INITIALIZERS
 GameMap map;GameMode game{root,&map};int checks=0,failures=0;
 auto check=[&](bool ok,const char* why){++checks;if(!ok){++failures;std::cout<<"FAIL "<<why<<'\n';}};
 for(std::map<SkillType,Skill>::const_iterator it=data.begin();it!=data.end();++it)if(hasCastButton(it->first))root->addChild(windows.createWindow("OD/GameTabButton","cast"+std::to_string(int(it->first))));
 for(uint32_t level=0;level<=3;++level){
  map.player.seat.level=level;map.player.seat.queue=2;map.player.seat.current=level<3;
  SkillManager::listAllSkills([&](const std::string& name,const std::string& cast,const std::string& bar,SkillType type){
   game.refreshSkillButtonState(name,cast,bar,type);auto* b=root->getChild("SkillTreeWindow/Skills/"+name);
   check(b->getText().empty(),"queue numbers stay absent from the icon");
   auto* badge=b->getChild("ResearchLevel");
   check(badge->getText()==std::to_string(level)+"/3","actual current and maximum level visible on every node");
   check(badge->isVisible()&&badge->isMousePassThroughEnabled()&&!badge->isClippedByParent(),"badge visible below icon without intercepting clicks");
   check(b->getProperty("ButtonImageColour")== (level==0?"FF666666":"FFFFFFFF"),"unresearched icons are greyed and researched icons retain colour");
   check(b->getProperty("ResearchLevelColour")== (level==3?"FFFFC947":level==2?"FFC98A4A":"00FFFFFF"),"level has no, bronze or gold frame");
   {const std::string st=b->getUserString("ResearchState").c_str();
    const std::string want=st=="Researching"?"OpenDungeonsSkin/ResearchTileWorking":st=="Queued"?"OpenDungeonsSkin/ResearchTileQueued":level>0?"OpenDungeonsSkin/ResearchTileLearned":"OpenDungeonsSkin/ResearchTileLocked";
    check(b->getProperty("ResearchTileImage")==CEGUI::String(want),"node state shows as a material tile, not a flat colour square");
    check(!b->isPropertyPresent("ResearchBackgroundColour"),"no flat state colour behind the icon");}
   check(b->isDisabled()==(level==3),"max-level selection rule preserved");
   check(cast.empty()||root->getChild(cast)->isVisible()==(level>0),"unlocked actions stay available during upgrades (a keeper skill has no cast button)");
   check(b->getUserString("ResearchDetails").find(level==3?"Maximum level":"Queue position: 2")!=CEGUI::String::npos,"queue and level information remains accessible");
   check(b->getUserString("ResearchDetails").find("Requires all (level 1):")!=CEGUI::String::npos || data.at(type).parents.empty(),"prerequisites are explicitly all required");
   check(b->getTooltipText()==b->getUserString("ResearchDetails"),"descriptions are optional hover help, not persistent panels");
   check(b->getChild(b->getName()+"ProgressBar")->isVisible()==(type==SkillType::roomTrainingHall&&level<3),"only the current node displays progress");
  });
  game.refreshSkillConnections();game.refreshSkillConnections();
  for(std::map<SkillType,Skill>::const_iterator it=data.begin();it!=data.end();++it){const Skill& node=it->second;
   CEGUI::Window* button=root->getChild("SkillTreeWindow/Skills/"+node.path);CEGUI::Window* parent=button->getParent();
   for(size_t d=0;d<node.parents.size();++d){const Skill* dependency=node.parents[d];
    for(int part=0;part<9;++part){
     const std::string linkName="ResearchLink_"+std::to_string(int(dependency->type))+"_"+std::to_string(int(it->first))+"_"+std::to_string(part);
     if(dependency->tab!=node.tab){check(!parent->isChild(linkName),"a parent in another tab has no path");continue;}
     const bool sameRow=dependency->tier==node.tier;
     const int bars=sameRow?1:2*std::max(1,node.tier-dependency->tier)+1;
     if(part>=bars){check(!parent->isChild(linkName)||!parent->getChild(linkName)->isVisible(),"a path has one bar per straight stretch and no more");continue;}
     CEGUI::Window* line=parent->getChild(linkName);
     check(line->isMousePassThroughEnabled(),"connections do not intercept clicks");
     check(line->getPixelSize().d_width>0&&line->getPixelSize().d_height>0,"each immediate edge has positive geometry");
     check(line->getProperty("ImageColours").find(level>0?"FFE8862E":"FF6E5232")!=CEGUI::String::npos,"permanent paths reflect actual prerequisite completion");
    }
   }
  }
  system.getDefaultGUIContext().draw();
 }
 auto* tree=root->getChild("SkillTreeWindow");
 check(!tree->isChild("CurrentResearch")&&!tree->isChild("ResearchDetails"),"no text banner or explanation panel");
 map.player.seat.level=0;
 {CEGUI::Window* tabs=root->getChild("SkillTreeWindow/Skills/SkillTabs");
  check(tabs->getChild("Rooms")->getText()=="Rooms"&&tabs->getChild("Traps")->getText()=="Traps and doors"&&tabs->getChild("Spells")->getText()=="Spells","tab titles");}
 map.player.seat.level=0;map.player.seat.levels.clear();game.refreshSkillConnections();
 for(std::map<SkillType,Skill>::const_iterator it=data.begin();it!=data.end();++it){const Skill& node=it->second;
  CEGUI::Window* button=root->getChild("SkillTreeWindow/Skills/"+node.path);CEGUI::Window* parent=button->getParent();
  const char* pageNames[3]={"Rooms","Traps","Spells"};
  check(parent->getName()==pageNames[node.tab],"every research button stands in the page of its tab");
  CEGUI::Rectf rect=button->getUnclippedOuterRect().get();CEGUI::Rectf bounds=parent->getUnclippedOuterRect().get();
  int rowSize=0,rowIndex=0;bool seen=false;
  for(size_t i=0;i<SkillManager::order.size();++i){const Skill& other=data.at(SkillManager::order[i]);
   if(other.tab!=node.tab||other.tier!=node.tier)continue;++rowSize;if(SkillManager::order[i]==it->first)seen=true;else if(!seen)++rowIndex;}
  const float centre=(rect.left()+rect.getWidth()*.5f-bounds.left())/bounds.getWidth();
  check(std::abs(centre-(rowIndex+.5f)/rowSize)<.01f,"entry i of n of a row stands at (i + 0.5) / n of the page width");
  for(size_t i=0;i<SkillManager::order.size();++i){const Skill& other=data.at(SkillManager::order[i]);if(other.tab!=node.tab)continue;
   CEGUI::Rectf r=root->getChild("SkillTreeWindow/Skills/"+other.path)->getUnclippedOuterRect().get();
   if(other.tier==node.tier)check(std::abs(r.top()-rect.top())<.5f,"the entries of a tier share one row");
   if(other.tier>node.tier)check(r.top()>rect.top(),"tier I is at the top, tier IV at the bottom");}
  const std::string details=button->getUserString("ResearchDetails").c_str();
  for(size_t d=0;d<node.parents.size();++d){const Skill* dependency=node.parents[d];
   if(dependency->tab==node.tab)continue;
   const char* tabTitles[3]={"Rooms","Traps and doors","Spells"};
   check(details.find("Needs: ")!=std::string::npos&&details.find(std::string(" (")+tabTitles[dependency->tab]+")")!=std::string::npos,"a parent in another tab is named with its tab in the tooltip");}
 }
 {Seat& seat=map.player.seat;seat.denied.assign(1,SkillType::roomGuardRoom);seat.levels.clear();seat.level=0;seat.queue=0;seat.current=false;seat.levels[SkillType::trapAlarm]=1;
  const std::string bannerPath=data.at(SkillType::trapWatchBanner).path;
  game.refreshSkillButtonState(bannerPath,"cast"+std::to_string(int(SkillType::trapWatchBanner)),bannerPath+"/"+bannerPath.substr(bannerPath.find_last_of('/')+1)+"ProgressBar",SkillType::trapWatchBanner);
  CEGUI::Window* banner=root->getChild("SkillTreeWindow/Skills/"+bannerPath);
  const std::string bannerText=banner->getUserString("ResearchDetails").c_str();
  check(bannerText.find("Needs: ")!=std::string::npos&&bannerText.find("- MISSING")==std::string::npos,"a parent the level does not allow counts as ready");
  check(banner->getUserString("ResearchState")!="Locked","an entry whose parents are done or not allowed is not locked");
  seat.denied.clear();seat.levels.clear();seat.levels[SkillType::roomTreasury]=1;seat.gate=false;
  const std::string treasuryPath=data.at(SkillType::roomTreasury).path;
  game.refreshSkillButtonState(treasuryPath,"cast"+std::to_string(int(SkillType::roomTreasury)),treasuryPath+"/"+treasuryPath.substr(treasuryPath.find_last_of('/')+1)+"ProgressBar",SkillType::roomTreasury);
  CEGUI::Window* treasury=root->getChild("SkillTreeWindow/Skills/"+treasuryPath);
  check(treasury->getUserString("ResearchState")=="Locked","level II waits for the tab gate");
  check(std::string(treasury->getUserString("ResearchDetails").c_str()).find("Locked: more entries of the Rooms tab")!=std::string::npos,"the tooltip says why the level is locked");
  seat.gate=true;seat.levels.clear();}
 map.player.seat.levels.clear();
 map.player.seat.level=0;map.player.seat.current=true;map.player.seat.queue=2;
 SkillManager::listAllSkills([&](const std::string& n,const std::string& c,const std::string& b,SkillType t){game.refreshSkillButtonState(n,c,b,t);});
 game.mIsSkillWindowOpen=true;game.refreshSkillConnections();
 for(const CEGUI::Sizef size:std::vector<CEGUI::Sizef>{CEGUI::Sizef(640,480),CEGUI::Sizef(800,600),CEGUI::Sizef(1024,768),CEGUI::Sizef(1280,720),CEGUI::Sizef(1920,1200),CEGUI::Sizef(7680,4320)})for(float user:{.8f,1.f,1.2f}){
  renderer.setDisplaySize(size);const float scale=std::min(size.d_width/1024.f,size.d_height/768.f)*user;
  auto fonts=CEGUI::FontManager::getSingleton().getIterator();
  while(!fonts.isAtEnd()){fonts.getCurrentValue()->setNativeResolution(CEGUI::Sizef(800/user,600/user));fonts.getCurrentValue()->setAutoScaled(CEGUI::ASM_Min);++fonts;}
  CEGUI::FontManager::getSingleton().notifyDisplaySizeChanged(size);
  for(const auto& p:authored){auto area=p.second;area.d_min.d_x.d_offset*=scale;area.d_min.d_y.d_offset*=scale;area.d_max.d_x.d_offset*=scale;area.d_max.d_y.d_offset*=scale;p.first->setArea(area);}
  game.refreshSkillConnections();
  for(const auto& p:data){auto* button=root->getChild("SkillTreeWindow/Skills/"+p.second.path);auto* parent=button->getParent();
   auto rect=button->getUnclippedOuterRect().get();auto bounds=parent->getUnclippedOuterRect().get();
   auto* badge=button->getChild("ResearchLevel");auto label=badge->getUnclippedOuterRect().get();
   check(label.top()>=rect.bottom()-.5f&&label.bottom()<=bounds.bottom(),"level badge below icon and inside graph");
   check(label.getWidth()>=badge->getFont()->getTextExtent(badge->getText())&&label.getHeight()>=badge->getFont()->getLineSpacing(),"level text fits at every scale");
   check(label.left()>=bounds.left()&&label.right()<=bounds.right(),"level badge stays in its category");
   check(rect.left()>=bounds.left()&&rect.right()<=bounds.right()&&rect.top()>=bounds.top()&&rect.bottom()<=bounds.bottom(),"symbol stays inside its graph column");
   check(std::abs(rect.getWidth()-rect.getHeight())<2,"square symbols at all viewport scales");
   check(!parent->isChild(button->getName()+"Label")&&!parent->isChild(button->getName()+"Status"),"no prose around symbol nodes");
   for(std::map<SkillType,Skill>::const_iterator other=data.begin();other!=data.end();++other)if(other->first!=p.first&&other->second.tab==p.second.tab){CEGUI::Rectf r=root->getChild("SkillTreeWindow/Skills/"+other->second.path)->getUnclippedOuterRect().get();
    check(rect.right()<=r.left()||rect.left()>=r.right()||rect.bottom()<=r.top()||rect.top()>=r.bottom(),"node hit areas never overlap inside a tab");}
   auto* bar=static_cast<CEGUI::ProgressBar*>(button->getChild(button->getName()+"ProgressBar"));
   check(bar->getUnclippedOuterRect().get().bottom()<=label.top(),"level count never covers current progress");
   if(p.first==SkillType::roomTrainingHall){
    check(button->getProperty("ResearchTileImage")=="OpenDungeonsSkin/ResearchTileWorking","active node highlighted");
    check(bar->isVisible()&&bar->getProgress()==.5f&&bar->getAlpha()==1,"real progress visible on active node");}
   for(size_t d=0;d<p.second.parents.size();++d){const Skill* dep=p.second.parents[d];if(dep->tab!=p.second.tab)continue;
    const int bars=dep->tier==p.second.tier?1:2*std::max(1,p.second.tier-dep->tier)+1;
    for(int part=0;part<bars;++part){
     CEGUI::Window* line=parent->getChild("ResearchLink_"+std::to_string(int(dep->type))+"_"+std::to_string(int(p.first))+"_"+std::to_string(part));
     check(line->isVisible(),"all prerequisite paths stay visible without hover");
     CEGUI::Rectf edge=line->getUnclippedOuterRect().get();
     check(edge.getWidth()>0&&edge.getHeight()>0,"positive edge geometry");
     for(std::map<SkillType,Skill>::const_iterator other=data.begin();other!=data.end();++other)if(other->second.tab==p.second.tab){CEGUI::Rectf r=root->getChild("SkillTreeWindow/Skills/"+other->second.path)->getUnclippedOuterRect().get();
      check(edge.right()<=r.left()+1||edge.left()>=r.right()-1||edge.bottom()<=r.top()+1||edge.top()>=r.bottom()-1,"connections never cross symbol interiors");}
    }
   }
  }
 }
 windows.destroyWindow(root);CEGUI::System::destroy();CEGUI::NullRenderer::destroy(renderer);
 std::cout<<"CHECKS="<<checks<<" FAILURES="<<failures<<'\n';return failures?1:0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
'''.replace('METHODS', research_colours+chr(10)+function('void GameMode::refreshSkillButtonState(')+'\n'+function('void GameMode::refreshSkillConnections(')).replace('INITIALIZERS', initializers).replace('NAMES', skill_names[names_start:names_end])
if args.render:
    probe = probe.replace('#include <CEGUI/RendererModules/Null/Renderer.h>', '#include <CEGUI/RendererModules/Ogre/Renderer.h>\n#include <CEGUI/BasicImage.h>\n#include <Ogre.h>\n#include <OgreRenderTexture.h>\n#include <OgreHardwarePixelBuffer.h>\n#include <RTShaderSystem/OgreShaderGenerator.h>\n#include <Bites/OgreSGTechniqueResolverListener.h>')
    probe = probe.replace('auto& renderer=CEGUI::NullRenderer::create();renderer.setDisplaySize(CEGUI::Sizef(1920,1200));', r'''
 ogre.loadPlugin(std::string(argv[2])+"/bin/RenderSystem_GL3Plus");
 auto* renderSystem=ogre.getAvailableRenderers().front();ogre.setRenderSystem(renderSystem);
 renderSystem->setConfigOption("Full Screen","No");ogre.initialise(false);
 Ogre::NameValuePairList options;options["hidden"]="true";
 auto* window=ogre.createRenderWindow("Research graph preview",1280,960,false,&options);window->setAutoUpdated(false);
 resources.addResourceLocation(std::string(argv[2])+"/Media/Main","FileSystem","OgreInternal");
 resources.addResourceLocation(std::string(argv[2])+"/Media/RTShaderLib","FileSystem","General");
 resources.initialiseAllResourceGroups();
 Ogre::RTShader::ShaderGenerator::initialize();auto* shaders=Ogre::RTShader::ShaderGenerator::getSingletonPtr();
 OgreBites::SGTechniqueResolverListener listener(shaders);Ogre::MaterialManager::getSingleton().addListener(&listener);
 auto* scene=ogre.createSceneManager("DefaultSceneManager");auto* camera=scene->createCamera("Camera");
 shaders->addSceneManager(scene);Ogre::MaterialManager::getSingleton().setActiveScheme(Ogre::RTShader::ShaderGenerator::DEFAULT_SCHEME_NAME);
 scene->getRootSceneNode()->createChildSceneNode()->attachObject(camera);
 window->addViewport(camera)->setBackgroundColour(Ogre::ColourValue(.02f,.03f,.04f));
 auto& renderer=CEGUI::OgreRenderer::create(*window);renderer.setFrameControlExecutionEnabled(false);
 renderer.setDisplaySize(CEGUI::Sizef(1920,1200));''')
    probe = probe.replace(' windows.destroyWindow(root);', r'''
 renderer.setDisplaySize(CEGUI::Sizef(1280,960));
 auto fonts=CEGUI::FontManager::getSingleton().getIterator();
 while(!fonts.isAtEnd()){fonts.getCurrentValue()->setNativeResolution(CEGUI::Sizef(800,600));fonts.getCurrentValue()->setAutoScaled(CEGUI::ASM_Min);++fonts;}
 CEGUI::FontManager::getSingleton().notifyDisplaySizeChanged(CEGUI::Sizef(1280,960));
 for(const auto& p:authored){auto area=p.second;area.d_min.d_x.d_offset*=1.25f;area.d_min.d_y.d_offset*=1.25f;area.d_max.d_x.d_offset*=1.25f;area.d_max.d_y.d_offset*=1.25f;p.first->setArea(area);}
 auto& seat=map.player.seat;seat.currentType=SkillType::roomArena;seat.current=true;seat.level=0;
 for(const auto& p:data)if(p.second.parents.empty())seat.levels[p.first]=1;
 seat.levels[SkillType::roomTrainingHall]=2;seat.levels[SkillType::roomTreasury]=3;
 seat.levels[SkillType::spellCallToWar]=1;seat.levels[SkillType::spellCreatureExplosion]=1;seat.levels[SkillType::roomPrison]=1;
 game.mSkillPending={SkillType::roomArena,SkillType::roomTorture};
 SkillManager::listAllSkills([&](const std::string& n,const std::string& c,const std::string& b,SkillType t){game.refreshSkillButtonState(n,c,b,t);});
 game.refreshSkillConnections();
 for(const auto& p:data)root->getChild("cast"+std::to_string(int(p.first)))->hide();
 system.getDefaultGUIContext().injectMousePosition(0,0);
 auto texture=Ogre::TextureManager::getSingleton().createManual("ResearchPreview","General",Ogre::TEX_TYPE_2D,1280,960,0,Ogre::PF_BYTE_RGBA,Ogre::TU_RENDERTARGET);
 auto* target=texture->getBuffer()->getRenderTarget();target->setAutoUpdated(false);
 target->addViewport(camera)->setBackgroundColour(Ogre::ColourValue(.02f,.03f,.04f));
 renderer.setDefaultRootRenderTarget(*target);renderSystem->setScissorTest(false);
 target->update(false);system.renderAllGUIContexts();
 target->writeContentsToFile(std::string(argv[1])+"/build/review-followups/research-visual-graph-preview.png");
 renderer.setDefaultRootRenderTarget(*window);target->removeAllViewports();Ogre::TextureManager::getSingleton().remove(texture->getHandle());
 windows.destroyWindow(root);''')
    probe = probe.replace('CEGUI::NullRenderer::destroy(renderer);', 'CEGUI::OgreRenderer::destroy(renderer);shaders->removeSceneManager(scene);ogre.destroySceneManager(scene);Ogre::MaterialManager::getSingleton().removeListener(&listener);Ogre::RTShader::ShaderGenerator::destroy();')
with tempfile.TemporaryDirectory(prefix='odp-research-tree-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(probe)
    cegui_source = prefix.parent / 'src/cegui/cegui'
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/std:c++17', '/DCEGUINULLRENDERER_EXPORTS',
        f'/I{repo / "source"}', f'/I{prefix / "include/cegui-0"}', f'/I{cegui_source / "include"}', f'/I{prefix / "include/OGRE"}', f'/I{prefix / "include/OGRE/RTShaderSystem"}',
        'check.cpp', *[str(cegui_source / 'src/RendererModules/Null' / (name+'.cpp')) for name in ('Renderer','GeometryBuffer','Texture','TextureTarget')],
        '/Fecheck.exe', '/link', f'/LIBPATH:{prefix / "lib"}', 'CEGUIBase-0.lib', 'CEGUIOgreRenderer-0.lib', 'OgreMain.lib', 'OgreRTShaderSystem.lib', 'OgreBites.lib'], cwd=work, check=True)
    subprocess.run([str(work / 'check.exe'), str(repo), str(prefix)], cwd=work, check=True)
