"""
End-to-end test of the Phase 2 extraction + parsing pipeline.

Run:  python scripts/test_extraction.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sds_studio.core.extractor import PDFExtractor
from sds_studio.core.sds_parser import SDSParser
from sds_studio.core.template_config import TemplateConfig


def main():
    pdf = Path("/home/z/my-project/input/sample_sds_acme.pdf")
    assert pdf.exists(), f"Sample PDF not found: {pdf}"

    print(f"\n=== Extracting: {pdf.name} ===")
    extractor = PDFExtractor(auto_ocr=False)  # disable OCR for the test
    extracted = extractor.extract(pdf)
    print(f"Pages: {extracted.page_count}")
    print(f"Method: {extracted.extraction_method}")
    print(f"OCR'd: {extracted.any_ocrd}")
    print(f"Total chars: {sum(len(p.text) for p in extracted.pages)}")
    for p in extracted.pages:
        print(f"  Page {p.page_num}: {len(p.text)} chars, {len(p.tables)} tables, {len(p.images)} images")

    print(f"\n=== Parsing (OSHA HCS 2012) ===")
    tc = TemplateConfig()
    parser = SDSParser(tc)
    doc = parser.parse(extracted, standard_code="osha_hcs_2012", source_file=str(pdf))

    print(f"Standard: {doc.standard_code}")
    print(f"Sections found: {sorted(doc.sections.keys())}")
    for n in sorted(doc.sections.keys()):
        s = doc.sections[n]
        empty = "(empty)" if s.is_empty() else f"{len(s.raw_text)} chars"
        review = " [REVIEW]" if s.needs_review else ""
        print(f"  Section {n}: {s.title} - {empty}{review}")

    print(f"\n=== Product info ===")
    p = doc.product
    print(f"  Name:        {p.product_name}")
    print(f"  Code:        {p.product_code}")
    print(f"  CAS:         {p.cas_number}")
    print(f"  EC:          {p.ec_number}")
    print(f"  Synonyms:    {p.synonyms}")
    print(f"  Intended use: {p.intended_use}")

    print(f"\n=== Revision metadata ===")
    print(f"  Revision date: {doc.revision_date}")
    print(f"  Revision no:   {doc.revision_number}")
    print(f"  Supersedes:    {doc.supersedes_date}")

    # Sample section content
    if doc.sections.get(2):
        print(f"\n=== Section 2 sample (first 400 chars) ===")
        print(doc.sections[2].raw_text[:400])

    # Sanity assertions
    assert doc.product.product_name == "AcmeSol 505", f"Product name mismatch: {doc.product.product_name}"
    assert doc.product.cas_number == "67-63-0", f"CAS mismatch: {doc.product.cas_number}"
    assert doc.product.product_code == "AC-505-GAL", f"Product code mismatch: {doc.product.product_code}"
    assert doc.revision_date == "2024-03-15", f"Revision date mismatch: {doc.revision_date}"
    assert all(n in doc.sections for n in range(1, 17)), "Missing sections"
    print("\nALL ASSERTIONS PASS - Phase 2 extraction pipeline works end-to-end.")


if __name__ == "__main__":
    main()
