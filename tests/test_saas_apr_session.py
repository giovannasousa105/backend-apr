from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from main import app


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


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_apr_status_flow_and_tenant_isolation():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        admin_token = _create_company(
            client,
            name=f"Empresa Status {suffix}",
            email=f"admin.status.{suffix}@example.com",
        )
        apr_create = client.post(
            "/v1/aprs",
            headers=_auth_header(admin_token),
            json={
                "worksite": "Obra A",
                "sector": "Setor A",
                "responsible": "Resp A",
                "date": "2026-02-20",
                "activity_id": "ATV-1",
                "activity_name": "Atividade A",
                "titulo": "APR A",
                "risco": "medio",
                "descricao": "Descricao A",
            },
        )
        assert apr_create.status_code == 200, apr_create.text
        apr_id = apr_create.json()["id"]

        sent = client.patch(
            f"/v1/aprs/{apr_id}/status",
            headers=_auth_header(admin_token),
            json={"status": "enviado"},
        )
        assert sent.status_code == 200, sent.text
        assert sent.json()["status"] == "enviado"

        approved = client.patch(
            f"/v1/aprs/{apr_id}/status",
            headers=_auth_header(admin_token),
            json={"status": "aprovado"},
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == "aprovado"

        invalid_back = client.patch(
            f"/v1/aprs/{apr_id}/status",
            headers=_auth_header(admin_token),
            json={"status": "rascunho"},
        )
        assert invalid_back.status_code == 400, invalid_back.text
        assert invalid_back.json().get("code") == "invalid_status_transition"

        history = client.get(f"/v1/aprs/{apr_id}/history", headers=_auth_header(admin_token))
        assert history.status_code == 200, history.text
        events = history.json()
        status_events = [e for e in events if e["event"] == "status_changed"]
        assert status_events, events
        actor = (status_events[-1].get("payload") or {}).get("actor")
        assert actor and actor.get("email"), status_events[-1]

        other_company_token = _create_company(
            client,
            name=f"Empresa Other {suffix}",
            email=f"admin.other.{suffix}@example.com",
        )
        forbidden = client.get(f"/v1/aprs/{apr_id}", headers=_auth_header(other_company_token))
        assert forbidden.status_code == 403, forbidden.text


def test_session_expiration_and_refresh(monkeypatch):
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        monkeypatch.setenv("SESSION_TTL_MINUTES", "-1")
        expired_token = _create_company(
            client,
            name=f"Empresa Session {suffix}",
            email=f"admin.session.{suffix}@example.com",
        )

        me_expired = client.get("/auth/me", headers=_auth_header(expired_token))
        assert me_expired.status_code == 401, me_expired.text
        assert me_expired.json().get("code") == "token_expired"

        monkeypatch.setenv("SESSION_TTL_MINUTES", "60")
        refreshed = client.post("/auth/refresh", headers=_auth_header(expired_token))
        assert refreshed.status_code == 200, refreshed.text
        new_token = refreshed.json()["token"]

        me_ok = client.get("/auth/me", headers=_auth_header(new_token))
        assert me_ok.status_code == 200, me_ok.text
