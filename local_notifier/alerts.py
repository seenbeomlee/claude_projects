import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from notifier import send_notification

_KST = ZoneInfo("Asia/Seoul")
SCHEDULE_FILE = Path(__file__).parent.parent / "kakao_bot" / "schedule_data.json"
STATE_FILE = Path(__file__).parent / "state.json"

_DEADLINES = [
    ("2026-06-14", "봉사활동 결과보고서", "2점"),
    ("2026-06-21", "지방현장체험 운영계획서", "1점"),
    ("2026-06-22", "<사례1> 토의결과", "17:00까지"),
    ("2026-06-23", "<사례1> 개인보고서", "4점"),
    ("2026-06-28", "팀별 실습계획서", ""),
    ("2026-06-29", "<사례2> 토의결과", "17:00까지"),
    ("2026-07-01", "<사례2> 개인보고서", "4점"),
    ("2026-07-07", "<정책&법제> 1차보고서", ""),
    ("2026-07-15", "예산요구서 초안", ""),
    ("2026-07-19", "예산 발표자료", ""),
    ("2026-07-23", "정책 발표자료", ""),
    ("2026-07-26", "정책/법제/예산 최종 보고서", ""),
    ("2026-08-23", "지방현장체험 결과보고서", "1점"),
    ("2026-09-07", "NHI TED 발표자료", ""),
]


def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    with open(STATE_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _load_schedule() -> dict:
    if not SCHEDULE_FILE.exists():
        return {}
    with open(SCHEDULE_FILE, encoding="utf-8") as f:
        return json.load(f)


def _today() -> date:
    return datetime.now(_KST).date()


def _now() -> datetime:
    return datetime.now(_KST)


# ── B-1: 과제 마감 임박 알림 ─────────────────────────────────────────────────

def check_deadline_alerts() -> None:
    today = _today()
    state = _load_state()
    alerted: list[str] = state.get("alerted_deadlines", [])
    changed = False

    for deadline_str, name, note in _DEADLINES:
        deadline = date.fromisoformat(deadline_str)
        diff = (deadline - today).days

        for trigger_day, label in [(3, "D-3"), (1, "D-1"), (0, "오늘 마감!")]:
            if diff != trigger_day:
                continue
            key = f"{deadline_str}_{label}"
            if key in alerted:
                continue

            note_str = f" ({note})" if note else ""
            if diff == 0:
                body = f"오늘 마감: {name}{note_str}"
            else:
                body = f"{label} | {name}{note_str} → {deadline.month}/{deadline.day}"
            send_notification(body, title="📋 과제 마감 알림")
            print(f"[마감 알림] {body}")
            alerted.append(key)
            changed = True

    if changed:
        state["alerted_deadlines"] = alerted
        _save_state(state)


# ── B-2: 오늘 일정 아침 알림 ─────────────────────────────────────────────────

def check_morning_schedule() -> None:
    now = _now()
    # 08:00~08:59 사이에 하루 한 번만 발송
    if now.hour != 8:
        return

    today = _today()
    today_str = today.isoformat()
    state = _load_state()

    if state.get("last_morning_alert") == today_str:
        return

    schedule = _load_schedule()
    items = schedule.get(today_str, [])

    # 중식·석식·교육준비·일일정리 제외, 실제 강의·일정만 추출
    skip = {"중식", "석식", "교육준비", "일일정리", "조식"}
    lectures = [
        item["title"]
        for item in items
        if not any(s in item["title"] for s in skip)
    ]

    if not lectures:
        body = "오늘은 일정이 없습니다."
    else:
        # 최대 4개까지만 표시
        preview = lectures[:4]
        if len(lectures) > 4:
            preview.append(f"외 {len(lectures) - 4}건")
        body = "\n".join(f"• {t}" for t in preview)

    send_notification(body, title=f"📅 {today.month}/{today.day} 오늘 일정")
    print(f"[아침 일정 알림] {today_str}: {', '.join(lectures[:3])}")

    state["last_morning_alert"] = today_str
    _save_state(state)


# ── B-3: 귀원 시간 알림 ──────────────────────────────────────────────────────

def _is_dormitory_night(date_str: str, schedule: dict) -> bool:
    """집합교육 숙박일 여부 (석식 제공 = 숙박)"""
    items = schedule.get(date_str, [])
    return any("석식" in item.get("title", "") for item in items)


def check_return_reminder() -> None:
    now = _now()
    # 22:20~22:59 사이에 하루 한 번만 발송
    if not (now.hour == 22 and now.minute >= 20):
        return

    today = _today()
    today_str = today.isoformat()
    state = _load_state()

    if state.get("last_return_reminder") == today_str:
        return

    schedule = _load_schedule()
    if not _is_dormitory_night(today_str, schedule):
        return

    send_notification("귀원 마감까지 40분 남았습니다 (23:00)", title="🏠 귀원 시간 알림")
    print(f"[귀원 알림] {today_str} 22:xx 귀원 리마인더 발송")

    state["last_return_reminder"] = today_str
    _save_state(state)


# ── 전체 실행 ────────────────────────────────────────────────────────────────

def run_all_checks() -> None:
    check_deadline_alerts()
    check_morning_schedule()
    check_return_reminder()
