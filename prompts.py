"""
AI prompts for SDS extraction refinement and normalization.

Two prompts:
  1. EXTRACTION_REFINE_PROMPT  - given raw text + the regex-parsed sections,
     ask the AI to fix mis-split sections, recover missing subfields, and
     return a clean JSON payload.
  2. NORMALIZE_SECTION_PROMPT  - given one section's raw text + the target
     standard's title, ask the AI to rewrite the section in the standard
     format (concise paragraphs, GHS codes preserved, no marketing fluff).

Both prompts require JSON-only output (no markdown, no preface) so the
caller can `json.loads` directly.
"""
from __future__ import annotations


# ---- System prompt: shared --------------------------------------------------
SYSTEM_PROMPT = (
    "You are a regulatory document specialist. You process Safety Data Sheets "
    "(SDS) for chemical products. You are precise, conservative, and never "
    "invent information. If a field is missing from the source, you return an "
    "empty string for that field - never guess. You preserve all CAS numbers, "
    "EC numbers, hazard codes (H/P statements), and units exactly as written."
)


# ---- Extraction refinement -------------------------------------------------
EXTRACTION_REFINE_PROMPT = """You are refining the extraction of a Safety Data Sheet.

The source PDF was parsed with regex, which may have mis-split sections or missed
subfields. Your job is to return a clean, structured JSON object that fixes these
issues.

INPUT:
- Standard: {standard_name}
- Detected product info: {product_info}
- Parsed sections (raw text): {sections_json}

OUTPUT (JSON ONLY, no markdown, no commentary):
{{
  "product": {{
    "product_name": "...",
    "product_code": "...",
    "cas_number": "...",
    "ec_number": "...",
    "reach_registration": "...",
    "molecular_formula": "...",
    "synonyms": ["...", "..."],
    "intended_use": "..."
  }},
  "sections": {{
    "1": {{"title": "...", "text": "...", "confidence": 0.0-1.0, "needs_review": false}},
    "2": {{"title": "...", "text": "...", "confidence": 0.0-1.0, "needs_review": false}},
    ...
    "16": {{"title": "...", "text": "...", "confidence": 0.0-1.0, "needs_review": false}}
  }},
  "revision_date": "...",
  "revision_number": "...",
  "supersedes_date": "..."
}}

RULES:
1. Preserve all factual content from the source. Do NOT add information that is
   not present. If a section is empty in the source, return empty text and set
   needs_review=true.
2. Re-attributing text to the correct section is OK (and encouraged) if the regex
   mis-split. For example, if Section 1's text contains transport info, move it
   to Section 14.
3. Confidence: 1.0 = clearly correct, 0.5 = partially correct, 0.0 = unknown.
   Set needs_review=true if confidence < 0.6 OR if the section looks incomplete.
4. The 'title' field must match the standard's expected title for that number
   (use the titles already given in the input).
5. Output JSON ONLY. No ```json fences, no preamble, no postscript.
"""


# ---- Section normalization -------------------------------------------------
NORMALIZE_SECTION_PROMPT = """You are normalizing one section of a Safety Data Sheet to a consistent style.

INPUT:
- Standard: {standard_name}
- Section number: {section_num}
- Section title: {section_title}
- Raw section text:
---
{raw_text}
---

OUTPUT (JSON ONLY):
{{
  "normalized_text": "...",
  "key_value_pairs": {{"Field name": "value", ...}},
  "preserved_codes": ["H225", "P210", ...],
  "needs_review": false
}}

STYLE RULES:
1. Rewrite the section as 1-3 concise paragraphs. Use plain regulatory English.
2. Preserve ALL factual data: CAS numbers, percentages, units, hazard codes
   (H-codes, P-codes, UN numbers, packing groups). These MUST appear verbatim
   in `preserved_codes` if they exist.
3. If the section has obvious structure (e.g. Section 4 First-Aid has
   "Inhalation / Skin / Eye / Ingestion" subheadings), preserve that structure
   as short labeled paragraphs.
4. Remove marketing language, disclaimers unrelated to safety, and redundant
   whitespace.
5. Extract any clear key:value pairs into `key_value_pairs`
   (e.g. {{"Boiling point": "82°C", "Flash point": "12°C"}}).
6. Set needs_review=true if the source text is incomplete, ambiguous, or
   appears to contain text from a different section.
7. Output JSON ONLY. No markdown fences, no commentary.
"""


# ---- Validation ------------------------------------------------------------
VALIDATION_PROMPT = """You are validating a regenerated Safety Data Sheet against its source.

INPUT:
- Source sections (raw): {source_json}
- Regenerated sections (normalized): {regen_json}

OUTPUT (JSON ONLY):
{{
  "overall_match": true|false,
  "missing_information": ["..."],
  "altered_values": [{{"field": "...", "source": "...", "regenerated": "..."}}],
  "needs_human_review": true|false,
  "notes": "..."
}}

RULES:
1. Flag ANY factual change: CAS numbers, percentages, hazard codes, units,
   regulatory references. Cosmetic rewording is OK and should NOT be flagged.
2. `missing_information` lists anything present in source but absent in regen.
3. `needs_human_review=true` if any altered_values or missing_information items
   exist.
4. Output JSON ONLY.
"""
