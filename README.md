# Cyber Influence Bot

Lokalny pipeline „droga na skróty” dla cyber:

`RSS (PL) → scoring → 3 wersje posta → pliki do akceptacji (+ opcjonalnie Telegram)`

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

Folder `hub/` — artefakt do GitHub Pages:

- `hub/index.html` — strona kanoniczna + FAQ schema
- `hub/checklist-72h.md` — checklista do kradzieży
- `hub/llms.txt` + `SUMMARY.md` — pod AI / cytowania

Plan publikacji: `plan-14-dni-zero-dm.md`

## Tryby

| Komenda | Co robi |
|---|---|
| `.\.venv\Scripts\python.exe bot.py --once --no-llm` | jeden przebieg, tylko szablony |
| `.\.venv\Scripts\python.exe bot.py --once` | jak wyżej + dopieszczenie LLM (jeśli klucz w `.env`) |
| `.\.venv\Scripts\python.exe bot.py --loop --interval 30 --no-llm` | co 30 min |

## Co jest zautomatyzowane

1. Zbieranie feedów CERT / Niebezpiecznik / Z3S / Sekurak / CyberDefence24 itd.
2. Scoring (źródło + słowa kluczowe + świeżość)
3. Deduplikacja URL (nie spamuje tym samym newsem)
4. Generowanie 3 draftów: **short / medium / sharp**
5. Lista kont do piggybacku w każdym pliku
6. Opcjonalny ping na Telegram

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

## Telegram (opcjonalnie)

1. Stwórz bota u `@BotFather`
2. Wyślij do niego `/start`
3. Wpisz token i chat_id do `.env`

## Proponowany rytm dnia

1. Rano: `.\.venv\Scripts\python.exe bot.py --once --no-llm`
2. Weź 1 draft ze score ≥ 60
3. Wrzuć SHORT na X + 5 komentarzy z listy Priority
4. Popołudniu MEDIUM na LinkedIn
