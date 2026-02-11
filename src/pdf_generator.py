"""
PDF Generator - produces a premium, McKinsey-meets-Morning-Brew style
AI & Tech Weekly Briefing PDF using ReportLab.
"""
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

# ── Color Palette ─────────────────────────────────────────────────────────────
NAVY          = HexColor("#0D1B2A")
DEEP_PURPLE   = HexColor("#1B0D2A")
INDIGO        = HexColor("#2D3192")
BRAND_BLUE    = HexColor("#1A56DB")
LIGHT_BLUE    = HexColor("#E8F0FE")
ACCENT_GOLD   = HexColor("#F59E0B")
WHITE         = HexColor("#FFFFFF")
OFF_WHITE     = HexColor("#F8F9FA")
LIGHT_GRAY    = HexColor("#E5E7EB")
MID_GRAY      = HexColor("#9CA3AF")
DARK_GRAY     = HexColor("#374151")
TEXT_BLACK    = HexColor("#111827")
CARD_BG       = HexColor("#FAFAFA")
CARD_BORDER   = HexColor("#E2E8F0")

# Category colors (text, badge_bg)
CATEGORY_COLORS = {
    "Research Breakthroughs":        (HexColor("#7C3AED"), HexColor("#EDE9FE")),
    "Product Launches & Updates":    (HexColor("#0369A1"), HexColor("#E0F2FE")),
    "Industry News & Business":      (HexColor("#065F46"), HexColor("#D1FAE5")),
    "Policy, Safety & Ethics":       (HexColor("#9D174D"), HexColor("#FCE7F3")),
    "Open Source & Developer Tools": (HexColor("#92400E"), HexColor("#FEF3C7")),
    "Robotics & Autonomous Systems": (HexColor("#1E40AF"), HexColor("#DBEAFE")),
    "Other AI & Tech News":          (HexColor("#374151"), HexColor("#F3F4F6")),
}

CATEGORY_ICONS = {
    "Research Breakthroughs":        "Research",
    "Product Launches & Updates":    "Products",
    "Industry News & Business":      "Business",
    "Policy, Safety & Ethics":       "Policy",
    "Open Source & Developer Tools": "Dev Tools",
    "Robotics & Autonomous Systems": "Robotics",
    "Other AI & Tech News":          "Tech News",
}

CATEGORY_GRADIENTS = {
    "Research Breakthroughs":        (HexColor("#7C3AED"), HexColor("#A78BFA")),
    "Product Launches & Updates":    (HexColor("#0369A1"), HexColor("#38BDF8")),
    "Industry News & Business":      (HexColor("#065F46"), HexColor("#34D399")),
    "Policy, Safety & Ethics":       (HexColor("#9D174D"), HexColor("#F472B6")),
    "Open Source & Developer Tools": (HexColor("#92400E"), HexColor("#FBBF24")),
    "Robotics & Autonomous Systems": (HexColor("#1E40AF"), HexColor("#60A5FA")),
    "Other AI & Tech News":          (HexColor("#374151"), HexColor("#9CA3AF")),
}

# Source colors (text_color, badge_bg)
SOURCE_COLORS = {
    "Hacker News":          (HexColor("#FF6600"), HexColor("#FFE5CC")),
    "ArXiv":                (HexColor("#0066CC"), HexColor("#CCE5FF")),
    "ArXiv cs.AI":          (HexColor("#0066CC"), HexColor("#CCE5FF")),
    "ArXiv cs.LG":          (HexColor("#0066CC"), HexColor("#CCE5FF")),
    "ArXiv cs.CL":          (HexColor("#0066CC"), HexColor("#CCE5FF")),
    "TechCrunch":           (HexColor("#00CC66"), HexColor("#CCFFDD")),
    "The Verge":            (HexColor("#9966CC"), HexColor("#E5CCFF")),
    "MIT Technology Review":(HexColor("#CC3333"), HexColor("#FFCCCC")),
    "VentureBeat":          (HexColor("#FFAA00"), HexColor("#FFF5CC")),
    "Wired":                (HexColor("#0099AA"), HexColor("#CCFFFF")),
}

TOP_STORY_COLORS = [
    (HexColor("#B45309"), HexColor("#FEF3C7")),  # Gold  — #1
    (HexColor("#4338CA"), HexColor("#EDE9FE")),  # Indigo — #2
    (HexColor("#065F46"), HexColor("#D1FAE5")),  # Green  — #3
    (HexColor("#C2410C"), HexColor("#FFEDD5")),  # Orange — #4
    (HexColor("#6B21A8"), HexColor("#F3E8FF")),  # Purple — #5
]

PAGE_W, PAGE_H = letter   # 612 × 792 pt
MARGIN = 0.75 * inch
CONTENT_W = PAGE_W - 2 * MARGIN


# ── Utility Flowables ─────────────────────────────────────────────────────────

class GradientRect(Flowable):
    """Draw a horizontal gradient rectangle."""
    def __init__(self, width, height, color1, color2, radius=4):
        super().__init__()
        self.width = width
        self.height = height
        self.color1 = color1
        self.color2 = color2
        self.radius = radius

    def draw(self):
        steps = 60
        for i in range(steps):
            t = i / (steps - 1)
            r = self.color1.red   + t * (self.color2.red   - self.color1.red)
            g = self.color1.green + t * (self.color2.green - self.color1.green)
            b = self.color1.blue  + t * (self.color2.blue  - self.color1.blue)
            self.canv.setFillColorRGB(r, g, b)
            x = self.width * i / steps
            w = self.width / steps + 1  # +1 to avoid gaps
            if i == 0:
                self.canv.roundRect(x, 0, w + self.radius, self.height, self.radius, fill=1, stroke=0)
            elif i == steps - 1:
                self.canv.rect(x, 0, w, self.height, fill=1, stroke=0)
            else:
                self.canv.rect(x, 0, w, self.height, fill=1, stroke=0)


class ColoredRoundRect(Flowable):
    """Filled rounded-corner rectangle, used for source badges."""
    def __init__(self, width, height, fill_color, radius=3):
        super().__init__()
        self.width = width
        self.height = height
        self.fill_color = fill_color
        self.radius = radius

    def draw(self):
        self.canv.setFillColor(self.fill_color)
        self.canv.setStrokeColor(self.fill_color)
        self.canv.roundRect(0, 0, self.width, self.height, self.radius, fill=1, stroke=0)


class ShadowRect(Flowable):
    """White card with subtle drop shadow."""
    def __init__(self, width, height, bg=None, border=None):
        super().__init__()
        self.width = width
        self.height = height
        self.bg = bg or CARD_BG
        self.border = border or CARD_BORDER

    def draw(self):
        # Shadow
        self.canv.setFillColor(HexColor("#00000015"))
        self.canv.roundRect(2, -2, self.width, self.height, 6, fill=1, stroke=0)
        # Card body
        self.canv.setFillColor(self.bg)
        self.canv.setStrokeColor(self.border)
        self.canv.setLineWidth(0.5)
        self.canv.roundRect(0, 0, self.width, self.height, 6, fill=1, stroke=1)


# ── Styles ────────────────────────────────────────────────────────────────────

def _make_styles():
    base = getSampleStyleSheet()

    def S(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        # Cover
        "cover_title": S("cover_title",
            fontSize=36, fontName="Helvetica-Bold", textColor=WHITE,
            leading=44, alignment=TA_CENTER),
        "cover_subtitle": S("cover_subtitle",
            fontSize=15, fontName="Helvetica", textColor=HexColor("#CBD5E1"),
            leading=22, alignment=TA_CENTER),
        "cover_footer": S("cover_footer",
            fontSize=10, fontName="Helvetica", textColor=HexColor("#94A3B8"),
            leading=14, alignment=TA_CENTER),
        "cover_stat_num": S("cover_stat_num",
            fontSize=40, fontName="Helvetica-Bold", textColor=WHITE,
            leading=46, alignment=TA_CENTER),
        "cover_stat_label": S("cover_stat_label",
            fontSize=11, fontName="Helvetica", textColor=HexColor("#CBD5E1"),
            leading=15, alignment=TA_CENTER),
        # TOC
        "toc_title": S("toc_title",
            fontSize=22, fontName="Helvetica-Bold", textColor=TEXT_BLACK,
            leading=28, spaceBefore=0, spaceAfter=12),
        "toc_item": S("toc_item",
            fontSize=12, fontName="Helvetica", textColor=DARK_GRAY,
            leading=20, leftIndent=8),
        "toc_item_bold": S("toc_item_bold",
            fontSize=12, fontName="Helvetica-Bold", textColor=TEXT_BLACK,
            leading=20, leftIndent=8),
        # Section headings
        "section_title": S("section_title",
            fontSize=22, fontName="Helvetica-Bold", textColor=WHITE,
            leading=28, alignment=TA_LEFT),
        "section_count": S("section_count",
            fontSize=11, fontName="Helvetica", textColor=HexColor("#E2E8F0"),
            leading=16, alignment=TA_LEFT),
        # Executive summary
        "exec_title": S("exec_title",
            fontSize=20, fontName="Helvetica-Bold", textColor=TEXT_BLACK,
            leading=26, spaceBefore=0, spaceAfter=8),
        "exec_body": S("exec_body",
            fontSize=11.5, fontName="Helvetica", textColor=DARK_GRAY,
            leading=19, alignment=TA_JUSTIFY),
        "bullet": S("bullet",
            fontSize=11, fontName="Helvetica", textColor=DARK_GRAY,
            leading=18, leftIndent=16, bulletIndent=4),
        # Story cards
        "card_title": S("card_title",
            fontSize=13, fontName="Helvetica-Bold", textColor=TEXT_BLACK,
            leading=18, spaceAfter=4),
        "card_body": S("card_body",
            fontSize=10.5, fontName="Helvetica", textColor=DARK_GRAY,
            leading=16, alignment=TA_JUSTIFY),
        "card_source": S("card_source",
            fontSize=9, fontName="Helvetica-Bold", textColor=WHITE,
            leading=12, alignment=TA_CENTER),
        "card_link": S("card_link",
            fontSize=9.5, fontName="Helvetica", textColor=BRAND_BLUE,
            leading=14),
        # Top stories
        "top_badge": S("top_badge",
            fontSize=22, fontName="Helvetica-Bold", textColor=WHITE,
            leading=28, alignment=TA_CENTER),
        "top_title": S("top_title",
            fontSize=14, fontName="Helvetica-Bold", textColor=TEXT_BLACK,
            leading=20, spaceAfter=4),
        "top_body": S("top_body",
            fontSize=11, fontName="Helvetica", textColor=DARK_GRAY,
            leading=18, alignment=TA_JUSTIFY),
        "top_link": S("top_link",
            fontSize=10, fontName="Helvetica", textColor=BRAND_BLUE,
            leading=14),
        # Footer / meta
        "footer_left": S("footer_left",
            fontSize=8, fontName="Helvetica", textColor=MID_GRAY, leading=10),
        "footer_center": S("footer_center",
            fontSize=8, fontName="Helvetica", textColor=MID_GRAY,
            leading=10, alignment=TA_CENTER),
        "footer_right": S("footer_right",
            fontSize=8, fontName="Helvetica", textColor=MID_GRAY,
            leading=10, alignment=TA_RIGHT),
        # Sources page
        "sources_title": S("sources_title",
            fontSize=20, fontName="Helvetica-Bold", textColor=TEXT_BLACK,
            leading=26, spaceAfter=6),
        "sources_body": S("sources_body",
            fontSize=10.5, fontName="Helvetica", textColor=DARK_GRAY,
            leading=16),
        "sources_url": S("sources_url",
            fontSize=10, fontName="Helvetica", textColor=BRAND_BLUE,
            leading=15),
    }


# ── Page Templates ────────────────────────────────────────────────────────────

def _cover_background(canvas, doc):
    """Full-page gradient cover background."""
    canvas.saveState()
    steps = 80
    for i in range(steps):
        t = i / (steps - 1)
        r = NAVY.red   + t * (DEEP_PURPLE.red   - NAVY.red)
        g = NAVY.green + t * (DEEP_PURPLE.green - NAVY.green)
        b = NAVY.blue  + t * (DEEP_PURPLE.blue  - NAVY.blue)
        canvas.setFillColorRGB(r, g, b)
        y = PAGE_H * i / steps
        canvas.rect(0, y, PAGE_W, PAGE_H / steps + 1, fill=1, stroke=0)

    # Subtle dot grid decoration
    canvas.setFillColorRGB(1, 1, 1, 0.04)
    for x in range(int(MARGIN), int(PAGE_W - MARGIN), 24):
        for y in range(int(MARGIN), int(PAGE_H - MARGIN), 24):
            canvas.circle(x, y, 1, fill=1, stroke=0)
    canvas.restoreState()


def _page_background(canvas, doc):
    """Normal page: white with footer."""
    canvas.saveState()
    canvas.setFillColor(WHITE)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Footer bar
    footer_y = 0.45 * inch
    canvas.setStrokeColor(LIGHT_GRAY)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, footer_y + 10, PAGE_W - MARGIN, footer_y + 10)

    # Footer text
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MID_GRAY)
    canvas.drawString(MARGIN, footer_y, f"AI & Tech Weekly Briefing  •  {date_str}")
    canvas.drawRightString(PAGE_W - MARGIN, footer_y, "Curated by Claude AI")
    canvas.drawCentredString(PAGE_W / 2, footer_y, f"— {doc.page} —")

    canvas.restoreState()


# ── Main PDF Generation Function ──────────────────────────────────────────────

def generate_pdf(
    briefing: dict,
    output_path: Optional[str] = None,
) -> Path:
    """
    Generate a premium PDF briefing. Returns the path of the created file.

    Args:
        briefing: The structured briefing dict from summarizer.py
        output_path: Override for the output file path. If None, uses project root.
    """
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    date_range = f"{week_ago.strftime('%B %d')} – {now.strftime('%B %d, %Y')}"
    date_slug = now.strftime("%Y-%m-%d")

    if output_path:
        pdf_path = Path(output_path)
    else:
        project_root = Path(__file__).resolve().parent.parent
        pdf_path = project_root / f"AI-Tech-Briefing-{date_slug}.pdf"

    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    styles = _make_styles()
    story_elements = []

    # Collect stats
    categories = briefing.get("categories", {})
    all_stories = [s for cat in categories.values() for s in cat]
    sources = {s.get("source", "Unknown") for s in all_stories}
    top_stories = briefing.get("top_stories", [])
    non_empty_cats = [(k, v) for k, v in categories.items() if v]
    total_stories = len(all_stories)

    # ── Document setup ────────────────────────────────────────────────────────
    doc = BaseDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=0.75 * inch,
        title=f"AI & Tech Weekly Briefing — {date_range}",
        author="Claude AI",
        subject="Weekly AI & Technology News Briefing",
    )

    cover_frame = Frame(0, 0, PAGE_W, PAGE_H, leftPadding=0, rightPadding=0,
                        topPadding=0, bottomPadding=0, id="cover")
    body_frame  = Frame(MARGIN, 0.75 * inch, CONTENT_W, PAGE_H - MARGIN - 0.75 * inch,
                        id="body")

    cover_template = PageTemplate(id="Cover", frames=[cover_frame],
                                  onPage=_cover_background)
    body_template  = PageTemplate(id="Body",  frames=[body_frame],
                                  onPage=_page_background)
    doc.addPageTemplates([cover_template, body_template])

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 1 — COVER
    # ═══════════════════════════════════════════════════════════════════════════
    story_elements.append(NextPageTemplate("Cover"))
    story_elements.append(Spacer(1, 1.6 * inch))

    story_elements.append(Paragraph("AI & Tech", styles["cover_title"]))
    story_elements.append(Paragraph("Weekly Briefing", styles["cover_title"]))
    story_elements.append(Spacer(1, 0.18 * inch))
    story_elements.append(Paragraph(date_range, styles["cover_subtitle"]))
    story_elements.append(Spacer(1, 0.6 * inch))

    # Stats box — 3-column table
    stat_data = [[
        Paragraph(str(total_stories), styles["cover_stat_num"]),
        Paragraph(str(len(sources)),  styles["cover_stat_num"]),
        Paragraph(str(len(non_empty_cats)), styles["cover_stat_num"]),
    ], [
        Paragraph("Total Stories",  styles["cover_stat_label"]),
        Paragraph("Sources",        styles["cover_stat_label"]),
        Paragraph("Categories",     styles["cover_stat_label"]),
    ]]
    stat_col_w = (CONTENT_W - 40) / 3
    stat_table = Table(
        stat_data,
        colWidths=[stat_col_w] * 3,
        rowHeights=[52, 22],
        hAlign="CENTER",
    )
    stat_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), HexColor("#FFFFFF18")),
        ("LINEABOVE",   (0, 0), (-1, 0),  0.5, HexColor("#FFFFFF30")),
        ("LINEBELOW",   (0, -1), (-1, -1), 0.5, HexColor("#FFFFFF30")),
        ("LINEBEFORE",  (1, 0), (1, -1), 0.5, HexColor("#FFFFFF30")),
        ("LINEBEFORE",  (2, 0), (2, -1), 0.5, HexColor("#FFFFFF30")),
        ("TOPPADDING",  (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",  (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("ROUNDEDCORNERS", [8]),
    ]))

    # Center the stat table on the page
    stat_wrapper = Table([[stat_table]], colWidths=[CONTENT_W])
    stat_wrapper.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story_elements.append(stat_wrapper)

    story_elements.append(Spacer(1, 2.0 * inch))
    story_elements.append(Paragraph(
        "Curated by Claude AI  •  Automated with GitHub Actions",
        styles["cover_footer"]
    ))

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 2 — TABLE OF CONTENTS
    # ═══════════════════════════════════════════════════════════════════════════
    story_elements.append(NextPageTemplate("Body"))
    story_elements.append(PageBreak())
    story_elements.append(Spacer(1, 0.1 * inch))

    # TOC header accent bar
    story_elements.append(Table(
        [[Paragraph("Table of Contents", styles["toc_title"])]],
        colWidths=[CONTENT_W],
        style=[
            ("LEFTPADDING",  (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
        ],
    ))
    story_elements.append(HRFlowable(width=CONTENT_W, thickness=2,
                                     color=BRAND_BLUE, spaceAfter=12))

    toc_items = [
        ("01", "Executive Summary",  "p. 3"),
        ("02", "Top 5 Stories",       "p. 3"),
    ]
    page_num = 4
    for cat_name, _ in non_empty_cats:
        toc_items.append((f"{page_num:02d}", cat_name, f"p. {page_num}"))
        page_num += 1
    toc_items.append((f"{page_num:02d}", "Sources & Methodology", f"p. {page_num}"))

    for num, title, pg in toc_items:
        row = Table(
            [[
                Paragraph(f'<font color="#94A3B8">{num}</font>', styles["toc_item"]),
                Paragraph(title, styles["toc_item_bold"]),
                Paragraph(f'<font color="#9CA3AF">{pg}</font>', styles["toc_item"]),
            ]],
            colWidths=[30, CONTENT_W - 90, 60],
            style=[
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING",   (0, 0), (-1, -1), 4),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
                ("TOPPADDING",    (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ],
        )
        story_elements.append(row)
        story_elements.append(HRFlowable(
            width=CONTENT_W, thickness=0.5, color=LIGHT_GRAY, spaceAfter=0))

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 3 — EXECUTIVE SUMMARY + TOP STORIES
    # ═══════════════════════════════════════════════════════════════════════════
    story_elements.append(PageBreak())
    story_elements.append(Spacer(1, 0.1 * inch))

    # --- Executive Summary ---
    story_elements.append(Paragraph("📊  Executive Summary", styles["exec_title"]))
    story_elements.append(HRFlowable(width=CONTENT_W, thickness=2,
                                     color=BRAND_BLUE, spaceAfter=10))

    # Highlighted summary box
    exec_text = briefing.get("executive_summary", "No summary available.")
    exec_box = Table(
        [[Paragraph(exec_text, styles["exec_body"])]],
        colWidths=[CONTENT_W - 24],
        style=[
            ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_BLUE),
            ("LEFTPADDING",   (0, 0), (-1, -1), 16),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
            ("TOPPADDING",    (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ("ROUNDEDCORNERS", [6]),
        ],
    )
    story_elements.append(exec_box)
    story_elements.append(Spacer(1, 0.25 * inch))

    # Week at a Glance callout
    glance_items = [
        f"📅  {date_range}",
        f"📰  {total_stories} stories aggregated from {len(sources)} sources",
        f"🗂️  {len(non_empty_cats)} active categories covered",
        f"⭐  {len(top_stories)} top stories selected by Claude AI",
    ]
    glance_content = [
        [Paragraph("<b>Week at a Glance</b>", ParagraphStyle(
            "ga_title", fontSize=12, fontName="Helvetica-Bold",
            textColor=INDIGO, leading=16))],
    ] + [[Paragraph(f"  {item}", ParagraphStyle(
        "ga_item", fontSize=10.5, fontName="Helvetica",
        textColor=DARK_GRAY, leading=17))] for item in glance_items]

    glance_box = Table(
        glance_content,
        colWidths=[CONTENT_W - 24],
        style=[
            ("BACKGROUND",    (0, 0), (-1, -1), HexColor("#EEF2FF")),
            ("LEFTPADDING",   (0, 0), (-1, -1), 14),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LINEAFTER",     (0, 0), (0, -1), 3, INDIGO),
        ],
    )
    story_elements.append(glance_box)
    story_elements.append(Spacer(1, 0.35 * inch))

    # --- Top 5 Stories ---
    story_elements.append(Paragraph("⭐  Top 5 Stories of the Week", styles["exec_title"]))
    story_elements.append(HRFlowable(width=CONTENT_W, thickness=2,
                                     color=ACCENT_GOLD, spaceAfter=12))

    for i, story in enumerate(top_stories[:5]):
        txt_color, badge_bg = TOP_STORY_COLORS[i % len(TOP_STORY_COLORS)]
        badge_num = str(i + 1)
        src = story.get("source", "Unknown")
        src_text_c, src_bg_c = SOURCE_COLORS.get(src, (DARK_GRAY, LIGHT_GRAY))
        url = story.get("url", "#")

        badge_cell = Table(
            [[Paragraph(badge_num, ParagraphStyle(
                "tn", fontSize=26, fontName="Helvetica-Bold",
                textColor=txt_color, leading=32, alignment=TA_CENTER))]],
            colWidths=[44],
            rowHeights=[44],
            style=[
                ("BACKGROUND", (0, 0), (-1, -1), badge_bg),
                ("ROUNDEDCORNERS", [8]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ],
        )

        src_display = src[:20]
        src_badge_p = Paragraph(
            f'<font color="{src_text_c.hexval()}" size="8"><b>{src_display}</b></font>',
            ParagraphStyle("sb2", fontSize=8, fontName="Helvetica-Bold",
                           textColor=src_text_c, leading=11,
                           backColor=src_bg_c, borderPadding=(3, 6, 3, 6))
        )

        title_text  = story.get("title", "Untitled")
        reason_text = story.get("reason", "")
        link_text   = f'<link href="{url}"><font color="#1A56DB">Read full article →</font></link>'

        content_cell = [
            src_badge_p,
            Spacer(1, 4),
            Paragraph(title_text, styles["top_title"]),
            Paragraph(reason_text, styles["top_body"]),
            Spacer(1, 4),
            Paragraph(link_text, styles["top_link"]),
        ]

        card_data = [[badge_cell, content_cell]]
        card = Table(
            card_data,
            colWidths=[56, CONTENT_W - 68],
            style=[
                ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND",    (0, 0), (-1, -1), CARD_BG),
                ("BOX",           (0, 0), (-1, -1), 0.5, CARD_BORDER),
                ("LEFTPADDING",   (0, 0), (-1, -1), 10),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
                ("TOPPADDING",    (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("ROUNDEDCORNERS", [6]),
            ],
        )
        story_elements.append(KeepTogether([card, Spacer(1, 8)]))

    # ═══════════════════════════════════════════════════════════════════════════
    # CATEGORY PAGES
    # ═══════════════════════════════════════════════════════════════════════════
    for cat_name, cat_stories in non_empty_cats:
        story_elements.append(PageBreak())
        story_elements.append(Spacer(1, 0.05 * inch))

        grad_c1, grad_c2 = CATEGORY_GRADIENTS.get(
            cat_name, (INDIGO, BRAND_BLUE))
        cat_emoji = {
            "Research Breakthroughs":        "🔬",
            "Product Launches & Updates":    "🚀",
            "Industry News & Business":      "💼",
            "Policy, Safety & Ethics":       "⚖️",
            "Open Source & Developer Tools": "🛠️",
            "Robotics & Autonomous Systems": "🤖",
            "Other AI & Tech News":          "📰",
        }.get(cat_name, "📌")

        # Category header — gradient bar
        header_content = Table(
            [[
                Paragraph(f"{cat_emoji}  {cat_name}", ParagraphStyle(
                    "ch", fontSize=19, fontName="Helvetica-Bold",
                    textColor=WHITE, leading=24)),
                Paragraph(f"{len(cat_stories)} stories", ParagraphStyle(
                    "cc", fontSize=11, fontName="Helvetica",
                    textColor=HexColor("#E2E8F0"), leading=15,
                    alignment=TA_RIGHT)),
            ]],
            colWidths=[CONTENT_W - 90, 80],
            style=[
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING",   (0, 0), (-1, -1), 16),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
                ("TOPPADDING",    (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("BACKGROUND", (0, 0), (-1, -1), grad_c1),
                ("ROUNDEDCORNERS", [6]),
            ],
        )
        story_elements.append(header_content)
        story_elements.append(Spacer(1, 10))

        # Story cards — 2-column grid
        cards_left  = []
        cards_right = []
        for idx, s in enumerate(cat_stories):
            card = _build_story_card(s, styles)
            if idx % 2 == 0:
                cards_left.append(card)
            else:
                cards_right.append(card)

        col_w = (CONTENT_W - 10) / 2

        # Pair up left and right cards
        max_rows = max(len(cards_left), len(cards_right))
        for row_i in range(max_rows):
            left_cell  = cards_left[row_i]  if row_i < len(cards_left)  else Spacer(1, 1)
            right_cell = cards_right[row_i] if row_i < len(cards_right) else Spacer(1, 1)
            row_table = Table(
                [[left_cell, right_cell]],
                colWidths=[col_w, col_w],
                style=[
                    ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING",   (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
                    ("TOPPADDING",    (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ],
            )
            story_elements.append(row_table)
            story_elements.append(Spacer(1, 8))

    # ═══════════════════════════════════════════════════════════════════════════
    # FINAL PAGE — SOURCES & METHODOLOGY
    # ═══════════════════════════════════════════════════════════════════════════
    story_elements.append(PageBreak())
    story_elements.append(Spacer(1, 0.1 * inch))
    story_elements.append(Paragraph("📚  Sources & Methodology", styles["sources_title"]))
    story_elements.append(HRFlowable(width=CONTENT_W, thickness=2,
                                     color=BRAND_BLUE, spaceAfter=12))

    source_info = [
        ("Hacker News",           "https://news.ycombinator.com",             "AI/tech stories via Algolia search API, filtered for relevance"),
        ("ArXiv",                 "https://arxiv.org",                        "Research papers from cs.AI, cs.LG, cs.CL categories via RSS"),
        ("TechCrunch",            "https://techcrunch.com",                   "AI section coverage via RSS feed"),
        ("The Verge",             "https://www.theverge.com",                 "AI technology coverage via RSS feed"),
        ("MIT Technology Review", "https://www.technologyreview.com",         "AI research and analysis via RSS feed"),
        ("VentureBeat",           "https://venturebeat.com",                  "AI business and product news via RSS feed"),
        ("Wired",                 "https://www.wired.com",                    "AI coverage via topic RSS feed"),
    ]

    for src_name, src_url, src_desc in source_info:
        src_txt_c, src_bg_c = SOURCE_COLORS.get(src_name, (DARK_GRAY, LIGHT_GRAY))
        src_badge_p = Paragraph(
            f'<font color="{src_txt_c.hexval()}" size="9"><b>{src_name}</b></font>',
            ParagraphStyle("sb3", fontSize=9, fontName="Helvetica-Bold",
                           textColor=src_txt_c, leading=12,
                           backColor=src_bg_c, borderPadding=(4, 8, 4, 8))
        )
        link_p = Paragraph(
            f'<link href="{src_url}">{src_url}</link>',
            styles["sources_url"]
        )
        desc_p = Paragraph(src_desc, styles["sources_body"])
        row = Table(
            [[src_badge_p, link_p, desc_p]],
            colWidths=[110, 180, CONTENT_W - 310],
            style=[
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING",   (0, 0), (-1, -1), 6),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
                ("TOPPADDING",    (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ],
        )
        story_elements.append(row)
        story_elements.append(HRFlowable(width=CONTENT_W, thickness=0.5,
                                         color=LIGHT_GRAY, spaceAfter=0))

    story_elements.append(Spacer(1, 0.3 * inch))

    # Methodology box
    methodology = (
        "Stories are aggregated automatically every Saturday from 7 curated sources "
        "covering AI research, technology products, industry news, and policy. Each "
        "article is analyzed and summarized by Claude AI (Anthropic), which also "
        "categorizes stories into thematic sections and identifies the week's most "
        "significant developments. The pipeline runs on GitHub Actions and requires "
        "no manual intervention."
    )
    meth_box = Table(
        [[Paragraph(f"<b>Methodology</b><br/><br/>{methodology}", ParagraphStyle(
            "meth", fontSize=10.5, fontName="Helvetica", textColor=DARK_GRAY,
            leading=17, alignment=TA_JUSTIFY))]],
        colWidths=[CONTENT_W - 24],
        style=[
            ("BACKGROUND",    (0, 0), (-1, -1), OFF_WHITE),
            ("LEFTPADDING",   (0, 0), (-1, -1), 16),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
            ("TOPPADDING",    (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ("BOX",           (0, 0), (-1, -1), 0.5, CARD_BORDER),
            ("ROUNDEDCORNERS", [6]),
        ],
    )
    story_elements.append(meth_box)
    story_elements.append(Spacer(1, 0.2 * inch))

    gen_time = now.strftime("%A, %B %d, %Y at %H:%M UTC")
    story_elements.append(Paragraph(
        f"Generated: {gen_time}  •  Powered by GitHub Actions  •  Briefing v2.0",
        ParagraphStyle("meta", fontSize=9, fontName="Helvetica",
                       textColor=MID_GRAY, leading=13, alignment=TA_CENTER)
    ))

    # ── Build the PDF ─────────────────────────────────────────────────────────
    logger.info("Building PDF: %s", pdf_path)
    doc.build(story_elements)
    size_kb = pdf_path.stat().st_size // 1024
    logger.info("PDF generated: %s (%d KB)", pdf_path, size_kb)
    return pdf_path


# ── Story Card Builder ────────────────────────────────────────────────────────

def _build_story_card(story: dict, styles: dict) -> Table:
    """Build a single story card flowable for a category section."""
    src = story.get("source", "Unknown")
    src_txt_c, src_bg_c = SOURCE_COLORS.get(src, (DARK_GRAY, LIGHT_GRAY))
    title = story.get("title", "Untitled")
    summary = story.get("summary", "")
    url = story.get("url", "#")

    # Truncate very long source names
    src_display = src[:22] if len(src) > 22 else src

    # Source badge — rendered as a colored Paragraph (avoids nested Table width issues)
    src_badge_p = Paragraph(
        f'<font color="{src_txt_c.hexval()}" size="8"><b>{src_display}</b></font>',
        ParagraphStyle("cb2", fontSize=8, fontName="Helvetica-Bold",
                       textColor=src_txt_c, leading=11,
                       backColor=src_bg_c, borderPadding=(3, 6, 3, 6))
    )

    # Title (truncate to keep cards balanced)
    title_display = title[:120] + ("…" if len(title) > 120 else "")
    summary_display = summary[:280] + ("…" if len(summary) > 280 else "")
    link_text = f'<link href="{url}"><font color="#1A56DB">Read more →</font></link>'

    card_inner = [
        src_badge_p,
        Spacer(1, 4),
        Paragraph(title_display, styles["card_title"]),
        Spacer(1, 3),
        Paragraph(summary_display, styles["card_body"]),
        Spacer(1, 5),
        Paragraph(link_text, styles["card_link"]),
    ]

    card = Table(
        [[card_inner]],
        colWidths=[(CONTENT_W - 10) / 2 - 10],
        style=[
            ("BACKGROUND",    (0, 0), (-1, -1), CARD_BG),
            ("BOX",           (0, 0), (-1, -1), 0.5, CARD_BORDER),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("ROUNDEDCORNERS", [6]),
        ],
    )
    return card
