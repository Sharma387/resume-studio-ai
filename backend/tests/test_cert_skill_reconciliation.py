"""Deterministic reconciliation of certifications against skills, same chunk only.

The real V4.1 resume puts genuine credentials and six topical tool lines under
one heading, "CERTIFICATIONS & PROFESSIONAL DEVELOPMENT", all in the identical
``• Heading: items`` shape. The source offers no structural cue to separate
them, so the classification has to come from the model — and the model already
supplies it. Measured over five runs of the unmodified production prompt, the
model wrote the correct ``skills`` groups in four of five runs while *also*
re-emitting most of those same categories under ``certifications``. ``merge_chunks``
read both keys and kept both copies, so the tools rendered twice: once under
Certifications and again under Skills.

The policy pinned here:

    When the same category is emitted by both certifications and skills from
    the same mixed chunk, skills takes precedence because the model explicitly
    classified that category as a skill group.

Three properties make this safe, and each has its own test below:

* **Same chunk only.** Another chunk's skill groups say nothing about where
  this chunk's lines belong, so reconciliation never crosses a chunk boundary.
* **Never removes without replacing.** The categories considered are those
  that :func:`_skill_group_categories` accepts — the exact set
  :func:`_add_skill_groups` will merge — so a malformed group cannot drop a
  certification without a skill group taking its place.
* **No skills key means no change.** A single-purpose certifications chunk
  yields an empty set and keeps its previous behaviour byte for byte, which is
  what the completeness fixture relies on.

The headline tests run a *captured* raw model response — verbatim output of
the production prompt, defect included — through the merge. The input contains
the overlap and the output must not, and :func:`merge_chunks` accepts nothing
but the chunk results, so the correction is provably happening in this
deterministic layer rather than through another model call.
"""

from __future__ import annotations

import inspect
import json
import logging

import pytest

from app.services.resume_chunk_parser import CHUNK_PROMPTS, merge_chunks

logger_name = "app.services.resume_chunk_parser"

# ---------------------------------------------------------------------------
# Captured raw model output for the real V4.1 certifications chunk.
#
# Produced by the unmodified production prompt (CHUNK_PROMPTS["certifications"]
# as shipped), qwen2.5:3b-instruct, num_predict=3200, temperature=0.1 — run 2
# of the five-run diagnostic capture. Reproduced verbatim, defect included:
# five of the six skill-group categories appear under BOTH "certifications"
# and "skills", and the genuine credentials sit alongside them.
#
# Recording the real response is what lets these tests assert the correction
# without a model call: the input is fixed, so any change in behaviour is
# attributable to merge_chunks alone.
# ---------------------------------------------------------------------------
V41_RAW_CHUNK_JSON = r"""
{
  "certifications": [
    {
      "name": "PRINCE2 Practitioner",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Professional Credentials",
      "values": []
    },
    {
      "name": "Certified Scrum Master (CSM)",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Professional Credentials",
      "values": []
    },
    {
      "name": "ITIL Foundation Certificate",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Professional Credentials",
      "values": []
    },
    {
      "name": "GitHub Copilot",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "AI & Emerging Technologies",
      "values": []
    },
    {
      "name": "Claude",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "AI & Emerging Technologies",
      "values": []
    },
    {
      "name": "Prompt Engineering",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "AI & Emerging Technologies",
      "values": []
    },
    {
      "name": "LLM Integration",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "AI & Emerging Technologies",
      "values": []
    },
    {
      "name": "RAG",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "AI & Emerging Technologies",
      "values": []
    },
    {
      "name": "Vector Databases",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "AI & Emerging Technologies",
      "values": []
    },
    {
      "name": "MCP",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "AI & Emerging Technologies",
      "values": []
    },
    {
      "name": "AI-Assisted Development",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "AI & Emerging Technologies",
      "values": []
    },
    {
      "name": "ClearPass",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Cloud, IT Infrastructure & Security",
      "values": []
    },
    {
      "name": "Data Center Migration Tools",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Cloud, IT Infrastructure & Security",
      "values": []
    },
    {
      "name": "Cloud Infrastructure",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Cloud, IT Infrastructure & Security",
      "values": []
    },
    {
      "name": "Python",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Data, ETL & Business Intelligence",
      "values": []
    },
    {
      "name": "SQL",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Data, ETL & Business Intelligence",
      "values": []
    },
    {
      "name": "RDBMS",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Data, ETL & Business Intelligence",
      "values": []
    },
    {
      "name": "Tableau",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Data, ETL & Business Intelligence",
      "values": []
    },
    {
      "name": "Talend",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Data, ETL & Business Intelligence",
      "values": []
    },
    {
      "name": "Crystal Reports",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Data, ETL & Business Intelligence",
      "values": []
    },
    {
      "name": "Adobe Experience Manager (AEM)",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Digital Experience & CMS",
      "values": []
    },
    {
      "name": "Sitecore",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Digital Experience & CMS",
      "values": []
    },
    {
      "name": "WordPress",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Digital Experience & CMS",
      "values": []
    },
    {
      "name": "Micro Frontends",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Digital Experience & CMS",
      "values": []
    },
    {
      "name": "Microservices",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Digital Experience & CMS",
      "values": []
    },
    {
      "name": "C#.NET",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Core Software & Engineering",
      "values": []
    },
    {
      "name": "Selenium WebDriver",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Core Software & Engineering",
      "values": []
    },
    {
      "name": "AS400",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Core Software & Engineering",
      "values": []
    },
    {
      "name": "Microsoft 365 Dynamics/Navision (ERP)",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Core Software & Engineering",
      "values": []
    },
    {
      "name": "Xero",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Core Software & Engineering",
      "values": []
    },
    {
      "name": "MYOB",
      "issuer": "Not specified",
      "date": "Not specified",
      "url": "Not specified",
      "category": "Core Software & Engineering",
      "values": []
    }
  ],
  "skills": [
    {
      "category": "AI & Emerging Technologies",
      "skills": [
        "GitHub Copilot",
        "Claude",
        "Prompt Engineering",
        "LLM Integration",
        "RAG",
        "Vector Databases",
        "MCP",
        "AI-Assisted Development"
      ]
    },
    {
      "category": "Enterprise Platforms & DevOps",
      "skills": [
        "ServiceNow",
        "Azure DevOps",
        "Jira",
        "Cherwell",
        "Microsoft Project",
        "MuleSoft"
      ]
    },
    {
      "category": "Data, ETL & Business Intelligence",
      "skills": [
        "Python",
        "SQL",
        "RDBMS",
        "Tableau",
        "Talend",
        "Crystal Reports"
      ]
    },
    {
      "category": "Cloud, IT Infrastructure & Security",
      "skills": [
        "ClearPass",
        "Data Center Migration Tools",
        "Cloud Infrastructure"
      ]
    },
    {
      "category": "Digital Experience & CMS",
      "skills": [
        "Adobe Experience Manager (AEM)",
        "Sitecore",
        "WordPress",
        "Micro Frontends",
        "Microservices"
      ]
    },
    {
      "category": "Core Software & Engineering",
      "skills": [
        "C#.NET",
        "Selenium WebDriver",
        "AS400",
        "Microsoft 365 Dynamics/Navision (ERP)",
        "Xero",
        "MYOB"
      ]
    }
  ]
}
"""


@pytest.fixture
def raw_chunk() -> dict:
    """A fresh parse of the capture.

    ``merge_chunks`` edits the chunk it is given in place, so each test needs
    its own copy rather than a shared one.
    """
    return json.loads(V41_RAW_CHUNK_JSON)


def _cert_categories(chunk: dict) -> set[str]:
    return {
        str(item["category"])
        for item in chunk.get("certifications") or []
        if isinstance(item, dict) and item.get("category")
    }


def _skill_categories(chunk: dict) -> set[str]:
    return {
        str(group["category"])
        for group in chunk.get("skills") or []
        if isinstance(group, dict) and group.get("category")
    }


class TestCapturedV41Payload:
    """The capture must show the defect in, and the correction out."""

    def test_the_capture_actually_contains_the_overlap(self, raw_chunk):
        """Precondition — otherwise these tests prove nothing.

        If the input never overlapped, a clean merged output would say only
        that the model behaved. The capture has to be broken first.
        """
        overlap = _cert_categories(raw_chunk) & _skill_categories(raw_chunk)
        assert len(overlap) == 5, f"capture no longer reproduces the defect: {overlap}"
        assert "AI & Emerging Technologies" in overlap
        assert len(raw_chunk["certifications"]) == 31
        assert len(raw_chunk["skills"]) == 6

    def test_overlapping_categories_are_retained_only_in_skills(self, raw_chunk):
        merged = merge_chunks([("certifications", raw_chunk)])

        overlap = _cert_categories(merged) & _skill_categories(merged)
        assert overlap == set(), f"categories still claimed by both sections: {overlap}"

    def test_overlapping_certification_records_are_removed(self, raw_chunk):
        merged = merge_chunks([("certifications", raw_chunk)])

        # 31 records in, 28 belonging to the five overlapping categories gone.
        assert len(merged["certifications"]) == 3
        assert {c["category"] for c in merged["certifications"]} == {"Professional Credentials"}

    def test_professional_credentials_remains_a_certification(self, raw_chunk):
        merged = merge_chunks([("certifications", raw_chunk)])

        names = [c["name"] for c in merged["certifications"]]
        assert names == [
            "PRINCE2 Practitioner",
            "Certified Scrum Master (CSM)",
            "ITIL Foundation Certificate",
        ]

    def test_every_skill_group_survives_with_its_items(self, raw_chunk):
        merged = merge_chunks([("certifications", raw_chunk)])

        assert [g["category"] for g in merged["skills"]] == [
            "AI & Emerging Technologies",
            "Enterprise Platforms & DevOps",
            "Data, ETL & Business Intelligence",
            "Cloud, IT Infrastructure & Security",
            "Digital Experience & CMS",
            "Core Software & Engineering",
        ]
        # Nothing was dropped to make room: 34 items in, 34 items out.
        assert sum(len(g["skills"]) for g in merged["skills"]) == 34
        assert "GitHub Copilot" in merged["skills"][0]["skills"]

    def test_no_item_is_lost_from_the_resume(self, raw_chunk):
        """Reconciliation relocates, it does not delete.

        Every name the capture produced must still be findable in exactly one
        of the two sections afterwards.
        """
        merged = merge_chunks([("certifications", raw_chunk)])

        cert_names = {c["name"] for c in merged["certifications"]}
        skill_names = {s for g in merged["skills"] for s in g["skills"]}

        before_cert = {c["name"] for c in raw_chunk["certifications"]}
        before_skill = {s for g in raw_chunk["skills"] for s in g["skills"]}
        assert cert_names | skill_names == before_cert | before_skill
        assert not cert_names & skill_names, "the same item now sits in both sections"


class TestCorrectionHappensInTheMerge:
    """Not in another model call — this layer accepts no way to make one."""

    def test_merge_chunks_cannot_reach_a_model(self):
        params = list(inspect.signature(merge_chunks).parameters)
        assert params == ["results"], (
            "merge_chunks takes only the chunk results; a call hook here would "
            "mean the correction depended on another LLM round trip"
        )

    def test_the_same_capture_merges_to_the_same_answer(self, raw_chunk):
        """Fixed input, fixed output — no sampling involved anywhere."""
        first = merge_chunks([("certifications", json.loads(V41_RAW_CHUNK_JSON))])
        second = merge_chunks([("certifications", json.loads(V41_RAW_CHUNK_JSON))])
        assert first == second

    def test_the_overlap_is_present_before_and_absent_after(self, raw_chunk):
        """The delta between raw and merged *is* the reconciliation."""
        merged = merge_chunks([("certifications", raw_chunk)])
        before = _cert_categories(raw_chunk) & _skill_categories(raw_chunk)
        after = _cert_categories(merged) & _skill_categories(merged)

        assert before, "raw capture must overlap"
        assert after == set()
        assert len(before) == 5


class TestNoOverlap:
    """A clean payload must pass through untouched."""

    def test_both_sections_survive_unchanged(self):
        chunk = {
            "certifications": [
                {"name": "PMP", "issuer": "PMI", "date": "2025",
                 "category": "Professional Credentials", "values": []},
                {"name": "AWS Solutions Architect", "category": "Cloud & Architecture",
                 "values": []},
            ],
            "skills": [{"category": "Core Competencies", "skills": ["Python", "SQL"]}],
        }

        merged = merge_chunks([("certifications", dict(chunk))])

        assert [(c["name"], c["category"]) for c in merged["certifications"]] == [
            ("PMP", "Professional Credentials"),
            ("AWS Solutions Architect", "Cloud & Architecture"),
        ]
        assert merged["skills"] == [{"category": "Core Competencies",
                                     "skills": ["Python", "SQL"]}]

    def test_a_shared_item_name_under_a_different_category_is_kept(self):
        """Only a category *match* triggers reconciliation, not any resemblance.

        The two keys may legitimately hold the same string under different
        headings, and a name-level rule would have to guess at meaning.
        """
        chunk = {
            "certifications": [{"name": "Agile", "category": "Professional Credentials"}],
            "skills": [{"category": "Delivery", "skills": ["Agile"]}],
        }

        merged = merge_chunks([("certifications", chunk)])

        assert [c["name"] for c in merged["certifications"]] == ["Agile"]
        assert merged["skills"][0]["skills"] == ["Agile"]


class TestNoSkillsKey:
    """Backward compatibility: absent key, absent policy."""

    def test_certifications_are_untouched_without_a_skills_key(self):
        chunk = {"certifications": [
            {"name": "PMP", "category": "Professional Credentials", "values": []},
            {"name": "PRINCE2 Practitioner", "category": "Professional Credentials", "values": []},
            {"name": "AWS Solutions Architect", "category": "Cloud & Architecture", "values": []},
            {"name": "Azure Fundamentals", "category": "Cloud & Architecture", "values": []},
        ]}

        merged = merge_chunks([("certifications", chunk)])

        assert [c["name"] for c in merged["certifications"]] == [
            "PMP", "PRINCE2 Practitioner", "AWS Solutions Architect", "Azure Fundamentals",
        ]
        assert merged["skills"] == []

    def test_an_empty_skills_list_also_changes_nothing(self):
        chunk = {
            "certifications": [{"name": "PMP", "category": "Professional Credentials"}],
            "skills": [],
        }

        merged = merge_chunks([("certifications", chunk)])

        assert [c["name"] for c in merged["certifications"]] == ["PMP"]
        assert merged["skills"] == []

    def test_a_malformed_skill_group_removes_nothing(self):
        """Safety: nothing is removed unless a valid group replaces it.

        The categories considered are the ones ``_add_skill_groups`` would
        actually merge, so a group it would reject cannot delete a
        certification.
        """
        chunk = {
            "certifications": [{"name": "GitHub Copilot", "category": "AI & Emerging Technologies"}],
            "skills": [{"skills": ["orphan"]}, "not-a-dict", None, {"category": ""}],
        }

        merged = merge_chunks([("certifications", chunk)])

        assert [c["name"] for c in merged["certifications"]] == ["GitHub Copilot"]
        assert merged["skills"] == []


class TestMultipleRecordsSharingACategory:
    """Every record under an overlapping category goes, not just the first."""

    def test_all_records_for_the_category_are_removed(self):
        chunk = {
            "certifications": [
                {"name": "GitHub Copilot", "category": "AI & Emerging Technologies", "values": []},
                {"name": "Claude", "category": "AI & Emerging Technologies", "values": []},
                {"name": "RAG", "category": "AI & Emerging Technologies", "values": []},
                {"name": "Vector Databases", "category": "AI & Emerging Technologies", "values": []},
                {"name": "PMP", "category": "Professional Credentials", "values": []},
            ],
            "skills": [{"category": "AI & Emerging Technologies",
                        "skills": ["GitHub Copilot", "Claude", "RAG", "Vector Databases"]}],
        }

        merged = merge_chunks([("certifications", chunk)])

        assert [c["name"] for c in merged["certifications"]] == ["PMP"]
        assert len(merged["skills"]) == 1

    def test_a_category_only_record_is_removed_too(self):
        """A record with no name still names the category, so it must go."""
        chunk = {
            "certifications": [
                {"category": "Cloud, IT Infrastructure & Security",
                 "values": ["ClearPass", "Cloud Infrastructure"]},
                {"name": "PMP", "category": "Professional Credentials"},
            ],
            "skills": [{"category": "Cloud, IT Infrastructure & Security",
                        "skills": ["ClearPass", "Cloud Infrastructure"]}],
        }

        merged = merge_chunks([("certifications", chunk)])

        assert [c.get("name") for c in merged["certifications"]] == ["PMP"]


class TestOtherChunksAreNeverReconciledAgainst:
    """Precedence is scoped to the chunk that produced both keys."""

    def test_skills_from_another_chunk_do_not_remove_certifications(self):
        results = [
            ("skills", {"skills": [{"category": "AI & Emerging Technologies",
                                    "skills": ["Claude"]}]}),
            ("certifications", {"certifications": [
                {"name": "GitHub Copilot", "category": "AI & Emerging Technologies"},
                {"name": "PMP", "category": "Professional Credentials"},
            ]}),
        ]

        merged = merge_chunks(results)

        assert [c["name"] for c in merged["certifications"]] == [
            "GitHub Copilot", "PMP",
        ]
        assert [g["category"] for g in merged["skills"]] == ["AI & Emerging Technologies"]

    def test_order_of_the_two_chunks_does_not_matter(self):
        certs = ("certifications", {"certifications": [
            {"name": "GitHub Copilot", "category": "AI & Emerging Technologies"},
        ]})
        skills = ("skills", {"skills": [
            {"category": "AI & Emerging Technologies", "skills": ["Claude"]},
        ]})

        for results in ([skills, certs], [certs, skills]):
            merged = merge_chunks(list(results))
            assert [c["name"] for c in merged["certifications"]] == ["GitHub Copilot"]
            assert len(merged["skills"]) == 1

    def test_two_certifications_chunks_reconcile_independently(self):
        """Each chunk is judged only on what it itself emitted."""
        results = [
            ("certifications", {
                "certifications": [{"name": "GitHub Copilot",
                                    "category": "AI & Emerging Technologies"}],
                "skills": [{"category": "AI & Emerging Technologies",
                            "skills": ["Claude"]}],
            }),
            ("certifications", {"certifications": [
                {"name": "Claude", "category": "AI & Emerging Technologies"},
            ]}),
        ]

        merged = merge_chunks(results)

        # First chunk reconciled; second had no skills key, so it stands.
        assert [c["name"] for c in merged["certifications"]] == ["Claude"]
        assert [g["category"] for g in merged["skills"]] == ["AI & Emerging Technologies"]


class TestCompletenessFixtureStillPasses:
    """``Cloud & Architecture`` must stay a certification.

    ``test_parse_completeness`` requires AWS Solutions Architect and Azure
    Fundamentals in ``resume.certifications``, and its fake provider returns
    no ``skills`` key at all — so the policy has nothing to act on. This runs
    that fixture's own text and its own fake provider, with no model call.
    """

    def test_the_fixture_fake_provider_emits_no_skills_key(self):
        from app.services.resume_chunker import chunk_resume
        from tests.test_parse_completeness import RESUME_TEXT, _fake_model

        chunk = next(c for c in chunk_resume(RESUME_TEXT)
                     if c["section"] == "certifications")
        system = f"You are a resume parser. {CHUNK_PROMPTS['certifications']}"

        payload = json.loads(_fake_model(system, chunk["text"]))
        assert "skills" not in payload, (
            "the fixture's fake provider gained a skills key; the "
            "completeness test would no longer be testing this path"
        )

        merged = merge_chunks([("certifications", payload)])
        names = [c["name"] for c in merged["certifications"]]
        assert "AWS Solutions Architect" in names
        assert "Azure Fundamentals" in names
        assert merged["skills"] == []

    def test_credentials_survive_even_when_the_chunk_carries_skills(self):
        """Same text, but a provider that does emit a skills key.

        The topical line is absent from that key, so it must stay a
        certification — precedence only applies to categories the model itself
        classified as skills.
        """
        from app.services.resume_chunker import chunk_resume
        from tests.test_parse_completeness import RESUME_TEXT

        chunk = next(c for c in chunk_resume(RESUME_TEXT)
                     if c["section"] == "certifications")
        payload = {
            "certifications": [
                {"name": "PMP", "category": "Professional Credentials"},
                {"name": "AWS Solutions Architect", "category": "Cloud & Architecture"},
                {"name": "Azure Fundamentals", "category": "Cloud & Architecture"},
            ],
            "skills": [{"category": "Professional Credentials",
                        "skills": ["PMP"]}],
        }
        merged = merge_chunks([("certifications", payload)])

        names = [c["name"] for c in merged["certifications"]]
        assert "AWS Solutions Architect" in names
        assert "Azure Fundamentals" in names
        # Only the category the model explicitly classified moves.
        assert "PMP" not in names
        assert merged["skills"][0]["skills"] == ["PMP"]
        assert chunk["section"] == "certifications"


class TestReconciliationIsLogged:
    """A signal when it fires — categories and counts, never resume content."""

    def test_the_log_names_the_categories_and_how_many_records_moved(self,
                                                                    raw_chunk,
                                                                    caplog):
        with caplog.at_level(logging.DEBUG, logger=logger_name):
            merge_chunks([("certifications", raw_chunk)])

        messages = [r.getMessage() for r in caplog.records
                    if r.name == logger_name]
        signal = [m for m in messages if "Reconciled" in m]
        assert len(signal) == 1, "exactly one reconciliation signal expected"
        assert "28 certification record(s)" in signal[0]
        assert "AI & Emerging Technologies x8" in signal[0]
        assert "Core Software & Engineering x6" in signal[0]

    def test_the_log_carries_no_resume_content(self, raw_chunk, caplog):
        with caplog.at_level(logging.DEBUG, logger=logger_name):
            merge_chunks([("certifications", raw_chunk)])

        text = " ".join(r.getMessage() for r in caplog.records if r.name == logger_name)
        for leaked in ("PRINCE2", "GitHub Copilot", "ClearPass", "RAG",
                       "Certified Scrum Master"):
            assert leaked not in text, f"{leaked!r} should never reach the log"

    def test_nothing_is_logged_when_there_is_nothing_to_reconcile(self,
                                                                  caplog):
        chunk = {"certifications": [{"name": "PMP",
                                     "category": "Professional Credentials"}]}

        with caplog.at_level(logging.DEBUG, logger=logger_name):
            merge_chunks([("certifications", chunk)])

        assert not [r for r in caplog.records
                    if r.name == logger_name and "Reconciled" in r.getMessage()]
