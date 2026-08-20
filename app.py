"""Proste UI Streamlit dla cyber influence bot."""

from __future__ import annotations

import re
from pathlib import Path

import streamlit as st
import yaml

import bot

ROOT = bot.ROOT
DRAFTS_DIR = bot.DRAFTS_DIR
DATA_DIR = bot.DATA_DIR
CONFIG_FILE = bot.CONFIG_FILE


def list_drafts() -> list[Path]:
    if not DRAFTS_DIR.exists():
        return []
    return sorted(DRAFTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)


def parse_draft(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    for key in ("Tytuł", "Źródło", "URL", "Opublikowano", "Wiek", "Keywords", "Status"):
        m = re.search(rf"- \*\*{key}:\*\* (.+)", text)
        if m:
            meta[key] = m.group(1).strip()

    score_m = re.search(r"score\s+(\d+)/100", text, re.I)
    sections = {
        "short": _section(text, "Short"),
        "medium": _section(text, "Medium"),
        "sharp": _section(text, "Sharp"),
        "piggyback": _section(text, "Piggyback"),
    }
    return {
        "path": path,
        "name": path.name,
        "score": int(score_m.group(1)) if score_m else 0,
        "meta": meta,
        "sections": sections,
        "raw": text,
        "status": meta.get("Status", "PENDING_APPROVAL"),
    }


def _section(text: str, heading: str) -> str:
    pattern = rf"## {heading}.*?\n+(.*?)(?=\n## |\Z)"
    m = re.search(pattern, text, re.S | re.I)
    return m.group(1).strip() if m else ""


def set_status(path: Path, status: str) -> None:
    text = path.read_text(encoding="utf-8")
    if re.search(r"- \*\*Status:\*\* .+", text):
        text = re.sub(r"- \*\*Status:\*\* .+", f"- **Status:** {status}", text)
    else:
        text = text.replace("\n## Short", f"\n- **Status:** {status}\n\n## Short", 1)
    path.write_text(text, encoding="utf-8")


def save_section(path: Path, section_key: str, new_body: str) -> None:
    text = path.read_text(encoding="utf-8")
    heading_map = {
        "short": r"Short \(X\)",
        "medium": r"Medium \(LinkedIn / wątek\)",
        "sharp": r"Sharp \(framing\)",
    }
    heading = heading_map[section_key]
    pattern = rf"(## {heading}\n\n)(.*?)(?=\n## |\Z)"
    repl = rf"\1{new_body.strip()}\n\n"
    updated, n = re.subn(pattern, repl, text, count=1, flags=re.S)
    if n == 0:
        raise ValueError(f"Nie znaleziono sekcji {section_key}")
    path.write_text(updated, encoding="utf-8")


def load_ranking() -> list[dict]:
    path = DATA_DIR / "last_ranking.json"
    if not path.exists():
        return []
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def page_home() -> None:
    st.title("Cyber Influence Bot")
    st.caption("RSS → score → drafty postów → akceptacja")

    c1, c2, c3 = st.columns(3)
    drafts = list_drafts()
    pending = [d for d in drafts if "DONE" not in parse_draft(d).get("status", "")]
    ranking = load_ranking()

    c1.metric("Drafty", len(drafts))
    c2.metric("Do akceptacji", len(pending))
    c3.metric("Ostatni ranking", len(ranking))

    st.subheader("Uruchom pipeline")
    use_llm = st.checkbox("Użyj LLM (wymaga klucza w .env)", value=False)
    if st.button("Zbierz sygnały i wygeneruj drafty", type="primary"):
        with st.spinner("Zbieram feedy i generuję drafty…"):
            written = bot.run_once(use_llm=use_llm)
        if written:
            st.success(f"Wygenerowano {len(written)} draft(ów)")
            for p in written:
                st.write(f"- `{p.name}`")
        else:
            st.info("Brak nowych sygnałów powyżej progu (albo wszystkie już widziane).")
        st.rerun()

    st.divider()
    st.subheader("Szybki start dnia")
    st.markdown(
        """
1. Kliknij **Zbierz sygnały…**
2. Wejdź w **Drafty** i wybierz score ≥ 60
3. Skopiuj **Short** → X
4. Wrzuć 3–5 komentarzy z listy Priority
5. Skopiuj **Medium** → LinkedIn
6. Oznacz jako DONE
"""
    )


def page_ranking() -> None:
    st.title("Ranking sygnałów")
    ranking = load_ranking()
    if not ranking:
        st.warning("Brak rankingu. Najpierw uruchom pipeline na stronie głównej.")
        return

    rows = [
        {
            "score": r.get("score", 0),
            "source": r.get("source", ""),
            "title": r.get("title", ""),
            "age_h": r.get("age_hours"),
            "keywords": ", ".join(r.get("matched_keywords") or []),
            "url": r.get("url", ""),
        }
        for r in ranking
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption("Top 30 z ostatniego przebiegu (`data/last_ranking.json`).")


def page_drafts() -> None:
    st.title("Drafty")
    drafts = list_drafts()
    if not drafts:
        st.info("Brak draftów. Uruchom pipeline na stronie głównej.")
        return

    parsed = [parse_draft(p) for p in drafts]
    status_filter = st.selectbox("Filtr statusu", ["Wszystkie", "PENDING_APPROVAL", "APPROVED", "DONE"])
    if status_filter != "Wszystkie":
        parsed = [d for d in parsed if d["status"] == status_filter]

    names = [f"{d['score']:>3} | {d['status']:<16} | {d['name']}" for d in parsed]
    if not names:
        st.info("Brak draftów dla tego filtra.")
        return

    choice = st.selectbox("Wybierz draft", names, key="draft_select")
    draft = parsed[names.index(choice)]
    draft_id = draft["name"]  # unikalny klucz widgetów przy zmianie draftu

    meta = draft["meta"]
    st.markdown(f"**{meta.get('Tytuł', draft['name'])}**")
    m1, m2, m3 = st.columns(3)
    m1.write(f"Score: **{draft['score']}**")
    m2.write(f"Źródło: **{meta.get('Źródło', '?')}**")
    m3.write(f"Status: **{draft['status']}**")
    if meta.get("URL"):
        st.link_button("Otwórz źródło", meta["URL"])

    tab_s, tab_m, tab_h, tab_p = st.tabs(["Short (X)", "Medium (LI)", "Sharp", "Piggyback"])

    with tab_s:
        short = st.text_area(
            "Short",
            draft["sections"]["short"],
            height=160,
            key=f"short_edit_{draft_id}",
        )
        b1, b2 = st.columns(2)
        if b1.button("Zapisz Short", key=f"save_short_{draft_id}"):
            save_section(draft["path"], "short", short)
            st.success("Zapisano")
        b2.code(short, language=None)

    with tab_m:
        medium = st.text_area(
            "Medium",
            draft["sections"]["medium"],
            height=240,
            key=f"medium_edit_{draft_id}",
        )
        b1, b2 = st.columns(2)
        if b1.button("Zapisz Medium", key=f"save_medium_{draft_id}"):
            save_section(draft["path"], "medium", medium)
            st.success("Zapisano")
        b2.code(medium, language=None)

    with tab_h:
        sharp = st.text_area(
            "Sharp",
            draft["sections"]["sharp"],
            height=180,
            key=f"sharp_edit_{draft_id}",
        )
        b1, b2 = st.columns(2)
        if b1.button("Zapisz Sharp", key=f"save_sharp_{draft_id}"):
            save_section(draft["path"], "sharp", sharp)
            st.success("Zapisano")
        b2.code(sharp, language=None)

    with tab_p:
        st.markdown(draft["sections"]["piggyback"] or "_brak_")

    st.divider()
    a1, a2, a3 = st.columns(3)
    if a1.button("Oznacz APPROVED", use_container_width=True, key=f"approved_{draft_id}"):
        set_status(draft["path"], "APPROVED")
        st.rerun()
    if a2.button("Oznacz DONE", type="primary", use_container_width=True, key=f"done_{draft_id}"):
        set_status(draft["path"], "DONE")
        st.rerun()
    if a3.button("Cofnij do PENDING", use_container_width=True, key=f"pending_{draft_id}"):
        set_status(draft["path"], "PENDING_APPROVAL")
        st.rerun()


def page_config() -> None:
    st.title("Konfiguracja")
    cfg = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8"))

    st.write("Aktualne progi:")
    st.json(
        {
            "min_score": cfg.get("min_score"),
            "max_drafts_per_run": cfg.get("max_drafts_per_run"),
            "dedupe_hours": cfg.get("dedupe_hours"),
            "feeds": [f["name"] for f in cfg.get("rss_feeds", [])],
        }
    )

    st.subheader("Konta X (Priority)")
    st.write(", ".join(cfg.get("x_accounts", {}).get("priority", [])))

    st.subheader("Edycja pliku")
    st.caption("Zmiany zaawansowane rób w `config.yaml`, potem odśwież UI.")
    edited = st.text_area("config.yaml", CONFIG_FILE.read_text(encoding="utf-8"), height=420)
    if st.button("Zapisz config.yaml"):
        yaml.safe_load(edited)  # walidacja
        CONFIG_FILE.write_text(edited, encoding="utf-8")
        st.success("Zapisano config.yaml")


def main() -> None:
    st.set_page_config(
        page_title="Cyber Influence Bot",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.2rem; max-width: 1100px; }
        div[data-testid="stMetricValue"] { font-size: 1.6rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### Nawigacja")
        page = st.radio(
            "Strona",
            ["Start", "Drafty", "Ranking", "Config"],
            label_visibility="collapsed",
        )
        st.divider()
        st.caption("Lokalny panel. Bez autoposta na X.")

    if page == "Start":
        page_home()
    elif page == "Drafty":
        page_drafts()
    elif page == "Ranking":
        page_ranking()
    else:
        page_config()


if __name__ == "__main__":
    main()
