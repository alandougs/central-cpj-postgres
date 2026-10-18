"""Materialize only. Does NOT execute the benchmark or write after results.

Usage: python prepare_benchmark.py STATIC_DIRECTORY OUTPUT_HTML
Legacy standalone HTML is also accepted. Read only source assets, no backend.
"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import re,json,hashlib,sys
HERE=Path(__file__).resolve().parent
BASELINE=HERE
hashes={}
def sha(data):return hashlib.sha256(data).hexdigest()
if len(sys.argv)>2:
    source=Path(sys.argv[1]).resolve();target=Path(sys.argv[2]).resolve()
    if not target.is_relative_to(HERE):raise SystemExit('Output must remain inside reserved metrics directory')
    index=source/'index.html' if source.is_dir() else source
    html=index.read_text(encoding='utf-8');hashes[str(index)]=sha(index.read_bytes())
    class Attrs(HTMLParser):
        def __init__(self,tag):super().__init__();self.attrs={};self.feed(tag)
        def handle_starttag(self,tag,attrs):self.attrs=dict(attrs)
    def load(url):
        part=urlsplit(url);path=unquote(part.path)
        if part.scheme or part.netloc or not path.startswith('/static/'):raise ValueError('Nonlocal source: '+url)
        relative=path[len('/static/'):]
        if '\\' in relative or any(p in ('','.','..') for p in relative.split('/')):raise ValueError('Unsafe source')
        item=(index.parent/relative).resolve()
        if not item.is_relative_to(index.parent):raise ValueError('Outside static')
        data=item.read_bytes();hashes[url]=sha(data);return data.decode('utf-8')
    def script(m):
        a=Attrs(m[1]).attrs
        if 'src' not in a:return m[0]
        if any(k in a for k in ('async','defer')) or a.get('type')=='module':raise ValueError('Changed script execution order')
        return '<script>'+load(a['src'])+'</script>'
    def style(m):
        a=Attrs(m[0]).attrs
        return '<style>'+load(a['href'])+'</style>' if 'stylesheet' in a.get('rel','').split() else m[0]
    html=re.sub(r'(<script\b[^>]*>)(.*?)</script>',script,html,flags=re.S|re.I)
    html=re.sub(r'<link\b[^>]*>',style,html,flags=re.I)
    if len(re.findall(r'iniciar\(\);\s*</script>',html))!=1:raise ValueError('Bootstrap must be uniquely neutralized by original harness')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(html,encoding='utf-8')
    (target.with_suffix('.sources.json')).write_text(json.dumps({'source':str(source),'assets':hashes,'expanded_sha256':sha(html.encode())},indent=2),encoding='utf-8')

text=(BASELINE/'benchmark-original.cjs').read_text(encoding='utf-8')
text="// AST13 harness: execute only on frozen snapshots. Original baseline is intact.\nif(!process.argv.includes('--execute-frozen'))throw Error('Source/host release required; pass --execute-frozen explicitly');\n"+text
text=text.replace("const source=fs.readFileSync(input,'utf8');", "const runLabel=process.env.ASTRA_RUN_LABEL;if(!runLabel||!/^[a-z0-9-]+$/.test(runLabel))throw Error('Set a fresh ASTRA_RUN_LABEL');\nconst output=path.join(dir,'results-'+runLabel+'.json');if(fs.existsSync(output))throw Error('Never overwrite an existing result');\nconst source=fs.readFileSync(input,'utf8');")
text=text.replace("path.join(dir,'results.json')",'output')
text=text.replace("let fixture='idle';", "result.adapter={version:1,mode:process.env.ASTRA_GROUPED==='1'?'grouped-separate-ablation':'fully-expanded',labels:process.env.ASTRA_LABELS==='all'?'all':'adaptive',cache:'cleared per repetition; JIT context retained',originalHarnessSha256:'"+sha((BASELINE/'benchmark-original.cjs').read_bytes())+"'};\nlet fixture='idle';")
text=text.replace('const tick=grTickPhysics,draw=grDesenhar,start=grStartLoop;', '''const tick=grTickPhysics,drawOriginal=grDesenhar,start=grStartLoop;
   const full=window.__allLabels;
   const draw=()=>drawOriginal({detalheCompleto:full});
   grDesenhar=draw;
   if(typeof grAgrupar!=='undefined'){grAgrupar=window.__grouped;grExpandidos.clear();grProjecao=null}\n   if(typeof grVistas!=='undefined'){grVistas.clear();grPosicoes.clear();grVistaChave=null;grDominioChave=null;grNodes=[];grEdges=[];grSelectedNode=null;if(typeof grSelectedEdge!=='undefined')grSelectedEdge=null;grVisCache=null;grHitCache=null;grSimulando=false;grEnergy=1}''')
text=text.replace("const page=await context.newPage();page.on('pageerror'", "const page=await context.newPage();await page.addInitScript(options=>{window.__allLabels=options.labels;window.__grouped=options.grouped},{labels:process.env.ASTRA_LABELS==='all',grouped:process.env.ASTRA_GROUPED==='1'});page.on('pageerror'")
text=text.replace('grTickPhysics=tick;grDesenhar=draw;grStartLoop=start;', 'grTickPhysics=tick;grDesenhar=drawOriginal;grStartLoop=start;')
text=text.replace('return {mountMs:mount,physicsMs:physics,', "return {renderMode:typeof grAgrupar!=='undefined'&&grAgrupar?'grouped':'expanded',projectedNodeCount:typeof grProjetar==='undefined'?grNodes.length:grProjetar().nos.length,projectedEdgeCount:typeof grProjetar==='undefined'?grEdges.length:grProjetar().arestas.length,layoutState:typeof grLayoutEstado==='undefined'?'energy':grLayoutEstado,layoutTicks:typeof grTicks==='undefined'?null:grTicks,visibleNodeCount:grNodes.filter(n=>grCatAtiva(n.cat)).length,visibleEdgeCount:grEdges.filter(e=>grCatAtiva(e.source.cat)&&grCatAtiva(e.target.cat)).length,mountMs:mount,physicsMs:physics,")
start=text.index(' // Real ciclo scheduler');end=text.index(' const summaries=[];',start)
text=text[:start]+text[end:]
(HERE/'benchmark-expanded.cjs').write_text(text,encoding='utf-8')
print(json.dumps({'prepared':str(HERE/'benchmark-expanded.cjs'),'executed':False,'original_baseline_unchanged':True}))
