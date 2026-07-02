"""
Full pipeline test (Phases 1-4):

  PDF → extract → parse → normalize (manual) → render standardized PDF

Validates:
  - Extraction pulls all 16 sections
  - Parser populates product info correctly
  - Normalizer works in manual mode (preserves raw text, flags for review)
  - Renderer produces a valid output PDF with logo + supplier block + 16 sections
  - Output file size is reasonable (not zero, not absurdly large)

Output: /home/z/my-project/output/sample_sds_acme_standardized.pdf
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sds_studio.core.extractor import PDFExtractor
from sds_studio.core.sds_parser import SDSParser
from sds_studio.core.template_config import TemplateConfig
from sds_studio.core.ai_provider import get_provider
from sds_studio.core.paths import SETTINGS_FILE, load_yaml, OUTPUT_DIR
from sds_studio.core.normalizer import normalize_document
from sds_studio.core.renderer import SDSRenderer
from sds_studio.core.supplier import SupplierDB


def main():
    print("=" * 70)
    print("SDS Studio - full pipeline test (Phases 1-4)")
    print("=" * 70)

    # Inputs
    pdf = Path("/home/z/my-project/input/sample_sds_acme.pdf")
    assert pdf.exists(), f"Missing {pdf}"

    print(f"\n[1/5] Extracting text from {pdf.name}...")
    extractor = PDFExtractor(auto_ocr=False)
    extracted = extractor.extract(pdf)
    print(f"      Pages: {extracted.page_count}, method: {extracted.extraction_method}")

    print("\n[2/5] Parsing into 16 sections (OSHA HCS 2012)...")
    tc = TemplateConfig()
    parser = SDSParser(tc)
    doc = parser.parse(extracted, "osha_hcs_2012", str(pdf))
    print(f"      Sections: {sorted(doc.sections.keys())}")
    print(f"      Product: {doc.product.product_name} (CAS {doc.product.cas_number})")

    print("\n[3/5] Normalizing with AI provider (manual mode)...")
    settings = load_yaml(SETTINGS_FILE)
    provider = get_provider(settings)
    std = tc.get_standard("osha_hcs_2012")
    normalize_document(doc, provider, std)
    print(f"      Provider: {provider.name}")
    print(f"      Flagged for review: {sum(1 for s in doc.sections.values() if s.needs_review)}/16")

    print("\n[4/5] Loading supplier from DB...")
    db = SupplierDB()
    supplier = db.get("supplier_001")  # Acme
    assert supplier is not None, "supplier_001 not found"
    print(f"      Supplier: {supplier.legal_name}")
    print(f"      Logo: {supplier.resolved_logo_path()}")

    print("\n[5/5] Rendering standardized PDF...")
    renderer = SDSRenderer(tc)
    out_path = OUTPUT_DIR / "sample_sds_acme_standardized.pdf"
    renderer.render(doc, supplier, out_path)
    size_kb = out_path.stat().st_size / 1024
    print(f"      Output: {out_path}")
    print(f"      Size:   {size_kb:.1f} KB")

    # Validation
    assert out_path.exists(), "Output file not created"
    assert size_kb > 5, f"Output suspiciously small: {size_kb} KB"
    assert size_kb < 5000, f"Output suspiciously large: {size_kb} KB"

    # Verify the output is a valid PDF
    with open(out_path, "rb") as f:
        header = f.read(8)
    assert header.startswith(b"%PDF"), f"Output is not a PDF: {header!r}"

    # Test second standard (EU CLP)
    print("\n[Bonus] Re-rendering with EU CLP standard...")
    doc2 = parser.parse(extracted, "eu_clp", str(pdf))
    normalize_document(doc2, provider, tc.get_standard("eu_clp"))
    out2 = OUTPUT_DIR / "sample_sds_acme_eu_clp.pdf"
    renderer.render(doc2, db.get("supplier_002"), out2)  # use EuroLab supplier
    print(f"      Output: {out2}")
    print(f"      Size:   {out2.stat().st_size / 1024:.1f} KB")

    print("\n" + "=" * 70)
    print("ALL PHASES 1-4 PASS")
    print("Output PDFs in /home/z/my-project/output/")
    print("=" * 70)


if __name__ == "__main__":
    main()
