"""Exercise log streaming with a fake command; no compiler or build is started."""
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent / 'win32'


class LiveOutput(unittest.TestCase):
    """Both script pipelines must forward output before the command exits."""
    def test_build_and_check_pipelines(self):
        build = (ROOT / 'orchestrator-build.ps1').read_text()
        check = (ROOT / 'compile-check-changed.ps1').read_text()
        function = re.search(r'function Write-CheckLog.*?^}', check, re.M | re.S).group()
        pipelines = [line.split(' | ', 1)[1] for line in build.splitlines() if '*>&1 | ' in line]
        pipelines.append(next(line.split(' | ', 1)[1] for line in check.splitlines() if '& cmd /c' in line))
        self.assertEqual(len(pipelines), 3)
        for pipeline in pipelines:
            with self.subTest(pipeline=pipeline), tempfile.TemporaryDirectory() as folder:
                folder = pathlib.Path(folder)
                (folder / 'out').mkdir()
                producer = folder / 'producer.py'
                producer.write_text("import pathlib,sys,time\nprint('first',flush=True)\ngate=pathlib.Path(sys.argv[1])\nend=time.monotonic()+8\nwhile not gate.exists() and time.monotonic()<end: time.sleep(.02)\nprint('second',flush=True)\nsys.exit(7 if gate.exists() else 9)\n")
                gate = folder / 'gate'
                quote = lambda s: "'" + str(s).replace("'", "''") + "'"
                script = folder / 'probe.ps1'
                script.write_text("$ErrorActionPreference='Continue'\n$wt="+quote(folder)+"\n$run='test'\n$log="+quote(folder/'out/check.log')+"\n"+function+"\n& "+quote(sys.executable)+" "+quote(producer)+" "+quote(gate)+" 2>&1 | "+pipeline+"\nWrite-Output ('EXIT='+$LASTEXITCODE)\n")
                process = subprocess.Popen(['powershell','-NoProfile','-File',str(script)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                try:
                    first = process.stdout.readline().strip()
                    self.assertEqual(first, 'first')
                    gate.touch()
                    rest = process.communicate(timeout=12)[0]
                    self.assertIn('second', rest)
                    self.assertIn('EXIT=7', rest)
                    logs = list((folder/'out').glob('*.log'))
                    self.assertEqual(len(logs), 1)
                    data = logs[0].read_bytes()
                    content = data.decode('utf-16') if data.startswith(b'\xff\xfe') else data.decode('utf-8-sig')
                    self.assertIn('first', content)
                    self.assertIn('second', content)
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()


if __name__ == '__main__':
    unittest.main()
