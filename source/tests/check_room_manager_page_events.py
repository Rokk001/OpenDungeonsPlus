"""Exercise production Room Manager page callbacks with GUI/network boundary stubs.

Use --source-only during plan work. FINAL runs this without that flag in the
compiler environment. No game build, game instance or rendering is performed.
"""
from pathlib import Path
import re
import sys
from item_probe_support import compile_and_run

ROOT = Path(__file__).resolve().parents[2]
GROUPS = {
    'GameModeMerchant.cpp': ('changeMerchantMargin','cycleMerchantMode','setMerchantSettingsShown',
        'refreshMerchantSelection','confirmMerchantItem','cancelMerchantItem','buyMerchantItem','hoverMerchantItem'),
    'GameMode.cpp': ('sendInfirmarySettings','cycleInfirmaryPayer','toggleInfirmaryHealing','changeInfirmaryThreshold',
        'cycleTavernPayer','setTavernPayerShown','cycleSpaPayer','setSpaWindowShown','cycleCasinoPayout','setCasinoPayoutShown',
        'cycleGhostProduct','toggleGhostRevive','setGhostRoomSettingsShown','updateTrapProductionButtons',
        'moveTrapProductionOrder','moveTrapProductionOrderEarlier','moveTrapProductionOrderLater'),
    'GameModeAlchemy.cpp': ('cycleLabMode','setLabModeShown'),
}


def function(text, signature):
    """Extract a whole production callback, including every guard and request write."""
    start=text.index(signature)
    opening=text.index('{',start)
    depth,end=1,opening+1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}')
        end+=1
    return text[start:end]


METHODS=[]
DECLARATIONS=[]
for filename,names in GROUPS.items():
    text=(ROOT/'source/modes'/filename).read_text()
    for name in names:
        match=re.search(r'(?:bool|void) GameMode::'+name+r'\(',text)
        assert match,name
        method=function(text,match.group())
        METHODS.append(method)
        declaration=method[:method.index('{')].strip().replace('GameMode::','')
        declaration=re.sub(r'const CEGUI::EventArgs&(?:\s+\w+)?',r'\g<0> = {}',declaration)
        DECLARATIONS.append(declaration+';')
assert len(METHODS)==27,'fixed production callback inventory'

STUBS=r'''
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace Helper {
template<class T> std::string toString(const T& value) { std::ostringstream stream;stream<<value;return stream.str(); }
}
namespace CEGUI {
struct EventArgs { virtual ~EventArgs() {} };
struct Vector2f { float d_x,d_y;Vector2f(float x=0,float y=0):d_x(x),d_y(y){} };
class Window;
struct WindowEventArgs : EventArgs { Window* window;explicit WindowEventArgs(Window* w):window(w){} };
enum {LeftButton=0,RightButton=1};
struct MouseEventArgs : WindowEventArgs { int button;Vector2f position;explicit MouseEventArgs(Window* w):WindowEventArgs(w),button(LeftButton){} };
struct Tooltip { int positions=0;void positionSelf(){++positions;} };
struct ListboxItem {
    unsigned id;bool disabled;std::string tooltip;
    explicit ListboxItem(unsigned value=0):id(value),disabled(false){}
    unsigned getID()const{return id;}bool isDisabled()const{return disabled;}
    const std::string& getTooltipText()const{return tooltip;}
};
class Window {
public:
    std::string name,text,tooltip;unsigned id=0;bool selected=false,enabled=true,visible=false;float value=0,alpha=1;
    std::map<std::string,std::string> properties;
    std::map<std::string,std::unique_ptr<Window> > children;
    ListboxItem* pointerItem=nullptr;ListboxItem* selectedItem=nullptr;Tooltip tip;
    explicit Window(const std::string& n="root"):name(n){}
    Window* getChild(const std::string& path) {
        const std::size_t slash=path.find('/');const std::string key=path.substr(0,slash);
        if(!children.count(key))children[key].reset(new Window(key));
        Window* result=children[key].get();return slash==std::string::npos?result:result->getChild(path.substr(slash+1));
    }
    const std::string& getName()const{return name;}unsigned getID()const{return id;}
    void setText(const std::string& s){text=s;}void setProperty(const std::string& key,const std::string& s){properties[key]=s;}
    void show(){visible=true;}void hide(){visible=false;}void moveToFront(){}void setVisible(bool v){visible=v;}
    void setEnabled(bool v){enabled=v;}bool isDisabled()const{return !enabled;}void setAlpha(float a){alpha=a;}
    bool isSelected()const{return selected;}void setSelected(bool v){selected=v;}
    float getCurrentValue()const{return value;}void setCurrentValue(float v){value=v;}
    ListboxItem* getFirstSelectedItem(){return selectedItem;}
    void setTooltipText(const std::string& s){tooltip=s;}Tooltip* getTooltip(){return &tip;}
};
typedef Window MultiColumnList;typedef Window Slider;typedef Window ToggleButton;
}
CEGUI::ListboxItem* merchantItemAtPointer(CEGUI::MultiColumnList* list,const CEGUI::Vector2f&){return list->pointerItem;}
enum class GhostProduct:unsigned {research=0,mana=1,crystal=2};
enum class TavernPayer:unsigned {keeper=0,creature=1};
enum class SpaPayer:unsigned {keeper=0,creature=1};
enum class CasinoPayout:unsigned {money=0,smiles=1,nbValues=2};
struct Seat {
    double gold=0;int lab=0;GhostProduct product=GhostProduct::mana;bool revive=false;
    bool unlocked[3]={false,true,false};
    double getGold()const{return gold;}int getLabMode()const{return lab;}void setLabMode(int v){lab=v;}
    GhostProduct getGhostProduct()const{return product;}void setGhostProduct(GhostProduct v){product=v;}
    bool getGhostRevive()const{return revive;}void setGhostRevive(bool v){revive=v;}
};
struct Player { Seat* seat;explicit Player(Seat* s):seat(s){}Seat* getSeat(){return seat;} };
struct GameMap { Player* player;explicit GameMap(Player* p):player(p){}Player* getLocalPlayer(){return player;} };
struct RoomGhostRoom { static bool isApparatusUnlocked(const Seat& s,GhostProduct p){return s.unlocked[static_cast<unsigned>(p)];} };
struct ItemInstance {
    double price;std::string name,image;
    ItemInstance(double p=0,const std::string& n="Item",const std::string& i="Test"):price(p),name(n),image(i){}
    double getPrice(GameMap*)const{return price;}std::string getDisplayName(GameMap*)const{return name;}
    std::string getImageName()const{return image;}
};
struct Config { int32_t getRoomConfigInt32(const std::string& key){
    if(key=="InfirmaryDischargeMinPercent")return 40;
    if(key=="InfirmaryDischargeMaxPercent")return 100;
    if(key=="InfirmaryDischargeStepPercent")return 10;
    throw std::runtime_error("unmodelled config: "+key);
} };
enum class ClientNotificationType {askMerchantBuy,askMerchantSettings,askInfirmarySettings,askTavernPayer,
    askSpaPayer,askCasinoPayout,askGhostRoomSettings,askMoveTrapProductionOrder,askLabSetting};
struct ODPacket { std::vector<std::string> values;template<class T>ODPacket& operator<<(const T& v){values.push_back(Helper::toString(v));return *this;} };
struct ClientNotification { ClientNotificationType type;ODPacket mPacket;explicit ClientNotification(ClientNotificationType t):type(t){} };
struct ODClient {
    std::vector<ClientNotification> requests;
    static ODClient& getSingleton(){static ODClient instance;return instance;}
    void queueClientNotification(ClientNotification* p){requests.push_back(*p);delete p;}
    void append(ODPacket&){}
    template<class T,class... Rest>void append(ODPacket& p,const T& v,const Rest&... rest){p<<v;append(p,rest...);}
    template<class... Args>void queueClientNotification(ClientNotificationType type,const Args&... args){
        ClientNotification* p=new ClientNotification(type);append(p->mPacket,args...);queueClientNotification(p);
    }
};
struct Order { std::string name;explicit Order(const std::string& n):name(n){} };
struct TrapData {std::vector<Order> orders;};
const float MARGIN_STEP=5.0f;
@@PAYER@@
class GameMode {
public:
    CEGUI::Window* mRootWindow;GameMap* mGameMap;Config config;bool connected=true;
    std::vector<std::pair<uint32_t,ItemInstance> > mMerchantItems;
    uint32_t mMerchantPendingId=0;bool mMerchantConfirmationOpen=false,mMerchantUpdating=false;
    int32_t mMerchantMarginShown=10;std::string mMerchantModeShown="fair";
    int32_t mInfirmaryPayer=0,mInfirmaryThreshold=100;bool mInfirmaryHealOn=true,mUpdatingInfirmary=false;
    int mTavernX=3,mTavernY=4,mSpaX=5,mSpaY=6,mCasinoX=7,mCasinoY=8,mGhostRoomX=9,mGhostRoomY=10;
    uint32_t mTavernPayer=0,mSpaPayer=0,mCasinoPayout=1;bool mUpdatingGhost=false;
    TrapData mTrapProductionData;bool mProductionRequestPending=false;float mProductionRefreshElapsed=0;
    unsigned ghostRefreshes=0;
    GameMode(CEGUI::Window* root,GameMap* map):mRootWindow(root),mGameMap(map){}
    bool isConnected()const{return connected;}void refreshGhostRoomWindow(){++ghostRefreshes;}
    @@DECLARATIONS@@
};
@@METHODS@@
void expect(bool condition,const char* message){if(!condition)throw std::runtime_error(message);}
void packet(ClientNotificationType type,const std::vector<std::string>& values){
    const ClientNotification& request=ODClient::getSingleton().requests.back();
    expect(request.type==type,"request type");expect(request.mPacket.values==values,"request payload");
}
int main(){try {
    Seat seat;Player player(&seat);GameMap map(&player);CEGUI::Window root;GameMode game(&root,&map);
    ODClient& client=ODClient::getSingleton();
    CEGUI::Window* stock=root.getChild("RoomManagerWindow/Pages/MerchantPage/StockList");
    CEGUI::Window* confirmation=root.getChild("RoomManagerWindow/Pages/MerchantPage/Confirmation");
    CEGUI::ListboxItem first(41),second(99),empty;empty.disabled=true;first.tooltip="Item bonuses";
    game.mMerchantItems.push_back(std::make_pair(41,ItemInstance(250,"Crown","CrownRare")));
    game.mMerchantItems.push_back(std::make_pair(99,ItemInstance(5,"Ring","RingCommon")));
    stock->pointerItem=&first;CEGUI::MouseEventArgs click(stock);
    game.confirmMerchantItem(click);
    expect(confirmation->visible && !confirmation->getChild("OK")->enabled,"unaffordable confirmation still opens");
    expect(confirmation->getChild("Name")->text=="Crown" && confirmation->getChild("Price")->text=="250","confirmed item and price");
    game.buyMerchantItem();expect(client.requests.empty(),"disabled OK cannot buy");
    seat.gold=250;game.refreshMerchantSelection();expect(confirmation->getChild("OK")->enabled,"gold enables OK");
    stock->pointerItem=&second;game.buyMerchantItem();packet(ClientNotificationType::askMerchantBuy,{"41"});
    expect(!confirmation->visible && !game.mMerchantConfirmationOpen,"confirmed identity bought once");
    game.buyMerchantItem();expect(client.requests.size()==1,"no double confirmation");
    game.confirmMerchantItem(click);game.cancelMerchantItem();expect(client.requests.size()==1 && !confirmation->visible,"cancel has no purchase");
    stock->pointerItem=&first;game.confirmMerchantItem(click);game.mMerchantItems.erase(game.mMerchantItems.begin());
    game.refreshMerchantSelection();expect(!confirmation->visible,"vanished good cancels instead of substituting");
    stock->pointerItem=&empty;game.confirmMerchantItem(click);expect(!confirmation->visible,"empty slot cannot confirm");
    stock->pointerItem=&first;game.hoverMerchantItem(click);expect(stock->tooltip=="Item bonuses" && stock->tip.positions==1,"hover tooltip follows pointer");
    stock->pointerItem=&empty;game.hoverMerchantItem(click);expect(stock->tooltip.empty(),"empty slot clears tooltip");
    game.setMerchantSettingsShown(20,"fair");expect(!root.getChild("RoomManagerWindow/Pages/MerchantPage/MarginSlider")->visible,"fair hides margin");
    game.setMerchantSettingsShown(25,"profit");expect(root.getChild("RoomManagerWindow/Pages/MerchantPage/MarginLabel")->visible,"profit shows margin");
    CEGUI::Window* profit=root.getChild("RoomManagerWindow/Pages/MerchantPage/ProfitButton");CEGUI::WindowEventArgs profitClick(profit);
    game.cycleMerchantMode(profitClick);packet(ClientNotificationType::askMerchantSettings,{"25","profit"});
    CEGUI::Window* fair=root.getChild("RoomManagerWindow/Pages/MerchantPage/ModeButton");CEGUI::WindowEventArgs fairClick(fair);
    game.cycleMerchantMode(fairClick);packet(ClientNotificationType::askMerchantSettings,{"25","fair"});
    root.getChild("RoomManagerWindow/Pages/MerchantPage/MarginSlider")->value=13;game.changeMerchantMargin();
    packet(ClientNotificationType::askMerchantSettings,{"15","profit"});
    std::size_t before=client.requests.size();game.mMerchantUpdating=true;game.changeMerchantMargin();expect(client.requests.size()==before,"snapshot does not echo settings");game.mMerchantUpdating=false;
    CEGUI::Window ghost;ghost.id=0;CEGUI::WindowEventArgs ghostClick(&ghost);
    game.cycleGhostProduct(ghostClick);expect(client.requests.size()==before,"locked product sends nothing");
    seat.unlocked[0]=true;game.cycleGhostProduct(ghostClick);packet(ClientNotificationType::askGhostRoomSettings,{"9","10","0","0","1"});
    root.getChild("RoomManagerWindow/Pages/GhostPage/GhostReviveButton")->selected=true;
    game.toggleGhostRevive();packet(ClientNotificationType::askGhostRoomSettings,{"9","10","0","1","1"});
    before=client.requests.size();game.mUpdatingGhost=true;game.toggleGhostRevive();expect(client.requests.size()==before,"revive snapshot guard");game.mUpdatingGhost=false;
    game.setGhostRoomSettingsShown(9,10,2,false);expect(seat.product==GhostProduct::crystal && !seat.revive,"ghost reply adopted");
    game.setGhostRoomSettingsShown(0,0,0,true);expect(seat.product==GhostProduct::crystal,"stale ghost reply ignored");
    game.setTavernPayerShown(3,4,0);game.cycleTavernPayer();packet(ClientNotificationType::askTavernPayer,{"3","4","1"});
    game.setTavernPayerShown(3,4,1);game.cycleTavernPayer();packet(ClientNotificationType::askTavernPayer,{"3","4","0"});
    game.setSpaWindowShown(5,6,0,5);game.cycleSpaPayer();packet(ClientNotificationType::askSpaPayer,{"5","6","1","1"});
    game.setSpaWindowShown(5,6,1,5);expect(root.getChild("RoomManagerWindow/Pages/SpaPage/SpaPriceText")->text=="5","bath price");
    CEGUI::Window money;money.id=0;CEGUI::WindowEventArgs moneyClick(&money);game.cycleCasinoPayout(moneyClick);
    packet(ClientNotificationType::askCasinoPayout,{"7","8","0","1"});
    game.setCasinoPayoutShown(7,8,0);expect(root.getChild("RoomManagerWindow/Pages/CasinoPage/MoneyButton/Image")->properties["FrameEnabled"]=="True","money picture framed");
    game.setCasinoPayoutShown(7,8,1);expect(root.getChild("RoomManagerWindow/Pages/CasinoPage/CasinoPayoutButton/Image")->properties["FrameEnabled"]=="True","smiles picture framed");
    game.cycleInfirmaryPayer();packet(ClientNotificationType::askInfirmarySettings,{"1","100","1"});
    root.getChild("RoomManagerWindow/Pages/InfirmaryPage/HealButton")->selected=false;game.toggleInfirmaryHealing();packet(ClientNotificationType::askInfirmarySettings,{"1","100","0"});
    CEGUI::Window minus("Minus"),plus("Plus");CEGUI::WindowEventArgs minusClick(&minus),plusClick(&plus);
    game.changeInfirmaryThreshold(minusClick);packet(ClientNotificationType::askInfirmarySettings,{"1","90","0"});
    for(int i=0;i<10;++i)game.changeInfirmaryThreshold(minusClick);expect(game.mInfirmaryThreshold==40,"discharge minimum");
    for(int i=0;i<10;++i)game.changeInfirmaryThreshold(plusClick);expect(game.mInfirmaryThreshold==100,"discharge maximum");
    before=client.requests.size();game.changeInfirmaryThreshold(plusClick);expect(client.requests.size()==before,"boundary sends no change");
    for(int mode=0;mode<3;++mode){game.setLabModeShown(mode);game.cycleLabMode();packet(ClientNotificationType::askLabSetting,{Helper::toString((mode+1)%3)});}
    game.setLabModeShown(9);expect(seat.lab==2,"invalid lab reply ignored");
    game.mTrapProductionData.orders.push_back(Order("spikes"));game.mTrapProductionData.orders.push_back(Order("gas"));
    CEGUI::Window* orders=root.getChild("RoomManagerWindow/Pages/WorkshopPage/Orders");CEGUI::ListboxItem order(0);orders->selectedItem=&order;
    game.updateTrapProductionButtons();expect(!root.getChild("RoomManagerWindow/Pages/WorkshopPage/MoveUp")->enabled && root.getChild("RoomManagerWindow/Pages/WorkshopPage/MoveDown")->enabled,"first order arrow bounds");
    game.moveTrapProductionOrderLater(CEGUI::EventArgs());packet(ClientNotificationType::askMoveTrapProductionOrder,{"spikes","0"});
    expect(root.getChild("RoomManagerWindow/Pages/WorkshopPage/MoveDown")->enabled,"pending snapshot preserves responsive priority controls");
    game.mProductionRequestPending=false;order.id=1;game.updateTrapProductionButtons();expect(root.getChild("RoomManagerWindow/Pages/WorkshopPage/MoveUp")->enabled && !root.getChild("RoomManagerWindow/Pages/WorkshopPage/MoveDown")->enabled,"last order arrow bounds");
    game.moveTrapProductionOrderEarlier(CEGUI::EventArgs());packet(ClientNotificationType::askMoveTrapProductionOrder,{"gas","1"});
    orders->selectedItem=nullptr;before=client.requests.size();game.moveTrapProductionOrder(true);expect(client.requests.size()==before,"no selected priority sends nothing");
    game.connected=false;before=client.requests.size();game.buyMerchantItem();game.changeMerchantMargin();game.cycleLabMode();game.moveTrapProductionOrder(false);expect(client.requests.size()==before,"disconnected guarded actions");
    std::cout<<"PASS 27 production callbacks: merchant confirmation, margins, products, revive, payers, healing, discharge, lab modes, payout and priorities\n";
    return 0;
} catch(const std::exception& error){std::cerr<<error.what()<<"\n";return 1;}}
'''
helper=(ROOT/'source/modes/RoomManagerListItem.h').read_text()
probe=STUBS.replace('@@PAYER@@',function(helper,'inline void roomManagerPayer('))
probe=probe.replace('@@DECLARATIONS@@','\n'.join(DECLARATIONS)).replace('@@METHODS@@','\n'.join(METHODS))
assert '@@' not in probe
if '--source-only' in sys.argv:
    print('PASS 27 production page callbacks extracted; executable checks deferred to FINAL')
else:
    compile_and_run('room-manager-page-events',probe)
