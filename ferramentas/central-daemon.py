#!/usr/bin/env python3
"""Supervisor / Daemon da Central CPJ para Operação Full-Time 24/7.

Gerencia o processo do servidor web (servidor.py) na porta estática 8765,
mantendo-o em execução contínua com reinício automático em caso de crash (watchdog),
sentinela de parada graciosa (config/central.stop) e controle de PID (config/central.pid).

Uso:
  python central-daemon.py iniciar [--porta 8765] [--workspace PASTA]
  python central-daemon.py parar
  python central-daemon.py status [--json]
  python central-daemon.py reiniciar
  python central-daemon.py instalar-boot
  python central-daemon.py remover-boot
"""
import argparse
import datetime
import json
from pathlib import Path
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

PORTA_PADRAO = 8765
AQUI = os.path.dirname(os.path.abspath(__file__))
PROJETO_DIR = os.path.dirname(AQUI)
APP_DIR = os.path.join(PROJETO_DIR, "plugin", "investigacao-cpj", "app")
SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def resolver_workspace(ws_arg: str = None) -> str:
    if ws_arg and os.path.isdir(ws_arg):
        return os.path.abspath(ws_arg)
    if os.environ.get("CPJ_WORKSPACE") and os.path.isdir(os.environ["CPJ_WORKSPACE"]):
        return os.path.abspath(os.environ["CPJ_WORKSPACE"])
    return PROJETO_DIR


def config_dir(ws: str) -> str:
    d = os.path.join(ws, "config")
    os.makedirs(d, exist_ok=True)
    return d


def pid_path(ws: str) -> str:
    return os.path.join(config_dir(ws), "central.pid")


def stop_sentinel_path(ws: str) -> str:
    return os.path.join(config_dir(ws), "central.stop")


def startup_shortcut_path() -> str:
    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        return ""
    return os.path.join(
        appdata,
        "Microsoft",
        "Windows",
        "Start Menu",
        "Programs",
        "Startup",
        "Central-CPJ-24-7.lnk",
    )


def processo_vivo(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            r = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=SEM_JANELA,
            )
            return str(pid) in r.stdout
        except Exception:
            return False
    else:
        try:
            # kill(pid, 0) também encontra zumbis; eles já não supervisionam nada.
            stat = Path(f"/proc/{pid}/stat")
            if stat.exists() and stat.read_text().rsplit(")", 1)[1].strip().startswith("Z "):
                return False
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def testar_saude_http(porta: int, timeout: float = 3.0) -> bool:
    url = f"http://127.0.0.1:{porta}/api/contato"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CentralDaemon/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status in (200, 401, 403, 404)
    except urllib.error.HTTPError as e:
        return e.code in (200, 401, 403, 404)
    except Exception:
        return False


def ler_info_pid(ws: str) -> dict:
    p = pid_path(ws)
    if not os.path.isfile(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def gravar_info_pid(ws: str, info: dict):
    p = pid_path(ws)
    tmp = p + f".{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)
    os.replace(tmp, p)


def limpar_pid(ws: str):
    p = pid_path(ws)
    if os.path.isfile(p):
        try:
            os.remove(p)
        except Exception:
            pass


def cmd_status(ws: str, formato_json: bool = False):
    info = ler_info_pid(ws)
    daemon_pid = info.get("daemon_pid")
    server_pid = info.get("server_pid")
    porta = info.get("porta", PORTA_PADRAO)
    inicio = info.get("inicio", "")

    vivo = processo_vivo(server_pid) if server_pid else False
    http_ok = testar_saude_http(porta) if vivo else False

    dados = {
        "ativo": vivo and http_ok,
        "daemon_pid": daemon_pid,
        "server_pid": server_pid,
        "processo_vivo": vivo,
        "http_ok": http_ok,
        "porta": porta,
        "url": f"http://127.0.0.1:{porta}",
        "inicio": inicio,
        "workspace": ws,
    }

    if formato_json:
        print(json.dumps(dados, indent=2, ensure_ascii=False))
        return 0 if dados["ativo"] else 1

    if dados["ativo"]:
        print(f"[OK] Central CPJ operando 24/7 na porta {porta}")
        print(f"     PID Servidor : {server_pid}")
        print(f"     PID Daemon   : {daemon_pid}")
        print(f"     Início       : {inicio}")
        print(f"     URL          : {dados['url']}")
        return 0
    elif vivo and not http_ok:
        print(f"[AVISO] Processo {server_pid} ativo, mas porta {porta} não responde HTTP.")
        return 2
    else:
        print(f"[PARADA] Central CPJ não está em execução.")
        return 1


def cmd_parar(ws: str, timeout: float = 15.0):
    info = ler_info_pid(ws)
    daemon_pid = info.get("daemon_pid")
    server_pid = info.get("server_pid")

    sentinela = stop_sentinel_path(ws)
    with open(sentinela, "w", encoding="utf-8") as f:
        f.write(f"stop requested at {datetime.datetime.now().isoformat()}\n")

    pids_para_matar = [p for p in (daemon_pid, server_pid) if p and processo_vivo(p)]
    if not pids_para_matar:
        limpar_pid(ws)
        if os.path.exists(sentinela):
            try:
                os.remove(sentinela)
            except Exception:
                pass
        print("Central CPJ já estava parada.")
        return 0

    print(f"Parando Central CPJ (PIDs: {pids_para_matar})...")
    fim = time.time() + timeout
    while time.time() < fim:
        restantes = [p for p in pids_para_matar if processo_vivo(p)]
        if not restantes:
            break
        time.sleep(0.5)

    restantes = [p for p in pids_para_matar if processo_vivo(p)]
    if restantes:
        print(f"Forçando encerramento dos processos restantes: {restantes}")
        for p in restantes:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(p)], capture_output=True, creationflags=SEM_JANELA)
            else:
                try:
                    os.kill(p, signal.SIGKILL)
                except Exception:
                    pass

    limpar_pid(ws)
    if os.path.exists(sentinela):
        try:
            os.remove(sentinela)
        except Exception:
            pass
    print("[OK] Central CPJ parada com sucesso.")
    return 0


def cmd_iniciar_supervisor(ws: str, porta: int):
    sentinela = stop_sentinel_path(ws)
    if os.path.exists(sentinela):
        try:
            os.remove(sentinela)
        except Exception:
            pass

    info_existente = ler_info_pid(ws)
    spid = info_existente.get("server_pid")
    if spid and processo_vivo(spid) and testar_saude_http(porta):
        print(f"Central CPJ já está em execução no PID {spid} (porta {porta}).")
        return 0

    print(f"Iniciando supervisor 24/7 da Central CPJ na porta {porta}...")

    servidor_py = os.path.join(APP_DIR, "servidor.py")
    if not os.path.isfile(servidor_py):
        print(f"Erro: Arquivo do servidor não encontrado em {servidor_py}", file=sys.stderr)
        return 1

    my_pid = os.getpid()
    tentativas = 0
    max_reinicios_rapidos = 5
    intervalo_janela = 60.0
    tempos_falha = []

    def encerrar_servidor(proc):
        if proc and proc.poll() is None:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, creationflags=SEM_JANELA)
            else:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()

    while True:
        if os.path.exists(sentinela):
            print("Sentinela de parada detectado pelo supervisor. Encerrando.")
            break

        agora = time.time()
        tempos_falha = [t for t in tempos_falha if agora - t < intervalo_janela]
        if len(tempos_falha) >= max_reinicios_rapidos:
            print(f"Erro crítico: Servidor reiniciou {len(tempos_falha)} vezes em {intervalo_janela}s. Abortando watchdog.", file=sys.stderr)
            break

        env = dict(os.environ)
        env["CPJ_WORKSPACE"] = ws
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        cmd = [
            sys.executable,
            servidor_py,
            "--porta",
            str(porta),
            "--workspace",
            ws,
            "--somente-local",
            "--sem-navegador",
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=ws,
                env=env,
                creationflags=SEM_JANELA,
            )
        except Exception as e:
            print(f"Falha ao disparar processo servidor: {e}", file=sys.stderr)
            time.sleep(3)
            tempos_falha.append(time.time())
            continue

        gravar_info_pid(
            ws,
            {
                "daemon_pid": my_pid,
                "server_pid": proc.pid,
                "porta": porta,
                "inicio": datetime.datetime.now().isoformat(),
                "workspace": ws,
            },
        )

        time.sleep(2.0)
        if proc.poll() is not None:
            print(f"Servidor finalizou imediatamente (código {proc.returncode}). Reiniciando...", file=sys.stderr)
            tempos_falha.append(time.time())
            time.sleep(1.0)
            continue

        print(f"Servidor ativo (PID {proc.pid}). Monitorando saúde 24/7...")

        while True:
            if os.path.exists(sentinela):
                print("Sentinela de parada detectado. Finalizando servidor...")
                encerrar_servidor(proc)
                limpar_pid(ws)
                return 0

            ret = proc.poll()
            if ret is not None:
                print(f"[ALERTA WATCHDOG] Processo {proc.pid} caiu com código {ret}. Reiniciando automaticamente...", file=sys.stderr)
                tempos_falha.append(time.time())
                break

            time.sleep(3.0)

    limpar_pid(ws)
    return 1


def cmd_instalar_boot(ws: str):
    destino = startup_shortcut_path()
    if not destino:
        print("Erro: Não foi possível determinar a pasta Startup do Windows.", file=sys.stderr)
        return 1

    vbs = os.path.join(PROJETO_DIR, "ferramentas", "iniciar-central-24-7.vbs")
    if not os.path.isfile(vbs):
        print(f"Erro: {vbs} não encontrado.", file=sys.stderr)
        return 1

    script_ps1 = f"""
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut('{destino}')
$s.TargetPath = 'wscript.exe'
$s.Arguments = '"{vbs}"'
$s.WorkingDirectory = '{PROJETO_DIR}'
$s.Description = 'Central CPJ 24/7 Daemon'
$s.Save()
"""
    r = subprocess.run(["powershell", "-NoProfile", "-Command", script_ps1], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode == 0 and os.path.isfile(destino):
        print(f"[OK] Inicialização automática com o Windows configurada:")
        print(f"     Atalho: {destino}")
        return 0
    else:
        print(f"Falha ao criar atalho no Startup: {r.stderr or r.stdout}", file=sys.stderr)
        return 1


def cmd_remover_boot():
    destino = startup_shortcut_path()
    if destino and os.path.isfile(destino):
        try:
            os.remove(destino)
            print(f"[OK] Atalho de inicialização automática removido: {destino}")
            return 0
        except Exception as e:
            print(f"Erro ao remover atalho: {e}", file=sys.stderr)
            return 1
    print("Nenhum atalho de inicialização no boot encontrado.")
    return 0


def main():
    p = argparse.ArgumentParser(description="Daemon / Supervisor 24/7 da Central CPJ.")
    p.add_argument("comando", choices=["iniciar", "parar", "status", "reiniciar", "instalar-boot", "remover-boot"])
    p.add_argument("--porta", type=int, default=PORTA_PADRAO, help="Porta TCP estática (padrão 8765)")
    p.add_argument("--workspace", default=None, help="Caminho do workspace CPJ")
    p.add_argument("--json", action="store_true", help="Saída em formato JSON para status")
    args = p.parse_args()

    ws = resolver_workspace(args.workspace)

    if args.comando == "status":
        sys.exit(cmd_status(ws, formato_json=args.json))
    elif args.comando == "parar":
        sys.exit(cmd_parar(ws))
    elif args.comando == "iniciar":
        sys.exit(cmd_iniciar_supervisor(ws, args.porta))
    elif args.comando == "reiniciar":
        cmd_parar(ws)
        time.sleep(1.0)
        sys.exit(cmd_iniciar_supervisor(ws, args.porta))
    elif args.comando == "instalar-boot":
        sys.exit(cmd_instalar_boot(ws))
    elif args.comando == "remover-boot":
        sys.exit(cmd_remover_boot())


if __name__ == "__main__":
    main()
