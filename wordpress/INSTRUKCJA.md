# Układ stron WP — hub vendor EDM (Bezpieczny Blog)

Gotowe wklejki w tym folderze. Docelowy kanoniczny adres:

`https://bezpiecznyblog.pl/odpowiedzialnosc-vendora-edm/`

## Pliki

| Plik | Co to |
|------|--------|
| `strona-hub.html` | Główna nota (rama, fakty, 5 pytań, skrót checklisty, FAQ, cytowanie, changelog) |
| `checklista-72h.html` | Osobna strona „do kradzieży” / memo |
| `faq-schema.json` | FAQPage schema (Rank Math / Yoast / wtyczka schema) |

## 1. Strona główna huba

1. **Strony → Dodaj nową** (nie wpis — to evergreen).
2. **Tytuł:**  
   `Odpowiedzialność vendora EDM przy wycieku danych zdrowotnych (case MyDr)`
3. **Slug:** `odpowiedzialnosc-vendora-edm`
4. W treści: blok **Custom HTML** → wklej zawartość `strona-hub.html` (od `<article…>` do końca; komentarz na górze możesz pominąć).
5. **SEO meta description:**  
   `Wyciek u dostawcy EDM to nie tylko incydent IT. Rama, fakty, 5 pytań i checklista 72h dla placówek — case MyDr. Materiał do swobodnego wykorzystania.`
6. Opublikuj.

## 2. Checklista (druga strona)

1. Nowa strona, tytuł: `Checklista 72h — wyciek u vendora EDM / procesora`
2. Slug: `checklista-72h-vendor-edm`
3. Custom HTML → `checklista-72h.html`
4. Opublikuj (linki w hubie już na nią wskazują).

## 3. Schema FAQ

- **Rank Math / Yoast:** FAQ schema z treści H3+p **albo** wklej JSON z `faq-schema.json` jako custom schema.
- Albo drugi blok Custom HTML na dole huba z `<script type="application/ld+json">…</script>`.

## 4. Po publikacji

- W Search Console: sprawdź URL + poproś o indeksację.
- W postach LI/X używaj URL bloga (nie github.io).
- GitHub Pages ma canonical + banner wskazujący na blog.

## 5. Automatyzacja (REST)

W `.env` ustaw Application Password (WP: Użytkownicy → Profil → Application Passwords):

```
WP_BASE_URL=https://bezpiecznyblog.pl
WP_USER=twoj_login
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
```

```powershell
.\.venv\Scripts\python.exe wp_publish.py --discover
.\.venv\Scripts\python.exe wp_publish.py --publish
```

Albo w UI: **Drafty → DONE** z checkboxem WordPress.

Opcjonalnie: `WP_HUB_PAGE_ID`, `WP_CHECKLIST_PAGE_ID` (inaczej wykrywane po slug).

## 6. Czego nie robić

- Nie wrzucaj huba jako zwykłego „newsa dnia” — trzymaj jako **Stronę**.
- Nie dodawaj CTA sprzedażowego / „napisz DM”.
- Nie kasuj od razu Pages — lustro techniczne + canonical na blog.

## Rama (do powtarzania)

> Problem nie zaczyna się w momencie ataku — zaczyna się, gdy milion ludzi jest zależnych od jednego vendora bez równoważnej odpowiedzialności.
