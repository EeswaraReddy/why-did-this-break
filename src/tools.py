import json
import logging
from pathlib import Path


INCIDENT_FILE = Path("data/incidents/s3_access_denied.json")

logger = logging.getLogger("incident-agent")


def load_incident():
    with open(INCIDENT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _trace_tool(name: str, result) -> str:
    print("\n" + "-" * 60)
    print(f"[TOOL] {name}")
    print("-" * 60)

    output = json.dumps(result, indent=2)

    print(output)

    print("-" * 60)

    return output


def get_logs() -> str:
    """Retrieve application logs for the current incident."""
    incident = load_incident()
    return _trace_tool("investigate_logs", incident["logs"])


def get_metrics() -> str:
    """Retrieve monitoring metrics for the current incident."""
    incident = load_incident()
    return _trace_tool("investigate_metrics", incident["metrics"])


def get_recent_changes() -> str:
    """Retrieve recent code, deployment and infrastructure changes."""
    incident = load_incident()
    return _trace_tool(
        "investigate_recent_changes",
        incident["recent_changes"],
    )


def get_infrastructure_state() -> str:
    """Retrieve infrastructure and IAM state."""
    incident = load_incident()
    return _trace_tool(
        "investigate_infrastructure",
        incident["infrastructure"],
    )


def get_runbook() -> str:
    """Retrieve the operational runbook."""
    incident = load_incident()
    return _trace_tool(
        "investigate_runbook",
        incident["runbook"],
    )
def remediate_iam_permission() -> str:
    """
    Simulate restoring the missing S3 PutObject permission.
    This does NOT modify AWS.
    """
    return (
        "SIMULATION ONLY: IAM remediation would restore "
        "s3:PutObject permission to order-service-prod."
    )