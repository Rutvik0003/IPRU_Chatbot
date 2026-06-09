"""
ICICI Prudential Product Finder — Streamlit UI
Run from project root: streamlit run app.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

import streamlit as st
import plotly.graph_objects as go
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from scoring.profile_mapper import map_profile
from scoring.ranker import rank_ipru

# ─── constants ────────────────────────────────────────────────────────────────

ORANGE = "#F58220"
NAVY   = "#003087"

FEATURE_LABELS: dict[str, str] = {
    "terminal_illness_inbuilt":   "Terminal Illness Cover",
    "critical_illness_rider":     "Critical Illness Rider",
    "ci_illnesses_covered":       "Critical Illnesses Covered",
    "accidental_death_rider":     "Accidental Death Rider",
    "disability_rider":           "Disability Rider",
    "waiver_of_premium":          "Waiver of Premium",
    "family_income_benefit":      "Family Income Benefit",
    "maternity_benefit":          "Maternity Benefit",
    "return_of_premium":          "Return of Premium",
    "income_payout_option":       "Income Payout Option",
    "income_payout_duration":     "Income Payout Duration",
    "whole_life_option":          "Whole Life Cover",
    "increasing_cover_option":    "Increasing Cover",
    "life_stage_enhancement":     "Life Stage Enhancement",
    "partial_withdrawal":         "Partial Withdrawal",
    "systematic_withdrawal_plan": "Systematic Withdrawal Plan",
    "fund_switching":             "Fund Switching",
    "free_fund_switches":         "Free Fund Switches",
    "premium_holiday":            "Premium Holiday",
    "top_up_allowed":             "Top-Up Premium",
    "loan_against_policy":        "Loan Against Policy",
    "portfolio_strategies":       "Portfolio Strategies",
    "guaranteed_returns":         "Guaranteed Returns",
    "loyalty_additions":          "Loyalty Additions",
    "loyalty_addition_pct":       "Loyalty Addition %",
    "maturity_booster":           "Maturity Booster",
    "capital_guarantee":          "Capital Guarantee",
    "capital_guarantee_pct":      "Capital Guarantee %",
    "return_of_charges":          "Return of Charges",
    "projected_irr_4pct":         "Projected IRR @ 4%",
    "projected_irr_8pct":         "Projected IRR @ 8%",
    "online_purchase":            "Online Purchase",
    "nri_allowed":                "NRI Eligible",
    "bancassurance_available":    "Available via Bank",
    "claim_settlement_ratio":     "Claim Settlement Ratio",
    "max_sum_assured":            "Max Sum Assured",
    "min_sum_assured":            "Min Sum Assured",
    "min_entry_age":              "Min Entry Age",
    "max_entry_age":              "Max Entry Age",
    "premium_pay_modes":          "Premium Pay Modes",
    "death_benefit_type":         "Death Benefit Type",
}

DIMENSION_LABELS: dict[str, str] = {
    "protection":  "Protection",
    "returns":     "Returns",
    "flexibility": "Flexibility",
    "riders":      "Riders",
    "eligibility": "Eligibility",
    "charges":     "Charges",
}

TYPE_META: dict[str, tuple[str, str]] = {
    "term":    ("TERM",    "#C62828"),
    "ulip":    ("ULIP",    "#1565C0"),
    "savings": ("SAVINGS", "#2E7D32"),
    "annuity": ("ANNUITY", "#6A1B9A"),
    "child":   ("CHILD",   "#E65100"),
    "health":  ("HEALTH",  "#00695C"),
    "group":   ("GROUP",   "#37474F"),
}

# Answer option → internal key maps
GOAL_MAP = {
    "🛡️  Protect my family":           "protect_family",
    "📈  Grow my wealth":               "wealth_growth",
    "🧓  Plan for retirement":          "retirement",
    "👶  Secure my child's future":     "child_future",
}
RISK_MAP = {
    "🔒  Conservative — guaranteed, safe returns":  "conservative",
    "⚖️  Moderate — some market risk is fine":       "moderate",
    "🚀  Aggressive — maximum growth":               "aggressive",
    "🏦  Capital Safe — protect my principal first": "capital_safe",
}
HORIZON_MAP = {
    "⏱️  Less than 5 years":  "under_5",
    "📅  5 – 10 years":       "5_to_10",
    "📆  10 – 20 years":      "10_to_20",
    "🗓️  More than 20 years": "20_plus",
}
DEP_MAP = {
    "👫  Spouse":          "spouse",
    "🧒  Children":        "children",
    "👴  Parents":         "parents",
    "—   No dependents":  "none",
}
LIQ_MAP = {
    "✅  Yes, anytime — I need full flexibility": "anytime",
    "🔓  Yes, but only after 5 years":           "after_5_years",
    "🔐  No — I can lock it in completely":      "none",
}
HEALTH_MAP = {
    "🏥  Critical illness (cancer, heart attack …)": "critical_illness",
    "🤕  Accident or disability":                     "accident",
    "🩺  Both":                                        "both",
    "—   Neither":                                     "neither",
}
PAY_MAP = {
    "💳  Single lump-sum payment":               "single",
    "📦  Limited pay (5–10 year window)":        "limited",
    "🔄  Regular — throughout the policy term":  "regular",
    "📅  Monthly installments":                  "monthly",
}
MAT_MAP = {
    "🔄  Return of all premiums paid": "rop",
    "💵  Regular income / monthly payout": "income",
    "💰  Lump-sum payout":             "lump_sum",
    "🏛️  Leave as legacy / whole life": "legacy",
}

# ─── page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ICICI Pru Product Finder",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── global CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* ---------- layout ---------- */
[data-testid="stAppViewContainer"] > .main {
    padding-top: 0 !important;
    background: #F4F7FB;
}
[data-testid="stVerticalBlock"] { gap: 0.5rem; }

/* ---------- header ---------- */
.ipru-header {
    background: linear-gradient(135deg, #003087 0%, #0050A0 60%, #0070C0 100%);
    padding: 2.2rem 2.5rem 1.8rem;
    border-radius: 0 0 24px 24px;
    margin: -0.5rem -1rem 2rem -1rem;
}
.ipru-co     { font-size:.85rem; font-weight:700; color:#F58220;
               letter-spacing:2px; text-transform:uppercase; margin-bottom:.4rem; }
.ipru-title  { font-size:2rem; font-weight:800; color:#fff; margin:0; }
.ipru-sub    { font-size:1rem; color:rgba(255,255,255,.8); margin:.5rem 0 0; }

/* ---------- section headings ---------- */
.sec-heading {
    font-size:1.05rem; font-weight:700; color:#003087;
    border-left:4px solid #F58220; padding-left:.7rem;
    margin: 1.2rem 0 .8rem;
}

/* ---------- question label ---------- */
.q-label {
    font-size:.92rem; font-weight:600; color:#1A202C; margin-bottom:.25rem;
}
.q-num {
    display:inline-block; background:#F58220; color:#fff;
    font-size:.68rem; font-weight:700; padding:2px 7px;
    border-radius:20px; margin-right:6px; vertical-align:middle;
}

/* ---------- product cards ---------- */
.prod-header { display:flex; align-items:center; gap:.6rem; margin-bottom:.5rem; }
.rank-badge {
    background:#003087; color:#fff;
    font-size:.7rem; font-weight:800; padding:3px 9px;
    border-radius:20px; white-space:nowrap; flex-shrink:0;
}
.prod-name { font-size:1.1rem; font-weight:700; color:#1A202C; }
.type-badge {
    display:inline-block; font-size:.68rem; font-weight:700;
    padding:3px 9px; border-radius:20px; color:#fff;
    white-space:nowrap; flex-shrink:0;
}

/* ---------- score bar ---------- */
.score-wrap { margin: .4rem 0 .8rem; }
.score-num  { font-size:1.6rem; font-weight:800; display:inline; }
.score-denom{ font-size:.85rem; color:#718096; }
.bar-track  { background:#EDF2F7; border-radius:100px; height:7px; margin-top:5px; }
.bar-fill   { height:7px; border-radius:100px; }

/* ---------- feature pills ---------- */
.feat-matched {
    display:inline-block; background:#E8F5E9; color:#1B5E20;
    font-size:.75rem; font-weight:600; padding:3px 10px;
    border-radius:20px; margin:3px 3px; border:1px solid #A5D6A7;
}
.feat-missing {
    display:inline-block; background:#FFF8E1; color:#E65100;
    font-size:.75rem; font-weight:600; padding:3px 10px;
    border-radius:20px; margin:3px 3px; border:1px solid #FFE082;
}
.pills-section { margin-top:.5rem; }
.pills-label {
    font-size:.7rem; font-weight:700; color:#9CA3AF;
    letter-spacing:1px; text-transform:uppercase; margin-bottom:3px;
}

/* ---------- profile banner ---------- */
.profile-banner {
    background: linear-gradient(135deg,#EFF6FF,#F0FDF4);
    border:1.5px solid #BFDBFE; border-radius:14px;
    padding:1rem 1.5rem; margin-bottom:1.5rem;
}
.profile-title { font-size:.72rem; font-weight:700; color:#6B7280;
                 letter-spacing:1px; text-transform:uppercase; margin-bottom:4px; }
.profile-text  { font-size:1rem; font-weight:600; color:#1E40AF; }
.profile-meta  { font-size:.85rem; color:#4B5563; margin-top:6px; }

/* ---------- results header ---------- */
.results-title { font-size:1.35rem; font-weight:800; color:#003087; margin-bottom:.3rem; }
.results-sub   { font-size:.85rem; color:#718096; margin-bottom:1.2rem; }

/* ---------- divider ---------- */
.thin-hr { border:0; border-top:1px solid #E2E8F0; margin:.8rem 0; }

/* ---------- no-results ---------- */
.no-results {
    background:#FFF7ED; border:1.5px solid #FED7AA; border-radius:12px;
    padding:1.2rem 1.5rem; color:#92400E; font-weight:600;
}
</style>
""", unsafe_allow_html=True)

# ─── header ───────────────────────────────────────────────────────────────────

st.markdown("""
<div class="ipru-header">
  <div class="ipru-co">ICICI Prudential Life Insurance</div>
  <div class="ipru-title">🛡️ Find Your Best-Fit Policy</div>
  <div class="ipru-sub">Answer 8 quick questions — we'll match you to the right ICICI Pru products instantly.</div>
</div>
""", unsafe_allow_html=True)

# ─── helpers ──────────────────────────────────────────────────────────────────

def q_label(n: int, text: str):
    st.markdown(f'<div class="q-label"><span class="q-num">Q{n}</span>{text}</div>',
                unsafe_allow_html=True)


def score_color(score: float) -> str:
    if score >= 65:
        return "#16A34A"
    if score >= 45:
        return "#D97706"
    return "#DC2626"


def make_dim_chart(dim_scores: dict) -> go.Figure:
    ordered = ["protection", "returns", "flexibility", "riders", "eligibility", "charges"]
    labels = [DIMENSION_LABELS[k] for k in ordered if k in dim_scores]
    values = [dim_scores[k] for k in ordered if k in dim_scores]
    peak   = max(values) if values else 1

    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(
            color=values,
            colorscale=[[0, "#FEE2E2"], [0.45, "#FED7AA"], [1.0, "#F58220"]],
            cmin=0, cmax=max(peak, 0.01),
        ),
        text=[f"{v:.1f}" for v in values],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}: %{x:.1f}/100<extra></extra>",
    ))
    fig.update_layout(
        height=200, margin=dict(l=4, r=50, t=4, b=4),
        xaxis=dict(range=[0, max(peak * 1.35, 15)], visible=False, showgrid=False),
        yaxis=dict(autorange="reversed", tickfont=dict(size=11)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


def render_product_card(rank: int, result: dict, max_score: float):
    name       = result.get("product_name") or "Unknown Product"
    ins_type   = (result.get("insurance_type") or "").lower().strip()
    raw_score  = result.get("total_score", 0)
    dim_scores = result.get("dimension_scores", {})
    matched    = result.get("matched_features", [])
    missing    = result.get("missing_features", [])

    # Normalize display score relative to best result → gives intuitive 0-100 feel
    disp_score = (raw_score / max_score * 100) if max_score > 0 else 0
    disp_score = min(100, round(disp_score, 1))

    type_label, type_color = TYPE_META.get(ins_type, (ins_type.upper() or "—", NAVY))
    sc = score_color(disp_score)
    bar_pct = disp_score

    with st.container(border=True):
        left, right = st.columns([2.2, 1.5], gap="large")

        with left:
            st.markdown(f"""
<div class="prod-header">
  <span class="rank-badge">#{rank}</span>
  <span class="prod-name">{name}</span>
  <span class="type-badge" style="background:{type_color};">{type_label}</span>
</div>
<div class="score-wrap">
  <span class="score-num" style="color:{sc};">{disp_score:.0f}</span>
  <span class="score-denom"> / 100 &nbsp; match score</span>
  <div class="bar-track">
    <div class="bar-fill" style="width:{bar_pct}%;
         background:linear-gradient(90deg,{sc},{sc}99);"></div>
  </div>
</div>
""", unsafe_allow_html=True)

            # Matched features
            if matched:
                matched_pills = "".join(
                    f'<span class="feat-matched">✓ {FEATURE_LABELS.get(f, f.replace("_"," ").title())}</span>'
                    for f in matched[:6]
                )
                st.markdown(f"""
<div class="pills-section">
  <div class="pills-label">What this product covers</div>
  {matched_pills}
</div>""", unsafe_allow_html=True)

            # Missing features
            if missing:
                missing_pills = "".join(
                    f'<span class="feat-missing">✗ {FEATURE_LABELS.get(f, f.replace("_"," ").title())}</span>'
                    for f in missing[:4]
                )
                st.markdown(f"""
<div class="pills-section" style="margin-top:6px;">
  <div class="pills-label">Not available in this product</div>
  {missing_pills}
</div>""", unsafe_allow_html=True)

        with right:
            st.markdown('<div style="font-size:.72rem;font-weight:700;color:#9CA3AF;'
                        'letter-spacing:1px;text-transform:uppercase;margin-bottom:2px;">'
                        'Dimension Scores</div>', unsafe_allow_html=True)
            st.plotly_chart(
                make_dim_chart(dim_scores),
                use_container_width=True,
                config={"displayModeBar": False},
            )


def parse_answers(q1, q2, q3, q4, q5, q6, q7, q8) -> dict:
    dependents = [DEP_MAP[d] for d in (q4 or []) if d in DEP_MAP]
    if not dependents:
        dependents = ["none"]
    return {
        "q1_goal":        GOAL_MAP.get(q1, "protect_family"),
        "q2_risk":        RISK_MAP.get(q2, "moderate"),
        "q3_horizon":     HORIZON_MAP.get(q3, "10_to_20"),
        "q4_dependents":  dependents,
        "q5_liquidity":   LIQ_MAP.get(q5, "none"),
        "q6_health_risk": HEALTH_MAP.get(q6, "neither"),
        "q7_pay_mode":    PAY_MAP.get(q7, "regular"),
        "q8_maturity":    MAT_MAP.get(q8, "lump_sum"),
    }


# ─── questionnaire ────────────────────────────────────────────────────────────

col_a, col_b = st.columns(2, gap="large")

with col_a:
    st.markdown('<div class="sec-heading">Your Goals & Risk Profile</div>', unsafe_allow_html=True)

    q_label(1, "What is your primary financial goal?")
    q1 = st.radio("q1", list(GOAL_MAP.keys()), key="q1",
                  label_visibility="collapsed")

    st.markdown("")
    q_label(2, "How comfortable are you with investment risk?")
    q2 = st.radio("q2", list(RISK_MAP.keys()), key="q2",
                  label_visibility="collapsed")

    st.markdown("")
    q_label(3, "How long can you stay invested?")
    q3 = st.radio("q3", list(HORIZON_MAP.keys()), key="q3",
                  label_visibility="collapsed")

    st.markdown("")
    q_label(4, "Who depends on you financially?")
    q4 = st.multiselect("q4", list(DEP_MAP.keys()), key="q4",
                        placeholder="Select all that apply",
                        label_visibility="collapsed")

with col_b:
    st.markdown('<div class="sec-heading">Preferences & Needs</div>', unsafe_allow_html=True)

    q_label(5, "Do you need access to your money before maturity?")
    q5 = st.radio("q5", list(LIQ_MAP.keys()), key="q5",
                  label_visibility="collapsed")

    st.markdown("")
    q_label(6, "Are you concerned about health or accident risks?")
    q6 = st.radio("q6", list(HEALTH_MAP.keys()), key="q6",
                  label_visibility="collapsed")

    st.markdown("")
    q_label(7, "How do you prefer to pay your premiums?")
    q7 = st.radio("q7", list(PAY_MAP.keys()), key="q7",
                  label_visibility="collapsed")

    st.markdown("")
    q_label(8, "What do you expect when the policy matures?")
    q8 = st.radio("q8", list(MAT_MAP.keys()), key="q8",
                  label_visibility="collapsed")

# ─── CTA ──────────────────────────────────────────────────────────────────────

st.markdown("")
_, btn_col, _ = st.columns([3, 2, 3])
with btn_col:
    find_btn = st.button(
        "🔍  Find My Best-Fit Products",
        type="primary",
        use_container_width=True,
    )

# ─── results ──────────────────────────────────────────────────────────────────

if find_btn:
    answers = parse_answers(q1, q2, q3, q4, q5, q6, q7, q8)
    profile = map_profile(answers)

    with st.spinner("Scoring all ICICI Pru products against your profile…"):
        raw_results = rank_ipru(profile, top_k=20)

    # Soft type-match boost (25%) so recommended types surface higher
    type_filter = profile.get("product_type_filter", [])
    if type_filter and raw_results:
        for r in raw_results:
            ptype = (r.get("insurance_type") or "").lower().strip()
            if ptype in type_filter:
                r["total_score"] = min(200, r["total_score"] * 1.25)
        raw_results.sort(key=lambda x: x["total_score"], reverse=True)

    results    = raw_results[:5]
    max_score  = results[0]["total_score"] if results else 1

    st.markdown("<hr/>", unsafe_allow_html=True)

    # Profile banner
    horizon_labels = {"under_5": "< 5 yrs", "5_to_10": "5–10 yrs",
                      "10_to_20": "10–20 yrs", "20_plus": "20+ yrs"}
    type_label_str = ", ".join(t.upper() for t in type_filter) if type_filter else "Any"
    st.markdown(f"""
<div class="profile-banner">
  <div class="profile-title">Your Profile</div>
  <div class="profile-text">🎯 {profile["profile_label"]}</div>
  <div class="profile-meta">
    Recommended plan type: <strong>{type_label_str}</strong>
    &nbsp;·&nbsp; Horizon: <strong>{horizon_labels.get(answers["q3_horizon"], answers["q3_horizon"])}</strong>
    &nbsp;·&nbsp; Premium mode: <strong>{answers["q7_pay_mode"].replace("_", " ").title()}</strong>
    {f'&nbsp;·&nbsp; Hard filters: <strong>{", ".join(profile["hard_filters"].keys())}</strong>' if profile["hard_filters"] else ""}
  </div>
</div>
""", unsafe_allow_html=True)

    if not results:
        st.markdown("""
<div class="no-results">
  ⚠️ No products matched your hard filters. Try adjusting your risk level or maturity preference.
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="results-title">🏆 Top {len(results)} Matching Products</div>',
                    unsafe_allow_html=True)
        st.markdown(
            '<div class="results-sub">Ranked by alignment with your goals, risk profile, and preferences. '
            'Score is relative — 100 = best match among all ICICI Pru products for your profile.</div>',
            unsafe_allow_html=True,
        )

        for i, result in enumerate(results, 1):
            render_product_card(i, result, max_score)

        # Summary comparison table
        with st.expander("📊 Compare all matched products side-by-side", expanded=False):
            import pandas as pd
            rows = []
            for result in results:
                row = {
                    "Product": result.get("product_name", "—"),
                    "Type": (result.get("insurance_type") or "—").upper(),
                    "Match Score": f"{(result['total_score']/max_score*100):.0f}/100",
                    "Protection": f"{result['dimension_scores'].get('protection', 0):.1f}",
                    "Returns":    f"{result['dimension_scores'].get('returns', 0):.1f}",
                    "Flexibility":f"{result['dimension_scores'].get('flexibility', 0):.1f}",
                    "Riders":     f"{result['dimension_scores'].get('riders', 0):.1f}",
                    "Charges":    f"{result['dimension_scores'].get('charges', 0):.1f}",
                }
                rows.append(row)
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # Full feature details for each product
        with st.expander("🔎 Full feature details", expanded=False):
            for i, result in enumerate(results, 1):
                feat = result.get("_raw_features", {})
                meta = feat.get("_meta", {})
                display_fields = {
                    k: v for k, v in feat.items()
                    if k != "_meta" and v is not None
                }
                st.markdown(f"**#{i} {result.get('product_name')}**")
                cols = st.columns(3)
                for j, (k, v) in enumerate(display_fields.items()):
                    label = FEATURE_LABELS.get(k, k.replace("_", " ").title())
                    if isinstance(v, bool):
                        icon = "✅" if v else "❌"
                        val_str = f"{icon} {'Yes' if v else 'No'}"
                    elif isinstance(v, list):
                        val_str = ", ".join(str(x) for x in v)
                    else:
                        val_str = str(v)
                    cols[j % 3].markdown(f"**{label}**  \n{val_str}")
                st.markdown("---")
