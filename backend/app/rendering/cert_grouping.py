"""Group certification records under a single category heading.

A resume lists credentials under headings ("Professional Credentials: A | B |
C"). That structure reaches the renderer in one of two shapes:

* one record holding the whole group — ``category`` set, ``values`` filled;
* the heading repeated on every individual credential — ``category`` set on
  each record with ``name`` filled and ``values`` empty.

Both shapes carry the same information, and a model may even emit both for the
same heading. Rendering one bullet per record therefore repeats the heading
once per credential and drops the credential names, and a resume with dozens of
certifications collapses into a wall of repeated headings. :func:`group_certs`
merges records by category so each heading is emitted once, followed by the
credentials it covers, with values de-duplicated across both shapes.

The renderer and the content analyzer both go through here, so the text that is
measured is the text that is drawn.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field


@dataclass
class CertificationSlot:
    """One heading's worth of certifications, or a standalone credential card.

    ``card`` is set only for a credential that carries its own issuer or date,
    which deserves its own block rather than a slot in a heading's list.
    """

    category: str = ""
    values: list[str] = field(default_factory=list)
    card: object | None = None

    @property
    def is_card(self) -> bool:
        return self.card is not None

    def logical_text(self) -> str:
        """The single string this slot renders as (used for word counting)."""
        if self.card is not None:
            parts = [_field(self.card, "name"), _field(self.card, "issuer"), _field(self.card, "date")]
            return " ".join(part for part in parts if part)
        if not self.values:
            return self.category
        return f"{self.category}: {' | '.join(self.values)}"


def _field(record: object, key: str) -> str:
    if isinstance(record, Mapping):
        value = record.get(key)
    else:
        value = getattr(record, key, None)
    return str(value).strip() if value is not None else ""


def _values_of(record: object) -> list[str]:
    raw = record.get("values") if isinstance(record, Mapping) else getattr(record, "values", None)
    return [text for text in (str(v).strip() for v in (raw or ())) if text]


def group_certs(certs: Iterable[object]) -> list[CertificationSlot]:
    """Merge certification records by category, preserving first-seen order."""
    slots: list[CertificationSlot] = []
    position_by_category: dict[str, int] = {}

    for cert in certs:
        category = _field(cert, "category")
        if not category:
            slots.append(CertificationSlot(card=cert))
            continue

        name = _field(cert, "name")
        if name and (_field(cert, "issuer") or _field(cert, "date")):
            # A credential with its own metadata is a card, not a list item.
            slots.append(CertificationSlot(category=category, card=cert))
            continue

        values = _values_of(cert)
        if name and not values:
            values = [name]

        position = position_by_category.get(category)
        if position is None:
            position_by_category[category] = len(slots)
            slots.append(CertificationSlot(category=category, values=list(values)))
            continue
        existing = slots[position].values
        for value in values:
            if value not in existing:
                existing.append(value)

    return slots
