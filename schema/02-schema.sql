BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 67c7571bc5b8

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
GRANT SELECT,
  UPDATE,
  INSERT ON TABLE prompt_template TO app;
CREATE TABLE IF NOT EXISTS client_token (
  token TEXT NOT NULL PRIMARY KEY,
  client TEXT NOT NULL,
  -- this might be an email, i.e "sams@allenai.org" or an identifier i.e. "system-x"
  created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '1 day'
);

GRANT SELECT,
  UPDATE,
  INSERT ON TABLE client_token TO app;
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
GRANT SELECT,
  UPDATE,
  INSERT,
  DELETE ON TABLE completion TO app;

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
  logprobs JSONB [] NULL,
  completion TEXT NULL,
  FOREIGN KEY (root) REFERENCES message(id),
  FOREIGN KEY (parent) REFERENCES message(id),
  FOREIGN KEY (template) REFERENCES prompt_template(id),
  FOREIGN KEY (completion) REFERENCES completion(id)
);
GRANT SELECT,
  UPDATE,
  INSERT,
  DELETE ON TABLE message TO app;

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
GRANT SELECT,
  UPDATE,
  INSERT,
  DELETE ON TABLE label TO app;
-- Add the final column and immediately set it to true for all messages, since this
-- will be released prior to streaming support.
ALTER TABLE message
ADD COLUMN IF NOT EXISTS final BOOLEAN NOT NULL DEFAULT false;
UPDATE message
SET final = true;

-- Add the original column that's used to track edits.
ALTER TABLE message
ADD COLUMN IF NOT EXISTS original TEXT NULL;

-- We always drop and re-add the constraint so that the effect is idempotent
ALTER TABLE message DROP CONSTRAINT IF EXISTS message_original_fkey;
ALTER TABLE message
ADD CONSTRAINT message_original_fkey FOREIGN KEY (original) REFERENCES message(id);

-- Tokens can be used for different purposes. An 'auth' token is used for authenticating API clients.
-- An 'invite' token is used to generate a single-use URL for creating a 'client' token.
DO $$ BEGIN IF to_regtype('TOKEN_TYPE') IS NULL THEN CREATE TYPE TOKEN_TYPE AS ENUM('auth', 'invite');
END IF;
END $$;

ALTER TABLE client_token
ADD COLUMN IF NOT EXISTS token_type TOKEN_TYPE NOT NULL DEFAULT 'auth',
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

GRANT SELECT,
  UPDATE,
  INSERT ON TABLE datachip TO app;

ALTER TABLE message
ADD COLUMN IF NOT EXISTS private BOOLEAN NOT NULL DEFAULT false;

-- A globally unique, human readable ID for referencing the datachip.
ALTER TABLE datachip
ADD COLUMN IF NOT EXISTS ref TEXT NOT NULL UNIQUE;

-- Add a column to track the type of model used.
DO $$ BEGIN IF to_regtype('MODEL_TYPE') IS NULL THEN CREATE TYPE MODEL_TYPE AS ENUM('base', 'chat');
END IF;
END $$;

ALTER TABLE message
ADD COLUMN IF NOT EXISTS model_type MODEL_TYPE NULL;

ALTER TYPE MODEL_TYPE
ADD VALUE IF NOT EXISTS 'image_prompt';

-- Add delete cascade to below foreign keys so that deleting any rows in parent tables will automatically remove related rows in child tables --
ALTER TABLE message DROP CONSTRAINT IF EXISTS message_completion_fkey;
ALTER TABLE message
ADD CONSTRAINT message_completion_fkey FOREIGN KEY (completion) REFERENCES completion(id) ON DELETE CASCADE;

ALTER TABLE message DROP CONSTRAINT IF EXISTS message_root_fkey;
ALTER TABLE message
ADD CONSTRAINT message_root_fkey FOREIGN KEY (root) REFERENCES message(id) ON DELETE CASCADE;

ALTER TABLE message DROP CONSTRAINT IF EXISTS message_parent_fkey;
ALTER TABLE message
ADD CONSTRAINT message_parent_fkey FOREIGN KEY (parent) REFERENCES message(id) ON DELETE CASCADE;

ALTER TABLE message DROP CONSTRAINT IF EXISTS message_original_fkey;
ALTER TABLE message
ADD CONSTRAINT message_original_fkey FOREIGN KEY (original) REFERENCES message(id) ON DELETE CASCADE;

ALTER TABLE label DROP CONSTRAINT IF EXISTS label_message_fkey;
ALTER TABLE label
ADD CONSTRAINT label_message_fkey FOREIGN KEY (message) REFERENCES message(id) ON DELETE CASCADE;

CREATE TABLE IF NOT EXISTS olmo_user (
  id TEXT NOT NULL PRIMARY KEY,
  -- this might be an email, i.e "sams@allenai.org" or an identifier i.e. "system-x". it may be an oauth ID in the future
  client TEXT NOT NULL,
  terms_accepted_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  -- GDPR requires that consent can be revoked. This field will allow us to track that while still keeping the user around. That may come in handy if we need to delete their data programmatically
  acceptance_revoked_date TIMESTAMPTZ NULL
);
GRANT SELECT,
  UPDATE,
  INSERT ON TABLE olmo_user TO app;
CREATE INDEX IF NOT EXISTS client_idx ON olmo_user(client);

-- Avoid users from creating new prompts to chats that reach the max length limit
ALTER TABLE message
ADD COLUMN IF NOT EXISTS finish_reason TEXT NULL;

-- Add harmful column for storing WildGuard results
ALTER TABLE message
ADD COLUMN IF NOT EXISTS harmful BOOLEAN NULL;

ALTER TABLE message
ADD COLUMN IF NOT EXISTS model_id TEXT NULL;

ALTER TABLE message
ADD COLUMN IF NOT EXISTS model_host TEXT NULL;

UPDATE message
SET model_id = 'unknown'
WHERE model_id IS NULL;

ALTER TABLE message
ALTER COLUMN model_id
SET NOT NULL;

UPDATE message
SET model_host = 'unknown'
WHERE model_host IS NULL;

ALTER TABLE message
ALTER COLUMN model_host
SET NOT NULL;

ALTER TABLE message
ADD COLUMN IF NOT EXISTS expiration_time TIMESTAMPTZ NULL;

ALTER TABLE message
ADD COLUMN IF NOT EXISTS file_urls TEXT ARRAY NULL;

CREATE OR REPLACE VIEW playground_messages AS
select message.id,
  message.content,
  message.creator,
  message.role,
  message.opts,
  message.root,
  message.created,
  message.deleted,
  message.parent,
  message.template,
  message.logprobs,
  message.completion,
  message.final,
  message.original,
  message.private,
  -- BigQuery doesn't like enums so we cast it to text here
  message.model_type::TEXT,
  message.finish_reason,
  message.harmful,
  message.model_id,
  message.model_host,
  message.expiration_time,
  message.file_urls,
  label.rating as label_rating,
  label.creator as label_creator,
  label.comment as label_comment,
  label.created as label_created,
  label.deleted as label_deleted,
  completion.input as completion_input,
  completion.outputs as completion_outputs,
  completion.opts as completion_opts,
  completion.model as completion_model,
  completion.sha as completion_sha,
  completion.created as completion_created,
  completion.tokenize_ms as completion_tokenize_ms,
  completion.generation_ms as completion_generation_ms,
  completion.input_tokens as completion_input_tokens,
  completion.output_tokens as completion_output_tokens
from message
  JOIN olmo_user ON message.creator = olmo_user.client
  LEFT JOIN label ON label.message = message.id
  LEFT JOIN completion on completion.id = message.completion
where message.private != TRUE
  and message.created <= NOW() - '30 days'::INTERVAL
  AND message.model_id != 'mm-olmo-uber-model-v4-synthetic' -- We're waiting for legal to clear any issues with using user-submitted images for training
  AND olmo_user.terms_accepted_date IS NOT NULL
  AND (
    olmo_user.acceptance_revoked_date IS NULL
    OR olmo_user.acceptance_revoked_date::date < olmo_user.terms_accepted_date::date
  );


GRANT SELECT ON TABLE playground_messages TO playground_messages_viewer;

CREATE INDEX IF NOT EXISTS message_root_fkey_ix ON message (root);
CREATE INDEX IF NOT EXISTS message_original_fkey_ix ON message (original);
CREATE INDEX IF NOT EXISTS message_parent_fkey_ix ON message (parent);
CREATE INDEX IF NOT EXISTS message_created_ix ON message (created)
WHERE message.created != NULL;

CREATE OR REPLACE VIEW playground_messages_internal_only AS
select message.id,
  message.content,
  message.creator,
  message.role,
  message.opts,
  message.root,
  message.created,
  message.deleted,
  message.parent,
  message.template,
  message.logprobs,
  message.completion,
  message.final,
  message.original,
  message.private,
  -- BigQuery doesn't like enums so we cast it to text here
  message.model_type::TEXT,
  message.finish_reason,
  message.harmful,
  message.model_id,
  message.model_host,
  message.expiration_time,
  message.file_urls,
  label.rating as label_rating,
  label.creator as label_creator,
  label.comment as label_comment,
  label.created as label_created,
  label.deleted as label_deleted,
  completion.input as completion_input,
  completion.outputs as completion_outputs,
  completion.opts as completion_opts,
  completion.model as completion_model,
  completion.sha as completion_sha,
  completion.created as completion_created,
  completion.tokenize_ms as completion_tokenize_ms,
  completion.generation_ms as completion_generation_ms,
  completion.input_tokens as completion_input_tokens,
  completion.output_tokens as completion_output_tokens
from message
  JOIN olmo_user ON message.creator = olmo_user.client
  LEFT JOIN label ON label.message = message.id
  LEFT JOIN completion on completion.id = message.completion
where message.private != TRUE;

GRANT SELECT ON TABLE playground_messages_internal_only TO playground_messages_viewer;;

INSERT INTO alembic_version (version_num) VALUES ('67c7571bc5b8') RETURNING alembic_version.version_num;

-- Running upgrade 67c7571bc5b8 -> befde9e1de64

CREATE TYPE prompttype AS ENUM ('text_only', 'multi_modal');

CREATE TABLE model_config (
    id VARCHAR NOT NULL, 
    prompt_type prompttype NOT NULL, 
    PRIMARY KEY (id)
);

UPDATE alembic_version SET version_num='befde9e1de64' WHERE alembic_version.version_num = '67c7571bc5b8';

-- Running upgrade befde9e1de64 -> 4d6e17a0fdf6

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE model_config TO app;

UPDATE alembic_version SET version_num='4d6e17a0fdf6' WHERE alembic_version.version_num = 'befde9e1de64';

-- Running upgrade 4d6e17a0fdf6 -> ea686b7953cb

CREATE TYPE modeltype AS ENUM ('Base', 'Chat');

CREATE TYPE modelhost AS ENUM ('InferD', 'Modal');

ALTER TABLE model_config ADD COLUMN host modelhost NOT NULL;

ALTER TABLE model_config ADD COLUMN name VARCHAR NOT NULL;

ALTER TABLE model_config ADD COLUMN description VARCHAR NOT NULL;

ALTER TABLE model_config ADD COLUMN model_type modeltype NOT NULL;

ALTER TABLE model_config ADD COLUMN model_id_on_host VARCHAR NOT NULL;

ALTER TABLE model_config ADD COLUMN default_system_prompt VARCHAR;

ALTER TABLE model_config ADD COLUMN family_id VARCHAR;

ALTER TABLE model_config ADD COLUMN family_name VARCHAR;

ALTER TABLE model_config ADD COLUMN internal BOOLEAN NOT NULL;

UPDATE alembic_version SET version_num='ea686b7953cb' WHERE alembic_version.version_num = '4d6e17a0fdf6';

-- Running upgrade ea686b7953cb -> 636b1b8f1f03

CREATE TYPE filerequiredtopromptoption AS ENUM ('FirstMessage', 'AllMessages', 'NoRequirement');

CREATE TABLE multi_modal_model_config (
    id VARCHAR NOT NULL, 
    accepted_file_types VARCHAR[] NOT NULL, 
    max_files_per_message INTEGER, 
    require_file_to_prompt filerequiredtopromptoption, 
    max_total_file_size INTEGER, 
    allow_files_in_followups BOOLEAN, 
    PRIMARY KEY (id), 
    FOREIGN KEY(id) REFERENCES model_config (id)
);

UPDATE alembic_version SET version_num='636b1b8f1f03' WHERE alembic_version.version_num = 'ea686b7953cb';

-- Running upgrade 636b1b8f1f03 -> f996e9be1bb0

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE multi_modal_model_config TO app;

UPDATE alembic_version SET version_num='f996e9be1bb0' WHERE alembic_version.version_num = '636b1b8f1f03';

-- Running upgrade f996e9be1bb0 -> 03da13313751

ALTER TABLE model_config ADD COLUMN available_time TIMESTAMP WITH TIME ZONE;

ALTER TABLE model_config ADD COLUMN deprecation_time TIMESTAMP WITH TIME ZONE;

UPDATE alembic_version SET version_num='03da13313751' WHERE alembic_version.version_num = 'f996e9be1bb0';

-- Running upgrade 03da13313751 -> c97651b81c1a

ALTER TABLE model_config ADD COLUMN "order" INTEGER NOT NULL;

UPDATE alembic_version SET version_num='c97651b81c1a' WHERE alembic_version.version_num = '03da13313751';

-- Running upgrade c97651b81c1a -> 9089586a14c3

ALTER TYPE "public"."prompttype" RENAME TO prompttype_old;

CREATE TYPE "public"."prompttype" AS ENUM('TEXT_ONLY', 'MULTI_MODAL');

CREATE FUNCTION new_old_not_equals(
                new_enum_val "public"."prompttype", old_enum_val "public"."prompttype_old"
            )
            RETURNS boolean AS $$
                SELECT new_enum_val::text != old_enum_val::text;
            $$ LANGUAGE SQL IMMUTABLE;

CREATE OPERATOR != (
            leftarg = "public"."prompttype",
            rightarg = "public"."prompttype_old",
            procedure = new_old_not_equals
        );

CREATE FUNCTION new_old_equals(
                new_enum_val "public"."prompttype", old_enum_val "public"."prompttype_old"
            )
            RETURNS boolean AS $$
                SELECT new_enum_val::text = old_enum_val::text;
            $$ LANGUAGE SQL IMMUTABLE;

CREATE OPERATOR = (
            leftarg = "public"."prompttype",
            rightarg = "public"."prompttype_old",
            procedure = new_old_equals
        );

ALTER TABLE "public"."model_config" 
                ALTER COLUMN "prompt_type" TYPE "public"."prompttype" 
                USING "prompt_type"::text::"public"."prompttype";

DROP FUNCTION new_old_not_equals(
            new_enum_val "public"."prompttype", old_enum_val "public"."prompttype_old"
        ) CASCADE;

DROP FUNCTION new_old_equals(
            new_enum_val "public"."prompttype", old_enum_val "public"."prompttype_old"
        ) CASCADE;

DROP TYPE "public"."prompttype_old";

UPDATE alembic_version SET version_num='9089586a14c3' WHERE alembic_version.version_num = 'c97651b81c1a';

-- Running upgrade 9089586a14c3 -> 724dff1a0068

ALTER TABLE model_config ADD COLUMN created_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;

ALTER TABLE model_config ADD COLUMN updated_time TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;

UPDATE alembic_version SET version_num='724dff1a0068' WHERE alembic_version.version_num = '9089586a14c3';

-- Running upgrade 724dff1a0068 -> 3772048c8bd0

CREATE SEQUENCE model_config_order_seq INCREMENT BY 10 START WITH 10 OWNED BY model_config.order;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app;

ALTER TABLE model_config ALTER COLUMN "order" SET DEFAULT nextval('model_config_order_seq');

UPDATE alembic_version SET version_num='3772048c8bd0' WHERE alembic_version.version_num = '724dff1a0068';

-- Running upgrade 3772048c8bd0 -> c26ec1a12f09

ALTER TYPE "public"."modelhost" RENAME TO modelhost_old;

CREATE TYPE "public"."modelhost" AS ENUM('InferD', 'Modal', 'BeakerQueue');

CREATE FUNCTION new_old_not_equals(
                new_enum_val "public"."modelhost", old_enum_val "public"."modelhost_old"
            )
            RETURNS boolean AS $$
                SELECT new_enum_val::text != old_enum_val::text;
            $$ LANGUAGE SQL IMMUTABLE;

CREATE OPERATOR != (
            leftarg = "public"."modelhost",
            rightarg = "public"."modelhost_old",
            procedure = new_old_not_equals
        );

CREATE FUNCTION new_old_equals(
                new_enum_val "public"."modelhost", old_enum_val "public"."modelhost_old"
            )
            RETURNS boolean AS $$
                SELECT new_enum_val::text = old_enum_val::text;
            $$ LANGUAGE SQL IMMUTABLE;

CREATE OPERATOR = (
            leftarg = "public"."modelhost",
            rightarg = "public"."modelhost_old",
            procedure = new_old_equals
        );

ALTER TABLE "public"."model_config" 
                ALTER COLUMN "host" TYPE "public"."modelhost" 
                USING "host"::text::"public"."modelhost";

DROP FUNCTION new_old_not_equals(
            new_enum_val "public"."modelhost", old_enum_val "public"."modelhost_old"
        ) CASCADE;

DROP FUNCTION new_old_equals(
            new_enum_val "public"."modelhost", old_enum_val "public"."modelhost_old"
        ) CASCADE;

DROP TYPE "public"."modelhost_old";

UPDATE alembic_version SET version_num='c26ec1a12f09' WHERE alembic_version.version_num = '3772048c8bd0';

-- Running upgrade c26ec1a12f09 -> fae16d8f38d0

ALTER TYPE "public"."modelhost" RENAME TO modelhost_old;

CREATE TYPE "public"."modelhost" AS ENUM('InferD', 'Modal', 'BeakerQueues');

CREATE FUNCTION new_old_not_equals(
                new_enum_val "public"."modelhost", old_enum_val "public"."modelhost_old"
            )
            RETURNS boolean AS $$
                SELECT new_enum_val::text != old_enum_val::text;
            $$ LANGUAGE SQL IMMUTABLE;

CREATE OPERATOR != (
            leftarg = "public"."modelhost",
            rightarg = "public"."modelhost_old",
            procedure = new_old_not_equals
        );

CREATE FUNCTION new_old_equals(
                new_enum_val "public"."modelhost", old_enum_val "public"."modelhost_old"
            )
            RETURNS boolean AS $$
                SELECT new_enum_val::text = old_enum_val::text;
            $$ LANGUAGE SQL IMMUTABLE;

CREATE OPERATOR = (
            leftarg = "public"."modelhost",
            rightarg = "public"."modelhost_old",
            procedure = new_old_equals
        );

ALTER TABLE "public"."model_config" 
                ALTER COLUMN "host" TYPE "public"."modelhost" 
                USING "host"::text::"public"."modelhost";

DROP FUNCTION new_old_not_equals(
            new_enum_val "public"."modelhost", old_enum_val "public"."modelhost_old"
        ) CASCADE;

DROP FUNCTION new_old_equals(
            new_enum_val "public"."modelhost", old_enum_val "public"."modelhost_old"
        ) CASCADE;

DROP TYPE "public"."modelhost_old";

UPDATE alembic_version SET version_num='fae16d8f38d0' WHERE alembic_version.version_num = 'c26ec1a12f09';

-- Running upgrade fae16d8f38d0 -> 93d6e3c1967d

ALTER TYPE "public"."prompttype" RENAME TO prompttype_old;

CREATE TYPE "public"."prompttype" AS ENUM('TEXT_ONLY', 'MULTI_MODAL', 'FILES_ONLY');

CREATE FUNCTION new_old_not_equals(
                new_enum_val "public"."prompttype", old_enum_val "public"."prompttype_old"
            )
            RETURNS boolean AS $$
                SELECT new_enum_val::text != old_enum_val::text;
            $$ LANGUAGE SQL IMMUTABLE;

CREATE OPERATOR != (
            leftarg = "public"."prompttype",
            rightarg = "public"."prompttype_old",
            procedure = new_old_not_equals
        );

CREATE FUNCTION new_old_equals(
                new_enum_val "public"."prompttype", old_enum_val "public"."prompttype_old"
            )
            RETURNS boolean AS $$
                SELECT new_enum_val::text = old_enum_val::text;
            $$ LANGUAGE SQL IMMUTABLE;

CREATE OPERATOR = (
            leftarg = "public"."prompttype",
            rightarg = "public"."prompttype_old",
            procedure = new_old_equals
        );

ALTER TABLE "public"."model_config" 
                ALTER COLUMN "prompt_type" TYPE "public"."prompttype" 
                USING "prompt_type"::text::"public"."prompttype";

DROP FUNCTION new_old_not_equals(
            new_enum_val "public"."prompttype", old_enum_val "public"."prompttype_old"
        ) CASCADE;

DROP FUNCTION new_old_equals(
            new_enum_val "public"."prompttype", old_enum_val "public"."prompttype_old"
        ) CASCADE;

DROP TYPE "public"."prompttype_old";

UPDATE alembic_version SET version_num='93d6e3c1967d' WHERE alembic_version.version_num = 'fae16d8f38d0';

-- Running upgrade 93d6e3c1967d -> b85b60aa5479

ALTER TYPE "public"."modelhost" RENAME TO modelhost_old;

CREATE TYPE "public"."modelhost" AS ENUM('InferD', 'Modal', 'BeakerQueues', 'CirrascaleBackend');

CREATE FUNCTION new_old_not_equals(
                new_enum_val "public"."modelhost", old_enum_val "public"."modelhost_old"
            )
            RETURNS boolean AS $$
                SELECT new_enum_val::text != old_enum_val::text;
            $$ LANGUAGE SQL IMMUTABLE;

CREATE OPERATOR != (
            leftarg = "public"."modelhost",
            rightarg = "public"."modelhost_old",
            procedure = new_old_not_equals
        );

CREATE FUNCTION new_old_equals(
                new_enum_val "public"."modelhost", old_enum_val "public"."modelhost_old"
            )
            RETURNS boolean AS $$
                SELECT new_enum_val::text = old_enum_val::text;
            $$ LANGUAGE SQL IMMUTABLE;

CREATE OPERATOR = (
            leftarg = "public"."modelhost",
            rightarg = "public"."modelhost_old",
            procedure = new_old_equals
        );

ALTER TABLE "public"."model_config" 
                ALTER COLUMN "host" TYPE "public"."modelhost" 
                USING "host"::text::"public"."modelhost";

DROP FUNCTION new_old_not_equals(
            new_enum_val "public"."modelhost", old_enum_val "public"."modelhost_old"
        ) CASCADE;

DROP FUNCTION new_old_equals(
            new_enum_val "public"."modelhost", old_enum_val "public"."modelhost_old"
        ) CASCADE;

DROP TYPE "public"."modelhost_old";

UPDATE alembic_version SET version_num='b85b60aa5479' WHERE alembic_version.version_num = '93d6e3c1967d';

-- Running upgrade b85b60aa5479 -> c44d4eee37f6

ALTER TABLE olmo_user ADD COLUMN data_collection_accepted_date TIMESTAMP WITH TIME ZONE;

ALTER TABLE olmo_user ADD COLUMN data_collection_acceptance_revoked_date TIMESTAMP WITH TIME ZONE;

COMMENT ON COLUMN olmo_user.data_collection_acceptance_revoked_date IS 'GDPR requires that consent can be revoked. This field will allow us to track that while still keeping the user around. That may come in handy if we need to delete their data programmatically.';

UPDATE alembic_version SET version_num='c44d4eee37f6' WHERE alembic_version.version_num = 'b85b60aa5479';

-- Running upgrade c44d4eee37f6 -> f34d2db4d75d

ALTER TABLE model_config ADD COLUMN can_call_tools BOOLEAN DEFAULT 'false' NOT NULL;

UPDATE alembic_version SET version_num='f34d2db4d75d' WHERE alembic_version.version_num = 'c44d4eee37f6';

-- Running upgrade f34d2db4d75d -> 17a551c5bc64

ALTER TYPE "public"."modelhost" RENAME TO modelhost_old;

CREATE TYPE "public"."modelhost" AS ENUM('InferD', 'Modal', 'BeakerQueues', 'CirrascaleBackend', 'Cirrascale', 'ModalOpenAI');

CREATE FUNCTION new_old_not_equals(
                new_enum_val "public"."modelhost", old_enum_val "public"."modelhost_old"
            )
            RETURNS boolean AS $$
                SELECT new_enum_val::text != old_enum_val::text;
            $$ LANGUAGE SQL IMMUTABLE;

CREATE OPERATOR != (
            leftarg = "public"."modelhost",
            rightarg = "public"."modelhost_old",
            procedure = new_old_not_equals
        );

CREATE FUNCTION new_old_equals(
                new_enum_val "public"."modelhost", old_enum_val "public"."modelhost_old"
            )
            RETURNS boolean AS $$
                SELECT new_enum_val::text = old_enum_val::text;
            $$ LANGUAGE SQL IMMUTABLE;

CREATE OPERATOR = (
            leftarg = "public"."modelhost",
            rightarg = "public"."modelhost_old",
            procedure = new_old_equals
        );

ALTER TABLE "public"."model_config" 
                ALTER COLUMN "host" TYPE "public"."modelhost" 
                USING "host"::text::"public"."modelhost";

DROP FUNCTION new_old_not_equals(
            new_enum_val "public"."modelhost", old_enum_val "public"."modelhost_old"
        ) CASCADE;

DROP FUNCTION new_old_equals(
            new_enum_val "public"."modelhost", old_enum_val "public"."modelhost_old"
        ) CASCADE;

DROP TYPE "public"."modelhost_old";

UPDATE alembic_version SET version_num='17a551c5bc64' WHERE alembic_version.version_num = 'f34d2db4d75d';

-- Running upgrade 17a551c5bc64 -> 97428846ee1e

ALTER TYPE "public"."modelhost" RENAME TO modelhost_old;

CREATE TYPE "public"."modelhost" AS ENUM('InferD', 'Modal', 'BeakerQueues', 'CirrascaleBackend', 'Cirrascale', 'ModalOpenAI', 'TestBackend');

CREATE FUNCTION new_old_not_equals(
                new_enum_val "public"."modelhost", old_enum_val "public"."modelhost_old"
            )
            RETURNS boolean AS $$
                SELECT new_enum_val::text != old_enum_val::text;
            $$ LANGUAGE SQL IMMUTABLE;

CREATE OPERATOR != (
            leftarg = "public"."modelhost",
            rightarg = "public"."modelhost_old",
            procedure = new_old_not_equals
        );

CREATE FUNCTION new_old_equals(
                new_enum_val "public"."modelhost", old_enum_val "public"."modelhost_old"
            )
            RETURNS boolean AS $$
                SELECT new_enum_val::text = old_enum_val::text;
            $$ LANGUAGE SQL IMMUTABLE;

CREATE OPERATOR = (
            leftarg = "public"."modelhost",
            rightarg = "public"."modelhost_old",
            procedure = new_old_equals
        );

ALTER TABLE "public"."model_config" 
                ALTER COLUMN "host" TYPE "public"."modelhost" 
                USING "host"::text::"public"."modelhost";

DROP FUNCTION new_old_not_equals(
            new_enum_val "public"."modelhost", old_enum_val "public"."modelhost_old"
        ) CASCADE;

DROP FUNCTION new_old_equals(
            new_enum_val "public"."modelhost", old_enum_val "public"."modelhost_old"
        ) CASCADE;

DROP TYPE "public"."modelhost_old";

UPDATE alembic_version SET version_num='97428846ee1e' WHERE alembic_version.version_num = '17a551c5bc64';

-- Running upgrade 97428846ee1e -> ba2462b3122c

ALTER TABLE message ADD COLUMN thinking VARCHAR;

ALTER TABLE message ADD COLUMN tool_calls JSON[];

UPDATE alembic_version SET version_num='ba2462b3122c' WHERE alembic_version.version_num = '97428846ee1e';

-- Running upgrade ba2462b3122c -> 51ded224eed6

ALTER TABLE message ALTER COLUMN tool_calls TYPE JSONB[];

UPDATE alembic_version SET version_num='51ded224eed6' WHERE alembic_version.version_num = 'ba2462b3122c';

-- Running upgrade 51ded224eed6 -> a48c549f771e

ALTER TABLE model_config ADD COLUMN can_think BOOLEAN DEFAULT 'false' NOT NULL;

UPDATE alembic_version SET version_num='a48c549f771e' WHERE alembic_version.version_num = '51ded224eed6';
-- Running upgrade 51ded224eed6 -> 87f54c8af836

-- TODO fix order of upgrades
CREATE TABLE tool_call (
    tool_call_id VARCHAR NOT NULL, 
    tool_name VARCHAR NOT NULL, 
    args JSONB, 
    message_id TEXT NOT NULL, 
    PRIMARY KEY (tool_call_id), 
    FOREIGN KEY(message_id) REFERENCES message (id)
);

ALTER TABLE message DROP COLUMN tool_calls;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE tool_call TO app;

UPDATE alembic_version SET version_num='87f54c8af836' WHERE alembic_version.version_num = '51ded224eed6';

COMMIT;

