import json
import os
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

STATE_FILE = Path(__file__).parent / "state.json"

BASE_URL = "https://e-learning.nhi.go.kr"
LOGIN_URL = f"{BASE_URL}/sso/ssoControl.do"
NOTICE_URL = f"{BASE_URL}/study/announce/setAnnounceList.do"

LOGIN_ID = os.getenv("NARAEBAEUM_ID", "")
LOGIN_PW = os.getenv("NARAEBAEUM_PW", "")


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
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
    })
    if LOGIN_ID and LOGIN_PW:
        session.post(LOGIN_URL, data={
            "loginId": LOGIN_ID,
            "loginPwd": LOGIN_PW,
        }, timeout=10)
    return session


def _parse_notices(session: requests.Session) -> list[dict]:
    resp = session.post(NOTICE_URL, data={}, timeout=10)
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
    """최근 공지사항 목록 반환."""
    if not (LOGIN_ID and LOGIN_PW):
        return []
    session = _make_session()
    return _parse_notices(session)


def check_for_new_content() -> list[dict]:
    """신규 공지사항 목록 반환."""
    if not (LOGIN_ID and LOGIN_PW):
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
