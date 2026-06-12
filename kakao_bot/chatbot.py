import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

_KST = ZoneInfo("Asia/Seoul")

SCHEDULE_FILE = Path(__file__).parent / "schedule_data.json"

# (마감일, 항목명, 비고)
_DEADLINES = [
    ("2026-06-14", "봉사활동 결과보고서", "2점"),
    ("2026-06-21", "지방현장체험 운영계획서", "1점"),
    ("2026-06-22", "<사례1> 토의결과", "17:00까지 / 2점"),
    ("2026-06-23", "<사례1> 개인보고서", "4점"),
    ("2026-06-28", "팀별 실습계획서", ""),
    ("2026-06-29", "<사례2> 토의결과", "17:00까지 / 2점"),
    ("2026-07-01", "<사례2> 개인보고서", "4점"),
    ("2026-07-07", "<정책&법제> 1차보고서", ""),
    ("2026-07-15", "예산요구서 초안", ""),
    ("2026-07-19", "예산 발표자료", ""),
    ("2026-07-23", "정책 발표자료", ""),
    ("2026-07-26", "정책/법제/예산 최종 보고서", "정책10점, 법제6점, 예산4점+3점"),
    ("2026-08-23", "지방현장체험 결과보고서", "1점"),
    ("2026-09-07", "NHI TED 발표자료", ""),
]

_FACILITIES = """시설 이용시간

식당 (1층)
• 조식  07:30~08:00
• 중식  11:30~13:30
• 석식  17:30~18:30
(월 조식, 금 석식, 주말 미운영)

휘트니스룸 (기숙사 1층)
• 06:00~09:00
• 12:00~14:00
• 18:00~21:30

체력단련실 (기숙사 2층)
• 07:30~08:00
• 11:30~14:00
• 18:00~22:00

북카페 (기숙사 2층)
• 09:00~18:00

실내체육관
• 17:00~21:30

매점 (1층)
• 24시간

ATM (1층, 농협)
수건 수령: 주중 17:00~18:00 (1일 2장)"""

_CONTACTS = """비상연락처

의무실 (1층 107호)
• 09:00~18:00 (번호는 입소 시 안내)

기숙사 안내실
• 043-931-7501, 7503

운영진
• 문용준 팀장  043-931-6313
• 이도영 팀장  043-931-6320
• 김진석 주무관 043-931-6321
• 이민영 주무관 043-931-6322
• 홍유경 주무관 043-931-6330

야간 당직 (18:00~)
• 당직실  043-931-6062
• 방재실  043-931-7551
• 방호실  043-931-6064

응급
• 경찰  112
• 소방/응급  119
• 중앙제일병원 응급 (24시간)
• 덕산지구대  043-536-4112"""

_TRANSPORT = """교통 안내

셔틀버스
• 운행: 집합교육 시작/종료 시
• 노선: 오송역, 사당역
• 금요일 퇴소/월요일 입소 시 미운행

시외버스
• 충북혁신도시버스터미널
  (충북 음성군 맹동면 원중로 1363)

개인차량
• 2번째 집합교육부터 이용 가능
• 합숙기간 (5/26~6/5) 중 이용 불가
• 주차: A(태양광), B(체육관), C(기숙사동) 구역

주소 (택배)
충북 진천군 덕산읍 교학로 30
국가공무원인재개발원"""

_EVALUATION = """평가 배점 (100점 만점)

개인평가 (64점)
• 봉사활동 결과보고서  2점 (P/F)
• <사례1> 보고서 실습  4점 (P/F)
• <사례2> 보고서 실습  4점 (P/F)
• 역량실습             4점 (P/F)
• 개인보고서 평가     20점 (상대)
• 근무태도            30점 (기본 24점)

단체평가 (36점)
• 정책보고서          10점 (상대)
• 정책 최종발표        4점 (절대)
• 예산요구서           4점 (절대)
• 예산안 협의실습      3점 (절대)
• 예산 재원배분보고서  3점 (절대)
• 법제보고서           6점 (절대)
• 사례1,2 분임토의   각 2점 (P/F)
• 지방현장체험 운영/결과 각 1점 (P/F)

수료 기준
• 총점 60점 이상
• 결석 10일 미만"""

_RULES = """생활규정

귀원 시간
• 기본 23:00까지 복귀
• 23:00 이후 귀원 시 사전 신고 필요
  (당일 17시 전, 기숙사부장에게)

주요 감점 항목
• 무단결석/결강  0.5점/시간
• 미승인 결석    0.5점/시간
• 승인 후 결석   0.1점/시간
• 귀원시간 위반  0.5점/회
• 과제 지연제출  0.1점/회 (24시간 이내)
• 무단외박       1.2점/회

기숙사
• 음주·흡연·고성방가 금지
• 개인 전열기구 사용 금지
• 수건: 주중 17:00~18:00 수령 (1일 2장)
• WiFi: MAC 주소 사전 등록 필요"""


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


def format_deadlines(show_all: bool = False) -> str:
    today = datetime.now(_KST).date()
    upcoming = [
        (d, name, note)
        for d, name, note in _DEADLINES
        if date.fromisoformat(d) >= today
    ]

    if not upcoming:
        return "남은 제출 마감일이 없습니다."

    display = upcoming if show_all else upcoming[:5]
    lines = ["과제 마감일\n"]
    for d, name, note in display:
        dt = date.fromisoformat(d)
        diff = (dt - today).days
        if diff == 0:
            tag = "오늘!"
        elif diff == 1:
            tag = "내일!"
        elif diff <= 3:
            tag = f"D-{diff} ⚠️"
        else:
            tag = f"D-{diff}"
        note_str = f"  ({note})" if note else ""
        lines.append(f"• {dt.month}/{dt.day}  {name}{note_str}  [{tag}]")

    if not show_all and len(upcoming) > 5:
        lines.append(f"\n'전체 마감일'로 모두 조회 가능")
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

    # 일정 조회
    date_str = parse_date(utterance)
    if date_str:
        items = schedule.get(date_str)
        if items:
            return build_kakao_response(format_schedule(date_str, items))
        else:
            month, day = date_str[5:7].lstrip("0"), date_str[8:10].lstrip("0")
            return build_kakao_response(f"{month}월 {day}일 일정이 없습니다.")

    # 과제 마감일
    if any(k in utterance for k in ["마감", "제출", "과제", "보고서"]):
        show_all = any(k in utterance for k in ["전체", "모두", "다"])
        return build_kakao_response(format_deadlines(show_all))

    # 시설 이용시간
    if any(k in utterance for k in ["시설", "식당", "헬스", "휘트니스", "체육관", "카페", "매점", "ATM", "atm", "수건"]):
        return build_kakao_response(_FACILITIES)

    # 비상연락처
    if any(k in utterance for k in ["비상", "연락처", "의무실", "당직", "경찰", "소방", "운영진", "전화번호"]):
        return build_kakao_response(_CONTACTS)

    # 교통 안내
    if any(k in utterance for k in ["셔틀", "버스", "교통", "오송", "사당", "주차", "택배", "주소"]):
        return build_kakao_response(_TRANSPORT)

    # 평가 정보
    if any(k in utterance for k in ["평가", "배점", "점수", "수료", "성적"]):
        return build_kakao_response(_EVALUATION)

    # 생활규정
    if any(k in utterance for k in ["규정", "생활", "귀원", "결석", "감점", "외박", "수칙"]):
        return build_kakao_response(_RULES)

    # 일정 키워드 (날짜 없는 경우)
    if any(k in utterance for k in ["일정", "스케줄", "시간표"]):
        return build_kakao_response("날짜를 함께 말씀해 주세요.\n예) '6월 11일 일정'")

    # 도움말
    return build_kakao_response(
        "안녕하세요! 제71기 신임관리자과정 챗봇입니다.\n\n"
        "📅 일정 조회\n'오늘 일정', '6월 12일 일정'\n\n"
        "📋 과제 마감일\n'마감일', '전체 마감일'\n\n"
        "🏢 시설 이용시간\n'식당 시간', '헬스장 시간'\n\n"
        "📞 비상연락처\n'연락처', '의무실'\n\n"
        "🚌 교통 안내\n'셔틀버스', '오송역'\n\n"
        "📊 평가 정보\n'평가 배점', '수료 기준'\n\n"
        "📖 생활규정\n'귀원 시간', '감점 기준'"
    )
