INSERT INTO prompt_template (
    id,
    name,
    content,
    creator,
    opts,
    model_type,
    file_urls,
    extra_parameters
) VALUES (
    'p_tpl_12345',
    'test prompt template',
    'Tell me about lions',
    'taylor',
    '{}',
    'Chat',
    NULL,
    NULL
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    id,
    name,
    content,
    creator,
    opts,
    model_type,
    file_urls,
    extra_parameters
) VALUES (
    'p_tpl_tool_definitions',
    'prompt template with tool definitions',
    'Tell me the weather',
    'taylor',
    '{}',
    'Chat',
    NULL,
    NULL
) ON CONFLICT DO NOTHING;

INSERT INTO tool_definition (
    id,
    name,
    description,
    parameters,
    tool_source
) VALUES (
    'td_template_tool',
    'get_weather',
    'Get the current weather in a given location',
    ('{"type": "object","default": null,"required": ["location"],"properties": {"location": {"type": "string","default": {"string_value": "Boston, MA"},"required": [],"properties": null,"description": "The city name of the location for which to get the weather.","propertyOrdering": null}},"description": null,"propertyOrdering": null}'),
    'USER_DEFINED'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template_tool_definition_association (
    prompt_template_id,
    tool_definition_id
) VALUES (
    'p_tpl_tool_definitions',
    'td_template_tool'
) ON CONFLICT DO NOTHING;