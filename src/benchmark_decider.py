import time

from decider import ask_decider


state = """
Production S3 incident.
Application logs show AccessDenied on PutObject.
Recent Terraform IAM change detected.
"""

question = """
Is investigating the infrastructure IAM state
an appropriate next troubleshooting action?
"""


latencies = []

for i in range(5):
    start = time.perf_counter()

    result = ask_decider(
        state=state,
        question=question,
    )

    elapsed = time.perf_counter() - start
    latencies.append(elapsed)

    print(
        f"Run {i + 1}: "
        f"{elapsed:.2f}s | "
        f"model reported {result['latency_ms']:.2f}ms | "
        f"probability={result['probability']:.4f}"
    )


latencies.sort()

print("\n" + "=" * 60)
print("DECIDER BENCHMARK")
print("=" * 60)

print(f"Min : {min(latencies):.2f}s")
print(f"Max : {max(latencies):.2f}s")
print(f"Avg : {sum(latencies) / len(latencies):.2f}s")
print(f"P50 : {latencies[len(latencies) // 2]:.2f}s")