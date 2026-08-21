# Układ stron WP — Hub odpowiedzialności (Bezpieczny Blog)

## Struktura (logiczna)

```
/hub-odpowiedzialnosci/                 ← indeks
/odpowiedzialnosc-vendora-edm/          ← case MyDr
/checklista-72h-vendor-edm/             ← narzędzie + PDF na Pages
/umowa-powierzenia-edm/                 ← klaster
/zgloszenie-uodo-72h-vendor/            ← klaster
/zastrzezenie-pesel-a-dane-medyczne/    ← klaster
```

URL-e są **płaskie** (lepsze SEO). Rejestr: `pages.yaml`.

Kanoniczny indeks: `https://bezpiecznyblog.pl/hub-odpowiedzialnosci/`

## Pliki

| Plik | Co to |
|------|--------|
| `pages.yaml` | Rejestr URL → plik HTML (sitemap + publish) |
| `sitemap-hub.xml` | Sitemap kanoniczny (blog) — generowany |
| `hub-index.html` | Indeks |
| `strona-hub.html` | Case MyDr |
| `checklista-72h.html` | Checklista 72h |
| `cluster/_TEMPLATE.html` | Szablon nowej strony klastra |
| `cluster/*.html` | Strony 1 intencja = 1 URL |
| `faq-schema.json` | Schema FAQ (case) |
| `checklista-72h-vendor-edm.pdf` | Kopia PDF (źródło generowane do `docs/`) |

## Budowa assetów (sitemap + PDF)

```powershell
cd "C:\Users\bkowa\droga na skróty"
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\python.exe build_hub_assets.py
```

PDF ląduje w `docs/` i `hub/` (GitHub Pages):
`https://secuoia-pl.github.io/vendor-edm-accountability/checklista-72h-vendor-edm.pdf`

### Sitemap w GSC (blog)

1. Skopiuj `wordpress/sitemap-hub.xml` do rootu domeny **albo** wklej URL-e w wtyczce SEO (Rank Math / Yoast) jako dodatkowe strony.
2. W Search Console property `bezpiecznyblog.pl` → Sitemaps → zgłoś `https://bezpiecznyblog.pl/sitemap-hub.xml` (jeśli plik jest na root) **albo** użyj wtyczkowego sitemap + URL Inspection na 6 URL-ach.
3. Lustro: `docs/sitemap-hub.xml` (lista kanonicznych URL-i bloga; property Pages to osobna rzecz).

## Publikacja

```powershell
.\.venv\Scripts\python.exe wp_publish.py --publish
# tylko klaster:
.\.venv\Scripts\python.exe wp_publish.py --cluster-only
```

`.env`: `WP_USER`, `WP_APP_PASSWORD`, opcjonalnie ID głównych stron.

## Nowy URL klastra

1. Skopiuj `cluster/_TEMPLATE.html` → `cluster/<slug>.html`
2. Dopisz wpis w `pages.yaml` (`kind: cluster`)
3. Link z `hub-index.html` + wzajemne linki
4. `python build_hub_assets.py` → `python wp_publish.py --publish`

## Rama

> Problem nie zaczyna się w momencie ataku — zaczyna się, gdy milion ludzi jest zależnych od jednego vendora bez równoważnej odpowiedzialności.
