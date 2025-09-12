# Model Configuration


## Adding models
1. Get the model name.
    - If you're getting this yourself and it's hosted on Modal, you can check the [reviz-modal repo](https://github.com/allenai/reviz-modal)'s `src` folder. Find the `.py` file with the model and version you want to serve, then find the `MODEL_NAME` variable in the file. That will be the value we use for this.
2. Add an entry to the local `config.json`'s `models` section
    - The placement in the `models` array will determine the model's position in the UI dropdown. The first entry will be first, etc.
    - The `id` and `compute_source_id` should be the model name you got in the earlier step.
    - the `name` should be a human-readable, nicely formatted name. It will be shown on the UI.
    - the `description` should be a sentence about what the model is.
    - the `information_url` is optional, but if provided it should be a URL where users can learn more about the model.
    - example (the model name is `Tulu-v3-8-dpo-preview` here):
        ```
        {
            "id": "Tulu-v3-8-dpo-preview",
            "name": "Tulu v3 Preview",
            "description": "A preview version of Ai2's latest Tulu model",
            "information_url": "https://allenai.org/blog/tulu",
            "compute_source_id": "Tulu-v3-8-dpo-preview",
            "model_type": "chat"
        }
        ```
3. Test this by changing your local `config.json` to ensure the values are correct. Send a message to the model you've added. If it doesn't work, make sure the model name you got is correct.
4. Copy the new model config to the [olmo-api config for this in Marina](https://marina.apps.allenai.org/a/olmo-api/s/cfg/update)

## Setting an available time
To automatically make a model available at a certain time, set the `available_time` field to the desired time. This should be an ISO8601 timestamp, ideally in the UTC time zone. 

Example: `"available_time": "2025-03-07T20:53:19.073Z"`

## Setting a deprecation time
To automatically remove a model from the UI at a certain time, set the `deprecation_time` field to the desired time. This should be an ISO8601 timestamp, ideally in the UTC time zone. 

Example: `"deprecation_time": "2025-03-07T20:53:19.073Z"`

## Configuring multi-modal models
Multi-modal models have some extra configuration you can use to enforce restrictions around uploading files.

Here are the configurations available for multi-modal models:

| Property                   | Default          | Description                                                                                                                                                                                           |
|----------------------------|------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `accepts_files`              | `false`          | This determines if a model is multi-modal. Set it to `true` if it's a multi-modal model!                                                                                                              |
| `accepted_file_types`      | `[]`             | A list of [file type specifiers](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/file#unique_file_type_specifiers). This determines what kinds of file a user can send to this model. |
| `max_files_per_message`    | `undefined`      | The maximum number of files the user is allowed to send with a message.                                                                                                                               |
| `require_file_to_prompt`   | `no_requirement` | Defines if a user is required to send files with messages. Doesn't prevent users from sending files.                                                                                                  |
| `max_total_file_size`      | `undefined`      | The maximum total file size a user is allowed to send. Adds up the size of every file.                                                                                                                |
| `allow_files_in_followups` | `false`          | Defines if a user is allowed to send files with follow-up prompts.                                                                                                                                    |