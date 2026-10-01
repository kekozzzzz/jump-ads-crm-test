import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()  # must run before importing app.bot, which reads BOT_TOKEN at import time

from aiogram.types import Update
from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import db
from app.bot import bot, dp

WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")  # e.g. https://your-app.onrender.com/telegram/webhook


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    if bot and WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL)
    yield
    if bot:
        await bot.session.close()


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")


@app.get("/")
def index(request: Request, tag: str | None = None):
    leads = db.list_leads(tag_filter=tag)
    tags = db.all_tags()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "leads": leads, "tags": tags, "current_tag": tag},
    )


@app.post("/leads")
def add_lead(name: str = Form(...), contact: str = Form(...), request_text: str = Form(..., alias="request")):
    db.create_lead(name=name, contact=contact, request=request_text, source="manual")
    return RedirectResponse(url="/", status_code=303)


@app.post("/leads/{lead_id}/tags")
def add_tag(lead_id: int, tag_name: str = Form(...)):
    db.add_tag_to_lead(lead_id, tag_name)
    return RedirectResponse(url="/", status_code=303)


@app.post("/leads/{lead_id}/tags/{tag_id}/delete")
def delete_tag(lead_id: int, tag_id: int):
    db.remove_tag_from_lead(lead_id, tag_id)
    return RedirectResponse(url="/", status_code=303)


@app.post("/telegram/webhook")
async def telegram_webhook(update: dict):
    if bot:
        aiogram_update = Update.model_validate(update)
        await dp.feed_update(bot, aiogram_update)
    return {"ok": True}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
