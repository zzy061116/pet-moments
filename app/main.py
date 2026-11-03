"""宠物朋友圈 —— FastAPI 入口。

启动：uvicorn app.main:app --reload
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db, llm, seed, service
from .config import MODE, MODEL, UPLOAD_DIR, WEB_DIR

MAX_UPLOAD = 8 * 1024 * 1024
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="宠物朋友圈", lifespan=lifespan)


class PetIn(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    species: str = Field(default="猫", max_length=20)
    age: str = Field(default="", max_length=20)
    traits: str = Field(default="", max_length=120)


class PostIn(BaseModel):
    event: str = Field(min_length=1, max_length=300)
    photo: str = Field(default="", max_length=300)


@app.get("/api/state")
async def state() -> dict:
    pet = db.get_pet()
    return {
        "mode": MODE,
        "pet": pet,
        "posts": db.list_posts(),
        "stats": db.stats(),
    }


@app.post("/api/pet")
async def create_pet(payload: PetIn) -> dict:
    # 建新宠物 = 从头开始，避免上一只的动态串到新宠物名下
    if db.get_pet():
        db.reset_all()

    persona = await service.build_persona(
        payload.name.strip(),
        payload.species.strip(),
        payload.age.strip(),
        payload.traits.strip(),
    )
    pet = db.save_pet(
        payload.name.strip(),
        payload.species.strip(),
        payload.age.strip(),
        persona,
    )
    return {"pet": pet, "persona": persona}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="只支持 jpg / png / webp / gif")
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(status_code=400, detail="图片不要超过 8MB")
    name = f"{uuid.uuid4().hex}{suffix}"
    (UPLOAD_DIR / name).write_bytes(data)
    return {"url": f"/uploads/{name}"}


@app.post("/api/post")
async def create_post(payload: PostIn) -> dict:
    pet = db.get_pet()
    if not pet:
        raise HTTPException(status_code=400, detail="先创建宠物")

    recent = [p["caption"] for p in db.list_posts(limit=4)]
    streak, bonus = db.touch_streak()
    result = await service.build_post(pet, payload.event.strip(), streak, recent)
    exp_gain = 12 + bonus

    post = db.add_post(
        caption=result["caption"],
        mood=result["mood"],
        event=payload.event.strip(),
        photo=payload.photo,
        comments=result["comments"],
        likes=result["likes"],
        exp_gain=exp_gain,
    )
    return {
        "post": post,
        "pet": db.get_pet(),
        "stats": db.stats(),
        "exp_gain": exp_gain,
        "offline": result.get("offline", False),
        "now": datetime.now().isoformat(timespec="seconds"),
    }


@app.post("/api/demo")
async def load_demo() -> dict:
    seed.load_demo()
    return await state()


@app.post("/api/reset")
async def reset() -> dict:
    db.reset_all()
    return await state()


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "mode": MODE,
        "model": MODEL,
        "has_pet": db.get_pet() is not None,
        # 最近一次调模型的失败原因，排查"填了 key 但文案没变"用
        "llm_error": llm.last_error(),
    }


app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")
