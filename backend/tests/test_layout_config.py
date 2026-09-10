"""Tests for LayoutConfig (Layout Engine, P3.1)."""

import pytest
from pydantic import ValidationError

from app.rendering.layout import (
    ColumnRatio,
    Density,
    GapSize,
    LayoutConfig,
    LayoutMode,
    SectionLayoutConfig,
    SidebarSide,
)
from app.rendering.layout.layout_regions import RegionType


class TestDefaults:
    def test_default_construction(self):
        config = LayoutConfig()
        assert config.mode is LayoutMode.SINGLE
        assert config.sidebar is SidebarSide.LEFT
        assert config.ratio is ColumnRatio.RATIO_35_65
        assert config.gap is GapSize.BALANCED
        assert config.density is Density.NORMAL
        assert config.sections == {}

    def test_default_dump_is_stable(self):
        assert LayoutConfig().model_dump() == {
            "mode": "single",
            "sidebar": "left",
            "ratio": "35/65",
            "gap": "balanced",
            "density": "normal",
            "sections": {},
        }

    def test_default_round_trips(self):
        assert LayoutConfig.model_validate(LayoutConfig().model_dump()) == LayoutConfig()


class TestValidConfigurations:
    def test_valid_two_column_configuration(self):
        config = LayoutConfig(
            mode="two_column",
            sidebar="right",
            ratio="32/68",
            gap="wide",
            density="compact",
            sections={
                "skills": SectionLayoutConfig(region="sidebar", order=1),
                "summary": SectionLayoutConfig(region="main", visible=True),
            },
        )
        assert config.mode is LayoutMode.TWO_COLUMN
        assert config.sidebar is SidebarSide.RIGHT
        assert config.ratio is ColumnRatio.RATIO_32_68
        assert config.gap is GapSize.WIDE
        assert config.density is Density.COMPACT
        assert config.sections["skills"].region is RegionType.SIDEBAR
        assert config.sections["skills"].order == 1
        assert config.sections["summary"].visible is True

    @pytest.mark.parametrize("ratio", ["30/70", "32/68", "35/65", "40/60"])
    def test_all_supported_ratios(self, ratio):
        assert LayoutConfig(ratio=ratio).ratio.value == ratio

    def test_none_section_fields_mean_auto(self):
        config = LayoutConfig(sections={"summary": SectionLayoutConfig()})
        assert config.sections["summary"].region is None
        assert config.sections["summary"].order is None
        assert config.sections["summary"].visible is None


class TestValidation:
    @pytest.mark.parametrize("ratio", ["50/50", "25/75", "0/100", "35/65x"])
    def test_invalid_ratio_rejected(self, ratio):
        with pytest.raises(ValidationError):
            LayoutConfig(ratio=ratio)

    @pytest.mark.parametrize("field", ["mode", "sidebar", "gap", "density"])
    def test_invalid_enum_value_rejected(self, field):
        with pytest.raises(ValidationError):
            LayoutConfig(**{field: "bogus"})

    def test_unknown_section_rejected(self):
        with pytest.raises(ValidationError, match="unknown section"):
            LayoutConfig(sections={"not_a_section": SectionLayoutConfig(region="main")})

    def test_negative_order_rejected(self):
        with pytest.raises(ValidationError):
            LayoutConfig(sections={"skills": SectionLayoutConfig(order=-1)})

    def test_unknown_field_rejected(self):
        with pytest.raises(ValidationError):
            LayoutConfig(**{"mode": "single", "not_a_field": 1})


class TestSerialization:
    def test_section_configuration_serialization(self):
        config = LayoutConfig(sections={"skills": SectionLayoutConfig(region="sidebar", order=2, visible=True)})
        assert config.model_dump()["sections"] == {"skills": {"region": "sidebar", "order": 2, "visible": True}}

    def test_json_round_trip(self):
        config = LayoutConfig(
            mode="two_column",
            sidebar="right",
            ratio="40/60",
            gap="none",
            density="spacious",
            sections={
                "experience": SectionLayoutConfig(region="main", order=0, visible=True),
                "languages": SectionLayoutConfig(region="sidebar"),
            },
        )
        loaded = LayoutConfig.model_validate_json(config.model_dump_json())
        assert loaded == config

    def test_empty_sections_serialize(self):
        assert LayoutConfig().model_dump_json() == (
            '{"mode":"single","sidebar":"left","ratio":"35/65","gap":"balanced","density":"normal","sections":{}}'
        )
