import os

import httpx

BASE = os.getenv("API_BASE", "http://127.0.0.1:8000/api")


def login(client, email):
    response = client.post("/auth/login", json={"email": email, "password": "demo123"})
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


with httpx.Client(base_url=BASE, timeout=60) as client:
    author = login(client, "author@demo.ru")
    student = login(client, "student@demo.ru")

    created = client.post(
        "/instructions",
        headers=author,
        json={
            "title": "Тест петли",
            "summary": "Проверка обратной связи",
            "category_id": 1,
            "difficulty": "easy",
            "minutes": 5,
            "tags": ["тест"],
            "steps": [
                {"title": "Шаг один", "body": "Старый текст"},
                {"title": "Шаг два", "body": "Второй текст"},
            ],
        },
    ).raise_for_status().json()
    iid = created["id"]
    client.post(f"/instructions/{iid}/publish", headers=author).raise_for_status()

    step = created["steps"][0]
    comment = client.post(
        f"/instructions/{iid}/comments",
        headers=student,
        json={
            "body": "Добавьте фото",
            "step_id": step["id"],
            "kind": "suggestion",
            "suggested_body": "Новый текст с фото",
        },
    ).raise_for_status().json()

    accepted = client.post(f"/comments/{comment['id']}/accept", headers=author)
    accepted.raise_for_status()
    print("accepted:", accepted.json()["accepted_at"] is not None)

    versions = client.get(f"/instructions/{iid}/versions").raise_for_status().json()
    print("versions after accept:", len(versions), versions[0]["number"])

    notifications = client.get("/me/notifications", headers=student).raise_for_status().json()
    print("student notifications:", len(notifications), notifications[0]["type"])

    client.post(
        "/events",
        headers={**student, "X-Session-Id": "loop-test"},
        json={"type": "instruction_start", "instruction_id": iid},
    ).raise_for_status()
    client.post(
        "/events",
        headers={**student, "X-Session-Id": "loop-test"},
        json={"type": "step_stuck", "instruction_id": iid, "step_id": step["id"]},
    ).raise_for_status()
    analytics = client.get(f"/instructions/{iid}/analytics", headers=author).raise_for_status().json()
    print("stuck count:", analytics["steps"][0]["stuck"])

    coach = client.post(
        f"/instructions/{iid}/ai-coach",
        headers=author,
        json={"step_id": step["id"]},
    ).raise_for_status().json()
    print("coach keys:", sorted(coach.keys()))

    applied = client.post(
        f"/instructions/{iid}/ai-coach/apply",
        headers=author,
        json={"step_id": step["id"], "body": coach["rewrite"], "message": "ИИ-правка"},
    ).raise_for_status()
    versions = client.get(f"/instructions/{iid}/versions").raise_for_status().json()
    print("versions after coach:", len(versions))

    client.post(
        f"/instructions/{iid}/versions/{versions[-1]['id']}/rollback",
        headers=author,
    ).raise_for_status()
    versions = client.get(f"/instructions/{iid}/versions").raise_for_status().json()
    print("versions after rollback:", len(versions))

    client.delete(f"/instructions/{iid}", headers=author).raise_for_status()
    print("loop ok")
