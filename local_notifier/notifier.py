import subprocess


def send_notification(body: str, title: str = "나라배움터 공지사항") -> None:
    safe_body = body.replace('"', "'")
    safe_title = title.replace('"', "'")
    script = f'display notification "{safe_body}" with title "{safe_title}"'
    subprocess.run(["osascript", "-e", script])
