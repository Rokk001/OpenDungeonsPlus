"""Compile the production cot layout and minimum-square methods against rectangle fixtures."""
from check_infirmary_rules import PRELUDE, function, read, room_declaration, run_probe

# Determine wall accessories from the documented centre-and-wall fixture geometry.
def accessory_cells(width, height):
    floor = {(x, y) for x in range(width) for y in range(height)}
    centres = []
    for x, y in sorted(floor):
        neighbors = {(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy}
        if neighbors <= floor and not neighbors.intersection(centres):
            centres.append((x, y))
    accessories = set()
    for x, y in centres:
        for dx, dy in ((-1, 0), (1, 0), (0, 1)):
            if (x + 2 * dx, y + 2 * dy) not in floor:
                accessories.add((x + dx, y + dy))
            if ((x + 3 * dx, y + 3 * dy) not in floor and
                    all((x + 2 * dx + k * abs(dy), y + 2 * dy + k * abs(dx)) in floor for k in (-1, 0, 1))):
                accessories.add((x + 2 * dx, y + 2 * dy))
    return sorted(accessories)

# Run production placement and independently verify occupancy, paths, preservation and build validation.
def main():
    source = read("source/rooms/RoomInfirmary.cpp")
    code = PRELUDE + room_declaration()
    code += function(source, "void RoomInfirmary::layoutCots(")
    code += function(source, "bool RoomInfirmary::containsMinimumBlock(")
    code += r"""
//! \brief Creates north/east/west walls and an open southern corridor.
void terrain(GameMap& map,RoomInfirmary& room,int width,int height){
 for(int x=-1;x<=width;++x)for(int y=-1;y<=height;++y){Tile tile={x,y};tile.full=!(x>=0&&x<width&&y==-1);map.tiles[{x,y}]=tile;}
 for(int x=0;x<width;++x)for(int y=0;y<height;++y){Tile* tile=map.getTile(x,y);tile->full=false;tile->room=&room;room.mCoveredTiles.push_back(tile);}
 const int dx[]={-1,1,0,0},dy[]={0,0,-1,1};
 for(std::pair<const std::pair<int,int>,Tile>& entry:map.tiles)for(int i=0;i<4;++i){Tile* neighbor=map.getTile(entry.second.x+dx[i],entry.second.y+dy[i]);if(neighbor)entry.second.neighbors.push_back(neighbor);}
}
//! \brief Verifies the produced geometry without reproducing candidate scheduling.
void reachable(RoomInfirmary& room,int width,int height){
 typedef std::pair<int,int> Cell;std::set<Cell> free,occupied,accessories;
 for(Tile* tile:room.mCoveredTiles)free.insert({tile->x,tile->y});
 for(Tile* tile:room.mAccessoryTiles)accessories.insert({tile->x,tile->y});
 for(const std::pair<const size_t,RoomInfirmary::CotInfo>& entry:room.mCots)
  for(Tile* tile:entry.second.tiles){check(tile!=nullptr,"cot within room");Cell cell(tile->x,tile->y);
   check(!accessories.count(cell),"cot avoids wall accessory");check(occupied.insert(cell).second,"cot footprints disjoint");check(free.erase(cell)==1,"cot belongs to floor");}
 std::set<Cell> seen;std::queue<Cell> pending;for(const Cell& cell:free)if(cell.second==0){seen.insert(cell);pending.push(cell);}
 const int dx[]={-1,1,0,0},dy[]={0,0,-1,1};
 while(!pending.empty()){Cell cell=pending.front();pending.pop();for(int i=0;i<4;++i){Cell next(cell.first+dx[i],cell.second+dy[i]);if(free.count(next)&&seen.insert(next).second)pending.push(next);}}
 check(seen==free,"every free/accessory tile entrance-connected");
 for(const std::pair<const size_t,RoomInfirmary::CotInfo>& entry:room.mCots){bool touches=false;
  for(Tile* tile:entry.second.tiles)for(int i=0;i<4;++i)if(seen.count({tile->x+dx[i],tile->y+dy[i]}))touches=true;
  check(touches,"every cot reached from free walkway");}
}
int main(){try{
"""
    for width, height, counts in ((4, 4, (1, 2, 1)), (5, 5, (3, 3, 1)),
            (5, 7, (5, 5, 1)), (7, 7, (5, 8, 2)), (3, 3, (1, 2, 0)),
            (3, 4, (2, 2, 0)), (4, 3, (2, 2, 0))):
        # Small-room counts pin the plan's totals; their mix is checked only for the absence of large cots.
        accessories = "".join(f"room.mAccessoryTiles.push_back(map.getTile({x},{y}));\n" for x, y in accessory_cells(width, height))
        code += f"{{ GameMap map;Seat seat;RoomInfirmary room(&map,&seat);terrain(map,room,{width},{height});\n" + accessories
        code += f"room.layoutCots();check(room.mCots.size()=={sum(counts)},\"{width}x{height} total\");int sizes[3]={{0,0,0}};\n"
        code += "for(const std::pair<const size_t,RoomInfirmary::CotInfo>& entry:room.mCots)++sizes[entry.second.size-1];\n"
        if width >= 4 and height >= 4:
            for index, expected in enumerate(counts):
                code += f'check(sizes[{index}]=={expected},"{width}x{height} size {index+1}");\n'
        else:
            code += 'check(sizes[2]==0,"small floor has no large cot");\n'
        code += f"reachable(room,{width},{height});\n"
        code += f'check(RoomInfirmary::containsMinimumBlock(map,&seat,room.mCoveredTiles)=={str(width>=4 and height>=4).lower()},"minimum block {width}x{height}");\n'
        code += r"""
 const size_t occupied=room.mCots.begin()->first;const RoomInfirmary::CotInfo saved=room.mCots.at(occupied);
 Creature patient;room.mPatients[occupied].creature=&patient;room.layoutCots();
 check(room.mCots.count(occupied)&&room.mCots.at(occupied).tiles==saved.tiles,"patient cot preserved");
 room.mPatients[occupied].creature=nullptr;room.mPatients[occupied].reservedBy=&patient;room.layoutCots();
 check(room.mCots.count(occupied)&&room.mCots.at(occupied).tiles==saved.tiles,"reserved cot preserved");
"""
        code += f"reachable(room,{width},{height});}}\n"
    code += r"""
 {GameMap map;Seat seat;RoomInfirmary room(&map,&seat);terrain(map,room,4,4);for(int x=0;x<4;++x)map.getTile(x,-1)->full=true;
  room.layoutCots();check(room.mCots.empty(),"no entrance means no cots");}
 {GameMap map;Seat seat,enemy;RoomInfirmary room(&map,&seat);terrain(map,room,4,4);
  std::vector<Tile*> extension;for(Tile* tile:room.mCoveredTiles)if(tile->y==0)extension.push_back(tile);
  check(RoomInfirmary::containsMinimumBlock(map,&seat,extension),"joined own floor meets 4x4 rule");
  check(!RoomInfirmary::containsMinimumBlock(map,&enemy,extension),"enemy floor cannot satisfy build rule");}
 std::cout<<"infirmary layout: ok\n";
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
"""
    run_probe("infirmary-layout", code)

if __name__ == "__main__":
    main()
