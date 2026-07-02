"""
PDF text + table + image extraction.

Wraps PyMuPDF (fitz) for fast text extraction and pdfplumber for tables.
Falls back to OCR (pytesseract) when a page has very little extractable text.

Returns a per-page structure:
  {
    page_num: int,
    text: str,                  # full page text
    tables: list[list[list[str]]],   # extracted tables
    images: list[ImageInfo],    # image metadata
    was_ocrd: bool,
  }
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ImageInfo:
    page_num: int
    image_index: int
    xref: int
    width: int
    height: int
    bbox: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


@dataclass
class PageContent:
    page_num: int                       # 1-indexed
    text: str = ""
    tables: list[list[list[str]]] = field(default_factory=list)
    images: list[ImageInfo] = field(default_factory=list)
    was_ocrd: bool = False
    char_count: int = 0


@dataclass
class ExtractedPDF:
    source_file: str
    page_count: int
    pages: list[PageContent] = field(default_factory=list)
    any_ocrd: bool = False
    extraction_method: str = ""

    @property
    def full_text(self) -> str:
        return "\n\n".join(f"--- Page {p.page_num} ---\n{p.text}" for p in self.pages)


class PDFExtractor:
    """
    Extracts text, tables, and image metadata from a PDF file.

    Args:
        auto_ocr:           If True, OCR pages below the char threshold.
        ocr_text_threshold: Pages with fewer chars than this trigger OCR.
        tesseract_cmd:      Path to tesseract binary; if None, try PATH.
    """

    def __init__(
        self,
        auto_ocr: bool = True,
        ocr_text_threshold: int = 50,
        tesseract_cmd: Optional[str] = None,
    ):
        self.auto_ocr = auto_ocr
        self.ocr_text_threshold = ocr_text_threshold
        self.tesseract_cmd = tesseract_cmd

    # ---- Public API ------------------------------------------------------
    def extract(self, pdf_path: str | Path) -> ExtractedPDF:
        """Extract all pages from a PDF. Throws on read failure."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)

        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise RuntimeError("PyMuPDF (fitz) is required for PDF extraction") from e

        out = ExtractedPDF(
            source_file=str(pdf_path),
            page_count=0,
            extraction_method="pymupdf",
        )

        with fitz.open(pdf_path) as doc:
            out.page_count = doc.page_count
            for i, page in enumerate(doc, start=1):
                pc = self._extract_page_fitz(page, i)
                # OCR fallback
                if (self.auto_ocr and pc.char_count < self.ocr_text_threshold):
                    ocr_text = self._ocr_page(doc, page, i)
                    if ocr_text and len(ocr_text) > pc.char_count:
                        pc.text = ocr_text
                        pc.was_ocrd = True
                        out.any_ocrd = True
                        out.extraction_method = "pymupdf+ocr"
                out.pages.append(pc)

        # Tables via pdfplumber (slower but more accurate than fitz for tables)
        try:
            self._extract_tables_pdfplumber(pdf_path, out)
        except Exception as e:
            logger.warning(f"pdfplumber table extraction failed for {pdf_path}: {e}")

        return out

    # ---- Per-page extraction --------------------------------------------
    def _extract_page_fitz(self, page, page_num: int) -> PageContent:
        import fitz
        pc = PageContent(page_num=page_num)
        # Plain text
        pc.text = page.get_text("text") or ""
        pc.char_count = len(pc.text.strip())

        # Image metadata
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            try:
                pix = fitz.Pixmap(page.parent, xref)
                w, h = pix.width, pix.height
                bbox = (0.0, 0.0, 0.0, 0.0)
                # Try to find image bbox on page
                for rect_info in page.get_image_rects(xref):
                    bbox = (rect_info.x0, rect_info.y0, rect_info.x1, rect_info.y1)
                    break
                pc.images.append(ImageInfo(
                    page_num=page_num, image_index=img_index, xref=xref,
                    width=w, height=h, bbox=bbox,
                ))
                pix = None  # free
            except Exception as e:
                logger.debug(f"Failed to read image xref={xref} on page {page_num}: {e}")
        return pc

    def _ocr_page(self, doc, page, page_num: int) -> str:
        """OCR a single page using pytesseract. Returns text or ''."""
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            logger.warning("pytesseract/PIL not installed - skipping OCR")
            return ""

        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

        try:
            # Render at 300 DPI for OCR quality
            pix = page.get_pixmap(dpi=300)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            text = pytesseract.image_to_string(img, lang="eng")
            logger.info(f"OCR'd page {page_num}: {len(text)} chars")
            return text
        except Exception as e:
            logger.warning(f"OCR failed on page {page_num}: {e}")
            return ""

    def _extract_tables_pdfplumber(self, pdf_path: Path, out: ExtractedPDF) -> None:
        """Add table data to each PageContent in `out`."""
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                if i > len(out.pages):
                    break
                try:
                    tables = page.extract_tables() or []
                    # Sanitize: replace None with "", strip whitespace
                    clean = []
                    for t in tables:
                        clean_t = [[(c or "").strip() for c in row] for row in t]
                        if clean_t:
                            clean.append(clean_t)
                    if clean:
                        out.pages[i - 1].tables = clean
                except Exception as e:
                    logger.debug(f"Table extraction failed on page {i}: {e}")
