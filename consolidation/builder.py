from typing import Dict, List
from datetime import datetime
import hashlib
import json


# ==============================
# BUILDER DO DOCUMENTO CANÔNICO
# ==============================

def construir_documento(
    atividades: Dict,
    epis: Dict[int, Dict],
    perigos: Dict[int, Dict],
    hashes: Dict[str, str],
) -> Dict:
    """
    Constrói o JSON técnico canônico da APR,
    pronto para PDF, IA e auditoria.
    """

    documentos = []

    for atividade_id, atividade in atividades.items():
        documento = _construir_documento_atividade(
            atividade=atividade,
            epis=epis,
            perigos=perigos,
            hashes=hashes
        )
        documentos.append(documento)

    return {
        "tipo_documento": "APR",
        "versao_modelo": "1.0",
        "gerado_em": datetime.utcnow().isoformat() + "Z",
        "documentos": documentos
    }


# ==============================
# CONSTRUÇÃO POR ATIVIDADE
# ==============================

def _construir_documento_atividade(
    atividade: Dict,
    epis: Dict[int, Dict],
    perigos: Dict[int, Dict],
    hashes: Dict[str, str],
) -> Dict:

    passos_consolidados = []

    for passo in sorted(atividade["passos"], key=lambda p: p["ordem"]):
        passos_consolidados.append(
            _construir_passo(passo, epis, perigos)
        )

    normas_base = _coletar_normas_base(passos_consolidados)

    documento = {
        "apr": {
            "atividade_id": atividade["atividade_id"],
            "atividade": atividade["atividade"],
            "local": atividade["local"],
            "funcao": atividade["funcao"],
            "normas_base": normas_base
        },
        "passos": passos_consolidados,
        "audit": {
            "hashes_origem": hashes,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "origem": "excel_validado"
        }
    }

    return documento


# ==============================
# CONSTRUÇÃO DE PASSOS
# ==============================

def _construir_passo(
    passo: Dict,
    epis: Dict[int, Dict],
    perigos: Dict[int, Dict]
) -> Dict:

    perigos_consolidados = []
    for perigo_id in passo.get("perigos", []):
        perigo_id = int(perigo_id)
        perigo = perigos[perigo_id]
        perigos_consolidados.append(perigo)

    epis_consolidados = []
    for epi_id in passo.get("epis", []):
        epi_id = int(epi_id)
        epi = epis[epi_id]
        epis_consolidados.append(epi)

    return {
        "ordem": passo["ordem"],
        "descricao": passo["descricao"],
        "perigos": perigos_consolidados,
        "riscos": passo.get("riscos", []),
        "medidas_controle": passo.get("medidas_controle", []),
        "epis": epis_consolidados,
        "normas": passo.get("normas", [])
    }


# ==============================
# FUNÇÕES AUXILIARES
# ==============================

def _coletar_normas_base(passos: List[Dict]) -> List[str]:
    normas = set()

    for passo in passos:
        for norma in passo.get("normas", []):
            normas.add(norma)

        for epi in passo.get("epis", []):
            for norma in epi.get("normas", []):
                normas.add(norma)

    return sorted(list(normas))
