"""Check synthetic AST172 artifacts without launching a browser or querying Windows."""
import collections
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    data = json.loads((ROOT / 'results-working-set-complete.json').read_text(encoding='utf-8'))
    assert not data.get('fatal') and data.get('finished')
    assert not data['errors'] and not data['externalRequests']
    complete = [r for r in data['samples'] if r['complete']]
    invalid = [r for r in data['samples'] if not r['complete']]
    expected = {(n, side, repeat) for n in (50, 100, 500, 1000)
                for side in ('before', 'after') for repeat in (1, 2, 3)}
    assert len(complete) == 24
    assert {(r['nodes'], r['side'], r['repeat']) for r in complete} == expected
    for row in data['samples']:
        assert row['density'] == 10
        assert row['mounted']['rafStopped']
        for key in ('nodeCount', 'visibleNodeCount', 'projectedNodeCount'):
            assert row['mounted'][key] == row['nodes']
        for key in ('edgeCount', 'visibleEdgeCount', 'projectedEdgeCount'):
            assert row['mounted'][key] == row['nodes'] * 10
        processes = row['processes']
        assert len({p['id'] for p in processes}) == len(processes)
        assert {'browser', 'renderer', 'GPU'} <= {p['type'] for p in processes}
        available = [p for p in processes if p['workingSetBytes'] is not None]
        assert all(type(p['workingSetBytes']) is int and p['workingSetBytes'] > 0 for p in available)
        assert row['sumWorkingSetBytes'] == sum(p['workingSetBytes'] for p in available)
        totals = collections.defaultdict(int)
        for p in available:
            totals[p['type']] += p['workingSetBytes']
        assert dict(totals) == row['workingSetBytesByType']
        assert row['complete'] == (len(available) == len(processes))
        assert row['missingPids'] == [p['id'] for p in processes if p['workingSetBytes'] is None]
    for entry in data['summary']:
        for side in ('before', 'after'):
            values = sorted(r['sumWorkingSetBytes'] for r in complete
                            if r['nodes'] == entry['nodes'] and r['side'] == side)
            assert len(values) == entry[side]['samples'] == 3
            assert values[1] == entry[side]['workingSetBytesP50']
            assert values[-1] == entry[side]['workingSetBytesP95']
    sources = {}
    for side, metadata in data['sources'].items():
        packed = (ROOT.parent / 'grafo' / 'snapshots' / (side + '.html.gz')).read_bytes()
        raw = gzip.decompress(packed)
        assert sha(packed) == metadata['gzipSha256']
        assert sha(raw) == metadata['sha256']
        sources[side] = metadata['sha256']
    print(json.dumps({'completeSamples': len(complete), 'invalidAttempts': len(invalid),
                      'missingTypes': [p['type'] for r in invalid for p in r['processes']
                                       if p['workingSetBytes'] is None],
                      'errors': len(data['errors']), 'externalRequests': len(data['externalRequests']),
                      'sourceSha256': sources, 'allOracles': 'passed'}, indent=2))


if __name__ == '__main__':
    main()
