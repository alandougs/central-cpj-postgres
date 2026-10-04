"""Regressões L05 em PDF fictício: checkpoint, Markdown e CSV de tabela visual."""
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

RAIZ=Path(__file__).resolve().parents[2]; EXTRAIR=RAIZ/"skills"/"pdf-autos-policiais"/"scripts"/"extrair.py"; TABELAS=EXTRAIR.parent/"tabelas.py"
class Extracao(unittest.TestCase):
 def test_checkpoint_e_tabela_visual(self):
  with tempfile.TemporaryDirectory(prefix="cpj-ocr-ficticio-") as d:
   pdf=Path(d)/"ficticio.pdf"; c=Canvas(str(pdf),pagesize=A4); c.drawString(70,750,"DOCUMENTO FICTICIO pagina um com texto suficiente para extracao local."); c.showPage(); c.showPage(); c.save()
   saida=Path(d)/"saida"; tv=saida/"transcricoes_visuais"; tv.mkdir(parents=True); (tv/"p0002.md").write_text("| data | valor |\n|---|---|\n| 01/01/2099 | R$ 10,00 |",encoding="utf-8")
   cmd=[sys.executable,str(EXTRAIR),str(pdf),"--saida",str(saida),"--ocr","visao"]
   subprocess.run(cmd,check=True,capture_output=True,text=True,errors="replace"); rel=json.loads((saida/"relatorio_extracao.json").read_text(encoding="utf-8"))
   self.assertEqual(rel["metodos"],{"texto-nativo":1,"transcricao-visual-llm":1}); self.assertEqual(rel["checkpoints_reutilizados"],0)
   subprocess.run(cmd,check=True,capture_output=True,text=True,errors="replace"); rel=json.loads((saida/"relatorio_extracao.json").read_text(encoding="utf-8")); self.assertEqual(rel["checkpoints_reutilizados"],2)
   subprocess.run([sys.executable,str(TABELAS),str(saida/"transcricao.md"),"--saida",str(saida)],check=True,capture_output=True,text=True,errors="replace")
   self.assertIn("01/01/2099",next((saida/"tabelas").glob("t*.csv")).read_text(encoding="utf-8-sig"))
   (tv/"p0002.md").write_text("CORREÇÃO VISUAL FICTÍCIA ATUALIZADA",encoding="utf-8")
   subprocess.run(cmd,check=True,capture_output=True,text=True,errors="replace")
   rel=json.loads((saida/"relatorio_extracao.json").read_text(encoding="utf-8"))
   self.assertEqual(rel["checkpoints_reutilizados"],1)
   self.assertIn("CORREÇÃO VISUAL FICTÍCIA ATUALIZADA",(saida/"transcricao.md").read_text(encoding="utf-8"))
   (tv/"p0002.md").unlink()
   subprocess.run(cmd,check=True,capture_output=True,text=True,errors="replace")
   rel=json.loads((saida/"relatorio_extracao.json").read_text(encoding="utf-8"))
   self.assertEqual(rel["pendentes_transcricao_visual"],[2])
   self.assertNotIn("CORREÇÃO VISUAL FICTÍCIA ATUALIZADA",(saida/"transcricao.md").read_text(encoding="utf-8"))
if __name__=="__main__": unittest.main(verbosity=2)
