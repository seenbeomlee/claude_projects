import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

_KST = ZoneInfo("Asia/Seoul")

from scraper import get_recent_notices

SCHEDULE_FILE = Path(__file__).parent / "schedule_data.json"


def load_schedule() -> dict:
    if not SCHEDULE_FILE.exists():
        return {}
    with open(SCHEDULE_FILE, encoding="utf-8") as f:
        return json.load(f)


def parse_date(utterance: str) -> str | None:
    """발화에서 날짜를 추출하여 YYYY-MM-DD 형식으로 반환."""
    today = datetime.now(_KST).date()

    if "오늘" in utterance:
        return today.isoformat()
    if "내일" in utterance:
        return (today + timedelta(days=1)).isoformat()
    if "모레" in utterance:
        return (today + timedelta(days=2)).isoformat()

    # "6월 11일", "6월11일" 패턴
    m = re.search(r"(\d{1,2})월\s*(\d{1,2})일", utterance)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        year = today.year
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None

    # "6/11", "06/11" 패턴
    m = re.search(r"(\d{1,2})/(\d{1,2})", utterance)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        year = today.year
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None

    return None


def format_schedule(date_str: str, items: list[dict]) -> str:
    month, day = date_str[5:7].lstrip("0"), date_str[8:10].lstrip("0")
    lines = [f"📅 {month}월 {day}일 일정\n"]
    for item in items:
        time = item.get("time", "")
        title = item.get("title", "")
        location = item.get("location", "")
        instructor = item.get("instructor", "")

        detail_parts = [p for p in [location, instructor] if p]
        detail = f" ({', '.join(detail_parts)})" if detail_parts else ""
        lines.append(f"• {time}  {title}{detail}")
    return "\n".join(lines)


def build_kakao_response(text: str) -> dict:
    return {
        "version": "2.0",
        "template": {
            "outputs": [
                {"simpleText": {"text": text}}
            ]
        }
    }


def handle_webhook(body: dict) -> dict:
    utterance: str = body.get("userRequest", {}).get("utterance", "")
    schedule = load_schedule()

    date_str = parse_date(utterance)

    if date_str:
        items = schedule.get(date_str)
        if items:
            return build_kakao_response(format_schedule(date_str, items))
        else:
            month, day = date_str[5:7].lstrip("0"), date_str[8:10].lstrip("0")
            return build_kakao_response(f"{month}월 {day}일 일정이 없습니다.")

    # 일정 관련 키워드가 있지만 날짜 파싱 실패
    if any(k in utterance for k in ["일정", "스케줄", "시간표"]):
        return build_kakao_response(
            "날짜를 함께 말씀해 주세요.\n예) '6월 11일 일정'"
        )

    # 공지사항 조회
    if any(k in utterance for k in ["공지", "공지사항"]):
        try:
            notices = get_recent_notices()
            if notices:
                lines = ["📢 최근 공지사항\n"]
                for n in notices[:5]:
                    lines.append(f"• [{n['date']}] {n['title']}")
                return build_kakao_response("\n".join(lines))
            else:
                return build_kakao_response("공지사항을 불러올 수 없습니다.\n(로그인 정보를 확인해 주세요)")
        except Exception as e:
            return build_kakao_response(f"공지사항 조회 중 오류가 발생했습니다.")

    return build_kakao_response(
        "안녕하세요! 아래 기능을 사용할 수 있습니다.\n\n📅 일정 조회\n예) '오늘 일정', '6월 12일 일정'\n\n📢 공지사항\n예) '공지사항'"
    )
