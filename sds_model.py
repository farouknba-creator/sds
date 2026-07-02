"""
SDS data model - holds the structured content of one SDS document.

The same model is used regardless of standard (OSHA / GHS / CLP / ISO).
The standard only affects section *titles* and *ordering*, not the data shape.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class SDSSection:
    """One of the 16 GHS sections."""
    num: int                                  # 1..16
    title: str                                # localised title per standard
    raw_text: str = ""                        # verbatim from source PDF
    normalized_text: str = ""                 # after AI reformat
    subfields: dict[str, str] = field(default_factory=dict)  # e.g. {"CAS No.": "1310-73-2"}
    tables: list[list[list[str]]] = field(default_factory=list)  # raw rows
    source_pages: list[int] = field(default_factory=list)  # page numbers in source PDF
    extraction_confidence: float = 0.0        # 0..1 from AI
    needs_review: bool = False                # flagged by AI or parser

    def is_empty(self) -> bool:
        return not (self.raw_text.strip() or self.normalized_text.strip()
                    or self.subfields or self.tables)


@dataclass
class SDSProductInfo:
    """Product identification - section 1 subfields normalized."""
    product_name: str = ""
    product_code: str = ""
    cas_number: str = ""
    ec_number: str = ""
    reach_registration: str = ""
    molecular_formula: str = ""
    synonyms: list[str] = field(default_factory=list)
    intended_use: str = ""


@dataclass
class SDSDocument:
    """The full SDS in structured form."""
    source_file: str = ""                     # path to original PDF
    source_page_count: int = 0
    source_was_ocrd: bool = False
    extraction_method: str = ""               # "pymupdf" | "pymupdf+ocr" | "manual"

    product: SDSProductInfo = field(default_factory=SDSProductInfo)
    sections: dict[int, SDSSection] = field(default_factory=dict)  # keyed by num 1..16

    # Audit
    extracted_at: Optional[datetime] = None
    normalized_at: Optional[datetime] = None
    rendered_at: Optional[datetime] = None
    ai_provider: str = ""
    ai_model: str = ""
    standard_code: str = ""                   # which standard was used for titles

    # Metadata carried for rendering
    revision_date: str = ""
    revision_number: str = ""
    supersedes_date: str = ""

    def get_section(self, num: int) -> Optional[SDSSection]:
        return self.sections.get(num)

    def ensure_section(self, num: int, title: str) -> SDSSection:
        if num not in self.sections:
            self.sections[num] = SDSSection(num=num, title=title)
        return self.sections[num]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_file": self.source_file,
            "source_page_count": self.source_page_count,
            "source_was_ocrd": self.source_was_ocrd,
            "extraction_method": self.extraction_method,
            "product": self.product.__dict__,
            "sections": {str(n): {
                "num": s.num,
                "title": s.title,
                "raw_text": s.raw_text,
                "normalized_text": s.normalized_text,
                "subfields": s.subfields,
                "tables": s.tables,
                "source_pages": s.source_pages,
                "extraction_confidence": s.extraction_confidence,
                "needs_review": s.needs_review,
            } for n, s in self.sections.items()},
            "standard_code": self.standard_code,
            "revision_date": self.revision_date,
            "revision_number": self.revision_number,
            "ai_provider": self.ai_provider,
            "ai_model": self.ai_model,
        }
