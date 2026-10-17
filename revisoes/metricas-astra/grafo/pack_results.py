"""Lossless deterministic packaging, only generated synthetic JSON/HTML here."""
from pathlib import Path
import gzip
import hashlib
import json
import os

HERE = Path(__file__).resolve().parent
if (HERE / 'package-manifest.json').exists():
    raise SystemExit('Package already exists; preserve its manifest and frozen measurements.')
BACKUP = Path(os.environ['TEMP']) / 'cpj-astra-ast13-raw-20261014'
BACKUP.mkdir(parents=True, exist_ok=True)
manifest = {'schema': 'astra-measurements-package/1', 'gzipMtime': 0, 'rawBackup': str(BACKUP), 'files': {}}
files = sorted(HERE.glob('results-*.json')) + [HERE / 'historical-results.json'] + sorted((HERE / 'snapshots').glob('*.html'))
for p in files:
    if not p.is_file():
        continue
    assert p.resolve().is_relative_to(HERE)
    relative = p.relative_to(HERE)
    raw = p.read_bytes()
    packed = gzip.compress(raw, compresslevel=9, mtime=0)
    assert gzip.decompress(packed) == raw
    backup = BACKUP / relative
    backup.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists() and backup.read_bytes() != raw:
        raise SystemExit('Backup with different bytes already exists: ' + str(backup))
    backup.write_bytes(raw)
    assert backup.read_bytes() == raw
    gz = p.with_suffix(p.suffix + '.gz')
    gz.write_bytes(packed)
    manifest['files'][relative.as_posix()] = {'sha256': hashlib.sha256(raw).hexdigest(),
        'gzipSha256': hashlib.sha256(packed).hexdigest(), 'bytes': len(raw), 'gzipBytes': len(packed)}
    p.unlink()  # Exact original preserved and verified in dedicated TEMP above.
(HERE / 'package-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(json.dumps({'files': len(manifest['files']), 'rawBackup': str(BACKUP),
                  'rawBytes': sum(x['bytes'] for x in manifest['files'].values()),
                  'gzipBytes': sum(x['gzipBytes'] for x in manifest['files'].values())}))
