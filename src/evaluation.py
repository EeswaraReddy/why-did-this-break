def evaluate_root_cause(actual: str, expected: str) -> dict:

    actual = actual.lower()

    checks = {
        "iam": "iam" in actual,
        "s3_putobject": "s3:putobject" in actual,
        "access_denied": "accessdenied" in actual,
        "terraform": "terraform" in actual,
    }

    return {
        "root_cause_correct": all(checks.values()),
        "criteria": checks,
        "expected_root_cause": expected,
    }


def evaluate_investigation(
    result: str,
    expected_root_cause: str,
    tool_calls: list[str],
    elapsed_seconds: float,
) -> dict:

    root_cause = evaluate_root_cause(
        result,
        expected_root_cause,
    )

    return {
        **root_cause,
        "tool_call_count": len(tool_calls),
        "tool_calls": tool_calls,
        "elapsed_seconds": round(elapsed_seconds, 2),
    }


def print_evaluation(evaluation: dict):

    print("\n" + "=" * 70)
    print("EVALUATION")
    print("=" * 70)

    print(
        f"Root cause correct : "
        f"{evaluation['root_cause_correct']}"
    )

    print("\nCriteria:")

    for name, result in evaluation["criteria"].items():
        print(
            f"  {name:<20} "
            f"{'PASS' if result else 'FAIL'}"
        )

    print(
        f"\nTool calls         : "
        f"{evaluation['tool_call_count']}"
    )

    print(
        f"Execution time     : "
        f"{evaluation['elapsed_seconds']} sec"
    )

    print("\nTool trajectory:")

    for i, tool_name in enumerate(
        evaluation["tool_calls"],
        start=1,
    ):
        print(f"  {i}. {tool_name}")

    print("=" * 70)