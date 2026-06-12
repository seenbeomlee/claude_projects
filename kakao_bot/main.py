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


@app.get("/debug/notice")
async def debug_notice():
    import os
    import traceback
    import requests
    from bs4 import BeautifulSoup

    login_id = os.getenv("NARAEBAEUM_ID", "")
    login_pw = os.getenv("NARAEBAEUM_PW", "")

    if not login_id or not login_pw:
        return {"error": "환경변수 미설정", "NARAEBAEUM_ID": bool(login_id), "NARAEBAEUM_PW": bool(login_pw)}

    try:
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0"})

        login_page = session.get("https://e-learning.nhi.go.kr/sso/ssoControl.do", timeout=15)
        login_soup = BeautifulSoup(login_page.text, "html.parser")
        form_data = {
            "loginId": login_id,
            "loginPwd": login_pw,
            "return_url": "/",
            "rtnUrl": "/",
            "grantType": "owner_password",
        }
        for hidden in login_soup.select("form input[type=hidden]"):
            name = hidden.get("name")
            value = hidden.get("value", "")
            if name and name not in form_data:
                form_data[name] = value

        login_resp = session.post(
            "https://e-learning.nhi.go.kr/sso/ssoControl.do",
            data=form_data,
            timeout=15,
            allow_redirects=True,
        )

        notice_resp = session.post(
            "https://e-learning.nhi.go.kr/study/announce/setAnnounceList.do",
            data={},
            timeout=15,
        )

        soup = BeautifulSoup(notice_resp.text, "html.parser")
        title = soup.title.string.strip() if soup.title else "없음"
        rows = soup.select("div.tbl-type5 table tbody tr td.ta-left")

        return {
            "login_status": login_resp.status_code,
            "login_url_final": str(login_resp.url),
            "hidden_fields_sent": [k for k in form_data if k not in ("loginId", "loginPwd")],
            "notice_status": notice_resp.status_code,
            "page_title": title,
            "logged_in": "로그인" not in title,
            "notice_count": len(rows),
            "first_notice": rows[0].get_text(strip=True) if rows else None,
            "notice_html_snippet": notice_resp.text[500:1000],
        }
    except Exception:
        return {"error": traceback.format_exc()}


@app.post("/webhook/kakao")
async def kakao_webhook(request: Request):
    body = await request.json()
    response = handle_webhook(body)
    return JSONResponse(content=response)
