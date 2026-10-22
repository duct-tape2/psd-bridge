import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'PSDBridge'
DEFAULT_OUTPUT = Path.home() / 'Documents' / 'PSD Bridge' / '작업본'


def engine_dir():
    return ROOT / 'vendor' / 'photocraft'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, path)


def safe_name(name):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', name).strip(' .')[:80] or '작업'
    if name.upper().split('.')[0] in {'CON', 'PRN', 'AUX', 'NUL', *('COM'+str(i) for i in range(1,10)), *('LPT'+str(i) for i in range(1,10))}:
        name = '_' + name
    return name
