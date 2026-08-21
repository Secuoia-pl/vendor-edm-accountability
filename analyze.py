"""Analiza sygnalow RSS pod hub vendor-EDM — Atlas / Wiro LLM -> drafty do akceptacji."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

import bot

# Windows cp1250 consoles cannot print arrows / some Unicode.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _print(*args: object, **kwargs: object) -> None:
    text = " ".join(str(a) for a in args)
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        print(text, **kwargs)
    except UnicodeEncodeError:
        safe = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(safe, **kwargs)


ROOT = bot.ROOT
DRAFTS_DIR = bot.DRAFTS_DIR
DATA_DIR = bot.DATA_DIR
HUB_URL = "https://bezpiecznyblog.pl/odpowiedzialnosc-vendora-edm/"
FRAME = (
    "Problem nie zaczyna się w momencie ataku — zaczyna się, gdy milion ludzi "
    "jest zależnych od jednego vendora bez równoważnej odpowiedzialności."
)

SYSTEM_PROMPT = f"""Jesteś analitykiem cyber / RODO PL wspierającym publiczny hub (zero DM, zero sprzedaży).

Rama stała (używaj 1:1 gdy pasuje):
{FRAME}

Hub: {HUB_URL}
Case lens: MyDr / vendor EDM / admin vs procesor / pacjent.

Zwróć WYŁĄCZNIE jeden obiekt JSON (bez markdown) o schemacie:
{{
  "update_hub": true/false,
  "rationale": "1-3 zdania dlaczego update albo nie",
  "signals_used": [{{"title": "...", "url": "...", "why": "..."}}],
  "changelog_bullets": ["..."],
  "new_faq": [{{"q": "...", "a": "..."}}],
  "li_post": "gotowy post LinkedIn po polsku, z linkiem do huba na końcu",
  "x_thread": ["1/n ...", "2/n ..."],
  "facts_to_verify": ["..."]
}}

Zasady:
- Nie wymyślaj liczb ani oficjalnych decyzji — oznacz niepewność w facts_to_verify.
- Zero CTA sprzedażowego, zero „napisz DM”, zero tagowania osób.
- li_post i x_thread mają trzymać ramę i prowadzić do huba.
- Jeśli sygnały słabo pasują do vendora EDM / odpowiedzialności — update_hub=false, i tak daj broadcast z ramą evergreen.
"""


def load_analyze_config() -> dict[str, Any]:
    cfg = bot.load_config()
    section = cfg.get("analyze") or {}
    return {
        "provider": str(os.getenv("ANALYZE_PROVIDER") or section.get("provider") or "atlas"),
        "model": str(
            os.getenv("ANALYZE_MODEL")
            or section.get("model")
            or "Qwen/Qwen3-235B-A22B-Instruct-2507"
        ),
        "wiro_model": str(
            os.getenv("WIRO_ANALYZE_MODEL")
            or section.get("wiro_model")
            or "ByteDance/seed-v2.1-turbo"
        ),
        "top_n": int(section.get("top_n") or 8),
        "min_score": int(section.get("min_score") or cfg.get("min_score") or 40),
        "temperature": float(section.get("temperature") or 0.3),
        "max_tokens": int(section.get("max_tokens") or 2500),
    }


def _env_paths() -> list[Path]:
    paths = [ROOT / ".env"]
    # opcjonalnie: te same klucze co studio (bez kopiowania sekretów do chatu)
    sibling = Path(r"C:\Users\bkowa\Projects\architektura-szumu\studio\.env")
    if sibling.exists():
        paths.append(sibling)
    return paths


def load_keys() -> None:
    for path in _env_paths():
        load_dotenv(path, override=False)


def atlas_key() -> str:
    return (
        os.getenv("ATLASCLOUD_API_KEY")
        or os.getenv("ATLAS_API_KEY")
        or ""
    ).strip()


def wiro_key() -> str:
    return (os.getenv("WIRO_API_KEY") or "").strip()


def signals_payload(signals: list[bot.Signal], top_n: int, min_score: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for s in signals:
        if s.score < min_score:
            continue
        out.append(
            {
                "title": s.title,
                "url": s.url,
                "source": s.source,
                "score": s.score,
                "age_hours": s.age_hours,
                "keywords": s.matched_keywords,
                "summary": s.summary[:220],
            }
        )
        if len(out) >= top_n:
            break
    return out


def build_user_prompt(items: list[dict[str, Any]]) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return (
        f"Data UTC: {today}\n"
        f"Sygnały (posortowane po score):\n"
        f"{json.dumps(items, ensure_ascii=False, indent=2)}\n\n"
        "Zrób analizę pod hub vendor-EDM i drafty broadcast."
    )


def extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("pustą odpowiedź modelu")
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("brak obiektu JSON w odpowiedzi")
    return json.loads(text[start : end + 1])


def heuristic_analysis(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Lokalny stub bez API — do --dry-run."""
    top = items[0] if items else None
    related = any(
        any(k in f"{it['title']} {it.get('summary','')}".lower() for k in (
            "mydr", "wyciek", "dane", "pesel", "medycz", "uodo", "rodo", "edm", "vendor", "procesor"
        ))
        for it in items
    )
    title = top["title"] if top else "brak silnego sygnału"
    url = top["url"] if top else HUB_URL
    return {
        "update_hub": bool(related),
        "rationale": (
            "Dry-run lokalny (bez LLM). Sygnały zebrane; "
            + ("wykryto frazy bliskie wyciekowi/danym/RODO." if related else "brak silnego dopasowania do case MyDr — evergreen.")
        ),
        "signals_used": (
            [{"title": title, "url": url, "why": "najwyższy score w przebiegu"}] if top else []
        ),
        "changelog_bullets": (
            [f"Odnotowano sygnał: {title}"] if related and top else []
        ),
        "new_faq": [],
        "li_post": (
            f"{FRAME}\n\n"
            f"Dziś w radarze m.in.: {title}\n\n"
            f"Pełna nota + checklista 72h:\n{HUB_URL}"
        ),
        "x_thread": [
            f"1/4 {FRAME}",
            f"2/4 Sygnał: {title}",
            "3/4 Zamiast „czy był atak?” — jakie obowiązki ex ante ma vendor EDM skali krajowej?",
            f"4/4 Hub: {HUB_URL}",
        ],
        "facts_to_verify": [f"Zweryfikuj źródło: {url}"] if top else [],
        "_meta": {"mode": "dry-run-heuristic", "signals": len(items)},
    }


def call_atlas(model: str, user_prompt: str, temperature: float, max_tokens: int) -> str:
    key = atlas_key()
    if not key:
        raise RuntimeError("Brak ATLASCLOUD_API_KEY w .env")
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Origin": "https://www.atlascloud.ai",
        "Referer": "https://www.atlascloud.ai/",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    last_err = ""
    with httpx.Client(timeout=httpx.Timeout(30.0, read=180.0)) as client:
        for attempt in range(1, 4):
            resp = client.post(
                "https://api.atlascloud.ai/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            if resp.status_code < 400:
                data = resp.json()
                try:
                    return data["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError) as exc:
                    raise RuntimeError(f"Atlas: nieoczekiwana odpowiedź: {data!r}"[:500]) from exc
            last_err = f"Atlas HTTP {resp.status_code}: {resp.text[:400]}"
            if resp.status_code in {429, 502, 503, 504} and attempt < 3:
                time.sleep(2 * attempt)
                continue
            raise RuntimeError(last_err)
    raise RuntimeError(last_err)


def _wiro_headers() -> dict[str, str]:
    key = wiro_key()
    if not key:
        raise RuntimeError("Brak WIRO_API_KEY w .env")
    return {"Content-Type": "application/json", "x-api-key": key}


def call_wiro(model: str, user_prompt: str) -> str:
    """Wiro Run + poll Task/Detail — modele chat (Seed, Grok, Qwen…)."""
    base = os.getenv("WIRO_BASE_URL", "https://api.wiro.ai/v1").rstrip("/")
    prompt = SYSTEM_PROMPT + "\n\n" + user_prompt
    with httpx.Client(timeout=180.0) as client:
        run = client.post(
            f"{base}/Run/{model}",
            headers=_wiro_headers(),
            json={"prompt": prompt},
        )
        raw = run.text
        if run.status_code >= 400:
            raise RuntimeError(f"Wiro Run HTTP {run.status_code}: {raw[:400]}")
        payload = run.json()
        if not payload.get("result"):
            raise RuntimeError(f"Wiro Run failed: {raw[:400]}")
        task_id = str(payload["taskid"])

        for _ in range(60):
            detail = client.post(
                f"{base}/Task/Detail",
                headers=_wiro_headers(),
                json={"taskid": task_id},
            )
            detail.raise_for_status()
            data = detail.json()
            tasks = data.get("tasklist") or []
            if isinstance(tasks, dict):
                tasks = [tasks]
            if not tasks:
                time.sleep(2)
                continue
            task = tasks[0]
            status = str(task.get("status") or task.get("taskstat") or "").lower()
            text = _wiro_task_text(task)
            if text and any(s in status for s in ("ok", "success", "complete", "done", "output", "end")):
                return text
            if text and status and status not in {"", "0", "queue", "queued", "pending", "running", "processing", "start"}:
                return text
            if any(s in status for s in ("fail", "error", "-1")):
                raise RuntimeError(f"Wiro task failed: {json.dumps(task, ensure_ascii=False)[:500]}")
            time.sleep(2)
    raise RuntimeError(f"Wiro timeout dla task {task_id}")


def _wiro_task_text(task: dict[str, Any]) -> str:
    for key in ("output", "result", "text", "response", "message", "answer", "content"):
        val = task.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
        if isinstance(val, dict):
            for sub in ("text", "content", "output", "message"):
                if isinstance(val.get(sub), str) and val[sub].strip():
                    return val[sub].strip()
    outputs = task.get("outputs") or []
    chunks: list[str] = []
    for out in outputs:
        if not isinstance(out, dict):
            continue
        for key in ("content", "text", "url", "name"):
            val = out.get(key)
            if isinstance(val, str) and val.strip() and not val.startswith("http"):
                chunks.append(val.strip())
        # czasem tekst w URL do .txt
        url = str(out.get("url") or "")
        ctype = str(out.get("contenttype") or "").lower()
        if url and ("text" in ctype or url.endswith(".txt") or url.endswith(".json")):
            try:
                with httpx.Client(timeout=60.0) as client:
                    r = client.get(url)
                    if r.status_code < 400 and r.text.strip():
                        chunks.append(r.text.strip())
            except Exception:  # noqa: BLE001
                pass
    return "\n".join(chunks).strip()


def normalize_result(data: dict[str, Any], *, provider: str, model: str) -> dict[str, Any]:
    data = dict(data)
    data.setdefault("update_hub", False)
    data.setdefault("rationale", "")
    data.setdefault("signals_used", [])
    data.setdefault("changelog_bullets", [])
    data.setdefault("new_faq", [])
    data.setdefault("li_post", "")
    data.setdefault("x_thread", [])
    data.setdefault("facts_to_verify", [])
    meta = dict(data.get("_meta") or {})
    meta.update({"provider": provider, "model": model, "ts": datetime.now(timezone.utc).isoformat()})
    data["_meta"] = meta
    return data


def write_outputs(result: dict[str, Any], items: list[dict[str, Any]]) -> tuple[Path, Path]:
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = DRAFTS_DIR / f"analyze-{stamp}.json"
    md_path = DRAFTS_DIR / f"analyze-{stamp}.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    meta = result.get("_meta") or {}
    faq_lines = []
    for faq in result.get("new_faq") or []:
        if isinstance(faq, dict):
            faq_lines.append(f"**Q:** {faq.get('q', '')}\n**A:** {faq.get('a', '')}")
    thread = "\n\n".join(result.get("x_thread") or [])
    changelog = "\n".join(f"- {b}" for b in (result.get("changelog_bullets") or [])) or "_brak_"
    facts = "\n".join(f"- {f}" for f in (result.get("facts_to_verify") or [])) or "_brak_"
    used = "\n".join(
        f"- {s.get('title')} — {s.get('url')} ({s.get('why', '')})"
        for s in (result.get("signals_used") or [])
        if isinstance(s, dict)
    ) or "_brak_"

    md = f"""# Analiza hub — {stamp}

- **Status:** PENDING_APPROVAL
- **Provider:** {meta.get('provider')} / {meta.get('model')}
- **Update hub:** {result.get('update_hub')}
- **Sygnałów wejściowych:** {len(items)}

## Rationale

{result.get('rationale')}

## Sygnały użyte

{used}

## Changelog (propozycja)

{changelog}

## Nowe FAQ

{chr(10).join(faq_lines) if faq_lines else '_brak_'}

## LinkedIn (copy-paste)

{result.get('li_post')}

## Wątek X

{thread}

## Do weryfikacji

{facts}

## Hub

{HUB_URL}
"""
    md_path.write_text(md, encoding="utf-8")

    ranking_path = DATA_DIR / "last_analyze_input.json"
    ranking_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return md_path, json_path


def run_analyze(*, dry_run: bool = False, provider: str | None = None) -> dict[str, Any]:
    load_keys()
    bot.ensure_dirs()
    acfg = load_analyze_config()
    if provider:
        acfg["provider"] = provider

    signals = bot.collect_signals(bot.load_config())
    items = signals_payload(signals, acfg["top_n"], acfg["min_score"])
    _print(f"Sygnaly lacznie: {len(signals)}; do analizy: {len(items)} (min_score={acfg['min_score']})")
    for it in items[:5]:
        _print(f"  [{it['score']}] {it['source']}: {it['title'][:90]}")

    if dry_run:
        result = normalize_result(
            heuristic_analysis(items),
            provider="local",
            model="heuristic",
        )
        md_path, json_path = write_outputs(result, items)
        _print(f"Dry-run -> {md_path.name}")
        _print(f"JSON     -> {json_path.name}")
        return result

    user_prompt = build_user_prompt(items)
    prov = acfg["provider"].lower().strip()
    raw = ""
    model_used = acfg["model"]

    if prov == "atlas":
        model_used = acfg["model"]
        raw = call_atlas(model_used, user_prompt, acfg["temperature"], acfg["max_tokens"])
    elif prov == "wiro":
        model_used = acfg["wiro_model"]
        raw = call_wiro(model_used, user_prompt)
    elif prov == "auto":
        try:
            model_used = acfg["model"]
            raw = call_atlas(model_used, user_prompt, acfg["temperature"], acfg["max_tokens"])
            prov = "atlas"
        except Exception as atlas_exc:  # noqa: BLE001
            _print(f"Atlas niedostepny ({atlas_exc}); fallback Wiro...")
            model_used = acfg["wiro_model"]
            raw = call_wiro(model_used, user_prompt)
            prov = "wiro"
    else:
        raise RuntimeError(f"Nieznany provider: {prov} (atlas|wiro|auto)")

    parsed = extract_json(raw)
    result = normalize_result(parsed, provider=prov, model=model_used)
    md_path, json_path = write_outputs(result, items)
    _print(f"Analiza -> {md_path.name}")
    _print(f"JSON    -> {json_path.name}")
    _print(f"update_hub={result.get('update_hub')} | {result.get('rationale', '')[:160]}")
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analiza sygnalow -> drafty hub/LI/X")
    parser.add_argument("--dry-run", action="store_true", help="Bez API - lokalna heurystyka")
    parser.add_argument("--provider", choices=["atlas", "wiro", "auto"], help="Nadpisz config analyze.provider")
    parser.add_argument("--once", action="store_true", help="Jeden przebieg (domyslne)")
    args = parser.parse_args()
    run_analyze(dry_run=args.dry_run, provider=args.provider)
