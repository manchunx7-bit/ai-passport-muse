"""Fail closed if a tracked file exceeds this application's reviewed allowlist."""
from pathlib import Path
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
scope = json.loads((ROOT / 'PUBLIC_FILES.json').read_text(encoding='utf-8'))
files = set(filter(None, subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '-z']).decode().split('\0')))
assert files == set(scope['files']) | {'PUBLIC_FILES.json'}, 'Update/review the explicit public file allowlist'
app = scope['application']
allowed_device = ('device/main/apps/voice/', 'device/tests/') if app == 'voice' else (
    'device/main/apps/muse/', 'device/components/passport_muse/', 'device/components/noise_core/', 'device/tests/')
for name in sorted(files):
    p = ROOT / name
    assert p.is_file() and not p.is_symlink(), name
    assert not (name.startswith('device/') and not name.startswith(allowed_device)), name
    assert not name.startswith(('firmware/', 'source/', 'backups/', 'dist/', 'build/')), name
    assert p.suffix.lower() not in {'.bin', '.exe', '.elf', '.map', '.zip', '.log', '.pyc'}, name
    assert p.name not in {'sdkconfig', 'sdkconfig.old', 'voice-config.json', 'muse_avatar_frames.c'}, name
    text = p.read_text(encoding='utf-8-sig')
    if name != 'tools/check_scope.py':
        assert not re.search(r'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|mgst_[A-Za-z0-9_-]{24,}|192\.168\.5\.4|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', text), name
        assert 'Generated from official Jollybot artwork' not in text, name
    if p.suffix == '.md':
        for target in re.findall(r'\]\(([^)]+)\)', text):
            if '://' in target or target.startswith(('#', 'mailto:')):
                continue
            local = target.split('#')[0]
            assert not local or (p.parent / local).exists(), (name, target)
print(f'PASS: {app} application-only allowlist, no firmware/binaries/secrets, document links')
