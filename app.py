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


def draft_kind(path: Path) -> str:
    return "analyze" if path.name.startswith("analyze-") else "post"


def parse_draft(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    kind = draft_kind(path)
    meta: dict[str, str] = {}
    for key in (
        "Tytuł",
        "Źródło",
        "URL",
        "Opublikowano",
        "Wiek",
        "Keywords",
        "Status",
        "Provider",
        "Update hub",
        "Sygnałów wejściowych",
    ):
        m = re.search(rf"- \*\*{key}:\*\* (.+)", text)
        if m:
            meta[key] = m.group(1).strip()

    score_m = re.search(r"score\s+(\d+)/100", text, re.I)
    if kind == "analyze":
        sections = {
            "rationale": _section(text, "Rationale"),
            "signals": _section(text, "Sygnały użyte"),
            "changelog": _section(text, "Changelog"),
            "faq": _section(text, "Nowe FAQ"),
            "linkedin": _section(text, "LinkedIn"),
            "x_thread": _section(text, "Wątek X"),
            "verify": _section(text, "Do weryfikacji"),
            "hub": _section(text, "Hub"),
        }
        title = "Analiza hub"
        if meta.get("Update hub"):
            title = f"Analiza hub (update={meta['Update hub']})"
    else:
        sections = {
            "short": _section(text, "Short"),
            "medium": _section(text, "Medium"),
            "sharp": _section(text, "Sharp"),
            "piggyback": _section(text, "Piggyback"),
        }
        title = meta.get("Tytuł", path.name)

    return {
        "path": path,
        "name": path.name,
        "kind": kind,
        "title": title,
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
        # analyze drafts: status jest w bloku meta przed pierwszą sekcją ##
        if draft_kind(path) == "analyze":
            text = re.sub(r"(\n)(## )", rf"\1- **Status:** {status}\n\n\2", text, count=1)
        else:
            text = text.replace("\n## Short", f"\n- **Status:** {status}\n\n## Short", 1)
    path.write_text(text, encoding="utf-8")


def save_section(path: Path, section_key: str, new_body: str) -> None:
    text = path.read_text(encoding="utf-8")
    heading_map = {
        "short": r"Short \(X\)",
        "medium": r"Medium \(LinkedIn / wątek\)",
        "sharp": r"Sharp \(framing\)",
        "linkedin": r"LinkedIn \(copy-paste\)",
        "x_thread": r"Wątek X",
        "changelog": r"Changelog \(propozycja\)",
        "faq": r"Nowe FAQ",
        "rationale": r"Rationale",
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
    st.caption("RSS -> score -> drafty postow / analiz hub -> akceptacja")

    c1, c2, c3 = st.columns(3)
    drafts = list_drafts()
    pending = [d for d in drafts if "DONE" not in parse_draft(d).get("status", "")]
    ranking = load_ranking()

    c1.metric("Drafty", len(drafts))
    c2.metric("Do akceptacji", len(pending))
    c3.metric("Ostatni ranking", len(ranking))

    st.subheader("Uruchom pipeline")
    use_llm = st.checkbox("Użyj LLM do draftów postów (wymaga klucza w .env)", value=False)
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

    st.subheader("Analiza pod hub (Atlas / Wiro)")
    dry = st.checkbox("Dry-run (bez API, lokalna heurystyka)", value=False)
    if st.button("Uruchom analyze.py"):
        import analyze

        with st.spinner("Analizuję sygnały…"):
            result = analyze.run_analyze(dry_run=dry, provider=None if dry else "atlas")
        st.success(f"update_hub={result.get('update_hub')} — draft w zakładce Drafty")
        st.rerun()

    st.divider()
    st.subheader("Szybki start dnia")
    st.markdown(
        """
1. Kliknij **Zbierz sygnały…** albo **Uruchom analyze.py**
2. Wejdź w **Drafty** — posty (`score-…`) albo analizy (`analyze-…`)
3. Skopiuj treść → X / LinkedIn (albo zaktualizuj hub)
4. Oznacz jako DONE
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


def _editable_block(draft_id: str, path: Path, key: str, label: str, body: str, height: int) -> None:
    edited = st.text_area(label, body, height=height, key=f"{key}_edit_{draft_id}")
    b1, b2 = st.columns(2)
    if b1.button(f"Zapisz {label}", key=f"save_{key}_{draft_id}"):
        save_section(path, key, edited)
        st.success("Zapisano")
    b2.code(edited, language=None)


def page_drafts() -> None:
    st.title("Drafty")
    drafts = list_drafts()
    if not drafts:
        st.info("Brak draftów. Uruchom pipeline na stronie głównej.")
        return

    parsed = [parse_draft(p) for p in drafts]
    f1, f2 = st.columns(2)
    kind_filter = f1.selectbox("Typ", ["Wszystkie", "Posty", "Analizy hub"])
    status_filter = f2.selectbox("Status", ["Wszystkie", "PENDING_APPROVAL", "APPROVED", "DONE"])
    if kind_filter == "Posty":
        parsed = [d for d in parsed if d["kind"] == "post"]
    elif kind_filter == "Analizy hub":
        parsed = [d for d in parsed if d["kind"] == "analyze"]
    if status_filter != "Wszystkie":
        parsed = [d for d in parsed if d["status"] == status_filter]

    def _label(d: dict) -> str:
        tag = "ANALIZA" if d["kind"] == "analyze" else f"{d['score']:>3}"
        return f"{tag} | {d['status']:<16} | {d['name']}"

    names = [_label(d) for d in parsed]
    if not names:
        st.info("Brak draftów dla tego filtra.")
        return

    choice = st.selectbox("Wybierz draft", names, key="draft_select")
    draft = parsed[names.index(choice)]
    draft_id = draft["name"]

    meta = draft["meta"]
    st.markdown(f"**{draft.get('title') or meta.get('Tytuł', draft['name'])}**")
    m1, m2, m3 = st.columns(3)
    if draft["kind"] == "analyze":
        m1.write(f"Update hub: **{meta.get('Update hub', '?')}**")
        m2.write(f"Provider: **{meta.get('Provider', '?')}**")
    else:
        m1.write(f"Score: **{draft['score']}**")
        m2.write(f"Źródło: **{meta.get('Źródło', '?')}**")
    m3.write(f"Status: **{draft['status']}**")
    if meta.get("URL"):
        st.link_button("Otwórz źródło", meta["URL"])

    if draft["kind"] == "analyze":
        tabs = st.tabs(
            ["LinkedIn", "Wątek X", "Changelog", "FAQ", "Rationale", "Weryfikacja", "Raw MD"]
        )
        with tabs[0]:
            _editable_block(
                draft_id, draft["path"], "linkedin", "LinkedIn", draft["sections"]["linkedin"], 260
            )
        with tabs[1]:
            _editable_block(
                draft_id, draft["path"], "x_thread", "Wątek X", draft["sections"]["x_thread"], 280
            )
        with tabs[2]:
            _editable_block(
                draft_id, draft["path"], "changelog", "Changelog", draft["sections"]["changelog"], 180
            )
        with tabs[3]:
            _editable_block(draft_id, draft["path"], "faq", "FAQ", draft["sections"]["faq"], 220)
        with tabs[4]:
            st.markdown(draft["sections"]["rationale"] or "_brak_")
            st.markdown("##### Sygnały")
            st.markdown(draft["sections"]["signals"] or "_brak_")
        with tabs[5]:
            st.markdown(draft["sections"]["verify"] or "_brak_")
            hub = draft["sections"]["hub"]
            if hub:
                st.info(hub)
        with tabs[6]:
            st.code(draft["raw"], language="markdown")
    else:
        tab_s, tab_m, tab_h, tab_p = st.tabs(["Short (X)", "Medium (LI)", "Sharp", "Piggyback"])
        with tab_s:
            _editable_block(draft_id, draft["path"], "short", "Short", draft["sections"]["short"], 160)
        with tab_m:
            _editable_block(
                draft_id, draft["path"], "medium", "Medium", draft["sections"]["medium"], 240
            )
        with tab_h:
            _editable_block(draft_id, draft["path"], "sharp", "Sharp", draft["sections"]["sharp"], 180)
        with tab_p:
            st.markdown(draft["sections"]["piggyback"] or "_brak_")

    st.divider()
    push_pages = False
    push_wp = False
    force_hub = False
    if draft["kind"] == "analyze":
        push_pages = st.checkbox(
            "Przy DONE: zaktualizuj lustro GitHub Pages i wypchnij na main",
            value=True,
            key=f"push_pages_{draft_id}",
        )
        push_wp = st.checkbox(
            "Przy DONE: wypchnij na bezpiecznyblog.pl (WP REST)",
            value=True,
            key=f"push_wp_{draft_id}",
        )
        if str(meta.get("Update hub", "")).lower() not in {"true", "1", "yes", "tak"}:
            force_hub = st.checkbox(
                "Wymus update huba mimo update_hub=false",
                value=False,
                key=f"force_hub_{draft_id}",
            )

    a1, a2, a3 = st.columns(3)
    if a1.button("Oznacz APPROVED", use_container_width=True, key=f"approved_{draft_id}"):
        set_status(draft["path"], "APPROVED")
        st.rerun()
    if a2.button("Oznacz DONE", type="primary", use_container_width=True, key=f"done_{draft_id}"):
        set_status(draft["path"], "DONE")
        if draft["kind"] == "analyze" and (push_pages or push_wp):
            import hub_publish

            with st.spinner("Publikuje hub (Pages / WordPress)..."):
                result = hub_publish.publish_analyze_draft(
                    draft["path"],
                    force=force_hub,
                    push=push_pages,
                    push_wordpress=push_wp,
                )
            apply = result.get("apply") or {}
            if apply.get("skipped"):
                st.warning(apply.get("reason", "Hub pominiety"))
            else:
                st.success(
                    f"Lokalnie OK: +{apply.get('changelog_added', 0)} changelog, "
                    f"FAQ lacznie {apply.get('faq_total')}"
                )
                st.caption("Kanonicznie: https://bezpiecznyblog.pl/odpowiedzialnosc-vendora-edm/")
            push = result.get("push")
            if push:
                if push.get("ok"):
                    st.success("GitHub Pages (main) OK")
                else:
                    st.error("Push GitHub nieudany — lokalne pliki juz zmienione")
                    for log in push.get("logs") or []:
                        st.code(log)
            wp = result.get("wordpress")
            if wp:
                if wp.get("skipped"):
                    st.warning(wp.get("reason", "WordPress pominiety"))
                elif wp.get("error") or wp.get("ok") is False:
                    st.error(f"WordPress: {wp.get('error') or wp}")
                else:
                    link = (wp.get("hub") or {}).get("link") or "https://bezpiecznyblog.pl/odpowiedzialnosc-vendora-edm/"
                    st.success(f"WordPress OK: {link}")
                    if wp.get("checklist_error"):
                        st.warning(f"Checklista WP: {wp['checklist_error']}")
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
