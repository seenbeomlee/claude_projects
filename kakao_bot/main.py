from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from chatbot import handle_webhook
from notifier import send_alimtalk
from scraper import check_for_new_content


async def monitor_job() -> None:
    try:
        new_items = check_for_new_content()
        for item in new_items:
            send_alimtalk(
                title=f"[{item['category']}] {item['title']}",
                url=item.get("url", ""),
            )
    except Exception as e:
        print(f"[모니터링 오류] {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
    scheduler.add_job(monitor_job, "interval", minutes=15, id="monitor")
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="나라배움터 챗봇", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook/kakao")
async def kakao_webhook(request: Request):
    body = await request.json()
    response = handle_webhook(body)
    return JSONResponse(content=response)
