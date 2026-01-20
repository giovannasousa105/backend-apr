from typing import Dict, List, Any
import pandas as pd
import re
import unicodedata


# ==================================================
# EXCEPTION
# ==================================================

class ValidationError(Exception):
    """Erro de validação técnica do documento."""
    pass


# ==================================================
# NORMALIZAÇÃO
# ==================================================

def _norm_colname(s: str) -> str:
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def _split_lista(valor) -> List[str]:
    if pd.isna(valor):
        return []
    if not isinstance(valor, str):
        valor = str(valor)
    partes = re.split(r"[;,]", valor)
    return [p.strip() for p in partes if p.strip()]


# ==================================================
# LOADER: EPIs
# ==================================================

def carregar_epis(caminho_arquivo: str) -> List[Dict[str, Any]]:
    df = pd.read_excel(caminho_arquivo)

    colunas = {_norm_colname(c): c for c in df.columns}

    if "id" not in colunas:
        raise ValidationError("Excel de EPIs precisa conter a coluna 'id'")

    epis = []

    for _, row in df.iterrows():
        epi_id = int(row[colunas["id"]])

        nome = None
        for campo in ["epi", "nome", "descricao"]:
            if campo in colunas and pd.notna(row[colunas[campo]]):
                nome = str(row[colunas[campo]]).strip()
                break

        tipo = None
        if "tipo" in colunas and pd.notna(row[colunas["tipo"]]):
            tipo = str(row[colunas["tipo"]]).strip()

        epis.append({
            "id": epi_id,
            "nome": nome or f"EPI {epi_id}",
            "tipo": tipo,
        })

    return epis


# ==================================================
# LOADER: PERIGOS
# ==================================================

def carregar_perigos(caminho_arquivo: str) -> List[Dict[str, Any]]:
    df = pd.read_excel(caminho_arquivo)

    colunas = {_norm_colname(c): c for c in df.columns}

    aliases = {
        "id": "id",
        "codigo": "id",

        "perigo": "perigo",
        "title": "perigo",
        "titulo": "perigo",
        "descricao": "perigo",

        "consequencias": "consequencias",
        "consequencia": "consequencias",

        "salvaguardas": "salvaguardas",
        "salvaguarda": "salvaguardas",
        "salva_guarda": "salvaguardas",
        "medidas": "salvaguardas",
        "controles": "salvaguardas",
        "medidas_de_controle": "salvaguardas",
    }

    def achar_coluna(padrao: str) -> str | None:
        for norm, original in colunas.items():
            if aliases.get(norm) == padrao:
                return original
        return None

    col_id = achar_coluna("id")
    if not col_id:
        raise ValidationError("Excel de perigos precisa conter a coluna 'id'")

    col_perigo = achar_coluna("perigo")
    col_conseq = achar_coluna("consequencias")
    col_salva = achar_coluna("salvaguardas")

    col_normas = colunas.get("normas")
    col_epi = colunas.get("epi")

    perigos = []

    for _, row in df.iterrows():
        perigo_id = int(row[col_id])

        perigo = (
            str(row[col_perigo]).strip()
            if col_perigo and pd.notna(row[col_perigo])
            else f"Perigo {perigo_id}"
        )

        consequencias = _split_lista(row[col_conseq]) if col_conseq else []
        salvaguardas = _split_lista(row[col_salva]) if col_salva else []

        if not salvaguardas:
            if col_normas and pd.notna(row[col_normas]):
                salvaguardas = _split_lista(row[col_normas])
            elif col_epi and pd.notna(row[col_epi]):
                salvaguardas = _split_lista(row[col_epi])

        perigos.append({
            "id": perigo_id,
            "perigo": perigo,
            "consequencias": consequencias,
            "salvaguardas": salvaguardas,
        })

    return perigos


# ==================================================
# VALIDATION
# ==================================================

def validar_documento(
    atividades: Dict[Any, Dict[str, Any]],
    epis: List[Dict[str, Any]],
    perigos: List[Dict[str, Any]],
):

    if not isinstance(atividades, dict) or not atividades:
        raise ValidationError("Nenhuma atividade válida encontrada")

    if not isinstance(epis, list):
        raise ValidationError("Cadastro de EPIs inválido")

    if not isinstance(perigos, list):
        raise ValidationError("Cadastro de perigos inválido")

    epis_index = _indexar_por_id(epis)
    perigos_index = _indexar_por_id(perigos)

    for atividade in atividades.values():
        atividade_id = atividade.get("atividade_id", "atividade_sem_id")
        _validar_atividade(
            atividade_id,
            atividade,
            epis_index,
            perigos_index,
        )


def _validar_atividade(
    atividade_id: str,
    atividade: Dict[str, Any],
    epis: Dict[int, Dict],
    perigos: Dict[int, Dict],
):
    passos = atividade.get("passos")

    if not isinstance(passos, list) or not passos:
        raise ValidationError(f"Atividade '{atividade_id}' não possui passos")

    ordens = []

    for passo in passos:
        _validar_passo(atividade_id, passo, epis, perigos)
        if isinstance(passo.get("ordem"), int):
            ordens.append(passo["ordem"])

    if ordens and sorted(ordens) != list(range(1, len(ordens) + 1)):
        raise ValidationError(f"Ordem dos passos inválida em '{atividade_id}'")


def _validar_passo(
    atividade_id: str,
    passo: Dict[str, Any],
    epis: Dict[int, Dict],
    perigos: Dict[int, Dict],
):
    ordem = passo.get("ordem")

    if not isinstance(ordem, int):
        raise ValidationError(f"Passo sem ordem válida em '{atividade_id}'")

    if not passo.get("descricao"):
        raise ValidationError(
            f"Descrição vazia no passo {ordem} da atividade '{atividade_id}'"
        )

    _validar_referencias(atividade_id, ordem, passo.get("epis", []), epis, "EPI")
    _validar_referencias(atividade_id, ordem, passo.get("perigos", []), perigos, "Perigo")


def _validar_referencias(
    atividade_id: str,
    ordem: int,
    referencias: List[Any],
    cadastro: Dict[int, Dict],
    tipo: str,
):
    if not isinstance(referencias, list):
        return

    if not cadastro:
        return  # 🔒 ignora validação se cadastro não existe

    for ref in referencias:
        try:
            ref_id = int(ref)
        except (ValueError, TypeError):
            raise ValidationError(
                f"{tipo} inválido '{ref}' no passo {ordem} da atividade '{atividade_id}'"
            )

        if ref_id not in cadastro:
            raise ValidationError(
                f"{tipo} ID {ref_id} não encontrado "
                f"(passo {ordem}, atividade '{atividade_id}')"
            )


def _indexar_por_id(lista: List[Dict[str, Any]]) -> Dict[int, Dict]:
    index = {}
    for item in lista:
        try:
            index[int(item["id"])] = item
        except Exception:
            continue
    return index
