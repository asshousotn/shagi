import os

import httpx

BASE = os.getenv("API_BASE", "http://127.0.0.1:8000/api")

with httpx.Client(base_url=BASE, timeout=60) as client:
    token = client.post("/auth/login", json={"email": "author@demo.ru", "password": "demo123"}).json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    item = client.post("/instructions", headers=auth, json={
        "title": "Проверка картинок",
        "summary": "test",
        "category_id": 1,
        "images": ["/uploads/cover.png"],
        "steps": [{"title": "Шаг", "body": "Текст", "images": ["/uploads/step.png"]}]
    }).raise_for_status().json()
    client.post(f"/instructions/{item['id']}/publish", headers=auth).raise_for_status()
    detail = client.get(f"/instructions/{item['id']}").raise_for_status().json()
    print("instruction images:", len(detail["images"]))
    print("step images:", len(detail["steps"][0]["images"]))

    categories = client.get("/forum/categories").raise_for_status().json()
    topic = client.post("/forum/topics", headers=auth, json={
        "title": "Тема с картинками",
        "body": "Вопрос",
        "category_id": categories[0]["id"],
        "images": ["/uploads/topic.png"]
    }).raise_for_status().json()
    print("topic images:", len(topic["images"]))

    post = client.post(f"/forum/topics/{topic['id']}/posts", headers=auth, json={
        "body": "Ответ", "images": ["/uploads/post.png"]
    }).raise_for_status().json()
    first_post = post["posts"][0]
    print("post images:", len(first_post["images"]))

    reply = client.post(f"/forum/topics/{topic['id']}/posts", headers=auth, json={
        "body": "Вложенный ответ", "parent_id": first_post["id"]
    }).raise_for_status().json()
    print("nested parent:", reply["posts"][1]["parent_id"] == first_post["id"])

    solved = client.post(f"/forum/posts/{first_post['id']}/solution", headers=auth).raise_for_status().json()
    print("solution:", solved["posts"][0]["is_solution"], solved["solved_at"] is not None)

    edited = client.patch(f"/forum/posts/{first_post['id']}", headers=auth, json={"body": "Изменено"}).raise_for_status().json()
    print("edited:", edited["posts"][0]["body"])

    reaction = client.post("/reactions", headers=auth, json={"target_type": "post", "target_id": first_post["id"], "value": 1}).raise_for_status().json()
    print("reaction:", reaction["likes"])

    client.delete(f"/instructions/{item['id']}", headers=auth).raise_for_status()
    print("images+forum ok")
