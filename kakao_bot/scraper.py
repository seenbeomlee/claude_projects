import json
import os
from pathlib import Path

import requests
from bs4 import BeautifulSoup

STATE_FILE = Path(__file__).parent / "state.json"

NOTICE_URL = os.getenv("NARAEBAEUM_NOTICE_URL", "")
MATERIAL_URL = os.getenv("NARAEBAEUM_MATERIAL_URL", "")
LOGIN_ID = os.getenv("NARAEBAEUM_ID", "")
LOGIN_PW = os.getenv("NARAEBAEUM_PW", "")

# 나라배움터 로그인 URL - 실제 확인 후 수정 필요
LOGIN_URL = "https://www.lms.go.kr/login"


def _load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"last_notice_ids": [], "last_material_ids": []}


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
        session.post(LOGIN_URL, data={"id": LOGIN_ID, "pw": LOGIN_PW}, timeout=10)
    return session


def _parse_board(session: requests.Session, url: str) -> list[dict]:
    """게시판 페이지에서 게시물 목록을 파싱. URL/HTML 구조에 맞게 수정 필요."""
    if not url:
        return []
    resp = session.get(url, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    # TODO: 실제 나라배움터 HTML 구조에 맞게 셀렉터 수정
    # 현재는 일반적인 게시판 패턴 (tr 기반)을 가정
    for row in soup.select("table tbody tr"):
        cols = row.find_all("td")
        if len(cols) < 2:
            continue
        link_tag = row.find("a")
        if not link_tag:
            continue
        post_id = link_tag.get("href", "") or cols[0].get_text(strip=True)
        title = link_tag.get_text(strip=True)
        items.append({"id": post_id, "title": title, "url": url})
    return items


def check_for_new_content() -> list[dict]:
    """신규 공지사항 및 강의교안 목록 반환."""
    state = _load_state()
    session = _make_session()

    new_items = []

    # 공지사항 확인
    notices = _parse_board(session, NOTICE_URL)
    current_ids = [n["id"] for n in notices]
    new_notice_ids = [i for i in current_ids if i not in state["last_notice_ids"]]
    for item in notices:
        if item["id"] in new_notice_ids:
            item["category"] = "공지사항"
            new_items.append(item)

    # 강의교안 확인
    materials = _parse_board(session, MATERIAL_URL)
    current_material_ids = [m["id"] for m in materials]
    new_material_ids = [i for i in current_material_ids if i not in state["last_material_ids"]]
    for item in materials:
        if item["id"] in new_material_ids:
            item["category"] = "강의교안"
            new_items.append(item)

    # 상태 업데이트 (최초 실행 시엔 현재 목록을 기준으로 초기화만)
    if not state["last_notice_ids"] and not state["last_material_ids"]:
        state["last_notice_ids"] = current_ids
        state["last_material_ids"] = current_material_ids
        _save_state(state)
        return []  # 최초 실행엔 알림 없음 (기준선 설정)

    state["last_notice_ids"] = current_ids
    state["last_material_ids"] = current_material_ids
    _save_state(state)
    return new_items


if __name__ == "__main__":
    items = check_for_new_content()
    if items:
        for item in items:
            print(f"[{item['category']}] {item['title']}")
    else:
        print("신규 콘텐츠 없음")
