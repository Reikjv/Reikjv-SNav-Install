"""Installer control-flow tests with simulated Docker/network, not hardware tests.

Run: python -m unittest discover -s tests -v
On Windows set BASH_EXE to the Git for Windows bash.exe path.
"""
import hashlib
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = os.environ.get('BASH_EXE') or shutil.which('bash')


def posix(path):
    value = str(path).replace('\\', '/')
    return '/' + value[0].lower() + value[2:] if len(value) > 1 and value[1] == ':' else value


DOCKER = r'''#!/usr/bin/env bash
set -eu
echo "$*" >> "$MOCK_ROOT/events"
if [[ "$1" == version ]]; then echo "${MOCK_ARCH:-arm}"; exit; fi
if [[ "$1" == container ]]; then test -d "$MOCK_ROOT/$3"; exit; fi
if [[ "$1" == image ]]; then echo arm; exit; fi
if [[ "$1" == inspect ]]; then
  obj="${@: -1}"
  test -d "$MOCK_ROOT/$obj" || exit 1
  case "$3" in
    *managed*) echo "${MOCK_MANAGED:-true}" ;;
    *install*) cat "$MOCK_ROOT/$obj/install" ;;
    *Running*) cat "$MOCK_ROOT/$obj/running" ;;
  esac
  exit
fi
if [[ "$1" == load ]]; then exit; fi
if [[ "$1" == stop ]]; then echo false > "$MOCK_ROOT/$2/running"; exit; fi
if [[ "$1" == rename ]]; then mv "$MOCK_ROOT/$2" "$MOCK_ROOT/$3"; exit; fi
if [[ "$1" == start ]]; then echo true > "$MOCK_ROOT/$2/running"; exit; fi
if [[ "$1" == rm ]]; then rm -r "$MOCK_ROOT/${@: -1}"; exit; fi
if [[ "$1" == logs ]]; then exit; fi
if [[ "$1" == exec ]]; then exit "${MOCK_HEALTH_ERROR:-0}"; fi
if [[ "$1" == run && "$2" == --rm ]]; then exit "${MOCK_GUARD_ERROR:-0}"; fi
if [[ "$1" == run ]]; then
  mkdir "$MOCK_ROOT/reikjv-snav"
  echo true > "$MOCK_ROOT/reikjv-snav/running"
  for arg in "$@"; do
    if [[ "$arg" == org.reikjv.snav.install=* ]]; then echo "${arg#*=}" > "$MOCK_ROOT/reikjv-snav/install"; fi
  done
  printf '%s\n' "$@" > "$MOCK_ROOT/run-args"
  exit
fi
echo "Unexpected Docker command: $*" >&2
exit 99
'''


@unittest.skipUnless(BASH, 'Bash is required')
class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.archive = self.root / 'image.tar.gz'
        self.archive.write_bytes(b'verified test image')
        self.wrapper('docker', DOCKER)
        self.wrapper('flock', '#!/usr/bin/env bash\nexit 0\n')
        self.wrapper('sleep', '#!/usr/bin/env bash\nexit 0\n')
        self.wrapper('python3', '#!/usr/bin/env bash\ncat >/dev/null\nexit "${MOCK_PORT_ERROR:-0}"\n')
        self.wrapper('curl', '#!/usr/bin/env bash\ncp "$MOCK_ARCHIVE" "${@: -1}"\n')
        script = (ROOT / 'install.sh').read_text(encoding='utf-8')
        script = script.replace('[[ $EUID == 0 ]]', '[[ 0 == 0 ]]')
        script = script.replace('/usr/blueos/extensions/reikjv-snav', posix(self.root / 'data'))
        script = script.replace('/var/cache/reikjv-snav', posix(self.root / 'cache'))
        script = script.replace('/var/lock/reikjv-snav-install.lock', posix(self.root / 'install.lock'))
        script, count = re.subn(r'(?m)^SHA256="[0-9a-f]{64}"$',
                                f'SHA256="{hashlib.sha256(self.archive.read_bytes()).hexdigest()}"', script)
        self.assertEqual(count, 1)
        self.script = self.root / 'install.sh'
        self.script.write_text(script, encoding='utf-8', newline='\n')

    def wrapper(self, name, content):
        path = self.bin / name
        path.write_text(content, encoding='utf-8', newline='\n')
        path.chmod(0o755)

    def existing(self):
        old = self.root / 'reikjv-snav'
        old.mkdir()
        (old / 'install').write_text('previous')
        (old / 'running').write_text('true')

    def run_installer(self, online=False, **extra):
        env = dict(os.environ, MOCK_ROOT=posix(self.root), MOCK_ARCHIVE=posix(self.archive), MOCK_BIN=posix(self.bin))
        env.update(extra)
        args = [BASH, '-c', 'export PATH="$MOCK_BIN:$PATH"; exec bash "$@"', 'test', posix(self.script)]
        if not online:
            args += ['--archive', posix(self.archive)]
        result = subprocess.run(args, env=env, capture_output=True, text=True, timeout=30)
        self.output = result.stdout + result.stderr
        return result.returncode

    def test_online_install_and_port(self):
        self.assertEqual(self.run_installer(online=True), 0, self.output)
        self.assertIn('--port\n8099', (self.root / 'run-args').read_text())
        self.assertIn('Instalacao concluida', self.output)

    def test_wrong_architecture(self):
        self.assertNotEqual(self.run_installer(MOCK_ARCH='arm64'), 0)
        self.assertFalse((self.root / 'reikjv-snav').exists())

    def test_corrupt_archive(self):
        self.archive.write_bytes(b'corrupted')
        self.assertNotEqual(self.run_installer(), 0)
        self.assertIn('Checksum', self.output)
        self.assertNotIn('load -i', (self.root / 'events').read_text())

    def test_guard_preserves_existing_container(self):
        self.existing()
        self.assertNotEqual(self.run_installer(MOCK_GUARD_ERROR='1'), 0)
        self.assertEqual((self.root / 'reikjv-snav/install').read_text().strip(), 'previous')
        self.assertNotIn('stop reikjv-snav', (self.root / 'events').read_text())

    def test_unmanaged_container(self):
        self.existing()
        self.assertNotEqual(self.run_installer(MOCK_MANAGED='false'), 0)
        self.assertNotIn('stop reikjv-snav', (self.root / 'events').read_text())

    def test_update_preserves_backup(self):
        self.existing()
        self.assertEqual(self.run_installer(), 0, self.output)
        backup, = self.root.glob('reikjv-snav-backup-*')
        self.assertEqual((backup / 'install').read_text().strip(), 'previous')
        self.assertEqual((backup / 'running').read_text().strip(), 'false')

    def test_health_failure_rolls_back(self):
        self.existing()
        self.assertNotEqual(self.run_installer(MOCK_HEALTH_ERROR='1'), 0)
        self.assertEqual((self.root / 'reikjv-snav/install').read_text().strip(), 'previous')
        self.assertEqual((self.root / 'reikjv-snav/running').read_text().strip(), 'true')

    def test_port_conflict_rolls_back(self):
        self.existing()
        self.assertNotEqual(self.run_installer(MOCK_PORT_ERROR='1'), 0)
        self.assertEqual((self.root / 'reikjv-snav/install').read_text().strip(), 'previous')
        self.assertEqual((self.root / 'reikjv-snav/running').read_text().strip(), 'true')


if __name__ == '__main__':
    unittest.main()
