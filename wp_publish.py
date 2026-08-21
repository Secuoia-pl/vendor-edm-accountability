"""Publikacja huba na WordPress (REST API + Application Password)."""

from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
WP_DIR = ROOT / "wordpress"
INDEX_HTML = WP_DIR / "hub-index.html"
HUB_HTML = WP_DIR / "strona-hub.html"
CHECKLIST_HTML = WP_DIR / "checklista-72h.html"
FAQ_SCHEMA = WP_DIR / "faq-schema.json"

CANONICAL_INDEX = "https://bezpiecznyblog.pl/hub-odpowiedzialnosci/"
CANONICAL_HUB = "https://bezpiecznyblog.pl/odpowiedzialnosc-vendora-edm/"
CANONICAL_CHECKLIST = "https://bezpiecznyblog.pl/checklista-72h-vendor-edm/"


def _load_env() -> None:
    load_dotenv(ROOT / ".env", override=False)
    sibling = Path(r"C:\Users\bkowa\Projects\architektura-szumu\studio\.env")
    if sibling.exists():
        load_dotenv(sibling, override=False)


def wp_config() -> dict[str, str]:
    _load_env()
    base = (os.getenv("WP_BASE_URL") or "https://bezpiecznyblog.pl").rstrip("/")
    return {
        "base_url": base,
        "user": (os.getenv("WP_USER") or "").strip(),
        "app_password": (os.getenv("WP_APP_PASSWORD") or "").strip().replace(" ", ""),
        "index_page_id": (os.getenv("WP_INDEX_PAGE_ID") or "").strip(),
        "hub_page_id": (os.getenv("WP_HUB_PAGE_ID") or "").strip(),
        "checklist_page_id": (os.getenv("WP_CHECKLIST_PAGE_ID") or "").strip(),
        "index_slug": (os.getenv("WP_INDEX_SLUG") or "hub-odpowiedzialnosci").strip(),
        "hub_slug": (os.getenv("WP_HUB_SLUG") or "odpowiedzialnosc-vendora-edm").strip(),
        "checklist_slug": (os.getenv("WP_CHECKLIST_SLUG") or "checklista-72h-vendor-edm").strip(),
    }


def is_configured() -> bool:
    cfg = wp_config()
    return bool(cfg["user"] and cfg["app_password"])


def _auth_header(user: str, app_password: str) -> str:
    token = base64.b64encode(f"{user}:{app_password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def _client(cfg: dict[str, str] | None = None) -> httpx.Client:
    cfg = cfg or wp_config()
    if not cfg["user"] or not cfg["app_password"]:
        raise RuntimeError(
            "Brak WP_USER / WP_APP_PASSWORD w .env "
            "(Uzytkownicy -> Profil -> Application Passwords)"
        )
    return httpx.Client(
        base_url=f"{cfg['base_url']}/wp-json/wp/v2",
        headers={
            "Authorization": _auth_header(cfg["user"], cfg["app_password"]),
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "vendor-edm-hub-publisher/0.1",
        },
        timeout=60.0,
    )


def strip_file_comment(html: str) -> str:
    """Usuń komentarz instrukcji z góry pliku wordpress/*.html."""
    return re.sub(r"^\s*<!--.*?-->\s*", "", html, count=1, flags=re.S).strip()


def wrap_wp_html_block(html: str) -> str:
    body = strip_file_comment(html)
    return f"<!-- wp:html -->\n{body}\n<!-- /wp:html -->"


def find_page_id_by_slug(slug: str) -> int | None:
    cfg = wp_config()
    with _client(cfg) as client:
        resp = client.get("/pages", params={"slug": slug, "status": "publish,draft,private"})
        if resp.status_code >= 400:
            raise RuntimeError(f"WP list pages HTTP {resp.status_code}: {resp.text[:300]}")
        items = resp.json()
    if not items:
        return None
    return int(items[0]["id"])


def resolve_page_id(explicit_id: str, slug: str) -> int:
    if explicit_id:
        return int(explicit_id)
    found = find_page_id_by_slug(slug)
    if found is None:
        raise RuntimeError(f"Nie znaleziono strony WP o slug={slug!r}. Ustaw WP_*_PAGE_ID.")
    return found


def update_page(
    page_id: int,
    *,
    content_html: str,
    title: str | None = None,
    parent: int | None = None,
    slug: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"content": wrap_wp_html_block(content_html)}
    if title:
        payload["title"] = title
    if parent is not None:
        payload["parent"] = int(parent)
    if slug:
        payload["slug"] = slug
    with _client() as client:
        resp = client.post(f"/pages/{page_id}", json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(f"WP update page {page_id} HTTP {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
    return {
        "id": data.get("id"),
        "link": data.get("link"),
        "modified": data.get("modified"),
        "status": data.get("status"),
        "parent": data.get("parent"),
    }


def create_page(
    *,
    title: str,
    slug: str,
    content_html: str,
    parent: int | None = None,
    status: str = "publish",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "title": title,
        "slug": slug,
        "status": status,
        "content": wrap_wp_html_block(content_html),
    }
    if parent is not None:
        payload["parent"] = int(parent)
    with _client() as client:
        resp = client.post("/pages", json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(f"WP create page HTTP {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
    return {
        "id": data.get("id"),
        "link": data.get("link"),
        "modified": data.get("modified"),
        "status": data.get("status"),
        "parent": data.get("parent"),
        "created": True,
    }


def ensure_page(
    *,
    explicit_id: str,
    slug: str,
    title: str,
    content_html: str,
    parent: int | None = None,
) -> dict[str, Any]:
    """Update if exists (by id/slug), otherwise create."""
    if explicit_id:
        return update_page(
            int(explicit_id),
            content_html=content_html,
            title=title,
            parent=parent,
            slug=slug,
        )
    existing = find_page_id_by_slug(slug)
    if existing is not None:
        return update_page(
            existing,
            content_html=content_html,
            title=title,
            parent=parent,
            slug=slug,
        )
    return create_page(title=title, slug=slug, content_html=content_html, parent=parent)


def discover_pages() -> list[dict[str, Any]]:
    """Lista stron — pomoc przy ustawianiu PAGE_ID."""
    with _client() as client:
        resp = client.get("/pages", params={"per_page": 50, "status": "publish,draft"})
        if resp.status_code >= 400:
            raise RuntimeError(f"WP discover HTTP {resp.status_code}: {resp.text[:300]}")
        items = resp.json()
    out = []
    for it in items:
        out.append(
            {
                "id": it.get("id"),
                "slug": it.get("slug"),
                "status": it.get("status"),
                "title": (it.get("title") or {}).get("rendered", ""),
                "link": it.get("link"),
            }
        )
    return out


def publish_hub_to_wordpress(
    *,
    include_checklist: bool = True,
    include_index: bool = True,
    nest_under_index: bool | None = None,
) -> dict[str, Any]:
    """Wyślij indeks + case (+ checklista) na WP.

    Domyślnie dzieci mają parent=0 (płaskie URL-e). Ustaw WP_NEST_PAGES=1,
    żeby zagnieździć je pod indeksem w drzewie stron WP.
    """
    cfg = wp_config()
    if nest_under_index is None:
        nest_under_index = (os.getenv("WP_NEST_PAGES") or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "tak",
        }

    result: dict[str, Any] = {
        "index": None,
        "hub": None,
        "checklist": None,
        "canonical_index": CANONICAL_INDEX,
        "canonical_hub": CANONICAL_HUB,
        "nested": nest_under_index,
    }

    index_id: int | None = None
    if include_index and INDEX_HTML.exists():
        index_res = ensure_page(
            explicit_id=cfg["index_page_id"],
            slug=cfg["index_slug"],
            title="Hub odpowiedzialności",
            content_html=INDEX_HTML.read_text(encoding="utf-8"),
            parent=None,
        )
        result["index"] = index_res
        index_id = int(index_res["id"])

    if not HUB_HTML.exists():
        raise FileNotFoundError(f"Brak {HUB_HTML}")

    child_parent = index_id if nest_under_index else 0

    hub_res = ensure_page(
        explicit_id=cfg["hub_page_id"],
        slug=cfg["hub_slug"],
        title="Odpowiedzialność vendora EDM przy wycieku danych zdrowotnych (case MyDr)",
        content_html=HUB_HTML.read_text(encoding="utf-8"),
        parent=child_parent,
    )
    result["hub"] = hub_res

    if include_checklist and CHECKLIST_HTML.exists():
        try:
            result["checklist"] = ensure_page(
                explicit_id=cfg["checklist_page_id"],
                slug=cfg["checklist_slug"],
                title="Checklista 72h — wyciek u vendora EDM / procesora",
                content_html=CHECKLIST_HTML.read_text(encoding="utf-8"),
                parent=child_parent,
            )
        except Exception as exc:  # noqa: BLE001
            result["checklist_error"] = str(exc)

    return result


def write_faq_schema(questions: list[dict[str, str]]) -> None:
    payload = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q["q"],
                "acceptedAnswer": {"@type": "Answer", "text": q["a"]},
            }
            for q in questions
        ],
    }
    WP_DIR.mkdir(parents=True, exist_ok=True)
    FAQ_SCHEMA.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    import argparse
    import sys

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    parser = argparse.ArgumentParser(description="WordPress REST publish for vendor-EDM hub")
    parser.add_argument("--discover", action="store_true", help="Wylistuj strony (id/slug)")
    parser.add_argument("--publish", action="store_true", help="Wypchnij indeks + case (+ checklista) na WP")
    parser.add_argument("--hub-only", action="store_true", help="Bez checklisty")
    parser.add_argument("--no-index", action="store_true", help="Bez strony nadrzednej")
    args = parser.parse_args()

    if args.discover:
        for row in discover_pages():
            print(f"{row['id']:>6}  {row['status']:<8}  /{row['slug']}/  {row['title'][:60]}")
    elif args.publish:
        out = publish_hub_to_wordpress(
            include_checklist=not args.hub_only,
            include_index=not args.no_index,
        )
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
