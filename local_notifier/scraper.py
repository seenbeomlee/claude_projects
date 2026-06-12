import json
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

STATE_FILE = Path(__file__).parent / "state.json"

BASE_URL = "https://e-learning.nhi.go.kr"
LOGIN_FORM_URL = f"{BASE_URL}/user/loginFrm.do"
LOGIN_URL = f"{BASE_URL}/sso/ssoControl.do"
MY_ROOM_URL = f"{BASE_URL}/myspace/myroom/myHomeStudyList.do"
STUDY_MAIN_URL = f"{BASE_URL}/study/main/setStudyMain.do"
NOTICE_URL = f"{BASE_URL}/study/announce/setAnnounceList.do"

LOGIN_ID = os.getenv("NARAEBAEUM_ID", "")
LOGIN_PW = os.getenv("NARAEBAEUM_PW", "")
COURSE_SESSION_ID = os.getenv("NARAEBAEUM_COURSE_ID", "")


def _load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"last_notice_ids": []}


def _save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
    })
    if LOGIN_ID and LOGIN_PW:
        login_page = session.get(LOGIN_FORM_URL, timeout=10)
        soup = BeautifulSoup(login_page.text, "html.parser")

        form_data = {
            "loginId": LOGIN_ID,
            "loginPwd": LOGIN_PW,
            "return_url": "/",
            "rtnUrl": "/",
            "grantType": "owner_password",
        }
        for hidden in soup.select("form input[type=hidden]"):
            name = hidden.get("name")
            value = hidden.get("value", "")
            if name and name not in form_data:
                form_data[name] = value

        session.post(LOGIN_URL, data=form_data, timeout=10, allow_redirects=True, headers={
            "Referer": LOGIN_FORM_URL,
            "Origin": BASE_URL,
        })
        session.get(BASE_URL, timeout=10)
    return session


def _parse_notices(session: requests.Session) -> list[dict]:
    # 브라우저와 동일한 탐색 순서: 나의 강의실 → 과정 메인 → 공지사항
    session.get(MY_ROOM_URL, timeout=10)
    session.post(STUDY_MAIN_URL, data={
        "sbjectSessId": COURSE_SESSION_ID,
        "clubId": "",
        "atnlcNo": "",
        "sbjectId": "",
        "cmd": "",
        "connYn": "",
        "crseSessId": "",
        "changeHistoryYn": "",
    }, timeout=10)

    resp = session.post(NOTICE_URL, data={"scCrseSeCd": ""}, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    for row in soup.select("div.tbl-type5 table tbody tr"):
        link = row.select_one("td.ta-left a")
        if not link:
            continue

        title = link.get_text(strip=True)
        onclick = link.get("onclick", "")
        m = re.search(r"onViewPage\('(\d+)'\)", onclick)
        if not m:
            continue
        post_id = m.group(1)

        tds = row.find_all("td")
        date = tds[3].get_text(strip=True) if len(tds) > 3 else ""

        items.append({
            "id": post_id,
            "title": title,
            "date": date,
        })

    return items


def get_recent_notices() -> list[dict]:
    if not (LOGIN_ID and LOGIN_PW and COURSE_SESSION_ID):
        return []
    session = _make_session()
    return _parse_notices(session)


def check_for_new_notices() -> list[dict]:
    if not (LOGIN_ID and LOGIN_PW and COURSE_SESSION_ID):
        return []

    state = _load_state()
    session = _make_session()
    notices = _parse_notices(session)
    current_ids = [n["id"] for n in notices]

    if not state["last_notice_ids"]:
        state["last_notice_ids"] = current_ids
        _save_state(state)
        return []

    new_items = [n for n in notices if n["id"] not in state["last_notice_ids"]]
    state["last_notice_ids"] = current_ids
    _save_state(state)
    return new_items


if __name__ == "__main__":
    notices = get_recent_notices()
    for n in notices:
        print(f"[{n['date']}] {n['title']}")
