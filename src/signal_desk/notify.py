"""알림 전달(텔레그램) — in-app 알림을 폰으로 능동 푸시. 시그널 변동·봇 체결·악재 감지 등.

키는 .env(TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID, 콤마로 여러 채팅). 키 없으면 조용히 no-op
(in-app 알림은 그대로). 표준 라이브러리(urllib)만 사용.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from signal_desk import config

log = logging.getLogger("signal_desk.notify")

_TIMEOUT = 10


def available() -> bool:
    return bool(config.telegram_token() and config.telegram_chat_ids())


def push(text: str) -> bool:
    """텔레그램으로 메시지 전송(설정된 모든 채팅). 성공 1건 이상이면 True. 미설정/실패 시 False(그레이스풀)."""
    tok = config.telegram_token()
    chats = config.telegram_chat_ids()
    text = (text or "").strip()
    if not tok or not chats or not text:
        return False
    ok = False
    for chat in chats:
        body = json.dumps({"chat_id": chat, "text": text[:4000],
                           "disable_web_page_preview": True}).encode("utf-8")
        req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage",
                                     data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT):
                ok = True
        except urllib.error.HTTPError as e:
            log.warning("텔레그램 전송 실패: HTTP %s", e.code)
        except Exception as e:
            log.warning("텔레그램 전송 실패: %s", type(e).__name__)
    return ok
