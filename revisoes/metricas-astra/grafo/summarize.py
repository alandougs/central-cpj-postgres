"""Summarize raw synthetic runs without rewriting them."""
from pathlib import Path
import json
import hashlib
import platform
import os
import gzip

HERE = Path(__file__).resolve().parent


def load(label):
    path = HERE / f'results-{label}.json'
    result = json.loads(path.read_bytes() if path.exists() else gzip.decompress(path.with_suffix('.json.gz').read_bytes()))
    assert len(result['graph']) == 40, label
    assert len(result['summary']) == 8, label
    assert not result.get('errors') and not result.get('externalRequests') and not result.get('fatal'), label
    assert all(not s['timedOut'] for s in result['graph']), label
    for s in result['graph']:
        assert s['nodeCount'] == s['visibleNodeCount'] == s['nodes'], (label, s['nodes'])
        assert s['edgeCount'] == s['visibleEdgeCount'] == s['nodes'] * s['density'], (label, s['nodes'])
        if label.startswith('paired-') or label == 'all-labels':
            assert s['projectedNodeCount'] == s['nodes']
            assert s['projectedEdgeCount'] == s['nodes'] * s['density']
    return result


before, after = load('paired-before'), load('paired-after')
assert before['browser'] == after['browser']
assert {(s['canvas']['width'], s['canvas']['height']) for s in before['graph']} == {(s['canvas']['width'], s['canvas']['height']) for s in after['graph']}
rows = []
for a, b in zip(before['summary'], after['summary']):
    assert (a['nodes'], a['density']) == (b['nodes'], b['density'])
    row = {'nodes': a['nodes'], 'edges': a['nodes'] * a['density']}
    for key in ('mountMs', 'physicsMs', 'drawMs', 'liveFrameIntervalMs', 'liveDurationMs', 'cdpHeapUsedBytes', 'cdpTaskDurationSeconds'):
        row[key] = {'before': a[key], 'after': b[key]}
    row['tickIntervalDerivedFps'] = {'before': a['medianFps'], 'after': b['medianFps']}
    row['afterStates'] = {state: sum(s['layoutState'] == state for s in after['graph'] if s['nodes'] == a['nodes'] and s['density'] == a['density'])
                          for state in sorted({s['layoutState'] for s in after['graph']})}
    rows.append(row)
out = {'schema': 'astra-graph-comparison/1', 'browser': before['browser'],
       'environment': {'platform': platform.platform(), 'processor': platform.processor(), 'cpuCount': os.cpu_count()},
       'runs': {label: {'started': result['started'], 'finished': result['finished'], 'inputSha256': result['sha256']}
                for label, result in [('paired-before', before), ('paired-after', after)]},
       'sourceHashes': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob('*.cjs'))},
       'rows': rows}
for label in ('all-labels', 'grouped'):
    if (HERE / f'results-{label}.json').exists() or (HERE / f'results-{label}.json.gz').exists():
        result = load(label)
        out[label] = {'microOnly': True, 'summary': result['summary'],
                      'projectedCounts': [{'nodes': s['nodes'], 'edges': s['edgeCount'],
                                           'projectedNodes': s['projectedNodeCount'], 'projectedEdges': s['projectedEdgeCount']}
                                          for s in result['graph']]}
(HERE / 'comparison.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
print('| Nós/arestas | Montagem p50 antes→depois | Física p95 | Desenho p95 | Intervalo tick p95 | FPS derivada p50 |')
print('|---|---:|---:|---:|---:|---:|')
for r in rows:
    def pair(key, quantile):
        return f"{r[key]['before'][quantile]:.2f} → {r[key]['after'][quantile]:.2f}"
    fps = r['tickIntervalDerivedFps']
    print(f"| {r['nodes']}/{r['edges']} | {pair('mountMs','p50')} | {pair('physicsMs','p95')} | {pair('drawMs','p95')} | {pair('liveFrameIntervalMs','p95')} | {fps['before']:.1f} → {fps['after']:.1f} |")
