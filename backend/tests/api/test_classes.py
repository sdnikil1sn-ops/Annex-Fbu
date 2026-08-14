"""API tests for the v1 classes endpoints (Phase 17)."""

from __future__ import annotations

from uuid import uuid4

from app.application.services.class_service import ClassService
from app.infrastructure.repositories.mock_class_repository import MockClassRepository
from app.main import create_app
from fastapi.testclient import TestClient


def _headers() -> dict[str, str]:
    """Headers authenticating as the fixed test identity."""
    return {"Authorization": "Bearer test-token"}


def _teacher_id(token_verifier) -> str:
    """The uid behind the fixed ``test-token`` (the class teacher)."""
    return str(token_verifier._identities["test-token"].uid)  # type: ignore[attr-defined]


def _add_student(token_verifier, uid):
    """Register a second identity under ``student-token``; returns the uid."""
    from app.application.ports.auth import VerifiedIdentity

    token_verifier._identities["student-token"] = VerifiedIdentity(  # type: ignore[attr-defined]
        uid=uid, email="bob@example.com", display_name="Bob"
    )
    return uid


def _student_headers() -> dict[str, str]:
    return {"Authorization": "Bearer student-token"}


def _build(settings, token_verifier, user_service):
    """An app with mock auth + the mock-backed class service."""
    repository = MockClassRepository()
    repository.seed_lesson(
        uuid4(), "spotting-misinformation", "Spotting Misinformation"
    )
    repository.seed_lesson(uuid4(), "analyzing-claims", "Analyzing Claims")
    class_service = ClassService(repository)
    app = create_app(
        settings,
        token_verifier=token_verifier,
        user_service=user_service,
        class_service=class_service,
    )
    return app, repository


def test_create_class_requires_token(settings, token_verifier, user_service) -> None:
    """A missing bearer token yields a 401 envelope."""
    app, _ = _build(settings, token_verifier, user_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/v1/classes", json={"name": "Media Literacy 101"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth.missing_token"


def test_create_class_returns_class_with_invite_code(
    settings, token_verifier, user_service
) -> None:
    """Creating a class returns its detail including the invite code."""
    app, _ = _build(settings, token_verifier, user_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/classes",
            headers=_headers(),
            json={"name": "Media Literacy 101", "description": "Spring cohort"},
        )
    assert response.status_code == 201
    payload = response.json()["data"]
    assert payload["name"] == "Media Literacy 101"
    assert payload["role"] == "teacher"
    assert len(payload["invite_code"]) == 8
    assert payload["owner_id"]


def test_create_class_validates_name(settings, token_verifier, user_service) -> None:
    """An empty name is rejected by the API boundary."""
    app, _ = _build(settings, token_verifier, user_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/classes", headers=_headers(), json={"name": ""}
        )
    assert response.status_code == 422


def test_teacher_and_student_flow(settings, token_verifier, user_service) -> None:
    """The full lifecycle: create → assign → progress for the teacher."""
    app, repository = _build(settings, token_verifier, user_service)
    assert _teacher_id(token_verifier)
    with TestClient(app, raise_server_exceptions=False) as client:
        created = client.post(
            "/api/v1/classes",
            headers=_headers(),
            json={"name": "Media Literacy 101"},
        )
        class_id = created.json()["data"]["id"]

        # The teacher sees the class with role teacher.
        listing = client.get("/api/v1/classes", headers=_headers())
        assert listing.status_code == 200
        assert listing.json()["data"][0]["role"] == "teacher"

        # The teacher assigns the seeded lesson by slug.
        assigned = client.post(
            f"/api/v1/classes/{class_id}/assignments",
            headers=_headers(),
            json={"lesson_ref": "spotting-misinformation"},
        )
        assert assigned.status_code == 201
        assignment = assigned.json()["data"]
        assert assignment["lesson_slug"] == "spotting-misinformation"

        # Re-assigning is idempotent.
        again = client.post(
            f"/api/v1/classes/{class_id}/assignments",
            headers=_headers(),
            json={"lesson_ref": "spotting-misinformation"},
        )
        assert again.json()["data"]["id"] == assignment["id"]

        # An unknown lesson yields lesson.not_found.
        missing = client.post(
            f"/api/v1/classes/{class_id}/assignments",
            headers=_headers(),
            json={"lesson_ref": "no-such-lesson"},
        )
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "lesson.not_found"

        # Progress for the empty class reports no students.
        progress = client.get(f"/api/v1/classes/{class_id}/progress", headers=_headers())
        assert progress.status_code == 200
        assert progress.json()["data"][0]["students"] == []


def test_join_class_with_invite_code(settings, token_verifier, user_service) -> None:
    """A student joins by invite code and sees the class as student."""
    app, repository = _build(settings, token_verifier, user_service)
    student_uid = _add_student(token_verifier, uuid4())
    teacher_uid = _teacher_id(token_verifier)
    with TestClient(app, raise_server_exceptions=False) as client:
        created = client.post(
            "/api/v1/classes",
            headers=_headers(),
            json={"name": "Media Literacy 101"},
        )
        class_id = created.json()["data"]["id"]
        invite_code = created.json()["data"]["invite_code"]

        joined = client.post(
            f"/api/v1/classes/{class_id}/join",
            headers=_student_headers(),
            json={"invite_code": invite_code},
        )
        assert joined.status_code == 200
        assert joined.json()["data"]["role"] == "student"

        # The student lists the class and sees the roster.
        listing = client.get("/api/v1/classes", headers=_student_headers())
        assert [item["id"] for item in listing.json()["data"]] == [class_id]

        detail = client.get(f"/api/v1/classes/{class_id}", headers=_student_headers())
        roles = {
            member["user_id"]: member["role"]
            for member in detail.json()["data"]["members"]
        }
        assert roles[str(student_uid)] == "student"
        assert roles[teacher_uid] == "teacher"


def test_join_class_wrong_invite_is_404(settings, token_verifier, user_service) -> None:
    """A wrong invite code (or a code for another class) yields 404."""
    app, _ = _build(settings, token_verifier, user_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        created = client.post(
            "/api/v1/classes", headers=_headers(), json={"name": "Media Literacy 101"}
        )
        class_id = created.json()["data"]["id"]

        wrong_code = client.post(
            f"/api/v1/classes/{class_id}/join",
            headers=_headers(),
            json={"invite_code": "ZZZZZZZZ"},
        )
        assert wrong_code.status_code == 404
        assert wrong_code.json()["error"]["code"] == "class.not_found"


def test_student_cannot_assign_or_read_progress(
    settings, token_verifier, user_service
) -> None:
    """Non-teachers get class.not_found on teacher-only routes."""
    app, repository = _build(settings, token_verifier, user_service)
    _add_student(token_verifier, uuid4())
    with TestClient(app, raise_server_exceptions=False) as client:
        created = client.post(
            "/api/v1/classes", headers=_headers(), json={"name": "Media Literacy 101"}
        )
        class_id = created.json()["data"]["id"]
        client.post(
            f"/api/v1/classes/{class_id}/join",
            headers={"Authorization": "Bearer student-token"},
            json={"invite_code": created.json()["data"]["invite_code"]},
        )

        assignment = client.post(
            f"/api/v1/classes/{class_id}/assignments",
            headers=_student_headers(),
            json={"lesson_ref": "spotting-misinformation"},
        )
        assert assignment.status_code == 404
        assert assignment.json()["error"]["code"] == "class.not_found"

        progress = client.get(
            f"/api/v1/classes/{class_id}/progress", headers=_student_headers()
        )
        assert progress.status_code == 404

        deleted = client.delete(f"/api/v1/classes/{class_id}", headers=_student_headers())
        assert deleted.status_code == 404


def test_teacher_progress_reflects_student_completion(
    settings, token_verifier, user_service
) -> None:
    """Completing a lesson surfaces in the teacher's progress report."""
    from uuid import UUID as Uuid

    app, repository = _build(settings, token_verifier, user_service)
    student_uid = _add_student(token_verifier, uuid4())
    with TestClient(app, raise_server_exceptions=False) as client:
        created = client.post(
            "/api/v1/classes", headers=_headers(), json={"name": "Media Literacy 101"}
        )
        class_id = created.json()["data"]["id"]
        client.post(
            f"/api/v1/classes/{class_id}/join",
            headers=_student_headers(),
            json={"invite_code": created.json()["data"]["invite_code"]},
        )
        assigned = client.post(
            f"/api/v1/classes/{class_id}/assignments",
            headers=_headers(),
            json={"lesson_ref": "spotting-misinformation"},
        )
        lesson_id = Uuid(assigned.json()["data"]["lesson_id"])
        repository.seed_completion(student_uid, uuid4())  # wrong lesson: no effect

        progress = client.get(f"/api/v1/classes/{class_id}/progress", headers=_headers())
        assert progress.status_code == 200
        students = progress.json()["data"][0]["students"]
        assert len(students) == 1
        assert students[0]["completed"] is False

        # Seed completion for the actual lesson id and re-read.
        repository.seed_completion(student_uid, lesson_id)
        progress = client.get(f"/api/v1/classes/{class_id}/progress", headers=_headers())
        assert progress.json()["data"][0]["students"][0]["completed"] is True
        assert progress.json()["data"][0]["assignment"]["completed_count"] == 1


def test_remove_member_and_delete_class(settings, token_verifier, user_service) -> None:
    """Teachers remove students; owners delete classes."""
    app, _ = _build(settings, token_verifier, user_service)
    student_uid = _add_student(token_verifier, uuid4())
    with TestClient(app, raise_server_exceptions=False) as client:
        created = client.post(
            "/api/v1/classes", headers=_headers(), json={"name": "Media Literacy 101"}
        )
        class_id = created.json()["data"]["id"]
        client.post(
            f"/api/v1/classes/{class_id}/join",
            headers={"Authorization": "Bearer student-token"},
            json={"invite_code": created.json()["data"]["invite_code"]},
        )

        removed = client.delete(
            f"/api/v1/classes/{class_id}/members/{student_uid}", headers=_headers()
        )
        assert removed.status_code == 200
        assert removed.json()["data"]["removed"] == str(student_uid)

        detail = client.get(f"/api/v1/classes/{class_id}", headers=_headers())
        assert str(student_uid) not in {
            member["user_id"] for member in detail.json()["data"]["members"]
        }

        deleted = client.delete(f"/api/v1/classes/{class_id}", headers=_headers())
        assert deleted.status_code == 200
        listing = client.get("/api/v1/classes", headers=_headers())
        assert listing.json()["data"] == []


def test_classes_not_configured_returns_503(authed_client: TestClient) -> None:
    """Without a wired class service, the endpoints answer 503."""
    response = authed_client.get("/api/v1/classes", headers=_headers())
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "classes.not_configured"
