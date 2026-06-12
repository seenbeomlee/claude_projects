import time
from datetime import datetime

from alerts import run_all_checks
from notifier import send_notification
from scraper import check_for_new_notices

INTERVAL_MINUTES = 15


def run() -> None:
    print(f"[모니터링 시작] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[{INTERVAL_MINUTES}분 간격으로 나라배움터 공지사항 및 일정 알림을 확인합니다]")

    while True:
        ts = datetime.now().strftime('%H:%M:%S')
        try:
            # 공지사항 체크
            new_notices = check_for_new_notices()
            if new_notices:
                print(f"[{ts}] 신규 공지 {len(new_notices)}건 발견")
                for notice in new_notices:
                    print(f"  - [{notice['date']}] {notice['title']}")
                    send_notification(notice["title"])
            else:
                print(f"[{ts}] 신규 공지 없음")
        except Exception as e:
            print(f"[{ts}] 공지 확인 오류: {e}")

        try:
            # 마감 알림 / 아침 일정 / 귀원 알림
            run_all_checks()
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 알림 체크 오류: {e}")

        time.sleep(INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    run()
