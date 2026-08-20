# Plan 14 dni — wpływ bez DM („robota robi się sama”)

**Cel:** zbudować publiczny artefakt z Twoją ramą i sprawić, by **inni sami go podnosili** (SEO, AI Overview, kopiowanie, media/IOD).  
**Zasada:** 0 cold DM, 0 „napisz do mnie”, 0 pitch usług.  
**Rama:** Problem nie zaczyna się w momencie ataku — zaczyna się, gdy milion ludzi jest zależnych od jednego vendora bez równoważnej odpowiedzialności.

---

## 1) Co budujesz (jeden hub, nie 10 postów)

### Publiczny hub (źródło prawdy)
Proponowana nazwa / slug:
- PL: `odpowiedzialnosc-vendora-edm`  
- albo EN+PL: `vendor-accountability-health-data-pl`

**Struktura strony (1 URL = 1 artefakt):**

1. **Lead (40–60 słów)** — rama w pierwszym akapicie (dla Google + AI Overview)  
2. **TL;DR (3 bullet)**  
3. **Co wiemy / czego nie wiemy** (tabela faktów, ze źródłami i datą)  
4. **Przesunięcie pytania** — z „czy atak?” na „jaki model odpowiedzialności?”  
5. **5 pytań** (dla mediów / IOD / biur) — kopiowalne  
6. **Checklista 72h dla administratora** — kopiowalna  
7. **FAQ (8–12 pytań)** — paliwo SEO  
8. **Changelog** — data aktualizacji (sygnał świeżości)  
9. **Cytowanie** — gotowy blok „jak cytować ten materiał” (bez CTA)

**Formaty równoległe z tego samego źródła:**
- `index.html` / Markdown na GitHub Pages  
- `vendor-edm-checklist.pdf` (1 strona, bez brandingu osobistego)  
- `faq.json` lub FAQSchema w HTML (structured data)

### Stack (minimum)
- GitHub repo + GitHub Pages **albo** prosty blog (Hugo/Astro)  
- Domena opcjonalna (`*.pl` lepsza pod PL SEO, nie obowiązkowa na start)  
- Plik `llms.txt` / czytelny Markdown (łatwiejsze dla modeli AI)

---

## 2) Jak artefakt ma docierać do ludzi (mapa dystrybucji)

Bez DM. Kanały ułożone od „pasywnych” do „lekko aktywnych, ale bez rozmów”.

### A. SEO (organiczne wyszukiwanie) — główny silnik

**Frazy primary (1 strona = 1 intencja):**
- `wyciek MyDr odpowiedzialność`  
- `administrator procesor dane medyczne`  
- `obowiązki placówki wyciek EDM`  
- `vendor EDM RODO`  
- `powierzenie przetwarzania danych zdrowotnych`

**Frazy secondary (FAQ / nagłówki H2):**
- `czy pacjent musi być poinformowany o wycieku`  
- `72 godziny zgłoszenie UODO procesor`  
- `zastrzeżenie PESEL a wyciek danych medycznych`  
- `umowa powierzenia prawo audytu`

**Technika on-page (must):**
- H1 = fraza + rama (nie clickbait)  
- pierwsze 100 słów: odpowiedź wprost  
- tabele + listy (Google je lubi w featured/AI)  
- daty przy faktach (`Stan na 20.08.2026`)  
- linki do źródeł pierwotnych (UODO, MC, CERT, artykuły)  
- FAQPage schema + Article/WebPage schema  
- `lastmod` w sitemap  
- szybkość, mobile, czysty HTML

**Technika off-page bez networkingu:**
- link z Twojego LinkedIn / X w bio (nie w DM)  
- publikacja PDF z tym samym tytułem (ludzie linkują PDF)  
- wpis na GitHub Topics: `rodo`, `cybersecurity`, `healthcare`, `poland`  
- (opcjonalnie później) odpowiedź na publiczne pytanie StackOverflow / Reddit r/Polska / r/privacy — **tylko link do huba, zero pitchu**

**Czego nie grać:** kupowanie backlinków, PBN, spam katalogów.

### B. AI Overview / ChatGPT / Perplexity (coraz ważniejsze)

Modele cytują źródła, które są:
- konkretne, datowane, ze źródłami  
- w formie Q&A  
- niepaywallowe  

Dlatego FAQ + tabela faktów + changelog > długi felieton „moim zdaniem”.

Dodatkowo:
- krótki plik `SUMMARY.md` / `llms.txt` z ramą i 5 pytaniami  
- unikalne sformułowanie ramy (łatwe do powtórzenia 1:1)

### C. Social bez rozmów (broadcast only)

| Kanał | Co wrzucasz | Częstotliwość |
|-------|-------------|----------------|
| LinkedIn | 1 post: 1 wykres/tabela + rama + link do huba | 2× w 14 dni |
| X | wątek 5 tweetów = 5 pytań + link | 1× przy starcie, 1× przy update |
| LinkedIn newsletter / artykuł | „Checklista 72h” (fragment huba) | 1× |

**Zasady broadcast:**
- nie taguj osób  
- nie prosisz o komentarz „co myślicie?” jako engagement bait  
- CTA tylko: „pełna wersja + źródła: [URL]”

### D. Dystrybucja „przez kradzież” (najbardziej szara eminencja)

Zaprojektuj artefakt tak, by **opłacało się go ukraść**:
- checklista 1 strona PDF bez Twojego logo  
- bloki „do wklejenia do memo zarządu”  
- 5 pytań „do użycia w materiale”  
- licencja: CC BY albo „wolno kopiować z linkiem do źródła”

Im łatwiej skopiować, tym szybciej rama żyje bez Ciebie.

### E. Kanały instytucjonalne (pasywne, formalne)

Bez rozmów — jednorazowe złożenie:
- ewentualna opinia do konsultacji publicznych (gdy otwarte)  
- nie: maile do redakcji (to jest kontakt ludzi)

### F. Co NIE jest w tym planie
- DM do Pauli i innych  
- cold maile `redakcja@`  
- auto-komentowanie cudzych postów botem  

---

## 3) Kalendarz 14 dni

### Dni 1–2 — fundament SEO + struktura
- [ ] Repo + GitHub Pages (lub hosting)  
- [ ] Szkielet strony: H1, TL;DR, sekcje, FAQ puste  
- [ ] `robots.txt`, `sitemap.xml`, kanoniczny URL  
- [ ] Wybór 1 primary keyword na H1  

**Deliverable:** żywy URL (choćby draft).

### Dni 3–4 — treść merytoryczna
- [ ] Tabela faktów MyDr + źródła + daty  
- [ ] Sekcja „przesunięcie pytania” z ramą  
- [ ] 5 pytań kopiowalnych  
- [ ] Checklista 72h dla ADO  

**Deliverable:** v1.0 treści.

### Dzień 5 — FAQ + schema
- [ ] 10 FAQ pod secondary keywords  
- [ ] FAQPage JSON-LD  
- [ ] Blok „jak cytować”  

**Deliverable:** strona „gotowa do indeksacji”.

### Dzień 6 — PDF + llms.txt
- [ ] 1-stronicowy PDF checklisty (bez twarzy)  
- [ ] `llms.txt` / `SUMMARY.md` z ramą  

**Deliverable:** pakiet do kradzieży.

### Dzień 7 — publikacja startowa (broadcast)
- [ ] LinkedIn: post z 1 tabelą + link  
- [ ] X: 5 pytań + link  
- [ ] Bio LI/X: link do huba  

**KPI dnia:** URL działa, 2 broadcasty wyszły.

### Dni 8–9 — wzmocnienie SEO
- [ ] Search Console (jeśli domena) — zgłoś sitemap  
- [ ] Dopisz 2 H2 pod frazy z Search Suggest / „podobne pytania”  
- [ ] Wewnętrzne kotwice (`#checklist`, `#faq`, `#pytania`)  

### Dzień 10 — update pod świeży news
- [ ] Changelog: nowy fakt / nowa data  
- [ ] 1 krótki post LI: „Update: co się zmieniło w 48h” + link  
- [ ] `lastmod`  

Świeżość = lepsze SEO przy temacie newsowym.

### Dni 11–12 — druga warstwa odkrywalności
- [ ] Opublikuj PDF pod tym samym tytułem co H1 (spójność)  
- [ ] Wrzuć repo na GitHub z dobrym README (rama w 1. akapicie)  
- [ ] (opcjonalnie) 1 publiczna odpowiedź na forum/Reddit **tylko** jeśli ktoś pyta — link do huba  

### Dzień 13 — pomiar
- [ ] Sprawdź: indeksacja (`site:twoj-url`)  
- [ ] Jakie frazy już łapie (GSC / ręcznie 5 zapytań)  
- [ ] Czy ktoś skopiował fragment (Google: 5–7 słów z ramy w cudzysłowie)  

### Dzień 14 — decyzja v1.1
- [ ] Dopisz brakujące FAQ spod realnych zapytań  
- [ ] Ustal rytm dalej: **1 update / tydzień** przy newsie albo 2×/miesiąc  

---

## 4) Metryki sukcesu (bez vanity)

| Metryka | Dobry sygnał po 14–30 dniach |
|---------|------------------------------|
| Indeksacja | URL w Google `site:` |
| Fraza brandowa ramy | Google znajduje hub po 6–8 słowach ramy |
| Kradzież | ktoś wkleja checklistę / pytania bez Twojego udziału |
| AI | Perplexity/Chat cytuje lub parafrazuje hub |
| Ruch | nie licznik „like”, tylko wejścia na `#checklist` / PDF |

**Sukces szarej eminencji:** widzisz swoją frazę u kogoś innego — bez rozmowy z Tobą.

---

## 5) Szablon treści H1 + lead (do huba)

**H1:** Odpowiedzialność vendora EDM przy wycieku danych zdrowotnych (case MyDr)

**Lead:**
> Wyciek u dostawcy oprogramowania dla placówek medycznych nie jest tylko incydentem IT. To test modelu, w którym pacjent nie wybiera systemu, a dane zdrowotne koncentrują się u vendora obsługującego tysiące administratorów. Poniżej: co wiadomo, jakie pytania warto zadawać i checklista 72h dla placówek — do swobodnego wykorzystania.

---

## 6) Rytm po 14 dniach (utrzymanie „automatu”)

Tygodniowo (30–60 min):
1. Bot zbiera sygnały (`bot.py`)  
2. Ty wybierasz 1 fakt  
3. Update changelog huba  
4. 1 broadcast post z linkiem  

Miesięcznie:
- 2–3 nowe FAQ spod realnych zapytań  
- przegląd pozycji fraz primary  

---

## 7) Ryzyka i jak ich uniknąć

| Ryzyko | Mitygacja |
|--------|-----------|
| Niepewne liczby w SEO | zawsze „wg X na datę Y”; sekcja „czego nie wiemy” |
| Wygląda jak oferta usług | zero CTA sprzedażowego |
| Temat stygnie | hub = evergreen (admin/procesor/vendor), case = MyDr jako przykład |
| Nikt nie linkuje | PDF + kopiowalne bloki > prośba o share |

---

## 8) Decyzja startowa (zaznacz jedno)

- [ ] A: GitHub Pages + Markdown (najszybciej)  
- [ ] B: własna domena `.pl` + Astro/Hugo (lepsze SEO długoterminowo)  
- [ ] C: najpierw tylko PDF publiczny na GitHub Releases (najmniej friction)

**Rekomendacja:** A w dniach 1–7, domena (B) dopiero gdy v1.0 działa i jest update.

---

## Checklist „czy artefakt jest gotowy do życia bez Ciebie”

- [ ] Rama w pierwszym ekranie  
- [ ] Da się skopiować checklistę w 30 sekund  
- [ ] FAQ pokrywa 8+ zapytań  
- [ ] Źródła klikalne  
- [ ] Data / changelog  
- [ ] Brak „umów konsultację”  
- [ ] Jeden kanoniczny URL  
- [ ] Broadcast 2× w pierwszym tygodniu  

Gdy to jest — **robota naprawdę zaczyna robić się sama**: indeksowanie, cytowania, kradzież języka.
