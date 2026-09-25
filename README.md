# Sistema de Gestão de Mentoria — API

API REST desenvolvida com FastAPI para gerenciamento de usuários, turmas de mentoria, alunos, monitores e atividades/materiais. O projeto possui autenticação JWT, confirmação de e-mail, fluxo institucional específico para professores, recuperação de senha, documentação automática com Swagger/ReDoc, PostgreSQL e ambiente Docker com Mailpit para testes de e-mail.

## 1. Tecnologias e arquitetura

A aplicação utiliza Python 3.12, FastAPI, SQLAlchemy assíncrono, PostgreSQL/asyncpg, Pydantic 2, JWT com `python-jose`, `passlib/bcrypt` para senhas, `aiosmtplib` para e-mail e Docker/Docker Compose para padronização do ambiente. O código é dividido em `routes/` para endpoints HTTP, `services/` para regras de negócio, `repositories/` para acesso ao banco, `models/` para entidades SQLAlchemy, `schemas/` para validação e contratos da API, `core/` para configuração/segurança/banco e `scripts/api_tests/` para a suíte de testes de todas as rotas.

O arquivo `create_tables.py` usa `Base.metadata.create_all()` para criar tabelas ausentes. As migrations SQL existentes ficam em `migrations/`. Em um ambiente de produção, o recomendado é substituir a estratégia manual de migrations por Alembic antes de evoluções maiores de schema.

## 2. Papéis e regras de acesso

Existem dois papéis persistidos em `users.role`: `TEACHER` e `STUDENT`. **Monitor não é uma terceira role.** Um monitor continua sendo `STUDENT` e recebe privilégios adicionais em uma turma por meio da tabela associativa `course_class_monitors`. Isso permite que um aluno seja monitor apenas nas turmas às quais foi explicitamente vinculado.

| Operação | Professor responsável | Monitor da turma | Aluno da turma |
|---|:---:|:---:|:---:|
| Listar/detalhar suas turmas | ✅ | ✅ | ✅ |
| Ver atividades da turma | ✅ | ✅ | ✅ |
| Criar atividade/material | ✅ | ✅ | ❌ |
| Editar atividade | ✅ | ✅ | ❌ |
| Excluir atividade | ✅ | ✅ | ❌ |
| Adicionar/remover aluno | ✅ | ❌ | ❌ |
| Adicionar/remover monitor | ✅ | ❌ | ❌ |

As atividades aceitam `fileUrl`. Atualmente a API armazena a URL de um arquivo; ela **não implementa upload binário multipart** de PDFs/imagens. Caso o cliente use S3, Supabase Storage, Firebase Storage ou outro serviço, o arquivo pode ser enviado para esse storage e a URL resultante informada em `fileUrl`.

## 3. Fluxos de autenticação

### 3.1 Aluno

1. `POST /auth/register` cria a conta com role `STUDENT` e senha forte.
2. A API envia um código de seis dígitos por e-mail.
3. `POST /auth/request-confirmation-code` permite solicitar um novo código.
4. `POST /auth/verify-confirmation-code` confirma o e-mail.
5. `POST /auth/token` realiza o login. Apesar do campo do OAuth2 se chamar `username`, informe **o e-mail** nele.
6. `GET /auth/me` retorna o usuário autenticado.

O domínio definido em `INSTITUTIONAL_EMAIL_DOMAINS` fica reservado ao fluxo institucional do professor. Portanto, com `INSTITUTIONAL_EMAIL_DOMAINS=alu.ufc.br`, o e-mail `pedroerykles@gmail.com` pode ser usado como aluno e `pedroerykles@alu.ufc.br` pode ser usado no fluxo institucional de professor.

### 3.2 Professor

1. `POST /auth/professor/signup/request` recebe o e-mail institucional e valida o domínio configurado no `.env`.
2. Um código de seis dígitos é enviado ao e-mail.
3. `POST /auth/professor/signup/verify` valida o código e devolve um `signup_token` temporário.
4. `POST /auth/professor/signup/complete` usa esse token para criar a conta `TEACHER` já verificada.
5. A partir daí, o login normal é feito em `POST /auth/token`.

O e-mail final da conta de professor pode ser diferente do institucional verificado, pois o vínculo entre a verificação e o cadastro é garantido pelo `signup_token`. Nos testes fornecidos, o mesmo `pedroerykles@alu.ufc.br` é usado como e-mail institucional e e-mail final da conta.

### 3.3 Recuperação de senha

O fluxo é `POST /auth/forgot-password` → código por e-mail → `POST /auth/verify-reset-code` → `reset_token` → `POST /auth/reset-password`. A última rota redefine a senha e já devolve um novo access token.

## 4. Entidades principais

### User

Campos principais: `id`, `username`, `email`, `role`, `hashed_password` e `email_verified_at`.

### CourseClass

Campos principais: `id`, `name`, `discipline`, `teacher_id` e `status`. Os relacionamentos incluem professor responsável, lista de estudantes, lista de monitores e atividades.

### Activity

Campos principais: `id`, `title`, `description`, `fileUrl` opcional e `course_class_id`.

Também existem entidades para códigos de confirmação de e-mail, códigos de recuperação de senha e verificações temporárias de cadastro institucional de professor.

## 5. Rotas disponíveis

### Health

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Verifica se a API está respondendo |
| GET | `/health/db` | Verifica conexão com PostgreSQL |

### Autenticação

| Método | Rota | Descrição |
|---|---|---|
| POST | `/auth/register` | Cadastrar aluno |
| POST | `/auth/token` | Login OAuth2 usando e-mail no campo `username` |
| GET | `/auth/me` | Obter usuário autenticado |
| POST | `/auth/request-confirmation-code` | Reenviar código de confirmação |
| POST | `/auth/verify-confirmation-code` | Confirmar e-mail do aluno |
| POST | `/auth/forgot-password` | Solicitar recuperação de senha |
| POST | `/auth/verify-reset-code` | Validar código de recuperação |
| POST | `/auth/reset-password` | Definir nova senha |
| POST | `/auth/professor/signup/request` | Solicitar código institucional do professor |
| POST | `/auth/professor/signup/verify` | Validar código institucional |
| POST | `/auth/professor/signup/complete` | Concluir cadastro de professor |

### Professor

| Método | Rota | Descrição |
|---|---|---|
| POST | `/teacher/register-class` | Criar turma |
| GET | `/teacher/my-classes` | Listar turmas do professor; suporta filtros e paginação |
| GET | `/teacher/my-classes/{course_class_id}` | Detalhar uma turma do professor |
| PUT | `/teacher/my-classes/{course_class_id}/add-student` | Adicionar aluno pelo e-mail |
| PATCH | `/teacher/my-classes/{course_class_id}/remove-student` | Remover aluno pelo UUID |
| PUT | `/teacher/my-classes/{course_class_id}/add-monitor` | Adicionar monitor pelo e-mail |
| PATCH | `/teacher/my-classes/{course_class_id}/remove-monitor` | Remover monitor pelo UUID |
| POST | `/teacher/my-classes/{course_class_id}/add-activity` | Criar atividade pela rota específica do professor |

### Aluno

| Método | Rota | Descrição |
|---|---|---|
| GET | `/student/my-classes` | Listar turmas em que o usuário é aluno |
| GET | `/student/my-classes/{course_class_id}` | Detalhar uma turma em que o usuário é aluno |

### Monitor

| Método | Rota | Descrição |
|---|---|---|
| GET | `/monitor/my-classes` | Listar turmas em que o aluno atua como monitor |
| GET | `/monitor/my-classes/{course_class_id}` | Detalhar turma como monitor |

### Atividades

| Método | Rota | Descrição |
|---|---|---|
| POST | `/activities/class/{course_class_id}` | Professor ou monitor cria uma atividade |
| GET | `/activities/class/{course_class_id}` | Lista atividades para professor, monitor ou aluno da turma |
| GET | `/activities/{activity_id}` | Detalhar atividade acessível ao usuário |
| PATCH | `/activities/{activity_id}` | Professor ou monitor atualiza atividade |
| DELETE | `/activities/{activity_id}` | Professor ou monitor exclui atividade |

Total atual: **30 rotas distintas**.

## 6. Documentação automática da API

Com a aplicação executando em `http://localhost:8000`:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Health check: `http://localhost:8000/health`
- Health check do banco: `http://localhost:8000/health/db`
- Mailpit: `http://localhost:8025`

O Swagger é gerado diretamente das rotas e schemas do FastAPI, portanto deve ser considerado a referência HTTP atual da aplicação.

## 7. Configuração do ambiente

Copie o exemplo:

```bash
cp .env.example .env
```

Configuração recomendada para os testes fornecidos:

```env
INSTITUTIONAL_EMAIL_DOMAINS=alu.ufc.br
```

As principais variáveis são:

| Variável | Finalidade |
|---|---|
| `DB_URL` | URL assíncrona do PostgreSQL |
| `POSTGRES_DB` | Nome do banco usado pelo Docker Compose |
| `POSTGRES_USER` | Usuário do PostgreSQL |
| `POSTGRES_PASSWORD` | Senha do PostgreSQL |
| `JWT_SECRET` | Segredo para assinatura dos JWTs |
| `ALGORITHM` | Algoritmo JWT, padrão HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duração do access token |
| `INSTITUTIONAL_EMAIL_DOMAINS` | Domínios aceitos para professor, separados por vírgula |
| `MAIL_HOST` / `MAIL_PORT` | Servidor SMTP |
| `MAIL_USERNAME` / `MAIL_PASSWORD` | Credenciais SMTP, quando necessárias |
| `MAIL_FROM` | Remetente dos e-mails |
| `MAIL_START_TLS` | Habilita STARTTLS |
| `MAIL_VALIDATE_CERTS` | Validação de certificado TLS |
| `DOCKER_MAIL_HOST` | Host SMTP visto pelo container da API |
| `CORS_ORIGINS` | Origens CORS separadas por vírgula |

Nunca utilize a chave JWT e as senhas padrão do exemplo em produção.

## 8. Executando com Docker — recomendado

Pré-requisitos: Docker e Docker Compose v2.

```bash
cp .env.example .env
docker compose up --build -d
```

O Compose inicia PostgreSQL, Mailpit e a API. Durante a inicialização, a API executa `python create_tables.py` antes do Uvicorn.

Verifique os serviços:

```bash
docker compose ps
curl http://localhost:8000/health
curl http://localhost:8000/health/db
```

Logs da API:

```bash
docker compose logs -f api
```

Encerrar sem apagar o banco:

```bash
docker compose down
```

Encerrar e apagar o volume do PostgreSQL — recomendado antes de uma execução completa da suíte com os e-mails fixos:

```bash
docker compose down -v
docker compose up --build -d
```

O reset é necessário para uma execução totalmente determinística porque a regra de negócio impede reutilizar um e-mail institucional que já concluiu o cadastro de professor.

## 9. Executando sem Docker

É necessário Python 3.12 e uma instância PostgreSQL disponível.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python create_tables.py
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

No Windows PowerShell, a ativação do ambiente virtual é:

```powershell
.\.venv\Scripts\Activate.ps1
```

Para usar os scripts de teste, instale também as dependências de desenvolvimento:

```bash
pip install -r requirements-dev.txt
```

## 10. Suíte de testes de todas as rotas

A suíte está em `scripts/api_tests/` e utiliza `httpx`. Cada fluxo possui seu próprio arquivo:

```text
scripts/api_tests/
├── auth_flow.py
├── health_flow.py
├── teacher_flow.py
├── student_flow.py
├── monitor_flow.py
├── activities_flow.py
├── run_all.py
├── run_non_auth.py
├── common.py
└── config.py
```

Os dados padrão de teste são:

```text
Professor institucional: pedroerykles@alu.ufc.br
Aluno/monitor:            pedroerykles@gmail.com
Professor username:       prof_pedro
Aluno username:           aluno_pedro
```

As senhas são senhas exclusivas de teste definidas em `scripts/api_tests/config.py` e podem ser sobrescritas por variáveis de ambiente `API_TEST_*`.

### 10.1 Execução completa

Primeiro garanta um banco limpo:

```bash
docker compose down -v
docker compose up --build -d
```

Instale as dependências de teste no ambiente Python que executará o script:

```bash
pip install -r requirements-dev.txt
```

Execute:

```bash
python -m scripts.api_tests.run_all
```

A suíte para três vezes para você informar os códigos recebidos:

1. código de confirmação do aluno;
2. código de recuperação de senha do aluno;
3. código institucional do professor.

Abra `http://localhost:8025` para consultar os e-mails no Mailpit. Sempre use o código mais recente correspondente ao fluxo indicado no terminal.

Depois da autenticação, os tokens e UUIDs necessários são compartilhados automaticamente através de `.api-test-state.json`. Esse arquivo contém estado temporário da execução e está no `.gitignore`.

### 10.2 Autenticação separada dos demais fluxos

Se quiser lidar com os códigos primeiro e depois executar todo o restante sem novas interações:

```bash
python -m scripts.api_tests.auth_flow
```

Após informar todos os códigos e o fluxo terminar com sucesso:

```bash
python -m scripts.api_tests.run_non_auth
```

Esse é o modo recomendado quando você deseja separar o fluxo manual de e-mail do restante da automação.

### 10.3 Executando um fluxo específico

Depois que a autenticação tiver criado `.api-test-state.json` e a turma tiver sido preparada quando necessário, os módulos podem ser executados individualmente:

```bash
python -m scripts.api_tests.health_flow
python -m scripts.api_tests.teacher_flow --phase setup
python -m scripts.api_tests.student_flow
python -m scripts.api_tests.monitor_flow
python -m scripts.api_tests.activities_flow
python -m scripts.api_tests.teacher_flow --phase cleanup
```

A ordem completa usada por `run_all.py` é: health → auth → teacher setup → student → monitor → activities → teacher cleanup. Essa ordem é importante porque as rotas de remoção de aluno/monitor precisam ser testadas somente depois que os acessos de aluno e monitor já foram validados.

## 11. Relatórios gerados

Cada execução cria uma pasta como:

```text
api-test-reports/20260925-140000/
├── health.json
├── health.md
├── auth.json
├── auth.md
├── teacher.json
├── teacher.md
├── student.json
├── student.md
├── monitor.json
├── monitor.md
├── activities.json
├── activities.md
├── summary.json
└── summary.md
```

Cada fluxo gera um relatório independente em JSON e Markdown. O `summary.md` consolida sucessos, falhas e cobertura das **30 rotas**. Senhas, códigos e tokens são mascarados nos relatórios (`***REDACTED***`). Os tokens reais ficam apenas no `.api-test-state.json`, que não deve ser versionado.

Se uma rota devolver um status diferente do esperado, o relatório registra método, caminho, status esperado, status obtido, duração, request sanitizado e response. A execução é interrompida quando uma falha inviabiliza as etapas dependentes, preservando tudo que já foi testado até aquele ponto.

## 12. Variáveis opcionais da suíte

É possível trocar os dados sem editar os scripts:

```bash
export API_TEST_BASE_URL=http://localhost:8000
export API_TEST_STUDENT_EMAIL=pedroerykles@gmail.com
export API_TEST_PROFESSOR_INSTITUTIONAL_EMAIL=pedroerykles@alu.ufc.br
export API_TEST_STUDENT_PASSWORD='Aluno@12345'
export API_TEST_PROFESSOR_PASSWORD='Professor@12345'
python -m scripts.api_tests.run_all
```

Variáveis suportadas estão centralizadas em `scripts/api_tests/config.py`.

## 13. Testes unitários existentes

Os testes já existentes ficam em `testing/`. Para executá-los:

```bash
pytest
```

Para uma verificação simples de sintaxe de todo o projeto:

```bash
python -m compileall -q .
```

## 14. Estrutura principal do projeto

```text
.
├── core/
├── migrations/
├── models/
├── repositories/
├── routes/
├── schemas/
├── services/
├── scripts/api_tests/
├── testing/
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── create_tables.py
├── main.py
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## 15. Pontos de atenção atuais

O sistema possui autorização por turma para professor, aluno e monitor e o fluxo de cadastro institucional é configurável pelo `.env`. O monitor é um `STUDENT` vinculado à turma e pode criar/editar/excluir atividades apenas nessa turma. A API armazena `fileUrl`, mas ainda não faz upload físico de arquivos. Para produção, também é recomendável adotar Alembic para migrations, usar um `JWT_SECRET` forte, configurar SMTP real, restringir CORS aos domínios necessários e não expor Mailpit.

## 16. Solução de problemas da suíte de API

### `Server disconnected without sending a response` após `/auth/register`

O cadastro de aluno agenda o envio do código de confirmação em uma `BackgroundTask`. Em versões anteriores, se o SMTP/Mailpit estivesse indisponível, a exceção ocorria depois que o `201 Created` já havia sido enviado e podia fechar a conexão HTTP keep-alive. A etapa seguinte (`POST /auth/request-confirmation-code`) então aparecia no runner como `Server disconnected without sending a response`.

A versão atual trata falhas dos envios executados em background sem propagá-las para o ciclo HTTP e a suíte não reutiliza conexões keep-alive. O fluxo de autenticação também faz um preflight do Mailpit antes de criar usuários.

Antes de executar a suíte, confira:

```bash
docker compose ps
curl http://localhost:8000/health
curl http://localhost:8000/health/db
curl -I http://localhost:8025
```

Os serviços `api`, `db` e `mailpit` devem estar em execução. Para verificar o SMTP do Mailpit:

```bash
nc -zv localhost 1025
```

Se houver problema, consulte os logs:

```bash
docker compose logs --tail=200 api
docker compose logs --tail=200 mailpit
```

Se uma execução tiver sido interrompida depois do cadastro inicial, o usuário de teste pode já existir no PostgreSQL. Para executar a suíte completa desde o zero, use um banco limpo:

```bash
docker compose down -v
docker compose up --build -d
python -m scripts.api_tests.run_all
```

Por padrão, os testes exigem Mailpit local. As opções são configuráveis:

```env
API_TEST_REQUIRE_MAILPIT=true
API_TEST_MAILPIT_URL=http://localhost:8025
API_TEST_SMTP_HOST=localhost
API_TEST_SMTP_PORT=1025
```

Se estiver usando um SMTP real em vez do Mailpit, desative apenas o preflight específico do Mailpit:

```bash
export API_TEST_REQUIRE_MAILPIT=false
python -m scripts.api_tests.run_all
```

Isso não desativa o envio de e-mail da aplicação; apenas impede que a suíte exija `localhost:8025/1025` antes do teste.
