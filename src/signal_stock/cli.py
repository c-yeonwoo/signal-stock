"""CLI — Signal STOCK.

사용:
  sigstock serve                 # 웹 대시보드 실행
  sigstock fetch / build / report  # 2단계(수집기·시그널 엔진) 도입 후 구현
"""

from __future__ import annotations

import os

import typer
from rich.console import Console

app = typer.Typer(add_completion=False, help="Signal STOCK — 주식 매매 타이밍 시그널")
console = Console()


@app.command()
def serve(
    host: str = typer.Option(lambda: os.environ.get("HOST", "127.0.0.1")),
    port: int = typer.Option(lambda: int(os.environ.get("PORT", "8765"))),
):
    """대시보드 웹서버 실행."""
    import uvicorn

    console.print(f"[green]Signal STOCK:[/green] http://{host}:{port}")
    uvicorn.run("signal_stock.api:app", host=host, port=port, log_level="warning")


@app.command()
def fetch():
    """시세/공시/거시지표 자동 수집 — 2단계에서 구현."""
    console.print("[yellow]아직 구현되지 않았습니다.[/yellow] 2단계(ingest/) 도입 후 사용 가능합니다.")
    raise typer.Exit(1)


@app.command()
def build():
    """수동 데이터 파싱 → parquet 캐시 생성 — 2단계에서 구현."""
    console.print("[yellow]아직 구현되지 않았습니다.[/yellow] 2단계(ingest/) 도입 후 사용 가능합니다.")
    raise typer.Exit(1)


@app.command()
def report():
    """터미널 시그널 리포트 — 2단계(signals/engine.py) 도입 후 구현."""
    console.print("[yellow]아직 구현되지 않았습니다.[/yellow] 2단계(signals/) 도입 후 사용 가능합니다.")
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
