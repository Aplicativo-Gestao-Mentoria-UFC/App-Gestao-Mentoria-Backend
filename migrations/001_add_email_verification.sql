-- Para bancos já existentes. Novos ambientes criados com create_tables.py
-- já recebem a coluna diretamente pelo modelo SQLAlchemy.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ NULL;

-- Preserva o acesso de contas que já existiam antes da introdução da verificação.
UPDATE users
SET email_verified_at = COALESCE(email_verified_at, CURRENT_TIMESTAMP);
