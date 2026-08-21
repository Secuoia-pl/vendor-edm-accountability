# Układ stron WP — Hub odpowiedzialności (Bezpieczny Blog)

## Struktura (logiczna)

```
/hub-odpowiedzialnosci/          ← strona nadrzędna (indeks)
/odpowiedzialnosc-vendora-edm/   ← case MyDr
/checklista-72h-vendor-edm/      ← narzędzie do case'u
/…kolejne-case…/                 ← później
```

URL-e są **płaskie** (lepsze SEO). Hierarchia jest w treści indeksu i breadcrumbach, nie w zagnieżdżeniu WP.

Kanoniczny indeks: `https://bezpiecznyblog.pl/hub-odpowiedzialnosci/`

## Pliki

| Plik | Co to |
|------|--------|
| `hub-index.html` | Strona nadrzędna — lista not |
| `strona-hub.html` | Case MyDr |
| `checklista-72h.html` | Checklista 72h |
| `faq-schema.json` | Schema FAQ (case) |

## Publikacja

```powershell
cd "C:\Users\bkowa\droga na skróty"
.\.venv\Scripts\python.exe wp_publish.py --publish
```

Tworzy indeks (jeśli brak) i aktualizuje case + checklistę.

`.env`: `WP_USER`, `WP_APP_PASSWORD`, opcjonalnie ID:
`WP_INDEX_PAGE_ID`, `WP_HUB_PAGE_ID`, `WP_CHECKLIST_PAGE_ID`.

Slugi: `WP_INDEX_SLUG=hub-odpowiedzialnosci` itd.

Opcja `WP_NEST_PAGES=1` — zagnieżdża dzieci pod indeksem w drzewie WP (zmienia URL-e; zwykle niepotrzebne).

## Kolejny case

1. Nowy plik `wordpress/case-….html`
2. Wpis w sekcji „Noty w hubie” w `hub-index.html`
3. Rozszerz `wp_publish.py` / `.env` o nowy slug
4. `--publish`

## Rama

> Problem nie zaczyna się w momencie ataku — zaczyna się, gdy milion ludzi jest zależnych od jednego vendora bez równoważnej odpowiedzialności.
