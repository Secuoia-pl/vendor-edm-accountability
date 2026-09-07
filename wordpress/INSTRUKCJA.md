# Układ stron WP — Hub odpowiedzialności (Bezpieczny Blog)

## Struktura (logiczna)

```
/hub-odpowiedzialnosci/                 ← indeks
/odpowiedzialnosc-vendora-edm/          ← case MyDr (dane)
/zondacrypto-custody-odpowiedzialnosc/  ← case Zondacrypto (custody)
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
| `case-zondacrypto-custody.html` | Case Zondacrypto |
| `checklista-72h.html` | Checklista 72h (MyDr) |
| `cluster/_TEMPLATE.html` | Szablon nowej strony klastra |
| `cluster/*.html` | Strony 1 intencja = 1 URL |
| `faq-schema.json` | Schema FAQ (case MyDr) |

## Multi-case (analyze / DONE)

`analyze.py` zwraca `target_case`: `mydr` | `zondacrypto` | `none`.  
Przy DONE w Streamlit możesz nadpisać case.  
`hub_publish.apply_to_hub` aktualizuje **tylko wybrany** HTML (+ lustro Pages dla MyDr).

## Budowa assetów (sitemap + PDF)

```powershell
cd "C:\Users\bkowa\droga na skróty"
.\.venv\Scripts\python.exe build_hub_assets.py
```

## Publikacja

```powershell
.\.venv\Scripts\python.exe wp_publish.py --publish
```

## Nowy case

1. Skopiuj `case-zondacrypto-custody.html` lub `cluster/_TEMPLATE.html`
2. Dopisz wpis w `pages.yaml` (`kind: case`, `case_id: …`)
3. Wpis w `hub-index.html`
4. Dodaj `case_id` w `hub_publish.CASES` + prompt w `analyze.py`
5. `python build_hub_assets.py` → `python wp_publish.py --publish`

## Rama

> Problem nie zaczyna się w momencie ataku — zaczyna się, gdy milion ludzi jest zależnych od jednego vendora / operatora bez równoważnej odpowiedzialności.
