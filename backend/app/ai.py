import asyncio
import json
import re

import httpx

from .config import AI_API_KEY, AI_BASE_URL, AI_FALLBACK_MODELS, AI_MODEL


def auth_headers():
    return {
        "Authorization": f"Bearer {AI_API_KEY}",
        "HTTP-Referer": "http://185.202.207.229:8011",
        "X-Title": "Taskills",
    }


def clean_json(text: str) -> str:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    decoder = json.JSONDecoder()
    found = []
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[index:])
        except Exception:
            continue
        if isinstance(obj, dict):
            found.append(obj)
    if found:
        return json.dumps(found[-1], ensure_ascii=False)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return text


def extract_json(text: str, keys: tuple = ()):
    decoder = json.JSONDecoder()
    for index, char in enumerate(text or ""):
        if char != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[index:])
        except Exception:
            continue
        if isinstance(obj, dict) and (not keys or all(key in obj for key in keys)):
            return obj
    return None


async def chat(prompt: str, system: str = "", json_mode: bool = False, require_keys: tuple = ()):
    if not AI_API_KEY:
        return None
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    models = [AI_MODEL]
    for name in AI_FALLBACK_MODELS.split(","):
        name = name.strip()
        if name and name not in models:
            models.append(name)

    async with httpx.AsyncClient(timeout=60) as client:
        for model in models:
            for use_json in ([True, False] if json_mode else [False]):
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.4,
                    "max_tokens": 2000,
                }
                if use_json:
                    payload["response_format"] = {"type": "json_object"}
                for attempt in range(3):
                    try:
                        response = await client.post(
                            f"{AI_BASE_URL}/chat/completions",
                            headers=auth_headers(),
                            json=payload,
                        )
                        response.raise_for_status()
                        message = response.json()["choices"][0]["message"]
                        text = message.get("content") or message.get("reasoning")
                        if json_mode:
                            try:
                                if not extract_json(text or "", require_keys):
                                    break
                            except Exception:
                                break
                        return text
                    except httpx.HTTPStatusError as error:
                        if error.response.status_code in (429, 500, 502, 503) and attempt < 2:
                            await asyncio.sleep(1.5 * (attempt + 1))
                            continue
                        break
                    except Exception:
                        break
    return None


def fallback_instruction(goal: str, audience: str = "", level: str = ""):
    title = goal.strip().rstrip(".").capitalize() or "Новая инструкция"
    steps = [
        {
            "title": "Подготовьте всё необходимое",
            "body": "Соберите документы, доступы и инструменты, которые понадобятся для задачи.",
        },
        {
            "title": "Изучите требования",
            "body": "Проверьте условия, сроки и список того, что нужно получить в итоге.",
        },
        {
            "title": "Выполните основной этап",
            "body": "Действуйте по порядку и отмечайте каждый выполненный пункт.",
        },
        {
            "title": "Проверьте результат",
            "body": "Сверьтесь с требованиями и убедитесь, что всё готово.",
        },
        {
            "title": "Сохраните подтверждение",
            "body": "Сделайте копию документа или скриншот результата на случай вопросов.",
        },
    ]
    summary = f"Пошаговая инструкция: {goal.strip().rstrip('.')}."
    if audience:
        summary += f" Для: {audience}."
    return {"title": title, "summary": summary, "steps": steps, "ai": False}


async def generate_instruction(goal: str, audience: str = "", level: str = ""):
    system = (
        "Ты редактор пошаговых инструкций на русском языке. "
        "Возвращай только JSON без пояснений."
    )
    prompt = (
        f"Задача: {goal}\n"
        f"Аудитория: {audience or 'новички'}\n"
        f"Уровень: {level or 'начальный'}\n\n"
        "Сделай 5-6 шагов. Формат JSON:\n"
        '{"title": "название", "summary": "краткое описание", '
        '"steps": [{"title": "шаг", "body": "1-2 предложения"}]}'
    )
    raw = await chat(prompt, system, json_mode=True, require_keys=("title", "steps"))
    if not raw:
        return fallback_instruction(goal, audience, level)
    data = extract_json(raw, ("title", "steps"))
    if not data:
        return fallback_instruction(goal, audience, level)
    steps = [
        {"title": str(step["title"]), "body": str(step.get("body", ""))}
        for step in data.get("steps", [])
        if step.get("title")
    ]
    if not steps:
        return fallback_instruction(goal, audience, level)
    return {
        "title": str(data.get("title") or goal).strip(),
        "summary": str(data.get("summary") or "").strip(),
        "steps": steps,
        "ai": True,
    }


async def improve_text(text: str):
    system = "Ты редактор инструкций. Пиши коротко, понятно и по делу. Верни только улучшенный текст."
    prompt = f"Улучши этот шаг инструкции:\n\n{text}"
    raw = await chat(prompt, system)
    if not raw:
        return {"text": text, "ai": False}
    return {"text": raw.strip(), "ai": True}


async def suggest_tags(title: str, summary: str = ""):
    system = "Ты подбираешь теги для инструкций. Верни только JSON."
    prompt = (
        f"Название: {title}\nОписание: {summary}\n\n"
        'Верни {"tags": ["тег1", "тег2", "тег3"]}. Теги на русском, 1-2 слова.'
    )
    raw = await chat(prompt, system, json_mode=True, require_keys=("tags",))
    if raw:
        data = extract_json(raw, ("tags",))
        if data:
            tags = [str(tag).strip().lower() for tag in data.get("tags", []) if str(tag).strip()]
            if tags:
                return {"tags": tags[:6], "ai": True}
    words = [word.lower().strip(".,!?") for word in re.findall(r"[А-Яа-яЁёA-Za-z0-9-]{4,}", title)]
    stop = {"как", "для", "или", "это", "свой", "своими", "нужно", "можно", "инструкция"}
    tags = []
    for word in words:
        if word not in stop and word not in tags:
            tags.append(word)
    return {"tags": tags[:3], "ai": False}
