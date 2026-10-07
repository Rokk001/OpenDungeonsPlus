#ifndef ROOMOBJECTBOUNDS_H
#define ROOMOBJECTBOUNDS_H

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <string>

namespace RoomObjectPath
{
struct MeshBounds
{
    const char* name;
    float minX, minY, maxX, maxY;
    float maxZ = std::numeric_limits<float>::infinity();
};

// Mesh-local XY bounds measured from the shipped room furniture, not tile
// centers. Keep these synchronized with assets using check_room_object_bounds.py.
static const MeshBounds meshBounds[] = {
    {"AdventurerBed", -.406797f, -.679228f, .406797f, .679228f, .087917f},
    {"Anvil", -.335981f, -.280187f, .341827f, .231204f},
    {"Bed", -.337495f, -.681989f, .344794f, .702338f, .686024f},
    {"Bookcase", -.1694f, -.1694f, .1694f, .1694f},
    {"Bookshelf", -.52309f, -.0069419f, .530155f, .428917f},
    {"CasinoPokerTable", -.287885f, -.249315f, .287885f, .249315f},
    {"CasinoWallBeer", -.502785f, .325887f, .502785f, .493482f},
    {"CelticCross", -.391612f, -.28f, .391607f, .28f},
    {"ChickenCoop", -.203275f, -.4f, .796725f, .4f},
    {"ChickenCoopHouse", -.203275f, -.4f, .796725f, .4f},
    {"Chimney", -.63f, .0721364f, .63f, .583136f},
    {"DragonBed", -.941213f, -.96306f, .886655f, .969738f, .306282f},
    {"DungeonHeartObjectCritical", -1.73308f, -1.73308f, 1.73308f, 1.73308f},
    {"DungeonHeartObjectDamaged", -1.73308f, -1.73308f, 1.73308f, 1.73308f},
    {"DungeonHeartObjectHealthy", -1.73308f, -1.73308f, 1.73308f, 1.73308f},
    {"FenceCorner", -.502486f, -.500121f, .521221f, .514487f},
    {"FenceStraight", -.493929f, -.492016f, .516277f, -.462466f},
    {"GoblinBed", -.450071f, -.436337f, .444606f, .44576f, .073802f},
    {"GoldstackLv1", -.197478f, -.175391f, .186379f, .185685f},
    {"GoldstackLv2", -.185184f, -.182552f, .185553f, .182552f},
    {"GoldstackLv3", -.331379f, -.301391f, .290679f, .182552f},
    {"GoldstackLv4", -.331379f, -.301391f, .290679f, .282221f},
    {"Grindstone", -.329974f, -.215496f, .329974f, .371096f},
    {"KnightCoffin", -.254848f, -.627449f, .517051f, .632155f, .841464f},
    {"KnightStatue", -.293943f, -.32853f, .295722f, .325329f},
    {"KnightStatue2", -.323145f, -.358743f, .332038f, .367767f},
    {"LizardmanBed", -.32835f, -.77042f, .328337f, .769587f, .952407f},
    {"OrcBed", -.533745f, -.997136f, .529433f, .987434f, .560469f},
    {"Podium", -.193612f, -.148315f, .193891f, .148315f},
    {"PortalObject", -1.66302f, -1.66302f, 1.66302f, 1.66302f},
    {"RangerBed", -.53459f, -.777014f, .534418f, .775852f, .805918f},
    {"Roulette", -.292486f, -.296162f, .292326f, .296652f},
    {"Skull", -.205408f, -.216924f, .205408f, .460773f},
    {"SpiderBed", -.35f, -.435f, .35f, .435f, .59f},
    {"StoneCoffin", -.425477f, -.693722f, .425477f, .693722f, .767922f},
    {"TentacleBed", -.448981f, -.476366f, .461978f, .436628f, .276672f},
    {"TortureObject", -.7007f, -.606824f, .7007f, .606824f},
    {"TrainingDummy1", -.248242f, -.128432f, .248296f, .330221f},
    {"TrainingDummy2", -.455f, -.170625f, .455f, .4095f},
    {"TrainingDummy3", -.263341f, -.228943f, .30858f, .121115f},
    {"TrainingDummy4", -.462458f, -.248657f, .462458f, .248657f},
    {"TrollBed", -.787227f, -.794584f, .954702f, .813162f, 1.28522f},
    {"WorkerBed", -.3f, -.425f, .3f, .445f, .71f},
    {"WorkshopMachine1", -.5376f, -.506479f, .761215f, .337512f},
    {"WorkshopMachine2", -.730786f, -.336f, .5376f, .338177f}
};

// The dungeon heart has one mesh per health tier (see RoomDungeonTemple.cpp).
inline bool isDungeonHeartMesh(const std::string& name)
{
    return name == "DungeonHeartObjectHealthy" || name == "DungeonHeartObjectDamaged" ||
        name == "DungeonHeartObjectCritical";
}

// Narrow the visible furniture and its navigation bounds together. Leave Z
// unchanged so authored working heights and bed support surfaces stay valid.
// Large beds keep their existing multi-tile allocation; this is not a capacity
// or placement rule. Already compact meshes are never enlarged.
struct FurnitureScale
{
    float x, y;
};

inline FurnitureScale furnitureScale(const MeshBounds& bounds)
{
    const std::string name(bounds.name);
    if(name == "FenceCorner" || name == "FenceStraight" ||
       name == "PortalObject" || isDungeonHeartMesh(name))
        return {1.0f, 1.0f};
    // Treasury piles can fill adjacent tiles at arbitrary angles. Bound their
    // diagonal, not just their unrotated width, so rotation retains the margin.
    if(name.compare(0, 9, "Goldstack") == 0)
    {
        const float scale = std::min(1.0f, 0.4f / std::hypot(
            bounds.maxX - bounds.minX, bounds.maxY - bounds.minY));
        return {scale, scale};
    }
    float width = 0.6f, depth = 0.6f;
    const bool bed = name == "Bed" || name == "KnightCoffin" || name == "StoneCoffin" ||
        (name.size() >= 3 && name.compare(name.size() - 3, 3, "Bed") == 0);
    // This fallback also covers unassigned decorative instances. Actual beds
    // override it with the owning creature's allocated dimensions below.
    if(bed)
        width = depth = 0.4f;
    if(name == "DragonBed" || name == "TrollBed")
        width = depth = 1.2f;
    else if(name == "Bed" || name == "KnightCoffin" || name == "LizardmanBed" ||
            name == "OrcBed" || name == "RangerBed" || name == "StoneCoffin")
        depth = 1.2f;
    const float x = std::min(1.0f, width / (bounds.maxX - bounds.minX));
    const float y = std::min(1.0f, depth / (bounds.maxY - bounds.minY));
    if(bed)
        return {x, y};
    const float scale = std::min(x, y);
    return {scale, scale};
}

// A bed covers this fraction of its tile width and depth; the rest is the lane
// between two neighbouring beds. A creature wider than that lane cannot use it.
constexpr float bedTileFill = 0.70f;
constexpr float bedLaneWidth = 1.0f - bedTileFill;

struct BedPlacement
{
    float x, y, angle;
    FurnitureScale scale;
};

inline BedPlacement bedPlacement(const MeshBounds& bounds, int x, int y,
    int width, int height, float allocationAngle, const std::string& creatureName)
{
    // Stable across save/load and platforms, without consuming gameplay RNG.
    std::uint32_t hash = 2166136261u;
    for(unsigned char character : creatureName)
        hash = (hash ^ character) * 16777619u;
    const float angle = allocationAngle + float(hash % 8001u) * 0.001f - 4.0f;
    const float radians = angle * 0.01745329252f;
    const float cosine = std::cos(radians), sine = std::sin(radians);
    // Fit the rotated footprint, keeping the right and bottom 30% lanes clear.
    const float c = std::abs(cosine), s = std::abs(sine);
    const float determinant = c * c - s * s;
    const FurnitureScale scale{bedTileFill * (width * c - height * s) /
            (determinant * (bounds.maxX - bounds.minX)),
        bedTileFill * (height * c - width * s) /
            (determinant * (bounds.maxY - bounds.minY))};
    float left = 1.0e10f, top = -1.0e10f;
    for(float px : {bounds.minX * scale.x, bounds.maxX * scale.x})
        for(float py : {bounds.minY * scale.y, bounds.maxY * scale.y})
        {
            left = std::min(left, cosine * px - sine * py);
            top = std::max(top, sine * px + cosine * py);
        }
    return {float(x) - 0.5f - left, float(y + height) - 0.5f - top, angle, scale};
}

struct WalkingRadius
{
    const char* name;
    float radius;
    float minX, minY, maxX, maxY;
};

// Maximum XY distance of skinned vertices over the authored Walk cycle,
// rounded upward with a small interpolation margin; never use bind-pose arms.
static const WalkingRadius walkingRadii[] = {
    {"Adventurer.mesh", .42f, -.223013f, -.412246f, .219754f, .333578f},
    {"CaveHornet.mesh", .34f, -.336557f, -.204048f, .336531f, .223639f},
    {"Cultist.mesh", .45f, -.290157f, -.437019f, .290157f, .37038f},
    {"DarkElf.mesh", .30f, -.193203f, -.212566f, .139327f, .305f},
    {"Defender.mesh", 1.08f, -.257927f, -1.0724f, .338654f, .375236f},
    {"Dragon.mesh", .94f, -.742643f, -.907037f, .757226f, .858256f},
    {"Dwarf1.mesh", .33f, -.258449f, -.319074f, .25823f, .237622f},
    {"Dwarf2.mesh", .33f, -.253703f, -.312233f, .253375f, .223686f},
    {"Elf.mesh", .33f, -.193203f, -.228419f, .139327f, .322731f},
    {"Gnome.mesh", .30f, -.257412f, -.224375f, .257413f, .216508f},
    {"Goblin.mesh", .39f, -.143098f, -.359099f, .26421f, .255691f},
    {"Knight.mesh", .46f, -.271715f, -.428838f, .276299f, .395971f},
    {"Kobold.mesh", .30f, -.215426f, -.202178f, .146432f, .277816f},
    {"Kreatur.mesh", .95f, -.72982f, -.696044f, .73037f, .600837f},
    {"LavaSpawn.mesh", 1.13f, -.803072f, -.770489f, .801402f, 1.12894f},
    {"Lizardman.mesh", .72f, -.327972f, -.494859f, .319483f, .717053f},
    {"Monk.mesh", .39f, -.195454f, -.373016f, .193061f, .301613f},
    {"NatureMonster.mesh", .59f, -.48582f, -.437184f, .48582f, .508262f},
    {"Orc.mesh", .45f, -.301586f, -.442845f, .300999f, .430059f},
    {"PitDemon.mesh", 1.33f, -1.32384f, -.648509f, 1.32384f, .627703f},
    {"Rat.mesh", .59f, -.137487f, -.47173f, .130219f, .580713f},
    {"Roach.mesh", .56f, -.312113f, -.490705f, .314484f, .503523f},
    {"RunelordDwarf.mesh", .42f, -.2958f, -.403943f, .304318f, .219047f},
    {"Scarab.mesh", .63f, -.580074f, -.289168f, .583679f, .382623f},
    {"Slime.mesh", .57f, -.139284f, -.564724f, .139272f, .205f},
    {"Spider.mesh", .46f, -.395196f, -.425697f, .395635f, .414982f},
    {"TentacleAlbine.mesh", .32f, -.240472f, -.304768f, .239782f, .294454f},
    {"TentacleGreen.mesh", .32f, -.240472f, -.304768f, .239782f, .294454f},
    {"Troll.mesh", .64f, -.626231f, -.512311f, .635458f, .434564f},
    {"Wizard.mesh", .41f, -.238856f, -.314751f, .242062f, .378029f},
    {"Wyvern.mesh", .62f, -.56663f, -.318587f, .566629f, .619002f},
    {"lich.mesh", .83f, -.515405f, -.82278f, .42628f, .661376f},
    {"skeleton.mesh", .59f, -.248051f, -.586067f, .279937f, .440293f}
};

// Walking envelope of the skinned Walk poses clipped below the top of each bed:
// only the body under the bed top counts for passing it, arms and torso above
// do not. The clip lies at the bed top divided by the level-one scale (1.0, the
// unit size), so higher levels keep this conservative band, not a narrower guessed
// footprint.
// XY interpolation clearance matches the full walking catalog above. An empty
// band means no animated part reaches that low (flying creatures).
constexpr float lowWalkingMargin = .010001f;
struct BodyBand
{
    const char* name;
    float height;
    float minX, minY, maxX, maxY;
    bool empty;
    float minZ;
};
static const BodyBand bodyBands[] = {
    {"Adventurer.mesh", .073802f, -.112152f, -.402246f, .109564f, .323578f, false, -.02034f},
    {"Adventurer.mesh", .087917f, -.112152f, -.402246f, .109564f, .323578f, false, -.02034f},
    {"Adventurer.mesh", .276672f, -.148989f, -.402246f, .149287f, .323578f, false, -.02034f},
    {"Adventurer.mesh", .306282f, -.154314f, -.402246f, .149287f, .323578f, false, -.02034f},
    {"Adventurer.mesh", .560469f, -.213135f, -.402246f, .209982f, .323578f, false, -.02034f},
    {"Adventurer.mesh", .59f, -.213135f, -.402246f, .209982f, .323578f, false, -.02034f},
    {"Adventurer.mesh", .686024f, -.213135f, -.402246f, .209982f, .323578f, false, -.02034f},
    {"Adventurer.mesh", .71f, -.213135f, -.402246f, .209982f, .323578f, false, -.02034f},
    {"Adventurer.mesh", .767922f, -.213135f, -.402246f, .209982f, .323578f, false, -.02034f},
    {"Adventurer.mesh", .805918f, -.213135f, -.402246f, .209982f, .323578f, false, -.02034f},
    {"Adventurer.mesh", .841464f, -.213135f, -.402246f, .209982f, .323578f, false, -.02034f},
    {"Adventurer.mesh", .952407f, -.213135f, -.402246f, .209982f, .323578f, false, -.02034f},
    {"Adventurer.mesh", 1.28522f, -.213135f, -.402246f, .209982f, .323578f, false, -.02034f},
    {"CaveHornet.mesh", .073802f, 0.0f, 0.0f, 0.0f, 0.0f, true, 0.0f},
    {"CaveHornet.mesh", .087917f, 0.0f, 0.0f, 0.0f, 0.0f, true, 0.0f},
    {"CaveHornet.mesh", .276672f, -.326605f, -.194049f, .326581f, .213642f, false, .128645f},
    {"CaveHornet.mesh", .306282f, -.326605f, -.194049f, .326581f, .213642f, false, .128645f},
    {"CaveHornet.mesh", .560469f, -.326605f, -.194049f, .326581f, .213642f, false, .128645f},
    {"CaveHornet.mesh", .59f, -.326605f, -.194049f, .326581f, .213642f, false, .128645f},
    {"CaveHornet.mesh", .686024f, -.326605f, -.194049f, .326581f, .213642f, false, .128645f},
    {"CaveHornet.mesh", .71f, -.326605f, -.194049f, .326581f, .213642f, false, .128645f},
    {"CaveHornet.mesh", .767922f, -.326605f, -.194049f, .326581f, .213642f, false, .128645f},
    {"CaveHornet.mesh", .805918f, -.326605f, -.194049f, .326581f, .213642f, false, .128645f},
    {"CaveHornet.mesh", .841464f, -.326605f, -.194049f, .326581f, .213642f, false, .128645f},
    {"CaveHornet.mesh", .952407f, -.326605f, -.194049f, .326581f, .213642f, false, .128645f},
    {"CaveHornet.mesh", 1.28522f, -.326605f, -.194049f, .326581f, .213642f, false, .128645f},
    {"Cultist.mesh", .073802f, -.114426f, -.427019f, .114321f, .353293f, false, -.080379f},
    {"Cultist.mesh", .087917f, -.114426f, -.427019f, .114321f, .353293f, false, -.080379f},
    {"Cultist.mesh", .276672f, -.156874f, -.427019f, .179543f, .36038f, false, -.080379f},
    {"Cultist.mesh", .306282f, -.172309f, -.427019f, .192231f, .36038f, false, -.080379f},
    {"Cultist.mesh", .560469f, -.230145f, -.427019f, .231711f, .36038f, false, -.080379f},
    {"Cultist.mesh", .59f, -.231368f, -.427019f, .231711f, .36038f, false, -.080379f},
    {"Cultist.mesh", .686024f, -.231368f, -.427019f, .231711f, .36038f, false, -.080379f},
    {"Cultist.mesh", .71f, -.231368f, -.427019f, .231711f, .36038f, false, -.080379f},
    {"Cultist.mesh", .767922f, -.241245f, -.427019f, .241246f, .36038f, false, -.080379f},
    {"Cultist.mesh", .805918f, -.257167f, -.427019f, .257168f, .36038f, false, -.080379f},
    {"Cultist.mesh", .841464f, -.270747f, -.427019f, .270748f, .36038f, false, -.080379f},
    {"Cultist.mesh", .952407f, -.280157f, -.427019f, .280157f, .36038f, false, -.080379f},
    {"Cultist.mesh", 1.28522f, -.280157f, -.427019f, .280157f, .36038f, false, -.080379f},
    {"DarkElf.mesh", .073802f, -.07234f, -.202566f, .117295f, .291945f, false, -.07872f},
    {"DarkElf.mesh", .087917f, -.07234f, -.202566f, .117295f, .291945f, false, -.07872f},
    {"DarkElf.mesh", .276672f, -.124278f, -.202566f, .130499f, .291945f, false, -.07872f},
    {"DarkElf.mesh", .306282f, -.124278f, -.202566f, .130499f, .291945f, false, -.07872f},
    {"DarkElf.mesh", .560469f, -.165293f, -.202566f, .130499f, .291945f, false, -.07872f},
    {"DarkElf.mesh", .59f, -.173888f, -.202566f, .130499f, .291945f, false, -.07872f},
    {"DarkElf.mesh", .686024f, -.185211f, -.202566f, .130499f, .291945f, false, -.07872f},
    {"DarkElf.mesh", .71f, -.185211f, -.202566f, .130499f, .291945f, false, -.07872f},
    {"DarkElf.mesh", .767922f, -.185211f, -.202566f, .130499f, .291945f, false, -.07872f},
    {"DarkElf.mesh", .805918f, -.185211f, -.202566f, .130499f, .291945f, false, -.07872f},
    {"DarkElf.mesh", .841464f, -.185211f, -.202566f, .130499f, .291945f, false, -.07872f},
    {"DarkElf.mesh", .952407f, -.185211f, -.202566f, .130499f, .291945f, false, -.07872f},
    {"DarkElf.mesh", 1.28522f, -.185211f, -.202566f, .130499f, .291945f, false, -.07872f},
    {"Defender.mesh", .073802f, -.247502f, -.894867f, .119445f, .316512f, false, -.075047f},
    {"Defender.mesh", .087917f, -.251304f, -.900917f, .119445f, .318989f, false, -.075047f},
    {"Defender.mesh", .276672f, -.251304f, -.977463f, .132666f, .321638f, false, -.075047f},
    {"Defender.mesh", .306282f, -.251304f, -.988676f, .170341f, .321638f, false, -.075047f},
    {"Defender.mesh", .560469f, -.251304f, -1.04911f, .173962f, .365242f, false, -.075047f},
    {"Defender.mesh", .59f, -.251304f, -1.05731f, .174574f, .365242f, false, -.075047f},
    {"Defender.mesh", .686024f, -.251304f, -1.0624f, .174574f, .365242f, false, -.075047f},
    {"Defender.mesh", .71f, -.251304f, -1.0624f, .174574f, .365242f, false, -.075047f},
    {"Defender.mesh", .767922f, -.251304f, -1.0624f, .174574f, .365242f, false, -.075047f},
    {"Defender.mesh", .805918f, -.251304f, -1.0624f, .174574f, .365242f, false, -.075047f},
    {"Defender.mesh", .841464f, -.251304f, -1.0624f, .174574f, .365242f, false, -.075047f},
    {"Defender.mesh", .952407f, -.251304f, -1.0624f, .220031f, .365242f, false, -.075047f},
    {"Defender.mesh", 1.28522f, -.251304f, -1.0624f, .328654f, .365242f, false, -.075047f},
    {"Dragon.mesh", .073802f, -.289369f, -.427237f, .244315f, .430807f, false, -.039586f},
    {"Dragon.mesh", .087917f, -.297353f, -.427237f, .254623f, .430807f, false, -.039586f},
    {"Dragon.mesh", .276672f, -.342277f, -.427237f, .338384f, .717009f, false, -.039586f},
    {"Dragon.mesh", .306282f, -.342277f, -.427237f, .338384f, .766875f, false, -.039586f},
    {"Dragon.mesh", .560469f, -.73264f, -.897033f, .750112f, .848264f, false, -.039586f},
    {"Dragon.mesh", .59f, -.73264f, -.897033f, .750112f, .848264f, false, -.039586f},
    {"Dragon.mesh", .686024f, -.73264f, -.897033f, .750112f, .848264f, false, -.039586f},
    {"Dragon.mesh", .71f, -.73264f, -.897033f, .750112f, .848264f, false, -.039586f},
    {"Dragon.mesh", .767922f, -.73264f, -.897033f, .750112f, .848264f, false, -.039586f},
    {"Dragon.mesh", .805918f, -.73264f, -.897033f, .750112f, .848264f, false, -.039586f},
    {"Dragon.mesh", .841464f, -.73264f, -.897033f, .750112f, .848264f, false, -.039586f},
    {"Dragon.mesh", .952407f, -.73264f, -.897033f, .750112f, .848264f, false, -.039586f},
    {"Dragon.mesh", 1.28522f, -.73264f, -.897033f, .750112f, .848264f, false, -.039586f},
    {"Dwarf1.mesh", .073802f, -.121574f, -.309074f, .120664f, .227622f, false, -.057376f},
    {"Dwarf1.mesh", .087917f, -.121574f, -.309074f, .120664f, .227622f, false, -.057376f},
    {"Dwarf1.mesh", .276672f, -.247137f, -.309074f, .246456f, .227622f, false, -.057376f},
    {"Dwarf1.mesh", .306282f, -.248594f, -.309074f, .24818f, .227622f, false, -.057376f},
    {"Dwarf1.mesh", .560469f, -.248594f, -.309074f, .24818f, .227622f, false, -.057376f},
    {"Dwarf1.mesh", .59f, -.248594f, -.309074f, .24818f, .227622f, false, -.057376f},
    {"Dwarf1.mesh", .686024f, -.248594f, -.309074f, .24818f, .227622f, false, -.057376f},
    {"Dwarf1.mesh", .71f, -.248594f, -.309074f, .24818f, .227622f, false, -.057376f},
    {"Dwarf1.mesh", .767922f, -.248594f, -.309074f, .24818f, .227622f, false, -.057376f},
    {"Dwarf1.mesh", .805918f, -.248594f, -.309074f, .24818f, .227622f, false, -.057376f},
    {"Dwarf1.mesh", .841464f, -.248594f, -.309074f, .24818f, .227622f, false, -.057376f},
    {"Dwarf1.mesh", .952407f, -.248594f, -.309074f, .24818f, .227622f, false, -.057376f},
    {"Dwarf1.mesh", 1.28522f, -.248594f, -.309074f, .24818f, .227622f, false, -.057376f},
    {"Dwarf2.mesh", .073802f, -.121506f, -.302233f, .120806f, .213686f, false, -.034414f},
    {"Dwarf2.mesh", .087917f, -.121506f, -.302233f, .120806f, .213686f, false, -.034414f},
    {"Dwarf2.mesh", .276672f, -.238958f, -.302233f, .240135f, .213686f, false, -.034414f},
    {"Dwarf2.mesh", .306282f, -.242748f, -.302233f, .242276f, .213686f, false, -.034414f},
    {"Dwarf2.mesh", .560469f, -.243821f, -.302233f, .243376f, .213686f, false, -.034414f},
    {"Dwarf2.mesh", .59f, -.243821f, -.302233f, .243376f, .213686f, false, -.034414f},
    {"Dwarf2.mesh", .686024f, -.243821f, -.302233f, .243376f, .213686f, false, -.034414f},
    {"Dwarf2.mesh", .71f, -.243821f, -.302233f, .243376f, .213686f, false, -.034414f},
    {"Dwarf2.mesh", .767922f, -.243821f, -.302233f, .243376f, .213686f, false, -.034414f},
    {"Dwarf2.mesh", .805918f, -.243821f, -.302233f, .243376f, .213686f, false, -.034414f},
    {"Dwarf2.mesh", .841464f, -.243821f, -.302233f, .243376f, .213686f, false, -.034414f},
    {"Dwarf2.mesh", .952407f, -.243821f, -.302233f, .243376f, .213686f, false, -.034414f},
    {"Dwarf2.mesh", 1.28522f, -.243821f, -.302233f, .243376f, .213686f, false, -.034414f},
    {"Elf.mesh", .073802f, -.070562f, -.21842f, .115823f, .312731f, false, -.07402f},
    {"Elf.mesh", .087917f, -.070562f, -.21842f, .116097f, .312731f, false, -.07402f},
    {"Elf.mesh", .276672f, -.131449f, -.21842f, .131301f, .312731f, false, -.07402f},
    {"Elf.mesh", .306282f, -.131449f, -.21842f, .131301f, .312731f, false, -.07402f},
    {"Elf.mesh", .560469f, -.165293f, -.21842f, .131301f, .312731f, false, -.07402f},
    {"Elf.mesh", .59f, -.173888f, -.21842f, .131301f, .312731f, false, -.07402f},
    {"Elf.mesh", .686024f, -.185216f, -.21842f, .131301f, .312731f, false, -.07402f},
    {"Elf.mesh", .71f, -.185216f, -.21842f, .131301f, .312731f, false, -.07402f},
    {"Elf.mesh", .767922f, -.185216f, -.21842f, .131301f, .312731f, false, -.07402f},
    {"Elf.mesh", .805918f, -.185216f, -.21842f, .131301f, .312731f, false, -.07402f},
    {"Elf.mesh", .841464f, -.185216f, -.21842f, .131301f, .312731f, false, -.07402f},
    {"Elf.mesh", .952407f, -.185216f, -.21842f, .131301f, .312731f, false, -.07402f},
    {"Elf.mesh", 1.28522f, -.185216f, -.21842f, .131301f, .312731f, false, -.07402f},
    {"Gnome.mesh", .073802f, -.069328f, -.214375f, .069212f, .206508f, false, -.042925f},
    {"Gnome.mesh", .087917f, -.072946f, -.214375f, .072842f, .206508f, false, -.042925f},
    {"Gnome.mesh", .276672f, -.247508f, -.214375f, .247507f, .206508f, false, -.042925f},
    {"Gnome.mesh", .306282f, -.247508f, -.214375f, .247507f, .206508f, false, -.042925f},
    {"Gnome.mesh", .560469f, -.247508f, -.214375f, .247507f, .206508f, false, -.042925f},
    {"Gnome.mesh", .59f, -.247508f, -.214375f, .247507f, .206508f, false, -.042925f},
    {"Gnome.mesh", .686024f, -.247508f, -.214375f, .247507f, .206508f, false, -.042925f},
    {"Gnome.mesh", .71f, -.247508f, -.214375f, .247507f, .206508f, false, -.042925f},
    {"Gnome.mesh", .767922f, -.247508f, -.214375f, .247507f, .206508f, false, -.042925f},
    {"Gnome.mesh", .805918f, -.247508f, -.214375f, .247507f, .206508f, false, -.042925f},
    {"Gnome.mesh", .841464f, -.247508f, -.214375f, .247507f, .206508f, false, -.042925f},
    {"Gnome.mesh", .952407f, -.247508f, -.214375f, .247507f, .206508f, false, -.042925f},
    {"Gnome.mesh", 1.28522f, -.247508f, -.214375f, .247507f, .206508f, false, -.042925f},
    {"Goblin.mesh", .073802f, -.088977f, -.216901f, .111977f, .252987f, false, -.065341f},
    {"Goblin.mesh", .087917f, -.088977f, -.216901f, .251567f, .252987f, false, -.065341f},
    {"Goblin.mesh", .276672f, -.123498f, -.319379f, .254931f, .252987f, false, -.065341f},
    {"Goblin.mesh", .306282f, -.123498f, -.336714f, .254931f, .252987f, false, -.065341f},
    {"Goblin.mesh", .560469f, -.133241f, -.349964f, .254931f, .252987f, false, -.065341f},
    {"Goblin.mesh", .59f, -.133241f, -.349964f, .254931f, .252987f, false, -.065341f},
    {"Goblin.mesh", .686024f, -.133241f, -.349964f, .254931f, .252987f, false, -.065341f},
    {"Goblin.mesh", .71f, -.133241f, -.349964f, .254931f, .252987f, false, -.065341f},
    {"Goblin.mesh", .767922f, -.133241f, -.349964f, .254931f, .252987f, false, -.065341f},
    {"Goblin.mesh", .805918f, -.133241f, -.349964f, .254931f, .252987f, false, -.065341f},
    {"Goblin.mesh", .841464f, -.133241f, -.349964f, .254931f, .252987f, false, -.065341f},
    {"Goblin.mesh", .952407f, -.133241f, -.349964f, .254931f, .252987f, false, -.065341f},
    {"Goblin.mesh", 1.28522f, -.133241f, -.349964f, .254931f, .252987f, false, -.065341f},
    {"Knight.mesh", .073802f, -.218932f, -.418838f, .262491f, .347769f, false, -.075899f},
    {"Knight.mesh", .087917f, -.218932f, -.418838f, .262491f, .354469f, false, -.075899f},
    {"Knight.mesh", .276672f, -.218932f, -.418838f, .262491f, .385971f, false, -.075899f},
    {"Knight.mesh", .306282f, -.242071f, -.418838f, .262491f, .385971f, false, -.075899f},
    {"Knight.mesh", .560469f, -.261789f, -.418838f, .266867f, .385971f, false, -.075899f},
    {"Knight.mesh", .59f, -.261789f, -.418838f, .266867f, .385971f, false, -.075899f},
    {"Knight.mesh", .686024f, -.261789f, -.418838f, .266867f, .385971f, false, -.075899f},
    {"Knight.mesh", .71f, -.261789f, -.418838f, .266867f, .385971f, false, -.075899f},
    {"Knight.mesh", .767922f, -.261789f, -.418838f, .266867f, .385971f, false, -.075899f},
    {"Knight.mesh", .805918f, -.261789f, -.418838f, .266867f, .385971f, false, -.075899f},
    {"Knight.mesh", .841464f, -.261789f, -.418838f, .266867f, .385971f, false, -.075899f},
    {"Knight.mesh", .952407f, -.261789f, -.418838f, .266867f, .385971f, false, -.075899f},
    {"Knight.mesh", 1.28522f, -.261789f, -.418838f, .266867f, .385971f, false, -.075899f},
    {"Kobold.mesh", .073802f, -.190149f, -.155409f, .07425f, .162343f, false, -.026297f},
    {"Kobold.mesh", .087917f, -.20443f, -.166428f, .083221f, .163839f, false, -.026297f},
    {"Kobold.mesh", .276672f, -.205426f, -.192767f, .136456f, .267816f, false, -.026297f},
    {"Kobold.mesh", .306282f, -.205426f, -.192767f, .136456f, .267816f, false, -.026297f},
    {"Kobold.mesh", .560469f, -.205426f, -.192767f, .136456f, .267816f, false, -.026297f},
    {"Kobold.mesh", .59f, -.205426f, -.192767f, .136456f, .267816f, false, -.026297f},
    {"Kobold.mesh", .686024f, -.205426f, -.192767f, .136456f, .267816f, false, -.026297f},
    {"Kobold.mesh", .71f, -.205426f, -.192767f, .136456f, .267816f, false, -.026297f},
    {"Kobold.mesh", .767922f, -.205426f, -.192767f, .136456f, .267816f, false, -.026297f},
    {"Kobold.mesh", .805918f, -.205426f, -.192767f, .136456f, .267816f, false, -.026297f},
    {"Kobold.mesh", .841464f, -.205426f, -.192767f, .136456f, .267816f, false, -.026297f},
    {"Kobold.mesh", .952407f, -.205426f, -.192767f, .136456f, .267816f, false, -.026297f},
    {"Kobold.mesh", 1.28522f, -.205426f, -.192767f, .136456f, .267816f, false, -.026297f},
    {"Kreatur.mesh", .073802f, -.468494f, -.686044f, .468433f, .590146f, false, -.027044f},
    {"Kreatur.mesh", .087917f, -.468494f, -.686044f, .468433f, .590146f, false, -.027044f},
    {"Kreatur.mesh", .276672f, -.716941f, -.686044f, .716958f, .590146f, false, -.027044f},
    {"Kreatur.mesh", .306282f, -.720492f, -.686044f, .72051f, .590146f, false, -.027044f},
    {"Kreatur.mesh", .560469f, -.720492f, -.686044f, .72051f, .59084f, false, -.027044f},
    {"Kreatur.mesh", .59f, -.720492f, -.686044f, .72051f, .59084f, false, -.027044f},
    {"Kreatur.mesh", .686024f, -.720492f, -.686044f, .72051f, .59084f, false, -.027044f},
    {"Kreatur.mesh", .71f, -.720492f, -.686044f, .72051f, .59084f, false, -.027044f},
    {"Kreatur.mesh", .767922f, -.720492f, -.686044f, .72051f, .59084f, false, -.027044f},
    {"Kreatur.mesh", .805918f, -.720492f, -.686044f, .72051f, .59084f, false, -.027044f},
    {"Kreatur.mesh", .841464f, -.720492f, -.686044f, .72051f, .59084f, false, -.027044f},
    {"Kreatur.mesh", .952407f, -.720492f, -.686044f, .72051f, .59084f, false, -.027044f},
    {"Kreatur.mesh", 1.28522f, -.720492f, -.686044f, .72051f, .59084f, false, -.027044f},
    {"LavaSpawn.mesh", .073802f, -.794634f, -.627324f, .789449f, 1.11894f, false, -.052282f},
    {"LavaSpawn.mesh", .087917f, -.794634f, -.635597f, .789449f, 1.11894f, false, -.052282f},
    {"LavaSpawn.mesh", .276672f, -.794634f, -.702337f, .789449f, 1.11894f, false, -.052282f},
    {"LavaSpawn.mesh", .306282f, -.794634f, -.702396f, .789449f, 1.11894f, false, -.052282f},
    {"LavaSpawn.mesh", .560469f, -.794634f, -.762326f, .791635f, 1.11894f, false, -.052282f},
    {"LavaSpawn.mesh", .59f, -.794634f, -.763218f, .791635f, 1.11894f, false, -.052282f},
    {"LavaSpawn.mesh", .686024f, -.794634f, -.763218f, .791635f, 1.11894f, false, -.052282f},
    {"LavaSpawn.mesh", .71f, -.794634f, -.763218f, .791635f, 1.11894f, false, -.052282f},
    {"LavaSpawn.mesh", .767922f, -.794634f, -.763218f, .791635f, 1.11894f, false, -.052282f},
    {"LavaSpawn.mesh", .805918f, -.794634f, -.763218f, .791635f, 1.11894f, false, -.052282f},
    {"LavaSpawn.mesh", .841464f, -.794634f, -.763218f, .791635f, 1.11894f, false, -.052282f},
    {"LavaSpawn.mesh", .952407f, -.794634f, -.763218f, .791635f, 1.11894f, false, -.052282f},
    {"LavaSpawn.mesh", 1.28522f, -.794634f, -.763218f, .791635f, 1.11894f, false, -.052282f},
    {"Lizardman.mesh", .073802f, -.107998f, -.484859f, .108054f, .376819f, false, -.006661f},
    {"Lizardman.mesh", .087917f, -.107998f, -.484859f, .108054f, .384712f, false, -.006661f},
    {"Lizardman.mesh", .276672f, -.112642f, -.484859f, .112587f, .707037f, false, -.006661f},
    {"Lizardman.mesh", .306282f, -.244923f, -.484859f, .230799f, .707054f, false, -.006661f},
    {"Lizardman.mesh", .560469f, -.318192f, -.484859f, .309732f, .70706f, false, -.006661f},
    {"Lizardman.mesh", .59f, -.318192f, -.484859f, .309732f, .70706f, false, -.006661f},
    {"Lizardman.mesh", .686024f, -.318192f, -.484859f, .309732f, .70706f, false, -.006661f},
    {"Lizardman.mesh", .71f, -.318192f, -.484859f, .309732f, .70706f, false, -.006661f},
    {"Lizardman.mesh", .767922f, -.318192f, -.484859f, .309732f, .70706f, false, -.006661f},
    {"Lizardman.mesh", .805918f, -.318192f, -.484859f, .309732f, .70706f, false, -.006661f},
    {"Lizardman.mesh", .841464f, -.318192f, -.484859f, .309732f, .70706f, false, -.006661f},
    {"Lizardman.mesh", .952407f, -.318192f, -.484859f, .309732f, .70706f, false, -.006661f},
    {"Lizardman.mesh", 1.28522f, -.318192f, -.484859f, .309732f, .70706f, false, -.006661f},
    {"Monk.mesh", .073802f, -.147469f, -.363016f, .149341f, .244708f, false, -.031453f},
    {"Monk.mesh", .087917f, -.147469f, -.363016f, .149341f, .244708f, false, -.031453f},
    {"Monk.mesh", .276672f, -.147469f, -.363016f, .149341f, .291613f, false, -.031453f},
    {"Monk.mesh", .306282f, -.147469f, -.363016f, .149341f, .291613f, false, -.031453f},
    {"Monk.mesh", .560469f, -.185454f, -.363016f, .183061f, .291613f, false, -.031453f},
    {"Monk.mesh", .59f, -.185454f, -.363016f, .183061f, .291613f, false, -.031453f},
    {"Monk.mesh", .686024f, -.185454f, -.363016f, .183061f, .291613f, false, -.031453f},
    {"Monk.mesh", .71f, -.185454f, -.363016f, .183061f, .291613f, false, -.031453f},
    {"Monk.mesh", .767922f, -.185454f, -.363016f, .183061f, .291613f, false, -.031453f},
    {"Monk.mesh", .805918f, -.185454f, -.363016f, .183061f, .291613f, false, -.031453f},
    {"Monk.mesh", .841464f, -.185454f, -.363016f, .183061f, .291613f, false, -.031453f},
    {"Monk.mesh", .952407f, -.185454f, -.363016f, .183061f, .291613f, false, -.031453f},
    {"Monk.mesh", 1.28522f, -.185454f, -.363016f, .183061f, .291613f, false, -.031453f},
    {"NatureMonster.mesh", .073802f, -.42317f, -.403812f, .423169f, .383834f, false, -.054203f},
    {"NatureMonster.mesh", .087917f, -.424708f, -.415694f, .424707f, .389713f, false, -.054203f},
    {"NatureMonster.mesh", .276672f, -.460587f, -.418676f, .460587f, .498262f, false, -.054203f},
    {"NatureMonster.mesh", .306282f, -.473078f, -.418676f, .473078f, .498262f, false, -.054203f},
    {"NatureMonster.mesh", .560469f, -.475821f, -.427183f, .475819f, .498262f, false, -.054203f},
    {"NatureMonster.mesh", .59f, -.475821f, -.427183f, .475819f, .498262f, false, -.054203f},
    {"NatureMonster.mesh", .686024f, -.475821f, -.427183f, .475819f, .498262f, false, -.054203f},
    {"NatureMonster.mesh", .71f, -.475821f, -.427183f, .475819f, .498262f, false, -.054203f},
    {"NatureMonster.mesh", .767922f, -.475821f, -.427183f, .475819f, .498262f, false, -.054203f},
    {"NatureMonster.mesh", .805918f, -.475821f, -.427183f, .475819f, .498262f, false, -.054203f},
    {"NatureMonster.mesh", .841464f, -.475821f, -.427183f, .475819f, .498262f, false, -.054203f},
    {"NatureMonster.mesh", .952407f, -.475821f, -.427183f, .475819f, .498262f, false, -.054203f},
    {"NatureMonster.mesh", 1.28522f, -.475821f, -.427183f, .475819f, .498262f, false, -.054203f},
    {"Orc.mesh", .073802f, -.131532f, -.432845f, .133099f, .37149f, false, -.017526f},
    {"Orc.mesh", .087917f, -.131532f, -.432845f, .133099f, .383382f, false, -.017526f},
    {"Orc.mesh", .276672f, -.2776f, -.432845f, .27653f, .420059f, false, -.017526f},
    {"Orc.mesh", .306282f, -.286329f, -.432845f, .285498f, .420059f, false, -.017526f},
    {"Orc.mesh", .560469f, -.291687f, -.432845f, .29112f, .420059f, false, -.017526f},
    {"Orc.mesh", .59f, -.291687f, -.432845f, .29112f, .420059f, false, -.017526f},
    {"Orc.mesh", .686024f, -.291687f, -.432845f, .29112f, .420059f, false, -.017526f},
    {"Orc.mesh", .71f, -.291687f, -.432845f, .29112f, .420059f, false, -.017526f},
    {"Orc.mesh", .767922f, -.291687f, -.432845f, .29112f, .420059f, false, -.017526f},
    {"Orc.mesh", .805918f, -.291687f, -.432845f, .29112f, .420059f, false, -.017526f},
    {"Orc.mesh", .841464f, -.291687f, -.432845f, .29112f, .420059f, false, -.017526f},
    {"Orc.mesh", .952407f, -.291687f, -.432845f, .29112f, .420059f, false, -.017526f},
    {"Orc.mesh", 1.28522f, -.291687f, -.432845f, .29112f, .420059f, false, -.017526f},
    {"PitDemon.mesh", .073802f, -.182359f, -.638509f, .203589f, .549867f, false, -.06426f},
    {"PitDemon.mesh", .087917f, -.182359f, -.638509f, .203589f, .549867f, false, -.06426f},
    {"PitDemon.mesh", .276672f, -.182359f, -.638509f, .203589f, .612342f, false, -.06426f},
    {"PitDemon.mesh", .306282f, -.182359f, -.638509f, .203589f, .613724f, false, -.06426f},
    {"PitDemon.mesh", .560469f, -1.30046f, -.638509f, 1.30046f, .617701f, false, -.06426f},
    {"PitDemon.mesh", .59f, -1.31102f, -.638509f, 1.31101f, .617701f, false, -.06426f},
    {"PitDemon.mesh", .686024f, -1.315f, -.638509f, 1.315f, .617701f, false, -.06426f},
    {"PitDemon.mesh", .71f, -1.315f, -.638509f, 1.315f, .617701f, false, -.06426f},
    {"PitDemon.mesh", .767922f, -1.315f, -.638509f, 1.315f, .617701f, false, -.06426f},
    {"PitDemon.mesh", .805918f, -1.315f, -.638509f, 1.315f, .617701f, false, -.06426f},
    {"PitDemon.mesh", .841464f, -1.315f, -.638509f, 1.315f, .617701f, false, -.06426f},
    {"PitDemon.mesh", .952407f, -1.315f, -.638509f, 1.315f, .617701f, false, -.06426f},
    {"PitDemon.mesh", 1.28522f, -1.315f, -.638509f, 1.315f, .617701f, false, -.06426f},
    {"Rat.mesh", .073802f, -.125224f, -.434253f, .11939f, .570713f, false, -.040884f},
    {"Rat.mesh", .087917f, -.126082f, -.442194f, .11939f, .570713f, false, -.040884f},
    {"Rat.mesh", .276672f, -.131283f, -.46173f, .122514f, .570713f, false, -.040884f},
    {"Rat.mesh", .306282f, -.131283f, -.46173f, .122514f, .570713f, false, -.040884f},
    {"Rat.mesh", .560469f, -.131283f, -.46173f, .122514f, .570713f, false, -.040884f},
    {"Rat.mesh", .59f, -.131283f, -.46173f, .122514f, .570713f, false, -.040884f},
    {"Rat.mesh", .686024f, -.131283f, -.46173f, .122514f, .570713f, false, -.040884f},
    {"Rat.mesh", .71f, -.131283f, -.46173f, .122514f, .570713f, false, -.040884f},
    {"Rat.mesh", .767922f, -.131283f, -.46173f, .122514f, .570713f, false, -.040884f},
    {"Rat.mesh", .805918f, -.131283f, -.46173f, .122514f, .570713f, false, -.040884f},
    {"Rat.mesh", .841464f, -.131283f, -.46173f, .122514f, .570713f, false, -.040884f},
    {"Rat.mesh", .952407f, -.131283f, -.46173f, .122514f, .570713f, false, -.040884f},
    {"Rat.mesh", 1.28522f, -.131283f, -.46173f, .122514f, .570713f, false, -.040884f},
    {"Roach.mesh", .073802f, -.27884f, -.480705f, .280289f, .493523f, false, -.006572f},
    {"Roach.mesh", .087917f, -.280158f, -.480705f, .280289f, .493523f, false, -.006572f},
    {"Roach.mesh", .276672f, -.302113f, -.480705f, .304484f, .493523f, false, -.006572f},
    {"Roach.mesh", .306282f, -.302113f, -.480705f, .304484f, .493523f, false, -.006572f},
    {"Roach.mesh", .560469f, -.302113f, -.480705f, .304484f, .493523f, false, -.006572f},
    {"Roach.mesh", .59f, -.302113f, -.480705f, .304484f, .493523f, false, -.006572f},
    {"Roach.mesh", .686024f, -.302113f, -.480705f, .304484f, .493523f, false, -.006572f},
    {"Roach.mesh", .71f, -.302113f, -.480705f, .304484f, .493523f, false, -.006572f},
    {"Roach.mesh", .767922f, -.302113f, -.480705f, .304484f, .493523f, false, -.006572f},
    {"Roach.mesh", .805918f, -.302113f, -.480705f, .304484f, .493523f, false, -.006572f},
    {"Roach.mesh", .841464f, -.302113f, -.480705f, .304484f, .493523f, false, -.006572f},
    {"Roach.mesh", .952407f, -.302113f, -.480705f, .304484f, .493523f, false, -.006572f},
    {"Roach.mesh", 1.28522f, -.302113f, -.480705f, .304484f, .493523f, false, -.006572f},
    {"RunelordDwarf.mesh", .073802f, -.143535f, -.393727f, .143549f, .188577f, false, -.036456f},
    {"RunelordDwarf.mesh", .087917f, -.143535f, -.393727f, .143549f, .188577f, false, -.036456f},
    {"RunelordDwarf.mesh", .276672f, -.165403f, -.393727f, .16513f, .188577f, false, -.036456f},
    {"RunelordDwarf.mesh", .306282f, -.185789f, -.393727f, .202709f, .188577f, false, -.036456f},
    {"RunelordDwarf.mesh", .560469f, -.285583f, -.393727f, .294319f, .188577f, false, -.036456f},
    {"RunelordDwarf.mesh", .59f, -.285583f, -.393727f, .294319f, .188577f, false, -.036456f},
    {"RunelordDwarf.mesh", .686024f, -.285583f, -.393727f, .294319f, .188577f, false, -.036456f},
    {"RunelordDwarf.mesh", .71f, -.285583f, -.393727f, .294319f, .188577f, false, -.036456f},
    {"RunelordDwarf.mesh", .767922f, -.285583f, -.393727f, .294319f, .188577f, false, -.036456f},
    {"RunelordDwarf.mesh", .805918f, -.285583f, -.393727f, .294319f, .188577f, false, -.036456f},
    {"RunelordDwarf.mesh", .841464f, -.285583f, -.393727f, .294319f, .188577f, false, -.036456f},
    {"RunelordDwarf.mesh", .952407f, -.285583f, -.393727f, .294319f, .188577f, false, -.036456f},
    {"RunelordDwarf.mesh", 1.28522f, -.285583f, -.393727f, .294319f, .188577f, false, -.036456f},
    {"Scarab.mesh", .073802f, -.491525f, -.191101f, .497842f, .357729f, false, -.071964f},
    {"Scarab.mesh", .087917f, -.503859f, -.191101f, .506109f, .357729f, false, -.071964f},
    {"Scarab.mesh", .276672f, -.544791f, -.191101f, .54808f, .357729f, false, -.071964f},
    {"Scarab.mesh", .306282f, -.548877f, -.191101f, .552943f, .357729f, false, -.071964f},
    {"Scarab.mesh", .560469f, -.570193f, -.191101f, .573705f, .357729f, false, -.071964f},
    {"Scarab.mesh", .59f, -.570193f, -.191101f, .573705f, .357729f, false, -.071964f},
    {"Scarab.mesh", .686024f, -.570193f, -.191101f, .573705f, .357729f, false, -.071964f},
    {"Scarab.mesh", .71f, -.570193f, -.191101f, .573705f, .357729f, false, -.071964f},
    {"Scarab.mesh", .767922f, -.570193f, -.191101f, .573705f, .368681f, false, -.071964f},
    {"Scarab.mesh", .805918f, -.570193f, -.191101f, .573705f, .372516f, false, -.071964f},
    {"Scarab.mesh", .841464f, -.570193f, -.198815f, .573705f, .372516f, false, -.071964f},
    {"Scarab.mesh", .952407f, -.570193f, -.249815f, .573705f, .372516f, false, -.071964f},
    {"Scarab.mesh", 1.28522f, -.570193f, -.279468f, .573705f, .372516f, false, -.071964f},
    {"Slime.mesh", .073802f, -.128698f, -.402058f, .128706f, .195001f, false, -.016886f},
    {"Slime.mesh", .087917f, -.129409f, -.410907f, .129396f, .195001f, false, -.016886f},
    {"Slime.mesh", .276672f, -.129409f, -.506469f, .129396f, .195001f, false, -.016886f},
    {"Slime.mesh", .306282f, -.129409f, -.520964f, .129396f, .195001f, false, -.016886f},
    {"Slime.mesh", .560469f, -.129409f, -.554726f, .129396f, .195001f, false, -.016886f},
    {"Slime.mesh", .59f, -.129409f, -.554726f, .129396f, .195001f, false, -.016886f},
    {"Slime.mesh", .686024f, -.129409f, -.554726f, .129396f, .195001f, false, -.016886f},
    {"Slime.mesh", .71f, -.129409f, -.554726f, .129396f, .195001f, false, -.016886f},
    {"Slime.mesh", .767922f, -.129409f, -.554726f, .129396f, .195001f, false, -.016886f},
    {"Slime.mesh", .805918f, -.129409f, -.554726f, .129396f, .195001f, false, -.016886f},
    {"Slime.mesh", .841464f, -.129409f, -.554726f, .129396f, .195001f, false, -.016886f},
    {"Slime.mesh", .952407f, -.129409f, -.554726f, .129396f, .195001f, false, -.016886f},
    {"Slime.mesh", 1.28522f, -.129409f, -.554726f, .129396f, .195001f, false, -.016886f},
    {"Spider.mesh", .073802f, -.37984f, -.413525f, .374666f, .404982f, false, -.085179f},
    {"Spider.mesh", .087917f, -.37984f, -.413525f, .374666f, .404982f, false, -.085179f},
    {"Spider.mesh", .276672f, -.37984f, -.413525f, .374666f, .404982f, false, -.085179f},
    {"Spider.mesh", .306282f, -.37984f, -.413525f, .374666f, .404982f, false, -.085179f},
    {"Spider.mesh", .560469f, -.37984f, -.413525f, .374666f, .404982f, false, -.085179f},
    {"Spider.mesh", .59f, -.37984f, -.413525f, .374666f, .404982f, false, -.085179f},
    {"Spider.mesh", .686024f, -.37984f, -.413525f, .374666f, .404982f, false, -.085179f},
    {"Spider.mesh", .71f, -.37984f, -.413525f, .374666f, .404982f, false, -.085179f},
    {"Spider.mesh", .767922f, -.37984f, -.413525f, .374666f, .404982f, false, -.085179f},
    {"Spider.mesh", .805918f, -.37984f, -.413525f, .374666f, .404982f, false, -.085179f},
    {"Spider.mesh", .841464f, -.37984f, -.413525f, .374666f, .404982f, false, -.085179f},
    {"Spider.mesh", .952407f, -.37984f, -.413525f, .374666f, .404982f, false, -.085179f},
    {"Spider.mesh", 1.28522f, -.37984f, -.413525f, .374666f, .404982f, false, -.085179f},
    {"TentacleAlbine.mesh", .073802f, -.175996f, -.269539f, .16886f, .293374f, false, .011767f},
    {"TentacleAlbine.mesh", .087917f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleAlbine.mesh", .276672f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleAlbine.mesh", .306282f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleAlbine.mesh", .560469f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleAlbine.mesh", .59f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleAlbine.mesh", .686024f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleAlbine.mesh", .71f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleAlbine.mesh", .767922f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleAlbine.mesh", .805918f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleAlbine.mesh", .841464f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleAlbine.mesh", .952407f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleAlbine.mesh", 1.28522f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleGreen.mesh", .073802f, -.175996f, -.269539f, .16886f, .293374f, false, .011767f},
    {"TentacleGreen.mesh", .087917f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleGreen.mesh", .276672f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleGreen.mesh", .306282f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleGreen.mesh", .560469f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleGreen.mesh", .59f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleGreen.mesh", .686024f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleGreen.mesh", .71f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleGreen.mesh", .767922f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleGreen.mesh", .805918f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleGreen.mesh", .841464f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleGreen.mesh", .952407f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"TentacleGreen.mesh", 1.28522f, -.175996f, -.270396f, .16886f, .293374f, false, .011767f},
    {"Troll.mesh", .073802f, -.531179f, -.502311f, .532976f, .424564f, false, -.008895f},
    {"Troll.mesh", .087917f, -.537789f, -.502311f, .539076f, .424564f, false, -.008895f},
    {"Troll.mesh", .276672f, -.584778f, -.502311f, .596397f, .424564f, false, -.008895f},
    {"Troll.mesh", .306282f, -.590269f, -.502311f, .604276f, .424564f, false, -.008895f},
    {"Troll.mesh", .560469f, -.616233f, -.502311f, .625831f, .424564f, false, -.008895f},
    {"Troll.mesh", .59f, -.616233f, -.502311f, .625831f, .424564f, false, -.008895f},
    {"Troll.mesh", .686024f, -.616233f, -.502311f, .625831f, .424564f, false, -.008895f},
    {"Troll.mesh", .71f, -.616233f, -.502311f, .625831f, .424564f, false, -.008895f},
    {"Troll.mesh", .767922f, -.616233f, -.502311f, .625831f, .424564f, false, -.008895f},
    {"Troll.mesh", .805918f, -.616233f, -.502311f, .625831f, .424564f, false, -.008895f},
    {"Troll.mesh", .841464f, -.616233f, -.502311f, .625831f, .424564f, false, -.008895f},
    {"Troll.mesh", .952407f, -.616233f, -.502311f, .625831f, .424564f, false, -.008895f},
    {"Troll.mesh", 1.28522f, -.616233f, -.502311f, .625831f, .424564f, false, -.008895f},
    {"Wizard.mesh", .073802f, -.147413f, -.22372f, .13172f, .368029f, false, -.047371f},
    {"Wizard.mesh", .087917f, -.147413f, -.22372f, .13172f, .368029f, false, -.047371f},
    {"Wizard.mesh", .276672f, -.147413f, -.22372f, .13172f, .368029f, false, -.047371f},
    {"Wizard.mesh", .306282f, -.147413f, -.22372f, .13172f, .368029f, false, -.047371f},
    {"Wizard.mesh", .560469f, -.228867f, -.22372f, .232063f, .368029f, false, -.047371f},
    {"Wizard.mesh", .59f, -.228867f, -.22372f, .232063f, .368029f, false, -.047371f},
    {"Wizard.mesh", .686024f, -.228867f, -.22372f, .232063f, .368029f, false, -.047371f},
    {"Wizard.mesh", .71f, -.228867f, -.22372f, .232063f, .368029f, false, -.047371f},
    {"Wizard.mesh", .767922f, -.228867f, -.22372f, .232063f, .368029f, false, -.047371f},
    {"Wizard.mesh", .805918f, -.228867f, -.22372f, .232063f, .368029f, false, -.047371f},
    {"Wizard.mesh", .841464f, -.228867f, -.22372f, .232063f, .368029f, false, -.047371f},
    {"Wizard.mesh", .952407f, -.228867f, -.22372f, .232063f, .368029f, false, -.047371f},
    {"Wizard.mesh", 1.28522f, -.228867f, -.22372f, .232063f, .368029f, false, -.047371f},
    {"Wyvern.mesh", .073802f, 0.0f, 0.0f, 0.0f, 0.0f, true, 0.0f},
    {"Wyvern.mesh", .087917f, 0.0f, 0.0f, 0.0f, 0.0f, true, 0.0f},
    {"Wyvern.mesh", .276672f, -.300208f, -.0707f, .300209f, .501527f, false, .095168f},
    {"Wyvern.mesh", .306282f, -.307658f, -.0707f, .30766f, .528634f, false, .095168f},
    {"Wyvern.mesh", .560469f, -.546165f, -.308589f, .546166f, .60904f, false, .095168f},
    {"Wyvern.mesh", .59f, -.551233f, -.308589f, .551233f, .60904f, false, .095168f},
    {"Wyvern.mesh", .686024f, -.55849f, -.308589f, .55849f, .60904f, false, .095168f},
    {"Wyvern.mesh", .71f, -.55849f, -.308589f, .55849f, .60904f, false, .095168f},
    {"Wyvern.mesh", .767922f, -.55849f, -.308589f, .55849f, .60904f, false, .095168f},
    {"Wyvern.mesh", .805918f, -.55849f, -.308589f, .55849f, .60904f, false, .095168f},
    {"Wyvern.mesh", .841464f, -.55849f, -.308589f, .55849f, .60904f, false, .095168f},
    {"Wyvern.mesh", .952407f, -.55849f, -.308589f, .55849f, .60904f, false, .095168f},
    {"Wyvern.mesh", 1.28522f, -.55849f, -.308589f, .55849f, .60904f, false, .095168f},
    {"lich.mesh", .073802f, -.329927f, -.81278f, .335793f, .647753f, false, -.08541f},
    {"lich.mesh", .087917f, -.332446f, -.81278f, .335793f, .649941f, false, -.08541f},
    {"lich.mesh", .276672f, -.332446f, -.81278f, .335793f, .651376f, false, -.08541f},
    {"lich.mesh", .306282f, -.332446f, -.81278f, .335793f, .651376f, false, -.08541f},
    {"lich.mesh", .560469f, -.332446f, -.81278f, .417298f, .651376f, false, -.08541f},
    {"lich.mesh", .59f, -.332446f, -.81278f, .417298f, .651376f, false, -.08541f},
    {"lich.mesh", .686024f, -.332446f, -.81278f, .417298f, .651376f, false, -.08541f},
    {"lich.mesh", .71f, -.332446f, -.81278f, .417298f, .651376f, false, -.08541f},
    {"lich.mesh", .767922f, -.332446f, -.81278f, .417298f, .651376f, false, -.08541f},
    {"lich.mesh", .805918f, -.332446f, -.81278f, .417298f, .651376f, false, -.08541f},
    {"lich.mesh", .841464f, -.332446f, -.81278f, .417298f, .651376f, false, -.08541f},
    {"lich.mesh", .952407f, -.489306f, -.81278f, .417298f, .651376f, false, -.08541f},
    {"lich.mesh", 1.28522f, -.505414f, -.81278f, .417298f, .651376f, false, -.08541f},
    {"skeleton.mesh", .073802f, -.149769f, -.576067f, .158873f, .422069f, false, -.056416f},
    {"skeleton.mesh", .087917f, -.149769f, -.576067f, .158873f, .424316f, false, -.056416f},
    {"skeleton.mesh", .276672f, -.149769f, -.576067f, .158873f, .430293f, false, -.056416f},
    {"skeleton.mesh", .306282f, -.149769f, -.576067f, .158873f, .430293f, false, -.056416f},
    {"skeleton.mesh", .560469f, -.23887f, -.576067f, .245288f, .430293f, false, -.056416f},
    {"skeleton.mesh", .59f, -.23887f, -.576067f, .247509f, .430293f, false, -.056416f},
    {"skeleton.mesh", .686024f, -.23887f, -.576067f, .247509f, .430293f, false, -.056416f},
    {"skeleton.mesh", .71f, -.23887f, -.576067f, .251654f, .430293f, false, -.056416f},
    {"skeleton.mesh", .767922f, -.23887f, -.576067f, .264971f, .430293f, false, -.056416f},
    {"skeleton.mesh", .805918f, -.23887f, -.576067f, .268597f, .430293f, false, -.056416f},
    {"skeleton.mesh", .841464f, -.23887f, -.576067f, .269937f, .430293f, false, -.056416f},
    {"skeleton.mesh", .952407f, -.23887f, -.576067f, .269937f, .430293f, false, -.056416f},
    {"skeleton.mesh", 1.28522f, -.23887f, -.576067f, .269937f, .430293f, false, -.056416f}
};

// The band measured for this creature below a furniture top, or nullptr when
// that height is not a measured bed top (the full walking envelope applies).
inline const BodyBand* bodyBand(const std::string& mesh, float height)
{
    for(const BodyBand& band : bodyBands)
        if(mesh == band.name && std::abs(band.height - height) < .0001f)
            return &band;
    return nullptr;
}
}

#endif
