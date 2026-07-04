"""미국 종목 한글 표기 — GICS 섹터(11종, 전량 매핑) + 주요 종목명(큐레이션, 나머지는 영문 유지).

토큰 절약: 요청마다 번역하지 않고 정적 사전으로 매핑한다. 전 500종목 한글명이 필요하면 1회
배치로 사전을 생성해 여기 NAME_KO에 채우면 된다(현재는 사용자가 자주 보는 대형주 위주 큐레이션)."""

from __future__ import annotations

GICS_KO = {
    "Information Technology": "정보기술", "Health Care": "헬스케어", "Financials": "금융",
    "Consumer Discretionary": "경기소비재", "Communication Services": "커뮤니케이션",
    "Industrials": "산업재", "Consumer Staples": "필수소비재", "Energy": "에너지",
    "Utilities": "유틸리티", "Real Estate": "부동산", "Materials": "소재",
}

NAME_KO = {
    "AAPL": "애플", "MSFT": "마이크로소프트", "NVDA": "엔비디아", "AMZN": "아마존",
    "GOOGL": "알파벳", "GOOG": "알파벳", "META": "메타", "TSLA": "테슬라", "AVGO": "브로드컴",
    "ORCL": "오라클", "NOW": "서비스나우", "PLTR": "팔란티어", "MU": "마이크론", "AMD": "AMD",
    "INTC": "인텔", "QCOM": "퀄컴", "TXN": "텍사스인스트루먼트", "CRM": "세일즈포스", "NFLX": "넷플릭스",
    "ADBE": "어도비", "CSCO": "시스코", "IBM": "IBM", "JPM": "JP모건", "BAC": "뱅크오브아메리카",
    "V": "비자", "MA": "마스터카드", "KO": "코카콜라", "PEP": "펩시코", "PG": "P&G",
    "JNJ": "존슨앤드존슨", "PFE": "화이자", "MRK": "머크", "LLY": "일라이릴리", "ABBV": "애브비",
    "XOM": "엑슨모빌", "CVX": "셰브론", "PSX": "필립스66", "WMT": "월마트", "HD": "홈디포",
    "DIS": "디즈니", "BA": "보잉", "CAT": "캐터필러", "GE": "GE", "UBER": "우버", "HAL": "핼리버튼",
    "COST": "코스트코", "MCD": "맥도날드", "NKE": "나이키", "SBUX": "스타벅스",
}


def sector_ko(gics: str | None) -> str:
    return GICS_KO.get(gics or "", gics or "-")


def name_ko(ticker: str, english: str) -> str:
    """한글명 있으면 '한글(TICKER)', 없으면 영문명 유지."""
    ko = NAME_KO.get(ticker)
    return f"{ko}({ticker})" if ko else english
