from __future__ import annotations

import json
import os
import socket
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import httpx

from . import config

ROOT_DIR = Path(__file__).resolve().parents[2]
STATE_FILE = ROOT_DIR / ".api-test-state.json"
REPORT_ROOT = ROOT_DIR / "api-test-reports"

SENSITIVE_KEYS = {
    "authorization",
    "access_token",
    "signup_token",
    "reset_token",
    "password",
    "new_password",
    "code",
}

ROUTE_INVENTORY: dict[str, str] = {
    "GET /health": "health",
    "GET /health/db": "health",
    "POST /auth/register": "auth",
    "POST /auth/token": "auth",
    "GET /auth/me": "auth",
    "POST /auth/forgot-password": "auth",
    "POST /auth/verify-reset-code": "auth",
    "POST /auth/reset-password": "auth",
    "POST /auth/request-confirmation-code": "auth",
    "POST /auth/verify-confirmation-code": "auth",
    "POST /auth/professor/signup/request": "auth",
    "POST /auth/professor/signup/verify": "auth",
    "POST /auth/professor/signup/complete": "auth",
    "POST /teacher/register-class": "teacher",
    "GET /teacher/my-classes": "teacher",
    "GET /teacher/my-classes/{course_class_id}": "teacher",
    "PUT /teacher/my-classes/{course_class_id}/add-monitor": "teacher",
    "PATCH /teacher/my-classes/{course_class_id}/remove-monitor": "teacher",
    "PUT /teacher/my-classes/{course_class_id}/add-student": "teacher",
    "PATCH /teacher/my-classes/{course_class_id}/remove-student": "teacher",
    "POST /teacher/my-classes/{course_class_id}/add-activity": "teacher",
    "GET /student/my-classes": "student",
    "GET /student/my-classes/{course_class_id}": "student",
    "GET /monitor/my-classes": "monitor",
    "GET /monitor/my-classes/{course_class_id}": "monitor",
    "POST /activities/class/{course_class_id}": "activities",
    "GET /activities/class/{course_class_id}": "activities",
    "GET /activities/{activity_id}": "activities",
    "PATCH /activities/{activity_id}": "activities",
    "DELETE /activities/{activity_id}": "activities",
}


class FlowAbort(RuntimeError):
    pass


def ensure_mailpit_available() -> None:
    """Valida o Mailpit usado pelos fluxos interativos de autenticação.

    Pode ser desabilitado com API_TEST_REQUIRE_MAILPIT=false quando os testes
    estiverem usando um SMTP real em vez do Mailpit local.
    """
    if not config.REQUIRE_MAILPIT:
        return

    try:
        response = httpx.get(config.MAILPIT_WEB_URL, timeout=3.0, follow_redirects=True)
        if response.status_code >= 500:
            raise RuntimeError(f"HTTP {response.status_code}")
    except Exception as exc:
        raise FlowAbort(
            "Mailpit web indisponível em "
            f"{config.MAILPIT_WEB_URL}. Suba o serviço com 'docker compose up -d mailpit' "
            "ou defina API_TEST_REQUIRE_MAILPIT=false se estiver usando SMTP real. "
            f"Detalhe: {exc}"
        ) from exc

    try:
        with socket.create_connection(
            (config.MAILPIT_SMTP_HOST, config.MAILPIT_SMTP_PORT), timeout=3.0
        ):
            pass
    except OSError as exc:
        raise FlowAbort(
            "SMTP do Mailpit indisponível em "
            f"{config.MAILPIT_SMTP_HOST}:{config.MAILPIT_SMTP_PORT}. "
            "Confira 'docker compose ps' e 'docker compose logs mailpit'. "
            f"Detalhe: {exc}"
        ) from exc


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def create_state() -> dict[str, Any]:
    run_id = make_run_id()
    report_dir = REPORT_ROOT / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "run_id": run_id,
        "report_dir": str(report_dir),
        "base_url": config.BASE_URL,
        "created_at": utc_now_iso(),
    }
    save_state(state)
    return state


def load_state(required: bool = True) -> dict[str, Any]:
    if not STATE_FILE.exists():
        if required:
            raise SystemExit(
                "Estado de testes não encontrado. Execute primeiro: "
                "python -m scripts.api_tests.auth_flow"
            )
        return create_state()
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def report_dir_from_state(state: dict[str, Any]) -> Path:
    path = Path(state["report_dir"])
    path.mkdir(parents=True, exist_ok=True)
    return path


def _redact(value: Any, parent_key: str | None = None) -> Any:
    if parent_key and parent_key.lower() in SENSITIVE_KEYS:
        return "***REDACTED***"
    if isinstance(value, dict):
        return {str(k): _redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _safe_response_body(response: httpx.Response) -> Any:
    try:
        return _redact(response.json())
    except Exception:
        text = response.text
        return text[:4000] + ("..." if len(text) > 4000 else "")


class FlowRunner:
    def __init__(self, flow_name: str, state: dict[str, Any], append_existing: bool = False):
        self.flow_name = flow_name
        self.state = state
        self.base_url = state.get("base_url", config.BASE_URL).rstrip("/")
        self.started_at = utc_now_iso()
        self.steps: list[dict[str, Any]] = []
        self.notes: list[str] = []

        if append_existing:
            previous_path = report_dir_from_state(state) / f"{flow_name}.json"
            if previous_path.exists():
                try:
                    previous = json.loads(previous_path.read_text(encoding="utf-8"))
                    self.started_at = previous.get("started_at", self.started_at)
                    self.steps.extend(previous.get("steps", []))
                    self.notes.extend(previous.get("notes", []))
                except Exception:
                    pass

        self.client = httpx.Client(
            timeout=config.REQUEST_TIMEOUT,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=0),
        )

    def close(self) -> None:
        self.client.close()

    def add_note(self, note: str) -> None:
        self.notes.append(note)

    def request(
        self,
        method: str,
        path: str,
        *,
        route_key: str,
        expected_status: int | Iterable[int],
        token: str | None = None,
        json_body: dict[str, Any] | None = None,
        form_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        critical: bool = True,
    ) -> httpx.Response:
        if isinstance(expected_status, int):
            expected = [expected_status]
        else:
            expected = list(expected_status)

        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        request_snapshot: dict[str, Any] = {
            "headers": _redact(headers),
            "params": _redact(params or {}),
        }
        if json_body is not None:
            request_snapshot["json"] = _redact(json_body)
        if form_body is not None:
            request_snapshot["form"] = _redact(form_body)

        started = time.perf_counter()
        try:
            response = self.client.request(
                method=method,
                url=f"{self.base_url}{path}",
                headers=headers,
                json=json_body,
                data=form_body,
                params=params,
            )
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            passed = response.status_code in expected
            self.steps.append(
                {
                    "route_key": route_key,
                    "method": method.upper(),
                    "path": path,
                    "expected_status": expected,
                    "actual_status": response.status_code,
                    "passed": passed,
                    "duration_ms": elapsed_ms,
                    "request": request_snapshot,
                    "response": _safe_response_body(response),
                }
            )
            if critical and not passed:
                raise FlowAbort(
                    f"{method.upper()} {path}: esperado {expected}, recebido {response.status_code}"
                )
            return response
        except httpx.RequestError as exc:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            self.steps.append(
                {
                    "route_key": route_key,
                    "method": method.upper(),
                    "path": path,
                    "expected_status": expected,
                    "actual_status": None,
                    "passed": False,
                    "duration_ms": elapsed_ms,
                    "request": request_snapshot,
                    "response": {"error": str(exc)},
                }
            )
            raise FlowAbort(f"Falha de conexão em {method.upper()} {path}: {exc}") from exc

    def record_internal_failure(self, message: str) -> None:
        self.steps.append(
            {
                "route_key": "INTERNAL",
                "method": "-",
                "path": "-",
                "expected_status": [],
                "actual_status": None,
                "passed": False,
                "duration_ms": 0,
                "request": {},
                "response": {"error": message},
            }
        )

    @property
    def passed(self) -> int:
        return sum(1 for step in self.steps if step.get("passed"))

    @property
    def failed(self) -> int:
        return sum(1 for step in self.steps if not step.get("passed"))

    def save(self) -> tuple[Path, Path]:
        report_dir = report_dir_from_state(self.state)
        json_path = report_dir / f"{self.flow_name}.json"
        md_path = report_dir / f"{self.flow_name}.md"

        payload = {
            "flow": self.flow_name,
            "started_at": self.started_at,
            "finished_at": utc_now_iso(),
            "base_url": self.base_url,
            "passed": self.passed,
            "failed": self.failed,
            "total": len(self.steps),
            "notes": self.notes,
            "steps": self.steps,
        }
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        lines = [
            f"# Relatório — {self.flow_name}",
            "",
            f"- **Base URL:** `{self.base_url}`",
            f"- **Sucessos:** {self.passed}",
            f"- **Falhas:** {self.failed}",
            f"- **Total de requisições:** {len(self.steps)}",
            "",
        ]
        if self.notes:
            lines += ["## Observações", ""] + [f"- {note}" for note in self.notes] + [""]
        lines += [
            "## Resultados",
            "",
            "| Status | Rota | HTTP | Esperado | Tempo |",
            "|---|---|---:|---|---:|",
        ]
        for step in self.steps:
            status_mark = "✅" if step.get("passed") else "❌"
            expected_text = ", ".join(str(v) for v in step.get("expected_status", [])) or "-"
            actual = step.get("actual_status") if step.get("actual_status") is not None else "-"
            lines.append(
                f"| {status_mark} | `{step.get('method')} {step.get('path')}` | "
                f"{actual} | {expected_text} | {step.get('duration_ms', 0)} ms |"
            )
        lines += ["", "## Detalhes", ""]
        for index, step in enumerate(self.steps, start=1):
            lines += [
                f"### {index}. {step.get('method')} {step.get('path')}",
                "",
                f"- Resultado: {'PASSOU' if step.get('passed') else 'FALHOU'}",
                f"- Route key: `{step.get('route_key')}`",
                f"- HTTP recebido: `{step.get('actual_status')}`",
                "",
                "```json",
                json.dumps(
                    {"request": step.get("request"), "response": step.get("response")},
                    indent=2,
                    ensure_ascii=False,
                ),
                "```",
                "",
            ]
        md_path.write_text("\n".join(lines), encoding="utf-8")
        return json_path, md_path


def require_json_key(response: httpx.Response, key: str, context: str) -> Any:
    try:
        payload = response.json()
    except Exception as exc:
        raise FlowAbort(f"{context}: resposta não é JSON válido") from exc
    if key not in payload:
        raise FlowAbort(f"{context}: campo obrigatório '{key}' ausente na resposta")
    return payload[key]


def prompt_six_digit_code(label: str) -> str:
    while True:
        code = input(f"{label} (6 dígitos): ").strip()
        if len(code) == 6 and code.isdigit():
            return code
        print("Código inválido. Digite exatamente 6 números.")


def build_summary(state: dict[str, Any]) -> tuple[Path, Path]:
    report_dir = report_dir_from_state(state)
    flow_reports: list[dict[str, Any]] = []
    covered_routes: set[str] = set()

    for path in sorted(report_dir.glob("*.json")):
        if path.name == "summary.json":
            continue
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        flow_reports.append(report)
        for step in report.get("steps", []):
            route_key = step.get("route_key")
            if route_key in ROUTE_INVENTORY:
                covered_routes.add(route_key)

    total_passed = sum(report.get("passed", 0) for report in flow_reports)
    total_failed = sum(report.get("failed", 0) for report in flow_reports)
    missing_routes = sorted(set(ROUTE_INVENTORY) - covered_routes)
    coverage = {
        "covered": len(covered_routes),
        "total": len(ROUTE_INVENTORY),
        "percent": round((len(covered_routes) / len(ROUTE_INVENTORY)) * 100, 2),
        "missing": missing_routes,
    }

    payload = {
        "run_id": state.get("run_id"),
        "generated_at": utc_now_iso(),
        "passed_requests": total_passed,
        "failed_requests": total_failed,
        "route_coverage": coverage,
        "flows": [
            {
                "flow": report.get("flow"),
                "passed": report.get("passed"),
                "failed": report.get("failed"),
                "total": report.get("total"),
            }
            for report in flow_reports
        ],
    }

    json_path = report_dir / "summary.json"
    md_path = report_dir / "summary.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Relatório consolidado dos testes da API",
        "",
        f"- **Run ID:** `{state.get('run_id')}`",
        f"- **Requisições aprovadas:** {total_passed}",
        f"- **Requisições com falha:** {total_failed}",
        f"- **Cobertura de rotas:** {coverage['covered']}/{coverage['total']} ({coverage['percent']}%)",
        "",
        "## Fluxos",
        "",
        "| Fluxo | Sucessos | Falhas | Total |",
        "|---|---:|---:|---:|",
    ]
    for report in flow_reports:
        lines.append(
            f"| {report.get('flow')} | {report.get('passed', 0)} | "
            f"{report.get('failed', 0)} | {report.get('total', 0)} |"
        )

    lines += ["", "## Cobertura das rotas", ""]
    for route_key in ROUTE_INVENTORY:
        lines.append(f"- {'✅' if route_key in covered_routes else '❌'} `{route_key}`")
    if missing_routes:
        lines += ["", "## Rotas ainda não executadas", ""]
        lines += [f"- `{route}`" for route in missing_routes]

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
