import json
import os

from strands import Agent, tool
from strands.models import LiteLLMModel
import time
from src.evaluation import evaluate_investigation, print_evaluation


from strands.telemetry import StrandsTelemetry
StrandsTelemetry().setup_console_exporter()
from src.decider_gate import RemediationDecisionGate
from strands import InterventionHandler
from strands.interventions import Proceed, Deny




global tool_trajectory
tool_trajectory = []
#tool_trajectory = []
def record_tool_call(name: str):
    tool_trajectory.append(name)
    print(f"\n[TOOL CALL] {name}")

from src.tools import (
    get_logs,
    get_metrics,
    get_recent_changes,
    get_infrastructure_state,
    get_runbook,
    remediate_iam_permission,
)
@tool
def remediate_iam_permission_tool() -> str:
    """
    Simulate restoring the missing S3 PutObject permission.
    This does not modify real AWS infrastructure.
    """
    record_tool_call("remediate_iam_permission_tool")
    return remediate_iam_permission()

@tool
def investigate_logs() -> str:
    """Retrieve application logs related to the incident."""
    record_tool_call("investigate_logs")
    return get_logs()


@tool
def investigate_metrics() -> str:
    """Retrieve monitoring metrics related to the incident."""
    record_tool_call("investigate_metrics")
    return get_metrics()


@tool
def investigate_recent_changes() -> str:
    """Retrieve recent application, deployment and infrastructure changes."""
    record_tool_call("investigate_recent_changes")
    return get_recent_changes()


@tool
def investigate_infrastructure() -> str:
    """Retrieve infrastructure and IAM state."""
    record_tool_call("investigate_infrastructure")
    return get_infrastructure_state()


@tool
def investigate_runbook() -> str:
    """Retrieve the relevant operational runbook."""
    record_tool_call("investigate_runbook")
    return get_runbook()

def require_llm_configuration() -> tuple[str, str]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured. Set it before running this script, for example: "
            "$env:GROQ_API_KEY='your-key'"
        )

    model_id = os.getenv("GROQ_MODEL_ID", "llama-3.1-8b-instant").strip()
    if not model_id:
        raise RuntimeError(
            "GROQ_MODEL_ID is empty. Set it to a model available in your Groq account, for example: "
            "llama-3.1-8b-instant or llama-3.3-70b-versatile."
        )

    return api_key, model_id


def build_agent() -> Agent:
    api_key, model_name = require_llm_configuration()

    return Agent(
    model=LiteLLMModel(
        model_id=f"groq/{model_name}",
        client_args={"api_key": api_key},
    ),

    system_prompt=(
        """
You are a senior Site Reliability and Platform Engineering investigator.

Your goal is to determine WHY an infrastructure incident happened.

IMPORTANT RULES:

1. Evidence before assumptions.
2. Do not invent evidence.
3. Do not automatically inspect every evidence source.
4. Decide which evidence is useful.
5. Investigate step by step.
6. Generate hypotheses.
7. Look for evidence that confirms or disproves hypotheses.
8. Do not declare root cause without supporting evidence.
9. Recommend remediation only after sufficient evidence.
10. Explain how remediation should be verified.

Available investigation tools:

- investigate_logs
- investigate_metrics
- investigate_recent_changes
- investigate_infrastructure
- investigate_runbook
- remediate_iam_permission_tool

After determining the root cause, if the evidence supports
the IAM permission regression, call
remediate_iam_permission_tool.

IMPORTANT:
The remediation tool is simulation-only.
It does not modify real AWS infrastructure.

Your final response must contain:

INCIDENT SUMMARY

SYMPTOMS

HYPOTHESES

EVIDENCE

ROOT CAUSE

RECOMMENDED ACTION

VERIFICATION
"""
    ),

    tools=[
        investigate_logs,
        investigate_metrics,
        investigate_recent_changes,
        investigate_infrastructure,
        investigate_runbook,
        remediate_iam_permission_tool,
    ],

    interventions=[
        RemediationDecisionGate(),
    ],
)

def load_incident(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_prompt(incident: dict) -> str:
    return f"""
Investigate this infrastructure incident.

Incident ID:
{incident["incident_id"]}

Title:
{incident["title"]}

Service:
{incident["service"]}

Environment:
{incident["environment"]}

Timestamp:
{incident["timestamp"]}

Initial symptoms:

{json.dumps(incident["symptoms"], indent=2)}

IMPORTANT:

The incident contains additional evidence sources.

Do NOT assume you have seen all the evidence.

Use the investigation tools to retrieve evidence when necessary.

Investigate step by step.

Determine:

1. What is happening?
2. What could explain it?
3. Which evidence should be investigated next?
4. What evidence confirms or rejects each hypothesis?
5. What is the most likely root cause?
6. What action should be taken?
7. How should the fix be verified?

Begin the investigation.
"""


def investigate(incident_path: str):
    global tool_trajectory
    tool_trajectory = []

    print("\n" + "=" * 70)
    print("INCIDENT INVESTIGATION START")
    print("=" * 70)

    start_time = time.perf_counter()

    incident = load_incident(incident_path)
    tool_calls = []

    print(f"\n[INCIDENT] {incident['incident_id']}")
    print(f"[SERVICE]  {incident['service']}")
    print(f"[TITLE]    {incident['title']}")

    print("\n[AGENT] Building investigation agent...")

    agent = build_agent()

    print("[AGENT] Agent ready.")
    print("[AGENT] Starting reasoning loop...\n")

    prompt = build_prompt(incident)

    try:
        result = agent(prompt)
         
        elapsed = time.perf_counter() - start_time

        evaluation = evaluate_investigation(
            result=str(result),
            expected_root_cause=incident["expected_root_cause"],
            tool_calls=tool_trajectory,
            elapsed_seconds=elapsed,
        )

        print("\n" + "=" * 70)
        print("STRANDS OBSERVABILITY")
        print("=" * 70)

        try:
            print(result.metrics.get_summary())
        except Exception as exc:
            print(f"Unable to read Strands metrics: {exc}")

        if hasattr(result, "traces"):
            print("\nSTRANDS TRACES")
            for trace in result.traces:
                print(trace)
        else:
            print("\nDetailed result.traces is not available in this Strands version.")
        

    except Exception as exc:
        message = str(exc)

        if (
            "model_not_found" in message
            or "does not exist or you do not have access" in message
        ):
            raise RuntimeError(
                "The Groq model is not available for this account."
            ) from exc

        raise

    elapsed = time.perf_counter() - start_time

    print("\n" + "=" * 70)
    print("INVESTIGATION COMPLETE")
    print("=" * 70)

    print(f"[TIME] {elapsed:.2f} seconds")

    return result


if __name__ == "__main__":
    result = investigate(
        "data/incidents/s3_access_denied.json"
    )

    print(result)