"""Targeted ODP diagnostic-journal regressions; no game or compiler is launched."""
import importlib.util
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import hq_check_events as events

# Exercise the real journal with isolated Git snapshots.
class JournalTests(unittest.TestCase):
    # Create a committed fixture and one declared binary artifact.
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        subprocess.run(['git','init','-q',str(self.repo)],check=True)
        (self.repo/'source.txt').write_text('original')
        subprocess.run(['git','-C',str(self.repo),'add','source.txt'],check=True)
        subprocess.run(['git','-C',str(self.repo),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','fixture'],check=True)
        self.head = events.git(self.repo, 'rev-parse','HEAD')
        self.journal = self.repo/'events.jsonl'
        self.env = patch.dict(os.environ, {'HQ_CHECK_EVENTS':str(self.journal),'HQ_CHECK_RUN':'fixture-run','HQ_CHECK_COMMIT':self.head})
        self.env.start()
        self.addCleanup(self.env.stop)

    # Read only complete emitted records.
    def rows(self):
        return [json.loads(line) for line in self.journal.read_text().splitlines()]

    # Retry failures are non-final; later errors and complete logs are retained.
    def test_retry_and_complete_outputs(self):
        s = events.Session(self.repo, self.repo/'checks.txt', ['first','second'], {})
        s.result('first', 1, 'WinError 4551\n' + 'x'*100000, final=False)
        s.result('first', 0, 'retry passed')
        s.result('second', 7, 'later error')
        self.assertEqual(s.finish(), 1)
        rows = self.rows()
        results = [r for r in rows if r['event']=='result']
        self.assertEqual([r['final'] for r in results[:3]], [False, True, True])
        self.assertEqual([r['exit'] for r in results[:3]], [1,0,7])
        self.assertEqual(Path(results[0]['output_path']).read_text(), 'WinError 4551\n'+'x'*100000)
        self.assertTrue(all(len(json.dumps(r))<65536 for r in rows))

    # Changed artifacts and sources must invalidate publication evidence.
    def test_snapshot_changes(self):
        artifact=self.repo/'game.exe'; artifact.write_bytes(b'built')
        s=events.Session(self.repo,self.repo/'checks.txt',['load'],{'game.exe':events.digest(artifact)})
        s.result('load',0,'passed')
        artifact.write_bytes(b'changed')
        self.assertEqual(s.finish(),1)
        self.assertNotIn('shared_writes_finished',[r['event'] for r in self.rows()])

    # Nested checks cannot inherit the parent's journal or deferred-release ownership.
    def test_child_has_no_journal_ownership(self):
        child=events.child_environment({**os.environ,'HQ_CHECK_DEFER_RELEASE':'1','KEEP':'yes'})
        self.assertTrue(all(key not in child for key in (*events.KEYS,'HQ_CHECK_DEFER_RELEASE')))
        self.assertEqual(child['KEEP'],'yes')

    # An absent result is an explicit failure instead of a silently omitted check.
    def test_missing_result(self):
        s=events.Session(self.repo,self.repo/'checks.txt',['first','second'],{})
        s.result('first',1,'early error')
        self.assertEqual(s.finish(),1)
        rows=self.rows()
        self.assertTrue(any(r.get('check')=='second' and r['exit']!=0 for r in rows))

# Exercise the runner's failure drain with the game and compiler replaced by bounded fixture calls.
class RunnerTests(unittest.TestCase):
    rows = JournalTests.rows
    # Include two required checks and the agreed level in a clean fixture snapshot.
    def setUp(self):
        JournalTests.setUp(self)
        for name in ['scripts/check-a.py','scripts/check-b.py','scripts/run-level-test.py',
                     'scripts/run-campaign-load-tests.py','levels/campaign/Mossgate.level','build/windows/opendungeons-plus.exe']:
            target=self.repo/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_text('fixture')
        (self.repo/'levels/campaign/Campaign.cfg').write_text('[Level]\nFile=campaign/Mossgate.level\n')
        subprocess.run(['git','-C',str(self.repo),'add','.'],check=True)
        subprocess.run(['git','-C',str(self.repo),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','checks'],check=True)
        self.head=events.git(self.repo,'rev-parse','HEAD');os.environ['HQ_CHECK_COMMIT']=self.head
        spec=importlib.util.spec_from_file_location('fixture_runner',ROOT/'scripts/run-checks.py')
        self.runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.runner)

    # Early failure remains final while a permitted retry and the later level/deploy checks all finish.
    def test_early_failure_retry_and_load_drain(self):
        calls=[]
        def run(repo,rel,extra,timeout,env):
            calls.append(rel)
            if rel.endswith('check-a.py'):
                return 9,'first complete error',0
            if rel.endswith('check-b.py') and calls.count(rel)==1:
                self.assertTrue(any(r.get('check')=='scripts/check-a.py' and r.get('final') for r in self.rows()))
                return 1,'WinError 4551: retryable',0
            return 0,'complete output',0
        def load(*args,**kwargs):
            calls.append('load');return 3,'independent load error',0
        argv=['runner','--repo',str(self.repo),'--out',str(self.repo/'out/checks.txt'),'--base',self.head]
        (self.repo/'out').mkdir()
        with patch.object(sys,'argv',argv), patch.object(self.runner,'check_environment',return_value=dict(os.environ)), \
             patch.object(self.runner,'run_script',side_effect=run),patch.object(self.runner,'run_load_parallel',side_effect=load):
            self.assertEqual(self.runner.main(),1)
        rows=self.rows(); manifest=rows[0]
        finals={r['check']:r for r in rows if r['event']=='result' and r['final']}
        self.assertEqual(set(finals),set(manifest['checks']))
        self.assertEqual(finals['scripts/check-a.py']['exit'],9)
        self.assertEqual(finals['scripts/check-b.py']['exit'],0)
        self.assertEqual(finals['load:levels/campaign/Mossgate.level']['exit'],3)
        self.assertIn('load',calls)
        self.assertEqual(finals['deploy-readiness']['exit'],0)
        self.assertEqual([r['final'] for r in rows if r.get('check')=='scripts/check-b.py'],[False,True])

    # Build publication probes use the last successful deploy even when the passed integration base has advanced.
    def test_build_uses_successful_deploy_baseline(self):
        baseline=self.head
        level=self.repo/'levels/campaign/Other.level';level.write_text('changed map')
        subprocess.run(['git','-C',str(self.repo),'add',str(level)],check=True)
        subprocess.run(['git','-C',str(self.repo),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','new map'],check=True)
        tip=events.git(self.repo,'rev-parse','HEAD');os.environ['HQ_CHECK_COMMIT']=tip
        (self.repo/'.git/odp-deploy-success.json').write_text(json.dumps({'schema':1,'status':'success','evidence':'fixture','data_commit':baseline}))
        (self.repo/'out').mkdir()
        status=self.repo/'out/build-status.json';status.write_text(json.dumps({'build:release':{'exit':0,'output':'fixture built'}}))
        argv=['runner','--repo',str(self.repo),'--out',str(self.repo/'out/checks.txt'),'--base',tip,'--build-status',str(status)]
        with patch.object(sys,'argv',argv), patch.object(self.runner,'check_environment',return_value=dict(os.environ)), patch.object(self.runner,'run_script',return_value=(0,'passed',0)), patch.object(self.runner,'run_load_parallel',return_value=(0,'loaded',0)) as load:
            self.assertEqual(self.runner.main(),0)
        self.assertEqual([call.args[3] for call in load.call_args_list],[['levels/campaign/Mossgate.level'],['levels/campaign/Other.level']])
        manifest=json.loads((self.repo/'out/checks.deployment-selection.json').read_text())
        self.assertEqual(manifest['base'],baseline)
        self.assertEqual(manifest['tip'],tip)

    # Missing game prerequisites become required failures, never missing final results or fake passes.
    def test_missing_executable_is_explicit(self):
        (self.repo/'build/windows/opendungeons-plus.exe').unlink()
        subprocess.run(['git','-C',str(self.repo),'add','-u'],check=True)
        subprocess.run(['git','-C',str(self.repo),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','no executable'],check=True)
        self.head=events.git(self.repo,'rev-parse','HEAD');os.environ['HQ_CHECK_COMMIT']=self.head
        (self.repo/'out').mkdir()
        with patch.object(sys,'argv',['runner','--repo',str(self.repo),'--out',str(self.repo/'out/checks.txt'),'--base',self.head]), \
             patch.object(self.runner,'check_environment',return_value=dict(os.environ)), \
             patch.object(self.runner,'run_script',return_value=(0,'static pass',0)),patch.object(self.runner,'run_load_parallel') as load:
            self.assertEqual(self.runner.main(),1)
            load.assert_not_called()
        final={r['check']:r for r in self.rows() if r['event']=='result' and r['final']}
        self.assertEqual(final['load:levels/campaign/Mossgate.level']['exit'],125)
        self.assertIn('missing',Path(final['load:levels/campaign/Mossgate.level']['output_path']).read_text())

# Run the real PowerShell Build controller with fixture configure/compiler commands only.
class BuildControllerTests(unittest.TestCase):
    # Failed configure/build still produce a complete suite with isolated deployment dependencies and all independent check results.
    @unittest.skipUnless(shutil.which('powershell'),'Windows Build controller')
    def test_failed_build_drains_checks(self):
        """Require real base capture with complete isolated dependencies, preserve build failures, and drain independent checks."""
        for configure_code,build_code in ((13,125),(0,17)):
            with self.subTest(configure=configure_code), tempfile.TemporaryDirectory() as temporary:
                repo=Path(temporary)
                for name in ['scripts/run-checks.py','scripts/run-checks-profiled.py','scripts/hq_check_events.py',
                             'scripts/owned_process.py','scripts/odp_deployment.py',
                             'scripts/run-campaign-load-tests.py','scripts/deploy-level-selection.py',
                             'scripts/win32/orchestrator-build.ps1']:
                    target=repo/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
                # This fixture supplies an empty compiler environment and never invokes a real compiler.
                runner=repo/'scripts/run-checks.py'
                runner.write_text(runner.read_text().replace('env = check_environment()', 'env = dict(os.environ)'))
                (repo/'scripts/win32/windows-paths.ps1').write_text('$taskCmakeExe = Join-Path $PSScriptRoot "fake-cmake.cmd"')
                (repo/'scripts/win32/fake-cmake.cmd').write_text('@echo fixture compiler output\n@exit /b 17\n')
                (repo/'scripts/win32/configure-windows-prereqs.ps1').write_text('param($BuildNumber)\nWrite-Output "fixture configure output"\nexit '+str(configure_code))
                (repo/'scripts/next-build-number.py').write_text('print(17)')
                (repo/'scripts/check-first.py').write_text('print("early fixture failure");raise SystemExit(9)')
                (repo/'scripts/check-second.py').write_text('print("later fixture check executed")')
                (repo/'levels/campaign').mkdir(parents=True)
                (repo/'levels/campaign/Mossgate.level').write_text('fixture')
                (repo/'levels/campaign/Campaign.cfg').write_text('[Level]\nFile=campaign/Mossgate.level\n')
                subprocess.run(['git','init','-q',str(repo)],check=True)
                subprocess.run(['git','-C',str(repo),'add','.'],check=True)
                subprocess.run(['git','-C',str(repo),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','fixture'],check=True)
                head=events.git(repo,'rev-parse','HEAD');journal=repo/'events.jsonl'
                # Start from a child environment so a deferred release of the outer check run cannot leak into the fixture.
                env={**events.child_environment(os.environ),'HQ_CHECK_EVENTS':str(journal),'HQ_CHECK_RUN':'fixture-build','HQ_CHECK_COMMIT':head}
                result=subprocess.run(['powershell','-NoProfile','-File',str(repo/'scripts/win32/orchestrator-build.ps1'),
                                       '-Counter',str(repo/'counter.txt'),'-Base',head,'-Checks','unused-legacy-runner','-Worktree',str(repo)],
                                      cwd=repo,env=env,capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,1,result.stdout+result.stderr)
                self.assertTrue(journal.is_file(),result.stdout+result.stderr)
                rows=[json.loads(line) for line in journal.read_text().splitlines()]
                final={r['check']:r for r in rows if r['event']=='result' and r['final']}
                self.assertEqual(set(final),set(rows[0]['checks']))
                self.assertEqual(final['build:preflight']['exit'],0,
                                 Path(final['build:preflight']['output_path']).read_text())
                captured=list((repo/'out').glob('load-base-*.json'))
                self.assertEqual(len(captured),1)
                self.assertEqual(json.loads(captured[0].read_text()),{'base':head,'tip':head})
                self.assertEqual(final['build:configure']['exit'],configure_code)
                self.assertEqual(final['build:release']['exit'],build_code)
                self.assertEqual(final['scripts/check-first.py']['exit'],9)
                self.assertEqual(final['scripts/check-second.py']['exit'],0)
                self.assertEqual(final['load:levels/campaign/Mossgate.level']['exit'],125)
                self.assertEqual(final['deploy-readiness']['exit'],125)
                self.assertIn('fixture configure output',Path(final['build:configure']['output_path']).read_text())
                self.assertEqual(rows[-1]['event'],'shared_writes_finished')

# Verify a targeted similarity request is represented once with its changed-map arguments.
class SimilarityTests(unittest.TestCase):
    setUp = RunnerTests.setUp
    rows = JournalTests.rows

    # A changed map must not create duplicate required IDs or a second unparameterized probe.
    def test_targeted_similarity_once(self):
        level=self.repo/'levels/campaign/Mossgate.level'
        level.write_text('changed fixture')
        subprocess.run(['git','-C',str(self.repo),'add',str(level)],check=True)
        subprocess.run(['git','-C',str(self.repo),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','map changed'],check=True)
        os.environ['HQ_CHECK_COMMIT']=events.git(self.repo,'rev-parse','HEAD')
        (self.repo/'out').mkdir()
        argv=['runner','--repo',str(self.repo),'--out',str(self.repo/'out/checks.txt'),'--base',self.head,'--only','scripts/check-level-similarity.py']
        with patch.object(sys,'argv',argv), patch.object(self.runner,'check_environment',return_value=dict(os.environ)), patch.object(self.runner,'run_script',return_value=(0,'similarity verified',0)) as run:
            self.assertEqual(self.runner.main(),0)
        self.assertEqual(run.call_count,1)
        self.assertEqual(run.call_args.args[2],['levels/campaign/Mossgate.level'])

# Real child-process checks cover timeout cleanup and aggregate deployment failure.
class ProcessTests(unittest.TestCase):
    # Parent success must not hide an owned descendant that never exits.
    @unittest.skipUnless(os.name=='nt','Windows job objects')
    def test_owned_descendant_timeout(self):
        from owned_process import OwnedProcess
        wait = 'import ctypes; k=ctypes.windll.kernel32; e=k.CreateEventW(None,True,False,None); k.WaitForSingleObject(e,0xffffffff)'
        parent = 'import subprocess,sys; p=subprocess.Popen([sys.executable,"-c",'+repr(wait)+'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); print(p.pid,flush=True)'
        child=OwnedProcess([sys.executable,'-c',parent],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        code,output=child.collect(0.5)
        self.assertEqual(code,124)
        self.assertIn('owned process exit=0',output)
        self.assertIn('all descendants reaped',output)

    # A failing delivery returns its real code, complete output and no successful delivery result.
    def test_partial_delivery_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo=Path(temporary)
            subprocess.run(['git','init','-q',str(repo)],check=True)
            (repo/'source.txt').write_text('unchanged')
            subprocess.run(['git','-C',str(repo),'add','.'],check=True)
            subprocess.run(['git','-C',str(repo),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','fixture'],check=True)
            head=events.git(repo,'rev-parse','HEAD');journal=repo/'events.jsonl'
            # Start from a child environment so a deferred release of the outer check run cannot leak into the fixture.
            env={**events.child_environment(os.environ),'HQ_CHECK_EVENTS':str(journal),'HQ_CHECK_RUN':'delivery','HQ_CHECK_COMMIT':head}
            command=[sys.executable,str(ROOT/'scripts/hq-check-command.py'),'--repo',str(repo),'--name','deploy-delivery','--',
                     sys.executable,'-c','print("partial copy happened; verification failed");raise SystemExit(7)']
            result=subprocess.run(command,env=env,capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,7,result.stdout+result.stderr)
            rows=[json.loads(line) for line in journal.read_text().splitlines()]
            final=[r for r in rows if r.get('check')=='deploy-delivery']
            self.assertEqual(len(final),1)
            self.assertEqual(final[0]['exit'],7)
            self.assertTrue(final[0]['final'])
            self.assertIn('verification failed',Path(final[0]['output_path']).read_text())

# Exercise output streaming across the protocol adapter, using an observable fixture gate.
class StreamingTests(unittest.TestCase):
    # The first line must arrive before the child is allowed to finish.
    def test_adapter_keeps_live_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo=Path(temporary)
            subprocess.run(['git','init','-q',str(repo)],check=True)
            (repo/'source.txt').write_text('frozen')
            subprocess.run(['git','-C',str(repo),'add','.'],check=True)
            subprocess.run(['git','-C',str(repo),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','fixture'],check=True)
            head=events.git(repo,'rev-parse','HEAD');gate=repo/'gate'
            # Start from a child environment so a deferred release of the outer check run cannot leak into the fixture.
            env={**events.child_environment(os.environ),'HQ_CHECK_EVENTS':str(repo/'events.jsonl'),'HQ_CHECK_RUN':'stream','HQ_CHECK_COMMIT':head}
            producer='import pathlib,sys,time; p=pathlib.Path(sys.argv[1]); print("ready",flush=True); deadline=time.monotonic()+5\nwhile not p.exists() and time.monotonic()<deadline: time.sleep(.01)\nraise SystemExit(0 if p.exists() else 9)'
            proc=subprocess.Popen([sys.executable,str(ROOT/'scripts/hq-check-command.py'),'--repo',str(repo),'--name','compile-check','--',
                                   sys.executable,'-c',producer,str(gate)],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            try:
                self.assertEqual(proc.stdout.readline().strip(),'ready')
                gate.touch()
                output=proc.communicate(timeout=10)[0]
                self.assertEqual(proc.returncode,0,output)
            finally:
                if proc.poll() is None:
                    proc.kill()
                proc.communicate()

if __name__ == '__main__':
    unittest.main()
