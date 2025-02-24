

<!-- toc -->

- [OpenAI Assistant Runner & Manager](#openai-assistant-runner--manager)
  * [What is OpenAI Assistant](#what-is-openai-assistant)
  * [Why using Assistant](#why-using-assistant)
  * [General pattern](#general-pattern)
  * [Code organization](#code-organization)
  * [How to use](#how-to-use)
    + [Assistant Manager](#assistant-manager)
    + [Running Assistant](#running-assistant)
- [API library](#api-library)
  * [Usage](#usage)
    + [File Structure](#file-structure)
    + [Uploading and Retrieving Files](#uploading-and-retrieving-files)
    + [Managing Assistants](#managing-assistants)
    + [ChatGPT Communication](#chatgpt-communication)
    + [E2E Assistant Runner](#e2e-assistant-runner)

<!-- tocstop -->

# OpenAI Assistant Runner & Manager

## What is OpenAI Assistant

- An assistant is pretty much similar to a modified GPT that has mastered some
  knowledge and will always be able to use them
- The official OpenAI documentation is at
  https://platform.openai.com/docs/assistants/overview

## Why using Assistant

- Normally you "chat" with ChatGPT, that means anything you send to it is
  treated as input
- But GPT forget things really fast: it will forget what you previously said or
  files uploaded, as the total length of the conversation grows
- By creating an Assistant, you build a new "instance" of ChatGPT and can give
  it some knowledge to learn
- These knowledge can be with many formats, and up to 20 files (512MB each) at a
  time
- With an instruction string, you define its behavior about how it should make
  use of those knowledge
- When talking to an assistant, you can still add files in the message
- These files does not count towards its 20 files' knowledge limit, as they are
  considered as input, and will be forgotten eventually

## General pattern

- Creation:
  - Send some `guideline or example files` for one type of task to the Assistant
    itself as knowledge
  - Send an instruction about how it should deal with tasks using those
    knowledge
- Running:
  - Whenever a specific task comes, send `the task and its data files` in the
    message as input
  - Let the assistant solve the task based on the knowledge it learned
  - It will forget everything in this task, and be ready for the next task like
    this one never happens
- Chatting:
  - You can continue the conversation if you are not satisfied with its reply
  - Chatting is not yet implemented in our code, since command line scripts
    cannot save conversations.

## Code organization

- Libraries are under `helpers`, e.g.,
  - `helpers/hchatgpt.py`
  - `helpers/hchatgpt_instructions.py`

- Scripts are under `dev_scripts/chatgpt`, e.g.,
  - `dev_scripts/chatgpt/manage_chatgpt_assistant.py`
  - `dev_scripts/chatgpt/run_chatgpt.py`

- Documentaiton is
  - `docs/work_tools/all.chatgpt_api.how_to_guide.md`

## How to use
```
> export OPENAI_API_KEY=<your secret key>
```

- Each API key can be bound to an OpenAI Organization. A key belongs to our Org
  is needed to start
- Assistants are organization-wide, an assistant created under our Org can be
  accessed by any API key that belongs to our Org
- Play safely: do not call update/delete methods if it's not necessary

### Assistant Manager

- To get help

  ```bash
  > manage_chatgpt_assistant.py -h
  Manage the ChatGPT Assistants in our OpenAI Organization

  optional arguments:
    -h, --help            show this help message and exit
    --create CREATE_NAME  Name of the assistant to be created
    --edit EDIT_NAME      Name of the assistant to be edited
    --delete DELETE_NAME  Name of the assistant to be deleted, will ignore all other arguments
    --new_name NEW_NAME   New name for the assistant, only used in -e
    --model MODEL         Model used by the assistant
    --instruction_name INSTRUCTION_NAME
                          Name of the instruction for the assistant, as shown in helpers.hchatgpt_instructions
    --input_files [INPUT_FILE_PATHS ...]
                          Files needed for the assistant, use relative path from project root
    --retrieval_tool, --no-retrieval_tool
                          Enable the retrieval tool. Use --no-r to disable
    --code_tool, --no-code_tool
                          Enable the code_interpreter tool. Use --no-c to disable
    --function FUNCTION   Apply certain function tool to the assistant, not implemented yet
    -v {TRACE,DEBUG,INFO,WARNING,ERROR,CRITICAL}
                          Set the logging level
  ```

- Use this script to create, modify, or delete an assistant in our Org
- A set of instructions are in `helpers/hchatgpt_instructions.py`
- Feel free to add more instructions for different tasks here
- For better understanding, the name of an assistant created should be related
  to its instruction name

- E.g., create a doc writer assistant with name `DocWriter-1` and use
  `instruction=DocWriter` from `helpers/hchatgpt_instructions.py`
  ```bash
  > manage_chatgpt_assistant.py \
      --create DocWriter-1 \
      --model "gpt-4-1106-preview" \
      --instruction_name DocWriter \
      --input_files docs/work_tools/all.bfg_repo_cleaner.how_to_guide.md docs/marketing/dropcontact.how_to_guide.md docs/coding/all.hplayback.how_to_guide.md \
      --retrieval_tool --code_tool
  ```

### Running Assistant

- The script `dev_scripts/chatgpt/run_chatgpt.py -h` runs an assistant

- To get help:

  ```bash
  > run_chatgpt.py -h
  Use ChatGPT Assistant to process a file or certain text.

  optional arguments:
    -h, --help            show this help message and exit
    --list                Show all currently available assistants and exit
    --assistant_name ASSISTANT_NAME
                          Name of the assistant to be used
    --input_files [INPUT_FILE_PATHS ...]
                          Files needed in this run, use relative path from project root
    --model MODEL         Use specific model for this run, overriding existing assistant config
    --output_file OUTPUT_FILE
                          Redirect the output to the given file
    --input_text INPUT_TEXT
                          Take a text input from command line as detailed instruction
    --vim                 Disable -i (but not -o), take input from stdin and output to stdout forcely
    -v {TRACE,DEBUG,INFO,WARNING,ERROR,CRITICAL}
                          Set the logging level
  ```

- `dev_scripts/run_chatgpt.py -l` will show all the available assistants in our
  Org.
- Refer to `helpers/hchatgpt_instructions.py` to see how they are instructed

  ```bash
  python dev_scripts/chatgpt/run_chatgpt.py \
    -n MarkdownLinter \ # Use the assistant "MarkdownLinter"
    -f dev_scripts/chatgpt/example_data/corrupted_dropcontact.how_to_guide.md \ # Give this corrupted markdown file
    -o dev_scripts/chatgpt/example_data/gpt_linted_dropcontact.how_to_guide.md # Redirect its output to this file
  ```

# API library

- `helpers/hchatgpt.py` provides methods that wrap and interact with OpenAI API.
- By using these methods, you can easily build an assistant and chat to it with
  our files.

- Key functionalities include:
  - Uploading and removing files from OpenAI
  - Adding and removing files for an assistant
  - Creating threads and messages for user input
  - Running threads with certain assistants
  - End-to-end communication method between users and the assistant

## Usage

The following snippets provide a basic overview of the code usage.

### File Structure

- Since OpenAI File manager does not hold folder structure, you use a cache
  dictionary to save the relation between our file (with folder) and OpenAI File
  IDs
- This dictionary will be constantly accessed and saved back to
  `project_root/gpt_id.json`
- If you find anything buggy, try deleting this cache file and rerun the code so
  that it can be regenerated from scratch

### Uploading and Retrieving Files

- To upload a file to OpenAI, which you can later attach to messages/assistants:

  ```python
  file_id = upload_to_gpt('path_to_your_file')
  ```

- If you want to retrieve a file that has been uploaded to OpenAI by its path or
  ID:
  ```python
  file_object = get_gpt_file_from_path('path_to_your_file')
  ```
  or
  ```python
  file_object = get_gpt_file_from_id(file_id)
  ```

### Managing Assistants

You can specify files an assistant should constantly use (like guidelines):

```python
set_assistant_files_by_name('assistant_name', ['file_path_1', 'file_path_2'])
```

Add or remove specific files to/from an existing assistant by file paths or IDs:

```python
add_files_to_assistant_by_name('assistant_name', ['new_file_path'])
delete_file_from_assistant_by_name('assistant_name', 'file_path_to_remove')
```

### ChatGPT Communication

- Create a thread and send a message, with or without attaching files:

  ```python
  thread_id = create_thread()
  message_id = create_message_on_thread_with_file_names(thread_id, 'Your message content', ['file_name_1'])
  ```

- Run a thread on an assistant to get the Assistant's response:
  ```python
  run_id = run_thread_on_assistant_by_name('assistant_name', thread_id)
  response_messages = wait_for_run_result(thread_id, run_id)
  ```

### E2E Assistant Runner

- Interact with an assistant conveniently with the `e2e_assistant_runner`
  function
- This function can take user input, send it to the assistant, and manage file
  attachments in one call:
  ```python
  response = e2e_assistant_runner('assistant_name', 'Your question or statement here', input_file_names=['file_name_1'])
  # Outputs the assistant's response.
  print(response)
  ```
