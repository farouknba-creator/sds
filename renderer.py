"""
SDS PDF renderer - generates the standardized output PDF using ReportLab.

Layout (per page):
  +--------------------------------------------------+
  |  [Supplier name]      SAFETY DATA SHEET   [LOGO] |
  +--------------------------------------------------+
  |  Section 1: Identification                       |
  |  ...                                             |
  |  Section 2: ...                                  |
  |  ...                                             |
  +--------------------------------------------------+
  |  Page X of Y   |   Rev: YYYY-MM-DD               |
  |  This SDS was reformatted by SDS Studio.         |
  +--------------------------------------------------+

Design decisions:
  - Neutral palette: dark navy section bars (#0F2A44), white text,
    light grey table headers, body text in near-black.
  - Logo: fixed height (14mm), auto-width up to 50mm, positioned top-right.
    Logos with ~30% width variance all fit cleanly without distortion.
  - Each section gets a full-width colored bar with "SECTION N: TITLE".
  - Empty sections (when show_empty_sections=false) are skipped.
  - Tables in section 3 / 9 / 15 are rendered as actual ReportLab tables.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .paths import resolve_path
from .sds_model import SDSDocument, SDSSection
from .supplier import Supplier
from .template_config import Standard, TemplateConfig

logger = logging.getLogger(__name__)


def _hex(s: str) -> HexColor:
    return HexColor(s if s.startswith("#") else f"#{s}")


class SDSRenderer:
    """Renders a SDSDocument to a standardized PDF."""

    def __init__(self, template_config: TemplateConfig):
        self.tc = template_config

    # ---- Public API ------------------------------------------------------
    def render(
        self,
        doc: SDSDocument,
        supplier: Optional[Supplier],
        out_path: str | Path,
    ) -> Path:
        """
        Render `doc` as a standardized SDS PDF using `supplier` for the
        header block (legal name, address, phone, logo). Writes to `out_path`.
        """
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        std = self.tc.get_standard(doc.standard_code)
        if std is None:
            raise ValueError(f"Unknown standard: {doc.standard_code}")

        # Build the document
        page_size = A4 if self.tc.page_size.upper() == "A4" else letter
        margins = self.tc.margins

        # Header / footer drawing is in the page template
        self._supplier = supplier  # cached for header drawing
        self._doc = doc

        rl_doc = BaseDocTemplate(
            str(out_path),
            pagesize=page_size,
            leftMargin=margins["left"] * mm,
            rightMargin=margins["right"] * mm,
            topMargin=margins["top"] * mm + 18 * mm,  # extra for header
            bottomMargin=margins["bottom"] * mm + 12 * mm,  # extra for footer
            title=f"SDS - {doc.product.product_name or 'Unknown Product'}",
            author=supplier.legal_name if supplier else "SDS Studio",
        )

        # Frame for body content
        frame = Frame(
            rl_doc.leftMargin, rl_doc.bottomMargin,
            rl_doc.width, rl_doc.height,
            id="body",
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        )

        page_tpl = PageTemplate(
            id="sds",
            frames=[frame],
            onPage=self._draw_header_footer,
        )
        rl_doc.addPageTemplates([page_tpl])

        # Build the story (content flow)
        story = self._build_story(doc, std, supplier)
        rl_doc.build(story)

        doc.rendered_at = datetime.now()
        logger.info(f"Rendered SDS to {out_path}")
        return out_path

    # ---- Story builder ---------------------------------------------------
    def _build_story(self, doc: SDSDocument, std: Standard, supplier: Optional[Supplier]):
        story = []
        styles = self._build_styles()

        # ---- Product identification block (top of first page) ----
        story.append(self._product_block(doc, supplier, styles))
        story.append(Spacer(1, 4 * mm))

        # ---- Sections 1..16 ----
        show_empty = self.tc.section_layout["show_empty_sections"]
        for sec_def in std.sections:
            sec = doc.sections.get(sec_def.num)
            if not sec:
                if show_empty:
                    sec = SDSSection(num=sec_def.num, title=sec_def.title, raw_text="")
                else:
                    continue
            block = self._section_block(sec, styles)
            if block:
                story.append(block)
                story.append(Spacer(1, 3 * mm))

        return story

    # ---- Styles ----------------------------------------------------------
    def _build_styles(self) -> dict[str, ParagraphStyle]:
        c = self.tc.colors
        f = self.tc.fonts
        fs = self.tc.font_sizes

        body = ParagraphStyle(
            "body", fontName=f["body"], fontSize=fs["body"],
            leading=fs["body"] + 3, textColor=_hex(c["text"]),
            alignment=TA_LEFT,
        )
        body_bold = ParagraphStyle("body_bold", parent=body, fontName=f["heading"])
        heading = ParagraphStyle(
            "heading", fontName=f["heading"], fontSize=fs["heading"],
            leading=fs["heading"] + 2, textColor=_hex(c["heading"]),
        )
        section_bar = ParagraphStyle(
            "section_bar", fontName=f["heading"], fontSize=fs["section_title"],
            leading=fs["section_title"] + 2, textColor=_hex(c["section_bar_text"]),
        )
        small = ParagraphStyle(
            "small", fontName=f["body"], fontSize=fs["header_footer"],
            leading=fs["header_footer"] + 1, textColor=_hex(c["text"]),
        )
        return {
            "body": body, "body_bold": body_bold, "heading": heading,
            "section_bar": section_bar, "small": small,
        }

    # ---- Product block ---------------------------------------------------
    def _product_block(self, doc: SDSDocument, supplier: Optional[Supplier], styles: dict) -> Table:
        """Top-of-page identification table: product name, code, CAS, supplier."""
        p = doc.product
        rows = [
            ["Product Name:", p.product_name or "—"],
            ["Product Code:", p.product_code or "—"],
            ["CAS Number:", p.cas_number or "—"],
            ["EC Number:", p.ec_number or "—"],
        ]
        if p.reach_registration:
            rows.append(["REACH Reg. No.:", p.reach_registration])
        if p.synonyms:
            rows.append(["Synonyms:", ", ".join(p.synonyms)])
        if supplier:
            addr_parts = [a for a in [
                supplier.address.street,
                supplier.address.street2,
                " ".join(filter(None, [
                    supplier.address.city, supplier.address.state, supplier.address.postal_code,
                ])),
                supplier.address.country,
            ] if a]
            rows.append(["Supplier:", supplier.legal_name])
            if supplier.dba:
                rows.append(["DBA:", supplier.dba])
            if addr_parts:
                rows.append(["Address:", ", ".join(addr_parts)])
            if supplier.phone:
                rows.append(["Phone:", supplier.phone])
            if supplier.emergency_phone:
                rows.append(["Emergency:", supplier.emergency_phone])

        # Render as 2-column table
        data = [[Paragraph(f"<b>{k}</b>", styles["body_bold"]),
                 Paragraph(v or "—", styles["body"])] for k, v in rows]
        t = Table(data, colWidths=[35 * mm, None])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("BACKGROUND", (0, 0), (0, -1), _hex(self.tc.colors["table_header_bg"])),
            ("BOX", (0, 0), (-1, -1), 0.5, _hex(self.tc.colors["table_border"])),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, _hex(self.tc.colors["table_border"])),
        ]))
        return t

    # ---- Section block ---------------------------------------------------
    def _section_block(self, sec: SDSSection, styles: dict):
        """One section: colored bar + body content."""
        bar_text = f"SECTION {sec.num}: {sec.title.upper()}"
        bar = Table(
            [[Paragraph(bar_text, styles["section_bar"])]],
            colWidths=[None],
        )
        bar.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _hex(self.tc.colors["section_bar"])),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))

        # Body: prefer normalized_text, fall back to raw_text
        body_text = (sec.normalized_text or sec.raw_text).strip()
        parts = [bar, Spacer(1, 1.5 * mm)]
        if not body_text:
            parts.append(Paragraph(
                "<i>No information available.</i>", styles["body"],
            ))
        else:
            # Render subfields as a small table if present
            if sec.subfields:
                kv_rows = [[Paragraph(f"<b>{k}</b>", styles["body_bold"]),
                            Paragraph(v, styles["body"])]
                           for k, v in sec.subfields.items()]
                kv_table = Table(kv_rows, colWidths=[45 * mm, None])
                kv_table.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ]))
                parts.append(kv_table)
                parts.append(Spacer(1, 1.5 * mm))

            # Split body text into paragraphs by blank lines, render each
            for para in body_text.split("\n\n"):
                para = para.strip()
                if para:
                    # Convert single newlines to <br/> for inline breaks
                    safe = para.replace("\n", "<br/>")
                    parts.append(Paragraph(safe, styles["body"]))
                    parts.append(Spacer(1, 1 * mm))

            # Tables from extraction (e.g. composition tables)
            for tbl in sec.tables:
                rendered = self._render_data_table(tbl, styles)
                if rendered:
                    parts.append(Spacer(1, 1 * mm))
                    parts.append(rendered)

            # Review flag (only visible if section needs review)
            if sec.needs_review:
                parts.append(Spacer(1, 1 * mm))
                parts.append(Paragraph(
                    "<font color='#B85C00'><i>[Flagged for review]</i></font>",
                    styles["small"],
                ))

        return KeepTogether(parts)

    def _render_data_table(self, rows: list[list[str]], styles: dict) -> Optional[Table]:
        if not rows:
            return None
        # Build with paragraphs to handle wrapping
        data = []
        for r_i, row in enumerate(rows):
            cells = []
            for cell in row:
                if r_i == 0:
                    cells.append(Paragraph(f"<b>{cell}</b>", styles["body_bold"]))
                else:
                    cells.append(Paragraph(cell or "", styles["body"]))
            data.append(cells)
        # Equal-ish column widths
        n_cols = max(len(r) for r in rows)
        col_w = None  # let table autofit
        t = Table(data, colWidths=col_w, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _hex(self.tc.colors["table_header_bg"])),
            ("GRID", (0, 0), (-1, -1), 0.5, _hex(self.tc.colors["table_border"])),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    # ---- Header / footer drawing ----------------------------------------
    def _draw_header_footer(self, canvas, doc):
        """Called by ReportLab on every page. Draws header + footer."""
        canvas.saveState()
        page_w, page_h = doc.pagesize

        c = self.tc.colors
        f = self.tc.fonts
        fs = self.tc.font_sizes

        # ---- Header band ----
        header_h = 18 * mm
        margins = self.tc.margins

        # "SAFETY DATA SHEET" - top center
        if self.tc.header_footer["header_show_document_title"]:
            canvas.setFont(f["heading"], 12)
            canvas.setFillColor(_hex(c["heading"]))
            canvas.drawCentredString(page_w / 2, page_h - 8 * mm, "SAFETY DATA SHEET")

        # Supplier name - top left
        if self.tc.header_footer["header_show_supplier"] and self._supplier:
            canvas.setFont(f["body"], fs["header_footer"])
            canvas.setFillColor(_hex(c["text"]))
            sup_text = self._supplier.legal_name
            if self._supplier.dba:
                sup_text += f" (DBA: {self._supplier.dba})"
            canvas.drawString(margins["left"] * mm, page_h - 8 * mm, sup_text)

        # Logo - top right
        if self._supplier:
            self._draw_logo(canvas, page_w, page_h, margins)

        # Header rule line
        canvas.setStrokeColor(_hex(c["table_border"]))
        canvas.setLineWidth(0.5)
        canvas.line(
            margins["left"] * mm, page_h - header_h + 4 * mm,
            page_w - margins["right"] * mm, page_h - header_h + 4 * mm,
        )

        # ---- Footer ----
        footer_y = 10 * mm
        canvas.setFont(f["body"], fs["header_footer"])
        canvas.setFillColor(_hex(c["text"]))

        # Page numbers
        if self.tc.header_footer["footer_show_page_numbers"]:
            page_text = f"Page {doc.page}"
            canvas.drawString(margins["left"] * mm, footer_y, page_text)

        # Revision date
        if self.tc.header_footer["footer_show_revision_date"] and self._doc.revision_date:
            rev_text = f"Revision: {self._doc.revision_date}"
            if self._doc.revision_number:
                rev_text += f" (Rev {self._doc.revision_number})"
            canvas.drawCentredString(page_w / 2, footer_y, rev_text)

        # Disclaimer - bottom right (or wrapped full width)
        disclaimer = self.tc.header_footer.get("footer_disclaimer", "")
        if disclaimer:
            canvas.setFont(f["body"], fs["header_footer"] - 1)
            canvas.setFillColor(_hex(c["text"]))
            canvas.drawRightString(
                page_w - margins["right"] * mm, footer_y,
                disclaimer[:80] + ("..." if len(disclaimer) > 80 else ""),
            )
            # Wrap disclaimer to second line if long
            if len(disclaimer) > 80:
                canvas.drawCentredString(
                    page_w / 2, footer_y - 4 * mm,
                    "Generated by SDS Studio",
                )

        # Footer rule line
        canvas.setStrokeColor(_hex(c["table_border"]))
        canvas.setLineWidth(0.5)
        canvas.line(
            margins["left"] * mm, footer_y + 4 * mm,
            page_w - margins["right"] * mm, footer_y + 4 * mm,
        )

        canvas.restoreState()

    def _draw_logo(self, canvas, page_w, page_h, margins):
        """Draw the supplier logo top-right, fixed height, auto-width."""
        if not self._supplier or not self._supplier.logo_path:
            return
        logo_path = self._supplier.resolved_logo_path()
        if not logo_path:
            return

        try:
            from reportlab.lib.utils import ImageReader
            img = ImageReader(str(logo_path))
            iw, ih = img.getSize()
        except Exception as e:
            logger.warning(f"Could not read logo {logo_path}: {e}")
            return

        logo_cfg = self.tc.logo
        target_h = logo_cfg["height_mm"] * mm
        max_w = logo_cfg["max_width_mm"] * mm
        # Scale to target height, then clamp width
        scale = target_h / ih
        target_w = iw * scale
        if target_w > max_w:
            scale = max_w / iw
            target_w = max_w
            target_h = ih * scale

        # Position: top-right with padding
        pad = logo_cfg["padding_mm"] * mm
        x = page_w - margins["right"] * mm - target_w - pad
        y = page_h - target_h - pad - 2 * mm

        try:
            canvas.drawImage(
                img, x, y, width=target_w, height=target_h,
                preserveAspectRatio=True, mask="auto",
            )
        except Exception as e:
            logger.warning(f"Could not draw logo: {e}")
