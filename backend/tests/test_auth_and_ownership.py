from __future__ import annotations


def test_register_login_and_me(temp_app_settings) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        register_response = client.post(
            "/auth/register",
            json={"email": "learner@example.com", "password": "password123", "full_name": "Learner"},
        )
        assert register_response.status_code == 200
        token = register_response.json()["access_token"]

        login_response = client.post(
            "/auth/login",
            json={"email": "learner@example.com", "password": "password123"},
        )
        assert login_response.status_code == 200

        me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "learner@example.com"


def test_documents_are_scoped_to_current_user(temp_app_settings) -> None:
    from fastapi.testclient import TestClient

    from app import database
    from app.main import app
    from app.services.auth import create_access_token, hash_password

    user_a = database.create_user(email="a@example.com", password_hash=hash_password("password123"))
    user_b = database.create_user(email="b@example.com", password_hash=hash_password("password123"))
    database.create_document("doc-a", "a.pdf", temp_app_settings / "a.pdf", owner_id=user_a["id"])
    database.create_document("doc-b", "b.pdf", temp_app_settings / "b.pdf", owner_id=user_b["id"])

    with TestClient(app) as client:
        response = client.get("/documents", headers={"Authorization": f"Bearer {create_access_token(user_a)}"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["doc-a"]
