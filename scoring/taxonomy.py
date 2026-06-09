FEATURE_TAXONOMY = {
    # === IDENTITY ===
    "product_name":     {"type": "str",          "section": "identity"},
    "insurer":          {"type": "str",          "section": "identity"},
    "product_type":     {"type": "enum",         "section": "identity",
                         "values": ["term", "ulip", "savings", "annuity", "child", "health", "group"]},
    "uin_number":       {"type": "str",          "section": "identity"},
    "is_linked":        {"type": "bool",         "section": "identity"},
    "is_participating": {"type": "bool",         "section": "identity"},

    # === ELIGIBILITY ===
    "min_entry_age":        {"type": "int",      "section": "eligibility"},
    "max_entry_age":        {"type": "int",      "section": "eligibility"},
    "min_policy_term":      {"type": "int",      "section": "eligibility"},
    "max_policy_term":      {"type": "int_or_str", "section": "eligibility"},
    "whole_life_option":    {"type": "bool",     "section": "eligibility"},
    "min_sum_assured":      {"type": "float",    "section": "eligibility"},
    "max_sum_assured":      {"type": "float_or_str", "section": "eligibility"},
    "min_annual_premium":   {"type": "float",    "section": "eligibility"},
    "premium_pay_modes":    {"type": "list",     "section": "eligibility"},
    "online_purchase":      {"type": "bool",     "section": "eligibility"},

    # === DEATH BENEFIT ===
    "death_benefit_type":           {"type": "enum", "section": "death_benefit",
                                     "values": ["lump_sum", "income", "combo"]},
    "income_payout_option":         {"type": "bool", "section": "death_benefit"},
    "income_payout_duration":       {"type": "int",  "section": "death_benefit"},
    "terminal_illness_inbuilt":     {"type": "bool", "section": "death_benefit"},
    "increasing_cover_option":      {"type": "bool", "section": "death_benefit"},
    "life_stage_enhancement":       {"type": "bool", "section": "death_benefit"},

    # === RETURNS / SAVINGS ===
    "guaranteed_returns":       {"type": "bool",  "section": "returns"},
    "return_of_premium":        {"type": "bool",  "section": "returns"},
    "rop_percentage":           {"type": "float", "section": "returns"},
    "projected_irr_4pct":       {"type": "float", "section": "returns"},
    "projected_irr_8pct":       {"type": "float", "section": "returns"},
    "loyalty_additions":        {"type": "bool",  "section": "returns"},
    "loyalty_addition_pct":     {"type": "float", "section": "returns"},
    "maturity_booster":         {"type": "bool",  "section": "returns"},
    "capital_guarantee":        {"type": "bool",  "section": "returns"},
    "capital_guarantee_pct":    {"type": "float", "section": "returns"},
    "return_of_charges":        {"type": "bool",  "section": "returns"},

    # === FLEXIBILITY ===
    "partial_withdrawal":           {"type": "bool",        "section": "flexibility"},
    "partial_withdrawal_min_years": {"type": "int",         "section": "flexibility"},
    "systematic_withdrawal_plan":   {"type": "bool",        "section": "flexibility"},
    "fund_switching":               {"type": "bool",        "section": "flexibility"},
    "free_fund_switches":           {"type": "int_or_str",  "section": "flexibility"},
    "premium_holiday":              {"type": "bool",        "section": "flexibility"},
    "premium_holiday_months":       {"type": "int",         "section": "flexibility"},
    "top_up_allowed":               {"type": "bool",        "section": "flexibility"},
    "portfolio_strategies":         {"type": "int",         "section": "flexibility"},
    "loan_against_policy":          {"type": "bool",        "section": "flexibility"},

    # === RIDERS ===
    "critical_illness_rider":   {"type": "bool", "section": "riders"},
    "ci_illnesses_covered":     {"type": "int",  "section": "riders"},
    "accidental_death_rider":   {"type": "bool", "section": "riders"},
    "disability_rider":         {"type": "bool", "section": "riders"},
    "waiver_of_premium":        {"type": "bool", "section": "riders"},
    "family_income_benefit":    {"type": "bool", "section": "riders"},
    "maternity_benefit":        {"type": "bool", "section": "riders"},

    # === CHARGES (ULIP-specific) ===
    "premium_allocation_charge_pct":    {"type": "float", "section": "charges"},
    "policy_admin_charge_monthly":      {"type": "float", "section": "charges"},
    "fund_management_charge_pct":       {"type": "float", "section": "charges"},
    "mortality_charge_basis":           {"type": "str",   "section": "charges"},

    # === SPECIAL FLAGS ===
    "claim_settlement_ratio":   {"type": "float", "section": "special"},
    "bancassurance_available":  {"type": "bool",  "section": "special"},
    "nri_allowed":              {"type": "bool",  "section": "special"},
}

SECTIONS = {
    "identity":     [f for f, m in FEATURE_TAXONOMY.items() if m["section"] == "identity"],
    "eligibility":  [f for f, m in FEATURE_TAXONOMY.items() if m["section"] == "eligibility"],
    "death_benefit":[f for f, m in FEATURE_TAXONOMY.items() if m["section"] == "death_benefit"],
    "returns":      [f for f, m in FEATURE_TAXONOMY.items() if m["section"] == "returns"],
    "flexibility":  [f for f, m in FEATURE_TAXONOMY.items() if m["section"] == "flexibility"],
    "riders":       [f for f, m in FEATURE_TAXONOMY.items() if m["section"] == "riders"],
    "charges":      [f for f, m in FEATURE_TAXONOMY.items() if m["section"] == "charges"],
    "special":      [f for f, m in FEATURE_TAXONOMY.items() if m["section"] == "special"],
}
