from datetime import date
import os

from fastapi.testclient import TestClient
from sqlalchemy import select

from database import SessionLocal
from main import app
from models import User


ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "integration@example.com")


def _get_admin_token() -> str:
    db = SessionLocal()
    try:
        user = db.execute(select(User).where(User.email == ADMIN_EMAIL)).scalar_one_or_none()
        if not user:
            raise AssertionError("Admin user not seeded")
        return user.api_token
    finally:
        db.close()


def test_risk_score_invalid_blocks_finalize():
    with TestClient(app) as client:
        headers = {"X-API-Token": _get_admin_token()}

        apr_payload = {
            "worksite": "Obra Teste",
            "sector": "Setor Teste",
            "responsible": "Engenheiro Responsável",
            "date": date.today().isoformat(),
            "activity_id": "act-integration",
            "activity_name": "Integração de Riscos",
            "titulo": "APR fluxo teste",
            "risco": "Testes de integração",
            "descricao": "Validando bloqueio do risk_score_invalid",
        }
        apr_resp = client.post("/v1/aprs", json=apr_payload, headers=headers)
        assert apr_resp.status_code == 200
        apr_id = apr_resp.json()["id"]

        step_payload = {
            "ordem": 1,
            "descricao": "Etapa com duas fontes de perigo",
            "perigos": (
                "Queda em diferença de nível abaixo de 1,80 m; "
                "Queda em diferença de nível acima de 1,80 m"
            ),
            "riscos": "Lesões graves e fraturas",
            "medidas_controle": "Sinalizar, delimitar área e usar coleira",
            "epis": "Capacete; Cinturão",
            "normas": "NR-6",
        }
        step_resp = client.post(
            f"/v1/aprs/{apr_id}/passos", json=step_payload, headers=headers
        )
        assert step_resp.status_code == 200

        finalize_payload = {"responsible_confirm": "Engenheiro Responsável"}
        finalize_resp = client.post(
            f"/v1/aprs/{apr_id}/finalize",
            json=finalize_payload,
            headers=headers,
        )
        assert finalize_resp.status_code == 400
        assert finalize_resp.json()["code"] == "risk_score_invalid"

        apr_detail = client.get(f"/v1/aprs/{apr_id}", headers=headers)
        risk_items = apr_detail.json()["risk_items"]
        invalid_item = next(
            (item for item in risk_items if item["risk_level"] == "invalid"), None
        )
        assert invalid_item, "Deve existir ao menos um risco com nível inválido"

        patch_resp = client.patch(
            f"/v1/aprs/{apr_id}/risk-items/{invalid_item['id']}",
            json={"probability": 3, "severity": 3},
            headers=headers,
        )
        assert patch_resp.status_code == 200
        updated_item = patch_resp.json()
        assert updated_item["risk_level"] == "medio"

        finalize_again = client.post(
            f"/v1/aprs/{apr_id}/finalize",
            json=finalize_payload,
            headers=headers,
        )
        assert finalize_again.status_code == 400
        assert finalize_again.json()["code"] == "risk_score_invalid"
