from __future__ import annotations

from .activities_flow import run_activities
from .common import FlowRunner, build_summary, load_state
from .health_flow import run_health
from .monitor_flow import run_monitor
from .student_flow import run_student
from .teacher_flow import run_teacher_cleanup, run_teacher_setup


def main() -> None:
    state = load_state(required=True)
    teacher_runner = FlowRunner("teacher", state)
    error: Exception | None = None
    try:
        run_health(state)
        run_teacher_setup(state, teacher_runner)
        run_student(state)
        run_monitor(state)
        run_activities(state)
        run_teacher_cleanup(state, teacher_runner)
    except Exception as exc:
        error = exc
        print(f"\nExecução interrompida: {exc}")
    finally:
        teacher_runner.save()
        teacher_runner.close()
        _, summary = build_summary(state)
        print(f"\nRelatório consolidado: {summary}")
    if error:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
