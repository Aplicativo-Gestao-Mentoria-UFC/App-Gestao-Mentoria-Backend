from __future__ import annotations

from .common import FlowRunner, build_summary, create_state, load_state


def run_health(state: dict) -> FlowRunner:
    runner = FlowRunner("health", state)
    try:
        runner.request(
            "GET",
            "/health",
            route_key="GET /health",
            expected_status=200,
        )
        runner.request(
            "GET",
            "/health/db",
            route_key="GET /health/db",
            expected_status=200,
        )
    except Exception as exc:
        if not runner.steps or runner.steps[-1].get("passed", True):
            runner.record_internal_failure(str(exc))
        raise
    finally:
        runner.save()
        runner.close()
    return runner


if __name__ == "__main__":
    state = load_state(required=False)
    try:
        run_health(state)
    finally:
        _, summary = build_summary(state)
        print(f"Relatório consolidado: {summary}")
