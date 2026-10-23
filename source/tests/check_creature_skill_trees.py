"""Check the creature skill tree system (package C of the attribute plan): skill points, ranks, unlock rules,
pre-skill, tier 4, template order, personal deviation with a fixed seed, reset rules, stream round trip, skill line
building and the wiring in the creature code (passives, new skill kinds, effect stacking, packets).

The rules are checked twice: the compiled probe runs CreatureSkillTree.cpp (it has no engine dependency) and a Python
model written from the rules computes the expected result. The probe needs the compiler (cl) in the PATH; without it
only the source checks run, with --probe a missing compiler is an error.
The content of config/creatureSkills.cfg (every skill row of the catalog and the templates) is checked by a later
package; this script uses the small example config in source/tests/fixtures.
"""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
FIXTURE = root / 'source/tests/fixtures/creature_skills_example.cfg'
BS = chr(92)

# Constants of the rules (the same as the plan states them)
FIRST_LEVEL = 10
MAX_RANK = 5
DEVIATION = 25
TIER_FOUR_MIN_SPENT = 20
RESET_FOLLOWERS = 3
CHICKENS = 2
WINDOW = 60.0


def text(relative):
    return (root / relative).read_text(encoding='utf-8')


# ---------------------------------------------------------------- Python model of the rules
def parse_fixture(path):
    """Reads the example config: skills by id, tier four skills and templates."""
    skills, tiers, templates, block, kind = {}, {}, [], None, None
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.split('#')[0].strip()
        if not line:
            continue
        if line.startswith('[/'):
            if kind == 'Skill':
                skills[block['Id']] = block
            elif kind == 'TierFour':
                tiers[block['Creature']] = block
            else:
                templates.append(block)
            block = None
        elif line.startswith('['):
            kind, block = line.strip('[]'), {}
        else:
            key, _, rest = line.partition(' ')
            block[key] = rest.strip()
    return skills, tiers, templates


SKILLS, TIERS, TEMPLATES = parse_fixture(FIXTURE)


def owner_of(skill):
    return skill.get('Group') or skill.get('Family').lower()


def path_skill(owner, path, tier):
    for skill in SKILLS.values():
        if owner_of(skill) == owner and skill['Path'].lower() == path.lower() and int(skill['Tier']) == tier:
            return skill['Id']
    return ''


def can_raise(ranks, spent, group, family, tier_four, skill_id):
    if skill_id == tier_four:
        return ranks.get(skill_id, 0) == 0 and spent >= TIER_FOUR_MIN_SPENT
    skill = SKILLS.get(skill_id)
    if skill is None or owner_of(skill) not in (group, family):
        return False
    if ranks.get(skill_id, 0) >= MAX_RANK:
        return False
    tier = int(skill['Tier'])
    if tier == 1:
        return True
    previous = path_skill(owner_of(skill), skill['Path'], tier - 1)
    return ranks.get(previous, 0) >= (1 if tier == 2 else 2)


def model_picks(group, family, template):
    primary = [path_skill(group, template['Primary'], tier) for tier in (1, 2, 3)]
    picks = [primary[0], primary[1], primary[1], primary[2]]
    picks += [primary[0]] * (MAX_RANK - 1) + [primary[1]] * (MAX_RANK - 2) + [primary[2]] * (MAX_RANK - 1)
    if family:
        fam_path = next(s['Path'] for s in SKILLS.values() if owner_of(s) == family)
        fam = [path_skill(family, fam_path, tier) for tier in (1, 2, 3)]
        picks += [fam[0], fam[0], fam[1], fam[1], fam[2]]
    return picks


def model_build(template_index, seed, pre, level, group='blocker', family='greenskin', tier_four='T4_Orc'):
    """Spends the points of a creature of the level from level 10 on, one per level, as plan section 7.8 says."""
    template = [t for t in TEMPLATES if t['Group'] == group][template_index]
    ranks = {pre: 1} if pre else {}
    state, cursor, order = seed, 0, []
    picks = model_picks(group, family, template)
    alternative = [path_skill(group, template['Alternative'], tier) for tier in (1, 2, 3)]
    fam_path = next(s['Path'] for s in SKILLS.values() if owner_of(s) == family)
    family_ids = [path_skill(family, fam_path, tier) for tier in (1, 2, 3)]
    others = [path_skill(group, name, tier) for name in ('Arms', 'Bulwark', 'War Cries') for tier in (1, 2, 3)]

    def spent():
        return sum(v for k, v in ranks.items() if not k.startswith('T4_')) - (1 if pre and ranks.get(pre, 0) >= 1 else 0)

    for _ in range(max(0, level - FIRST_LEVEL + 1)):
        done = spent()
        if done >= TIER_FOUR_MIN_SPENT:
            if can_raise(ranks, done, group, family, tier_four, tier_four):
                ranks[tier_four] = 1
                order.append(tier_four)
            continue
        state = (1103515245 * state + 12345) % (2 ** 31)
        raised = None
        if state % 100 < DEVIATION:
            for skill_id in alternative:
                if can_raise(ranks, done, group, family, tier_four, skill_id):
                    raised = skill_id
                    break
        if raised is None:
            while cursor < len(picks):
                pick = picks[cursor]
                cursor += 1
                if can_raise(ranks, done, group, family, tier_four, pick):
                    raised = pick
                    break
        if raised is None:
            for skill_id in family_ids + others:
                if can_raise(ranks, done, group, family, tier_four, skill_id):
                    raised = skill_id
                    break
        if raised is None:
            break
        ranks[raised] = ranks.get(raised, 0) + 1
        order.append(raised)
    return ranks, order


# ---------------------------------------------------------------- compiled probe
PROBE = r'''
#include "creatureskill/CreatureSkillTree.h"
#include <fstream>
#include <iostream>
#include <sstream>
using namespace CreatureSkillTree;

static void printRanks(const SkillBuild& build)
{
    for(std::map<std::string, uint32_t>::const_iterator it = build.mRanks.begin(); it != build.mRanks.end(); ++it)
        std::cout << " " << it->first << "=" << it->second;
}

int main(int argc, char** argv)
{
    std::ifstream file(argv[1]);
    SkillTreeConfig config;
    std::string error;
    if(!config.load(file, error))
    {
        std::cout << "load error " << error << std::endl;
        return 1;
    }
    std::cout << "counts " << config.getSkills().size() << " " << config.getTierFours().size() << " "
              << config.getTemplateDefs().size() << std::endl;

    const uint32_t levels[5] = {1, 9, 10, 11, 30};
    for(int i = 0; i < 5; ++i)
        std::cout << "points " << levels[i] << " " << pointsAtLevel(levels[i], 10) << std::endl;

    TypeInfo orc;
    orc.mGroup = "blocker";
    orc.mFamily = "greenskin";
    orc.mTierFour = "T4_Orc";
    SkillBuild empty;
    std::cout << "unlock A2 empty " << canRaise(config, orc, empty, "BLK_A2", 5) << std::endl;
    SkillBuild one;
    one.mRanks["BLK_A1"] = 1;
    std::cout << "unlock A2 after A1 " << canRaise(config, orc, one, "BLK_A2", 5) << std::endl;
    one.mRanks["BLK_A2"] = 1;
    std::cout << "unlock A3 after A2 rank 1 " << canRaise(config, orc, one, "BLK_A3", 5) << std::endl;
    one.mRanks["BLK_A2"] = 2;
    std::cout << "unlock A3 after A2 rank 2 " << canRaise(config, orc, one, "BLK_A3", 5) << std::endl;
    std::cout << "unlock other path tier 2 " << canRaise(config, orc, one, "BLK_B2", 5) << std::endl;
    std::cout << "unlock rank limit " << canRaise(config, orc, one, "BLK_A1", 1) << std::endl;
    std::cout << "unlock foreign skill " << canRaise(config, orc, one, "GRN_9", 5) << std::endl;
    SkillBuild nineteen;
    nineteen.mRanks["BLK_A1"] = 5;
    nineteen.mRanks["BLK_A2"] = 5;
    nineteen.mRanks["BLK_A3"] = 5;
    nineteen.mRanks["BLK_B1"] = 4;
    std::cout << "tier4 at 19 " << canRaise(config, orc, nineteen, "T4_Orc", 5) << std::endl;
    nineteen.mRanks["BLK_B1"] = 5;
    std::cout << "tier4 at 20 " << canRaise(config, orc, nineteen, "T4_Orc", 5) << std::endl;
    SkillBuild preSkilled;
    TypeInfo pre = orc;
    pre.mPreSkill = "GRN_1";
    startBuild(preSkilled, pre, 77);
    std::cout << "pre spent " << spentInPaths(preSkilled, pre) << " rank " << getRank(preSkilled, "GRN_1") << std::endl;

    for(int t = 0; t < 3; ++t)
    {
        std::cout << "picks " << t;
        std::vector<std::string> picks = templatePicks(config, orc, t, 5);
        for(size_t i = 0; i < picks.size(); ++i)
            std::cout << " " << picks[i];
        std::cout << std::endl;
    }

    const uint32_t seeds[4] = {1, 12345, 987654321u, 4000000000u};
    for(int t = 0; t < 3; ++t)
    {
        for(int s = 0; s < 4; ++s)
        {
            for(int p = 0; p < 2; ++p)
            {
                TypeInfo type = orc;
                if(p == 1)
                    type.mPreSkill = "GRN_1";
                SkillBuild build;
                build.mTemplate = t;
                startBuild(build, type, seeds[s]);
                std::cout << "build " << t << " " << seeds[s] << " " << p << " :";
                for(uint32_t level = 10; level <= 30; ++level)
                {
                    const std::string raised = spendNextPoint(config, type, build, 25.0, 5);
                    std::cout << " " << raised;
                }
                std::cout << " |";
                printRanks(build);
                std::cout << std::endl;
            }
        }
    }

    // The personal generator
    SkillBuild draws;
    draws.mRngState = 12345;
    std::cout << "draws";
    for(int i = 0; i < 5; ++i)
        std::cout << " " << nextDeviationDraw(draws);
    std::cout << std::endl;

    // Level up by level: spendUpToLevel gives the same result as the single points
    {
        SkillBuild leveled;
        leveled.mTemplate = 1;
        startBuild(leveled, orc, 12345);
        spendUpToLevel(config, orc, leveled, 9, 10, 25.0, 5);
        std::cout << "leveled 9 spent " << spentPoints(leveled, orc) << std::endl;
        spendUpToLevel(config, orc, leveled, 10, 10, 25.0, 5);
        std::cout << "leveled 10 spent " << spentPoints(leveled, orc) << std::endl;
        spendUpToLevel(config, orc, leveled, 30, 10, 25.0, 5);
        std::cout << "leveled 30 spent " << spentPoints(leveled, orc) << " tier4 " << getRank(leveled, "T4_Orc")
                  << " paths " << spentInPaths(leveled, orc) << std::endl;
        spendUpToLevel(config, orc, leveled, 30, 10, 25.0, 5);
        std::cout << "leveled again spent " << spentPoints(leveled, orc) << std::endl;
    }

    // Template choice: weight 1, times 3 when nobody follows
    {
        std::vector<uint32_t> followers;
        followers.push_back(2);
        followers.push_back(0);
        followers.push_back(1);
        const double units[6] = {0.0, 0.19, 0.2, 0.79, 0.8, 0.99};
        std::cout << "choose";
        for(int i = 0; i < 6; ++i)
            std::cout << " " << chooseTemplate(followers, units[i]);
        std::cout << std::endl;
        std::vector<uint32_t> none(3, 0);
        std::cout << "choose none";
        for(int i = 0; i < 6; ++i)
            std::cout << " " << chooseTemplate(none, units[i]);
        std::cout << std::endl;
    }

    // Reset rules
    {
        std::vector<uint32_t> followers;
        followers.push_back(3);
        followers.push_back(0);
        followers.push_back(0);
        std::cout << "reset a " << findResetTemplate(0, followers) << std::endl;
        followers[0] = 2;
        std::cout << "reset b " << findResetTemplate(0, followers) << std::endl;
        followers[0] = 3;
        followers[1] = 1;
        followers[2] = 1;
        std::cout << "reset c " << findResetTemplate(0, followers) << std::endl;
        followers[2] = 0;
        std::cout << "reset d " << findResetTemplate(0, followers) << std::endl;
        std::cout << "reset e " << findResetTemplate(-1, followers) << std::endl;

        SkillBuild chicken;
        countChicken(chicken, 2, 60.0);
        std::cout << "chicken 1 " << chicken.mChickens << " " << chicken.mRespecWindow << std::endl;
        countChicken(chicken, 2, 60.0);
        std::cout << "chicken 2 " << chicken.mChickens << " " << chicken.mRespecWindow << std::endl;
        tickRespecWindow(chicken, 59.5);
        std::cout << "window " << chicken.mRespecWindow << std::endl;
        tickRespecWindow(chicken, 1.0);
        std::cout << "window end " << chicken.mRespecWindow << std::endl;

        TypeInfo type = orc;
        type.mPreSkill = "GRN_1";
        SkillBuild before;
        before.mTemplate = 0;
        startBuild(before, type, 4242);
        spendUpToLevel(config, type, before, 30, 10, 25.0, 5);
        SkillBuild after = before;
        resetBuild(config, type, after, 2, 30, 10, 25.0, 5);
        std::cout << "reset build template " << after.mTemplate << " spent " << spentPoints(after, type) << " pre "
                  << getRank(after, "GRN_1") << " seed " << after.mSeed << " :";
        printRanks(after);
        std::cout << std::endl;
        SkillBuild again = before;
        resetBuild(config, type, again, 2, 30, 10, 25.0, 5);
        std::cout << "reset repeat " << (again.mRanks == after.mRanks) << std::endl;
        SkillBuild low = before;
        resetBuild(config, type, low, 1, 12, 10, 25.0, 5);
        std::cout << "reset level 12 spent " << spentPoints(low, type) << " pre " << getRank(low, "GRN_1") << std::endl;
    }

    // Save and stream round trip
    {
        SkillBuild build;
        build.mTemplate = 2;
        startBuild(build, orc, 31337);
        spendUpToLevel(config, orc, build, 20, 10, 25.0, 5);
        build.mChickens = 1;
        build.mRespecWindow = 12.25;
        std::ostringstream out;
        writeBuild(build, out);
        std::cout << "stream " << out.str() << std::endl;
        std::istringstream in(out.str());
        SkillBuild back;
        const bool ok = readBuild(in, back);
        std::ostringstream again;
        writeBuild(back, again);
        std::cout << "roundtrip " << ok << " " << (again.str() == out.str()) << " " << (back.mRanks == build.mRanks)
                  << std::endl;
        std::istringstream shortInput("2 31337 5");
        SkillBuild bad;
        std::cout << "short " << readBuild(shortInput, bad) << std::endl;
        std::cout << "passive dmg " << passiveSum(config, build, "dmg%") << " hp " << passiveSum(config, build, "hp%")
                  << " none " << passiveSum(config, build, "ar%") << std::endl;
    }

    // Skill lines
    {
        SkillNumber none;
        SkillNumber seven;
        seven.mSet = true;
        seven.mValue = 55;
        const SkillDef* roar = config.findSkill("BLK_C1");
        std::cout << "line roar1 " << buildSkillLine(roar->mKind, roar->mValues[0], roar->mCooldown, roar->mDuration,
            roar->mRadius, roar->mRange, roar->mBaseLine) << std::endl;
        std::cout << "line roar5 " << buildSkillLine(roar->mKind, roar->mValues[4], roar->mCooldown, roar->mDuration,
            roar->mRadius, roar->mRange, roar->mBaseLine) << std::endl;
        const SkillDef* spin = config.findSkill("BLK_C3");
        std::cout << "line spin " << buildSkillLine(spin->mKind, spin->mValues[2], spin->mCooldown, spin->mDuration,
            spin->mRadius, spin->mRange, spin->mBaseLine) << std::endl;
        const SkillDef* rally = config.findSkill("BLK_C2");
        std::cout << "line rally " << buildSkillLine(rally->mKind, rally->mValues[1], rally->mCooldown,
            rally->mDuration, rally->mRadius, rally->mRange, rally->mBaseLine) << std::endl;
        const SkillDef* blow = config.findSkill("BLK_A3");
        std::cout << "line strike " << buildSkillLine(blow->mKind, blow->mValues[3], blow->mCooldown, blow->mDuration,
            blow->mRadius, blow->mRange, blow->mBaseLine) << std::endl;
        const SkillDef* wall = config.findSkill("BLK_B2");
        std::cout << "line defense " << buildSkillLine(wall->mKind, wall->mValues[0], wall->mCooldown,
            wall->mDuration, wall->mRadius, wall->mRange, wall->mBaseLine) << std::endl;
        const SkillDef* mend = config.findSkill("GRN_3");
        std::cout << "line heal " << buildSkillLine(mend->mKind, mend->mValues[1], mend->mCooldown, mend->mDuration,
            mend->mRadius, mend->mRange, mend->mBaseLine) << std::endl;
        const SkillDef* passive = config.findSkill("BLK_A1");
        std::cout << "line passive [" << buildSkillLine(passive->mKind, passive->mValues[0], passive->mCooldown,
            passive->mDuration, passive->mRadius, passive->mRange, passive->mBaseLine) << "]" << std::endl;
        const TierFourDef* frenzy = config.findTierFour("Orc");
        std::cout << "line tier4 " << buildSkillLine(frenzy->mKind, frenzy->mValue, frenzy->mCooldown,
            frenzy->mDuration, frenzy->mRadius, frenzy->mRange, frenzy->mBaseLine) << std::endl;
        std::cout << "line explosion " << buildSkillLine("EXPLOSION", "0.5", none, none, none, none,
            "Explosion 40 2 6 12 1 30.75 20.5") << std::endl;
        std::cout << "line grenade " << buildSkillLine("GRENADE", "0.5", seven, none, none, none,
            "Grenade 10 2 6 0 8 Cannonball none 1 0 0 0 0 5 0.1 2 0 0 0 0 6.97 10.46") << std::endl;
        std::cout << "line missing base " << buildSkillLine("EXPLOSION", "0.5", none, none, none, none, "").size()
                  << std::endl;
        std::cout << "line class " << skillClassOfKind("HEAL_AREA") << " " << skillClassOfKind("PASSIVE_hp%").size()
                  << std::endl;
    }
    return 0;
}
'''


def run_probe(require):
    compiler = shutil.which('cl')
    if compiler is None:
        assert not require, '--probe needs the compiler (cl) in the PATH'
        print('compiled probe not run (no cl in the PATH)')
        return None
    with tempfile.TemporaryDirectory() as work_name:
        work = Path(work_name)
        (work / 'probe.cpp').write_text(PROBE, encoding='utf-8')
        subprocess.run(['cl', '/nologo', '/EHsc', '/std:c++17', f'/I{root / "source"}', 'probe.cpp',
                        str(root / 'source/creatureskill/CreatureSkillTree.cpp'), '/Fe:probe.exe'],
                       cwd=work, check=True, stdout=subprocess.DEVNULL)
        result = subprocess.run([str(work / 'probe.exe'), str(FIXTURE)], cwd=work, check=True,
                                capture_output=True, text=True)
    return result.stdout.splitlines()


def lines_starting(output, prefix):
    return [line for line in output if line.startswith(prefix)]


def check_probe(output):
    out = '\n'.join(output)
    assert 'counts 12 1 3' in out, out[:200]
    # 7.1: one point per level from 10 to 30 (21 points)
    for level, points in ((1, 0), (9, 0), (10, 1), (11, 2), (30, 21)):
        assert f'points {level} {points}\n' in out + '\n', (level, points)
    # 7.2: unlock rules and tier 4
    for line, value in (('unlock A2 empty', 0), ('unlock A2 after A1', 1), ('unlock A3 after A2 rank 1', 0),
                        ('unlock A3 after A2 rank 2', 1), ('unlock other path tier 2', 0), ('unlock rank limit', 0),
                        ('unlock foreign skill', 0), ('tier4 at 19', 0), ('tier4 at 20', 1)):
        assert f'{line} {value}' in output, (line, value)
    # 7.3: the free rank of the pre-skill is not a spent point
    assert 'pre spent 0 rank 1' in output
    # 7.8: the point order of the templates, from the rules written down independently
    for index, template in enumerate(t for t in TEMPLATES if t['Group'] == 'blocker'):
        expected = 'picks %d %s' % (index, ' '.join(model_picks('blocker', 'greenskin', template)))
        assert expected in output, expected
    # 7.8: the whole build of every template, seed and pre-skill equals the model (deviation with fixed seeds)
    seeds = (1, 12345, 987654321, 4000000000)
    for t in range(3):
        for seed in seeds:
            for p, pre in enumerate(('', 'GRN_1')):
                ranks, order = model_build(t, seed, pre, 30)
                order += [''] * (21 - len(order))
                tail = ' '.join(f'{k}={v}' for k, v in sorted(ranks.items()))
                expected = f'build {t} {seed} {p} : ' + ' '.join(order) + ' | ' + tail
                got = [line for line in output if line.startswith(f'build {t} {seed} {p} :')]
                assert got and got[0].replace('  ', ' ') == expected.replace('  ', ' '), (expected, got)
                # 20 points are spent at level 29 and the tier 4 skill is the 21st point
                assert order[20] == 'T4_Orc' and 'T4_Orc' not in order[:20], (t, seed, p, order)
    assert 'draws ' + ' '.join(str(d) for d in lcg_draws(12345, 5)) in output
    # Deviation really happens: with 25 percent over 20 points some build differs from the plain template order
    plain = {t: model_build(t, 1, '', 30)[1] for t in range(3)}
    assert any(model_build(t, s, '', 30)[1] != plain[t] for t in range(3) for s in seeds[1:])
    # Level by level and a repeated call give the same state
    assert 'leveled 9 spent 0' in output and 'leveled 10 spent 1' in output
    assert 'leveled 30 spent 21 tier4 1 paths 20' in output and 'leveled again spent 21' in output
    # Template choice with weights 1, 3, 1 (total 5): 0 to 0.2 -> 0, 0.2 to 0.8 -> 1, 0.8 to 1 -> 2
    assert 'choose 0 0 1 1 2 2' in output
    assert 'choose none 0 0 0 2 2 2' in output
    # 7.8 reset rules
    for line in ('reset a 1', 'reset b -1', 'reset c -1', 'reset d 2', 'reset e -1'):
        assert line in output, line
    assert 'chicken 1 1 0' in output and 'chicken 2 0 60' in output
    assert 'window 0.5' in output and 'window end 0' in output
    reset = [line for line in output if line.startswith('reset build template 2 spent 21 pre ')]
    assert reset, 'a reset spends all points again and keeps the free rank of the pre-skill'
    ranks, _ = model_build(2, 4242, 'GRN_1', 30)
    assert reset[0].endswith(': ' + ' '.join(f'{k}={v}' for k, v in sorted(ranks.items()))), reset
    assert 'reset repeat 1' in output
    assert 'reset level 12 spent 3 pre 1' in output
    # Stream round trip of the new creature fields
    assert 'roundtrip 1 1 1' in output and 'short 0' in output
    stream = lines_starting(output, 'stream ')[0].split()
    assert stream[1:7] == ['2', '31337', stream[3], stream[4], '1', '12.25'], stream
    # Passives add up over the ranked skills
    passive = lines_starting(output, 'passive dmg')[0].split()
    assert passive[-1] == '0', passive
    # Skill lines (7.4, 7.6)
    expected_lines = {
        'line roar1': 'StrengthSelf 55 2 0 20 1.01',
        'line roar5': 'StrengthSelf 55 2 0 20 1.05',
        'line spin': 'Whirlwind 14 1 2 0 1 1',
        'line rally': 'AuraAlly 60 0 0 4 20 1.007',
        'line strike': 'Strike 30 0 0 1.188',
        'line defense': 'DefenseSelf 45 0 0 25 0.298 0.298 0.298',
        'line heal': 'HealSelf 35 0 0 5 0 2.758',
        'line passive': '',
        'line tier4': 'StrengthSelf 140 0 0 20 1.201',
        'line explosion': 'Explosion 40 2 6 0 1 15.375 10.25',
    }
    for prefix, line in expected_lines.items():
        got = [l for l in output if l.startswith(prefix + ' ')]
        assert got and got[0][len(prefix) + 1:].replace('[', '').replace(']', '') == line, (prefix, got, line)
    # A grenade line: the cooldown cell replaces the base cooldown, the rank value halves every damage value
    assert 'line grenade Grenade 55 2 6 0 0 Cannonball none 1 0 0 0 0 2.5 0.05 2 0 0 0 0 3.485 5.23' in output
    assert 'line missing base 0' in output
    assert 'line class HealArea 0' in output


def lcg_draws(seed, count):
    draws, state = [], seed
    for _ in range(count):
        state = (1103515245 * state + 12345) % (2 ** 31)
        draws.append(state % 100)
    return draws


# ---------------------------------------------------------------- source checks
def function(source, signature):
    """Returns the source of the function that starts with the signature (up to its closing brace)."""
    start = source.index(signature)
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def check_sources():
    creature_cpp = text('source/entities/Creature.cpp')
    creature_h = text('source/entities/Creature.h')
    cmake = text('CMakeLists.txt')
    config_manager = text('source/utils/ConfigManager.cpp')

    # The loader: creatureSkills.cfg is read by the ConfigManager, the file exists with a documented header
    cfg = text('config/creatureSkills.cfg')
    for key in ('Id', 'Name', 'Kind', 'Group', 'Family', 'Path', 'Tier', 'Values', 'Mana', 'Cooldown', 'Duration',
                'Radius', 'Range', 'BaseLine', 'Creature', 'Value', 'Index', 'Primary', 'Alternative'):
        assert re.search(r'^#\s+' + key + r'\s', cfg, re.M), key
    for block in ('[Skill]', '[TierFour]', '[Template]'):
        assert block in cfg
    assert 'loadCreatureSkills' in config_manager and 'mCreatureSkillTree.load(' in config_manager
    assert 'creatureSkills.cfg' in config_manager and 'CreatureSkills' in text('config/global.cfg')
    example = FIXTURE.read_text(encoding='utf-8')
    assert '[/Skill]' in example and '[/TierFour]' in example and '[/Template]' in example

    # The skill classes: one file pair each, registered like HealSelf
    for name in ('Strike', 'AuraAlly', 'HealAlly', 'HealArea'):
        header = text(f'source/creatureskill/CreatureSkill{name}.h')
        source = text(f'source/creatureskill/CreatureSkill{name}.cpp')
        assert f'class CreatureSkill{name} : public CreatureSkill' in header
        assert f'static CreatureSkillRegister reg(new CreatureSkill{name}Factory);' in source
        assert f'const std::string CreatureSkill{name}Name = "{name}";' in source
        assert f'creatureskill/CreatureSkill{name}.cpp' in cmake
    assert 'creatureskill/CreatureSkillTree.cpp' in cmake
    heal_self = text('source/creatureskill/CreatureSkillHealSelf.cpp')
    assert 'mHealPercent' in heal_self and 'getSkillHealSelfBelow' in heal_self

    # Passives are read from the ranks (the stub is gone) and used by the derived values
    body = function(creature_cpp, 'double Creature::getSkillPassive(')
    assert 'passiveSum' in body and 'return 0.0;\n}' not in body.replace(' ', '')
    for stat in ('cd%', 'avoid', 'move%', 'wake%', 'hp%', 'ar%', 'dr%'):
        assert f'getSkillPassive("{stat}")' in creature_cpp, stat

    # Points, template choice, deviation and reset are driven from the creature
    assert 'CreatureSkillTree::spendUpToLevel' in function(creature_cpp, 'void Creature::updateSkillPoints(')
    assert 'chooseTemplate' in function(creature_cpp, 'void Creature::updateSkillPoints(')
    assert 'updateSkillPoints();' in function(creature_cpp, 'void Creature::setLevel(')
    assert 'initSkillBuild();' in function(creature_cpp, 'void Creature::setupDefinition(')
    assert 'resetBuild' in function(creature_cpp, 'void Creature::upkeepSkillTree(') and \
        'findResetTemplate' in function(creature_cpp, 'void Creature::upkeepSkillTree(')
    assert 'upkeepSkillTree();' in function(creature_cpp, 'void Creature::doUpkeep(')
    assert 'registerChickenEaten();' in text('source/creatureaction/CreatureActionEatChicken.cpp')

    # Save and network: the stream and the three packets carry the skill state; old saves load without it
    assert 'SkillBuild' in function(creature_cpp, 'void Creature::exportToStream(')
    assert 'readBuild' in function(creature_cpp, 'bool Creature::importFromStream(')
    for signature, call in (('void Creature::exportToPacket(', 'exportSkillBuildToPacket(os);'),
                            ('void Creature::exportToPacketForUpdate(', 'exportSkillBuildToPacket(os);'),
                            ('void Creature::importFromPacket(', 'importSkillBuildFromPacket(is);'),
                            ('void Creature::updateFromPacket(', 'importSkillBuildFromPacket(is);')):
        assert call in function(creature_cpp, signature), signature

    # Effect stacking (7.4): products and sums of the active contributions, only the own one is removed
    for name in ('Strength', 'Speed'):
        update = function(creature_cpp, f'void Creature::update{name}Modifier(')
        assert 'modifier *= it->second;' in update
    assert 'phy += it->second.mPhy;' in function(creature_cpp, 'void Creature::updateDefenseModifier(')
    for effect, calls in (('StrengthChange', ('setStrengthContribution', 'removeStrengthContribution')),
                          ('SpeedChange', ('setSpeedContribution', 'removeSpeedContribution')),
                          ('Defense', ('setDefenseContribution', 'removeDefenseContribution'))):
        source = text(f'source/creatureeffect/CreatureEffect{effect}.cpp')
        for call in calls:
            assert call in source, (effect, call)
        assert 'clear' not in function(source, f'void CreatureEffect{effect}::releaseEffect(')
    assert 'releaseEffect(*this)' in function(creature_cpp, 'void Creature::doUpkeep(')
    add_effect = function(creature_cpp, 'void Creature::addCreatureEffect(')
    assert 'effectRefreshKey' in add_effect and 'delete effect;' in add_effect and 'mNbTurnsEffect = ' in add_effect

    # Skill kinds: STRIKE is consumed by the melee blow against creatures only, spell damage scaling of 7.6
    melee = function(text('source/creatureskill/CreatureSkillMeleeFight.cpp'), 'bool CreatureSkillMeleeFight::tryUseFight(')
    creature_branch = melee[melee.index('rollMeleeDefence'):melee.index('phyAtk = magAtk = eleAtk = 0.0;')]
    assert 'consumeStrikeMultiplier()' in creature_branch and 'consumeStrikeMultiplier' not in melee[:melee.index('rollAttackHit')]
    assert 'getTreeSpellDamageFactor()' in text('source/creatureskill/CreatureSkillExplosion.cpp')
    assert 'getTreeSpellDamageFactor()' in text('source/creatureskill/CreatureSkillAreaDamage.cpp')
    factor = function(creature_cpp, 'double Creature::getTreeSpellDamageFactor(')
    assert 'getSkillSpellReferenceMinHP' in factor and 'damageMultiplierAt' in factor and 'spell%' in factor
    base = function(creature_cpp, 'double Creature::getHealBase(')
    assert 'getManaLevel()' in base and 'getMinHp()' in base
    assert 'getMaxHp' in text('source/creatureskill/CreatureSkillHealAlly.cpp')


def main():
    require_probe = '--probe' in sys.argv
    check_sources()
    output = run_probe(require_probe)
    if output is not None:
        if '--show' in sys.argv:
            print(chr(10).join(output))
        check_probe(output)
    print('check_creature_skill_trees: ok')


main()
