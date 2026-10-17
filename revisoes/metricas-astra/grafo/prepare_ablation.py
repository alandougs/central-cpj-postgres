"""Prepare separate 3-warmup/20-call ablations. Does not run measurements."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
s = (HERE / 'benchmark-expanded.cjs').read_text(encoding='utf-8')
start = s.index('   grStartLoop=start;grEnergy=1;grAjustarAoEstabilizar=false;')
end = s.index('   grTickPhysics=tick;grDesenhar=drawOriginal;', start)
s = s[:start] + '   const liveDuration=0,timedOut=false;\n' + s[end:]
s = s.replace("result.adapter={version:1,", "result.adapter={microOnly:true,version:1,")
s = s.replace("medianFps:1000/quant(rows.flatMap(x=>x.frameIntervalsMs),.5)", 'medianFps:null')
(HERE / 'benchmark-ablation.cjs').write_text(s, encoding='utf-8')
print('Prepared benchmark-ablation.cjs; no animation/FPS claim in separate ablations.')
