import json
import urllib.request


DECIDER_URL = "http://localhost:8099/v1/systemone"


def ask_decider(
    state: str,
    question: str,
) -> dict:

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
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))

    answer = result["answers"]["decision"]

    return {
        "probability": answer["noul"],
        "latency_ms": result["latency_ms"],
        "input_tokens": result["usage"]["input_tokens"],
        "output_tokens": result["usage"]["output_tokens"],
    }
if __name__ == "__main__":

    result = ask_decider(
        state="""
        Production S3 incident.
        Application logs show AccessDenied on PutObject.
        Recent Terraform IAM change detected.
        """,
        question="""
        Is investigating the infrastructure/IAM state
        an appropriate next troubleshooting action?
        """,
    )

    print(result)