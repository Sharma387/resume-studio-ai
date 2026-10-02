"""Tests for certification grouping by category heading.

A resume groups credentials under headings. The parser can express that either
as one record holding the whole group in ``values`` or as the heading repeated
on every individual credential. Both must render as one bullet per heading with
the credential names present, and the content analyzer must measure the same
logical text the renderer draws.
"""

import re

import pytest

from app.rendering.cert_grouping import group_certs
from app.rendering.components.reference import CertificationsComponent
from app.rendering.content.models import CertificationEntry, ContentView, Profile
from tests.test_content_analyzer import _analyze
from tests.test_tree_html_renderer import _body_text, blue_theme, render_layout_html, sidebar_layout

# The shape the resume parser actually produced: the heading carried on every
# individual credential, ``values`` empty.
#
# Every category here is a credential category. Tool lines from a mixed
# "CERTIFICATIONS & PROFESSIONAL DEVELOPMENT" section are reconciled into
# skills by ``merge_chunks`` before they reach the renderer, so they are no
# longer part of this fixture's intended representation — see
# ``test_cert_skill_reconciliation.py``. These are all genuine credentials.
PER_ITEM = (
    CertificationEntry(name="PRINCE2 Practitioner", category="Professional Credentials"),
    CertificationEntry(name="Certified Scrum Master (CSM)", category="Professional Credentials"),
    CertificationEntry(name="ITIL Foundation Certificate", category="Professional Credentials"),
    CertificationEntry(name="AWS Solutions Architect", category="Cloud & Architecture"),
    CertificationEntry(name="Azure Fundamentals", category="Cloud & Architecture"),
    CertificationEntry(name="CISSP", category="Security Credentials"),
)

# The shape with one record per heading holding the whole group.
PER_GROUP = (
    CertificationEntry(
        category="Professional Credentials",
        values=("PRINCE2 Practitioner", "Certified Scrum Master (CSM)", "ITIL Foundation Certificate"),
    ),
    CertificationEntry(category="Cloud & Architecture", values=("AWS Solutions Architect", "Azure Fundamentals")),
)


def _certs_section(certs: tuple[CertificationEntry, ...], stable_id: str = "resume.certs") -> str:
    cvm = ContentView(
        stable_id=stable_id,
        profile=Profile(full_name="Jane Doe", professional_title="Engineer"),
        certifications=certs,
    )
    html = render_layout_html(cvm, sidebar_layout(), blue_theme())
    match = re.search(r'<section class="resume-section resume-section-certifications".*?</section>', html, re.S)
    assert match is not None
    return match.group(0)


def _lis(section: str) -> list[str]:
    return re.findall(r"<li>.*?</li>", section, re.S)


class TestGroupCerts:
    def test_per_item_records_merge_into_one_slot_per_heading(self):
        slots = group_certs(PER_ITEM)
        assert [s.category for s in slots] == [
            "Professional Credentials",
            "Cloud & Architecture",
            "Security Credentials",
        ]
        assert slots[0].values == ["PRINCE2 Practitioner", "Certified Scrum Master (CSM)", "ITIL Foundation Certificate"]
        assert slots[1].values == ["AWS Solutions Architect", "Azure Fundamentals"]

    def test_per_group_records_pass_through(self):
        slots = group_certs(PER_GROUP)
        assert len(slots) == 2
        assert slots[0].values == ["PRINCE2 Practitioner", "Certified Scrum Master (CSM)", "ITIL Foundation Certificate"]

    def test_mixed_shapes_do_not_duplicate_values(self):
        """A model emitting both shapes for one heading must not double items."""
        slots = group_certs(PER_ITEM + PER_GROUP[:1])
        assert len(slots) == 3
        assert slots[0].values == ["PRINCE2 Practitioner", "Certified Scrum Master (CSM)", "ITIL Foundation Certificate"]

    def test_credential_with_issuer_stays_a_card(self):
        slots = group_certs(
            (
                CertificationEntry(name="PRINCE2 Practitioner", category="Professional Credentials"),
                CertificationEntry(name="PMP", issuer="PMI", date="2025", category="Professional Credentials"),
            )
        )
        assert slots[0].values == ["PRINCE2 Practitioner"]
        assert slots[1].is_card
        assert "PMP" in slots[1].logical_text()

    def test_credential_without_category_is_a_card(self):
        slots = group_certs((CertificationEntry(name="AWS Certified", issuer="Amazon", date="2022"),))
        assert len(slots) == 1
        assert slots[0].is_card
        assert slots[0].logical_text() == "AWS Certified Amazon 2022"

    def test_heading_order_follows_first_appearance(self):
        slots = group_certs(
            (
                CertificationEntry(name="Claude", category="AI"),
                CertificationEntry(name="ServiceNow", category="Enterprise"),
                CertificationEntry(name="RAG", category="AI"),
            )
        )
        assert [s.category for s in slots] == ["AI", "Enterprise"]
        assert slots[0].values == ["Claude", "RAG"]

    def test_blank_values_are_dropped(self):
        slots = group_certs((CertificationEntry(category="AI", values=("Claude", "  ", "")),))
        assert slots[0].values == ["Claude"]

    def test_plain_mapping_records_are_supported(self):
        slots = group_certs(({"name": "Claude", "category": "AI", "values": []},))
        assert slots[0].category == "AI"
        assert slots[0].values == ["Claude"]

    def test_empty_input(self):
        assert group_certs(()) == []


class TestCertificationsComponentGrouping:
    def test_per_item_records_render_one_li_per_heading(self):
        """The reported bug: every heading repeated once per credential."""
        section = _certs_section(PER_ITEM)
        assert _lis(section) == [
            "<li><strong>Professional Credentials:</strong> "
            "PRINCE2 Practitioner | Certified Scrum Master (CSM) | ITIL Foundation Certificate</li>",
            "<li><strong>Cloud &amp; Architecture:</strong> AWS Solutions Architect | Azure Fundamentals</li>",
            "<li><strong>Security Credentials:</strong> CISSP</li>",
        ]

    def test_heading_appears_once_no_matter_how_many_credentials(self):
        section = _certs_section(PER_ITEM)
        assert section.count("Professional Credentials") == 1
        assert section.count("Cloud &amp; Architecture") == 1

    def test_no_credential_name_is_dropped(self):
        body = _body_text(_certs_section(PER_ITEM))
        for name in ("PRINCE2 Practitioner", "Certified Scrum Master (CSM)",
                     "ITIL Foundation Certificate", "AWS Solutions Architect"):
            assert name in body

    def test_both_shapes_render_identically(self):
        per_item = _lis(_certs_section(PER_ITEM[:3], "resume.a"))
        per_group = _lis(_certs_section(PER_GROUP[:1], "resume.b"))
        assert per_item == per_group

    def test_mixed_card_and_group_order_preserved(self):
        section = _certs_section(
            (
                CertificationEntry(category="Professional Credentials", values=("PRINCE2 Practitioner",)),
                CertificationEntry(name="PMP", issuer="PMI", date="2025"),
                CertificationEntry(category="Cloud & Architecture", values=("AWS Solutions Architect",)),
            )
        )
        assert section.index("Professional Credentials") < section.index("PMP")
        assert section.index("PMP") < section.index("Cloud &amp; Architecture")
        assert "PMI · 2025" in section

    def test_credential_with_issuer_renders_as_card_under_its_heading(self):
        section = _certs_section(
            (
                CertificationEntry(name="PRINCE2 Practitioner", category="Professional Credentials"),
                CertificationEntry(name="PMP", issuer="PMI", date="2025", category="Professional Credentials"),
            )
        )
        assert _lis(section) == ["<li><strong>Professional Credentials:</strong> PRINCE2 Practitioner</li>"]
        assert '<p class="resume-text resume-strong">PMP</p>' in section
        assert "PMI · 2025" in section

    def test_heading_without_credentials_still_renders(self):
        section = _certs_section((CertificationEntry(category="In Progress"),))
        assert _lis(section) == ["<li>In Progress</li>"]


class TestContentAnalyzerMatchesRendering:
    def test_item_count_is_one_per_heading(self):
        cvm = ContentView(
            stable_id="resume.measure",
            profile=Profile(full_name="J", professional_title="Engineer"),
            certifications=PER_ITEM,
        )
        metrics = _analyze(cvm).sections["certifications"]
        assert metrics.item_count == 3

    def test_word_count_counts_each_credential_once(self):
        cvm = ContentView(
            stable_id="resume.measure-words",
            profile=Profile(full_name="J", professional_title="Engineer"),
            certifications=PER_ITEM,
        )
        metrics = _analyze(cvm).sections["certifications"]
        # Each logical item is measured on its own, so sum the per-item counts
        # rather than concatenating the items into one string.
        slots = group_certs(PER_ITEM)
        assert metrics.char_count == sum(len(slot.logical_text()) for slot in slots)
        assert metrics.word_count == sum(len(slot.logical_text().split()) for slot in slots)

    def test_heading_is_not_counted_once_per_credential(self):
        """Regression: the 3x-repeated heading inflated the section size."""
        cvm = ContentView(
            stable_id="resume.measure-repeat",
            profile=Profile(full_name="J", professional_title="Engineer"),
            certifications=PER_ITEM[:3],
        )
        metrics = _analyze(cvm).sections["certifications"]
        logical = "Professional Credentials: PRINCE2 Practitioner | Certified Scrum Master (CSM) | ITIL Foundation Certificate"
        assert metrics.item_count == 1
        assert metrics.word_count == len(logical.split())
        assert metrics.char_count == len(logical)

    def test_card_metrics_unchanged(self):
        cvm = ContentView(
            stable_id="resume.measure-card",
            profile=Profile(full_name="J", professional_title="Engineer"),
            certifications=(CertificationEntry(name="PMP", issuer="PMI", date="2025"),),
        )
        metrics = _analyze(cvm).sections["certifications"]
        assert metrics.item_count == 1
        assert metrics.word_count == len("PMP PMI 2025".split())


class TestComponentRegistryContract:
    @pytest.mark.parametrize("certs", [PER_ITEM, PER_GROUP, ()])
    def test_build_render_nodes_is_stable(self, certs):
        content = {"certifications": certs}
        first = CertificationsComponent().build_render_nodes(content, order=0)
        second = CertificationsComponent().build_render_nodes(content, order=0)
        assert first.model_dump() == second.model_dump()

    def test_node_ids_are_unique(self):
        node = CertificationsComponent().build_render_nodes({"certifications": PER_ITEM}, order=0)

        seen: set[str] = set()
        duplicates: list[str] = []

        def walk(current: object) -> None:
            node_id = getattr(current, "node_id", None)
            if node_id is not None:
                if node_id in seen:
                    duplicates.append(node_id)
                seen.add(node_id)
            for child in getattr(current, "children", ()) or ():
                walk(child)

        walk(node)
        assert not duplicates
