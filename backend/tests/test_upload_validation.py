from __future__ import annotations


def test_upload_rejects_pdf_extension_with_invalid_signature(temp_app_settings) -> None:
    from fastapi.testclient import TestClient

    from app import database
    from app.main import app

    with TestClient(app) as client:
        response = client.post(
            "/upload-pdf",
            files=[("files", ("notes.pdf", b"this is not a pdf", "application/pdf"))],
        )

    assert response.status_code == 400
    assert "valid PDF" in response.json()["detail"]
    assert database.list_documents() == []


def test_upload_rejects_duplicate_file_names(temp_app_settings) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    pdf_bytes = b"%PDF-1.4\n%%EOF"
    with TestClient(app) as client:
        response = client.post(
            "/upload-pdf",
            files=[
                ("files", ("notes.pdf", pdf_bytes, "application/pdf")),
                ("files", ("notes.pdf", pdf_bytes, "application/pdf")),
            ],
        )

    assert response.status_code == 400
    assert "selected more than once" in response.json()["detail"]
