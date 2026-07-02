"""
Generate a synthetic OSHA HCS 2012 SDS PDF for testing the extraction pipeline.

Run:  python scripts/make_sample_sds.py
Output: /home/z/my-project/input/sample_sds_acme.pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make the project root importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)
from reportlab.lib import colors


def build_sample_sds(out_path: Path, supplier_name: str = "Acme Chemical Corporation") -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out_path), pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        title=f"Sample SDS - Test Product",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=14, spaceAfter=6)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=11, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9, leading=12)

    story = []
    # Header
    story.append(Paragraph(f"<b>SAFETY DATA SHEET</b>", h1))
    story.append(Paragraph(f"{supplier_name}", body))
    story.append(Spacer(1, 0.1 * inch))

    # Section 1
    story.append(Paragraph("SECTION 1: IDENTIFICATION", h2))
    story.append(Paragraph("<b>Product name:</b> AcmeSol 505", body))
    story.append(Paragraph("<b>Product code:</b> AC-505-GAL", body))
    story.append(Paragraph("<b>Synonyms:</b> AC-505, Industrial Solvent 505", body))
    story.append(Paragraph("<b>CAS No.:</b> 67-63-0", body))
    story.append(Paragraph("<b>EC No.:</b> 200-661-7", body))
    story.append(Paragraph("<b>Manufacturer:</b> Acme Chemical Corporation, 100 Industrial Parkway, Houston, TX 77032", body))
    story.append(Paragraph("<b>Phone:</b> +1-713-555-0142", body))
    story.append(Paragraph("<b>Emergency phone:</b> +1-800-424-9300 (CHEMTREC)", body))
    story.append(Paragraph("<b>Recommended use:</b> Industrial cleaning solvent", body))
    story.append(Spacer(1, 0.1 * inch))

    # Section 2
    story.append(Paragraph("SECTION 2: HAZARD(S) IDENTIFICATION", h2))
    story.append(Paragraph("<b>GHS Classification:</b> Flammable Liquid Category 2, Eye Irritation Category 2A, Specific Target Organ Toxicity (Single Exposure) Category 3", body))
    story.append(Paragraph("<b>Hazard statements:</b> H225 - Highly flammable liquid and vapor. H319 - Causes serious eye irritation. H336 - May cause drowsiness or dizziness.", body))
    story.append(Paragraph("<b>Precautionary statements:</b> P210 - Keep away from heat/sparks/open flames. P305+P351+P338 - IF IN EYES: Rinse cautiously with water for several minutes.", body))
    story.append(Spacer(1, 0.1 * inch))

    # Section 3
    story.append(Paragraph("SECTION 3: COMPOSITION/INFORMATION ON INGREDIENTS", h2))
    table_data = [
        ["Ingredient", "CAS No.", "EC No.", "%"],
        ["Isopropanol", "67-63-0", "200-661-7", "90-100"],
    ]
    t = Table(table_data, colWidths=[2.0*inch, 1.2*inch, 1.2*inch, 0.8*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.1 * inch))

    # Section 4
    story.append(Paragraph("SECTION 4: FIRST-AID MEASURES", h2))
    story.append(Paragraph("<b>Inhalation:</b> Move to fresh air. If symptoms persist, seek medical attention.", body))
    story.append(Paragraph("<b>Skin contact:</b> Wash with soap and water. Remove contaminated clothing.", body))
    story.append(Paragraph("<b>Eye contact:</b> Rinse cautiously with water for at least 15 minutes. Remove contact lenses if present.", body))
    story.append(Paragraph("<b>Ingestion:</b> Do NOT induce vomiting. Rinse mouth. Seek medical attention immediately.", body))
    story.append(Spacer(1, 0.1 * inch))

    # Section 5
    story.append(Paragraph("SECTION 5: FIRE-FIGHTING MEASURES", h2))
    story.append(Paragraph("<b>Suitable extinguishing media:</b> Alcohol-resistant foam, dry chemical, carbon dioxide.", body))
    story.append(Paragraph("<b>Unsuitable:</b> Water jet (may spread fire).", body))
    story.append(Paragraph("<b>Specific hazards:</b> Highly flammable. Vapors may form explosive mixtures with air.", body))
    story.append(Spacer(1, 0.1 * inch))

    # Section 6
    story.append(Paragraph("SECTION 6: ACCIDENTAL RELEASE MEASURES", h2))
    story.append(Paragraph("<b>Personal precautions:</b> Eliminate ignition sources. Wear protective equipment.", body))
    story.append(Paragraph("<b>Environmental precautions:</b> Prevent entry into drains and waterways.", body))
    story.append(Paragraph("<b>Cleanup:</b> Absorb with inert material. Collect in closed container for disposal.", body))
    story.append(Spacer(1, 0.1 * inch))

    # Section 7
    story.append(Paragraph("SECTION 7: HANDLING AND STORAGE", h2))
    story.append(Paragraph("<b>Handling:</b> Use in well-ventilated area. Keep away from heat and ignition sources.", body))
    story.append(Paragraph("<b>Storage:</b> Store in tightly closed container in cool, dry, well-ventilated place.", body))
    story.append(Spacer(1, 0.1 * inch))

    # Section 8
    story.append(Paragraph("SECTION 8: EXPOSURE CONTROLS/PERSONAL PROTECTION", h2))
    story.append(Paragraph("<b>OSHA PEL:</b> 400 ppm TWA", body))
    story.append(Paragraph("<b>ACGIH TLV:</b> 200 ppm TWA, 400 ppm STEL", body))
    story.append(Paragraph("<b>PPE:</b> Chemical-resistant gloves, safety goggles, lab coat.", body))
    story.append(Spacer(1, 0.1 * inch))

    # Section 9
    story.append(Paragraph("SECTION 9: PHYSICAL AND CHEMICAL PROPERTIES", h2))
    story.append(Paragraph("<b>Appearance:</b> Clear colorless liquid", body))
    story.append(Paragraph("<b>Odor:</b> Alcohol-like", body))
    story.append(Paragraph("<b>Boiling point:</b> 82°C (180°F)", body))
    story.append(Paragraph("<b>Flash point:</b> 12°C (54°F) - closed cup", body))
    story.append(Paragraph("<b>Density:</b> 0.786 g/cm3 at 20°C", body))
    story.append(Spacer(1, 0.1 * inch))

    # Section 10
    story.append(Paragraph("SECTION 10: STABILITY AND REACTIVITY", h2))
    story.append(Paragraph("<b>Stability:</b> Stable under normal conditions.", body))
    story.append(Paragraph("<b>Incompatible materials:</b> Strong oxidizers, acids, bases.", body))
    story.append(Spacer(1, 0.1 * inch))

    # Section 11
    story.append(Paragraph("SECTION 11: TOXICOLOGICAL INFORMATION", h2))
    story.append(Paragraph("<b>LD50 oral (rat):</b> 5045 mg/kg", body))
    story.append(Paragraph("<b>LD50 dermal (rabbit):</b> 12800 mg/kg", body))
    story.append(Paragraph("<b>LC50 inhalation (rat):</b> 16000 ppm/8h", body))
    story.append(Spacer(1, 0.1 * inch))

    # Section 12
    story.append(Paragraph("SECTION 12: ECOLOGICAL INFORMATION", h2))
    story.append(Paragraph("<b>LC50 fish:</b> 9640 mg/L/96h (Pimephales promelas)", body))
    story.append(Paragraph("<b>Biodegradability:</b> Readily biodegradable.", body))
    story.append(Spacer(1, 0.1 * inch))

    # Section 13
    story.append(Paragraph("SECTION 13: DISPOSAL CONSIDERATIONS", h2))
    story.append(Paragraph("Dispose in accordance with local, state, federal regulations. Do not discharge into sewer.", body))
    story.append(Spacer(1, 0.1 * inch))

    # Section 14
    story.append(Paragraph("SECTION 14: TRANSPORT INFORMATION", h2))
    story.append(Paragraph("<b>UN number:</b> UN1219", body))
    story.append(Paragraph("<b>Proper shipping name:</b> Isopropanol", body))
    story.append(Paragraph("<b>Hazard class:</b> 3", body))
    story.append(Paragraph("<b>Packing group:</b> II", body))
    story.append(Spacer(1, 0.1 * inch))

    # Section 15
    story.append(Paragraph("SECTION 15: REGULATORY INFORMATION", h2))
    story.append(Paragraph("<b>US Federal:</b> TSCA listed. SARA 311/312 hazard categories: Fire Hazard, Acute Health.", body))
    story.append(Paragraph("<b>California Prop 65:</b> Not listed.", body))
    story.append(Spacer(1, 0.1 * inch))

    # Section 16
    story.append(Paragraph("SECTION 16: OTHER INFORMATION", h2))
    story.append(Paragraph("<b>Revision Date:</b> 2024-03-15", body))
    story.append(Paragraph("<b>Revision No.:</b> 3.0", body))
    story.append(Paragraph("<b>Supersedes Date:</b> 2022-08-01", body))
    story.append(Paragraph("This information is based on our current knowledge and is provided in good faith.", body))

    doc.build(story)
    print(f"Wrote sample SDS to: {out_path}")


if __name__ == "__main__":
    out = Path("/home/z/my-project/input/sample_sds_acme.pdf")
    build_sample_sds(out)
