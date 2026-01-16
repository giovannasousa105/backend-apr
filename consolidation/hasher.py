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


def gerar_hashes_origem(
    caminho_atividades: str,
    caminho_epis: str,
    caminho_perigos: str
) -> Dict[str, str]:
    """
    Gera hashes SHA-256 dos 3 Excels de origem.
    """
    return {
        "atividades_passos_excel": gerar_hash_arquivo(caminho_atividades),
        "epis_excel": gerar_hash_arquivo(caminho_epis),
        "perigos_excel": gerar_hash_arquivo(caminho_perigos),
    }
