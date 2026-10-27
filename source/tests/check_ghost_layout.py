"""Compile the actual joined-room and deterministic cauldron placement bodies."""
from check_ghost_rules import PRELUDE, GHOST_WORLD, function, read, run_probe

# Supply room storage and retain complete production geometry functions.
def layout_fixture():
    source = read('source/rooms/RoomGhostRoom.cpp')
    declarations = r'''
//! \brief Stores cauldron geometry independently of the production placement algorithm.
struct RoomGhostRoom:Room{GameMap* map=nullptr;std::vector<Tile*> mCoveredTiles;
 //! \brief Stores the actual anchor/reservation pair.
 struct Cauldron{Tile* anchor;Creature* hunter;};std::vector<Cauldron> mCauldrons;
 //! \brief Returns the controlled map.
 GameMap* getGameMap(){return map;}
 //! \brief Runs the actual joined-room minimum-square search.
 static bool containsMinimumBlock(GameMap&,Seat*,const std::vector<Tile*>&);
 //! \brief Runs the actual interior and spacing scan.
 void layoutCauldrons();
 //! \brief Returns the actual backpack capacity.
 uint32_t getBackpackCount()const;
};
'''
    signatures = ['bool tileOrder(', 'bool cauldronOrder(', 'bool RoomGhostRoom::containsMinimumBlock(',
        'uint32_t RoomGhostRoom::getBackpackCount()', 'void RoomGhostRoom::layoutCauldrons(']
    return PRELUDE+GHOST_WORLD+declarations+''.join(function(source, sig) for sig in signatures)

# Test minimum dimensions, merged ownership, spacing, deterministic order and occupied-anchor retention.
def main():
    code = layout_fixture()+r'''
//! \brief Exercises the production geometry on exact independently enumerated rectangles.
int main(){
 Seat seat,enemy;enemy.id=2;
 const int sizes[][3]={{3,3,0},{3,4,0},{4,3,0},{4,4,1},{5,5,1},{6,6,1},{7,4,2},{7,7,4},{10,10,9}};
 for(const int (&size)[3]:sizes){GameMap map;RoomGhostRoom room;room.map=&map;room.seat=&seat;room.type=RoomType::ghostRoom;
  for(int y=0;y<size[1];++y)for(int x=0;x<size[0];++x){Tile& tile=map.tiles[{x,y}];tile.x=x;tile.y=y;tile.room=&room;tile.owner=&seat;room.mCoveredTiles.push_back(&tile);}
  check(RoomGhostRoom::containsMinimumBlock(map,&seat,room.mCoveredTiles)==(size[0]>=4&&size[1]>=4),"minimum 4x4 block");
  std::reverse(room.mCoveredTiles.begin(),room.mCoveredTiles.end());room.layoutCauldrons();check(room.mCauldrons.size()==size_t(size[2]),"exact decided cauldron count");
  check(room.getBackpackCount()==3*size[2],"global supply per cauldron");
  for(size_t i=0;i<room.mCauldrons.size();++i){Tile* a=room.mCauldrons[i].anchor;check(a->x>0&&a->y>0&&a->x+2<size[0]&&a->y+2<size[1],"2x2 interior with full edge ring");for(size_t j=0;j<i;++j){Tile* b=room.mCauldrons[j].anchor;check(std::abs(a->x-b->x)>=3||std::abs(a->y-b->y)>=3,"eight-neighbor cauldron gap");}}
  if(!room.mCauldrons.empty()){Creature hunter;Tile* anchor=room.mCauldrons.back().anchor;room.mCauldrons.back().hunter=&hunter;room.layoutCauldrons();bool retained=false;for(const RoomGhostRoom::Cauldron& c:room.mCauldrons)retained|=c.anchor==anchor&&c.hunter==&hunter;check(retained,"occupied anchor survives recomputation");room.mCoveredTiles.erase(std::remove(room.mCoveredTiles.begin(),room.mCoveredTiles.end(),anchor),room.mCoveredTiles.end());room.layoutCauldrons();check(hunter.interrupts==1,"removed occupied footprint interrupts once");}
 }
 GameMap map;Room joined;joined.type=RoomType::ghostRoom;joined.seat=&seat;std::vector<Tile*> added;
 for(int y=0;y<4;++y)for(int x=0;x<4;++x){Tile& tile=map.tiles[{x,y}];tile.x=x;tile.y=y;if(x<2){tile.room=&joined;joined.floor.push_back(&tile);}else added.push_back(&tile);}
 for(std::pair<const std::pair<int,int>,Tile>& entry:map.tiles){Tile& tile=entry.second;for(int y=-1;y<=1;++y)for(int x=-1;x<=1;++x){Tile* next=map.getTile(tile.x+x,tile.y+y);if(next!=nullptr&&next!=&tile)tile.neighbors.push_back(next);}}
 check(RoomGhostRoom::containsMinimumBlock(map,&seat,added),"adjoining own room contributes before charge");joined.seat=&enemy;check(!RoomGhostRoom::containsMinimumBlock(map,&seat,added),"enemy room cannot satisfy minimum");joined.seat=&seat;joined.type=RoomType::other;check(!RoomGhostRoom::containsMinimumBlock(map,&seat,added),"different room cannot satisfy minimum");
 std::cout<<"ghost layout: ok\n";
}
'''
    run_probe('ghost-layout', code)


# Retain the actual wall-face subdivision and mesh selection rather than counting nominal supply only.
def wall_checks():
    code = layout_fixture()
    before = r'''
//! \brief Identifies the existing cardinal wall faces.
enum ActiveSpotPlace{activeSpotCenter,activeSpotTop,activeSpotLeft,activeSpotRight,activeSpotBottom};
//! \brief Observes exact original wall mesh placement without supplying allocation decisions.
struct BuildingObject{std::string mesh;double angle;Ogre::Vector3 position;Ogre::Vector2 scale;
 //! \brief Receives the original wall-object constructor shape.
 BuildingObject(GameMap*,Room&,const std::string& name,Tile&,double rotation,bool,float,const std::string&,bool):mesh(name),angle(rotation){}
 //! \brief Returns the original object rotation.
 double getRotationAngle()const{return angle;}
 //! \brief Returns the original object mesh.
 const std::string& getMeshName()const{return mesh;}
 //! \brief Receives actual face-subdivision placement.
 void setPosition(const Ogre::Vector3& value){position=value;}
 //! \brief Receives native-width-derived subdivision scale.
 void setFurnitureScale(const Ogre::Vector2& value){scale=value;}
 //! \brief Receives normal world registration.
 void addToGameMap(GameMap*){}
 //! \brief Leaves actual rendering outside the geometry check.
 void createMesh(){}
};
'''
    bounds = read('source/gamemap/RoomObjectBounds.h')
    start = bounds.index('constexpr float degreesToRadians')
    end = bounds.index('};',bounds.index('static const MeshBounds meshBounds[]'))+2
    before += '\nnamespace RoomObjectPath{'+bounds[start:end]+'}\n'
    code = code.replace('struct RoomGhostRoom:Room{',before+'\nstruct RoomGhostRoom:Room{')
    code = code.replace(' GameMap* getGameMap(){return map;}',r'''
 std::vector<Tile*> mDecorationTiles,mHookTiles;std::vector<BuildingObject*> mWallObjects,mHookObjects;
 //! \brief Runs the actual wall mesh chooser.
 BuildingObject* notifyActiveSpotCreated(ActiveSpotPlace,Tile*);
 //! \brief Runs the actual wall-face subdivision block.
 void createWalls(GameMap* map);
 //! \brief Returns the controlled map.
 GameMap* getGameMap(){return map;}
''')
    source = read('source/rooms/RoomGhostRoom.cpp')
    update = function(source,'void RoomGhostRoom::updateActiveSpots(')
    body = update[update.index('    std::vector<Tile*> ordered='):update.index('    createCauldronObjects();')]
    code += function(source,'BuildingObject* RoomGhostRoom::notifyActiveSpotCreated(')
    code += '\nvoid RoomGhostRoom::createWalls(GameMap* map){'+body+'}\n'
    code += r'''
//! \brief Checks hooks on true full neighbor walls, including native subdivision beyond wall-face capacity.
int main(){
 Seat seat;for(int side:{4,7,10,13,16}){GameMap map;RoomGhostRoom room;room.map=&map;room.type=RoomType::ghostRoom;room.seat=&seat;
 for(int y=-1;y<=side;++y)for(int x=-1;x<=side;++x){Tile& tile=map.tiles[{x,y}];tile.x=x;tile.y=y;tile.full=x==-1||y==-1||x==side||y==side;if(!tile.full){tile.room=&room;room.mCoveredTiles.push_back(&tile);}}
 room.layoutCauldrons();room.createWalls(&map);check(room.mHookTiles.size()==room.getBackpackCount()&&room.mHookObjects.size()==room.getBackpackCount(),"three actual wall hooks per cauldron");int bells=0;std::set<BuildingObject*> objects;
 for(BuildingObject* object:room.mWallObjects){check(objects.insert(object).second,"distinct auxiliary wall object identities");if(object->mesh=="GhostBell")++bells;check(object->scale.x>0&&object->scale.x<=1&&object->scale.y==1,"native wall subdivision scale");}
 check(bells==1,"one original wall bell");check(room.mWallObjects.size()>=room.getBackpackCount()+1,"no overwritten hook map keys");}
 GameMap map;RoomGhostRoom noWall;noWall.map=&map;noWall.seat=&seat;for(int y=-1;y<=4;++y)for(int x=-1;x<=4;++x){Tile& tile=map.tiles[{x,y}];tile.x=x;tile.y=y;if(x>=0&&x<4&&y>=0&&y<4){tile.room=&noWall;noWall.mCoveredTiles.push_back(&tile);}}noWall.layoutCauldrons();noWall.createWalls(&map);
 int rackBells=0;for(BuildingObject* object:noWall.mWallObjects)if(object->mesh=="GhostBell")++rackBells;
 check(noWall.mHookObjects.size()==3&&noWall.mHookTiles.size()==3&&noWall.getBackpackCount()==3,"free-standing room keeps all three hooks on room-edge racks");check(rackBells==1,"free-standing room keeps its bell on a room-edge rack");
 for(Tile* tile:noWall.mHookTiles)check(tile->x==0||tile->y==0||tile->x==3||tile->y==3,"rack hooks stand on the room edge ring, not on the cauldron tiles");
 std::cout<<"actual wall hook placement and free-standing room-edge racks: ok\n";
}
'''
    run_probe('ghost-wall-layout',code)

if __name__ == '__main__':
    main()
    wall_checks()
