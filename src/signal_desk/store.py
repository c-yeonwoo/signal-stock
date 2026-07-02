"""캐시 로더 — 2단계(수집기 도입) 전까지는 스텁.

Signal APT의 store.py는 KB 주간 시계열을 parquet로 캐싱해 반환한다. 여기서는 아직 수집기가
없으므로, 시세/시그널 캐시가 준비됐는지 여부만 판별한다. 실제 로딩 로직은 2단계에서 채운다.
"""

from __future__ import annotations

from pathlib import Path

CACHE_DIR = Path("data/cache")


def is_ready() -> bool:
    """시세/시그널 캐시가 아직 없음 — 2단계 전까지 항상 False."""
    return False
