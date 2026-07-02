"""
Supplier / Legal Entity data model and database.

Suppliers are persisted to config/suppliers.yaml. The Supplier class is the
single source of truth - the GUI, batch processor, and PDF renderer all use it.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from .paths import SUPPLIERS_FILE, load_yaml, resolve_path, save_yaml


@dataclass
class Address:
    street: str = ""
    street2: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = ""


@dataclass
class Supplier:
    id: str
    legal_name: str
    dba: str = ""
    address: Address = field(default_factory=Address)
    phone: str = ""
    emergency_phone: str = ""
    website: str = ""
    email: str = ""
    regulatory_contact: str = ""
    logo_path: str = ""  # relative to APP_ROOT or absolute

    @classmethod
    def from_dict(cls, d: dict) -> "Supplier":
        addr = Address(**(d.get("address") or {}))
        return cls(
            id=d["id"],
            legal_name=d.get("legal_name", ""),
            dba=d.get("dba", ""),
            address=addr,
            phone=d.get("phone", ""),
            emergency_phone=d.get("emergency_phone", ""),
            website=d.get("website", ""),
            email=d.get("email", ""),
            regulatory_contact=d.get("regulatory_contact", ""),
            logo_path=d.get("logo_path", ""),
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    def resolved_logo_path(self) -> Optional[Path]:
        """Return absolute Path to the logo if it exists, else None."""
        if not self.logo_path:
            return None
        p = resolve_path(self.logo_path)
        return p if p.exists() else None


class SupplierDB:
    """In-memory list of suppliers, backed by suppliers.yaml."""

    def __init__(self, path: Path | None = None):
        self.path = path or SUPPLIERS_FILE
        self.suppliers: list[Supplier] = []
        self.load()

    def load(self) -> None:
        data = load_yaml(self.path)
        rows = data.get("suppliers", []) or []
        self.suppliers = [Supplier.from_dict(r) for r in rows]

    def save(self) -> None:
        save_yaml(self.path, {"suppliers": [s.to_dict() for s in self.suppliers]})

    def get(self, supplier_id: str) -> Optional[Supplier]:
        for s in self.suppliers:
            if s.id == supplier_id:
                return s
        return None

    def add(self, supplier: Supplier) -> None:
        if not supplier.id:
            supplier.id = f"supplier_{uuid.uuid4().hex[:8]}"
        if self.get(supplier.id) is not None:
            raise ValueError(f"Supplier ID {supplier.id!r} already exists")
        self.suppliers.append(supplier)
        self.save()

    def update(self, supplier: Supplier) -> None:
        for i, s in enumerate(self.suppliers):
            if s.id == supplier.id:
                self.suppliers[i] = supplier
                self.save()
                return
        raise ValueError(f"Supplier ID {supplier.id!r} not found")

    def remove(self, supplier_id: str) -> None:
        self.suppliers = [s for s in self.suppliers if s.id != supplier_id]
        self.save()

    def list_names(self) -> list[tuple[str, str]]:
        """Return [(id, display_name), ...] for dropdowns."""
        out = []
        for s in self.suppliers:
            name = s.dba if s.dba else s.legal_name
            out.append((s.id, name))
        return out
