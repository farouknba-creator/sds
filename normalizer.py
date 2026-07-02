"""
SDS normalizer - calls the AI provider to refine extraction and normalize sections.

Two main entry points:
  1. `refine_extraction(doc, provider)`  - re-attribute mis-split sections,
     recover missing subfields. Called once per document right after parsing.
  2. `normalize_section(section, std, provider)` - rewrite one section's text
     in the standard style. Called per section.

Both are robust to manual mode (provider returns a marker -> original text is
preserved and the section is flagged for review).

The output JSON parsing is defensive: any malformed AI response results in the
original text being kept + a review flag, never an exception.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from .ai_provider import AIProvider, ManualProvider
from .prompts import (
    EXTRACTION_REFINE_PROMPT,
    NORMALIZE_SECTION_PROMPT,
    SYSTEM_PROMPT,
    VALIDATION_PROMPT,
)
from .sds_model import SDSDocument, SDSSection, SDSProductInfo
from .template_config import Standard

logger = logging.getLogger(__name__)


def _safe_json_loads(text: str) -> dict | None:
    """Try to extract a JSON object from an AI response that may have fences or preface."""
    if not text:
        return None
    text = text.strip()
    # Strip markdown fences
    if text.startswith("```"):
        # remove first line
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    # Find first { and last }
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start:end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        logger.debug(f"JSON decode failed: {e}\nCandidate: {candidate[:200]}...")
        return None


def _is_manual_response(text: str) -> bool:
    """Detect the ManualProvider marker."""
    try:
        d = json.loads(text)
        return isinstance(d, dict) and d.get("_manual_mode") is True
    except (json.JSONDecodeError, ValueError):
        return False


# --------------------------------------------------------------------------- refine
def refine_extraction(doc: SDSDocument, provider: AIProvider, standard: Standard) -> None:
    """
    Ask the AI to refine the regex-parsed extraction.

    Mutates `doc` in place:
      - doc.product fields may be updated
      - doc.sections[*].raw_text may be re-attributed
      - doc.sections[*].extraction_confidence and needs_review updated
      - doc.revision_date / revision_number / supersedes_date updated

    In manual mode, does nothing (leaves regex output as-is, sets review flags).
    """
    if isinstance(provider, ManualProvider):
        for sec in doc.sections.values():
            sec.needs_review = True
        doc.ai_provider = "manual"
        doc.ai_model = "manual"
        return

    # Build the input payload
    product_info = {
        "product_name": doc.product.product_name,
        "product_code": doc.product.product_code,
        "cas_number": doc.product.cas_number,
        "ec_number": doc.product.ec_number,
        "synonyms": doc.product.synonyms,
        "intended_use": doc.product.intended_use,
    }
    sections_json = {
        str(n): {
            "title": s.title,
            "text": s.raw_text,
            "confidence": s.extraction_confidence,
        }
        for n, s in doc.sections.items()
    }

    prompt = EXTRACTION_REFINE_PROMPT.format(
        standard_name=standard.name,
        product_info=json.dumps(product_info, ensure_ascii=False),
        sections_json=json.dumps(sections_json, ensure_ascii=False, indent=2),
    )

    try:
        response = provider.complete(prompt, system=SYSTEM_PROMPT, temperature=0.0, max_tokens=8000)
    except Exception as e:
        logger.error(f"AI refine call failed: {e}")
        for sec in doc.sections.values():
            sec.needs_review = True
        return

    if _is_manual_response(response):
        for sec in doc.sections.values():
            sec.needs_review = True
        return

    data = _safe_json_loads(response)
    if not data:
        logger.warning("Could not parse AI refine response - keeping regex output")
        for sec in doc.sections.values():
            sec.needs_review = True
        return

    # Apply product refinements
    p = data.get("product", {})
    if isinstance(p, dict):
        if p.get("product_name"):
            doc.product.product_name = p["product_name"]
        if p.get("product_code"):
            doc.product.product_code = p["product_code"]
        if p.get("cas_number"):
            doc.product.cas_number = p["cas_number"]
        if p.get("ec_number"):
            doc.product.ec_number = p["ec_number"]
        if p.get("reach_registration"):
            doc.product.reach_registration = p["reach_registration"]
        if p.get("molecular_formula"):
            doc.product.molecular_formula = p["molecular_formula"]
        if isinstance(p.get("synonyms"), list):
            doc.product.synonyms = [str(s) for s in p["synonyms"]]
        if p.get("intended_use"):
            doc.product.intended_use = p["intended_use"]

    # Apply section refinements
    secs = data.get("sections", {})
    if isinstance(secs, dict):
        for num_str, sec_data in secs.items():
            try:
                num = int(num_str)
            except (ValueError, TypeError):
                continue
            sec = doc.sections.get(num)
            if not sec or not isinstance(sec_data, dict):
                continue
            new_text = sec_data.get("text")
            if new_text and isinstance(new_text, str) and new_text.strip():
                sec.raw_text = new_text.strip()
            conf = sec_data.get("confidence")
            if isinstance(conf, (int, float)):
                sec.extraction_confidence = float(conf)
            sec.needs_review = bool(sec_data.get("needs_review", sec.needs_review))

    # Revision metadata
    if data.get("revision_date"):
        doc.revision_date = str(data["revision_date"])
    if data.get("revision_number"):
        doc.revision_number = str(data["revision_number"])
    if data.get("supersedes_date"):
        doc.supersedes_date = str(data["supersedes_date"])

    doc.ai_provider = provider.name
    doc.ai_model = provider.model


# --------------------------------------------------------------------------- normalize section
def normalize_section(section: SDSSection, standard: Standard, provider: AIProvider) -> None:
    """
    Ask the AI to rewrite one section's raw_text in the standardized style.

    Mutates `section.normalized_text` and `section.subfields` in place.
    In manual mode, copies raw_text to normalized_text and flags for review.
    """
    if not section.raw_text.strip():
        section.normalized_text = ""
        return

    if isinstance(provider, ManualProvider):
        section.normalized_text = section.raw_text
        section.needs_review = True
        return

    prompt = NORMALIZE_SECTION_PROMPT.format(
        standard_name=standard.name,
        section_num=section.num,
        section_title=section.title,
        raw_text=section.raw_text,
    )

    try:
        response = provider.complete(prompt, system=SYSTEM_PROMPT, temperature=0.0, max_tokens=2000)
    except Exception as e:
        logger.error(f"AI normalize call failed for section {section.num}: {e}")
        section.normalized_text = section.raw_text
        section.needs_review = True
        return

    if _is_manual_response(response):
        section.normalized_text = section.raw_text
        section.needs_review = True
        return

    data = _safe_json_loads(response)
    if not data:
        logger.warning(f"Could not parse AI normalize response for section {section.num}")
        section.normalized_text = section.raw_text
        section.needs_review = True
        return

    nt = data.get("normalized_text")
    if isinstance(nt, str) and nt.strip():
        section.normalized_text = nt.strip()
    else:
        section.normalized_text = section.raw_text

    kv = data.get("key_value_pairs")
    if isinstance(kv, dict):
        section.subfields = {str(k): str(v) for k, v in kv.items() if v}

    if data.get("needs_review") is True:
        section.needs_review = True


# --------------------------------------------------------------------------- normalize full doc
def normalize_document(doc: SDSDocument, provider: AIProvider, standard: Standard) -> None:
    """Convenience: refine + normalize all sections in one call."""
    refine_extraction(doc, provider, standard)
    for sec in doc.sections.values():
        normalize_section(sec, standard, provider)


# --------------------------------------------------------------------------- validation
def validate_document(
    source_doc: SDSDocument,
    regenerated_doc: SDSDocument,
    provider: AIProvider,
) -> dict[str, Any]:
    """
    Compare source vs. regenerated doc via AI. Returns a validation report dict.

    In manual mode, returns {"overall_match": False, "needs_human_review": True, ...}.
    """
    if isinstance(provider, ManualProvider):
        return {
            "overall_match": False,
            "missing_information": [],
            "altered_values": [],
            "needs_human_review": True,
            "notes": "Manual mode - human review required.",
        }

    source_json = json.dumps({
        str(n): {"text": s.raw_text} for n, s in source_doc.sections.items()
    }, ensure_ascii=False)
    regen_json = json.dumps({
        str(n): {"text": s.normalized_text} for n, s in regenerated_doc.sections.items()
    }, ensure_ascii=False)

    prompt = VALIDATION_PROMPT.format(
        source_json=source_json[:8000],   # cap to keep prompt manageable
        regen_json=regen_json[:8000],
    )

    try:
        response = provider.complete(prompt, system=SYSTEM_PROMPT, temperature=0.0, max_tokens=2000)
    except Exception as e:
        logger.error(f"AI validate call failed: {e}")
        return {
            "overall_match": False, "missing_information": [],
            "altered_values": [], "needs_human_review": True,
            "notes": f"Validation failed: {e}",
        }

    data = _safe_json_loads(response)
    if not data:
        return {
            "overall_match": False, "missing_information": [],
            "altered_values": [], "needs_human_review": True,
            "notes": "Could not parse validation response.",
        }
    return data
