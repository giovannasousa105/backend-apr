from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from main import app


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_company(client: TestClient, name: str, email: str) -> str:
    response = client.post(
        "/companies",
        json={
            "name": name,
            "admin_email": email,
            "admin_password": "Senha1234",
            "admin_name": "Admin",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


def test_apr_mvp_crud_submit_and_tenant_isolation():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        token_a = _create_company(
            client,
            f"Empresa APR MVP {suffix}",
            f"apr.mvi.a.{suffix}@example.com",
        )
        token_b = _create_company(
            client,
            f"Empresa APR MVP Other {suffix}",
            f"apr.mvi.b.{suffix}@example.com",
        )

        created = client.post(
            "/aprs",
            headers=_auth(token_a),
            json={
                "title": "APR - Montagem Andaime",
                "location": "Obra A - Setor 2",
                "activity": "Montagem de andaime tubular",
                "hazards": [{"name": "queda de altura", "severity": 4, "prob": 3}],
                "controls": [{"type": "EPI", "name": "cinto paraquedista"}],
            },
        )
        assert created.status_code == 200, created.text
        apr_id = created.json()["id"]
        assert apr_id
        assert created.json()["status"] == "draft"

        listed = client.get("/aprs", headers=_auth(token_a))
        assert listed.status_code == 200, listed.text
        assert any(item["id"] == apr_id for item in listed.json())

        details = client.get(f"/aprs/{apr_id}", headers=_auth(token_a))
        assert details.status_code == 200, details.text
        assert details.json()["title"] == "APR - Montagem Andaime"

        updated = client.put(
            f"/aprs/{apr_id}",
            headers=_auth(token_a),
            json={
                "title": "APR - Montagem Andaime Atualizada",
                "activity": "Montagem e ajuste de andaime tubular",
            },
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["title"] == "APR - Montagem Andaime Atualizada"

        submitted = client.post(f"/aprs/{apr_id}/submit", headers=_auth(token_a))
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["status"] == "submitted"

        forbidden = client.get(f"/aprs/{apr_id}", headers=_auth(token_b))
        assert forbidden.status_code == 403, forbidden.text
