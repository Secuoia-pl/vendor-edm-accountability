"""Cyber influence bot — lokalny pipeline: RSS → score → drafty postów."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import urllib.request
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DRAFTS_DIR = ROOT / "drafts"
STATE_FILE = DATA_DIR / "seen.json"
CONFIG_FILE = ROOT / "config.yaml"

USER_AGENT = "cyber-influence-bot/0.1 (+local; research)"


@dataclass
class Signal:
    title: str
    url: str
    summary: str
    source: str
    published: str | None
    weight: int
    tags: list[str] = field(default_factory=list)
    score: int = 0
    matched_keywords: list[str] = field(default_factory=list)
    age_hours: float | None = None


def load_config() -> dict[str, Any]:
    with CONFIG_FILE.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)


def load_seen() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"urls": {}}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save_seen(seen: dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")


def url_key(url: str) -> str:
    return hashlib.sha1(url.strip().encode("utf-8")).hexdigest()


def fetch_url(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _text(el: ET.Element | None) -> str:
    if el is None or el.text is None:
        return ""
    return el.text.strip()


def _find_link(item: ET.Element) -> str:
    # RSS 2.0
    link = item.find("link")
    if link is not None and (link.text or "").strip():
        return link.text.strip()
    # Atom
    for el in item.findall("{http://www.w3.org/2005/Atom}link"):
        href = el.attrib.get("href")
        if href:
            return href
    guid = item.find("guid")
    if guid is not None and (guid.text or "").strip().startswith("http"):
        return guid.text.strip()
    return ""


def _find_date(item: ET.Element) -> str | None:
    for tag in ("pubDate", "published", "updated", "{http://www.w3.org/2005/Atom}published"):
        el = item.find(tag)
        if el is not None and (el.text or "").strip():
            return el.text.strip()
    return None


def _find_summary(item: ET.Element) -> str:
    for tag in (
        "description",
        "summary",
        "{http://purl.org/rss/1.0/modules/content/}encoded",
        "{http://www.w3.org/2005/Atom}summary",
        "{http://www.w3.org/2005/Atom}content",
    ):
        el = item.find(tag)
        if el is not None:
            raw = "".join(el.itertext()).strip()
            if raw:
                return strip_html(raw)[:600]
    return ""


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_feed(xml_bytes: bytes, source: str, weight: int, tags: list[str]) -> list[Signal]:
    root = ET.fromstring(xml_bytes)
    items: list[ET.Element] = []
    items.extend(root.findall("./channel/item"))
    items.extend(root.findall(".//{http://www.w3.org/2005/Atom}entry"))

    signals: list[Signal] = []
    for item in items:
        title = _text(item.find("title")) or _text(item.find("{http://www.w3.org/2005/Atom}title"))
        url = _find_link(item)
        if not title or not url:
            continue
        signals.append(
            Signal(
                title=title,
                url=url,
                summary=_find_summary(item),
                source=source,
                published=_find_date(item),
                weight=weight,
                tags=list(tags),
            )
        )
    return signals


def parse_published(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            cleaned = value.replace("Z", "+0000") if fmt.endswith("%z") else value
            dt = datetime.strptime(cleaned[:26].rstrip("Z"), fmt.replace("%z", "").rstrip())
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
    # ISO fallback
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def score_signal(sig: Signal, cfg: dict[str, Any], now: datetime) -> Signal:
    text = f"{sig.title} {sig.summary}".lower()
    kw = cfg["keywords"]
    matched: list[str] = []
    score = sig.weight

    for word in kw.get("high", []):
        if word.lower() in text:
            score += 18
            matched.append(word)
    for word in kw.get("medium", []):
        if word.lower() in text:
            score += 8
            matched.append(word)
    for word in kw.get("low", []):
        if word.lower() in text:
            score += 3
            matched.append(word)

    published = parse_published(sig.published)
    if published:
        age = (now - published.astimezone(timezone.utc)).total_seconds() / 3600
        sig.age_hours = round(age, 1)
        if age <= 6:
            score += 20
        elif age <= 24:
            score += 12
        elif age <= 72:
            score += 5
        else:
            score -= 10
    else:
        score += 2

    # de-dupe keyword inflation
    matched = sorted(set(matched), key=lambda x: (-len(x), x))
    sig.matched_keywords = matched[:12]
    sig.score = max(0, min(100, int(score)))
    return sig


def collect_signals(cfg: dict[str, Any]) -> list[Signal]:
    now = datetime.now(timezone.utc)
    all_signals: list[Signal] = []
    errors: list[str] = []

    for feed in cfg.get("rss_feeds", []):
        try:
            raw = fetch_url(feed["url"])
            parsed = parse_feed(raw, feed["name"], int(feed.get("weight", 10)), feed.get("tags", []))
            for s in parsed:
                all_signals.append(score_signal(s, cfg, now))
        except Exception as exc:  # noqa: BLE001 — jeden feed nie powinien wywalić całego runu
            errors.append(f"{feed['name']}: {exc}")

    if errors:
        print("Ostrzeżenia (feedy):")
        for e in errors:
            print(f"  - {e}")

    # dedupe po URL (najwyższy score wygrywa)
    best: dict[str, Signal] = {}
    for s in all_signals:
        key = s.url.split("?")[0].rstrip("/")
        prev = best.get(key)
        if prev is None or s.score > prev.score:
            best[key] = s
    return sorted(best.values(), key=lambda x: x.score, reverse=True)


def is_fresh_enough(url: str, seen: dict[str, Any], hours: int) -> bool:
    entry = seen.get("urls", {}).get(url_key(url))
    if not entry:
        return True
    try:
        ts = datetime.fromisoformat(entry["ts"])
    except Exception:
        return True
    return datetime.now(timezone.utc) - ts > timedelta(hours=hours)


def mark_seen(url: str, seen: dict[str, Any], title: str) -> None:
    seen.setdefault("urls", {})[url_key(url)] = {
        "url": url,
        "title": title,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def bullets_from_summary(summary: str, title: str) -> str:
    parts = [p.strip(" .;-•") for p in re.split(r"[.!?]\s+", summary) if len(p.strip()) > 25]
    if not parts:
        parts = [title]
    lines = []
    for i, p in enumerate(parts[:3], 1):
        lines.append(f"{i}) {p[:140]}")
    return "\n".join(lines)


def build_frame(sig: Signal) -> str:
    t = f"{sig.title} {sig.summary}".lower()
    if any(k in t for k in ("wyciek", "breach", "dane", "pesel", "medycz")):
        return "To nie jest tylko „incydent IT” — to test odpowiedzialności za dane i łańcuch powierzeń."
    if any(k in t for k in ("phishing", "oszust", "sms", "fałszyw")):
        return "Skala i powtarzalność schematu mówi więcej niż pojedynczy przypadek."
    if any(k in t for k in ("ransomware", "malware", "apt", "ddos")):
        return "Pytanie nie brzmi „czy atak był możliwy?”, tylko „jak szybko widać skutki dla usług i ludzi”."
    if any(k in t for k in ("ai act", "kribsi", "nis2", "compliance", "rodo", "uodo")):
        return "Prawo bez egzekucji i bez praktyki w firmach to tylko teatr compliance."
    return "Kluczowe nie jest „co się stało”, tylko kto ma realną odpowiedzialność i deadline naprawczy."


def build_question(sig: Signal) -> str:
    t = f"{sig.title} {sig.summary}".lower()
    if "wyciek" in t or "dane" in t:
        return "kto odpowiada, gdy vendor trzyma dane milionów osób?"
    if "phishing" in t:
        return "dlaczego ten sam schemat wraca co kilka tygodni?"
    if "ai act" in t or "kribsi" in t:
        return "czy czekamy na pierwsze kary, czy na kolejny incydent?"
    return "co trzeba zmienić systemowo, zanim będzie następny raz?"


def clean_title(title: str) -> str:
    title = re.sub(r"\s*\[(?:OPINIA|ANALIZA|KOMENTARZ|NEWS)\]\s*$", "", title, flags=re.I)
    title = re.sub(r"\s+", " ", title).strip(" .")
    return title


def draft_templates(sig: Signal, cfg: dict[str, Any]) -> dict[str, str]:
    templates = cfg["templates"]
    hook = clean_title(sig.title)
    if len(hook) > 110:
        hook = hook[:107] + "…"
    frame = build_frame(sig)
    question = build_question(sig)
    bullets = bullets_from_summary(sig.summary, sig.title)
    ctx = {
        "hook": hook,
        "frame": frame,
        "question": question,
        "bullets": bullets,
        "source": sig.source,
        "url": sig.url,
    }
    return {
        "short": templates["short"].format(**ctx).strip(),
        "medium": templates["medium"].format(**ctx).strip(),
        "sharp": templates["sharp"].format(**ctx).strip(),
    }


def maybe_llm_polish(text: str, style: str) -> str | None:
    """Opcjonalne dopieszczenie draftu przez OpenAI-compatible API."""
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        return None
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    prompt = (
        "Jesteś ekspertem cyber w PL. Przepiszesz draft posta na X/LinkedIn.\n"
        f"Styl: {style}. Zachowaj fakty, nie wymyślaj liczb. Max 700 znaków. "
        "Polski, konkret, bez emoji i bez clickbaitu.\n\n"
        f"DRAFT:\n{text}"
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Odpowiadasz tylko gotowym tekstem posta."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # noqa: BLE001
        print(f"LLM niedostępny ({exc}) — zostawiam szablon.")
        return None


def write_draft_file(sig: Signal, drafts: dict[str, str], cfg: dict[str, Any]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    host = urlparse(sig.url).netloc.replace("www.", "")
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", host)[:40]
    path = DRAFTS_DIR / f"{stamp}-{slug}-score{sig.score}.md"

    accounts = cfg.get("x_accounts", {})
    priority = ", ".join(accounts.get("priority", [])[:8])
    amplify = ", ".join(accounts.get("amplify", [])[:8])

    content = f"""# Draft — score {sig.score}/100

- **Tytuł:** {sig.title}
- **Źródło:** {sig.source}
- **URL:** {sig.url}
- **Opublikowano:** {sig.published or "?"}
- **Wiek:** {sig.age_hours if sig.age_hours is not None else "?"} h
- **Keywords:** {", ".join(sig.matched_keywords) or "—"}
- **Status:** PENDING_APPROVAL

## Short (X)

{drafts["short"]}

## Medium (LinkedIn / wątek)

{drafts["medium"]}

## Sharp (framing)

{drafts["sharp"]}

## Piggyback — skomentuj / zacytuj

Priority: {priority}

Amplify: {amplify}

## Checklist

- [ ] Sprawdź fakty w źródle
- [ ] Opublikuj SHORT na X
- [ ] Wrzuć 3–5 komentarzy pod dużymi kontami
- [ ] Opublikuj MEDIUM na LinkedIn
- [ ] Zaznacz DONE
"""
    path.write_text(content, encoding="utf-8")
    return path


def notify_telegram(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    payload = json.dumps({"chat_id": chat_id, "text": text[:3500]}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=20).read()
    except Exception as exc:  # noqa: BLE001
        print(f"Telegram notify failed: {exc}")


def run_once(use_llm: bool = True) -> list[Path]:
    load_dotenv(ROOT / ".env")
    ensure_dirs()
    cfg = load_config()
    seen = load_seen()
    signals = collect_signals(cfg)

    min_score = int(cfg.get("min_score", 45))
    max_drafts = int(cfg.get("max_drafts_per_run", 3))
    dedupe_hours = int(cfg.get("dedupe_hours", 48))

    candidates = [
        s
        for s in signals
        if s.score >= min_score and is_fresh_enough(s.url, seen, dedupe_hours)
    ][:max_drafts]

    print(f"Zebrano {len(signals)} sygnałów, do draftów: {len(candidates)} (min_score={min_score})")
    written: list[Path] = []

    for sig in candidates:
        drafts = draft_templates(sig, cfg)
        if use_llm:
            for key, style in (("short", "krótki post X"), ("medium", "post LinkedIn"), ("sharp", "ostry framing")):
                polished = maybe_llm_polish(drafts[key], style)
                if polished:
                    drafts[key] = polished
        path = write_draft_file(sig, drafts, cfg)
        mark_seen(sig.url, seen, sig.title)
        written.append(path)
        print(f"  [{sig.score}] {sig.source}: {sig.title[:80]}")
        print(f"      -> {path.name}")
        notify_telegram(
            f"Cyber draft ({sig.score}/100)\n{sig.title}\n{sig.url}\nPlik: {path.name}"
        )

    save_seen(seen)

    # ranking do podglądu
    ranking_path = DATA_DIR / "last_ranking.json"
    ranking_path.write_text(
        json.dumps([asdict(s) for s in signals[:30]], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return written


def run_loop(interval_minutes: int = 30, use_llm: bool = True) -> None:
    print(f"Loop co {interval_minutes} min. Ctrl+C aby przerwać.")
    while True:
        try:
            run_once(use_llm=use_llm)
        except Exception as exc:  # noqa: BLE001
            print(f"Błąd przebiegu: {exc}")
        time.sleep(max(60, interval_minutes * 60))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cyber influence bot")
    parser.add_argument("--once", action="store_true", help="Jeden przebieg i wyjście")
    parser.add_argument("--loop", action="store_true", help="Pętla co N minut")
    parser.add_argument("--interval", type=int, default=30, help="Interwał pętli w minutach")
    parser.add_argument("--no-llm", action="store_true", help="Tylko szablony, bez LLM")
    args = parser.parse_args()

    if args.loop:
        run_loop(args.interval, use_llm=not args.no_llm)
    else:
        run_once(use_llm=not args.no_llm)
