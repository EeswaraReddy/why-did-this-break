import json
import os
import time
from pathlib import Path

from strands import Agent, tool
from strands.models import LiteLLMModel
from src.evaluation import evaluate_investigation
from strands import Agent, tool
from strands.models import LiteLLMModel

from src.evaluation import evaluate_investigation
from src.tools import (
    load_incident,
    get_logs,
    get_metrics,
    get_recent_changes,
    get_infrastructure_state,
    get_runbook,
    remediate_iam_permission,
)
from src.decider import ask_decider

from dotenv import load_dotenv

load_dotenv()

INCIDENT_PATH = Path("data/incidents/s3_access_denied.json")


def _load_incident():
    with INCIDENT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _llm():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    model_name = os.getenv("GROQ_MODEL_ID", "llama-3.1-8b-instant").strip()
    return LiteLLMModel(model_id=f"groq/{model_name}", client_args={"api_key": api_key})


def run_investigation(use_decider=False):
    incident = _load_incident()
    trajectory = []
    decision = None

    def record(name, result, started):
        trajectory.append({"type": "tool", "name": name, "latency_ms": (time.perf_counter() - started) * 1000, "result": result})

    @tool
    def investigate_logs() -> str:
        from src.tools import get_logs
        started = time.perf_counter(); result = get_logs(); record("investigate_logs", result, started); return result

    @tool
    def investigate_metrics() -> str:
        from src.tools import get_metrics
        started = time.perf_counter(); result = get_metrics(); record("investigate_metrics", result, started); return result

    @tool
    def investigate_recent_changes() -> str:
        from src.tools import get_recent_changes
        started = time.perf_counter(); result = get_recent_changes(); record("investigate_recent_changes", result, started); return result

    @tool
    def investigate_infrastructure() -> str:
        from src.tools import get_infrastructure_state
        started = time.perf_counter(); result = get_infrastructure_state(); record("investigate_infrastructure", result, started); return result

    @tool
    def investigate_runbook() -> str:
        from src.tools import get_runbook
        started = time.perf_counter(); result = get_runbook(); record("investigate_runbook", result, started); return result

    @tool
    def remediate_iam_permission_tool() -> str:
        nonlocal decision
        if use_decider:
            from src.decider_gate import ask_decider
            state = """
Production S3 incident.
Evidence:
- Application receives AccessDenied for PutObject.
- Recent Terraform IAM change detected.
- Infrastructure shows s3:PutObject is missing.
- Root cause is an IAM permission regression.
Proposed remediation:
Restore s3:PutObject permission to order-service-prod.
"""
            question = "Given the evidence and proposed remediation, is it appropriate and sufficiently justified to proceed with this remediation action?"
            result = ask_decider(state, question)
            probability = result["answers"]["decision"]["noul"]
            threshold = 0.70
            decision = {"probability": probability, "threshold": threshold, "latency_ms": result["latency_ms"], "decision": "PROCEED" if probability >= threshold else "DENY"}
            trajectory.append({"type": "decision", "name": "Decider 2B", "question": question, **decision})
            if probability < threshold:
                return "Remediation DENIED by Decider 2B."
        return "SIMULATION ONLY: IAM remediation would restore s3:PutObject permission to order-service-prod."

    prompt = f"""
Investigate this infrastructure incident.
Incident ID: {incident['incident_id']}
Title: {incident['title']}
Service: {incident['service']}
Environment: {incident['environment']}
Timestamp: {incident['timestamp']}
Initial symptoms:
{json.dumps(incident['symptoms'], indent=2)}

Investigate step by step. Use only evidence tools that are useful. Determine the likely root cause and supporting evidence. After establishing the root cause, call remediate_iam_permission_tool to simulate remediation. Do not invent evidence.
Return: INCIDENT SUMMARY, SYMPTOMS, HYPOTHESES, EVIDENCE, ROOT CAUSE, RECOMMENDED ACTION, VERIFICATION.
"""

    system_prompt = "You are a senior Site Reliability and Platform Engineering investigator. Evidence before assumptions. Do not invent evidence. Do not automatically inspect every source. Use tools selectively. Confirm the root cause with evidence. The remediation tool is simulation-only."

    start = time.perf_counter()
    agent = Agent(model=_llm(), system_prompt=system_prompt, tools=[investigate_logs, investigate_metrics, investigate_recent_changes, investigate_infrastructure, investigate_runbook, remediate_iam_permission_tool])
    result = agent(prompt)
    elapsed = time.perf_counter() - start

    evaluation = evaluate_investigation(result=str(result), expected_root_cause=incident["expected_root_cause"], tool_calls=[x["name"] for x in trajectory if x["type"] == "tool"], elapsed_seconds=elapsed)
    criteria = evaluation.get("criteria", {})
    evaluation["score"] = round(100 * sum(bool(v) for v in criteria.values()) / max(len(criteria), 1))

    observability = {"elapsed_seconds": round(elapsed, 2), "tool_calls": evaluation.get("tool_call_count", 0), "model": os.getenv("GROQ_MODEL_ID", "unknown")}
    try:
        observability["strands_metrics"] = str(result.metrics.get_summary())
    except Exception:
        pass

    return {"incident": incident, "trajectory": trajectory, "evaluation": evaluation, "observability": observability, "decision": decision, "root_cause": incident["expected_root_cause"], "final_answer": str(result)}
