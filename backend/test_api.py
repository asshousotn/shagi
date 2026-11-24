import os
import sys

import httpx

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.getenv("API_BASE", "http://127.0.0.1:8000/api")
SID = "api-test-session"


def client():
    return httpx.Client(base_url=BASE, headers={"X-Session-Id": SID}, timeout=30)


def login(c, email):
    response = c.post("/auth/login", json={"email": email, "password": "demo123"})
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


with client() as c:
    author = login(c, "author@demo.ru")
    student = login(c, "student@demo.ru")
    expert = login(c, "expert@demo.ru")

    payload = {
        "title": "Тестовая инструкция",
        "summary": "Проверка API",
        "category_id": 1,
        "difficulty": "easy",
        "minutes": 5,
        "tags": ["тест", "api"],
        "steps": [
            {"title": "Первый шаг", "body": "Тело первого шага"},
            {"title": "Второй шаг", "body": "Тело второго шага"},
            {"title": "Третий шаг", "body": "Тело третьего шага"},
        ],
    }
    created = c.post("/instructions", json=payload, headers=author)
    created.raise_for_status()
    item = created.json()
    iid = item["id"]
    assert item["status"] == "draft"
    assert len(item["steps"]) == 3
    assert item["tags"][0]["name"] == "тест"
    print("create: ok", iid)

    first_step_id = item["steps"][0]["id"]
    update = {
        **payload,
        "title": "Тестовая инструкция обновлённая",
        "steps": [
            {"id": first_step_id, "title": "Первый шаг изменён", "body": "Новое тело"},
            {"title": "Новый второй шаг", "body": "Новое тело 2"},
        ],
    }
    updated = c.patch(f"/instructions/{iid}", json=update, headers=author)
    updated.raise_for_status()
    item = updated.json()
    assert len(item["steps"]) == 2
    assert item["steps"][0]["title"] == "Первый шаг изменён"
    print("update steps: ok")

    c.post(f"/instructions/{iid}/publish", headers=author).raise_for_status()
    published = c.get(f"/instructions/{iid}").json()
    assert published["status"] == "published"
    found = c.get("/instructions", params={"q": "тестовая обновлённая"}).json()
    assert any(row["id"] == iid for row in found["items"])
    print("publish + search: ok")

    fork_response = c.post(f"/instructions/{iid}/fork", headers=student)
    fork_response.raise_for_status()
    fork = fork_response.json()
    assert fork["forked_from_id"] == iid
    assert fork["author"]["id"] != published["author"]["id"]
    print("fork: ok", fork["id"])

    verified = c.post(f"/instructions/{iid}/verify", headers=expert)
    verified.raise_for_status()
    assert verified.json()["verified_at"]
    print("verify: ok")

    rating = c.post(f"/instructions/{iid}/rating", json={"score": 5}, headers=student)
    rating.raise_for_status()
    assert rating.json()["my_rating"] == 5
    reaction = c.post(
        "/reactions",
        json={"target_type": "instruction", "target_id": iid, "value": 1},
        headers=student,
    )
    reaction.raise_for_status()
    assert reaction.json()["likes"] >= 1
    bookmark = c.post(f"/instructions/{iid}/bookmark", headers=student)
    bookmark.raise_for_status()
    assert bookmark.json()["bookmarked"] is True
    comment = c.post(
        f"/instructions/{iid}/comments",
        json={"body": "Тестовый комментарий", "step_id": item["steps"][0]["id"], "kind": "suggestion"},
        headers=student,
    )
    comment.raise_for_status()
    comments = c.get(f"/instructions/{iid}/comments").json()
    assert any(row["body"] == "Тестовый комментарий" for row in comments)
    print("rating + reaction + bookmark + comment: ok")

    for event_type, step_id in [
        ("instruction_start", None),
        ("step_view", item["steps"][0]["id"]),
        ("step_complete", item["steps"][0]["id"]),
        ("step_view", item["steps"][1]["id"]),
        ("step_complete", item["steps"][1]["id"]),
        ("instruction_complete", None),
    ]:
        response = c.post(
            "/events",
            json={
                "type": event_type,
                "instruction_id": iid,
                "step_id": step_id,
                "duration_ms": 1000,
            },
            headers=student,
        )
        response.raise_for_status()
    progress = c.get(f"/progress/{iid}", headers=student).json()
    assert progress["finished"] is True
    assert progress["completed_count"] == 2
    my_progress = c.get("/me/progress", headers=student).json()
    assert any(row["instruction_id"] == iid for row in my_progress["items"])
    print("events + progress: ok")

    analytics = c.get(f"/instructions/{iid}/analytics", headers=author)
    analytics.raise_for_status()
    data = analytics.json()
    assert data["starts"] >= 1
    assert len(data["steps"]) == 2
    print("analytics: ok", data["starts"], data["completion_rate"])

    delete_original = c.delete(f"/instructions/{iid}", headers=author)
    delete_original.raise_for_status()
    delete_fork = c.delete(f"/instructions/{fork['id']}", headers=student)
    delete_fork.raise_for_status()
    assert c.get(f"/instructions/{iid}").status_code == 404
    print("delete: ok")

print("all api tests passed")
