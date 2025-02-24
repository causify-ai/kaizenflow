#!/usr/bin/env python

import argparse
import logging
import os

import helpers.hchatgpt as hchatgp
import helpers.hdbg as hdbg
import helpers.hparser as hparser
import helpers.hprint as hprint

_LOG = logging.getLogger(__name__)


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Use ChatGPT Assistant to process a file or certain text.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # We prefer not to use short command line options since they are often
    # unclear.
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--list",
        dest="list",
        action="store_true",
        help="Show all currently available assistants and exit",
    )
    group.add_argument(
        "--assistant_name",
        dest="assistant_name",
        help="Name of the assistant to be used",
    )
    parser.add_argument(
        "--input_files",
        dest="input_file_paths",
        action="extend",
        nargs="*",
        help="Files needed in this run, use relative path from project root",
    )
    parser.add_argument(
        "--model",
        dest="model",
        help="Use specific model for this run, overriding existing assistant config",
    )
    parser.add_argument(
        "--output_file",
        dest="output_file",
        help="Redirect the output to the given file",
    )
    parser.add_argument(
        "--input_text",
        dest="input_text",
        default="Run with the given file",
        help="Take a text input from command line as detailed instruction",
    )
    parser.add_argument(
        "--vim",
        dest="vim_mode",
        action="store_true",
        help="Disable -i (but not -o), take input from stdin and output to stdout forcely",
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
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    if args.list:
        print(hprint.format_list(hchatgp.get_all_assistant_names()))
        return
    model = args.model
    assistant_name = args.assistant_name
    user_input = args.input_text
    input_file_paths = args.input_file_paths
    output_file = args.output_file
    vim_mode = args.vim_mode
    hchatgp.e2e_assistant_runner(
        assistant_name,
        user_input=user_input,
        model=model,
        vim_mode=vim_mode,
        input_file_names=input_file_paths,
        output_file_path=output_file,
    )


if __name__ == "__main__":
    _main(_parse())
