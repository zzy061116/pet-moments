"""业务编排：优先让大模型写，模型挂了/没配 key 就切离线引擎。

模型输出一律做字段校验，改过的名字、漏掉的字段、超长的句子都要兜住，
不让前端出现空文案或乱码评论。
"""

from __future__ import annotations

import random
from typing import Any

from . import offline
from .llm import chat_json
from .prompts import FRIENDS, PERSONA_SYSTEM, POST_SYSTEM, persona_user, post_user, relation_note

FRIEND_NAMES = [f["name"] for f in FRIENDS]


def _clean_str(value: Any, limit: int, default: str = "") -> str:
    if not isinstance(value, str):
        return default
    text = value.strip().replace("\n", " ")
    return text[:limit]


async def build_persona(
    name: str, species: str, age: str, traits: str
) -> dict[str, Any]:
    data = await chat_json(
        PERSONA_SYSTEM, persona_user(name, species, age, traits), temperature=0.9
    )
    if not data:
        return offline.make_persona(name, species, age, traits)

    tags = [
        _clean_str(t, 8)
        for t in (data.get("tags") or [])
        if isinstance(t, str) and t.strip()
    ][:3]
    persona = {
        "tags": tags or ["嘴硬心软", "贪吃", "半夜跑酷"],
        "nickname": _clean_str(data.get("nickname"), 6, "我"),
        "catchphrase": _clean_str(data.get("catchphrase"), 16, "这事跟我没关系"),
        "obsession": _clean_str(data.get("obsession"), 20, "凌晨三点在走廊冲刺"),
        "fear": _clean_str(data.get("fear"), 12, "吸尘器"),
        "tone": _clean_str(data.get("tone"), 40, "短句，爱用括号补充内心戏"),
        "voice_sample": _clean_str(data.get("voice_sample"), 80, ""),
        "offline": False,
    }
    if not persona["voice_sample"]:
        persona["voice_sample"] = f"{persona['catchphrase']}（这是{name}的说话方式）"
    return persona


async def build_post(
    pet: dict[str, Any], event: str, streak: int, recent: list[str]
) -> dict[str, Any]:
    data = await chat_json(
        POST_SYSTEM,
        post_user(pet, event, streak, recent, relation_note(streak)),
        temperature=1.0,
    )
    if not data:
        return offline.make_post(pet, event, streak, recent)

    caption = _clean_str(data.get("caption"), 160)
    if len(caption) < 6:
        return offline.make_post(pet, event, streak, recent)

    raw_comments = data.get("comments") or []
    texts: list[str] = []
    if isinstance(raw_comments, list):
        for item in raw_comments:
            if isinstance(item, dict):
                texts.append(_clean_str(item.get("text"), 40))
            else:
                texts.append(_clean_str(item, 40))
    texts = [t for t in texts if t]

    # 名字永远由后端决定，防止模型自己发明好友
    comments = []
    filler: dict[str, Any] = {}
    for i, friend in enumerate(FRIENDS):
        text = texts[i] if i < len(texts) else ""
        if not text:
            if not filler:
                filler = offline.make_post(pet, event, streak, recent)
            text = filler["comments"][i]["text"]
        comments.append({"friend": friend["name"], "text": text})

    raw_likes = data.get("likes")
    likes = [n for n in raw_likes if n in FRIEND_NAMES] if isinstance(raw_likes, list) else []
    if not likes:
        likes = random.sample(FRIEND_NAMES, 2)

    return {
        "caption": caption,
        "mood": _clean_str(data.get("mood"), 6, "平静"),
        "comments": comments,
        "likes": likes,
        "offline": False,
    }
