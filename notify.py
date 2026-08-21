"""Powiadomienia: ntfy + Signal (REST / signal-cli). Bez Telegrama."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent


def _load_env() -> None:
    load_dotenv(ROOT / ".env", override=False)


def _configured_channels() -> list[str]:
    _load_env()
    out: list[str] = []
    if (os.getenv("NTFY_TOPIC") or "").strip():
        out.append("ntfy")
    if (os.getenv("SIGNAL_REST_URL") or "").strip() and (os.getenv("SIGNAL_NUMBER") or "").strip():
        out.append("signal-rest")
    elif (os.getenv("SIGNAL_CLI_PATH") or shutil.which("signal-cli")) and (
        os.getenv("SIGNAL_NUMBER") or os.getenv("SIGNAL_CLI_ACCOUNT") or ""
    ).strip():
        out.append("signal-cli")
    return out


def notify_all(message: str, *, title: str | None = None, priority: int = 3) -> dict[str, Any]:
    """Wyślij na wszystkie skonfigurowane kanały. Zwraca status per kanał."""
    _load_env()
    text = (message or "").strip()
    if not text:
        return {"ok": False, "error": "empty message"}

    results: dict[str, Any] = {}
    if (os.getenv("NTFY_TOPIC") or "").strip():
        results["ntfy"] = _notify_ntfy(text, title=title, priority=priority)
    if (os.getenv("SIGNAL_REST_URL") or "").strip() and (os.getenv("SIGNAL_NUMBER") or "").strip():
        results["signal"] = _notify_signal_rest(text)
    elif _signal_cli_ready():
        results["signal"] = _notify_signal_cli(text)

    if not results:
        results["skipped"] = True
        results["reason"] = "Brak NTFY_TOPIC ani Signal (REST/CLI) w .env"
    return results


def _notify_ntfy(message: str, *, title: str | None, priority: int) -> dict[str, Any]:
    server = (os.getenv("NTFY_SERVER") or "https://ntfy.sh").rstrip("/")
    topic = (os.getenv("NTFY_TOPIC") or "").strip().lstrip("/")
    token = (os.getenv("NTFY_TOKEN") or "").strip()
    if not topic:
        return {"ok": False, "error": "NTFY_TOPIC empty"}

    headers: dict[str, str] = {
        "User-Agent": "cyber-influence-bot/ntfy",
        "Priority": str(max(1, min(5, int(priority)))),
    }
    if title:
        headers["Title"] = title[:120]
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{server}/{quote(topic, safe='')}"
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(url, content=message.encode("utf-8"), headers=headers)
        if resp.status_code >= 400:
            return {"ok": False, "status": resp.status_code, "error": resp.text[:200]}
        return {"ok": True, "status": resp.status_code, "topic": topic}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def _signal_recipients() -> list[str]:
    raw = (os.getenv("SIGNAL_RECIPIENTS") or os.getenv("SIGNAL_TO") or "").strip()
    number = (os.getenv("SIGNAL_NUMBER") or os.getenv("SIGNAL_CLI_ACCOUNT") or "").strip()
    if raw:
        return [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
    # Note to Self — ten sam numer
    return [number] if number else []


def _notify_signal_rest(message: str) -> dict[str, Any]:
    base = (os.getenv("SIGNAL_REST_URL") or "").rstrip("/")
    number = (os.getenv("SIGNAL_NUMBER") or "").strip()
    recipients = _signal_recipients()
    if not base or not number or not recipients:
        return {"ok": False, "error": "SIGNAL_REST_URL / SIGNAL_NUMBER / recipients incomplete"}

    payload = {
        "message": message,
        "number": number,
        "recipients": recipients,
    }
    try:
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(f"{base}/v2/send", json=payload)
        if resp.status_code >= 400:
            return {"ok": False, "status": resp.status_code, "error": resp.text[:300]}
        return {"ok": True, "status": resp.status_code, "via": "signal-cli-rest-api"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def _signal_cli_ready() -> bool:
    path = (os.getenv("SIGNAL_CLI_PATH") or "signal-cli").strip()
    account = (os.getenv("SIGNAL_NUMBER") or os.getenv("SIGNAL_CLI_ACCOUNT") or "").strip()
    if not account:
        return False
    if Path(path).exists():
        return True
    return bool(shutil.which(path))


def _notify_signal_cli(message: str) -> dict[str, Any]:
    path = (os.getenv("SIGNAL_CLI_PATH") or "signal-cli").strip()
    account = (os.getenv("SIGNAL_NUMBER") or os.getenv("SIGNAL_CLI_ACCOUNT") or "").strip()
    recipients = _signal_recipients()
    if not account or not recipients:
        return {"ok": False, "error": "SIGNAL_CLI account/recipients incomplete"}

    # signal-cli -a +48… send -m "…" +48…
    cmd = [path, "-a", account, "send", "-m", message, *recipients]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()[:300]
            return {"ok": False, "error": err or f"exit {proc.returncode}"}
        return {"ok": True, "via": "signal-cli"}
    except FileNotFoundError:
        return {
            "ok": False,
            "error": "signal-cli not found — zainstaluj CLI albo ustaw SIGNAL_REST_URL (Docker)",
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def format_analyze_alert(result: dict[str, Any], md_name: str | None = None) -> tuple[str, str]:
    """title, body — bez sekretów, tylko sygnał do działania."""
    update = result.get("update_hub")
    title = "Hub draft gotowy" if update else "Analyze draft"
    lines = [
        f"update_hub={update}",
        (result.get("rationale") or "")[:180],
    ]
    if md_name:
        lines.append(f"plik: drafts/{md_name}")
    lines.append("Otworz Streamlit -> Drafty -> Analizy hub")
    body = "\n".join(x for x in lines if x).strip()
    return title, body


if __name__ == "__main__":
    import argparse
    import sys

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    parser = argparse.ArgumentParser(description="Test ntfy / Signal notifications")
    parser.add_argument("--message", default="Test z cyber-influence-bot")
    parser.add_argument("--title", default="Test")
    parser.add_argument("--channels", action="store_true", help="Pokaz skonfigurowane kanaly")
    args = parser.parse_args()

    if args.channels:
        print("channels:", ", ".join(_configured_channels()) or "(none)")
    else:
        print(json.dumps(notify_all(args.message, title=args.title), ensure_ascii=False, indent=2))
