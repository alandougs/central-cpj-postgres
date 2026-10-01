$env:PYTHONIOENCODING="utf-8"
python "C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\pdf-autos-policiais\scripts\extrair.py" "C:\CPJ - TRABALHO\casos\OS-2699-2026\00-originais\LivroInquerito2160576_2026 (3).pdf" --saida "C:\CPJ - TRABALHO\casos\OS-2699-2026\01-extracao\LivroInquerito2160576_2026 (3)"
python "C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\pdf-autos-policiais\scripts\tabelas.py" "C:\CPJ - TRABALHO\casos\OS-2699-2026\01-extracao\LivroInquerito2160576_2026 (3)\transcricao.md"
python "C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\pdf-autos-policiais\scripts\entidades.py" "C:\CPJ - TRABALHO\casos\OS-2699-2026\01-extracao\LivroInquerito2160576_2026 (3)\transcricao.md"
python "C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\base-cpj\scripts\caso.py" status OS-2699-2026 extraido
