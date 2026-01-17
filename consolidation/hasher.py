import hashlib
from typing import Dict


# ==============================
# HASHER AUDITÁVEL (SHA-256)
# ==============================

def gerar_hash_arquivo(caminho_arquivo: str) -> str:
    """
    Gera hash SHA-256 de um arquivo.
    Usado para auditoria e rastreabilidade.
    """
    sha256 = hashlib.sha256()

    with open(caminho_arquivo, "rb") as f:
        for bloco in iter(lambda: f.read(8192), b""):
            sha256.update(bloco)

    return sha256.hexdigest()


import hashlib

def _hash_arquivo(caminho: str) -> str:
    sha = hashlib.sha256()
    with open(caminho, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()


def gerar_hashes_origem(
    caminho_epis: str,
    caminho_perigos: str,
    prompt_ai: str | None = None,
):
    hashes = {
        "epis": _hash_arquivo(caminho_epis),
        "perigos": _hash_arquivo(caminho_perigos),
    }

    if prompt_ai:
        hashes["prompt_ai"] = hashlib.sha256(
            prompt_ai.encode("utf-8")
        ).hexdigest()

    return hashes
