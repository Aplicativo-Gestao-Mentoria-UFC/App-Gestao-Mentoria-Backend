from __future__ import annotations

from . import config
from .common import (
    FlowAbort,
    FlowRunner,
    build_summary,
    create_state,
    ensure_mailpit_available,
    prompt_six_digit_code,
    require_json_key,
    save_state,
)


def run_auth(state: dict) -> FlowRunner:
    runner = FlowRunner("auth", state)
    try:
        ensure_mailpit_available()
        runner.add_note("Preflight do Mailpit concluído antes de iniciar a autenticação.")

        # 1) Cadastro de aluno
        runner.request(
            "POST",
            "/auth/register",
            route_key="POST /auth/register",
            expected_status=201,
            json_body={
                "username": config.STUDENT_USERNAME,
                "email": config.STUDENT_EMAIL,
                "role": "STUDENT",
                "password": config.STUDENT_PASSWORD,
            },
        )

        # 2) Reenvio explícito, para também cobrir essa rota e tornar o código pedido abaixo o mais recente.
        runner.request(
            "POST",
            "/auth/request-confirmation-code",
            route_key="POST /auth/request-confirmation-code",
            expected_status=200,
            json_body={"email": config.STUDENT_EMAIL},
        )
        print("\nAbra o Mailpit em http://localhost:8025 e use o código MAIS RECENTE do aluno.")
        student_confirmation_code = prompt_six_digit_code("Código de confirmação do aluno")
        runner.request(
            "POST",
            "/auth/verify-confirmation-code",
            route_key="POST /auth/verify-confirmation-code",
            expected_status=200,
            json_body={"email": config.STUDENT_EMAIL, "code": student_confirmation_code},
        )

        # 3) Login do aluno
        student_login = runner.request(
            "POST",
            "/auth/token",
            route_key="POST /auth/token",
            expected_status=200,
            form_body={"username": config.STUDENT_EMAIL, "password": config.STUDENT_PASSWORD},
        )
        state["student_access_token"] = require_json_key(
            student_login, "access_token", "Login do aluno"
        )
        student_me = runner.request(
            "GET",
            "/auth/me",
            route_key="GET /auth/me",
            expected_status=200,
            token=state["student_access_token"],
        )
        state["student_id"] = require_json_key(student_me, "id", "Perfil do aluno")

        # 4) Recuperação de senha
        runner.request(
            "POST",
            "/auth/forgot-password",
            route_key="POST /auth/forgot-password",
            expected_status=200,
            json_body={"email": config.STUDENT_EMAIL},
        )
        print("\nAbra novamente o Mailpit e use o código de RECUPERAÇÃO de senha do aluno.")
        reset_code = prompt_six_digit_code("Código de recuperação de senha")
        verify_reset = runner.request(
            "POST",
            "/auth/verify-reset-code",
            route_key="POST /auth/verify-reset-code",
            expected_status=200,
            json_body={"email": config.STUDENT_EMAIL, "code": reset_code},
        )
        reset_token = require_json_key(verify_reset, "reset_token", "Validação do reset")
        reset_response = runner.request(
            "POST",
            "/auth/reset-password",
            route_key="POST /auth/reset-password",
            expected_status=200,
            json_body={
                "reset_token": reset_token,
                "new_password": config.STUDENT_NEW_PASSWORD,
            },
        )
        state["student_access_token"] = require_json_key(
            reset_response, "access_token", "Reset de senha"
        )

        # Login novamente com a nova senha. A rota /auth/token já está coberta, mas isso valida o efeito do reset.
        runner.request(
            "POST",
            "/auth/token",
            route_key="POST /auth/token",
            expected_status=200,
            form_body={
                "username": config.STUDENT_EMAIL,
                "password": config.STUDENT_NEW_PASSWORD,
            },
        )

        # 5) Fluxo institucional do professor
        runner.request(
            "POST",
            "/auth/professor/signup/request",
            route_key="POST /auth/professor/signup/request",
            expected_status=200,
            json_body={"email": config.PROFESSOR_INSTITUTIONAL_EMAIL},
        )
        print("\nAbra o Mailpit e use o código institucional enviado ao professor.")
        professor_code = prompt_six_digit_code("Código institucional do professor")
        professor_verify = runner.request(
            "POST",
            "/auth/professor/signup/verify",
            route_key="POST /auth/professor/signup/verify",
            expected_status=200,
            json_body={
                "email": config.PROFESSOR_INSTITUTIONAL_EMAIL,
                "code": professor_code,
            },
        )
        signup_token = require_json_key(
            professor_verify, "signup_token", "Validação institucional do professor"
        )
        professor_complete = runner.request(
            "POST",
            "/auth/professor/signup/complete",
            route_key="POST /auth/professor/signup/complete",
            expected_status=201,
            json_body={
                "signup_token": signup_token,
                "email": config.PROFESSOR_ACCOUNT_EMAIL,
                "username": config.PROFESSOR_USERNAME,
                "password": config.PROFESSOR_PASSWORD,
            },
        )
        state["professor_access_token"] = require_json_key(
            professor_complete, "access_token", "Conclusão do cadastro do professor"
        )

        # Confirma login normal do professor.
        professor_login = runner.request(
            "POST",
            "/auth/token",
            route_key="POST /auth/token",
            expected_status=200,
            form_body={
                "username": config.PROFESSOR_ACCOUNT_EMAIL,
                "password": config.PROFESSOR_PASSWORD,
            },
        )
        state["professor_access_token"] = require_json_key(
            professor_login, "access_token", "Login do professor"
        )
        professor_me = runner.request(
            "GET",
            "/auth/me",
            route_key="GET /auth/me",
            expected_status=200,
            token=state["professor_access_token"],
        )
        state["professor_id"] = require_json_key(professor_me, "id", "Perfil do professor")

        save_state(state)
        runner.add_note("Tokens e IDs foram salvos em .api-test-state.json (arquivo ignorado pelo Git).")
        return runner
    except Exception as exc:
        if not isinstance(exc, FlowAbort):
            runner.record_internal_failure(str(exc))
        raise
    finally:
        runner.save()
        runner.close()
        save_state(state)


if __name__ == "__main__":
    state = create_state()
    try:
        run_auth(state)
    finally:
        _, summary = build_summary(state)
        print(f"Relatório consolidado: {summary}")
