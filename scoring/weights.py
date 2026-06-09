DIMENSION_WEIGHTS = {
    "protection":   0.28,
    "returns":      0.24,
    "flexibility":  0.20,
    "eligibility":  0.12,
    "riders":       0.10,
    "charges":      0.06,
}

FEATURE_DIM_WEIGHTS = {
    "protection": {
        "min_sum_assured":          0.05,
        "max_sum_assured":          0.20,
        "death_benefit_type":       0.20,
        "whole_life_option":        0.15,
        "terminal_illness_inbuilt": 0.15,
        "increasing_cover_option":  0.15,
        "life_stage_enhancement":   0.10,
    },
    "returns": {
        "guaranteed_returns":   0.20,
        "return_of_premium":    0.20,
        "return_of_charges":    0.15,
        "loyalty_additions":    0.15,
        "projected_irr_8pct":   0.15,
        "maturity_booster":     0.10,
        "capital_guarantee":    0.05,
    },
    "flexibility": {
        "partial_withdrawal":           0.30,
        "systematic_withdrawal_plan":   0.25,
        "fund_switching":               0.20,
        "premium_holiday":              0.15,
        "top_up_allowed":               0.10,
    },
    "riders": {
        "critical_illness_rider":   0.35,
        "waiver_of_premium":        0.30,
        "accidental_death_rider":   0.20,
        "disability_rider":         0.15,
    },
    "eligibility": {
        "min_entry_age":        0.20,
        "max_entry_age":        0.20,
        "online_purchase":      0.20,
        "min_annual_premium":   0.20,
        "premium_pay_modes":    0.20,
    },
    "charges": {
        "premium_allocation_charge_pct":    0.40,
        "fund_management_charge_pct":       0.40,
        "policy_admin_charge_monthly":      0.20,
    },
}

PROFILE_MULTIPLIERS = {
    "goal": {
        "protect_family":   {"protection": 2.0, "riders": 1.8, "returns": 0.5, "flexibility": 0.6},
        "wealth_growth":    {"returns": 2.0, "flexibility": 1.8, "protection": 0.6, "charges": 1.4},
        "retirement":       {"returns": 2.0, "protection": 0.8, "flexibility": 1.4, "riders": 0.8},
        "child_future":     {"riders": 2.2, "returns": 1.6, "protection": 1.2, "flexibility": 0.8},
    },
    "dependents": {
        "children":         {"waiver_of_premium": 2.5, "family_income_benefit": 2.0},
        "parents":          {"income_payout_option": 1.8, "guaranteed_returns": 1.5},
    },
    "risk": {
        "conservative":     {"guaranteed_returns": 2.5, "return_of_premium": 2.0,
                             "fund_management_charge_pct": 0.1},
        "aggressive":       {"return_of_charges": 1.8, "loyalty_additions": 1.8,
                             "systematic_withdrawal_plan": 1.6},
        "capital_safe":     {"capital_guarantee": 3.0, "guaranteed_returns": 2.0},
        "moderate":         {},
    },
    "health_risk": {
        "critical_illness": {"critical_illness_rider": 3.0, "ci_illnesses_covered": 2.0},
        "accident":         {"accidental_death_rider": 3.0, "disability_rider": 2.5},
        "both":             {"critical_illness_rider": 2.5, "accidental_death_rider": 2.5,
                             "disability_rider": 2.0},
        "neither":          {},
    },
    "liquidity": {
        "anytime":      {"partial_withdrawal": 2.5, "loan_against_policy": 2.0,
                         "premium_holiday": 1.8},
        "after_5_years":{"systematic_withdrawal_plan": 2.0, "partial_withdrawal": 1.5},
        "none":         {},
    },
    "maturity": {
        "rop":      {"return_of_premium": 2.5, "rop_percentage": 2.0},
        "income":   {"income_payout_option": 2.5},
        "lump_sum": {"maturity_booster": 1.8, "loyalty_additions": 1.5},
        "legacy":   {"whole_life_option": 2.0, "death_benefit_type": 1.8},
    },
}

HARD_FILTER_RULES = {
    "conservative": {"is_linked": False},
    "aggressive":   {"guaranteed_returns": False},
    "rop":          {"return_of_premium": True},
    "income":       {"income_payout_option": True},
}
