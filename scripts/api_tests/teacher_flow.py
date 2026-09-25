from __future__ import annotations

import argparse

from . import config
from .common import FlowAbort, FlowRunner, build_summary, load_state, require_json_key, save_state


def run_teacher_setup(state: dict, runner: FlowRunner | None = None) -> FlowRunner:
    own_runner = runner is None
    runner = runner or FlowRunner("teacher", state)
    try:
        token = state["professor_access_token"]
        response = runner.request(
            "POST",
            "/teacher/register-class",
            route_key="POST /teacher/register-class",
            expected_status=200,
            token=token,
            json_body={"name": config.CLASS_NAME, "discipline": config.CLASS_DISCIPLINE},
        )
        state["course_class_id"] = require_json_key(response, "id", "Criação da turma")

        runner.request(
            "GET",
            "/teacher/my-classes",
            route_key="GET /teacher/my-classes",
            expected_status=200,
            token=token,
            params={"name": config.CLASS_NAME, "skip": 0, "limit": 10},
        )
        class_id = state["course_class_id"]
        runner.request(
            "GET",
            f"/teacher/my-classes/{class_id}",
            route_key="GET /teacher/my-classes/{course_class_id}",
            expected_status=200,
            token=token,
        )
        runner.request(
            "PUT",
            f"/teacher/my-classes/{class_id}/add-student",
            route_key="PUT /teacher/my-classes/{course_class_id}/add-student",
            expected_status=200,
            token=token,
            json_body={"email": config.STUDENT_EMAIL},
        )
        runner.request(
            "PUT",
            f"/teacher/my-classes/{class_id}/add-monitor",
            route_key="PUT /teacher/my-classes/{course_class_id}/add-monitor",
            expected_status=200,
            token=token,
            json_body={"email": config.STUDENT_EMAIL},
        )
        activity = runner.request(
            "POST",
            f"/teacher/my-classes/{class_id}/add-activity",
            route_key="POST /teacher/my-classes/{course_class_id}/add-activity",
            expected_status=200,
            token=token,
            json_body={
                "title": config.TEACHER_ACTIVITY_TITLE,
                "description": "Atividade criada para validar a rota específica do professor.",
                "fileUrl": config.TEST_FILE_URL,
            },
        )
        state["teacher_activity_id"] = require_json_key(
            activity, "id", "Atividade criada pelo professor"
        )
        save_state(state)
        return runner
    except Exception as exc:
        if not isinstance(exc, FlowAbort):
            runner.record_internal_failure(str(exc))
        raise
    finally:
        if own_runner:
            runner.save()
            runner.close()


def run_teacher_cleanup(state: dict, runner: FlowRunner | None = None) -> FlowRunner:
    own_runner = runner is None
    runner = runner or FlowRunner("teacher", state, append_existing=True)
    try:
        token = state["professor_access_token"]
        class_id = state["course_class_id"]
        student_id = state["student_id"]
        runner.request(
            "PATCH",
            f"/teacher/my-classes/{class_id}/remove-monitor",
            route_key="PATCH /teacher/my-classes/{course_class_id}/remove-monitor",
            expected_status=200,
            token=token,
            json_body={"student_id": student_id},
        )
        runner.request(
            "PATCH",
            f"/teacher/my-classes/{class_id}/remove-student",
            route_key="PATCH /teacher/my-classes/{course_class_id}/remove-student",
            expected_status=200,
            token=token,
            json_body={"student_id": student_id},
        )
        runner.add_note(
            "O cleanup remove o aluno e o monitor da turma somente depois dos fluxos student/monitor/activities."
        )
        save_state(state)
        return runner
    except Exception as exc:
        if not isinstance(exc, FlowAbort):
            runner.record_internal_failure(str(exc))
        raise
    finally:
        if own_runner:
            runner.save()
            runner.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["setup", "cleanup", "all"], default="all")
    args = parser.parse_args()
    state = load_state(required=True)
    runner = FlowRunner("teacher", state, append_existing=args.phase == "cleanup")
    try:
        if args.phase in {"setup", "all"}:
            run_teacher_setup(state, runner)
        if args.phase in {"cleanup", "all"}:
            run_teacher_cleanup(state, runner)
    finally:
        runner.save()
        runner.close()
        _, summary = build_summary(state)
        print(f"Relatório consolidado: {summary}")
