CREATE TABLE IF NOT EXISTS professor_signup_verifications (
    id UUID PRIMARY KEY,
    email VARCHAR NOT NULL,
    code_hash VARCHAR NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    verified_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_professor_signup_verifications_email
    ON professor_signup_verifications (email);
