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
        'olmo-2-0325-32b-instruct',
        'OLMo 2 32B Instruct',
        'Ai2''s 32B model using the OLMo2 architecture.',
        'OLMo-2-0325-32B-Instruct-COMBO',
        'Chat',
        'You are OLMo 2 Instruct, a helpful, open-source AI Assistant built by the Allen Institute for AI.',
        'olmo',
        'OLMo',
        'Modal',
        'TEXT_ONLY',
        false
    );

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
    );

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
    );

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
    );



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
        'olmoasr',
        'Base',
        NULL,
        NULL,
        NULL,
        'Modal',
        'FILES_ONLY',
        true
    );

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
    );