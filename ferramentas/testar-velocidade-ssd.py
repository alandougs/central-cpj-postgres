#!/usr/bin/env python
"""Mede a velocidade de leitura sequencial de um disco.

Exemplo:
    python testar-velocidade-ssd.py E:\\ --gb 2

O teste cria um arquivo temporario no destino, le o arquivo em sequencia e o
remove ao terminar. Nenhum arquivo existente e alterado.
"""
import argparse
import os
import secrets
import time
from pathlib import Path


def formatar_mb(valor):
    return f"{valor / (1024 * 1024):,.1f} MB/s".replace(",", "X").replace(".", ",").replace("X", ".")


def testar(destino, tamanho_gb, bloco_mb):
    destino = Path(destino).expanduser().resolve()
    if not destino.is_dir():
        raise FileNotFoundError(f"Pasta nao encontrada: {destino}")
    tamanho = int(tamanho_gb * 1024**3)
    bloco = bloco_mb * 1024**2
    arquivo = destino / f".teste-leitura-ssd-{os.getpid()}-{secrets.token_hex(4)}.bin"
    dados = secrets.token_bytes(bloco)
    lidos = 0
    inicio = time.perf_counter()
    try:
        with arquivo.open("wb") as stream:
            restante = tamanho
            while restante:
                parte = dados if restante >= len(dados) else dados[:restante]
                stream.write(parte)
                restante -= len(parte)
            stream.flush()
            os.fsync(stream.fileno())
        inicio = time.perf_counter()
        with arquivo.open("rb", buffering=0) as stream:
            while parte := stream.read(bloco):
                lidos += len(parte)
        duracao = time.perf_counter() - inicio
    finally:
        try:
            arquivo.unlink()
        except FileNotFoundError:
            pass
    return lidos, duracao


def main():
    parser = argparse.ArgumentParser(description="Teste de leitura sequencial de SSD/HD")
    parser.add_argument("destino", help="Letra ou pasta do SSD, por exemplo E:\\")
    parser.add_argument("--gb", type=float, default=1.0, help="Tamanho do arquivo temporario (padrao: 1 GB)")
    parser.add_argument("--bloco-mb", type=int, default=8, help="Tamanho do bloco de leitura (padrao: 8 MB)")
    args = parser.parse_args()
    if args.gb <= 0 or args.bloco_mb <= 0:
        parser.error("--gb e --bloco-mb devem ser positivos")
    print(f"Destino: {Path(args.destino).resolve()}")
    print(f"Arquivo temporario: {args.gb:g} GB | bloco: {args.bloco_mb} MB")
    print("Gravando arquivo de teste...")
    lidos, duracao = testar(args.destino, args.gb, args.bloco_mb)
    print(f"Leitura: {formatar_mb(lidos / duracao)}")
    print(f"Tempo de leitura: {duracao:.2f} s")
    print("Arquivo temporario removido.")


if __name__ == "__main__":
    main()
