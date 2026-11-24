import os

import httpx

BASE = os.getenv("API_BASE", "http://127.0.0.1:8000/api")


def login(client, email, password="demo123"):
    response = client.post("/auth/login", json={"email": email, "password": password})
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


with httpx.Client(base_url=BASE, timeout=60) as client:
    owner = login(client, "qqqiy7829@gmail.com", os.getenv("OWNER_PASSWORD", "Owner2026!"))
    me = client.get("/auth/me", headers=owner).raise_for_status().json()
    print("owner role:", me["role"])

    stats = client.get("/admin/stats", headers=owner).raise_for_status().json()
    print("stats:", stats)
    users = client.get("/admin/users", headers=owner).raise_for_status().json()
    print("users:", len(users))

    student_id = next(user["id"] for user in users if user["email"] == "student@demo.ru")
    changed = client.post(f"/admin/users/{student_id}/role", headers=owner, json={"role": "admin"}).raise_for_status().json()
    print("granted:", changed["role"])
    client.post(f"/admin/users/{student_id}/role", headers=owner, json={"role": "student"}).raise_for_status()

    categories = client.get("/forum/categories").raise_for_status().json()
    print("categories:", len(categories))
    topic = client.post("/forum/topics", headers=owner, json={
        "title": "Тестовая тема форума",
        "body": "Первое сообщение",
        "category_id": categories[0]["id"],
        "instruction_id": 1,
    }).raise_for_status().json()
    topic_id = topic["id"]
    posted = client.post(f"/forum/topics/{topic_id}/posts", headers=owner, json={"body": "Ответ"}).raise_for_status().json()
    print("posts:", posted["posts_count"])
    client.post(f"/forum/topics/{topic_id}/close", headers=owner).raise_for_status()
    related = client.get("/forum/instructions/1/topics").raise_for_status().json()
    print("related topics:", len(related["items"]))

    report = client.post("/admin/reports", headers=owner, json={
        "target_type": "instruction", "target_id": 1, "reason": "тест"
    }).raise_for_status().json()
    resolved = client.post(f"/admin/reports/{report['id']}/resolve", headers=owner).raise_for_status().json()
    print("report status:", resolved["status"])

    print("admin+forum ok")
