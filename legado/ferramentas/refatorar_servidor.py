import os
import re

servidor_path = 'plugin/investigacao-cpj/app/servidor.py'
with open(servidor_path, 'r', encoding='utf-8') as f:
    linhas = f.readlines()

def extrair_bloco(inicio_str, fim_str=None):
    dentro = False
    bloco = []
    resto = []
    for linha in linhas:
        if linha.startswith(inicio_str):
            dentro = True
        elif fim_str and linha.startswith(fim_str):
            dentro = False
        
        if dentro:
            bloco.append(linha)
        else:
            resto.append(linha)
    return "".join(bloco), resto

# Ler todo o conteúdo
txt = "".join(linhas)

def extrair_entre(texto, start_mark, end_mark=None):
    if end_mark:
        padrao = re.escape(start_mark) + r"(.*?)(?=" + re.escape(end_mark) + r")"
        m = re.search(padrao, texto, flags=re.DOTALL)
        if m:
            extraido = start_mark + m.group(1)
            novo_texto = texto[:m.start()] + texto[m.end():]
            return extraido, novo_texto
    else:
        padrao = re.escape(start_mark) + r"(.*)"
        m = re.search(padrao, texto, flags=re.DOTALL)
        if m:
            extraido = start_mark + m.group(1)
            novo_texto = texto[:m.start()]
            return extraido, novo_texto
    return "", texto

# As marcações em servidor.py
m_utilidades = "# ================================================================== utilidades\n"
m_auth = "# ================================================================== autenticação e permissões\n"
m_usuarios = "# ================================================================== usuários, auditoria e rede (admin)\n"
m_proc = "# ================================================================== processamento de documentos (OCR/extração)\n"
m_casos = "# ================================================================== O.S., casos e pendências\n"
m_relatorios = "# ================================================================== relatório: minuta, DOCX, PDF, FINAL\n"
m_ia = "# ================================================================== IA\n"
m_plantao = "# ================================================================== plantão de agentes (D02)\n"
m_tarefas = "# ================================================================== tarefas, exportação e importação\n"
m_consulta = "# ================================================================== bases de consulta, referências e pesquisa\n"
m_https = "# ================================================================== HTTPS (certificado autoassinado para a rede local)\n"
m_main = "if __name__ == \"__main__\":\n"

# Extrair em ordem reversa ou pela ordem
bloco_consulta, txt = extrair_entre(txt, m_consulta, m_https)
bloco_tarefas, txt = extrair_entre(txt, m_tarefas, m_consulta)
bloco_plantao, txt = extrair_entre(txt, m_plantao, m_tarefas)
bloco_ia, txt = extrair_entre(txt, m_ia, m_plantao)
bloco_relatorios, txt = extrair_entre(txt, m_relatorios, m_ia)
bloco_casos, txt = extrair_entre(txt, m_casos, m_relatorios)
bloco_usuarios, txt = extrair_entre(txt, m_usuarios, m_proc)
bloco_auth, txt = extrair_entre(txt, m_auth, m_usuarios)

cabecalho_comum = '''from servidor import *
from flask import jsonify, request, abort, send_file, session, send_from_directory
import os, json, re, time, datetime, threading, shutil, subprocess, tempfile

'''

def gravar(nome, *blocos):
    with open(f"plugin/investigacao-cpj/app/{nome}", 'w', encoding='utf-8') as f:
        f.write(cabecalho_comum)
        for b in blocos:
            f.write(b)

gravar("rotas_usuarios.py", bloco_auth, bloco_usuarios)
gravar("rotas_casos.py", bloco_casos)
gravar("rotas_relatorios.py", bloco_relatorios)
gravar("rotas_sistema.py", bloco_ia, bloco_plantao, bloco_tarefas)
gravar("rotas_consulta.py", bloco_consulta)

# Inserir os imports no final de servidor.py, antes do m_https
idx_https = txt.find(m_https)

novos_imports = '''
# Importa as rotas divididas em módulos
import rotas_usuarios
import rotas_casos
import rotas_relatorios
import rotas_sistema
import rotas_consulta

'''
txt = txt[:idx_https] + novos_imports + txt[idx_https:]

with open(servidor_path, 'w', encoding='utf-8') as f:
    f.write(txt)

print("Refatoração concluída")
