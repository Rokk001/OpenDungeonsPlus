"""Exercise the production defeat sequence timeline and its GameMode driver without a game.

DefeatSequence.h is compiled as it is. The GameMode member functions that drive the sequence are cut out of
GameMode.cpp by signature and compiled against small mocks of CEGUI, the render manager and the game map.
"""
from pathlib import Path
import re
import subprocess
import tempfile
import time

repo = Path(__file__).resolve().parents[2]
game_mode = (repo / 'source/modes/GameMode.cpp').read_text()
game_mode_header = (repo / 'source/modes/GameMode.h').read_text()
sequence_header = (repo / 'source/modes/DefeatSequence.h').read_text()
client = (repo / 'source/network/ODClient.cpp').read_text()


def function(text, signature):
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def constant(name):
    match = re.search(r'^const std::string ' + name + r' = .*;$', game_mode, re.MULTILINE)
    assert match, name
    return match.group(0)


probe = r'''
#include <cmath>
#include <cstdint>
#include <functional>
#include <iostream>
#include <string>
#include <vector>
#include "modes/DefeatSequence.h"

std::vector<std::string> gLog;
#define OD_LOG_INF(x) gLog.push_back(x)
namespace Helper {template<typename T> std::string toString(T v){return std::to_string(v);}}
namespace Ogre
{
struct Vector3
{
    float x, y, z;
    Vector3():x(0),y(0),z(0){}
    Vector3(float ax, float ay, float az):x(ax),y(ay),z(az){}
    Vector3 operator+(const Vector3& o) const {return Vector3(x+o.x,y+o.y,z+o.z);}
    Vector3 operator*(float f) const {return Vector3(x*f,y*f,z*f);}
    float squaredLength() const {return x*x+y*y+z*z;}
    void normalise(){float l=std::sqrt(squaredLength());x/=l;y/=l;z/=l;}
    static const Vector3 UNIT_Y;
};
const Vector3 Vector3::UNIT_Y(0,1,0);
struct ColourValue {float r,g,b,a;};
}
namespace CEGUI
{
struct Window
{
    bool visible;float alpha;std::string text;std::vector<Window*> children;
    Window():visible(true),alpha(-1.0f){}
    size_t getChildCount(){return children.size();}
    Window* getChildAtIdx(size_t i){return children[i];}
    bool isVisible(){return visible;}
    void hide(){visible=false;}
    void setAlpha(float a){alpha=a;}
    void setText(const std::string& t){text=t;}
};
}
struct Seat {Ogre::ColourValue colour;const Ogre::ColourValue& getColorValue() const {return colour;}};
struct GameMap
{
    Seat seat;
    Seat* getSeatById(int id){return id==1?&seat:nullptr;}
};
struct Effect {std::string event,name,script;bool hasColour;Ogre::ColourValue colour;Ogre::Vector3 position;};
struct RenderManager
{
    std::vector<Effect> effects;
    static RenderManager& getSingleton(){static RenderManager manager;return manager;}
    void rrCreateFreeParticleEffect(const std::string& name,const std::string& script,const Ogre::Vector3& p,const Ogre::ColourValue* c)
    {Effect e;e.event="create";e.name=name;e.script=script;e.hasColour=c!=nullptr;if(c)e.colour=*c;e.position=p;effects.push_back(e);}
    void rrMoveFreeParticleEffect(const std::string& name,const Ogre::Vector3& p)
    {Effect e;e.event="move";e.name=name;e.hasColour=false;e.position=p;effects.push_back(e);}
    void rrDestroyFreeParticleEffect(const std::string& name)
    {Effect e;e.event="destroy";e.name=name;e.hasColour=false;effects.push_back(e);}
};
struct Camera {Ogre::Vector3 direction;Ogre::Vector3 getDerivedDirection() const {return direction;}};
struct CameraManager {Camera camera;Camera* getActiveCamera(){return &camera;}};
struct ODFrameListener
{
    CameraManager cameraManager;
    static ODFrameListener& getSingleton(){static ODFrameListener listener;return listener;}
    CameraManager* getCameraManager(){return &cameraManager;}
};
CONSTANTS

class GameMode
{
public:
    GameMode():mRootWindow(&mRoot),mGameMap(&mMap){}
    void updateDefeatSequence(float elapsed);
    void startDefeatSwirl();
    void stopDefeatEffects();
    void hideInterfaceForDefeat();
    void onDefeatSequenceFinished();
    void showDefeatDebriefing() {++mDebriefingShown;}
    int mDebriefingShown = 0;
    DefeatSequence mDefeatSequence;
    Ogre::Vector3 mDefeatHeartPosition;
    Ogre::Vector3 mDefeatSwirlDirection;
    bool mDefeatExplosionEffectActive = false;
    bool mDefeatSwirlEffectActive = false;
    bool mDefeatSwirlDone = false;
    CEGUI::Window* mDefeatTint = nullptr;
    CEGUI::Window* mDefeatFade = nullptr;
    CEGUI::Window* mDefeatSubtitle = nullptr;
    CEGUI::Window* mDefeatCameraMarker = nullptr;
    CEGUI::Window* mDefeatDebriefing = nullptr;
    CEGUI::Window mRoot;
    CEGUI::Window* mRootWindow;
    GameMap mMap;
    GameMap* mGameMap;
};
UPDATE
SWIRL
STOP
HIDE
FINISHED

int gChecks = 0, gFailures = 0;
void check(bool ok, const char* msg) {++gChecks;if(!ok){++gFailures;std::cout << "FAIL " << msg << '\n';}}
bool near(float a, float b) {return std::fabs(a - b) < 0.001f;}
typedef DefeatSequence DS;

struct Run
{
    GameMode mode;
    CEGUI::Window ui1, ui2, tint, fade, subtitle, marker;
    int explosionDestroys = 0, swirlCreates = 0, swirlDestroys = 0, swirlMoves = 0;
    float firstExplosionDestroy = -1, swirlCreateTime = -1, swirlDestroyTime = -1, finishTime = -1;
    bool sequenceWindowHidden = false;
    int uiShownAfterHide = 0;
    Ogre::ColourValue swirlColour;
    bool swirlColourGiven = false;
    float lastSwirlDistance = -1;
    bool swirlMonotonic = true;

    void begin(int32_t conqueror, int32_t hx, int32_t hy)
    {
        gLog.clear();RenderManager::getSingleton().effects.clear();
        mode.mMap.seat.colour = Ogre::ColourValue{0.2f, 0.9f, 0.1f, 0.5f};
        ODFrameListener::getSingleton().cameraManager.camera.direction = Ogre::Vector3(0, 1, -0.5f);
        mode.mRoot.children = {&ui1, &ui2, &tint, &fade, &subtitle, &marker};
        mode.mDefeatTint = &tint;mode.mDefeatFade = &fade;mode.mDefeatSubtitle = &subtitle;mode.mDefeatCameraMarker = &marker;
        mode.mDefeatSequence.start(conqueror, hx, hy);
        mode.mDefeatHeartPosition = Ogre::Vector3(float(hx), float(hy), 0.0f);
        mode.mDefeatExplosionEffectActive = true;
        RenderManager::getSingleton().rrCreateFreeParticleEffect("DefeatHeartExplosion", "HeartExplosion", mode.mDefeatHeartPosition, nullptr);
    }

    // one frame; the interface is shown again first, as game code does when it refreshes a window
    void frame(float dt)
    {
        ui1.visible = true;
        size_t before = RenderManager::getSingleton().effects.size();
        bool wasFinished = mode.mDefeatSequence.isFinished();
        mode.updateDefeatSequence(dt);
        if(ui1.visible || ui2.visible) ++uiShownAfterHide;
        if(!mode.mDefeatSequence.isFinished() && (!tint.visible || !fade.visible || !subtitle.visible || !marker.visible)) sequenceWindowHidden = true;
        float t = mode.mDefeatSequence.getElapsed();
        std::vector<Effect>& effects = RenderManager::getSingleton().effects;
        for(size_t i = before; i < effects.size(); ++i)
        {
            Effect& e = effects[i];
            if(e.name == "DefeatHeartExplosion" && e.event == "destroy") {++explosionDestroys;if(firstExplosionDestroy < 0) firstExplosionDestroy = t;}
            if(e.name == "DefeatSwirl" && e.event == "create")
            {
                ++swirlCreates;swirlCreateTime = t;swirlColourGiven = e.hasColour;swirlColour = e.colour;
            }
            if(e.name == "DefeatSwirl" && e.event == "move")
            {
                ++swirlMoves;
                float distance = e.position.y - mode.mDefeatHeartPosition.y;
                if(distance < lastSwirlDistance) swirlMonotonic = false;
                lastSwirlDistance = distance;
            }
            if(e.name == "DefeatSwirl" && e.event == "destroy") {++swirlDestroys;swirlDestroyTime = t;}
        }
        if(!wasFinished && mode.mDefeatSequence.isFinished()) {finishTime = t;}
    }
};

int main()
{
    // Timeline boundaries
    check(DS::phaseAt(-1.0f) == DS::Phase::Inactive, "before the start nothing runs");
    check(DS::phaseAt(0.0f) == DS::Phase::Explosion && DS::phaseAt(15.49f) == DS::Phase::Explosion, "explosion phase 0 to 15.5");
    check(DS::phaseAt(15.5f) == DS::Phase::Swirl && DS::phaseAt(18.49f) == DS::Phase::Swirl, "swirl phase 15.5 to 18.5");
    check(DS::phaseAt(18.5f) == DS::Phase::Fade && DS::phaseAt(29.49f) == DS::Phase::Fade, "fade phase until 29.5");
    check(DS::phaseAt(29.5f) == DS::Phase::Finished && DS::phaseAt(100.0f) == DS::Phase::Finished, "finished from 29.5");
    check(DS::isExplosionEffectActiveAt(0.0f) && DS::isExplosionEffectActiveAt(14.99f) && !DS::isExplosionEffectActiveAt(15.0f), "explosion effect lasts 15 s");
    check(!DS::isSwirlActiveAt(15.49f) && DS::isSwirlActiveAt(15.5f) && DS::isSwirlActiveAt(18.49f) && !DS::isSwirlActiveAt(18.5f), "swirl active 15.5 to 18.5");
    check(near(DS::swirlProgressAt(15.5f), 0.0f) && near(DS::swirlProgressAt(17.0f), 0.5f) && near(DS::swirlProgressAt(18.5f), 1.0f), "swirl progress is linear over 3 s");
    check(near(DS::redTintAlphaAt(0.0f), 0.35f) && near(DS::redTintAlphaAt(14.99f), 0.35f), "red tint during the explosion");
    check(near(DS::redTintAlphaAt(15.25f), 0.175f) && near(DS::redTintAlphaAt(15.5f), 0.0f) && near(DS::redTintAlphaAt(20.0f), 0.0f), "red tint fades out after the explosion");
    check(near(DS::blackAlphaAt(19.5f), 0.0f) && near(DS::blackAlphaAt(19.0f), 0.0f), "no black before 19.5 s");
    check(near(DS::blackAlphaAt(24.0f), 0.5f) && near(DS::blackAlphaAt(28.5f), 1.0f) && near(DS::blackAlphaAt(29.5f), 1.0f), "fade to black takes 9 s");
    check(DS::isFirstSubtitleVisibleAt(0.0f) && DS::isFirstSubtitleVisibleAt(14.99f) && !DS::isFirstSubtitleVisibleAt(15.0f), "first subtitle 0 to 15 s");
    check(!DS::isSecondSubtitleVisibleAt(20.49f) && DS::isSecondSubtitleVisibleAt(20.5f) && DS::isSecondSubtitleVisibleAt(29.5f), "second subtitle from 20.5 s");

    // One-shot guard, input gate, step limit
    DefeatSequence sequence;
    check(!sequence.isStarted() && !sequence.blocksInput(), "input is not blocked before the start");
    check(!sequence.advance(1.0f) && near(sequence.getElapsed(), 0.0f), "a sequence that was not started does not advance");
    check(sequence.start(2, 17, 23), "first start request is accepted");
    check(sequence.blocksInput() && sequence.isHeartKnown() && sequence.isSwirlWanted(), "started: input blocked, heart known, swirl wanted");
    check(!sequence.start(3, 5, 6), "second start request is ignored");
    check(sequence.getConquerorSeatId() == 2 && sequence.getHeartTileX() == 17 && sequence.getHeartTileY() == 23, "second request did not change the data");
    sequence.advance(10.0f);
    check(near(sequence.getElapsed(), DefeatSequenceSettings::MAX_STEP), "one slow frame advances at most the step limit");
    sequence.advance(-3.0f);
    check(near(sequence.getElapsed(), DefeatSequenceSettings::MAX_STEP), "negative time is ignored");
    int ends = 0;
    for(int i = 0; i < 1000; ++i) if(sequence.advance(0.1f)) ++ends;
    check(ends == 1, "the end is reported exactly once");
    check(sequence.isFinished() && sequence.blocksInput() && !sequence.start(1, 1, 1), "after the end input stays blocked and a restart is refused");
    DefeatSequence unknown;
    unknown.start(-1, -1, -1);
    check(!unknown.isSwirlWanted() && !unknown.isHeartKnown(), "-1 conqueror: no swirl; -1 heart: position unknown");
    DefeatSequence halfKnown;
    halfKnown.start(0, 4, -1);
    check(!halfKnown.isHeartKnown() && halfKnown.isSwirlWanted(), "a heart with only one coordinate counts as unknown; seat 0 is a valid conqueror");

    // The GameMode driver over a whole sequence at 60 frames per second
    {
        Run run;run.begin(1, 17, 23);
        for(int i = 0; i < 60 * 40; ++i) run.frame(1.0f / 60.0f);
        check(run.explosionDestroys == 1 && run.firstExplosionDestroy >= 14.99f && run.firstExplosionDestroy < 15.1f, "explosion effect is removed once, at about 15 s");
        check(run.swirlCreates == 1 && run.swirlCreateTime >= 15.5f && run.swirlCreateTime < 15.6f, "swirl is created once at about 15.5 s");
        check(run.swirlColourGiven && near(run.swirlColour.r, 0.2f) && near(run.swirlColour.g, 0.9f) && near(run.swirlColour.b, 0.1f) && near(run.swirlColour.a, 1.0f), "swirl uses the seat colour of the conqueror with full opacity");
        check(run.swirlMoves > 100 && run.swirlMonotonic && run.lastSwirlDistance > 12.0f && run.lastSwirlDistance <= DefeatSequenceSettings::SWIRL_DISTANCE + 0.01f, "swirl moves away from the heart along the camera direction");
        check(run.swirlDestroys == 1 && run.swirlDestroyTime >= 18.5f && run.swirlDestroyTime < 18.6f, "swirl is removed once, at about 18.5 s");
        check(run.finishTime >= 29.5f && run.finishTime < 29.6f, "the end is reached at 29.5 s");
        int finishedLogs = 0;for(size_t i = 0; i < gLog.size(); ++i) if(gLog[i] == "Defeat sequence finished") ++finishedLogs;
        check(finishedLogs == 1, "the finished hook runs exactly once");
        check(run.uiShownAfterHide == 0, "windows that the game shows again are hidden in the same frame");
        check(!run.sequenceWindowHidden, "the windows of the sequence itself are never hidden while the sequence runs");
        check(run.mode.mDebriefingShown == 1 && !run.subtitle.visible && !run.marker.visible, "the debriefing is opened once and takes the place of subtitle and marker");
        check(near(run.fade.alpha, 1.0f) && near(run.tint.alpha, 0.0f), "the screen ends black without tint");
        check(run.subtitle.text == "That's it for today. Until next time.", "the second subtitle stays until the end");
    }
    {
        Run run;run.begin(1, 17, 23);
        for(int i = 0; i < 60 * 5; ++i) run.frame(1.0f / 60.0f);
        check(run.subtitle.text == "Your dungeon heart has been destroyed." && near(run.tint.alpha, 0.35f) && near(run.fade.alpha, 0.0f), "after 5 s: first subtitle, red tint, no fade");
        check(run.explosionDestroys == 0 && run.swirlCreates == 0, "after 5 s the explosion still runs and there is no swirl");
        for(int i = 0; i < 60 * 12; ++i) run.frame(1.0f / 60.0f);
        check(run.subtitle.text == "" && run.swirlCreates == 1, "at 17 s no subtitle and the swirl runs");
        for(int i = 0; i < 60 * 2; ++i) run.frame(1.0f / 60.0f);
        check(run.subtitle.text == "" && near(run.fade.alpha, 0.0f), "at 19 s there is no subtitle and no fade yet");
        for(int i = 0; i < 60 * 2; ++i) run.frame(1.0f / 60.0f);
        check(run.subtitle.text == "That's it for today. Until next time." && run.fade.alpha > 0.15f && run.fade.alpha < 0.18f, "at 21 s the fade has begun and the second subtitle shows");
    }
    {
        Run run;run.begin(-1, 17, 23);
        for(int i = 0; i < 60 * 35; ++i) run.frame(1.0f / 60.0f);
        check(run.swirlCreates == 0 && run.swirlMoves == 0, "unknown conqueror (-1): no swirl");
        check(run.finishTime >= 29.5f, "the sequence still ends without a swirl");
    }
    {
        Run run;run.begin(7, 17, 23);
        for(int i = 0; i < 60 * 35; ++i) run.frame(1.0f / 60.0f);
        check(run.swirlCreates == 0 && run.swirlMoves == 0 && run.finishTime >= 29.5f, "conqueror seat that does not exist: no swirl, no crash");
    }
    {
        Run run;run.begin(1, 17, 23);
        for(int i = 0; i < 60 * 8; ++i) run.frame(1.0f / 60.0f);
        run.mode.stopDefeatEffects();
        int destroys = 0;for(size_t i = 0; i < RenderManager::getSingleton().effects.size(); ++i) if(RenderManager::getSingleton().effects[i].event == "destroy") ++destroys;
        check(destroys == 1 && !run.mode.mDefeatExplosionEffectActive, "leaving the mode removes the running effect");
    }
    std::cout << "CHECKS=" << gChecks << " FAILURES=" << gFailures << '\n';
    return gFailures ? 1 : 0;
}
'''

constants = '\n'.join(constant(name) for name in (
    'DEFEAT_EXPLOSION_EFFECT_NAME', 'DEFEAT_SWIRL_EFFECT_NAME', 'DEFEAT_FIRST_SUBTITLE', 'DEFEAT_SECOND_SUBTITLE'))
probe = (probe.replace('CONSTANTS', constants)
    .replace('UPDATE', function(game_mode, 'void GameMode::updateDefeatSequence('))
    .replace('SWIRL\n', function(game_mode, 'void GameMode::startDefeatSwirl(') + '\n')
    .replace('STOP', function(game_mode, 'void GameMode::stopDefeatEffects('))
    .replace('HIDE', function(game_mode, 'void GameMode::hideInterfaceForDefeat('))
    .replace('FINISHED', function(game_mode, 'void GameMode::onDefeatSequenceFinished(')))

# Static wiring checks on the production sources.
guard = '{\n    if(mDefeatSequence.blocksInput())\n'
for signature in ('bool GameMode::mouseMoved(', 'bool GameMode::mousePressed(', 'bool GameMode::mouseReleased(',
                  'bool GameMode::keyPressed(', 'bool GameMode::keyReleased('):
    body = function(game_mode, signature)
    assert body[body.index('{'):].startswith(guard), signature
    assert 'return true;' in body[:body.index('resetIdleHand();')], signature
print('WIRING OK: mouse move/press/release and key press/release are gated first and return before any game code while the sequence runs')
assert 'if(mDefeatSequence.blocksInput())' in function(game_mode, 'void GameMode::updateCameraControls(')
assert 'updateDefeatSequence(evt.timeSinceLastFrame);' in function(game_mode, 'void GameMode::onFrameStarted(')
start = function(game_mode, 'void GameMode::startDefeatSequence(')
assert 'if(!mDefeatSequence.start(' in start and start.index('return;') < start.index('cutCameraToHeart')
assert 'mDefeatSequence.isHeartKnown()' in start and 'getCameraViewTarget()' in start
assert 'onDefeatSequenceFinished' in game_mode_header
assert 'startDefeatSequence(conquerorSeatId, heartTileX, heartTileY)' in client
print('WIRING OK: camera controls blocked, frame update called, start is one-shot, unknown heart keeps the camera target')
for name in ('HeartExplosion', 'DefeatSwirl'):
    script = (repo / ('particles/' + name + '.particle')).read_text()
    assert 'particle_system ' + name in script
added = sequence_header + function(game_mode, 'void GameMode::startDefeatSequence(') + function(game_mode, 'void GameMode::updateDefeatSequence(')
assert re.search(r'\bauto\b', added) is None
print('STYLE OK: no auto in the new code')

with tempfile.TemporaryDirectory(prefix='odp-defeat-sequence-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(probe)
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/std:c++14', '/I', str(repo / 'source'), 'check.cpp', '/Fecheck.exe'],
                   cwd=work, check=True)
    # Windows may block a freshly compiled executable (WinError 4551) for a moment
    for attempt in range(4):
        try:
            subprocess.run([str(work / 'check.exe')], cwd=work, check=True)
            break
        except OSError as error:
            if attempt == 3:
                raise
            print('retrying after', error)
            time.sleep(2)
