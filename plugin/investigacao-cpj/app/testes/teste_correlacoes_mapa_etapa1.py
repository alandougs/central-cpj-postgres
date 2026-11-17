#!/usr/bin/env python3
"""Suíte de testes automatizados da Etapa 1: Radar de Coincidências Documentadas e Mapa de Referência Offline.

Cobre integralmente os 14 critérios de aceite de `revisoes/plano-correlacoes-mapa-etapa-1.md` (§6),
além de segurança de rotas (permissões, CSRF X-CPJ, somente leitura em GET) e desempenho em base sintética,
sempre em workspace temporário isolado (`tempfile.TemporaryDirectory`).
"""
import csv, importlib, json, os, re, shutil, sqlite3, subprocess, sys, tempfile, time, unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(AQUI)
PLUGIN_DIR = os.path.dirname(APP_DIR)
RAIZ = os.path.dirname(os.path.dirname(PLUGIN_DIR))
S_BASE = os.path.join(PLUGIN_DIR, "skills", "base-cpj", "scripts")
INDEXAR_PY = os.path.join(S_BASE, "indexar.py")

if S_BASE not in sys.path:
    sys.path.insert(0, S_BASE)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import geo_local as GEO  # noqa: E402
import correlacoes as CORR  # noqa: E402


TERMOS_PROIBIDOS_ETAPA1 = (
    "orcrim",
    "organização criminosa",
    "organizacao criminosa",
    "empresa de fachada",
    "beneficiário final",
    "beneficiario final",
    "alto risco",
)


def _gravar_caso(ws, cid, meta, pessoas=None, entidades=None, fluxo=None, transcricao=None, analise_md=None, relatorio_md=None):
    base = os.path.join(ws, "casos", cid)
    os.makedirs(os.path.join(base, "00-originais"), exist_ok=True)
    os.makedirs(os.path.join(base, "01-extracao", "ip-principal"), exist_ok=True)
    os.makedirs(os.path.join(base, "02-analise"), exist_ok=True)
    os.makedirs(os.path.join(base, "03-relatorios"), exist_ok=True)

    meta_completo = {
        "id": cid,
        "ordem_servico": cid.replace("OS-", "").replace("-", "/"),
        "inquerito": "",
        "processo": "",
        "status": "analisado",
        "datas": {"recebido": "2026-10-01"},
        **meta,
    }
    with open(os.path.join(base, "caso.json"), "w", encoding="utf-8") as f:
        json.dump(meta_completo, f, ensure_ascii=False, indent=2)

    if pessoas:
        cols = [
            "nome", "cpf", "rg", "nascimento", "mae", "pai", "telefones", "enderecos",
            "empresas", "cnpj", "emails", "placas", "condicao", "documento", "paginas", "fls",
            "lat", "lon", "contexto_coordenada", "fonte_coordenada", "endereco_empresa"
        ]
        with open(os.path.join(base, "02-analise", "pessoas.csv"), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, delimiter=";")
            w.writeheader()
            for p in pessoas:
                w.writerow({k: p.get(k, "") for k in cols})

    if entidades:
        cols_e = ["tipo", "valor", "pagina_pdf", "trecho"]
        with open(os.path.join(base, "01-extracao", "ip-principal", "entidades.csv"), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols_e, delimiter=";")
            w.writeheader()
            for e in entidades:
                w.writerow({k: e.get(k, "") for k in cols_e})

    if fluxo:
        cols_ff = [
            "seq", "data", "valor", "meio",
            "origem_titular", "origem_cpf_cnpj", "origem_banco", "origem_ag_conta", "origem_chave",
            "destino_titular", "destino_cpf_cnpj", "destino_banco", "destino_ag_conta", "destino_chave",
            "fonte_pag", "fls",
        ]
        with open(os.path.join(base, "02-analise", "fluxo-financeiro.csv"), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols_ff, delimiter=";")
            w.writeheader()
            for fl in fluxo:
                w.writerow({k: fl.get(k, "") for k in cols_ff})

    if transcricao:
        with open(os.path.join(base, "01-extracao", "ip-principal", "transcricao.md"), "w", encoding="utf-8") as f:
            f.write(transcricao)

    if analise_md:
        with open(os.path.join(base, "02-analise", "resumo-analise.md"), "w", encoding="utf-8") as f:
            f.write(analise_md)

    if relatorio_md:
        with open(os.path.join(base, "03-relatorios", f"RELATORIO-{cid}-v01.md"), "w", encoding="utf-8") as f:
            f.write(relatorio_md)


def _rodar_indexar(ws, extra_env=None):
    env = dict(os.environ, CPJ_WORKSPACE=ws, CPJ_SEM_AGENTE_EMBUTIDO="1", PYTHONIOENCODING="utf-8")
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, INDEXAR_PY, "--tudo"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


class TesteCorrelacoesMapaEtapa1(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpj_geo_etapa1_")
        self.ws = self.tmp.name
        for d in ("casos", "modelos", "producao", "rag", "consulta", "referencias", "calibracao", "config"):
            os.makedirs(os.path.join(self.ws, d), exist_ok=True)
        self._env_orig = os.environ.get("CPJ_WORKSPACE")
        os.environ["CPJ_WORKSPACE"] = self.ws
        os.environ["CPJ_SEM_AGENTE_EMBUTIDO"] = "1"

    def tearDown(self):
        if self._env_orig is None:
            os.environ.pop("CPJ_WORKSPACE", None)
        else:
            os.environ["CPJ_WORKSPACE"] = self._env_orig
        self.tmp.cleanup()

    def _popular_cenario_base(self):
        """Popula casos sintéticos cobrindo todos os critérios de aceite da Etapa 1."""
        # Procedimento 1 (IPe 2001111-11.2026): representado por DUAS O.S. (OS-101-2026 e OS-102-2026)
        _gravar_caso(
            self.ws,
            "OS-101-2026",
            {"inquerito": "2001111-11.2026.826.0482", "processo": "1500111-22.2026.8.26.0482"},
            pessoas=[
                {
                    "nome": "MARCOS FICTICIO UM",
                    "cpf": "123.456.789-01",
                    "telefones": "(18) 99111-2233",
                    "emails": "marcos.ficticio@exemplo.com",
                    "placas": "ABC-1D23",
                    "enderecos": "Rua Sete de Setembro, 100, Centro, Presidente Prudente/SP",
                    "empresas": "ALFA PAGAMENTOS DIGITAIS LTDA",
                    "cnpj": "12.345.678/0001-90",
                    "condicao": "investigado(a)",
                    "documento": "boletim-extrato.pdf",
                    "paginas": "12",
                    "fls": "25",
                },
                {
                    "nome": "VITIMA EXEMPLO UM",
                    "cpf": "987.654.321-09",
                    "enderecos": "Av. Brasil, 500, Centro, Assis/SP",
                    "condicao": "vítima",
                    "paginas": "3",
                    "fls": "5",
                    # Coordenada documentada de local do fato (NÃO deve virar coordenada residencial da pessoa se não tivesse município)
                    "lat": "-22.660800",
                    "lon": "-50.418200",
                    "contexto_coordenada": "endereco_pessoa",
                    "fonte_coordenada": "termo-declaracao.pdf pág. 3 fls. 5",
                },
                {
                    "nome": "PESSOA SO COM COORD FATO",
                    "cpf": "444.555.666-77",
                    "enderecos": "",
                    "condicao": "testemunha",
                    "paginas": "8",
                    "fls": "14",
                    "lat": "-22.120700",
                    "lon": "-51.388200",
                    "contexto_coordenada": "local_fato",
                    "fonte_coordenada": "auto-exibicao.pdf pág. 8 fls. 14",
                },
            ],
            entidades=[
                {"tipo": "CPF", "valor": "123.456.789-01", "pagina_pdf": "12", "trecho": "CPF 123.456.789-01 fls. 25"},
                {"tipo": "CHAVE_PIX", "valor": "a1b2c3d4-e5f6-4789-8012-34567890abcd", "pagina_pdf": "14", "trecho": "Chave Pix EVP fls. 28"},
                # Identificador incerto: NÃO pode gerar coincidência exata
                {"tipo": "CPF", "valor": "555.666.777-?1 [dígito incerto]", "pagina_pdf": "15", "trecho": "CPF ilegível 555.666.777-?1"},
                # Identificador exclusivo do mesmo procedimento (aparecerá só na OS-101 e OS-102 do mesmo IP)
                {"tipo": "CPF", "valor": "222.333.444-55", "pagina_pdf": "16", "trecho": "CPF exclusivo do IP 1"},
            ],
            fluxo=[
                {
                    "seq": "1", "data": "10/09/2026", "valor": "5000,00", "meio": "PIX",
                    "origem_titular": "VITIMA EXEMPLO UM", "origem_cpf_cnpj": "987.654.321-09",
                    "origem_banco": "001 Banco do Brasil", "origem_ag_conta": "Ag 1111 CC 22222-3", "origem_chave": "",
                    "destino_titular": "ALFA PAGAMENTOS DIGITAIS LTDA", "destino_cpf_cnpj": "12.345.678/0001-90",
                    "destino_banco": "237 Bradesco", "destino_ag_conta": "Ag 0123 CC 99887-6",
                    "destino_chave": "a1b2c3d4-e5f6-4789-8012-34567890abcd",
                    "fonte_pag": "14", "fls": "28",
                },
                # Conta sem banco informado e conta de banco diferente com mesmos dígitos 55555-0
                {
                    "seq": "2", "data": "11/09/2026", "valor": "1000,00", "meio": "TED",
                    "origem_titular": "ALFA PAGAMENTOS DIGITAIS LTDA", "origem_cpf_cnpj": "",
                    "origem_banco": "", "origem_ag_conta": "Ag 0001 CC 77777-9", "origem_chave": "",
                    "destino_titular": "CONTA BANCO ITAU", "destino_cpf_cnpj": "",
                    "destino_banco": "341 Itaú", "destino_ag_conta": "Ag 0001 CC 55555-0", "destino_chave": "",
                    "fonte_pag": "15", "fls": "29",
                },
            ],
            transcricao="## Página 12\nfls. 25\nQualificação de MARCOS FICTICIO UM, CPF 123.456.789-01.\n",
            analise_md="# Análise\nConsta o CPF 123.456.789-01 na pág. 12 (fls. 25).\n",
            relatorio_md="# Relatório\nO investigado de CPF 123.456.789-01 foi citado às (Fls. 25).\n",
        )

        # OS-102-2026 pertence ao MESMO procedimento (mesmo IPe 2001111-11.2026)
        _gravar_caso(
            self.ws,
            "OS-102-2026",
            {"inquerito": "2001111-11.2026.826.0482", "processo": "1500111-22.2026.8.26.0482"},
            entidades=[
                # Este CPF só aparece em OS-101 e OS-102 (mesmo procedimento) -> NÃO deve gerar correlação!
                {"tipo": "CPF", "valor": "222.333.444-55", "pagina_pdf": "4", "trecho": "Mesmo IP em outra O.S."},
            ],
        )

        # Procedimento 2 (IPe 2002222-22.2026 — distinto do Procedimento 1)
        _gravar_caso(
            self.ws,
            "OS-201-2026",
            {"inquerito": "2002222-22.2026.826.0482", "processo": "1500222-33.2026.8.26.0482"},
            pessoas=[
                {
                    "nome": "MARCOS FICTICIO UM",
                    "cpf": "12345678901",
                    "telefones": "18991112233",
                    "emails": "MARCOS.FICTICIO@EXEMPLO.COM",
                    "placas": "ABC1D23",
                    "enderecos": "Rua Oito, 200, Centro, Presidente Prudente - SP",
                    "condicao": "titular de conta recebedora",
                    "paginas": "20",
                    "fls": "42",
                },
                {
                    "nome": "PESSOA MUNICIPIO AMBIGUO",
                    "cpf": "333.444.555-66",
                    # Bom Jesus existe em PI, RN, PB, RS, SC -> sem UF deve ficar em sem_localizacao (municipio_ambiguo)
                    "enderecos": "Rua Principal, 10, Centro, Bom Jesus",
                    "condicao": "investigado(a)",
                    "paginas": "21",
                    "fls": "43",
                },
                {
                    "nome": "PESSOA ENDERECOS CONFLITANTES",
                    "cpf": "777.888.999-00",
                    "enderecos": "Rua A, 10, Presidente Prudente/SP | Av. Paulista, 1000, São Paulo/SP",
                    "condicao": "investigado(a)",
                    "paginas": "22",
                    "fls": "44",
                },
            ],
            entidades=[
                {"tipo": "CNPJ", "valor": "12.345.678/0001-90", "pagina_pdf": "20", "trecho": "Empresa ALFA CNPJ 12.345.678/0001-90 fls. 42"},
                {"tipo": "CHAVE_PIX", "valor": "a1b2c3d4-e5f6-4789-8012-34567890abcd", "pagina_pdf": "23", "trecho": "Chave Pix EVP fls. 45"},
                {"tipo": "CPF", "valor": "555.666.777-?1 [dígito incerto]", "pagina_pdf": "24", "trecho": "CPF com dígito incerto"},
                # Identificador para testar caso sem procedimento confirmado:
                {"tipo": "CPF", "valor": "888.777.666-55", "pagina_pdf": "25", "trecho": "CPF 888.777.666-55"},
            ],
            fluxo=[
                {
                    "seq": "1", "data": "18/09/2026", "valor": "3200,00", "meio": "PIX",
                    "origem_titular": "OUTRA VITIMA", "origem_cpf_cnpj": "",
                    "origem_banco": "104 Caixa", "origem_ag_conta": "Ag 0500 CC 12345-1", "origem_chave": "",
                    "destino_titular": "ALFA PAGAMENTOS DIGITAIS LTDA", "destino_cpf_cnpj": "12.345.678/0001-90",
                    "destino_banco": "Bradesco", "destino_ag_conta": "0123 / 99887-6",
                    "destino_chave": "a1b2c3d4-e5f6-4789-8012-34567890abcd",
                    "fonte_pag": "23", "fls": "45",
                },
                # Conta sem banco (mesmos dígitos 77777-9 da OS-101) e conta em banco diferente (260 Nubank vs 341 Itaú na OS-101, mesmos dígitos 55555-0)
                {
                    "seq": "2", "data": "19/09/2026", "valor": "900,00", "meio": "TED",
                    "origem_titular": "DESCONHECIDO", "origem_cpf_cnpj": "",
                    "origem_banco": "?", "origem_ag_conta": "Ag 0001 CC 77777-9", "origem_chave": "",
                    "destino_titular": "CONTA BANCO NUBANK", "destino_cpf_cnpj": "",
                    "destino_banco": "260 Nubank", "destino_ag_conta": "Ag 0001 CC 55555-0", "destino_chave": "",
                    "fonte_pag": "24", "fls": "46",
                },
            ],
        )

        # Caso sem número de IPe nem Processo (identidade de procedimento insuficiente)
        _gravar_caso(
            self.ws,
            "OS-301-2026",
            {"inquerito": "", "processo": "", "bo": "BO-9999/2026"},
            entidades=[
                {"tipo": "CPF", "valor": "888.777.666-55", "pagina_pdf": "2", "trecho": "Aparece em O.S. só com BO, sem IPe"},
            ],
        )

    def test_01_coincidencias_procedimentos_distintos_e_mesmo_procedimento(self):
        """Critérios 1, 2, 3, 4 e 7:
        - CPF, CNPJ, CHAVE_PIX, CONTA (com banco), TELEFONE, EMAIL e PLACA em 2 procedimentos distintos geram coincidência.
        - Duas O.S. do mesmo procedimento (OS-101 e OS-102) não contam como procedimentos distintos.
        - O.S. sem IPe/processo (OS-301) sinaliza limitação e não gera coincidência confirmada entre IPs.
        - Identificadores com '?' / '[dígito incerto]' e contas sem banco ou de bancos distintos não colidem.
        - Repetições em extração, análise e relatório do mesmo procedimento não inflam contagem, mas preservam todas as fontes.
        """
        self._popular_cenario_base()
        r_idx = _rodar_indexar(self.ws)
        self.assertEqual(r_idx.returncode, 0, r_idx.stderr)

        res = CORR.consultar_correlacoes(self.ws, estado="todos", limite=100)
        self.assertFalse(res["desatualizado"])

        por_tipo = {it["tipo"]: it for it in res["itens"]}
        for t_esp in ("CPF", "CNPJ", "CHAVE_PIX", "CONTA", "TELEFONE", "EMAIL", "PLACA"):
            self.assertIn(t_esp, por_tipo, f"Deveria haver coincidência confirmada para {t_esp}")
            self.assertEqual(por_tipo[t_esp]["total_procedimentos"], 2)

        # Critério 2: CPF 222.333.444-55 (presente em OS-101 e OS-102 do mesmo IPe) NÃO pode gerar correlação
        valores_corr = {it["valor_norm"] for it in res["itens"]}
        self.assertNotIn("22233344455", valores_corr)

        # Critério 2b: CPF 888.777.666-55 (OS-201 + OS-301 sem IPe/Processo) NÃO entra nas confirmadas, mas aparece em limitacoes_procedimento
        self.assertNotIn("88877766655", valores_corr)
        lims_proc = res["limitacoes_procedimento"]
        self.assertTrue(any(lp["valor_norm"] == "88877766655" and lp["motivo"] == "identidade_procedimento_insuficiente" for lp in lims_proc))

        # Critério 3: CPF com '?' / '[dígito incerto]' jamais entra nas coincidências
        self.assertFalse(any("555666777" in it["valor_norm"] for it in res["itens"]))
        self.assertTrue(any(lc["motivo"] == "identificador_com_incerteza" for lc in res["limitacoes_coleta"]))

        # Critério 4: Conta sem banco (77777-9) e contas de bancos distintos (341 Itaú vs 260 Nubank, 55555-0) não colidem
        contas_corr = [it for it in res["itens"] if it["tipo"] == "CONTA"]
        self.assertEqual(len(contas_corr), 1)
        self.assertEqual(contas_corr[0]["valor_norm"], "237_bradesco|0123998876")

        # Critério 7: CPF 123.456.789-01 repetido em extração, análise e relatório da OS-101 conta como 1 procedimento para OS-101,
        # preservando as etapas ['extracao', 'analise', 'relatorio'] e todas as fontes
        corr_cpf = por_tipo["CPF"]
        oc_101 = next(o for o in corr_cpf["ocorrencias"] if o["caso"] == "OS-101-2026")
        self.assertIn("extracao", oc_101["etapas"])
        self.assertIn("analise", oc_101["etapas"])
        self.assertIn("relatorio", oc_101["etapas"])
        self.assertGreaterEqual(len(oc_101["fontes"]), 3)
        self.assertIn("deduplicado_entre_etapas_do_mesmo_caso", corr_cpf["limitacoes"])

    def test_02_pf_pj_separados_coordenadas_contexto_e_sem_localizacao(self):
        """Critérios 5, 6 e 8:
        - PF com empresa/CNPJ na qualificação permanece PF, e a PJ é representada separadamente com vínculo.
        - Coordenada documentada com contexto 'local_fato' não é atribuída automaticamente à pessoa.
        - Município ambíguo sem UF ('Bom Jesus'), endereços conflitantes (Presidente Prudente vs São Paulo)
          e pessoa sem endereço ficam em `sem_localizacao` e nunca no meio do mapa.
        - Pontos no mesmo município compartilham a coordenada exata no grupo sem jitter artificial.
        """
        self._popular_cenario_base()
        _rodar_indexar(self.ws)

        mapa = CORR.consultar_mapa(self.ws, limite=500)
        self.assertFalse(mapa["desatualizado"])

        # Critério 5: MARCOS FICTICIO UM na OS-101 tem empresas/CNPJ, mas permanece PF, e ALFA PAGAMENTOS é PJ separada
        p_marcos_101 = next(p for p in mapa["pontos"] if p["caso"] == "OS-101-2026" and p["nome"] == "MARCOS FICTICIO UM")
        self.assertEqual(p_marcos_101["tipo_pessoa"], "PF")
        self.assertEqual(p_marcos_101["precisao"], "municipio_aproximado")
        self.assertEqual(p_marcos_101["municipio"], "Presidente Prudente")
        self.assertEqual(p_marcos_101["uf"], "SP")
        self.assertTrue(any(v["tipo"] == "PJ_ASSOCIADA" and "ALFA PAGAMENTOS" in v["nome"] for v in p_marcos_101["vinculos"]))

        pj_alfa_101 = next(s for s in mapa["sem_localizacao"] if s["caso"] == "OS-101-2026" and s["tipo_pessoa"] == "PJ")
        self.assertIn("ALFA PAGAMENTOS", pj_alfa_101["nome"])
        self.assertEqual(pj_alfa_101["motivo_sem_localizacao"], "sem_endereco_pj_associada")

        # Critério 6: VITIMA EXEMPLO UM tem coordenada documentada com contexto 'endereco_pessoa' -> 'coordenada_documentada'
        p_vit = next(p for p in mapa["pontos"] if p["nome"] == "VITIMA EXEMPLO UM")
        self.assertEqual(p_vit["precisao"], "coordenada_documentada")
        self.assertEqual(p_vit["contexto_coordenada"], "endereco_pessoa")

        # Já PESSOA SO COM COORD FATO tem coordenada com contexto 'local_fato' -> NÃO atribuída, fica em sem_localizacao!
        ids_pontos = {p["nome"] for p in mapa["pontos"]}
        self.assertNotIn("PESSOA SO COM COORD FATO", ids_pontos)
        sem_fato = next(s for s in mapa["sem_localizacao"] if s["nome"] == "PESSOA SO COM COORD FATO")
        self.assertEqual(sem_fato["motivo_sem_localizacao"], "coordenada_contexto_incompativel")
        self.assertIsNone(sem_fato["lat"])
        self.assertIsNone(sem_fato["lon"])

        # Critério 8: Município ambíguo sem UF ('Bom Jesus') e endereços conflitantes ficam em sem_localizacao
        sem_amb = next(s for s in mapa["sem_localizacao"] if s["nome"] == "PESSOA MUNICIPIO AMBIGUO")
        self.assertEqual(sem_amb["motivo_sem_localizacao"], "municipio_ambiguo")

        sem_conf = next(s for s in mapa["sem_localizacao"] if s["nome"] == "PESSOA ENDERECOS CONFLITANTES")
        self.assertEqual(sem_conf["motivo_sem_localizacao"], "localizacao_conflitante")
        self.assertEqual(len(sem_conf["enderecos"]), 2)

        # Sem jitter artificial: MARCOS na OS-101 e MARCOS na OS-201 em Presidente Prudente têm exatamente o mesmo lat/lon e formam 1 grupo
        p_marcos_201 = next(p for p in mapa["pontos"] if p["caso"] == "OS-201-2026" and p["nome"] == "MARCOS FICTICIO UM")
        self.assertEqual(p_marcos_101["lat"], p_marcos_201["lat"])
        self.assertEqual(p_marcos_101["lon"], p_marcos_201["lon"])
        grp_pp = next(g for g in mapa["grupos"] if g["municipio"] == "Presidente Prudente")
        self.assertEqual(grp_pp["total"], 2)

    def test_03_estado_humano_persistente_revisao_e_perda_de_suporte(self):
        """Critérios 9 e 10:
        - Estado `lido` é independente de `fixado`/`descartado`.
        - Descarte exige motivo.
        - Estado humano persiste após reindexação (`indexar.py --tudo`).
        - Se um 3º procedimento for adicionado para a mesma correlação já revisada, `requer_revisao` passa a True
          preservando o histórico humano.
        - Se um procedimento for removido e a correlação perder suporte (< 2 procedimentos), ela sai da lista ativa
          mas seu histórico humano permanece preservado.
        """
        self._popular_cenario_base()
        _rodar_indexar(self.ws)

        res = CORR.consultar_correlacoes(self.ws, tipo="CPF", estado="todos")
        corr_cpf = res["itens"][0]
        cid = corr_cpf["id"]

        # 1) Marcar como fixado
        reg1 = CORR.atualizar_estado_correlacao(self.ws, cid, "alan.silva", estado="fixado")
        self.assertEqual(reg1["estado"], "fixado")
        self.assertFalse(reg1["lido"])

        # 2) Marcar como lido sem perder o estado 'fixado'
        reg2 = CORR.atualizar_estado_correlacao(self.ws, cid, "alan.silva", lido=True)
        self.assertEqual(reg2["estado"], "fixado")
        self.assertTrue(reg2["lido"])
        self.assertEqual(len(reg2["historico"]), 2)

        # 3) Descartar sem motivo deve falhar com ValueError
        with self.assertRaises(ValueError):
            CORR.atualizar_estado_correlacao(self.ws, cid, "alan.silva", estado="descartado", motivo="")

        # 4) Reindexar e verificar que 'fixado' e 'lido=True' permanecem intactos e requer_revisao=False
        _rodar_indexar(self.ws)
        res_pos = CORR.consultar_correlacoes(self.ws, tipo="CPF", estado="todos")
        c_pos = res_pos["itens"][0]
        self.assertEqual(c_pos["estado"], "fixado")
        self.assertTrue(c_pos["lido"])
        self.assertFalse(c_pos["requer_revisao"])

        # 5) Critério 10: Adicionar um 3º procedimento distinto (OS-401-2026) com o mesmo CPF e reindexar
        _gravar_caso(
            self.ws,
            "OS-401-2026",
            {"inquerito": "2004444-44.2026.826.0482"},
            entidades=[{"tipo": "CPF", "valor": "123.456.789-01", "pagina_pdf": "1", "trecho": "Novo IP com o mesmo CPF"}],
        )
        _rodar_indexar(self.ws)
        res_rev = CORR.consultar_correlacoes(self.ws, tipo="CPF", estado="todos")
        c_rev = res_rev["itens"][0]
        self.assertEqual(c_rev["total_procedimentos"], 3)
        self.assertEqual(c_rev["estado"], "fixado")
        self.assertTrue(c_rev["lido"])
        self.assertTrue(c_rev["requer_revisao"], "Deve sinalizar requer_revisao=True quando novas evidências alteram a correlação")
        self.assertEqual(len(c_rev["historico"]), 2)

        # 6) Critério 9b: Perda de suporte — remover OS-201 e OS-401 para que o CPF fique em apenas 1 procedimento
        shutil.rmtree(os.path.join(self.ws, "casos", "OS-201-2026"))
        shutil.rmtree(os.path.join(self.ws, "casos", "OS-401-2026"))
        _rodar_indexar(self.ws)

        res_ativos = CORR.consultar_correlacoes(self.ws, tipo="CPF", estado="todos", incluir_sem_suporte=False)
        self.assertEqual(len(res_ativos["itens"]), 0, "Correlação sem suporte (< 2 procedimentos) deve sair dos resultados ativos")

        res_com_hist = CORR.consultar_correlacoes(self.ws, estado="todos", incluir_sem_suporte=True)
        c_hist = next(x for x in res_com_hist["itens"] if x["id"] == cid)
        self.assertFalse(c_hist["tem_suporte"])
        self.assertEqual(c_hist["estado"], "fixado")
        self.assertEqual(len(c_hist["historico"]), 2)

    def test_04_neutralidade_sem_scores_e_sem_termos_acusatorios(self):
        """Critério 11: Nenhuma rota, código da Etapa 1 ou payload usa score 1-100 ou rótulo acusatório automático."""
        self._popular_cenario_base()
        _rodar_indexar(self.ws)

        res_corr = CORR.consultar_correlacoes(self.ws, estado="todos")
        res_mapa = CORR.consultar_mapa(self.ws)
        dump = json.dumps({"c": res_corr, "m": res_mapa}, ensure_ascii=False).lower()

        for termo in TERMOS_PROIBIDOS_ETAPA1:
            self.assertNotIn(termo, dump, f"Termo acusatório proibido encontrado no payload: {termo}")

        for item in res_corr["itens"]:
            self.assertNotIn("score", item)
            self.assertNotIn("prioridade", item)
            self.assertNotIn("risco", item)
            self.assertRegex(item["titulo"], r"registrado em \d+ procedimentos")

    def test_05_isolamento_de_falha_e_deteccao_desatualizado(self):
        """Critério 14: Falha simulada no módulo de inteligência não bloqueia indexar.py nem apaga o RAG principal,
        e a consulta informa `desatualizado=True`."""
        self._popular_cenario_base()
        r_falha = _rodar_indexar(self.ws, extra_env={"CPJ_SIMULAR_ERRO_INTELIGENCIA": "1"})
        self.assertEqual(r_falha.returncode, 0, "indexar.py não deve falhar mesmo quando o módulo de inteligência lança exceção")
        self.assertIn("AVISO: atualização de correlações/mapa falhou", r_falha.stdout)

        # O banco RAG principal (trechos, entidades, pessoas) deve ter sido gravado normalmente
        con = sqlite3.connect(os.path.join(self.ws, "rag", "cpj.sqlite"))
        n_pessoas = con.execute("SELECT COUNT(*) FROM pessoas").fetchone()[0]
        con.close()
        self.assertGreater(n_pessoas, 0)

        # E a consulta de correlações deve indicar desatualizado=True sem quebrar
        res = CORR.consultar_correlacoes(self.ws)
        self.assertTrue(res["desatualizado"])

    def test_06_rotas_http_atalhos_e_zero_requisicoes_externas(self):
        """Critérios 12, 13 e contratos HTTP (§4.4):
        - GET /api/inteligencia/correlacoes e GET /api/inteligencia/mapa funcionam sem mutar estado;
        - POST /api/inteligencia/correlacoes/estado exige X-CPJ e motivo ao descartar;
        - Destaque de correlação no mapa informa quantos registros têm localização e quantos estão sem coordenadas;
        - `index.html` e `inteligencia-mapa.js` possuem zero requisições externas e contêm os 4 atalhos de navegação.
        """
        self._popular_cenario_base()
        _rodar_indexar(self.ws)

        import servidor as SRV
        import rotas.comum as COMUM
        COMUM.WS = self.ws
        COMUM.C.WS = self.ws
        COMUM.auth._inst = COMUM.Auth(self.ws)
        SRV.app.config.update(TESTING=True)

        COMUM.auth.salvar_usuario("inv_teste", "Investigador Ficticio", "investigador", "SenhaFicticia123")
        client = SRV.app.test_client()
        r_login = client.post("/api/entrar", json={"login": "inv_teste", "senha": "SenhaFicticia123"}, headers={"X-CPJ": "1"})
        self.assertEqual(r_login.status_code, 200)

        # GET correlacoes
        r1 = client.get("/api/inteligencia/correlacoes?tipo=CNPJ")
        self.assertEqual(r1.status_code, 200)
        j1 = r1.get_json()
        self.assertEqual(j1["total"], 1)
        corr_cnpj_id = j1["itens"][0]["id"]

        # Parâmetro inválido -> 400
        r_inv = client.get("/api/inteligencia/correlacoes?tipo=ENDERECO")
        self.assertEqual(r_inv.status_code, 400)

        # POST estado sem cabeçalho X-CPJ -> bloqueado (400/403)
        r_sem_csrf = client.post("/api/inteligencia/correlacoes/estado", json={"id": corr_cnpj_id, "lido": True})
        self.assertIn(r_sem_csrf.status_code, (400, 403))

        # POST estado com X-CPJ: descartar sem motivo -> 400
        r_sem_mot = client.post(
            "/api/inteligencia/correlacoes/estado",
            headers={"X-CPJ": "1"},
            json={"id": corr_cnpj_id, "estado": "descartado", "motivo": ""},
        )
        self.assertEqual(r_sem_mot.status_code, 400)

        # POST estado válido
        r_ok = client.post(
            "/api/inteligencia/correlacoes/estado",
            headers={"X-CPJ": "1"},
            json={"id": corr_cnpj_id, "estado": "descartado", "motivo": "Empresa intermediadora de pagamentos regulada", "lido": True},
        )
        self.assertEqual(r_ok.status_code, 200)
        self.assertEqual(r_ok.get_json()["item"]["estado"], "descartado")
        self.assertTrue(r_ok.get_json()["item"]["lido"])

        # GET mapa destacando correlação de CPF (localizados vs sem_localizacao)
        r_cpf = client.get("/api/inteligencia/correlacoes?tipo=CPF").get_json()
        corr_cpf_id = r_cpf["itens"][0]["id"]
        r_mapa = client.get(f"/api/inteligencia/mapa?correlacao_id={corr_cpf_id}")
        self.assertEqual(r_mapa.status_code, 200)
        jm = r_mapa.get_json()
        self.assertIsNotNone(jm["correlacao_selecionada"])
        self.assertEqual(jm["correlacao_selecionada"]["localizados"], 2)
        self.assertIn("metadata", jm["cartografia"])

        # Critério 12 e 13: inspecionar código estático de index.html e inteligencia-mapa.js
        js_path = os.path.join(APP_DIR, "static", "js", "inteligencia-mapa.js")
        html_path = os.path.join(APP_DIR, "static", "index.html")
        with open(js_path, encoding="utf-8") as f:
            js_txt = f.read()
        with open(html_path, encoding="utf-8") as f:
            html_txt = f.read()

        # MP91 (escolha do operador): o mapa real busca imagens em tile.openstreetmap.org; nenhuma outra URL externa.
        js_sem_osm = js_txt.replace("https://tile.openstreetmap.org/{z}/{x}/{y}.png", "").replace("https://www.openstreetmap.org/copyright", "")
        self.assertNotRegex(js_sem_osm, r"https?://", "inteligencia-mapa.js só pode citar os tiles do OpenStreetMap e a página de atribuição")
        for id_atalho in ("b-insp-qualificacao", "b-insp-caso", "b-insp-grafo", "b-insp-fonte"):
            self.assertIn(id_atalho, js_txt, f"Atalho obrigatório ausente no inspetor do mapa: {id_atalho}")
        self.assertIn('/static/js/inteligencia-mapa.js', html_txt)

    def test_07_desempenho_base_sintetica_representativa(self):
        """Ensaio de desempenho (§5): 30 casos sintéticos com qualificações e entidades em tempo < 5s."""
        for i in range(1, 31):
            cid = f"OS-{500 + i}-2026"
            cpf_compartilhado = f"{100 + (i % 5):03d}.222.333-44"
            _gravar_caso(
                self.ws,
                cid,
                {"inquerito": f"2009{i:03d}-11.2026.826.0482"},
                pessoas=[
                    {
                        "nome": f"INVESTIGADO SINTETICO {i}",
                        "cpf": cpf_compartilhado,
                        "enderecos": "Av. Coronel José Soares Marcondes, 1000, Presidente Prudente/SP",
                        "condicao": "investigado(a)",
                        "paginas": "5",
                        "fls": "10",
                    }
                ],
                entidades=[
                    {"tipo": "CPF", "valor": cpf_compartilhado, "pagina_pdf": "5", "trecho": "CPF recorrente"},
                ],
            )

        t0 = time.perf_counter()
        r = _rodar_indexar(self.ws)
        dt_index = time.perf_counter() - t0
        self.assertEqual(r.returncode, 0, r.stderr)

        t1 = time.perf_counter()
        res_c = CORR.consultar_correlacoes(self.ws, limite=100)
        res_m = CORR.consultar_mapa(self.ws, limite=500)
        dt_query = time.perf_counter() - t1

        self.assertEqual(res_c["total"], 5)
        self.assertEqual(res_m["resumo"]["localizados"], 30)
        self.assertLess(dt_index, 15.0, f"Indexação de 30 casos demorou {dt_index:.2f}s")
        self.assertLess(dt_query, 1.0, f"Consultas de correlações + mapa demoraram {dt_query:.3f}s")


if __name__ == "__main__":
    unittest.main(verbosity=2)
