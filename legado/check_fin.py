import os, json, re, glob
cases_dirs = [
    r'C:\CPJ - TRABALHO\casos\OS-2586-2026',
    r'C:\CPJ - TRABALHO\casos\OS-2623-2026',
    r'C:\CPJ - TRABALHO\casos\OS-2650-2026',
    r'C:\CPJ - TRABALHO\casos\OS-2668-2026',
    r'E:\CPJ - TRABALHO\casos\OS-2672-2026',
    r'C:\CPJ - TRABALHO\casos\OS-2705-2026',
    r'C:\CPJ - TRABALHO\casos\OS-2716-2026'
]

for d in cases_dirs:
    if not os.path.exists(d):
        continue
    caso_json_path = os.path.join(d, 'caso.json')
    if not os.path.exists(caso_json_path):
        continue
    with open(caso_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"\n--- {data['id']} ---")
    fin = data.get('financeiro', {})
    print(f"Prejuizo Declarado (caso.json): {fin.get('prejuizo_declarado')}")
    print(f"Prejuizo Documentado (caso.json): {fin.get('prejuizo_documentado')}")
    
    # find minuta
    minuta_files = glob.glob(os.path.join(d, '03-relatorios', 'minuta-*.md'))
    if not minuta_files:
        print("Minuta nao encontrada!")
    else:
        with open(minuta_files[-1], 'r', encoding='utf-8') as f:
            minuta_text = f.read()
        valores_minuta = re.findall(r'R\$\s*[\d\.,]+', minuta_text)
        print(f"Valores na minuta: {', '.join(set(valores_minuta))}")
        
    # find entidades.csv
    entidades_files = glob.glob(os.path.join(d, '01-extracao', '*', 'entidades.csv'))
    if entidades_files:
        with open(entidades_files[-1], 'r', encoding='utf-8') as f:
            entidades_text = f.read()
        valores_entidades = set(re.findall(r'R\$\s*[\d\.,]+', entidades_text))
        print(f"Valores em entidades.csv: {', '.join(valores_entidades)}")
    else:
        print("entidades.csv nao encontrado!")
