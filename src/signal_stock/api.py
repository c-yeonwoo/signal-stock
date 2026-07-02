"""FastAPI 백엔드 — 인증/온보딩/워치리스트 + 향후 탭용 스텁 라우트, SPA 서빙.

1단계 스캐폴딩 범위. 시그널/밸류에이션/후보/국면/매크로는 프론트가 바로 붙을 수 있도록
응답 스키마만 확정한 스텁이며, 실제 계산 로직은 2단계 이후(signals/, ingest/)에서 채운다.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import Body, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from signal_stock import auth, db

log = logging.getLogger("signal_stock")

WEB_DIR = Path(__file__).parent / "web"

# 인증 게이트: /api/* 는 세션 필수(아래 prefix 만 예외). 그 외(/, 정적)는 허용.
_OPEN_PREFIXES = ("/api/auth/",)


def _uid(request: Request):
    u = auth.current_user(request.cookies.get(auth.COOKIE))
    return u["id"] if u else None


app = FastAPI(title="signal-stock")


@app.middleware("http")
async def _auth_gate(request: Request, call_next):
    """인증된 유저만 데이터 API 접근. /api/auth/* 와 비-API(/, 정적)는 허용."""
    p = request.url.path
    if p.startswith("/api/") and not p.startswith(_OPEN_PREFIXES):
        if not _uid(request):
            return JSONResponse({"error": "인증이 필요합니다.", "auth": False}, status_code=401)
    return await call_next(request)


# ---------- 인증 ----------
@app.post("/api/auth/signup")
def auth_signup(data: dict = Body(...)):
    token, err = auth.signup(data.get("email", ""), data.get("pw", ""))
    if err:
        return JSONResponse({"ok": False, "error": err}, status_code=400)
    r = JSONResponse({"ok": True})
    r.set_cookie(auth.COOKIE, token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)
    return r


@app.post("/api/auth/login")
def auth_login(data: dict = Body(...)):
    token, err = auth.login(data.get("email", ""), data.get("pw", ""))
    if err:
        return JSONResponse({"ok": False, "error": err}, status_code=401)
    r = JSONResponse({"ok": True})
    r.set_cookie(auth.COOKIE, token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)
    return r


@app.post("/api/auth/logout")
def auth_logout(request: Request):
    auth.logout(request.cookies.get(auth.COOKIE))
    r = JSONResponse({"ok": True})
    r.delete_cookie(auth.COOKIE)
    return r


@app.get("/api/auth/me")
def auth_me(request: Request):
    u = auth.current_user(request.cookies.get(auth.COOKIE))
    if not u:
        return JSONResponse({"auth": False}, status_code=401)
    profile = db.profile_get(u["id"])
    return {"auth": True, "email": u["email"], "profile": profile, "onboarded": bool(profile)}


# ---------- 프로필(온보딩) ----------
@app.get("/api/profile")
def profile_get(request: Request):
    return db.profile_get(_uid(request))


@app.put("/api/profile")
def profile_put(request: Request, data: dict = Body(...)):
    db.profile_set(_uid(request), data)
    return {"ok": True}


# ---------- 워치리스트(즐겨찾기, kind='ticker') ----------
@app.get("/api/favorites")
def favorites_get(request: Request):
    return {"favorites": db.fav_list(_uid(request))}


@app.post("/api/favorites")
def favorites_add(request: Request, data: dict = Body(...)):
    db.fav_add(_uid(request), data.get("kind", "ticker"), data.get("key", ""), data.get("label", ""))
    return {"ok": True}


@app.delete("/api/favorites")
def favorites_del(request: Request, kind: str, key: str):
    db.fav_remove(_uid(request), kind, key)
    return {"ok": True}


# ---------- 탭 스텁 (2단계 이후 실데이터로 교체) ----------
@app.get("/api/signals")
def signals_stub():
    """TODO(phase2): 종목/섹터 시그널 테이블 + 백테스트 성적표."""
    return {"ready": False, "items": []}


@app.get("/api/valuation")
def valuation_stub():
    """TODO(phase5): 섹터/등급 대비 저평가(PER·PBR·성장) 스크리닝."""
    return {"ready": False, "items": []}


@app.get("/api/candidates/all")
def candidates_stub():
    """TODO(phase4): 통합 후보 뷰(눌림목·낙폭과대·IPO·실적서프라이즈·턴어라운드) + 기회도."""
    return {"ready": False, "items": []}


@app.get("/api/regime")
def regime_stub():
    """TODO(phase3): 시장 국면(강세·과열·조정·약세)."""
    return {"ready": False, "regime": None}


@app.get("/api/macro")
def macro_stub():
    """TODO(phase3): 매크로 미니차트(기준금리·환율·지수·거래대금)."""
    return {"ready": False, "series": []}


@app.post("/api/report/ai")
def report_ai_stub(request: Request, data: dict = Body(...)):
    """TODO(phase6): 프로필+워치리스트 기반 AI 리포트."""
    return {"available": False, "message": "준비 중"}


# ---------- SPA 서빙 ----------
@app.get("/", response_class=HTMLResponse)
def index():
    return (WEB_DIR / "index.html").read_text(encoding="utf-8")
