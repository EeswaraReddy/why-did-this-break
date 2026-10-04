import streamlit as st
from run_engine import run_investigation

st.set_page_config(page_title="Why Did This Break?", page_icon="🛡️", layout="wide")
st.title("🛡️ Why Did This Break?")
st.caption("AI SRE Investigation Console — trajectory, evaluation, observability and decision safety")

with st.sidebar:
    st.header("Investigation")
    mode = st.radio("Mode", ["LLM Only", "LLM + Decider 2B"])
    st.divider()
    st.caption("Incident")
    st.code("INC-001\nProduction S3 Access Denied")
    run = st.button("▶ Run Investigation", type="primary", use_container_width=True)

if "runs" not in st.session_state:
    st.session_state.runs = {}

if run:
    with st.spinner(f"Running {mode}..."):
        try:
            data = run_investigation(use_decider=(mode == "LLM + Decider 2B"))
            st.session_state.runs[mode] = data
            st.session_state.latest = mode
        except Exception as exc:
            st.error(f"Run failed: {exc}")
            st.exception(exc)

latest = st.session_state.get("latest")
if not latest:
    st.info("Choose a mode and click Run Investigation to start.")
    st.markdown("""
### What this console shows

**Trajectory** — what the agent actually did.

**Evaluation** — whether the investigation reached the expected root cause.

**Observability** — model/tool calls, tokens and latency when available.

**Decision gate** — the Decider 2B result before the simulated remediation.

Run the same incident in both modes and compare the runs.
""")
    st.stop()

data = st.session_state.runs[latest]
evaluation = data.get("evaluation", {})
obs = data.get("observability", {})
decision = data.get("decision")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Root Cause", "PASS" if evaluation.get("root_cause_correct") else "FAIL")
c2.metric("Evaluation", f"{evaluation.get('score', 0)}/100")
c3.metric("Tool Calls", evaluation.get("tool_call_count", 0))
c4.metric("Elapsed", f"{evaluation.get('elapsed_seconds', 0):.2f}s")

st.divider()
left, right = st.columns([1.5, 1])

with left:
    st.subheader("Investigation Trajectory")
    for event in data.get("trajectory", []):
        kind = event.get("type")
        if kind == "tool":
            with st.container(border=True):
                a, b = st.columns([4, 1])
                a.markdown(f"**🔧 {event.get('name')}**")
                if event.get("latency_ms") is not None:
                    b.caption(f"{event['latency_ms']:.0f} ms")
                if event.get("result"):
                    with st.expander("Evidence returned"):
                        st.code(event["result"], language="text")
        elif kind == "decision":
            with st.container(border=True):
                st.markdown("**🧠 Decision Model — Decider 2B**")
                st.write(event.get("question", ""))
                a, b, c = st.columns(3)
                a.metric("Confidence", f"{event.get('probability', 0):.2%}")
                b.metric("Threshold", f"{event.get('threshold', .70):.0%}")
                c.metric("Decision", event.get("decision", "UNKNOWN"))

with right:
    st.subheader("Evaluation")
    for name, passed in evaluation.get("criteria", {}).items():
        st.write(("✅" if passed else "❌") + f"  {name.replace('_', ' ').title()}")

    st.subheader("Observability")
    for key, value in obs.items():
        if key != "strands_metrics":
            st.write(f"**{key.replace('_', ' ').title()}**: {value}")

    if decision:
        st.subheader("Decision Gate")
        if decision.get("decision") == "PROCEED":
            st.success(f"PROCEED — {decision.get('probability', 0):.2%} confidence")
        else:
            st.error(f"DENY — {decision.get('probability', 0):.2%} confidence")
        st.caption(f"Decision latency: {decision.get('latency_ms', 0):.2f} ms")

st.divider()
st.subheader("Root Cause")
st.success(data.get("root_cause", "Root cause not captured."))

with st.expander("Agent Final Answer"):
    st.markdown(data.get("final_answer", ""))

if len(st.session_state.runs) >= 2:
    st.divider()
    st.subheader("⚖️ LLM Only vs LLM + Decider 2B")
    a = st.session_state.runs.get("LLM Only", {})
    b = st.session_state.runs.get("LLM + Decider 2B", {})
    ae = a.get("evaluation", {})
    be = b.get("evaluation", {})
    bd = b.get("decision") or {}
    st.table({
        "Metric": ["Root cause", "Evaluation score", "Tool calls", "Elapsed (s)", "Decision confidence", "Decision latency (s)"],
        "LLM Only": [ae.get("root_cause_correct"), ae.get("score"), ae.get("tool_call_count"), ae.get("elapsed_seconds"), "—", "—"],
        "LLM + Decider 2B": [be.get("root_cause_correct"), be.get("score"), be.get("tool_call_count"), be.get("elapsed_seconds"), f"{bd.get('probability', 0):.2%}", round(bd.get("latency_ms", 0) / 1000, 2)],
    })

st.caption("POC only — remediation is simulated and does not modify AWS infrastructure.")
