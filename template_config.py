"""
Template configuration loader.

Wraps template_config.yaml and exposes typed accessors used by the renderer.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .paths import TEMPLATE_CONFIG_FILE, load_yaml


@dataclass
class Section:
    num: int
    title: str


@dataclass
class Standard:
    code: str
    name: str
    sections: list[Section]


class TemplateConfig:
    def __init__(self, path: Path | None = None):
        self.path = path or TEMPLATE_CONFIG_FILE
        self.data: dict = {}
        self.load()

    def load(self) -> None:
        self.data = load_yaml(self.path)

    @property
    def template(self) -> dict:
        return self.data.get("template", {})

    @property
    def page_size(self) -> str:
        return self.template.get("page_size", "A4")

    @property
    def margins(self) -> dict[str, float]:
        t = self.template
        return {
            "top": t.get("margin_top_mm", 18),
            "bottom": t.get("margin_bottom_mm", 18),
            "left": t.get("margin_left_mm", 18),
            "right": t.get("margin_right_mm", 18),
        }

    @property
    def fonts(self) -> dict[str, str]:
        return {
            "body": self.template.get("font_family_body", "Helvetica"),
            "heading": self.template.get("font_family_heading", "Helvetica-Bold"),
        }

    @property
    def font_sizes(self) -> dict[str, int]:
        t = self.template
        return {
            "body": t.get("font_size_body", 9),
            "heading": t.get("font_size_heading", 11),
            "section_title": t.get("font_size_section_title", 13),
            "header_footer": t.get("font_size_header_footer", 8),
        }

    @property
    def colors(self) -> dict[str, str]:
        t = self.template
        return {
            "text": t.get("color_text", "#1A1A1A"),
            "heading": t.get("color_heading", "#0F2A44"),
            "section_bar": t.get("color_section_bar", "#0F2A44"),
            "section_bar_text": t.get("color_section_bar_text", "#FFFFFF"),
            "table_header_bg": t.get("color_table_header_bg", "#E8ECF0"),
            "table_border": t.get("color_table_border", "#B8C2CC"),
            "link": t.get("color_link", "#1F5FB0"),
        }

    @property
    def logo(self) -> dict:
        return {
            "height_mm": self.template.get("logo_height_mm", 14),
            "max_width_mm": self.template.get("logo_max_width_mm", 50),
            "position": self.template.get("logo_position", "right"),
            "padding_mm": self.template.get("logo_padding_mm", 2),
        }

    @property
    def header_footer(self) -> dict[str, bool]:
        t = self.template
        return {
            "header_show_supplier": t.get("header_show_supplier", True),
            "header_show_document_title": t.get("header_show_document_title", True),
            "footer_show_page_numbers": t.get("footer_show_page_numbers", True),
            "footer_show_revision_date": t.get("footer_show_revision_date", True),
            "footer_disclaimer": t.get("footer_disclaimer", ""),
        }

    @property
    def section_layout(self) -> dict[str, bool]:
        t = self.template
        return {
            "section_bar_full_width": t.get("section_bar_full_width", True),
            "section_number_in_bar": t.get("section_number_in_bar", True),
            "show_empty_sections": t.get("show_empty_sections", True),
        }

    def standards_codes(self) -> list[str]:
        return list(self.data.get("standards", {}).keys())

    def get_standard(self, code: str) -> Optional[Standard]:
        stds = self.data.get("standards", {})
        if code not in stds:
            return None
        s = stds[code]
        sections = [Section(num=r["num"], title=r["title"]) for r in s.get("sections", [])]
        return Standard(code=code, name=s.get("name", code), sections=sections)
