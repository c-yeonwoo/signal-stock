"""섹터별 밸류체인(업스트림→미드스트림→다운스트림) 대표기업 큐레이션 — 국내(코스피)/해외(나스닥).

투자 판단을 위한 "산업 구조 지도" 참고자료다. 종목은 각 단계의 대표성 기준으로 큐레이션했고
(전수/추천 아님), 국내는 티커를 달아 시그널 탭과 연결할 수 있게 했다. 해외는 라벨(티커)만.
사이클 탭의 국면별 주도 섹터(reference/cycle.py)와 `tags`로 연결된다.

주의: 편입/대표기업은 시황·구성 변화로 달라질 수 있는 큐레이션 스냅샷이며 추천이 아니다.
"""

from __future__ import annotations


def _d(name, ticker=None):
    return {"name": name, "ticker": ticker}


SECTORS = [
    {
        "key": "semiconductor",
        "name": "반도체",
        "tags": ["반도체"],
        "summary": "소재·장비 → 설계·제조 → 후공정·세트로 이어지는 한국 증시의 핵심 축.",
        "stages": [
            {
                "stage": "업스트림 · 소재/장비",
                "desc": "웨이퍼·소재·노광/증착 장비 등 전공정 인프라.",
                "domestic": [_d("한미반도체", "042700"), _d("원익IPS", "240810"),
                             _d("리노공업", "058470"), _d("이오테크닉스", "039030"), _d("DB하이텍", "000990")],
                "overseas": [_d("ASML", "ASML"), _d("Applied Materials", "AMAT"),
                             _d("Lam Research", "LRCX"), _d("KLA", "KLAC")],
            },
            {
                "stage": "미드스트림 · 설계/제조",
                "desc": "메모리·파운드리·팹리스 등 실제 칩 생산·설계.",
                "domestic": [_d("삼성전자", "005930"), _d("SK하이닉스", "000660")],
                "overseas": [_d("TSMC", "TSM"), _d("NVIDIA", "NVDA"),
                             _d("Micron", "MU"), _d("Intel", "INTC"), _d("Broadcom", "AVGO")],
            },
            {
                "stage": "다운스트림 · 후공정/부품/세트",
                "desc": "패키징·기판·카메라모듈 등 부품과 최종 세트.",
                "domestic": [_d("삼성전기", "009150"), _d("LG이노텍", "011070")],
                "overseas": [_d("Apple", "AAPL"), _d("Dell", "DELL")],
            },
        ],
    },
    {
        "key": "ai_datacenter",
        "name": "AI/데이터센터",
        "tags": ["AI/데이터센터", "IT/인터넷"],
        "summary": "AI 가속기(HBM) → 서버/전력·냉각 인프라 → 클라우드·소프트웨어 수요로 확산.",
        "stages": [
            {
                "stage": "업스트림 · AI 반도체/HBM",
                "desc": "AI 학습·추론용 가속기와 고대역폭 메모리(HBM).",
                "domestic": [_d("SK하이닉스", "000660"), _d("삼성전자", "005930"), _d("한미반도체", "042700")],
                "overseas": [_d("NVIDIA", "NVDA"), _d("Broadcom", "AVGO"), _d("AMD", "AMD")],
            },
            {
                "stage": "미드스트림 · 서버/전력·냉각",
                "desc": "데이터센터 서버·전력공급·액침/공랭 냉각 인프라.",
                "domestic": [_d("LS ELECTRIC", "010120"), _d("HD현대일렉트릭", "267260")],
                "overseas": [_d("Super Micro", "SMCI"), _d("Vertiv", "VRT"), _d("Dell", "DELL")],
            },
            {
                "stage": "다운스트림 · 클라우드/SW",
                "desc": "하이퍼스케일 클라우드와 AI 소프트웨어·플랫폼 서비스.",
                "domestic": [_d("네이버", "035420"), _d("삼성SDS", "018260"), _d("카카오", "035720")],
                "overseas": [_d("Microsoft", "MSFT"), _d("Amazon", "AMZN"), _d("Google", "GOOGL")],
            },
        ],
    },
    {
        "key": "battery",
        "name": "2차전지",
        "tags": ["2차전지"],
        "summary": "리튬·양극재 소재 → 셀 제조 → 전기차·ESS 수요로 이어지는 밸류체인.",
        "stages": [
            {
                "stage": "업스트림 · 광물/소재",
                "desc": "리튬·니켈 등 광물과 양극재·음극재·전해질 소재.",
                "domestic": [_d("포스코홀딩스", "005490"), _d("에코프로비엠", "247540"),
                             _d("포스코퓨처엠", "003670"), _d("엘앤에프", "066970"), _d("고려아연", "010130")],
                "overseas": [_d("Albemarle", "ALB"), _d("SQM", "SQM")],
            },
            {
                "stage": "미드스트림 · 셀 제조",
                "desc": "배터리 셀·모듈·팩 제조.",
                "domestic": [_d("LG에너지솔루션", "373220"), _d("삼성SDI", "006400"), _d("SK이노베이션", "096770")],
                "overseas": [_d("CATL", "300750.SZ"), _d("Panasonic", "6752.T")],
            },
            {
                "stage": "다운스트림 · 전기차/ESS",
                "desc": "전기차 완성차와 에너지저장장치(ESS) 수요처.",
                "domestic": [_d("현대차", "005380"), _d("기아", "000270")],
                "overseas": [_d("Tesla", "TSLA"), _d("BYD", "1211.HK")],
            },
        ],
    },
    {
        "key": "auto",
        "name": "자동차",
        "tags": ["자동차"],
        "summary": "부품·전장 → 완성차 → 모빌리티 서비스. 경기민감 대표 업종.",
        "stages": [
            {
                "stage": "업스트림 · 부품/전장",
                "desc": "구동·공조·전장 등 핵심 부품.",
                "domestic": [_d("현대모비스", "012330"), _d("한온시스템", "018880"), _d("HL만도", "204320")],
                "overseas": [_d("Bosch(비상장)"), _d("Aptiv", "APTV")],
            },
            {
                "stage": "미드스트림 · 완성차",
                "desc": "내연·전기차 완성차 제조.",
                "domestic": [_d("현대차", "005380"), _d("기아", "000270")],
                "overseas": [_d("Tesla", "TSLA"), _d("Toyota", "TM"), _d("GM", "GM")],
            },
            {
                "stage": "다운스트림 · 모빌리티/금융",
                "desc": "할부·리스·중고차·모빌리티 서비스.",
                "domestic": [_d("현대글로비스", "086280")],
                "overseas": [_d("Uber", "UBER")],
            },
        ],
    },
    {
        "key": "defense",
        "name": "방산",
        "tags": ["방산"],
        "summary": "소재·부품 → 체계종합(완성무기) → 수출/MRO. 지정학 리스크에 강한 방어·성장 성격.",
        "stages": [
            {
                "stage": "업스트림 · 소재/부품",
                "desc": "특수강·항공소재·전자부품.",
                "domestic": [_d("현대제철", "004020"), _d("풍산", "103140")],
                "overseas": [_d("Howmet Aerospace", "HWM")],
            },
            {
                "stage": "미드스트림 · 체계종합",
                "desc": "항공기·유도무기·지상장비 등 완성 무기체계.",
                "domestic": [_d("한화에어로스페이스", "012450"), _d("한국항공우주", "047810"),
                             _d("LIG넥스원", "079550"), _d("현대로템", "064350")],
                "overseas": [_d("Lockheed Martin", "LMT"), _d("RTX", "RTX"), _d("Northrop Grumman", "NOC")],
            },
            {
                "stage": "다운스트림 · 수출/MRO",
                "desc": "무기 수출과 유지·보수·정비(MRO).",
                "domestic": [_d("한화시스템", "272210")],
                "overseas": [_d("General Dynamics", "GD")],
            },
        ],
    },
    {
        "key": "energy",
        "name": "에너지/원자재",
        "tags": ["에너지/원자재", "소재/화학"],
        "summary": "자원 채굴 → 정제/화학 → 유통. 인플레·경기 후반부에 상대 강세.",
        "stages": [
            {
                "stage": "업스트림 · 자원/채굴",
                "desc": "원유·가스·비철금속 등 원자재 확보.",
                "domestic": [_d("고려아연", "010130"), _d("포스코홀딩스", "005490")],
                "overseas": [_d("ExxonMobil", "XOM"), _d("Freeport-McMoRan", "FCX")],
            },
            {
                "stage": "미드스트림 · 정제/화학",
                "desc": "정유·석유화학 등 소재 가공.",
                "domestic": [_d("S-Oil", "010950"), _d("LG화학", "051910"), _d("롯데케미칼", "011170")],
                "overseas": [_d("Chevron", "CVX"), _d("Dow", "DOW")],
            },
            {
                "stage": "다운스트림 · 유통/발전",
                "desc": "에너지 유통과 발전 연료 공급.",
                "domestic": [_d("GS", "078930"), _d("SK이노베이션", "096770")],
                "overseas": [_d("Shell", "SHEL")],
            },
        ],
    },
    {
        "key": "power_nuclear",
        "name": "전력/원전",
        "tags": ["전력/원전"],
        "summary": "기자재 → 발전·송배전 → 전력 판매. AI 전력수요·원전 르네상스 테마. 방어+성장 혼재.",
        "stages": [
            {
                "stage": "업스트림 · 원전/발전 기자재",
                "desc": "원자로·터빈·중전기기 등 발전 설비.",
                "domestic": [_d("두산에너빌리티", "034020"), _d("한전기술", "052690"), _d("효성중공업", "298040")],
                "overseas": [_d("GE Vernova", "GEV"), _d("Cameco(우라늄)", "CCJ")],
            },
            {
                "stage": "미드스트림 · 송배전/계통",
                "desc": "변압기·전력망 등 송배전 인프라.",
                "domestic": [_d("LS ELECTRIC", "010120"), _d("HD현대일렉트릭", "267260"), _d("대한전선", "001440")],
                "overseas": [_d("Quanta Services", "PWR")],
            },
            {
                "stage": "다운스트림 · 발전/전력판매",
                "desc": "발전 운영과 전력 판매.",
                "domestic": [_d("한국전력", "015760")],
                "overseas": [_d("Constellation Energy", "CEG"), _d("Vistra", "VST")],
            },
        ],
    },
    {
        "key": "bio",
        "name": "헬스케어/바이오",
        "tags": ["헬스케어/바이오"],
        "summary": "원료·CDMO → 신약개발 → 의료 서비스. 금리인하·경기방어 국면에 관심.",
        "stages": [
            {
                "stage": "업스트림 · 원료/CDMO",
                "desc": "바이오의약품 위탁개발·생산(CDMO)과 원료.",
                "domestic": [_d("삼성바이오로직스", "207940")],
                "overseas": [_d("Lonza", "LONN.SW"), _d("Thermo Fisher", "TMO")],
            },
            {
                "stage": "미드스트림 · 신약/바이오시밀러",
                "desc": "신약개발·바이오시밀러.",
                "domestic": [_d("셀트리온", "068270"), _d("유한양행", "000100"),
                             _d("한미약품", "128940"), _d("SK바이오팜", "326030")],
                "overseas": [_d("Eli Lilly", "LLY"), _d("Novo Nordisk", "NVO"), _d("Pfizer", "PFE")],
            },
            {
                "stage": "다운스트림 · 의료기기/서비스",
                "desc": "의료기기·진단·병원 서비스.",
                "domestic": [_d("클래시스", "214150"), _d("루닛", "328130")],
                "overseas": [_d("Intuitive Surgical", "ISRG"), _d("Medtronic", "MDT")],
            },
        ],
    },
]

_BY_KEY = {s["key"]: s for s in SECTORS}


def sectors() -> list[dict]:
    return SECTORS


def sector(key: str) -> dict | None:
    return _BY_KEY.get(key)


def key_for_tag(tag: str) -> str | None:
    """사이클의 주도섹터 이름(예: '반도체', 'IT/인터넷')을 밸류체인 섹터 key로 매핑. 없으면 None."""
    for s in SECTORS:
        if tag in s["tags"]:
            return s["key"]
    return None
