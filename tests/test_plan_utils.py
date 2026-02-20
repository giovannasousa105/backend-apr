from plan_utils import get_plan_tier, normalize_plan_name


def test_normalize_plan_name_defaults_to_free():
    assert normalize_plan_name(None) == "free"
    assert normalize_plan_name("") == "free"
    assert normalize_plan_name("  ") == "free"
    assert normalize_plan_name("pro") == "pro"
    assert normalize_plan_name("PrO") == "pro"
    assert normalize_plan_name("unknown") == "free"


def test_get_plan_tier_features_and_limits():
    free_tier = get_plan_tier("free")
    pro_tier = get_plan_tier("pro")
    enterprise_tier = get_plan_tier("enterprise")

    assert free_tier.features.pdf_logo is False
    assert free_tier.features.pdf_watermark is True
    assert free_tier.limits.max_active_aprs == 5
    assert free_tier.limits.ai_generations_per_month == 3
    assert free_tier.limits.evidence_per_step == 1

    assert pro_tier.features.pdf_logo is True
    assert pro_tier.features.pdf_watermark is False
    assert pro_tier.limits.max_active_aprs is None
    assert pro_tier.limits.ai_generations_per_month == 100
    assert pro_tier.limits.evidence_per_step is None

    assert enterprise_tier.features.history is True
    assert enterprise_tier.limits.max_active_aprs is None
    assert enterprise_tier.limits.ai_generations_per_month is None
