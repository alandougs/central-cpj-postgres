import os
import subprocess
import glob

def process_case(caso_id):
    base_dir = r"E:\CPJ - TRABALHO"
    os.chdir(base_dir)

    os.environ["PATH"] += r";C:\Program Files\Tesseract-OCR;C:\Program Files\PDF24\tesseract"
    tessdata_path = os.path.abspath(r"ferramentas\tessdata")
    if os.path.exists(tessdata_path):
        os.environ["TESSDATA_PREFIX"] = tessdata_path
    else:
        print("Tessdata not found at", tessdata_path)

    originais = glob.glob(f"casos/{caso_id}/00-originais/*.pdf")
    if not originais:
        print(f"No PDFs found for {caso_id}")
        return
    pdf = originais[0]
    filename = os.path.splitext(os.path.basename(pdf))[0]
    out_dir = f"casos/{caso_id}/01-extracao/{filename}"
    os.makedirs(out_dir, exist_ok=True)

    scripts_dir = r"plugin\investigacao-cpj\skills\pdf-autos-policiais\scripts"

    print("Running diagnostico...")
    subprocess.run(["python", os.path.join(scripts_dir, "diagnostico.py"), pdf])

    print("Running extrair...")
    subprocess.run(["python", os.path.join(scripts_dir, "extrair.py"), pdf, "--saida", out_dir, "--lang", "por"])

    print("Running tabelas (pdf)...")
    subprocess.run(["python", os.path.join(scripts_dir, "tabelas.py"), pdf, "--saida", out_dir])

    md_path = os.path.join(out_dir, "transcricao.md")
    if os.path.exists(md_path):
        print("Running tabelas (md)...")
        subprocess.run(["python", os.path.join(scripts_dir, "tabelas.py"), md_path, "--saida", out_dir])

        print("Running entidades...")
        subprocess.run(["python", os.path.join(scripts_dir, "entidades.py"), md_path])
    
    report_path = os.path.join(out_dir, "relatorio_extracao.json")
    if os.path.exists(report_path):
        print("Running caso.py ip...")
        subprocess.run(["python", r"plugin\investigacao-cpj\skills\base-cpj\scripts\caso.py", "ip", caso_id, report_path])

    print("Running indexar.py...")
    subprocess.run(["python", r"plugin\investigacao-cpj\skills\base-cpj\scripts\indexar.py"])

    print(f"Done processing {caso_id}!")

if __name__ == '__main__':
    process_case("OS-2672-2026")
