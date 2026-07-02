"""
SDS section parser.

Takes the raw extracted text from PDFExtractor and slices it into the
16 GHS sections. The parser is intentionally tolerant of header phrasing
variants because vendors format section headers many different ways:

  "SECTION 1: IDENTIFICATION"
  "1. Identification"
  "Section 1 - Identification"
  "1 IDENTIFICATION OF THE SUBSTANCE/MIXTURE AND OF THE COMPANY/UNDERTAKING"
  "1.1. Product identifier"
  ...

Strategy:
  1. Find candidate section-header lines using regex across all 16 numbers.
  2. Filter candidates by minimum length (avoid matching "1." in a list).
  3. Build a sorted list of (section_num, line_index) markers.
  4. Slice text between consecutive markers into per-section blobs.
  5. Attach subfield key/value pairs found in section 1 (CAS, EC, etc).
  6. Map to the chosen standard's section titles.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from .extractor import ExtractedPDF
from .sds_model import SDSProductInfo, SDSSection, SDSDocument
from .template_config import Standard, TemplateConfig

logger = logging.getLogger(__name__)


# Section header patterns - tries to match "1. ...", "Section 1: ...", "1 - ...", etc.
# Captures the section number 1..16 as group 1.
HEADER_PATTERNS = [
    # "SECTION 1: IDENTIFICATION" / "Section 1 - Identification"
    re.compile(r"^\s*section\s*(\d{1,2})\s*[:\-\.]\s*(.+)$", re.IGNORECASE),
    # "1. Identification" / "1.2. Product identifier" / "1) Identification"
    re.compile(r"^\s*(\d{1,2})\s*[\.\)\-]\s+([A-Z][^\n]{4,})$"),
    # "1 IDENTIFICATION" (no separator, ALL CAPS title)
    re.compile(r"^\s*(\d{1,2})\s+([A-Z][A-Z\s/\,]{4,})$"),
    # "1." with title on next line is handled separately below.
]

# Known subfield labels that appear in section 1 / 3.
SUBFIELD_PATTERNS = {
    "product_name": [
        re.compile(r"Product\s*(?:name|identifier)\s*[:\-]\s*(.+)", re.IGNORECASE),
        re.compile(r"Trade\s*name\s*[:\-]\s*(.+)", re.IGNORECASE),
        re.compile(r"Substance\s*name\s*[:\-]\s*(.+)", re.IGNORECASE),
    ],
    "product_code": [
        re.compile(r"Product\s*(?:code|number|No\.?)\s*[:\-]\s*([\w\-\/\.]+)", re.IGNORECASE),
        re.compile(r"Item\s*number\s*[:\-]\s*([\w\-\/\.]+)", re.IGNORECASE),
        re.compile(r"Catalog\s*(?:No\.?|number)\s*[:\-]\s*([\w\-\/\.]+)", re.IGNORECASE),
    ],
    "cas_number": [
        re.compile(r"CAS\s*(?:No\.?|Number)\s*[:\-]\s*([\d\-]+)", re.IGNORECASE),
    ],
    "ec_number": [
        re.compile(r"EC\s*(?:No\.?|Number)\s*[:\-]\s*([\d\-]+)", re.IGNORECASE),
        re.compile(r"EINECS\s*[:\-]\s*([\d\-]+)", re.IGNORECASE),
    ],
    "reach_registration": [
        re.compile(r"REACH\s*(?:Reg\.?\s*No\.?|Registration\s*Number)\s*[:\-]\s*([\w\-]+)", re.IGNORECASE),
    ],
    "molecular_formula": [
        re.compile(r"(?:Molecular|Mol\.)\s*Formula\s*[:\-]\s*([A-Za-z0-9\(\)\s]+)", re.IGNORECASE),
    ],
    "intended_use": [
        re.compile(r"(?:Relevant|Intended)\s*identified\s*uses\s*[:\-]\s*(.+)", re.IGNORECASE),
        re.compile(r"Use\s*[:\-]\s*(.+)", re.IGNORECASE),
    ],
}

# Synonyms line - often a comma/semicolon separated list
SYNONYMS_PATTERN = re.compile(
    r"(?:Synonyms?|Other\s*names)\s*[:\-]\s*(.+)", re.IGNORECASE,
)

# Revision / supersedes patterns (often in section 16 or footer)
REVISION_DATE_PATTERN = re.compile(
    r"(?:Revision|Rev\.?)\s*(?:Date|No\.?)\s*[:\-]\s*([\d\/\w\-\.]+)", re.IGNORECASE,
)
REVISION_NUMBER_PATTERN = re.compile(
    r"Revision\s*(?:No\.?|Number)\s*[:\-]\s*([\w\-\.]+)", re.IGNORECASE,
)
SUPERSEDES_PATTERN = re.compile(
    r"Supersedes\s*(?:Date)?\s*[:\-]\s*([\d\/\w\-\.]+)", re.IGNORECASE,
)


class SDSParser:
    """Parses raw extracted PDF text into a structured SDSDocument."""

    def __init__(self, template_config: TemplateConfig):
        self.template_config = template_config

    def parse(
        self,
        extracted: ExtractedPDF,
        standard_code: str,
        source_file: str = "",
    ) -> SDSDocument:
        """
        Parse `extracted` into an SDSDocument using `standard_code` for titles.

        Args:
            extracted:      output from PDFExtractor.extract()
            standard_code:  e.g. "osha_hcs_2012"
            source_file:    path of original PDF (for audit)
        """
        std = self.template_config.get_standard(standard_code)
        if std is None:
            raise ValueError(f"Unknown standard: {standard_code}")

        doc = SDSDocument(
            source_file=source_file or extracted.source_file,
            source_page_count=extracted.page_count,
            source_was_ocrd=extracted.any_ocrd,
            extraction_method=extracted.extraction_method,
            standard_code=standard_code,
            ai_provider="",
            ai_model="",
        )

        # Pre-init all 16 sections with the standard's titles
        for sec in std.sections:
            doc.sections[sec.num] = SDSSection(num=sec.num, title=sec.title)

        # Find all section header positions across the full text
        full_text = extracted.full_text
        lines = full_text.split("\n")
        markers = self._find_section_markers(lines)

        if not markers:
            # No section headers found - dump everything into section 1 and flag for review
            doc.sections[1].raw_text = full_text
            doc.sections[1].needs_review = True
            doc.sections[1].extraction_confidence = 0.1
            logger.warning(f"No SDS section headers detected in {source_file}")
        else:
            self._slice_sections(lines, markers, doc)

        # Extract product identification from section 1 + 3
        self._extract_product_info(doc)

        # Extract revision metadata from section 16 or full text
        self._extract_revision_metadata(doc)

        return doc

    # ---- Section detection ----------------------------------------------
    def _find_section_markers(self, lines: list[str]) -> list[tuple[int, int]]:
        """
        Return list of (section_num, line_index) for likely section headers.

        Filters out false positives by requiring:
          - section number 1..16
          - the title text has some length
          - not part of a list (no leading bullet, no trailing comma)
        """
        markers: list[tuple[int, int]] = []
        seen: set[int] = set()

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or len(stripped) < 4:
                continue

            for pat in HEADER_PATTERNS:
                m = pat.match(stripped)
                if not m:
                    continue
                try:
                    num = int(m.group(1))
                except (ValueError, IndexError):
                    continue
                if not (1 <= num <= 16):
                    continue
                if num in seen:
                    continue

                title_text = m.group(2).strip() if m.lastindex and m.lastindex >= 2 else ""
                # Reject if title is too short or looks like list continuation
                if len(title_text) < 3:
                    continue
                # Reject if line ends with comma (likely list item)
                if stripped.endswith(","):
                    continue

                markers.append((num, i))
                seen.add(num)
                break

        # Sort by line index
        markers.sort(key=lambda m: m[1])
        return markers

    def _slice_sections(
        self,
        lines: list[str],
        markers: list[tuple[int, int]],
        doc: SDSDocument,
    ) -> None:
        """Slice lines between markers into the corresponding sections."""
        # Add a sentinel marker at the end of the document
        end_marker = (0, len(lines))
        markers_with_end = markers + [end_marker]

        for idx, (num, start_line) in enumerate(markers):
            if num == 0:  # sentinel
                continue
            end_line = markers_with_end[idx + 1][1] if idx + 1 < len(markers_with_end) else len(lines)
            section_lines = lines[start_line:end_line]
            # Strip the first line (the header itself)
            if section_lines:
                section_lines = section_lines[1:]
            text = "\n".join(section_lines).strip()
            # Compress excessive blank lines
            text = re.sub(r"\n{3,}", "\n\n", text)

            sec = doc.sections.get(num)
            if sec is None:
                continue
            sec.raw_text = text
            # Rough page attribution: which source pages does this section span?
            # We approximate by counting newlines before this marker vs. total
            total_lines = len(lines)
            if total_lines > 0:
                start_ratio = start_line / total_lines
                end_ratio = end_line / total_lines
                start_page = max(1, int(start_ratio * doc.source_page_count) + 1)
                end_page = max(1, int(end_ratio * doc.source_page_count) + 1)
                sec.source_pages = list(range(start_page, min(end_page + 1, doc.source_page_count + 1)))
            # Confidence: did we actually find content?
            sec.extraction_confidence = 0.7 if text else 0.2
            sec.needs_review = not bool(text)

    # ---- Product info extraction ----------------------------------------
    def _extract_product_info(self, doc: SDSDocument) -> None:
        """Pull CAS / EC / product name etc. from sections 1 and 3."""
        sec1_text = doc.sections.get(1).raw_text if doc.sections.get(1) else ""
        sec3_text = doc.sections.get(3).raw_text if doc.sections.get(3) else ""
        combined = f"{sec1_text}\n\n{sec3_text}"

        product = doc.product

        for field_name, patterns in SUBFIELD_PATTERNS.items():
            for pat in patterns:
                m = pat.search(combined)
                if m:
                    value = m.group(1).strip()
                    # Cap to first line / first ~100 chars to avoid runaway
                    value = value.split("\n")[0][:200].strip()
                    if value:
                        setattr(product, field_name, value)
                        break

        # Synonyms - comma or semicolon separated
        m = SYNONYMS_PATTERN.search(combined)
        if m:
            raw = m.group(1).strip().split("\n")[0]
            parts = [s.strip() for s in re.split(r"[,;]", raw) if s.strip()]
            product.synonyms = parts[:20]  # cap

    # ---- Revision metadata ----------------------------------------------
    def _extract_revision_metadata(self, doc: SDSDocument) -> None:
        """Look for revision date / number, often in section 16 or footer."""
        sec16 = doc.sections.get(16)
        search_text = sec16.raw_text if sec16 else ""
        # Also scan the full doc as fallback
        # (we don't have full text here but section 16 is usually enough)

        m = REVISION_DATE_PATTERN.search(search_text)
        if m:
            doc.revision_date = m.group(1).strip()
        m = REVISION_NUMBER_PATTERN.search(search_text)
        if m:
            doc.revision_number = m.group(1).strip()
        m = SUPERSEDES_PATTERN.search(search_text)
        if m:
            doc.supersedes_date = m.group(1).strip()
