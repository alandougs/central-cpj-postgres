$env:PYTHONIOENCODING="utf-8"
python "C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\pdf-autos-policiais\scripts\diagnostico.py" "C:\CPJ - TRABALHO\casos\OS-2628-2026\00-originais\LivroInquerito2162641_2026 (6).pdf"
python "C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\pdf-autos-policiais\scripts\extrair.py" "C:\CPJ - TRABALHO\casos\OS-2628-2026\00-originais\LivroInquerito2162641_2026 (6).pdf"
python "C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\pdf-autos-policiais\scripts\tabelas.py" "C:\CPJ - TRABALHO\casos\OS-2628-2026\01-extracao\LivroInquerito2162641_2026 (6)"
python "C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\pdf-autos-policiais\scripts\entidades.py" "C:\CPJ - TRABALHO\casos\OS-2628-2026\01-extracao\LivroInquerito2162641_2026 (6)"
python "C:\CPJ - TRABALHO\plugin\investigacao-cpj\skills\base-cpj\scripts\caso.py" status OS-2628-2026 extraido
