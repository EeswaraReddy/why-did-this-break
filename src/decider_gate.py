import json
import urllib.request

from strands import InterventionHandler
from strands.interventions import Proceed, Deny


DECIDER_URL = "http://localhost:8099/v1/systemone"

DECISION_THRESHOLD = 0.70


class RemediationDecisionGate(InterventionHandler):

    name = "remediation-decision-gate"

    def before_tool_call(self, event):

        tool_name = event.tool_use["name"]

        # Only protect the consequential remediation tool.
        # All investigation tools proceed normally.
        if tool_name != "remediate_iam_permission_tool":
            return Proceed()

        print("\n" + "=" * 60)
        print("[DECIDER] Evaluating remediation")
        print("=" * 60)

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

        question = """
Given the evidence and proposed remediation,
is it appropriate and sufficiently justified
to proceed with this remediation action?
"""

        payload = {
            "state": state,
            "questions": {
                "decision": {
                    "type": "noul",
                    "instructions": question,
                }
            },
        }

        request = urllib.request.Request(
            DECIDER_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json"
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=120,
            ) as response:

                result = json.loads(
                    response.read().decode("utf-8")
                )

        except Exception as exc:

            print(f"[DECIDER] ERROR: {exc}")

            # Fail closed for consequential actions.
            return Deny(
                reason=(
                    "Decision model unavailable. "
                    "Remediation denied."
                )
            )

        probability = (
            result["answers"]
            ["decision"]
            ["noul"]
        )

        latency_ms = result["latency_ms"]

        print(
            f"[DECIDER] probability = "
            f"{probability:.4f}"
        )

        print(
            f"[DECIDER] latency = "
            f"{latency_ms:.2f} ms"
        )

        print(
            f"[DECIDER] threshold = "
            f"{DECISION_THRESHOLD:.2f}"
        )

        if probability >= DECISION_THRESHOLD:

            print("[DECIDER] >>> PROCEED")

            return Proceed()

        print("[DECIDER] >>> DENY")

        return Deny(
            reason=(
                f"Decision confidence "
                f"{probability:.4f} is below "
                f"threshold "
                f"{DECISION_THRESHOLD:.2f}"
            )
        )