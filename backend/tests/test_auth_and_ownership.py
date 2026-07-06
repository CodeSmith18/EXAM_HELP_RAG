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

        duplicate_response = client.post(
            "/auth/register",
            json={"email": "learner@example.com", "password": "password123"},
        )
        assert duplicate_response.status_code == 409


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


def test_user_cannot_delete_another_users_document(temp_app_settings) -> None:
    from fastapi.testclient import TestClient

    from app import database
    from app.main import app
    from app.services.auth import create_access_token, hash_password

    user_a = database.create_user(email="owner@example.com", password_hash=hash_password("password123"))
    user_b = database.create_user(email="other@example.com", password_hash=hash_password("password123"))
    database.create_document("doc-a", "a.pdf", temp_app_settings / "a.pdf", owner_id=user_a["id"])

    with TestClient(app) as client:
        response = client.delete("/documents/doc-a", headers={"Authorization": f"Bearer {create_access_token(user_b)}"})

    assert response.status_code == 404
    assert database.get_document("doc-a", owner_id=user_a["id"]) is not None


def test_study_sessions_are_owned_and_deletable(temp_app_settings) -> None:
    from fastapi.testclient import TestClient

    from app import database
    from app.main import app
    from app.services.auth import create_access_token, hash_password

    user = database.create_user(email="study@example.com", password_hash=hash_password("password123"))
    session = database.create_study_session(
        owner_id=user["id"],
        topic="Cell division",
        include_diagram=True,
        document_ids=[],
        response={
            "topic": "Cell division",
            "simple_explanation": "Cells divide.",
            "key_points": [],
            "example": None,
            "important_terms": [],
            "quick_revision_summary": "Cells divide.",
            "mermaid_diagram": None,
            "sources": [],
        },
    )
    headers = {"Authorization": f"Bearer {create_access_token(user)}"}

    with TestClient(app) as client:
        list_response = client.get("/study-sessions", headers=headers)
        detail_response = client.get(f"/study-sessions/{session['id']}", headers=headers)
        delete_response = client.delete(f"/study-sessions/{session['id']}", headers=headers)
        missing_response = client.get(f"/study-sessions/{session['id']}", headers=headers)

    assert list_response.status_code == 200
    assert list_response.json()[0]["topic"] == "Cell division"
    assert detail_response.status_code == 200
    assert delete_response.status_code == 200
    assert delete_response.json() == {"deleted": True}
    assert missing_response.status_code == 404
