from __future__ import annotations

from .common import FlowAbort, FlowRunner, build_summary, load_state


def run_student(state: dict) -> FlowRunner:
    runner = FlowRunner("student", state)
    try:
        token = state["student_access_token"]
        class_id = state["course_class_id"]
        runner.request(
            "GET",
            "/student/my-classes",
            route_key="GET /student/my-classes",
            expected_status=200,
            token=token,
            params={"skip": 0, "limit": 10},
        )
        runner.request(
            "GET",
            f"/student/my-classes/{class_id}",
            route_key="GET /student/my-classes/{course_class_id}",
            expected_status=200,
            token=token,
        )
        return runner
    except Exception as exc:
        if not isinstance(exc, FlowAbort):
            runner.record_internal_failure(str(exc))
        raise
    finally:
        runner.save()
        runner.close()


if __name__ == "__main__":
    state = load_state(required=True)
    try:
        run_student(state)
    finally:
        _, summary = build_summary(state)
        print(f"Relatório consolidado: {summary}")
