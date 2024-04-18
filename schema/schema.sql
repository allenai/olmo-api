-- For simplicity this application lacks automated database migrations. Instead
-- the schema is expressed in a single file and migrations are manually executed
-- by piping the content from stdin to the psql command.
--
-- See ./docs/db.md for more information about executing migrations.

CREATE TABLE IF NOT EXISTS prompt_template (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  content TEXT NOT NULL,
  author TEXT NOT NULL,
  created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted TIMESTAMPTZ NULL
);

GRANT SELECT, UPDATE, INSERT ON TABLE prompt_template TO app;

CREATE TABLE IF NOT EXISTS client_token (
  token TEXT NOT NULL PRIMARY KEY,
  client TEXT NOT NULL, -- this might be an email, i.e "sams@allenai.org" or an identifier i.e. "system-x"
  created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '1 day'
);

GRANT SELECT, UPDATE, INSERT ON TABLE client_token TO app;

CREATE TABLE IF NOT EXISTS completion (
  id TEXT NOT NULL PRIMARY KEY,
  input TEXT NOT NULL,
  outputs JSONB NOT NULL,
  opts JSONB NOT NULL,
  model TEXT NOT NULL,
  sha TEXT NOT NULL,
  created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  tokenize_ms INTEGER NOT NULL,
  generation_ms INTEGER NOT NULL,
  queue_ms INTEGER NOT NULL,
  input_tokens INTEGER NOT NULL,
  output_tokens INTEGER NOT NULL
);

GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE completion TO app;

CREATE TABLE IF NOT EXISTS message (
  id TEXT NOT NULL PRIMARY KEY,
  content TEXT NOT NULL,
  creator TEXT NOT NULL,
  role TEXT NOT NULL,
  opts JSONB NOT NULL,
  root TEXT NOT NULL,
  created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted TIMESTAMPTZ NULL,
  parent TEXT NULL,
  template TEXT NULL,
  logprobs JSONB[] NULL,
  completion TEXT NULL,

  FOREIGN KEY (root) REFERENCES message(id),
  FOREIGN KEY (parent) REFERENCES message(id),
  FOREIGN KEY (template) REFERENCES prompt_template(id),
  FOREIGN KEY (completion) REFERENCES completion(id)
);

GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE message TO app;

CREATE TABLE IF NOT EXISTS label (
  id TEXT NOT NULL PRIMARY KEY,
  message TEXT NOT NULL,
  rating INTEGER NOT NULL,
  creator TEXT NOT NULL,
  comment TEXT NULL,
  created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted TIMESTAMPTZ NULL,

  FOREIGN KEY (message) REFERENCES message(id)
);

GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE label TO app;

-- Add the final column and immediately set it to true for all messages, since this
-- will be released prior to streaming support.
ALTER TABLE message ADD COLUMN IF NOT EXISTS final BOOLEAN NOT NULL DEFAULT false;
UPDATE message SET final = true;

-- Add the original column that's used to track edits.
ALTER TABLE message ADD COLUMN IF NOT EXISTS original TEXT NULL;

-- We always drop and re-add the constraint so that the effect is idempotent
ALTER TABLE message DROP CONSTRAINT IF EXISTS message_original_fkey;
ALTER TABLE message ADD CONSTRAINT message_original_fkey FOREIGN KEY (original) REFERENCES message(id);

-- Tokens can be used for different purposes. An 'auth' token is used for authenticating API clients.
-- An 'invite' token is used to generate a single-use URL for creating a 'client' token.
CREATE TYPE TOKEN_TYPE AS ENUM('auth', 'invite');

ALTER TABLE client_token ADD COLUMN IF NOT EXISTS token_type TOKEN_TYPE NOT NULL DEFAULT 'auth',
                         ADD COLUMN IF NOT EXISTS creator TEXT NULL,
                         ADD COLUMN IF NOT EXISTS invite TEXT NULL REFERENCES client_token(token) UNIQUE;

-- Make sure filtering by token type is fast
CREATE INDEX IF NOT EXISTS token_type_idx ON client_token(token_type);

CREATE TABLE IF NOT EXISTS datachip (
  id TEXT NOT NULL PRIMARY KEY,
  name TEXT NOT NULL,
  content TEXT NOT NULL,
  creator TEXT NOT NULL,
  created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted TIMESTAMPTZ NULL
);


GRANT SELECT, UPDATE, INSERT ON TABLE datachip TO app;

ALTER TABLE message ADD COLUMN IF NOT EXISTS private BOOLEAN NOT NULL DEFAULT false;

-- A globally unique, human readable ID for referencing the datachip.
ALTER TABLE datachip ADD COLUMN ref TEXT NOT NULL UNIQUE;

-- Add a column to track the type of model used.
CREATE TYPE MODEL_TYPE AS ENUM('base', 'chat');
ALTER TABLE message ADD COLUMN IF NOT EXISTS model_type MODEL_TYPE NULL;

-- Add delete cascade to below foreign keys so that deleting any rows in parent tables will automatically remove related rows in child tables --
ALTER TABLE message DROP CONSTRAINT IF EXISTS message_completion_fkey;
ALTER TABLE message ADD CONSTRAINT message_completion_fkey FOREIGN KEY (completion) REFERENCES completion(id) ON DELETE CASCADE;

ALTER TABLE message DROP CONSTRAINT IF EXISTS message_root_fkey;
ALTER TABLE message ADD CONSTRAINT message_root_fkey FOREIGN KEY (root) REFERENCES message(id) ON DELETE CASCADE;

ALTER TABLE message DROP CONSTRAINT IF EXISTS message_parent_fkey;
ALTER TABLE message ADD CONSTRAINT message_parent_fkey FOREIGN KEY (parent) REFERENCES message(id) ON DELETE CASCADE;

ALTER TABLE message DROP CONSTRAINT IF EXISTS message_original_fkey;
ALTER TABLE message ADD CONSTRAINT message_original_fkey FOREIGN KEY (original) REFERENCES message(id) ON DELETE CASCADE;

ALTER TABLE label DROP CONSTRAINT IF EXISTS label_message_fkey;
ALTER TABLE label ADD CONSTRAINT label_message_fkey FOREIGN KEY (message) REFERENCES message(id) ON DELETE CASCADE;

CREATE TABLE IF NOT EXISTS olmo_user (
  id TEXT NOT NULL PRIMARY KEY,
  -- this might be an email, i.e "sams@allenai.org" or an identifier i.e. "system-x". it may be an oauth ID in the future
  client TEXT NOT NULL,
  terms_accepted_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  -- GDPR requires that consent can be revoked. This field will allow us to track that while still keeping the user around. That may come in handy if we need to delete their data programmatically
  acceptance_revoked_date TIMESTAMPTZ NULL 
);
GRANT SELECT, UPDATE, INSERT ON TABLE olmo_user TO app;
CREATE INDEX IF NOT EXISTS client_idx ON olmo_user(client);
