import base64
import os

import httpx

BASE = os.getenv("API_BASE", "http://185.202.207.229:8010/api")
png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==")

with httpx.Client(base_url=BASE, timeout=60) as client:
    token = client.post("/auth/login", json={"email": "student@demo.ru", "password": "demo123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    uploaded = client.post("/uploads", headers=headers, files={"file": ("tiny.png", png, "image/png")}).raise_for_status().json()
    comment = client.post("/instructions/1/comments", headers=headers, json={"body": "Комментарий с картинкой"}).raise_for_status().json()
    client.post("/attachments", headers=headers, json={
        "target_type": "comment", "target_id": comment["id"], "url": uploaded["url"]
    }).raise_for_status()
    comments = client.get("/instructions/1/comments").raise_for_status().json()
    found = next(item for item in comments if item["id"] == comment["id"])
    print("comment images:", len(found["images"]))
    print("comment image url:", found["images"][0]["url"])
    client.delete(f"/comments/{comment['id']}", headers=headers).raise_for_status()
    print("ok")
