INSERT INTO model_config(
        id,
        name,
        description,
        model_id_on_host,
        model_type,
        default_system_prompt,
        family_id,
        family_name,
        host,
        prompt_type,
        internal
    )
VALUES (
        'cs-OLMo-2-0325-32B-Instruct',
        'OLMo 2 32B Instruct',
        'Ai2''s 32B model using the OLMo2 architecture.',
        '22504',
        'Chat',
        'You are OLMo 2 Instruct, a helpful, open-source AI Assistant built by the Allen Institute for AI.',
        'olmo',
        'OLMo',
        'CirrascaleBackend',
        'TEXT_ONLY',
        false
    ) ON CONFLICT DO
UPDATE;

INSERT INTO model_config(
        id,
        name,
        description,
        model_id_on_host,
        model_type,
        default_system_prompt,
        family_id,
        family_name,
        host,
        prompt_type,
        internal
    )
VALUES (
        'tulu3-405b',
        'Llama Tülu 3 405B',
        'A 405B parameter model that is a fine-tuned version of Llama 2.',
        'csc_01jjqp4s2x3hq6e05j3a0h3f96',
        'Chat',
        NULL,
        'tulu',
        'Tülu',
        'InferD',
        'TEXT_ONLY',
        false
    ) ON CONFLICT DO
UPDATE;

INSERT INTO model_config(
        id,
        name,
        description,
        model_id_on_host,
        model_type,
        default_system_prompt,
        family_id,
        family_name,
        host,
        prompt_type,
        internal
    )
VALUES (
        'mm-olmo-uber-model-v4-synthetic',
        'Molmo',
        'Molmo',
        'mm-olmo-uber-model-v4-synthetic',
        'Chat',
        NULL,
        'molmo',
        'Molmo',
        'Modal',
        'MULTI_MODAL',
        false
    ) ON CONFLICT DO
UPDATE;

INSERT INTO multi_modal_model_config(
        id,
        accepted_file_types,
        max_files_per_message,
        require_file_to_prompt,
        allow_files_in_followups
    )
VALUES (
        'mm-olmo-uber-model-v4-synthetic',
        '{ "image/*" }',
        1,
        'FirstMessage',
        'false'
    ) ON CONFLICT DO
UPDATE;



INSERT INTO model_config(
        id,
        name,
        description,
        model_id_on_host,
        model_type,
        default_system_prompt,
        family_id,
        family_name,
        host,
        prompt_type,
        internal
    )
VALUES (
        'olmoasr',
        'OLMoASR',
        'OLMoASR',
        'olmoasr_769m',
        'Base',
        NULL,
        NULL,
        NULL,
        'Modal',
        'FILES_ONLY',
        true
    ) ON CONFLICT DO
UPDATE;

INSERT INTO multi_modal_model_config(
        id,
        accepted_file_types,
        max_files_per_message,
        require_file_to_prompt,
        allow_files_in_followups
    )
VALUES (
        'olmoasr',
        '{ "audio/webm", "audio/mp4", "audio/ogg", "audio/wav" }',
        1,
        'AllMessages',
        'false'
    ) ON CONFLICT DO
UPDATE;

INSERT INTO model_config(
        id,
        name,
        description,
        model_id_on_host,
        model_type,
        default_system_prompt,
        family_id,
        family_name,
        host,
        prompt_type,
        internal,
        can_call_tools
    )
VALUES (
        'qwen3-openai',
        'Qwen3',
        'Qwen3 hosted to test thinking and tool calls',
        'https://ai2-reviz--qwen3-openai-serve.modal.run/v1',
        'Chat',
        NULL,
        NULL,
        NULL,
        'ModalOpenAI',
        'TEXT_ONLY',
        true,
        true
    ) ON CONFLICT DO
UPDATE;

INSERT INTO model_config(
        id,
        name,
        description,
        model_id_on_host,
        model_type,
        default_system_prompt,
        family_id,
        family_name,
        host,
        prompt_type,
        internal,
        can_call_tools
    )
VALUES (
        'test-model',
        'Test Model',
        'A fake model to test with',
        'foo',
        'Chat',
        'You are a fake model used for testing',
        NULL,
        NULL,
        'TestBackend',
        'TEXT_ONLY',
        true,
        true
    ) ON CONFLICT DO
UPDATE;


INSERT INTO model_config(
        id,
        name,
        description,
        model_id_on_host,
        model_type,
        default_system_prompt,
        family_id,
        family_name,
        host,
        prompt_type,
        internal,
        can_call_tools
    )
VALUES (
        'test-model-no-tools',
        'Test Model No Tools',
        'A fake model to test with. (no tools)',
        'foo',
        'Chat',
        'You are a fake model used for testing',
        NULL,
        NULL,
        'TestBackend',
        'TEXT_ONLY',
        true,
        false
    ) ON CONFLICT DO
UPDATE;