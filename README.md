# Mentoria API

FastAPI backend for institutional signup, email-code confirmation, class management, monitors and activities.

## Run with Docker Compose

1. Copy the environment template:

   ```bash
   cp .env.example .env
   ```

2. Fill in the JWT and email credentials in `.env`.

3. Start the API and PostgreSQL:

   ```bash
   docker compose up --build
   ```

4. Open the API documentation:

   - Swagger: `http://localhost:8000/docs`
   - Health: `http://localhost:8000/health`

The local Compose stack creates the database tables and applies the email-verification migration automatically.

## Stop the stack

```bash
docker compose down
```

To also delete the local PostgreSQL data:

```bash
docker compose down -v
```

## Test without Docker

```bash
python -m pip install -r requirements-dev.txt
pytest -q
```

See `docs/COURSE_CLASS_ROUTES.md` for the class API and `docs/DOCKER_AND_CICD.md` for AWS deployment configuration.
