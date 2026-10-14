"""Extract exact frozen fixtures/raw JSON and copy runners into fresh TEMP."""
from pathlib import Path
import gzip
import hashlib
import json
import shutil
import tempfile

HERE = Path(__file__).resolve().parent
target = Path(tempfile.mkdtemp(prefix='cpj-astra-reproduce-'))
manifest = json.loads((HERE / 'package-manifest.json').read_text(encoding='utf-8'))
for name, expected in manifest['files'].items():
    destination = (target / name).resolve()
    assert destination.is_relative_to(target)
    compressed = (HERE / (name + '.gz')).read_bytes()
    assert hashlib.sha256(compressed).hexdigest() == expected['gzipSha256']
    raw = gzip.decompress(compressed)
    assert hashlib.sha256(raw).hexdigest() == expected['sha256']
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
for p in HERE.glob('benchmark*.cjs'):
    shutil.copyfile(p, target / p.name)
print(str(target))
