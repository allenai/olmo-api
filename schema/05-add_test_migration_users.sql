-- Test data for user migration e2e tests
-- Creates two test users (one anonymous, one authenticated) each with two messages

-- Insert anonymous test user
INSERT INTO olmo_user (
    id,
    client,
    terms_accepted_date,
    acceptance_revoked_date
) VALUES (
    'test_anon_user_id',
    'test_anonymous_user_client',
    '2023-01-01T00:00:00Z',
    NULL
) ON CONFLICT (id) DO UPDATE SET
    client = EXCLUDED.client,
    terms_accepted_date = EXCLUDED.terms_accepted_date;

-- Insert messages for anonymous user
INSERT INTO message (
    id,
    content,
    creator,
    role,
    opts,
    root,
    parent,
    final,
    private,
    model_id,
    model_host,
    created
) VALUES (
    'msg_anon_root_001',
    'Anonymous user test message 1',
    'test_anonymous_user_client',
    'user',
    '{}',
    'msg_anon_root_001',
    NULL,
    true,
    false,
    'test-model',
    'TestBackend',
    '2023-01-01T10:00:00Z'
) ON CONFLICT (id) DO UPDATE SET
    content = EXCLUDED.content,
    creator = EXCLUDED.creator;

INSERT INTO message (
    id,
    content,
    creator,
    role,
    opts,
    root,
    parent,
    final,
    private,
    model_id,
    model_host,
    created
) VALUES (
    'msg_anon_child_001',
    'Anonymous user test message 2',
    'test_anonymous_user_client',
    'assistant',
    '{}',
    'msg_anon_root_001',
    'msg_anon_root_001',
    true,
    false,
    'test-model',
    'TestBackend',
    '2023-01-01T10:01:00Z'
) ON CONFLICT (id) DO UPDATE SET
    content = EXCLUDED.content,
    creator = EXCLUDED.creator;
