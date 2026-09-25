from __future__ import annotations

from . import config
from .common import FlowAbort, FlowRunner, build_summary, load_state, require_json_key, save_state


def run_activities(state: dict) -> FlowRunner:
    runner = FlowRunner("activities", state)
    try:
        monitor_token = state["student_access_token"]
        class_id = state["course_class_id"]

        created = runner.request(
            "POST",
            f"/activities/class/{class_id}",
            route_key="POST /activities/class/{course_class_id}",
            expected_status=200,
            token=monitor_token,
            json_body={
                "title": config.MONITOR_ACTIVITY_TITLE,
                "description": "Atividade criada pelo aluno que está vinculado como monitor.",
                "fileUrl": config.TEST_FILE_URL,
            },
        )
        activity_id = require_json_key(created, "id", "Criação de atividade pelo monitor")
        state["monitor_activity_id"] = activity_id
        save_state(state)

        runner.request(
            "GET",
            f"/activities/class/{class_id}",
            route_key="GET /activities/class/{course_class_id}",
            expected_status=200,
            token=monitor_token,
        )
        runner.request(
            "GET",
            f"/activities/{activity_id}",
            route_key="GET /activities/{activity_id}",
            expected_status=200,
            token=monitor_token,
        )
        runner.request(
            "PATCH",
            f"/activities/{activity_id}",
            route_key="PATCH /activities/{activity_id}",
            expected_status=200,
            token=monitor_token,
            json_body={
                "title": f"{config.MONITOR_ACTIVITY_TITLE} - atualizada",
                "description": "Atualização feita pelo monitor para validar permissão de escrita.",
            },
        )
        runner.request(
            "DELETE",
            f"/activities/{activity_id}",
            route_key="DELETE /activities/{activity_id}",
            expected_status=200,
            token=monitor_token,
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
        run_activities(state)
    finally:
        _, summary = build_summary(state)
        print(f"Relatório consolidado: {summary}")
