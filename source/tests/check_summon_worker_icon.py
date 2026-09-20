"""Check the production summon-icon branch using the existing worker portrait path."""
from pathlib import Path
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[2]
source = (repo / 'source/modes/GameMode.cpp').read_text()
start = source.index('    if(resType == SkillType::spellSummonWorker)', source.index('void GameMode::refreshSkillButtonState'))
end = source.index('    CEGUI::ProgressBar* skillProgressBar', start)
branch = source[start:end]
spell = (repo / 'source/spells/SpellSummonWorker.cpp').read_text()
assert 'player->getSeat()->getWorkerClassToSpawn()' in spell
assert 'mRootWindow->getChild(button)->getProperty("NormalImage")' in source
probe = r'''
#include <iostream>
#include <map>
#include <string>
namespace CEGUI {using String=std::string;}
enum class SkillType {spellSummonWorker,other};
struct CreatureDefinition {std::string mesh;std::string getMeshName()const{return mesh;}};
struct Seat {const CreatureDefinition* worker;const CreatureDefinition* getWorkerClassToSpawn(){return worker;}};
struct Image {std::string mesh;std::string getName()const{return "CreatureHandIcon/"+mesh;}};
Image getCreatureHandIconImage(const std::string& mesh){return {mesh};}
struct Window {std::map<std::string,std::string> properties;Window* child=nullptr;
 void setProperty(const std::string& key,const std::string& value){properties[key]=value;}
 Window* getChild(const std::string&){return child;}};
void refresh(SkillType resType,Seat* localPlayerSeat,Window* skillButton,Window* guiSheet){
 const std::string castButtonName="SummonWorkerButton";
 BRANCH
}
int main(){int checks=0,failures=0;auto check=[&](bool ok){++checks;if(!ok)++failures;};
 Window skill,cast,root;root.child=&cast;Seat seat{nullptr};
 for(const auto& mesh:{"Kobold.mesh","Dwarf1.mesh","custom-worker.mesh"}){
  CreatureDefinition worker{mesh};seat.worker=&worker;
  refresh(SkillType::spellSummonWorker,&seat,&skill,&root);
  check(skill.properties["ButtonImage"]=="CreatureHandIcon/"+worker.mesh);
  check(cast.properties["NormalImage"]==skill.properties["ButtonImage"]);
  auto saved=skill.properties;refresh(SkillType::other,&seat,&skill,&root);check(skill.properties==saved);
 }
 seat.worker=nullptr;auto saved=skill.properties;refresh(SkillType::spellSummonWorker,&seat,&skill,&root);check(skill.properties==saved);
 std::cout<<"CHECKS="<<checks<<" FAILURES="<<failures<<'\n';return failures?1:0;
}
'''.replace('BRANCH', branch)
with tempfile.TemporaryDirectory(prefix='odp-summon-icon-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(probe)
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/std:c++14', 'check.cpp', '/Fecheck.exe'], cwd=work, check=True)
    subprocess.run([str(work / 'check.exe')], cwd=work, check=True)
