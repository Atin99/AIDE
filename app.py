import sys, os, time, json
import os
if os.path.exists('.env'):
    with open('.env') as f:
        for line in f:
            if '=' in line and not line.strip().startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k.strip()] = v.strip()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import streamlit as st
    import pandas as pd
    import plotly.graph_objects as go
except ImportError:
    print("Run: pip install streamlit pandas plotly  then  streamlit run app.py")
    sys.exit(1)

from core.elements import validate_composition, available
from core.alloy_db import lookup_alloy, ALLOY_DATABASE
from physics.filter import run_all
from physics.base import (density_rule_of_mixtures, vec, delta_size,
                          PREN_wt, mol_to_wt, wt_to_mol)
from engines.modes import route
from llms.intent_parser import classify_intent
from llms.conversation_memory import ConversationMemory
from core.data_hub import get_hub

st.set_page_config(page_title="AIDE v5.0", page_icon="🔬", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; max-width: 1400px; }
    .stChatMessage { font-size: 0.95rem; }
    h1 { font-size: 1.6rem !important; }
    h2 { font-size: 1.3rem !important; }
    h3 { font-size: 1.1rem !important; }
    .stMetric label { font-size: 0.85rem; }
    .stMetric [data-testid="stMetricValue"] { font-size: 1.4rem; }
    div[data-testid="stExpander"] summary { font-size: 0.95rem; font-weight: 600; }
    .thinking-step {
        padding: 0.4rem 0.8rem;
        margin: 0.2rem 0;
        border-left: 3px solid #4A90D9;
        background: #f8f9fa;
        font-size: 0.85rem;
    }
    .step-action { color: #4A90D9; font-weight: 600; }
    .agent-tag {
        display: inline-block;
        padding: 0 0.4rem;
        border-radius: 3px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.3rem;
    }
    .agent-compose { background: #e3f2fd; color: #1565c0; }
    .agent-evaluate { background: #e8f5e9; color: #2e7d32; }
    .agent-analyze { background: #fff3e0; color: #e65100; }
</style>
""", unsafe_allow_html=True)

if "memory" not in st.session_state:
    st.session_state.memory = ConversationMemory()
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

DOMAIN_NAMES = {
    1: "Thermodynamics", 2: "Hume-Rothery", 3: "Mechanical", 4: "Corrosion",
    5: "Oxidation", 6: "Radiation Physics", 7: "Weldability", 8: "Creep",
    9: "Fatigue & Fracture", 10: "Grain Boundary", 11: "Hydrogen Embrittlement",
    12: "Magnetism", 13: "Thermal Properties", 14: "Regulatory & Safety",
    15: "Electronic Structure", 16: "Superconductivity", 17: "Phase Stability",
    18: "Plasticity", 19: "Diffusion", 20: "Surface Energy",
    21: "Tribology & Wear", 22: "Acoustic Properties", 23: "Shape Memory",
    24: "Catalysis", 25: "Biocompatibility", 26: "Relativistic Effects",
    27: "Nuclear Fuel Compatibility", 28: "Optical Properties",
    29: "Hydrogen Storage", 30: "Structural Efficiency", 31: "CALPHAD Stability",
    32: "India Corrosion Index", 33: "Transformation Kinetics",
    34: "Castability", 35: "Machinability", 36: "Formability",
    37: "Additive Manufacturing", 38: "Heat Treatment Response",
    39: "Fracture Mechanics", 40: "Impact Toughness",
    41: "Galvanic Compatibility", 42: "Solidification",
}

COMMON_ELEMENTS = [
    "Fe", "Cr", "Ni", "Mo", "Mn", "C", "Si", "Ti", "Al", "V",
    "W", "Co", "Cu", "Nb", "Zr", "N", "Ta", "Hf", "B", "Re",
]

EDITOR_WEIGHT_PROFILES = {
    "Auto (from goal text)": "auto",
    "Balanced": "balanced",
    "Structural": "structural",
    "Corrosion-critical": "corrosion",
    "High-temperature": "high_temp",
    "Nuclear": "nuclear",
    "Biomedical": "biomedical",
    "Conductive/Electronic": "conductive",
    "Manufacturing": "manufacturing",
    "Catalysis": "catalysis",
}


def fmt_comp(comp, top=6):
    return "  ".join(f"{s}:{v*100:.1f}%"
                    for s, v in sorted(comp.items(), key=lambda x: -x[1])[:top])


def make_radar_chart(domain_results, title="Domain Scores"):
    names = [dr.domain_name[:20] for dr in domain_results]
    scores = [dr.score() for dr in domain_results]
    names.append(names[0])
    scores.append(scores[0])

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=scores, theta=names,
        fill='toself',
        fillcolor='rgba(74, 144, 217, 0.2)',
        line=dict(color='#4A90D9', width=2),
        name='Score',
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=9)),
            angularaxis=dict(tickfont=dict(size=8)),
        ),
        title=dict(text=title, font=dict(size=14)),
        height=420,
        margin=dict(l=60, r=60, t=50, b=30),
        showlegend=False,
    )
    return fig


def make_comparison_radar(domain_results_1, domain_results_2, name1, name2):
    names = [dr.domain_name[:20] for dr in domain_results_1]
    scores1 = [dr.score() for dr in domain_results_1]
    scores2 = [dr.score() for dr in domain_results_2]
    names.append(names[0])
    scores1.append(scores1[0])
    scores2.append(scores2[0])

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=scores1, theta=names,
        fill='toself',
        fillcolor='rgba(74, 144, 217, 0.15)',
        line=dict(color='#4A90D9', width=2),
        name=name1,
    ))
    fig.add_trace(go.Scatterpolar(
        r=scores2, theta=names,
        fill='toself',
        fillcolor='rgba(244, 67, 54, 0.15)',
        line=dict(color='#f44336', width=2),
        name=name2,
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=9)),
            angularaxis=dict(tickfont=dict(size=8)),
        ),
        title=dict(text=f"{name1} vs {name2}", font=dict(size=14)),
        height=500,
        margin=dict(l=60, r=60, t=50, b=30),
        showlegend=True,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )
    return fig


def make_comparison_bar(domain_results_1, domain_results_2, name1, name2):
    names = [dr.domain_name for dr in domain_results_1]
    scores1 = [dr.score() for dr in domain_results_1]
    scores2 = [dr.score() for dr in domain_results_2]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=names, x=scores1, orientation='h',
        name=name1, marker_color='#4A90D9', opacity=0.8,
    ))
    fig.add_trace(go.Bar(
        y=names, x=scores2, orientation='h',
        name=name2, marker_color='#f44336', opacity=0.8,
    ))
    fig.update_layout(
        barmode='group',
        title=dict(text="Domain-by-Domain Comparison", font=dict(size=14)),
        xaxis=dict(range=[0, 100], title="Score"),
        height=max(400, len(names) * 24),
        margin=dict(l=200, r=20, t=40, b=30),
        legend=dict(yanchor="bottom", y=0.01, xanchor="right", x=0.99),
    )
    return fig


def make_multi_radar(alloy_data):
    colors = ['#4A90D9', '#f44336', '#4CAF50', '#FF9800', '#9C27B0',
              '#00BCD4', '#795548', '#607D8B']
    fig = go.Figure()

    for i, (name, domain_results) in enumerate(alloy_data):
        names = [dr.domain_name[:20] for dr in domain_results]
        scores = [dr.score() for dr in domain_results]
        names.append(names[0])
        scores.append(scores[0])
        color = colors[i % len(colors)]

        fig.add_trace(go.Scatterpolar(
            r=scores, theta=names,
            fill='toself',
            fillcolor=color.replace(')', ',0.08)').replace('rgb', 'rgba').replace('#', 'rgba(')
                if color.startswith('rgb') else f'rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.1)',
            line=dict(color=color, width=2),
            name=name,
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=9)),
            angularaxis=dict(tickfont=dict(size=7)),
        ),
        title=dict(text="Multi-Alloy Comparison", font=dict(size=14)),
        height=550,
        margin=dict(l=60, r=60, t=50, b=30),
        showlegend=True,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )
    return fig


def make_score_bar_chart(domain_results, title="Domain Scores"):
    names = [dr.domain_name for dr in domain_results]
    scores = [dr.score() for dr in domain_results]
    colors = ['#4CAF50' if s >= 70 else '#FF9800' if s >= 40 else '#f44336'
              for s in scores]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=names, x=scores,
        orientation='h',
        marker_color=colors,
        text=[f"{s:.0f}" for s in scores],
        textposition='auto',
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        xaxis=dict(range=[0, 100], title="Score"),
        height=max(300, len(names) * 22),
        margin=dict(l=180, r=20, t=40, b=30),
    )
    return fig


def show_thinking_log(steps):
    if not steps:
        return
    with st.expander(" Thinking Log", expanded=True):
        for s in steps:
            step = s if isinstance(s, dict) else s.__dict__
            stage = step.get("stage", "")
            thought = step.get("thought", "")
            obs = step.get("observation", "")
            agent = step.get("agent", "")

            agent_class = ""
            if "Compos" in agent or "compose" in stage:
                agent_class = "agent-compose"
            elif "Evaluat" in agent or "evaluate" in stage:
                agent_class = "agent-evaluate"
            elif "Analyst" in agent or "Refin" in agent or "analyze" in stage:
                agent_class = "agent-analyze"

            agent_tag = (f'<span class="agent-tag {agent_class}">{agent}</span>'
                        if agent else '')

            st.markdown(
                f'<div class="thinking-step">'
                f'{agent_tag}'
                f'<span class="step-action">[{stage.upper()}]</span> '
                f'{thought}'
                f'{"<br><small>" + obs + "</small>" if obs else ""}'
                f'</div>',
                unsafe_allow_html=True
            )


def show_domain_checks(checks_list):
    for ch in checks_list:
        status_map = {
            "PASS": "🟢", "FAIL": "", "WARN": "🟡", "INFO": "ℹ",
        }
        if hasattr(ch, "status"):
            status, name = ch.status, ch.name
            value, unit = ch.value, ch.unit
            message = ch.message
            formula, citation = ch.formula, ch.citation
        else:
            status = ch.get("status", "")
            name = ch.get("name", "")
            value, unit = ch.get("value"), ch.get("unit", "")
            message = ch.get("message", "")
            formula, citation = ch.get("formula"), ch.get("citation")

        icon = status_map.get(status, "")
        val_str = f" = {value:.4g} {unit}" if value is not None else ""
        st.markdown(f"**{icon} {name}**{val_str}")
        st.markdown(f"> {message}")
        if formula:
            st.code(formula, language="text")
        if citation:
            st.caption(f"Ref: {citation}")


def show_properties(comp_mol):
    c1, c2, c3, c4 = st.columns(4)
    d = density_rule_of_mixtures(comp_mol)
    VEC_v = vec(comp_mol)
    delt = delta_size(comp_mol)
    fe = comp_mol.get("Fe", 0)
    cr = comp_mol.get("Cr", 0)
    pren = PREN_wt(comp_mol) if fe > 0.3 and cr > 0.05 else None
    c1.metric("Density", f"{d:.3f} g/cm³" if d else "N/A")
    c2.metric("VEC", f"{VEC_v:.2f}")
    c3.metric("δ (size)", f"{delt:.2f}%")
    c4.metric("PREN", f"{pren:.1f}" if pren else "N/A")


def domain_table(domain_results):
    rows = []
    for dr in domain_results:
        rows.append({
            "ID": dr.domain_id, "Domain": dr.domain_name,
            "Score": round(dr.score(), 1),
            "Pass": dr.n_pass, "Warn": dr.n_warn, "Fail": dr.n_fail,
        })
    return pd.DataFrame(rows)


def _generate_txt(query, intent, result, elapsed):
    lines = [
        "=" * 70, "AIDE v5.0 -- Alloy Analysis Report", "=" * 70,
        f"Query: {query}",
        f"Mode: {intent.get('mode', 'design').upper()}",
        f"Time: {elapsed:.1f}s",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    mode = result.get("mode", "design")

    if mode == "design" and result.get("top"):
        lines.append("TOP CANDIDATES")
        lines.append("-" * 70)
        for rank, (comp, r) in enumerate(result["top"][:10], 1):
            lines.append(f"#{rank}  Score: {r['composite_score']:.1f}/100  "
                         f"P={r['n_pass']} W={r['n_warn']} F={r['n_fail']}")
            lines.append(f"  Composition: {fmt_comp(comp, 6)}")
            if rank <= 3:
                for dr in r["domain_results"]:
                    lines.append(f"  [{dr.domain_id:2d}] {dr.domain_name:<30} {dr.score():.1f}/100")
                    for ch in dr.checks:
                        val_str = f" = {ch.value:.4g} {ch.unit}" if ch.value is not None else ""
                        lines.append(f"    [{ch.status}] {ch.name}{val_str}")
                        lines.append(f"      {ch.message}")
                        if ch.formula:
                            lines.append(f"      Formula: {ch.formula}")
                        if ch.citation:
                            lines.append(f"      Ref: {ch.citation}")
            lines.append("")

    elif mode == "study" and result.get("sections"):
        lines.append(f"STUDY: {result.get('topic', '')}")
        lines.append("-" * 70)
        for sec in result["sections"]:
            lines.append(f"\n{sec['domain']} -- {sec['score']:.1f}/100")
            for ch in sec.get("checks", []):
                val_str = (f" = {ch['value']:.4g} {ch['unit']}"
                           if ch.get("value") is not None else "")
                lines.append(f"  [{ch['status']}] {ch['name']}{val_str}")
                lines.append(f"    {ch['message']}")

    elif mode == "modify":
        lines.append(f"MODIFY: {result.get('alloy_name', '')}")
        orig = result.get("original_result", {})
        lines.append(f"Original Score: {orig.get('composite_score', 0):.1f}/100")
        for mod in result.get("modifications", []):
            lines.append(f"\n  Suggestion: {mod['description']}")
            lines.append(f"    New score: {mod['result']['composite_score']:.1f}/100 "
                         f"(delta: {mod['delta_score']:+.1f})")

    elif mode == "compare":
        a1, a2 = result.get("alloy_1", {}), result.get("alloy_2", {})
        lines.append(f"COMPARE: {a1.get('name','')} vs {a2.get('name','')}")
        lines.append(f"Winner: {result.get('overall_winner', '')}")
        for row in result.get("comparison", []):
            lines.append(f"  {row['domain']:<32} "
                         f"{row['score_1']:>6.1f} {row['score_2']:>6.1f}  {row['winner']}")

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)


def _render_result(result, show_detail, use_ml):
    mode = result.get("mode", "design")
    if mode == "design" and result.get("top"):
        rows = []
        for rank, (comp, r) in enumerate(result["top"][:5], 1):
            rows.append({"#": rank, "Score": round(r["composite_score"], 1),
                        "Composition": fmt_comp(comp, 5)})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _display_result(result, mode, intent, query, show_detail, use_ml, elapsed):

    if mode == "chat":
        response = result.get("response", "")
        st.markdown(response)
        return response

    steps = result.get("thinking_steps", [])
    if steps:
        show_thinking_log(steps)

    if mode == "design":
        top = result.get("top", [])
        if not top:
            st.warning("No candidates found.")
            return "No candidates found for this query."

        c1, c2, c3 = st.columns(3)
        c1.metric("Best Score", f"{result.get('best_score', 0):.1f}/100")
        c2.metric("Candidates", result.get("n_candidates", 0))
        c3.metric("Iterations", result.get("iterations", 1))

        st.subheader("Top Candidates")
        rows = []
        for rank, (comp, r) in enumerate(top[:10], 1):
            rows.append({
                "#": rank,
                "Score": round(r["composite_score"], 1),
                "P": r["n_pass"], "W": r["n_warn"], "F": r["n_fail"],
                "Composition": fmt_comp(comp, 5),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        detail = result.get("candidates_detail", [])
        for i, cd in enumerate(detail[:3]):
            rationale = cd.get("rationale", "")
            if rationale and rationale != "Template-generated candidate":
                st.markdown(f"**#{i+1} Rationale:** {rationale}")

        if top:
            try:
                from llms.explainer import explain_candidate
                explanation = explain_candidate(
                    top[0][0], top[0][1].get("composite_score", 0),
                    detail[0].get("rationale", "") if detail else "",
                    detail[0].get("weak_domains", []) if detail else [],
                    rank=1)
                if explanation:
                    st.markdown("---")
                    st.markdown("** AI Analysis (Top Candidate):**")
                    st.markdown(explanation)
            except Exception:
                pass

        for rank, (comp, r) in enumerate(top[:3], 1):
            with st.expander(f"Candidate #{rank} — {r['composite_score']:.1f}/100"):
                show_properties(comp)

                st.plotly_chart(make_radar_chart(r["domain_results"],
                               f"#{rank} Domain Profile"), use_container_width=True)

                st.dataframe(domain_table(r["domain_results"]),
                            use_container_width=True, hide_index=True)

                if show_detail:
                    for dr in r["domain_results"]:
                        with st.expander(f"[{dr.domain_id}] {dr.domain_name} — {dr.score():.1f}"):
                            show_domain_checks(dr.checks)

        if top:
            hub = get_hub()
            cost = hub.estimate_cost(mol_to_wt(top[0][0]))
            if cost:
                st.caption(f"Est. raw material cost: ${cost:.2f}/kg")

        txt = _generate_txt(query, intent, result, elapsed)
        st.download_button(" Download Report (TXT)", data=txt,
                           file_name="AIDE_v3_report.txt", mime="text/plain",
                           key=f"dl_design_{time.time()}")

        return f"Found {len(top)} candidates. Best score: {result.get('best_score', 0):.1f}/100."

    elif mode == "modify":
        if result.get("error"):
            st.error(result["error"])
            return result["error"]

        orig = result.get("original_result", {})
        st.metric("Original Score", f"{orig.get('composite_score', 0):.1f}/100")

        weak = result.get("weak_domains", [])
        if weak:
            st.markdown("**Weak Domains:**")
            st.dataframe(pd.DataFrame(weak, columns=["Domain", "Score"]),
                        use_container_width=True, hide_index=True)

        mods = result.get("modifications", [])
        if mods:
            st.markdown("**Suggested Modifications:**")
            for i, mod in enumerate(mods[:5], 1):
                delta = mod["delta_score"]
                with st.expander(f"Option {i}: {mod['description'][:80]} ({delta:+.1f})"):
                    st.metric("New Score", f"{mod['result']['composite_score']:.1f}/100")
                    st.markdown(f"`{fmt_comp(mod['composition'])}`")

        txt = _generate_txt(query, intent, result, elapsed)
        st.download_button(" Download Report (TXT)", data=txt,
                           file_name="AIDE_v3_modify_report.txt", mime="text/plain",
                           key=f"dl_modify_{time.time()}")

        return f"Analyzed {result.get('alloy_name', 'alloy')}. {len(mods)} suggestions."

    elif mode == "study":
        sections = result.get("sections", [])
        if not sections:
            st.warning("No analysis available.")
            return "No analysis data."

        explanation = result.get("explanation", "")
        if explanation:
            st.markdown("** AI Explanation:**")
            st.markdown(explanation)

        if result.get("analysis"):
            a = result["analysis"]
            c1, c2, c3 = st.columns(3)
            c1.metric("Score", f"{a['composite_score']:.1f}/100")
            c2.metric("Domains", a["n_domains"])
            c3.metric("Checks", a["n_pass"] + a["n_warn"] + a["n_fail"])

            st.plotly_chart(make_radar_chart(a["domain_results"],
                           "Domain Profile"), use_container_width=True)

        for sec in sections:
            with st.expander(f"{sec['domain']} — {sec['score']:.1f}/100"):
                show_domain_checks(sec.get("checks", []))

        txt = _generate_txt(query, intent, result, elapsed)
        st.download_button(" Download Report (TXT)", data=txt,
                           file_name="AIDE_v3_study_report.txt", mime="text/plain",
                           key=f"dl_study_{time.time()}")

        return f"Study of {result.get('topic', 'topic')}."

    elif mode == "compare":
        if result.get("error"):
            st.error(result["error"])
            return result["error"]

        a1, a2 = result["alloy_1"], result["alloy_2"]
        c1, c2 = st.columns(2)
        c1.metric(a1["name"], f"{a1['result']['composite_score']:.1f}/100")
        c2.metric(a2["name"], f"{a2['result']['composite_score']:.1f}/100")
        st.markdown(f"**Winner: {result['overall_winner']}**")

        try:
            from llms.explainer import explain_comparison
            comp_explanation = explain_comparison(a1["name"], a2["name"], result)
            if comp_explanation:
                st.markdown("** AI Analysis:**")
                st.markdown(comp_explanation)
        except Exception:
            pass

        cost1 = a1.get("cost_usd_kg")
        cost2 = a2.get("cost_usd_kg")
        if cost1 and cost2:
            cc1, cc2 = st.columns(2)
            cc1.metric(f"{a1['name']} Cost", f"${cost1:.2f}/kg")
            cc2.metric(f"{a2['name']} Cost", f"${cost2:.2f}/kg")

        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.plotly_chart(make_comparison_radar(
                a1["result"]["domain_results"],
                a2["result"]["domain_results"],
                a1["name"], a2["name"]),
                use_container_width=True)
        with chart_col2:
            st.plotly_chart(make_comparison_bar(
                a1["result"]["domain_results"],
                a2["result"]["domain_results"],
                a1["name"], a2["name"]),
                use_container_width=True)

        comp_rows = []
        for row in result.get("comparison", []):
            comp_rows.append({
                "Domain": row["domain"],
                a1["name"]: round(row["score_1"], 1),
                a2["name"]: round(row["score_2"], 1),
                "Winner": row["winner"],
            })
        st.dataframe(pd.DataFrame(comp_rows),
                    use_container_width=True, hide_index=True)

        txt = _generate_txt(query, intent, result, elapsed)
        st.download_button(" Download Report (TXT)", data=txt,
                           file_name="AIDE_v3_compare_report.txt", mime="text/plain",
                           key=f"dl_compare_{time.time()}")

        return f"Compared {a1['name']} vs {a2['name']}. Winner: {result['overall_winner']}."

    elif mode == "explore":
        db = result.get("db_matches", [])
        gen = result.get("generated_matches", [])

        if db:
            st.markdown(f"**Known Alloys ({len(db)}):**")
            rows = []
            for alloy in db[:15]:
                props = alloy.get("properties", {})
                rows.append({
                    "Alloy": alloy.get("key", ""),
                    "Category": alloy.get("category", ""),
                    "Yield (MPa)": props.get("yield_MPa", "?"),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        if gen:
            st.markdown(f"**Generated ({result['total_pass']}/{result['total_checked']}):**")
            rows = []
            for i, (comp, r) in enumerate(gen[:15], 1):
                rows.append({"#": i, "Score": round(r["composite_score"], 1),
                            "Composition": fmt_comp(comp, 4)})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        return f"Found {len(db)} known + {len(gen)} generated matches."

    elif mode == "geometry":
        if result.get("engineering_result"):
            eng = result["engineering_result"]
            for name, data in eng.items():
                if isinstance(data, dict) and not name.startswith("_"):
                    with st.expander(name.replace("_", " ").title()):
                        for k, v in data.items():
                            if k not in ("formula", "citation", "composition"):
                                st.markdown(f"**{k}:** {v:.4g}"
                                          if isinstance(v, float) else f"**{k}:** {v}")
                        if data.get("formula"):
                            st.code(data["formula"], language="text")

        return "Geometry analysis complete."

    return "Analysis complete."


with st.sidebar:
    st.header(" AIDE v5.0")
    st.caption("Agentic Alloy Design")

    st.subheader("Operating Conditions")
    T_op = st.slider("Temperature (K)", 77, 4000, 298, step=10)
    thickness = st.number_input("Thickness (mm)", value=25.0, min_value=1.0)

    st.subheader("Environment")
    weather = st.selectbox("Corrosion env",
        ["None", "mumbai_coastal", "chennai_coastal",
         "kolkata_coastal", "delhi_inland", "offshore_arabian"])
    process = st.selectbox("Processing state",
        ["annealed", "cold_worked", "quenched", "aged", "normalised"])

    st.subheader("Constraints")
    dpa_rate = st.select_slider("DPA rate (s⁻¹)",
        options=[1e-8, 5e-8, 1e-7, 5e-7, 1e-6, 5e-6, 1e-5, 5e-5, 1e-4],
        value=1e-7, format_func=lambda x: f"{x:.0e}")
    pressure_MPa = st.slider("Pressure (MPa)", 0, 500, 0, step=10)
    target_yield = st.slider("Target yield (MPa)", 0, 2000, 0, step=50)
    max_density = st.slider("Max density (g/cm³)", 0.0, 30.0, 0.0, step=0.5)
    min_PREN = st.slider("Min PREN", 0, 50, 0, step=1)

    st.subheader("Pipeline")
    n_cand = st.slider("Candidates", 50, 500, 200, step=50)
    top_n = st.slider("Show top N", 3, 20, 10)
    use_ml = st.checkbox("ML predictions", value=False)
    use_bayesian = st.checkbox("Bayesian Optimization", value=False)
    use_pareto = st.checkbox("Pareto Front", value=False)
    use_shap = st.checkbox("SHAP Explanations", value=False)
    use_rag = st.checkbox("RAG Literature", value=False)
    use_web = st.checkbox("Web Scraping", value=False)
    show_detail = st.checkbox("Show detailed checks", value=False)

    st.markdown("---")
    if st.button(" Clear Chat"):
        st.session_state.memory.clear()
        st.session_state.chat_messages = []
        st.rerun()

    st.markdown("---")
    st.caption("Use local Ollama models or set API keys (Gemini, DeepSeek, Groq) in .env for full reasoning")
    from llms.client import is_available
    if is_available():
        st.success(" LLM Connected", icon="✅")
    else:
        st.warning("No local/API LLM available — template mode", icon="✅")


user_constraints = {}
if target_yield > 0:
    user_constraints["min_yield_MPa"] = target_yield
if max_density > 0:
    user_constraints["max_density"] = max_density
if min_PREN > 0:
    user_constraints["min_PREN"] = min_PREN


st.title("AIDE v5 — Alloy Intelligence & Design Engine")
st.caption("42 Physics Domains | Multi-Agent Reasoning | Conversational AI")

tab_chat, tab_editor, tab_compare = st.tabs(
    [" Chat & Design", " Composition Editor", " Multi-Compare"])


with tab_chat:
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("result_key"):
                result = st.session_state.get(msg["result_key"])
                if result:
                    _render_result(result, show_detail, use_ml)

    if prompt := st.chat_input("Ask about alloys... (e.g. 'design a marine stainless steel')"):
        st.session_state.last_user_prompt = prompt
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        st.session_state.memory.add_user_message(prompt)

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            t0 = time.time()

            with st.status("Thinking...", expanded=True) as status:
                st.write("Classifying intent...")
                intent = classify_intent(prompt, memory=st.session_state.memory)
                st.session_state.last_intent = dict(intent)
                mode = intent.get("mode", "design")
                intent["temperature_K"] = intent.get("temperature_K") or T_op
                intent["n_results"] = intent.get("n_results") or n_cand
                intent["dpa_rate"] = dpa_rate
                intent["pressure_MPa"] = pressure_MPa
                if weather != "None":
                    intent["environment"] = weather
                if user_constraints:
                    intent.setdefault("constraints", {}).update(user_constraints)

                st.write(f"Mode: **{mode.upper()}**"
                        + (f" | Alloy: **{intent['alloy_name']}**"
                           if intent.get('alloy_name') else ""))

                thinking_steps = []

                def on_step(step):
                    thinking_steps.append(step)
                    agent_label = f"[{step.agent}] " if hasattr(step, 'agent') and step.agent else ""
                    st.write(f"{agent_label}[{step.stage.upper()}] {step.thought}")

                st.write(f"Running {mode.upper()} engine...")
                intent["use_ml"] = use_ml
                result = route(intent, verbose=False, on_step=on_step)

                elapsed = time.time() - t0
                status.update(label=f"Done in {elapsed:.1f}s", state="complete")

            response_text = _display_result(result, mode, intent, prompt,
                                           show_detail, use_ml, elapsed)

            if use_ml:
                try:
                    pred = {}
                    candidates_detail = result.get("candidates_detail", [])
                    if candidates_detail and candidates_detail[0].get("ml_predictions"):
                        pred = candidates_detail[0]["ml_predictions"]
                    elif result.get("top"):
                        from ml.predict import get_predictor
                        predictor = get_predictor()
                        if predictor.is_available():
                            pred = predictor.predict(result["top"][0][0]) or {}

                    if pred:
                        st.markdown("---")
                        st.subheader("ML Predictions — Top Candidate")
                        cols = st.columns(min(len(pred), 3))
                        for idx, (target, p) in enumerate(pred.items()):
                            if isinstance(p, dict):
                                cols[idx % len(cols)].metric(
                                    target.replace("_", " ").title(),
                                    f"{p['mean']:.2f} {p.get('unit', '')}",
                                    delta=f"±{p.get('sigma', 0):.2f}",
                                )
                except Exception:
                    pass

            st.session_state.memory.add_assistant_message(
                response_text,
                alloy_name=intent.get("alloy_name"),
                composition=intent.get("composition"),
                results=result,
                thinking_steps=thinking_steps,
            )

            result_key = f"result_{len(st.session_state.chat_messages)}"
            st.session_state[result_key] = result
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": response_text,
                "result_key": result_key,
            })


with tab_editor:
    st.subheader("Interactive Composition Editor")
    st.caption("Set element percentages → Select domains → Analyze across 42 domains")

    if "last_preset" not in st.session_state:
        st.session_state.last_preset = "Custom"

    preset = st.selectbox("Load preset alloy",
                          ["Custom"] + list(ALLOY_DATABASE.keys()))

    if preset != st.session_state.last_preset:
        st.session_state.last_preset = preset
        comp = {}
        if preset != "Custom":
            comp = ALLOY_DATABASE.get(preset, {}).get("composition_wt", {})
        for sym in COMMON_ELEMENTS:
            st.session_state[f"elem_{sym}"] = float(round(comp.get(sym, 0.0) * 100, 2))

    st.markdown("---")
    st.markdown("**Composition (wt%)**")

    comp_inputs = {}
    cols_per_row = 5
    rows_needed = (len(COMMON_ELEMENTS) + cols_per_row - 1) // cols_per_row
    for row_i in range(rows_needed):
        cols = st.columns(cols_per_row)
        for col_i, col in enumerate(cols):
            idx = row_i * cols_per_row + col_i
            if idx >= len(COMMON_ELEMENTS):
                break
            sym = COMMON_ELEMENTS[idx]
            with col:
                if f"elem_{sym}" not in st.session_state:
                    st.session_state[f"elem_{sym}"] = 0.0
                val = st.number_input(f"{sym} (%)", 0.0, 100.0,
                                      st.session_state[f"elem_{sym}"], 0.1,
                                      key=f"elem_{sym}")
                if val > 0.001:
                    comp_inputs[sym] = val

    total_pct = sum(comp_inputs.values())
    st.metric("Total", f"{total_pct:.2f}%",
              delta=f"{total_pct - 100:.2f}%" if abs(total_pct - 100) > 0.01 else "OK")

    st.markdown("---")
    st.subheader("Scoring Context")
    default_goal = st.session_state.get("editor_goal_text", "") or st.session_state.get("last_user_prompt", "")
    goal_text = st.text_input("Application / objective", value=default_goal, key="editor_goal_text")
    profile_label = st.selectbox("Weighting profile", options=list(EDITOR_WEIGHT_PROFILES.keys()),
                                 index=0, key="editor_weight_profile_label")
    focused_mode = st.checkbox(
        "Fast subset mode (runs only top-weighted domains)",
        value=False,
        key="editor_fast_subset_mode",
    )
    max_domains = st.slider(
        "Domains to evaluate in fast subset mode",
        16, 42, 30, 1,
        disabled=not focused_mode,
        key="editor_fast_subset_max_domains",
    )
    if focused_mode:
        st.caption(
            "Fast subset mode is quicker but can hide low-weight domains. "
            "Turn it off for close-composition comparisons."
        )

    st.markdown("---")
    st.subheader("Domains")
    all_domains = st.checkbox("Run full 42-domain sweep (recommended)", value=True)
    selected_domains = []
    if not all_domains:
        selected_domains = st.multiselect("Pick domains",
            options=list(DOMAIN_NAMES.values()),
            default=["Thermodynamics", "Mechanical", "Corrosion"])

    st.markdown("---")
    T_editor = st.slider("Temperature (K)", 77, 7000, 298, 10, key="T_editor")
    analyze_btn = st.button("Analyze", type="primary",
                            use_container_width=True, key="analyze_btn")

    if analyze_btn and comp_inputs:
        if abs(total_pct - 100) > 5.0:
            st.error(f"Total is {total_pct:.1f}%. Must be near 100%.")
        else:
            comp_wt = {sym: val / 100.0 for sym, val in comp_inputs.items()}
            try:
                comp_mol = validate_composition(wt_to_mol(comp_wt))
            except Exception:
                try:
                    comp_mol = validate_composition(comp_wt)
                except Exception as e:
                    st.error(f"Validation Error: {e}")
                    st.stop()

            with st.spinner("Analyzing..."):
                context_intent = {}
                if goal_text.strip():
                    try:
                        context_intent = classify_intent(goal_text, memory=st.session_state.memory)
                    except Exception:
                        context_intent = {}

                context_app = context_intent.get("application")
                context_props = context_intent.get("target_properties", [])
                profile_mode = EDITOR_WEIGHT_PROFILES.get(profile_label, "auto")
                domain_limit = max_domains if (all_domains and focused_mode) else None

                if all_domains:
                    result = run_all(comp_mol, T_K=T_editor, verbose=True,
                                     dpa_rate=dpa_rate, process=process,
                                     application=context_app, target_properties=context_props,
                                     weight_profile=profile_mode, max_domains=domain_limit)
                else:
                    result = run_all(comp_mol, T_K=T_editor, verbose=True,
                                     domains_focus=selected_domains,
                                     dpa_rate=dpa_rate, process=process,
                                     application=context_app, target_properties=context_props,
                                     weight_profile=profile_mode)
            
            st.session_state.editor_result = result
            st.session_state.editor_comp_wt = comp_wt
            st.session_state.editor_comp_mol = comp_mol

    if st.session_state.get("editor_result") and comp_inputs:
        result = st.session_state.editor_result
        comp_wt = st.session_state.editor_comp_wt
        comp_mol = st.session_state.editor_comp_mol

        raw_score = result.get("composite_score_raw", result["composite_score"])
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Weighted Score", f"{result['composite_score']:.1f}/100")
        c2.metric("Raw Score", f"{raw_score:.1f}/100")
        c3.metric("Pass", result["n_pass"])
        c4.metric("Warn", result["n_warn"])
        c5.metric("Fail", result["n_fail"])

        profile_used = ", ".join(result.get("weight_profiles_used", []))
        app_ctx = result.get("application_context") or "none"
        if profile_used:
            st.caption(f"Scoring profile: {profile_used} | Application context: {app_ctx}")
        n_domains = int(result.get("n_domains", len(result.get("domain_results", []))))
        if all_domains and n_domains < len(DOMAIN_NAMES):
            st.warning(
                f"Fast subset mode evaluated {n_domains}/{len(DOMAIN_NAMES)} domains. "
                "Disable fast subset mode to include low-weight domains for tie-breaking."
            )

        weights_used = result.get("domain_weights_used", {})
        if weights_used:
            top_weights = sorted(weights_used.items(), key=lambda x: -x[1])[:10]
            rows = [{"Domain": d, "Weight %": round(w * 100, 2)} for d, w in top_weights]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        show_properties(comp_mol)

        hub = get_hub()
        cost = hub.estimate_cost(comp_wt)
        if cost:
            st.metric("Est. Cost", f"${cost:.2f}/kg")

        st.markdown("---")

        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.plotly_chart(make_radar_chart(result["domain_results"]),
                           use_container_width=True)
        with chart_col2:
            st.plotly_chart(make_score_bar_chart(result["domain_results"]),
                           use_container_width=True)

        st.dataframe(domain_table(result["domain_results"]),
                    use_container_width=True, hide_index=True)

        if show_detail:
            for dr in result["domain_results"]:
                with st.expander(f"[{dr.domain_id}] {dr.domain_name} — {dr.score():.1f}/100"):
                    show_domain_checks(dr.checks)
                    
                    btn_key = f"explain_{dr.domain_id}"
                    if st.button(f" AI Explain {dr.domain_name}", key=btn_key):
                        with st.spinner(f"Analyzing {dr.domain_name}..."):
                            from llms.explainer import explain_single_domain
                            checks_str = []
                            for ch in dr.checks:
                                status = getattr(ch, "status", "")
                                name = getattr(ch, "name", "")
                                val = getattr(ch, "value", None)
                                unit = getattr(ch, "unit", "")
                                msg = getattr(ch, "message", "")
                                val_str = f" = {val:.4g} {unit}" if val is not None else ""
                                checks_str.append(f"[{status}] {name}{val_str} -> {msg}")
                            
                            explanation = explain_single_domain(
                                dr.domain_name, dr.score(), "\n".join(checks_str), fmt_comp(comp_wt)
                            )
                            st.markdown("---")
                            st.markdown(f"** {dr.domain_name} Analysis:**")
                            st.markdown(explanation)

        try:
            from llms.explainer import explain_results
            explanation = explain_results(comp_mol, result["domain_results"])
            if explanation:
                st.markdown("---")
                st.markdown("** AI Analysis:**")
                st.markdown(explanation)
        except Exception:
            pass

        txt_lines = [
            "AIDE v5.0 Composition Analysis",
            f"Composition (wt%): {comp_wt}",
            f"Temperature: {T_editor} K",
            f"Processing: {process}",
            f"Score: {result['composite_score']:.1f}/100",
            f"Pass: {result['n_pass']}  Warn: {result['n_warn']}  Fail: {result['n_fail']}",
            "",
        ]
        for dr in result["domain_results"]:
            txt_lines.append(f"\n[{dr.domain_id}] {dr.domain_name} -- {dr.score():.1f}/100")
            for ch in dr.checks:
                val_str = f" = {ch.value:.4g} {ch.unit}" if ch.value is not None else ""
                txt_lines.append(f"  [{ch.status}] {ch.name}{val_str}")
                txt_lines.append(f"    {ch.message}")
                if ch.formula:
                    txt_lines.append(f"    Formula: {ch.formula}")
                if ch.citation:
                    txt_lines.append(f"    Ref: {ch.citation}")

        st.download_button(" Download Report (TXT)", "\n".join(txt_lines),
                           file_name="AIDE_composition_report.txt",
                           mime="text/plain", key="editor_dl")

    elif analyze_btn:
        st.warning("Set at least one element.")


with tab_compare:
    st.subheader(" Multi-Alloy Comparison")
    st.caption("Select 2–5 alloys from the database and compare across all domains")

    alloy_options = list(ALLOY_DATABASE.keys())
    selected_alloys = st.multiselect(
        "Select alloys to compare",
        options=alloy_options,
        default=alloy_options[:2] if len(alloy_options) >= 2 else alloy_options,
        max_selections=5,
    )

    T_compare = st.slider("Temperature (K)", 77, 7000, 298, 10, key="T_compare")

    if st.button("Compare All", type="primary", use_container_width=True, key="compare_btn"):
        if len(selected_alloys) < 2:
            st.warning("Select at least 2 alloys to compare.")
        else:
            alloy_data = []
            score_rows = []

            with st.spinner(f"Analyzing {len(selected_alloys)} alloys..."):
                for alloy_name in selected_alloys:
                    alloy = ALLOY_DATABASE.get(alloy_name, {})
                    comp_wt = alloy.get("composition_wt", {})
                    if not comp_wt:
                        continue
                    try:
                        comp_mol = validate_composition(wt_to_mol(comp_wt))
                    except Exception:
                        try:
                            comp_mol = validate_composition(comp_wt)
                        except Exception:
                            continue

                    result = run_all(comp_mol, T_K=T_compare, verbose=False)
                    alloy_data.append((alloy_name, result["domain_results"]))

                    row = {"Alloy": alloy_name,
                           "Score": round(result["composite_score"], 1),
                           "Pass": result["n_pass"],
                           "Warn": result["n_warn"],
                           "Fail": result["n_fail"]}
                    for dr in result["domain_results"]:
                        row[dr.domain_name[:15]] = round(dr.score(), 1)
                    score_rows.append(row)

            if alloy_data:
                st.subheader("Summary")
                df = pd.DataFrame(score_rows)
                st.dataframe(df[["Alloy", "Score", "Pass", "Warn", "Fail"]],
                            use_container_width=True, hide_index=True)

                best = max(score_rows, key=lambda r: r["Score"])
                st.markdown(f"** Best overall: {best['Alloy']} ({best['Score']}/100)**")

                st.plotly_chart(make_multi_radar(alloy_data),
                               use_container_width=True)

                if len(alloy_data) == 2:
                    st.plotly_chart(make_comparison_bar(
                        alloy_data[0][1], alloy_data[1][1],
                        alloy_data[0][0], alloy_data[1][0]),
                        use_container_width=True)

                with st.expander(" Full Domain Scores"):
                    st.dataframe(pd.DataFrame(score_rows),
                                use_container_width=True, hide_index=True)

                hub = get_hub()
                cost_rows = []
                for alloy_name in selected_alloys:
                    alloy = ALLOY_DATABASE.get(alloy_name, {})
                    comp_wt = alloy.get("composition_wt", {})
                    cost = hub.estimate_cost(comp_wt)
                    cost_rows.append({"Alloy": alloy_name,
                                      "Cost ($/kg)": f"${cost:.2f}" if cost else "N/A"})
                st.dataframe(pd.DataFrame(cost_rows),
                            use_container_width=True, hide_index=True)


st.markdown("---")
st.caption("AIDE v5.0 | 42 Physics Domains | Multi-Agent Reasoning | Conversational AI")
