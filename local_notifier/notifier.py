import subprocess


def send_notification(title: str) -> None:
    script = f'display notification "{title}" with title "나라배움터 공지사항"'
    subprocess.run(["osascript", "-e", script])
