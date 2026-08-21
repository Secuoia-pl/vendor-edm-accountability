"""Zastosuj zaakceptowaną analizę do publicznego huba (docs/ + hub/) i opcjonalnie wypchnij Pages."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
HUB = ROOT / "hub"
DRAFTS = ROOT / "drafts"
WP_DIR = ROOT / "wordpress"
WP_HUB_HTML = WP_DIR / "strona-hub.html"

CANONICAL_BLOG = "https://bezpiecznyblog.pl/odpowiedzialnosc-vendora-edm/"


def today_iso() -> str:
    return date.today().isoformat()


def today_pl() -> str:
    d = date.today()
    return f"{d.day:02d}.{d.month:02d}.{d.year}"


def load_analyze_payload(md_path: Path) -> dict[str, Any]:
    """JSON sibling + nadpisanie z aktualnego MD (edycje w UI)."""
    json_path = md_path.with_suffix(".json")
    data: dict[str, Any] = {}
    if json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
    else:
        data = {
            "update_hub": True,
            "changelog_bullets": [],
            "new_faq": [],
            "rationale": "",
        }

    text = md_path.read_text(encoding="utf-8")
    changelog = _md_section(text, r"Changelog(?: \(propozycja\))?")
    faq = _md_section(text, r"Nowe FAQ")
    if changelog and changelog.strip() not in {"_brak_", ""}:
        bullets = [
            re.sub(r"^[-*]\s+", "", line).strip()
            for line in changelog.splitlines()
            if re.match(r"^[-*]\s+\S", line.strip())
        ]
        if bullets:
            data["changelog_bullets"] = bullets
    parsed_faq = _parse_faq_md(faq)
    if parsed_faq:
        data["new_faq"] = parsed_faq

    update_m = re.search(r"- \*\*Update hub:\*\* (.+)", text)
    if update_m:
        data["update_hub"] = update_m.group(1).strip().lower() in {"true", "1", "yes", "tak"}
    return data


def _md_section(text: str, heading: str) -> str:
    m = re.search(rf"## {heading}\n+(.*?)(?=\n## |\Z)", text, re.S | re.I)
    return m.group(1).strip() if m else ""


def _parse_faq_md(section: str) -> list[dict[str, str]]:
    if not section or section.strip() in {"_brak_", ""}:
        return []
    out: list[dict[str, str]] = []
    parts = re.split(r"\*\*Q:\*\*\s*", section)
    for part in parts[1:]:
        qa = re.split(r"\*\*A:\*\*\s*", part, maxsplit=1)
        if len(qa) != 2:
            continue
        q, a = qa[0].strip(), qa[1].strip()
        a = re.split(r"\n\s*\*\*Q:\*\*", a)[0].strip()
        if q and a:
            out.append({"q": q, "a": a})
    return out


def _faq_html(questions: list[dict[str, str]], *, indent: str = "    ") -> str:
    chunks = [f'{indent}<h2 id="faq">FAQ</h2>\n']
    for item in questions:
        q = escape(item["q"])
        a = escape(item["a"])
        chunks.append(f"\n{indent}<h3>{q}</h3>\n{indent}<p>{a}</p>\n")
    return "".join(chunks)


def _faq_jsonld(questions: list[dict[str, str]]) -> str:
    entities = []
    for item in questions:
        entities.append(
            {
                "@type": "Question",
                "name": item["q"],
                "acceptedAnswer": {"@type": "Answer", "text": item["a"]},
            }
        )
    payload = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": entities,
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    # wcięcie jak w oryginale
    indented = "\n".join(("  " + line if line else line) for line in body.splitlines())
    return f'  <script type="application/ld+json">\n{indented}\n  </script>'


def _replace_faq_jsonld(html: str, questions: list[dict[str, str]]) -> str:
    pattern = re.compile(
        r'  <script type="application/ld\+json">\s*\{\s*"@context": "https://schema\.org",\s*"@type": "FAQPage".*?</script>',
        re.S,
    )
    repl = _faq_jsonld(questions)
    updated, n = pattern.subn(repl, html, count=1)
    if n != 1:
        raise RuntimeError("Nie znaleziono bloku FAQPage JSON-LD w index.html")
    return updated


def _replace_faq_html(html: str, questions: list[dict[str, str]], *, indent: str = "    ") -> str:
    pattern = re.compile(r'<h2 id="faq">FAQ</h2>.*?(?=\n\s*<h2 id="cytowanie">)', re.S)
    m = re.search(r'^(\s*)<h2 id="faq">', html, re.M)
    prefix = m.group(1) if m else indent
    repl = _faq_html(questions, indent=prefix) + "\n"
    updated, n = pattern.subn(repl, html, count=1)
    if n != 1:
        raise RuntimeError("Nie znaleziono sekcji FAQ HTML")
    return updated


def _prepend_changelog(html: str, bullets: list[str], day: str) -> str:
    if not bullets:
        return html
    m = re.search(r'<h2 id="changelog">Changelog</h2>\s*<ul>(.*?)</ul>', html, re.S)
    existing = m.group(1) if m else ""
    fresh: list[str] = []
    for b in bullets:
        if escape(b) in existing or b in existing:
            continue
        fresh.append(b)
    if not fresh:
        return html
    items = "\n".join(f"  <li><strong>{day}</strong> — {escape(b)}</li>" for b in fresh)
    pattern = re.compile(r'(<h2 id="changelog">Changelog</h2>\s*<ul>\s*)', re.S)
    updated, n = pattern.subn(rf"\1{items}\n", html, count=1)
    if n != 1:
        raise RuntimeError("Nie znaleziono sekcji Changelog")
    return updated


def _apply_wordpress_mirror(questions: list[dict[str, str]], bullets: list[str], day: str, day_pl: str) -> list[str]:
    """Aktualizuj wordpress/strona-hub.html + faq-schema.json pod REST publish."""
    changed: list[str] = []
    if WP_HUB_HTML.exists():
        html = WP_HUB_HTML.read_text(encoding="utf-8")
        html = _touch_dates(html, day, day_pl)
        html = _replace_faq_html(html, questions, indent="")
        html = _prepend_changelog(html, bullets, day)
        # cytowanie: trzymaj URL bloga
        html = re.sub(
            r"(Bezpieczny Blog, stan na )[0-9]{2}\.[0-9]{2}\.[0-9]{4}",
            rf"\g<1>{day_pl}",
            html,
            count=1,
        )
        WP_HUB_HTML.write_text(html, encoding="utf-8")
        changed.append("wordpress/strona-hub.html")
    try:
        import wp_publish

        wp_publish.write_faq_schema(questions)
        changed.append("wordpress/faq-schema.json")
    except Exception:
        pass
    return changed


def _touch_dates(html: str, day: str, day_pl: str) -> str:
    html = re.sub(
        r'"dateModified":\s*"[0-9]{4}-[0-9]{2}-[0-9]{2}"',
        f'"dateModified": "{day}"',
        html,
        count=1,
    )
    html = re.sub(
        r"Stan na [0-9]{2}\.[0-9]{2}\.[0-9]{4}",
        f"Stan na {day_pl}",
        html,
        count=1,
    )
    html = re.sub(
        r"stan na [0-9]{2}\.[0-9]{2}\.[0-9]{4}",
        f"stan na {day_pl}",
        html,
        count=1,
    )
    return html


def _update_faq_json(path: Path, new_items: list[dict[str, str]], day: str) -> list[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    existing = data.get("questions") or []
    seen = {str(q.get("q", "")).strip().lower() for q in existing}
    for item in new_items:
        key = item["q"].strip().lower()
        if key in seen:
            continue
        existing.append({"q": item["q"].strip(), "a": item["a"].strip()})
        seen.add(key)
    data["questions"] = existing
    data["dateModified"] = day
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return existing


def _update_sitemap(path: Path, day: str) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<lastmod>[0-9]{4}-[0-9]{2}-[0-9]{2}</lastmod>", f"<lastmod>{day}</lastmod>", text)
    path.write_text(text, encoding="utf-8")


def _update_summary(path: Path, day: str, bullets: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"Last updated: .*", f"Last updated: {day}", text, count=1)
    if bullets:
        note = " | ".join(bullets[:2])
        if "## Recent" in text:
            text = re.sub(
                r"## Recent.*?(?=\n## |\Z)",
                f"## Recent\n- {day}: {note}\n\n",
                text,
                count=1,
                flags=re.S,
            )
        else:
            text = text.rstrip() + f"\n\n## Recent\n- {day}: {note}\n"
    path.write_text(text, encoding="utf-8")


def _mirror_to_hub(rel_names: list[str]) -> None:
    HUB.mkdir(parents=True, exist_ok=True)
    for name in rel_names:
        src = DOCS / name
        if src.exists():
            shutil.copy2(src, HUB / name)


def apply_to_hub(md_path: Path, *, force: bool = False) -> dict[str, Any]:
    payload = load_analyze_payload(md_path)
    if not payload.get("update_hub") and not force:
        return {
            "skipped": True,
            "reason": "update_hub=false — hub nie zmieniony (użyj force=True, by wymusić)",
        }

    day = today_iso()
    day_pl = today_pl()
    bullets = [b.strip() for b in (payload.get("changelog_bullets") or []) if str(b).strip()]
    new_faq = [
        {"q": str(x["q"]).strip(), "a": str(x["a"]).strip()}
        for x in (payload.get("new_faq") or [])
        if isinstance(x, dict) and x.get("q") and x.get("a")
    ]

    index_path = DOCS / "index.html"
    faq_path = DOCS / "faq.json"
    if not index_path.exists():
        raise FileNotFoundError(f"Brak {index_path}")

    questions = _update_faq_json(faq_path, new_faq, day)
    html = index_path.read_text(encoding="utf-8")
    html = _touch_dates(html, day, day_pl)
    html = _replace_faq_html(html, questions, indent="    ")
    html = _replace_faq_jsonld(html, questions)
    html = _prepend_changelog(html, bullets, day)
    index_path.write_text(html, encoding="utf-8")

    sitemap = DOCS / "sitemap.xml"
    if sitemap.exists():
        _update_sitemap(sitemap, day)
    summary = DOCS / "SUMMARY.md"
    if summary.exists():
        _update_summary(summary, day, bullets)

    changed = ["index.html", "faq.json", "sitemap.xml", "SUMMARY.md"]
    _mirror_to_hub(changed)
    changed.extend(_apply_wordpress_mirror(questions, bullets, day, day_pl))

    return {
        "skipped": False,
        "date": day,
        "changelog_added": len(bullets),
        "faq_total": len(questions),
        "faq_new": len(new_faq),
        "files": changed,
        "canonical": CANONICAL_BLOG,
    }


def git_push_hub(message: str | None = None) -> dict[str, Any]:
    msg = message or f"Update hub from approved analysis ({today_iso()})."
    cmds = [
        ["git", "add", "docs", "hub", "wordpress"],
        ["git", "commit", "-m", msg],
        ["git", "push", "origin", "HEAD:main"],
    ]
    logs: list[str] = []
    for cmd in cmds:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        logs.append(f"$ {' '.join(cmd)}\n{out.strip()}")
        if proc.returncode != 0:
            # commit bez zmian nie jest błędem krytycznym
            if cmd[1] == "commit" and "nothing to commit" in out.lower():
                continue
            return {"ok": False, "logs": logs}
    return {"ok": True, "logs": logs}


def mark_draft_published(md_path: Path, result: dict[str, Any]) -> None:
    text = md_path.read_text(encoding="utf-8")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    note = f"- **Hub published:** {stamp} ({result.get('changelog_added', 0)} changelog, FAQ total {result.get('faq_total', '?')})"
    if re.search(r"- \*\*Hub published:\*\* ", text):
        text = re.sub(r"- \*\*Hub published:\*\* .+", note, text)
    else:
        text = re.sub(r"(- \*\*Status:\*\* .+\n)", rf"\1{note}\n", text, count=1)
    md_path.write_text(text, encoding="utf-8")


def publish_analyze_draft(
    md_path: Path,
    *,
    force: bool = False,
    push: bool = True,
    push_wordpress: bool = True,
) -> dict[str, Any]:
    applied = apply_to_hub(md_path, force=force)
    out: dict[str, Any] = {"apply": applied, "push": None, "wordpress": None}
    if applied.get("skipped"):
        return out
    mark_draft_published(md_path, applied)
    if push:
        out["push"] = git_push_hub(
            f"Publish hub update from {md_path.name} ({applied.get('date')})."
        )
    if push_wordpress:
        try:
            import wp_publish

            if wp_publish.is_configured():
                out["wordpress"] = wp_publish.publish_hub_to_wordpress(include_checklist=True)
            else:
                out["wordpress"] = {
                    "skipped": True,
                    "reason": "Brak WP_USER / WP_APP_PASSWORD w .env",
                }
        except Exception as exc:  # noqa: BLE001
            out["wordpress"] = {"ok": False, "error": str(exc)}
    return out
