-- Initialize things locally that aren't relevant in production.
CREATE ROLE app LOGIN PASSWORD 'llmz';

CREATE USER bigquery_user with password 'llmz';
CREATE ROLE playground_messages_viewer;
GRANT playground_messages_viewer to app,
    bigquery_user;