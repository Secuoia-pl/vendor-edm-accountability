"""Buduj sitemap kanoniczny (blog) + PDF checklisty 72h."""

from __future__ import annotations

import shutil
import sys
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import yaml
from fpdf import FPDF

ROOT = Path(__file__).resolve().parent
WP_DIR = ROOT / "wordpress"
PAGES_YAML = WP_DIR / "pages.yaml"
SITEMAP_OUT = WP_DIR / "sitemap-hub.xml"
DOCS = ROOT / "docs"
HUB = ROOT / "hub"
PDF_NAME = "checklista-72h-vendor-edm.pdf"
CANONICAL_CHECKLIST = "https://bezpiecznyblog.pl/checklista-72h-vendor-edm/"
CANONICAL_CASE = "https://bezpiecznyblog.pl/odpowiedzialnosc-vendora-edm/"


def today_iso() -> str:
    return date.today().isoformat()


def load_pages() -> dict:
    return yaml.safe_load(PAGES_YAML.read_text(encoding="utf-8"))


def write_sitemap(lastmod: str | None = None) -> Path:
    data = load_pages()
    base = str(data["base_url"]).rstrip("/")
    lastmod = lastmod or today_iso()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for page in data["pages"]:
        loc = f"{base}/{page['slug']}/"
        priority = page.get("priority", "0.5")
        changefreq = page.get("changefreq", "monthly")
        lines.append("  <url>")
        lines.append(f"    <loc>{escape(loc)}</loc>")
        lines.append(f"    <lastmod>{escape(lastmod)}</lastmod>")
        lines.append(f"    <changefreq>{escape(str(changefreq))}</changefreq>")
        lines.append(f"    <priority>{escape(str(priority))}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    lines.append("")
    text = "\n".join(lines)
    SITEMAP_OUT.write_text(text, encoding="utf-8")
    # Lustro na Pages (GSC bloga i tak wymaga pliku na domenie bloga)
    for dest_dir in (DOCS, HUB):
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "sitemap-hub.xml").write_text(text, encoding="utf-8")
    return SITEMAP_OUT


def _pick_font() -> tuple[str, str]:
    candidates = [
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibri.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return "HubSans", str(path)
    raise FileNotFoundError("Brak czcionki TTF z polskimi znakami (arial/calibri/DejaVu).")


class ChecklistPDF(FPDF):
    def footer(self) -> None:  # noqa: N802
        self.set_y(-12)
        self.set_font("HubSans", size=8)
        self.set_text_color(90, 90, 90)
        self.cell(0, 8, f"Strona {self.page_no()} · nie stanowi porady prawnej", align="C")


def build_checklist_pdf() -> Path:
    family, font_path = _pick_font()
    pdf = ChecklistPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_font(family, "", font_path)
    pdf.add_font(family, "B", font_path)
    pdf.add_page()
    pdf.set_margins(16, 14, 16)

    pdf.set_font(family, "B", 14)
    pdf.multi_cell(0, 7, "Checklista 72h — wyciek u vendora EDM / procesora")
    pdf.ln(2)
    pdf.set_font(family, size=9)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(
        0,
        5,
        "Dla administratora danych (placówka / praktyka). "
        "Wolno kopiować do memo; przy publikacji podaj źródło.",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(1)
    pdf.set_text_color(31, 77, 58)
    pdf.set_font(family, "B", 9)
    pdf.multi_cell(
        0,
        5,
        "Rama: problem zaczyna się od zależności od vendora, nie od samego ataku.",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1)
    pdf.set_font(family, size=8)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(0, 4, f"Kanonicznie: {CANONICAL_CHECKLIST}", new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 4, f"Case: {CANONICAL_CASE}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    sections: list[tuple[str, list[str]]] = [
        (
            "0–4 h",
            [
                "Potwierdź, czy korzystacie z danego dostawcy i w jakim module (EDM / terminarz / inne)",
                "Wyznacz ownera incydentu (IOD + IT/security + zarządzanie)",
                "Zamroź spekulacyjną komunikację zewnętrzną („nie wiemy jeszcze zakresu”)",
            ],
        ),
        (
            "4–24 h",
            [
                "Pismo / ticket do procesora: zakres tenantów, kategorie danych, timeline, IOCs, rekomendacje",
                "Poproś o listę: czy Wasze ID klienta / baza jest w zakresie (tak / nie / nieustalone)",
                "Zabezpiecz logi własne (dostępy, integracje, eksporty)",
            ],
        ),
        (
            "24–72 h",
            [
                "Udokumentuj ocenę ryzyka (dla Waszych osób / danych)",
                "Decyzja: zgłoszenie do UODO — tak / nie / wstępne + uzasadnienie",
                "Decyzja: zawiadomienie pacjentów — tak / nie / po doprecyzowaniu zakresu",
                "Przygotuj komunikat antyphishing (recepty, wizyty, „dopłaty”, kody BLIK)",
                "Sprawdź polisę cyber / obowiązki zgłoszenia do ubezpieczyciela",
            ],
        ),
        (
            "Równolegle (umowa i odporność)",
            [
                "Umowa powierzenia: prawo audytu, SLA powiadomień, podprocesorzy, exit/eksport",
                "Lista innych vendorów z danymi wrażliwymi (top 10) — ten sam scenariusz „co jeśli jutro?”",
            ],
        ),
    ]

    for title, items in sections:
        pdf.set_font(family, "B", 11)
        pdf.set_text_color(31, 77, 58)
        pdf.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.set_font(family, size=9)
        for item in items:
            pdf.multi_cell(0, 5, f"[ ]  {item}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        pdf.ln(1)

    pdf.set_font(family, "B", 11)
    pdf.set_text_color(31, 77, 58)
    pdf.cell(0, 7, "5 pytań do vendora (wklej)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(family, size=9)
    questions = [
        "Jaki jest potwierdzony zakres per nasz tenant?",
        "Jakie kategorie danych mogły zostać ujawnione?",
        "Od kiedy wiecie / od kiedy informujecie administratorów?",
        "Jakie działania containment już wykonano?",
        "Kiedy dostaniemy materiał do oceny ryzyka i zawiadomień?",
    ]
    for i, q in enumerate(questions, 1):
        pdf.multi_cell(0, 5, f"{i}. {q}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.5)

    pdf.ln(4)
    pdf.set_font(family, size=8)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(
        0,
        4,
        f"Stan PDF: {today_iso()} · Bezpieczny Blog / hub odpowiedzialności · bez pitchu usług",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    out = DOCS / PDF_NAME
    DOCS.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out))
    HUB.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out, HUB / PDF_NAME)
    shutil.copy2(out, WP_DIR / PDF_NAME)
    return out


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
    sm = write_sitemap()
    pdf = build_checklist_pdf()
    print(f"sitemap: {sm}")
    print(f"pdf:     {pdf}")


if __name__ == "__main__":
    main()
