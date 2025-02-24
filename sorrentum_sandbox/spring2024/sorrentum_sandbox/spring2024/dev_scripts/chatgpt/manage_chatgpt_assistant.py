#!/usr/bin/env python

import argparse
import logging
import os

import helpers.hchatgpt as hchatgp
import helpers.hchatgpt_instructions as hchainst
import helpers.hdbg as hdbg
import helpers.hparser as hparser

_LOG = logging.getLogger(__name__)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage the ChatGPT Assistants in our OpenAI Organization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    # We prefer not to use short command line options since they are often
    # unclear.
    group.add_argument(
        "--create",
        dest="create_name",
        help="Name of the assistant to be created",
    )
    group.add_argument(
        "--edit",
        dest="edit_name",
        help="Name of the assistant to be edited",
    )
    group.add_argument(
        "--delete",
        dest="delete_name",
        help="Name of the assistant to be deleted, will ignore all other arguments",
    )
    parser.add_argument(
        "--new_name",
        dest="new_name",
        help="New name for the assistant, only used in -e",
    )
    parser.add_argument(
        "--model", dest="model", help="Model used by the assistant"
    )
    parser.add_argument(
        "--instruction_name",
        dest="instruction_name",
        help="Name of the instruction for the assistant, as shown in helpers.hchatgpt_instructions",
    )
    parser.add_argument(
        "--input_files",
        dest="input_file_paths",
        action="extend",
        nargs="*",
        help="Files needed for the assistant, use relative path from project root",
    )
    parser.add_argument(
        "--retrieval_tool",
        dest="retrieval_tool",
        action=argparse.BooleanOptionalAction,
        help="Enable the retrieval tool. Use --no-r to disable",
    )
    parser.add_argument(
        "--code_tool",
        dest="code_tool",
        action=argparse.BooleanOptionalAction,
        help="Enable the code_interpreter tool. Use --no-c to disable",
    )
    parser.add_argument(
        "--function",
        dest="function",
        action="store",
        help="Apply certain function tool to the assistant, not implemented yet",
    )

    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    if not os.environ["OPENAI_API_KEY"]:
        raise ValueError(
            "Your OpenAI API key is not set. "
            "Before running any OpenAI related code, "
            "add OPENAI_API_KEY=<YOUR_KEY> into your environment variable."
        )
    instructions = hchainst.instructions
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    if args.create_name:
        # TODO(Henry): Implement the function calling tool in OpenAI API.
        hchatgp.create_assistant(
            assistant_name=args.create_name,
            instructions=instructions[args.instruction_name],
            model=args.model,
            use_retrieval=args.retrieval_tool,
            use_code_interpreter=args.code_tool,
        )
        hchatgp.add_files_to_assistant_by_name(
            args.create_name, args.input_file_paths
        )
    elif args.edit_name:
        assistant_id = hchatgp.get_assistant_id_by_name(args.edit_name)
        tools = []
        if args.retrieval_tool:
            tools.append({"type": "retrieval"})
        if args.code_tool:
            tools.append({"type": "code_interpreter"})
        hchatgp.update_assistant_by_id(
            assistant_id=assistant_id,
            instructions=instructions[args.instruction_name],
            name=args.new_name,
            tools=tools,
            model=args.model,
            file_ids=[hchatgp.get_gpt_id(path) for path in args.input_file_paths],
        )
    elif args.delete_name:
        assistant_id = hchatgp.get_assistant_id_by_name(args.delete_name)
        hchatgp.delete_assistant_by_id(assistant_id)
    else:
        raise ValueError("Unsupported behavior. Please use one of -c, -e or -d")


if __name__ == "__main__":
    _main(_parse())
