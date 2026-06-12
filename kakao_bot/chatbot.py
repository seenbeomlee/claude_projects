import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

_KST = ZoneInfo("Asia/Seoul")

SCHEDULE_FILE = Path(__file__).parent / "schedule_data.json"


def load_schedule() -> dict:
    if not SCHEDULE_FILE.exists():
        return {}
    with open(SCHEDULE_FILE, encoding="utf-8") as f:
        return json.load(f)


def parse_date(utterance: str) -> str | None:
    today = datetime.now(_KST).date()

    if "오늘" in utterance:
        return today.isoformat()
    if "내일" in utterance:
        return (today + timedelta(days=1)).isoformat()
    if "모레" in utterance:
        return (today + timedelta(days=2)).isoformat()

    m = re.search(r"(\d{1,2})월\s*(\d{1,2})일", utterance)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        try:
            return date(today.year, month, day).isoformat()
        except ValueError:
            return None

    m = re.search(r"(\d{1,2})/(\d{1,2})", utterance)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        try:
            return date(today.year, month, day).isoformat()
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

    if any(k in utterance for k in ["일정", "스케줄", "시간표"]):
        return build_kakao_response(
            "날짜를 함께 말씀해 주세요.\n예) '6월 11일 일정'"
        )

    return build_kakao_response(
        "안녕하세요! 일정을 조회할 수 있습니다.\n\n📅 일정 조회\n예) '오늘 일정', '6월 12일 일정'"
    )
