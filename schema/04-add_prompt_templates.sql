insert into prompt_template (
    id,
    name,
    content,
    creator,
    opts,
    model_type,
    file_urls,
    extra_parameters
) values (
    'p_tpl_12345',
    'test prompt template',
    'Tell me about lions',
    'taylor',
    '{}',
    'Chat',
    NULL,
    NULL
)