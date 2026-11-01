"""Check worker allocation wiring and the plan's fixed/free quota cases.

Run with --static-only during the plan; the default compiles the acceptance cases in FINAL.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
header = (root / 'source/game/WorkerAllocation.h').read_text(encoding='utf-8')
assert 'fixedQuotas' in header and 'freeTargets' in header
if '--static-only' not in sys.argv:
    probe = r'''
#include "game/WorkerAllocation.h"
#include <array>
#include <cassert>
using A = std::array<uint32_t, 6>;
int main() {
    const A order{{0,1,2,3,4,5}}, parts{{6,5,4,3,2,1}};
    assert((WorkerAllocation::fixedQuotas(A{{10,0,0,0,10,0}},10) == A{{5,0,0,0,5,0}}));
    assert((WorkerAllocation::fixedQuotas(A{{10,0,0,0,10,0}},9) == A{{5,0,0,0,4,0}}));
    assert((WorkerAllocation::fixedQuotas(A{{3,2,0,0,0,0}},0) == A{{0,0,0,0,0,0}}));
    assert((WorkerAllocation::freeTargets(9,A{{20,15,0,0,1,0}},false,order,parts) == A{{4,4,0,0,1,0}}));
    assert((WorkerAllocation::freeTargets(0,A{{5,5,5,5,5,5}},false,order,parts) == A{{0,0,0,0,0,0}}));
    assert((WorkerAllocation::freeTargets(5,A{{0,0,0,0,0,0}},false,order,parts) == A{{0,0,0,0,0,0}}));
    assert((WorkerAllocation::freeTargets(10,A{{99,99,99,99,99,99}},true,order,parts) == A{{3,2,2,1,1,1}}));
    assert((WorkerAllocation::freeTargets(7,A{{99,99,99,99,0,0}},true,order,parts) == A{{2,2,2,1,0,0}}));
    assert((WorkerAllocation::freeTargets(5,A{{0,0,0,0,0,0}},true,order,parts) == A{{0,0,0,0,0,0}}));
    assert((WorkerAllocation::freeTargets(10,A{{1,99,99,99,99,99}},true,order,parts) == A{{1,3,2,2,1,1}}));
    std::vector<WorkerAllocation::Worker> ranked{
        {{{1,0,0,0,0,0}}, 3, "Ada", 0, true},
        {{{5,0,0,0,0,0}}, 1, "Bea", 0, true},
        {{{4,0,0,0,0,0}}, 2, "Cora", 6, false}};
    WorkerAllocation::assignFixed(ranked, A{{1,0,0,0,1,0}});
    assert(ranked[0].fixed && ranked[0].job == 4);
    assert(ranked[1].fixed && ranked[1].job == 0);
    assert(!ranked[2].fixed && ranked[2].job == 6);
    std::vector<WorkerAllocation::Worker> shortage{
        {{{5,0,0,0,0,0}}, 1, "Ada", 4, true},
        {{{1,0,0,0,0,0}}, 1, "Bea", 4, true}};
    WorkerAllocation::assignFixed(shortage, A{{1,0,0,0,1,0}});
    assert(shortage[0].job == 0 && shortage[0].fixed);
    assert(shortage[1].job == 4 && shortage[1].fixed);
    const std::array<bool,6> all{{true,true,true,true,true,true}};
    const std::array<bool,6> noDig{{false,true,true,true,true,true}};
    assert(WorkerAllocation::chooseFreeJob(0,A{{1,0,0,0,0,0}},A{{1,2,0,0,0,0}},all) == 0);
    assert(WorkerAllocation::chooseFreeJob(0,A{{2,0,0,0,0,0}},A{{1,2,0,0,0,0}},all) == 1);
    assert(WorkerAllocation::chooseFreeJob(0,A{{1,0,0,0,0,0}},A{{2,1,0,0,0,0}},noDig) == 1);
    assert(WorkerAllocation::chooseFreeJob(6,A{{0,0,0,0,0,0}},A{{0,0,0,0,0,0}},all) == 6);
}
'''
    with tempfile.TemporaryDirectory(prefix='odp-worker-allocation-') as directory:
        work = Path(directory)
        (work / 'probe.cpp').write_text(probe, encoding='utf-8')
        subprocess.run(['cl', '/nologo', '/EHsc', '/std:c++17', '/I' + str(root / 'source'), 'probe.cpp', '/Fe:probe.exe'], cwd=work, check=True)
        subprocess.run([str(work / 'probe.exe')], cwd=work, check=True)
print('worker allocation checks passed')
