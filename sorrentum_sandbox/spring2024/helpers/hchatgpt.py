"""
Import as:

import helpers.hchatgpt as hchatgp
"""

import logging
import math
import os
import sys
import time
from typing import Dict, List, Optional

import helpers.hio as hio

try:
    import openai
except ImportError:
    os.system("pip install openai")
finally:
    import openai

_LOG = logging.getLogger(__name__)

# Setting API as env var in your terminal is the correct approach.
# NEVER upload any OpenAI API key to GitHub, OpenAI will revoke it.

client = openai.OpenAI()

# The OpenAI File ID cache will be saved as `prefix_to_root/gpt_id.json`
# Only files under the given root directory may be uploaded to OpenAI.
prefix_to_root = os.path.join(os.path.dirname(__file__), "..")

# #############################################################################
# Create/update/delete Assistant.
# #############################################################################


def create_assistant(
    assistant_name: str,
    instructions: str,
    *,
    model: str = "gpt-3.5-turbo-1106",
    use_retrieval: bool = True,
    use_code_interpreter: bool = True,
    use_function: Dict = None,
) -> str:
    """
    Create an OpenAI Assistant for your OpenAI Organization. All configs can
    still be updated after creation.

    This method should only be used when a new Assistant is needed.
    Otherwise, use the Assistant name to retrieve an existing Assistant.

    :param assistant_name: name of the Assistant to be created
    :param instructions: instruction string that describes the expected
        behavior of assistant
    :param model: GPT model used by the assistant
    :param use_retrieval: enable the retrieval tool from OpenAI
    :param use_code_interpreter: enable the code interpreter tool from
        OpenAI
    :param use_function: enable the function tool from OpenAI (To be
        implemented)
    """
    # Create the assistant
    tools = []
    if use_retrieval:
        tools.append({"type": "retrieval"})
    if use_code_interpreter:
        tools.append({"type": "code_interpreter"})
    if use_function:
        tools.append(use_function)
    if not model:
        model = "gpt-3.5-turbo-1106"
    assistant = client.beta.assistants.create(
        instructions=instructions,
        name=assistant_name,
        model=model,
        tools=tools,
    )
    return assistant.id


def update_assistant_by_id(
    assistant_id: str,
    *,
    instructions: str = "",
    name: str = "",
    tools: Optional[List[Dict[str, str]]] = None,
    model: str = "",
    file_ids: Optional[List[str]] = None,
) -> str:
    """
    Update an existing OpenAI Assistant in our OpenAI Organization.

    :param assistant_id: Assistant to be updated
    :param instructions: instruction string that describes the expected
        behavior of assistant
    :param name: change the name of assistant, no change when empty
    :param tools: change the tools of assistant, no change when empty
    :param model: change the model of assistant, no change when empty
    :param file_ids: change the files linked to assistant, no change
        when empty
    """
    if tools is None:
        tools = []
    if file_ids is None:
        file_ids = []
    update_config = {
        "instructions": instructions,
        "name": name,
        "tools": tools,
        "model": model,
        "file_ids": file_ids,
    }
    not_empty_params = {k: v for k, v in update_config.items() if v}
    updated_assistant = client.beta.assistants.update(
        assistant_id, **not_empty_params
    )
    return updated_assistant.id


def delete_assistant_by_id(assistant_id: str) -> None:
    """
    Delete an Assistant from our OpenAI Organization.
    """
    client.beta.assistants.delete(assistant_id)


def get_all_assistants() -> List[openai.types.beta.assistant.Assistant]:
    """
    Get all available Assistant objects in our OpenAI Organization.
    """
    list_assistants_response = client.beta.assistants.list(
        order="desc",
        limit="100",
    )
    assistants = list_assistants_response.data
    return assistants


def get_all_assistant_names() -> List[str]:
    """
    Get all available Assistant names in our OpenAI Organization.
    """
    assistants = get_all_assistants()
    return [assistant.name for assistant in assistants]


def get_assistant_id_by_name(assistant_name) -> str:
    """
    Get the id of an Assistant by its name.
    """
    assistant = None
    assistants = get_all_assistants()
    for cur_assistant in assistants:
        if cur_assistant.name == assistant_name:
            assistant = cur_assistant
    return assistant.id


# #############################################################################
# Create directory structure storing gpt file ids
# #############################################################################


def _path_to_dict(path: str) -> Dict:
    """
    Generate a dictionary of all files under a given folder.
    """
    for root, dirs, files in os.walk(path):
        tree = {d: _path_to_dict(os.path.join(root, d)) for d in dirs}
        tree.update({f: {"name": f} for f in files})
        return tree


# TODO(Henry): We use fileIO here to store the directory structure, which may
# not be thread-safe. Should change to use DAO if we have any.
def _dump_gpt_ids(dictionary: Dict) -> None:
    """
    Dump a given OpenAI File ID dictionary into a cache file for furture use.
    """
    file_path = os.path.join(prefix_to_root, "gpt_id.json")
    hio.to_json(file_path, dictionary)
    return


def _load_gpt_ids() -> Dict:
    """
    Load the OpenAI File ID dictionary from the cache file.
    """
    file_path = os.path.join(prefix_to_root, "gpt_id.json")
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return hio.from_json(file_path)
    else:
        directory_dict = _path_to_dict(prefix_to_root)
        _dump_gpt_ids(directory_dict)
        return directory_dict


def _get_gpt_id_file(dictionary: Dict, path_from_root: str) -> Dict[str, str]:
    """
    Get the OpenAI File ID for a given file using a specific cache.

    If this file has not been uploaded to OpenAI, this method will
    upload it and generate its OpenAI File ID.
    """
    cur = dictionary
    path_list = path_from_root.split("/")
    for level in path_list:
        cur = cur[level]
    if "gpt_id" not in cur:
        cur["gpt_id"] = _upload_to_gpt_no_set_id(path_from_root)
        _dump_gpt_ids(dictionary)
    return cur


def _set_gpt_id(path_from_root: str, gpt_id: str) -> None:
    """
    Manually set the cached OpenAI File ID of a given file.

    This method should ONLY be called if a file manually uploaded to
    OpenAI. It will NOT upload the given file to OpenAI.
    """
    gpt_id_dict = _load_gpt_ids()
    item = _get_gpt_id_file(gpt_id_dict, path_from_root)
    item["gpt_id"] = gpt_id
    _dump_gpt_ids(gpt_id_dict)


def _remove_gpt_id(path_from_root: str):
    """
    Remove the cached ID of a given file.

    It does NOT fully remove a file from OpenAI. Use `remove_from_gpt`
    to fully remove a file.
    """
    gpt_id_dict = _load_gpt_ids()
    item = _get_gpt_id_file(gpt_id_dict, path_from_root)
    if "gpt_id" in item:
        del item["gpt_id"]
    _dump_gpt_ids(gpt_id_dict)


def get_gpt_id(path_from_root: str) -> str:
    """
    Get the OpenAI File ID from cache for a given file.

    If this file has not been uploaded to OpenAI, this method will
    upload it and generate its OpenAI File ID.
    """
    gpt_id_dict = _load_gpt_ids()
    return _get_gpt_id_file(gpt_id_dict, path_from_root)["gpt_id"]


# #############################################################################
# Upload file to OpenAI account
# #############################################################################


def _upload_to_gpt_no_set_id(path_from_root: str) -> str:
    """
    Upload a file to OpenAI.

    This method will NOT set File ID to cache.
    """
    _LOG.info(f"Uploading file {path_from_root} to chatgpt.")
    upload_file_response = client.files.create(
        # Must use 'rb' regardless of file type.
        file=open(os.path.join(prefix_to_root, path_from_root), "rb"),
        purpose="assistants",
    )
    gpt_id = upload_file_response.id
    return gpt_id


def upload_to_gpt(path_from_root: str) -> str:
    """
    Upload a file to OpenAI and set its File ID to cache.
    """
    gpt_id = _upload_to_gpt_no_set_id(path_from_root)
    _set_gpt_id(path_from_root, gpt_id)
    return gpt_id


def remove_from_gpt(path_from_root: str) -> None:
    """
    Fully remove a file from OpenAI.

    This method will first delete the file from OpenAI account, then
    remove its OpenAI File ID from the cache.
    """
    gpt_id = get_gpt_id(path_from_root)
    client.files.delete(gpt_id)
    _remove_gpt_id(path_from_root)


def get_gpt_file_from_id(gpt_id: str) -> openai.types.file_object.FileObject:
    """
    Get a OpenAI File Object using its OpenAI File ID.
    """
    return client.files.retrieve(gpt_id)


def get_gpt_file_from_path(
    path_from_root: str,
) -> openai.types.file_object.FileObject:
    """
    Get a OpenAI File Object using its file path.
    """
    gpt_id = get_gpt_id(path_from_root)
    return get_gpt_file_from_id(gpt_id)


# #############################################################################
# Add/Remove files for an assistant
# #############################################################################

# Note that files for Assistant means files constantly used by this assistant
# (like guidelines). For one-time used files, add them to a message instead.
# One Assistant can have up to 20 files linked to it.


def set_assistant_files_by_name(
    assistant_name: str, file_path_list: List[str]
) -> str:
    """
    Use the given file list to overwrite the file list linked to an assistant.
    """
    assistant_id = get_assistant_id_by_name(assistant_name)
    file_ids = [get_gpt_id(path) for path in file_path_list]
    return update_assistant_by_id(assistant_id, file_ids=file_ids)


def add_files_to_assistant_by_name(
    assistant_name: str, file_path_list: List[str]
) -> str:
    """
    Link all given files to an assistant.

    An Assistant can hold only 20 files, the oldest files will be
    unlinked automatically.
    """
    assistant_id = get_assistant_id_by_name(assistant_name)
    assistant_files = client.beta.assistants.files.list(
        assistant_id=assistant_id
    ).data
    existing_file_ids = [file.id for file in assistant_files]
    new_file_ids = [get_gpt_id(path) for path in file_path_list]
    file_ids = list(set(existing_file_ids + new_file_ids))
    file_ids = file_ids[-20:]
    return update_assistant_by_id(assistant_id, file_ids=file_ids)


def delete_file_from_assistant_by_id(assistant_id: str, file_id: str) -> None:
    """
    Unlink a file from an Assistant using Assistant id and file id.

    This method does NOT remove the file from OpenAI account.
    """
    client.beta.assistants.files.delete(
        assistant_id=assistant_id, file_id=file_id
    )


def delete_file_from_assistant_by_name(
    assistant_name: str, file_path: str
) -> None:
    """
    Unlink a file from an Assistant using Assistant name and file path.

    This method does NOT remove the file from OpenAI account.
    """
    gpt_id = get_gpt_id(file_path)
    assistant_id = get_assistant_id_by_name(assistant_name)
    delete_file_from_assistant_by_id(assistant_id, gpt_id)


# #############################################################################
# Create Thread and Message from user input
# #############################################################################


def create_thread() -> str:
    message_thread = client.beta.threads.create()
    return message_thread.id


def create_message_on_thread(
    thread_id: str, content: str, file_ids: List[str]
) -> str:
    """
    Create a message on a thread, then link files to the message using file id.

    Files linked to a message can only be used by ChatGPT in the thread
    that holds this message.
    """
    if not content:
        _LOG.error(
            "Message content must not be empty. This will cause an OpenAI error."
        )
    if file_ids:
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=content,
            file_ids=file_ids,
        )
    else:
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=content,
        )
    return message.id


def create_message_on_thread_with_file_names(
    thread_id: str, content: str, file_names: List[str]
) -> str:
    """
    Create a message on a thread, then link files to the message using file
    name.

    Files linked to a message can only be used by ChatGPT in the thread
    that holds this message.
    """
    if file_names:
        file_ids = [get_gpt_id(file) for file in file_names]
    else:
        file_ids = []
    return create_message_on_thread(thread_id, content, file_ids)


# #############################################################################
# Run thread on certain assistant
# #############################################################################


def run_thread_on_assistant(assistant_id, thread_id, model: str = "") -> str:
    """
    Run a thread on a given Assistant id.

    This is similar to sending a message to ChatGPT.
    """
    if model:
        run = client.beta.threads.runs.create(
            thread_id=thread_id, assistant_id=assistant_id, model=model
        )
    else:
        run = client.beta.threads.runs.create(
            thread_id=thread_id, assistant_id=assistant_id
        )
    return run.id


def run_thread_on_assistant_by_name(
    assistant_name: str, thread_id: str, model: str = ""
) -> str:
    """
    Run a thread on a given Assistant name.

    This is similar to sending a message to ChatGPT.
    """
    assistant_id = get_assistant_id_by_name(assistant_name)
    if model:
        return run_thread_on_assistant(assistant_id, thread_id, model)
    else:
        return run_thread_on_assistant(assistant_id, thread_id)


def wait_for_run_result(thread_id: str, run_id: str, timeout: int = 180) -> List:
    """
    Wait for the thread to be processed.

    This is similar to waiting for ChatGPT's typing.
    """
    finished = False
    _LOG.info("Waiting for chatgpt response...")
    for i in range(math.ceil(timeout / 5)):
        _LOG.info(f"{i*5}/{timeout} seconds before timeout.")
        time.sleep(5)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run_id
        )
        finished = run.status == "completed"
        if finished:
            break
    if not finished:
        raise TimeoutError("Failed to retrieve response from OpenAI.")
    messages = client.beta.threads.messages.list(thread_id=thread_id).data
    return messages


# #############################################################################
# ChatGPT runner
# #############################################################################


def e2e_assistant_runner(
    assistant_name: str,
    user_input: str = "",
    *,
    model: str = "",
    input_file_names: Optional[List[str]] = None,
    output_file_path: str = "",
    vim_mode: bool = False,
) -> str:
    """
    Send a message with files to an Assistant and wait for its reply.

    :param assistant_name: Assistant that should process this message
    :param user_input: message to be sent to ChatGPT assistant
    :param model: change the GPT model used by the assistant, no change
        when empty this WILL update the configuration of the assistant
    :param input_file_names: files to be used in this conversation
    :param output_file_path: redirect ChatGPT's output to the given file
    :param vim_mode: if True, take input from stdin and output to stdout
        forcely
    """
    if input_file_names is None:
        input_file_names = []
    if not assistant_name:
        _LOG.error("No Assistant name provided.")
        return ""
    if vim_mode:
        user_input = "".join(sys.stdin.readlines())
    thread_id = create_thread()
    create_message_on_thread_with_file_names(
        thread_id, user_input, input_file_names
    )
    if model:
        run_id = run_thread_on_assistant_by_name(assistant_name, thread_id, model)
    else:
        run_id = run_thread_on_assistant_by_name(assistant_name, thread_id)
    messages = wait_for_run_result(thread_id, run_id)
    output = messages[0].content[0].text.value
    if vim_mode or not output_file_path:
        sys.stdout.write(output)
    if output_file_path:
        with open(output_file_path, "w", encoding="utf-8") as fp:
            fp.write(output)
    return output
