# Cyber Influence Bot

Lokalny pipeline „droga na skróty” dla cyber:

`RSS (PL) → scoring → 3 wersje posta → pliki do akceptacji (+ ntfy / Signal)`

## Proste UI

```powershell
cd "C:\Users\bkowa\droga na skróty"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Otworzy się lokalny panel (`http://localhost:8501`):

- **Start** — uruchom pipeline jednym kliknięciem
- **Drafty** — edytuj / kopiuj Short·Medium·Sharp, oznacz APPROVED/DONE
- **Ranking** — ostatnie sygnały ze score
- **Config** — podgląd i edycja `config.yaml`

## Hub publiczny (zero DM / SEO)

**Kanonicznie:** https://bezpiecznyblog.pl/odpowiedzialnosc-vendora-edm/  
**Lustro:** folder `docs/` → GitHub Pages (canonical wskazuje na blog).  
**Wklejki WP:** `wordpress/` · publikacja REST: `wp_publish.py`  
**Sitemap + PDF:** `python build_hub_assets.py` → `wordpress/sitemap-hub.xml`, `docs/checklista-72h-vendor-edm.pdf` (szczegóły: `wordpress/INSTRUKCJA.md`)

## Tryby

| Komenda | Co robi |
|---|---|
| `.\.venv\Scripts\python.exe bot.py --once --no-llm` | jeden przebieg, tylko szablony |
| `.\.venv\Scripts\python.exe bot.py --once` | jak wyżej + dopieszczenie LLM (jeśli klucz w `.env`) |
| `.\.venv\Scripts\python.exe bot.py --loop --interval 30 --no-llm` | co 30 min |
| `.\.venv\Scripts\python.exe analyze.py --dry-run` | RSS → lokalna analiza stub (bez API) |
| `.\.venv\Scripts\python.exe analyze.py --provider atlas` | RSS → Grok/Atlas → draft hub/LI/X |

## Co jest zautomatyzowane

1. Zbieranie feedów CERT / Niebezpiecznik / Z3S / Sekurak / CyberDefence24 itd.
2. Scoring (źródło + słowa kluczowe + świeżość)
3. Deduplikacja URL (nie spamuje tym samym newsem)
4. Generowanie 3 draftów: **short / medium / sharp**
5. Lista kont do piggybacku w każdym pliku
6. Opcjonalny ping ntfy / Signal (`NOTIFY.md`)

## Czego świadomie NIE automatyzujemy na start

- Autopublish na X/LinkedIn (łatwo spalić konto)
- Auto-komentowanie pod cudzymi postami

Workflow: bot przygotowuje → Ty akceptujesz → publikujesz ręcznie w 2 minuty.

## Konfiguracja

Edytuj `config.yaml`:

- `rss_feeds` — źródła
- `keywords` — frazy podbijające score
- `min_score` / `max_drafts_per_run`
- `x_accounts` — lista kont do podpinania

## LLM (opcjonalnie)

W `.env` ustaw `OPENAI_API_KEY` (albo klucz OpenRouter + `OPENAI_BASE_URL`).  
Bez klucza bot i tak działa na szablonach.

### Analiza pod hub (`analyze.py`)

Używa **Atlas** (`ATLASCLOUD_API_KEY`, domyślnie `xai/grok-4.6`) albo **Wiro** (`WIRO_API_KEY` + Seed/Grok).  
Wynik: `drafts/analyze-*.md` + `.json` (PENDING_APPROVAL) — changelog, FAQ, post LI, wątek X.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# skopiuj klucze do .env (patrz .env.example)
.\.venv\Scripts\python.exe analyze.py --dry-run
.\.venv\Scripts\python.exe analyze.py --provider atlas
```

## Powiadomienia (ntfy + Signal)

Zobacz `NOTIFY.md`. Telegram usunięty z pipeline.

## Proponowany rytm dnia

1. Rano: `.\.venv\Scripts\python.exe bot.py --once --no-llm`
2. Weź 1 draft ze score ≥ 60
3. Wrzuć SHORT na X + 5 komentarzy z listy Priority
4. Popołudniu MEDIUM na LinkedIn
