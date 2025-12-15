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

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'Write a haiku about summer',
    'paul',
    NULL,
    NULL,
    'p_tpl_haiku',
    'Chat',
    'Write a haiku',
    '{"temperature":"0.5"}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'Count the boats in the images',
    'paull',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/Stock_278013497.jpeg","https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/Stock_278013638.jpeg"}',
    'images_counting_1',
    'Chat',
    'Count boats in multiple images',
    '{"temperature":0}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'Describe this image',
    'jieyu',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/msg_D2G4Q8S4O8-0.jpg"}',
    'images_dense_captioning_1',
    'Chat',
    'Caption an image',
    '{}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'Point at the boats',
    'paul',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/msg_D1V5J6C3M4-0.png"}',
    'image_pointing_1',
    'Chat',
    'Point at boats in an image',
    '{}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'How many penguins are there?',
    'zixian',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/msg_C8Q0P0C2R9-0.mp4"}',
    'video_counting_1',
    'Chat',
    'Count penguins in a video',
    '{"temperature":0}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'How many times does the player shoot?',
    'zixian',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/msg_K7O4L1E6S7-0.mp4"}',
    'video_counting_2',
    'Chat',
    'Count shots taken in soccer video',
    '{"temperature":0}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'How many waterfalls are there?',
    'zixian',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/msg_O0J1T3B1S9-0.mp4"}',
    'video_counting_3',
    'Chat',
    'Count the waterfalls in a video',
    '{"temperature":0}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'Count the backflips in this clip',
    'caleb',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/girl_doing_backflip.mov"}',
    'backflip_count',
    'Chat',
    'Count the backflips in a video clip',
    '{"temperature":0}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'Can you describe what is happening in detail?',
    'david',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/pie.mov"}',
    'video_dense_captioning_5',
    'Chat',
    'Caption a recipe video',
    '{"temperature":0}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'Describe this video',
    'jieyu',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/msg_R9M5L9J1W1-0.mp4"}',
    'video_dense_captioning_2',
    'Chat',
    'Caption a recipe video',
    '{}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'Point out visual artifacts in video',
    'zixian',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/msg_E1K0E1H1N8-0.mp4"}',
    'video_pointing_1',
    'Chat',
    'Pointing at visual artifacts in a video',
    '{"temperature":0}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'What game is this?',
    'zixian',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/msg_L1N9E2T2Q3-0.mp4"}',
    'video_qa_1',
    'Chat',
    'Identify the sport played in a video',
    '{"temperature":0}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'Who is the woman with purple highlights?',
    'zixian',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/msg_V1K2L9A8H5-0.mp4"}',
    'video_qa_2',
    'Chat',
    'Get the name of a person in a video',
    '{"temperature":0}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'What makes this video funny?',
    'zixian',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/msg_T9C1E1O9T5-0.mp4"}',
    'video_qa_3',
    'Chat',
    'Get a summary of a video essay',
    '{"temperature":0}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'Track the horses',
    'jae sung park',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/msg_J5U2N1C9P0-0.mov"}',
    'video_tracking_1',
    'Chat',
    'Track horses in a horse race video',
    '{"temperature":0}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'Track the car turning to the right',
    'jae sung park',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/msg_R8W2K3Z3D5-0.mp4"}',
    'video_tracking_2',
    'Chat',
    'Track cars in traffic video',
    '{"temperature":0}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'Track players in yellow jersey',
    'jae sung park',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/msg_M6W7G6Y2C8-0.mp4"}',
    'video_tracking_3',
    'Chat',
    'Track players in basketball game video',
    '{"temperature":0}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'Track the penguins',
    'caleb',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/penguins.mov"}',
    'video_tracking_4',
    'Chat',
    'Track multiple penguins in a video',
    '{"temperature":0}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'Track the orange toy that slides in from the left towards the beginning of the clip',
    'caleb',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/slow-cat.mp4"}',
    'video_tracking_5',
    'Chat',
    'Track the orange cat toy in a video',
    '{"temperature":0}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'Track the car with the number 36',
    'caleb',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/stock_car_race.mov"}',
    'video_tracking_6',
    'Chat',
    'Track the race cars in a video',
    '{"temperature":0}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'Track the players',
    'caleb',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/pickup_basketball.mov"}',
    'video_tracking_7',
    'Chat',
    'Track the players in a basketball game video',
    '{"temperature":0}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'Track the dogs',
    'caleb',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/husky_dogs_playing.mov"}',
    'video_tracking_8',
    'Chat',
    'Track the dogs in a video',
    '{"temperature":0}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'Track the skier in this clip',
    'caleb',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/skiier-clip.mp4"}',
    'skier_track',
    'Chat',
    'Follow the skier in a video clip',
    '{"temperature":0}'
) ON CONFLICT DO NOTHING;

INSERT INTO prompt_template (
    content,
    creator,
    extra_parameters,
    file_urls,
    id,
    model_type,
    name,
    opts
) VALUES (
    'Describe this video',
    'jieyu',
    NULL,
    '{"https://storage.googleapis.com/ai2-playground-molmo/promptTemplates/msg_E6D1C5V2F5-0.mp4"}',
    'video_dense_captioning_1',
    'Chat',
    'Caption an ocean video',
    '{}'
) ON CONFLICT DO NOTHING;

