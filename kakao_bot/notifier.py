import os

from solapi import SolapiMessageService

_api_key = os.getenv("COOLSMS_API_KEY", "")
_api_secret = os.getenv("COOLSMS_API_SECRET", "")
_sender_key = os.getenv("KAKAO_SENDER_KEY", "")
_template_code = os.getenv("KAKAO_TEMPLATE_CODE", "")
_recipient = os.getenv("RECIPIENT_PHONE", "")
_sender = os.getenv("SENDER_PHONE", "")


def send_alimtalk(title: str, url: str) -> None:
    if not all([_api_key, _api_secret, _sender_key, _template_code, _recipient]):
        print(f"[알림톡 미발송 - 환경변수 미설정] {title}")
        return

    service = SolapiMessageService(api_key=_api_key, api_secret=_api_secret)
    service.send({
        "type": "ATA",
        "to": _recipient,
        "from": _sender,
        "kakaoOptions": {
            "senderKey": _sender_key,
            "templateCode": _template_code,
            "variables": {
                "#{제목}": title,
                "#{링크}": url,
            },
        },
    })
