-- Existing accounts remain verified; new accounts start unverified.
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP NULL;

UPDATE users
SET email_verified = TRUE,
    email_verified_at = COALESCE(email_verified_at, CURRENT_TIMESTAMP)
WHERE email_verified IS NULL;

ALTER TABLE users ALTER COLUMN email_verified SET NOT NULL;
ALTER TABLE users ALTER COLUMN email_verified SET DEFAULT FALSE;
