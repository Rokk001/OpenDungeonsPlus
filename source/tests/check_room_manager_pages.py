"""R6 page elements, asset wiring, owner requests and 400 screen/scale fit cases.

This check does not compile. The companion page-events check executes production
callbacks in FINAL; it supports --source-only while the plan is in progress.
"""
from pathlib import Path
import math
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
RESOLUTIONS = ((640,480),(800,600),(1024,768),(1280,720),(1366,768),
               (1920,1080),(2560,1440),(3440,1440),(3840,2160),(7680,4320))
SCALES = (.8,.9,1.,1.1,1.2)
REQUIRED = {
    'Merchant': ('StockList','ModeButton','ProfitButton','MarginSlider','MarginLabel',
                 'Confirmation/Item','Confirmation/Name','Confirmation/Price','Confirmation/OK','Confirmation/Cancel'),
    'Ghost': ('Vessel','EctoplasmProgress','GhostBarText','GhostProductButton/Image','Product1/Image',
              'Product2/Image','GhostProductButton/Lock','Product1/Lock','Product2/Lock','Ratio0','Ratio1','Ratio2','GhostReviveButton'),
    'Tavern': ('Beer','BeerLock','BeerText','Keeper','Creature','KeeperLabel','CreatureLabel','PayerButton'),
    'Spa': ('Bath','SpaPriceText','Keeper','Creature','KeeperLabel','CreatureLabel','SpaPayerButton'),
    'Infirmary': ('PatientList','Keeper','Creature','PayerButton','HealButton','ThresholdLabel','ThresholdValue','Minus','Plus'),
    'Alchemy': ('CauldronList','Herb0','Herb1','Herb2','Herb3','HerbCount0','HerbCount1','HerbCount2','HerbCount3','ModeButton'),
    'Casino': ('CasinoPayoutButton/Image','MoneyButton/Image','SmilesLabel','MoneyLabel'),
    'Workshop': ('Workshops','Orders','OrdersLabel','MoveUp','MoveDown'),
}
SAMPLES = {
    'Merchant/MarginLabel':'50 %','Merchant/ModeButton':'Fair','Merchant/ProfitButton':'Profit',
    'Merchant/Confirmation/Name':'Crown of Iron Resolve','Merchant/Confirmation/Price':'1000000',
    'Ghost/GhostBarText':'100.0 / 100.0','Ghost/Ratio2':'6 : 1','Spa/SpaPriceText':'1000000',
    'Alchemy/HerbCount0':'4294967295','Alchemy/HerbCount1':'4294967295',
    'Alchemy/HerbCount2':'4294967295','Alchemy/HerbCount3':'4294967295',
    'Tavern/BeerText':'1000000','Infirmary/ThresholdValue':'100 %','Alchemy/ModeButton':'Combat potions',
}


def props(node):
    """Read direct CEGUI properties."""
    return {p.get('name'):p.get('value') for p in node.findall('Property')}


def windows(root, prefix=''):
    """Resolve actual nested paths instead of assuming controls are direct children."""
    result = {}
    for child in root.findall('Window'):
        name = prefix + child.get('name')
        result[name] = child
        result.update(windows(child, name+'/'))
    return result


def area(value, width, height, scale):
    """Resolve UDim coordinates using the production offset scaling convention."""
    n = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?',value)]
    assert len(n)==8, value
    return (n[0]*width+n[1]*scale,n[2]*height+n[3]*scale,
            n[4]*width+n[5]*scale,n[6]*height+n[7]*scale)


def fit_page(name, page, manager):
    """Check all children and visible label samples across the required screen matrix."""
    for width,height in RESOLUTIONS:
        for user in SCALES:
            raw=min(width/1024.,height/768.)*user
            scale=raw*min(1.,width/(880*raw),height/(710*raw))
            font_scale=min(width/800.,height/600.)*user
            title=20*4/3*1.35*font_scale+12*scale
            fw,fh=808*scale,710*scale-title-36*scale
            bounds=area(props(manager['Pages'])['Area'],fw,fh,scale)
            pw,ph=bounds[2]-bounds[0],bounds[3]-bounds[1]
            assert 880*scale<=width+.5 and 710*scale<=height+.5
            sizes={'':(pw,ph)}
            for path,node in page.items():
                parent=path.rpartition('/')[0]
                cw,ch=sizes[parent]
                q=props(node)
                left,top,right,bottom=area(q['Area'],cw,ch,scale)
                assert -.01<=left<right<=cw+.5,(name,path,width,height,user,'horizontal bounds')
                assert -.01<=top<bottom<=ch+.5,(name,path,width,height,user,'vertical bounds')
                bw,bh=right-left,bottom-top
                sizes[path]=(bw,bh)
                text=SAMPLES.get(name+'/'+path,q.get('Text',''))
                if not text: continue
                points=float(q.get('Font','MedievalSharp-10').rsplit('-',1)[1])
                px=points*4/3*font_scale
                if node.get('type')=='OD/Button':bw-=12*scale
                if node.get('type')=='OD/Checkbox':bw-=28*scale
                assert bw>0,(name,path,'text inset')
                line_count=max(1,math.ceil(len(text)*.52*px*1.15/bw))
                assert line_count*1.35*px<=bh+.5,(name,path,width,height,user,text,'text height',line_count,bw,bh)
                if 'WordWrap' not in q.get('HorzFormatting',''):
                    assert line_count==1,(name,path,width,height,user,text,'wrap')


def main():
    """Assert the fixed per-page R6 contract and production event/request routing."""
    manager=ET.parse(ROOT/'gui/WindowRoomManager.layout').getroot().find('Window')
    assert props(manager)['Area']=='{{0.5,-440},{0.5,-355},{0.5,440},{0.5,355}}','fixed frame design dimensions'
    manager_windows=windows(manager)
    scheme=ET.parse(ROOT/'gui/ODSkin.scheme').getroot()
    images={}
    for entry in scheme.findall('Imageset'):
        root=ET.parse(ROOT/'gui'/entry.get('filename')).getroot()
        for picture in root.findall('Image'):
            images[root.get('name')+'/'+picture.get('name')]=picture
    pages={}
    for name,required in REQUIRED.items():
        root=ET.parse(ROOT/('gui/RoomManager'+name+'Page.layout')).getroot().find('Window')
        page=windows(root);pages[name]=page
        assert root.get('type')=='DefaultWindow'
        for path in required:assert path in page,(name,path,'missing R6 element')
        for path,node in page.items():
            q=props(node)
            assert len(re.findall(r'[A-Za-z]+',q.get('Text','')))<=2,(name,path,'paragraph or long label')
            if 'Image' in q:assert q['Image'] in images,(name,path,q['Image'],'missing image')
            assert path not in ('HistoryPanel','HistoryText','EmptyText','GhostExplainText','Explanation')
        fit_page(name,page,manager_windows)
        print('PASS '+name+' elements, images and 50 screen/scale cases')
    assert pages['Ghost']['GhostReviveButton'].get('type')=='OD/Checkbox'
    assert pages['Infirmary']['HealButton'].get('type')=='OD/Checkbox'
    assert props(pages['Casino']['CasinoPayoutButton'])['ID']=='1'
    assert props(pages['Casino']['MoneyButton'])['ID']=='0'
    assert props(pages['Ghost']['GhostProductButton'])['ID']=='1'
    assert props(pages['Ghost']['Product1'])['ID']=='0'
    game=(ROOT/'source/modes/GameMode.cpp').read_text()
    merchant=(ROOT/'source/modes/GameModeMerchant.cpp').read_text()
    lab=(ROOT/'source/modes/GameModeAlchemy.cpp').read_text()
    helper=(ROOT/'source/modes/RoomManagerListItem.h').read_text()
    for text in (game,merchant,lab):
        for name,path in re.findall(r'RoomManagerWindow/Pages/(\w+)Page/([^"\n]+)"\)',text):
            if path.endswith('/'):continue
            assert path in pages[name],(name,path,'client refers to removed control')
    for callback in ('confirmMerchantItem','cancelMerchantItem','buyMerchantItem','hoverMerchantItem',
                     'cycleMerchantMode','changeMerchantMargin'):
        assert '&GameMode::'+callback in merchant,callback+' event disconnected'
    assert 'mMerchantPendingId' in merchant and 'getGold() >= price' in merchant
    assert 'mode == "profit"' in merchant and 'setVisible(mode == "profit")' in merchant
    assert 'setTooltipText(items[index].second.describe(mGameMap))' in merchant
    assert 'positionSelf()' in merchant and 'merchantItemAtPointer(list, event.position)' in merchant
    assert 'historyText(' not in merchant and '/HistoryText' not in merchant
    assert 'setSelected(seat->getGhostRevive())' in game and 'mUpdatingGhost = true' in game
    assert 'isApparatusUnlocked(*seat, nextKind)' in game and 'setEnabled(unlocked)' in game
    assert 'getLevelsPerEctoplasm(*seat)' in game and 'setProgress(' in game
    assert 'setVisible(!beerResearched)' in game
    for callback in ('cycleGhostProduct','toggleGhostRevive','cycleTavernPayer','cycleSpaPayer',
                     'cycleInfirmaryPayer','toggleInfirmaryHealing','changeInfirmaryThreshold','cycleCasinoPayout',
                     'moveTrapProductionOrderEarlier','moveTrapProductionOrderLater','cycleLabMode'):
        assert '&GameMode::'+callback in game,callback+' event disconnected'
    assert 'getCreatureProfilePortraitImage' in game and 'maxHp <= 0.0' in game and 'std::ceil(remaining)' in game
    assert 'row, images, fraction, false, 0xFFB33030' in game
    assert 'recipe->getImage()' in lab and 'getCreatureProfilePortraitImage' in lab and 'cauldron.mRemaining' in lab
    assert 'data.mHerbs.find(herb.mId)' in lab and 'setLabModeShown(data.mMode)' in lab
    assert 'mTrapProductionData.orders[selected->getID()].name << earlier' in game
    assert 'order.name == selectedName' in game and 'roomManagerTrapImage(order.type)' in game
    assert 'static_cast<float>(workshop.points) / workshop.required' in game
    for image in re.findall(r'"([A-Za-z]+(?:TrapButton|CannonButton))"',helper):
        assert 'OpenDungeonsIcons/'+image in images,image+' production icon'
    assert 'brush.render' in helper and 'std::min(1.0f, mProgress)' in helper
    server=(ROOT/'source/rooms/RoomMerchant.cpp').read_text()
    assert 'RoomMerchant::sellToKeeper' in server and 'player.pickUpEntity(bag)' in server
    print('PASS production routes, stable item identity, locks, payer/payout, patients, brewing and priority')
    print('DONE pages=8 screen_cases=400 red=0')


if __name__=='__main__':
    main()


