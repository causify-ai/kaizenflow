#!/usr/bin/env python

import argparse
import logging
import os

from openai import OpenAI

import helpers.hchatgpt_instructions as hchainst
import helpers.hdbg as hdbg
import helpers.hparser as hparser

_LOG = logging.getLogger(__name__)

try:
    pass
except ImportError:
    os.system("pip install openai")
finally:
    pass

_LOG = logging.getLogger(__name__)

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)


def _process_text(txt: str, instruction: str) -> str:
    prompt = instruction + "\n\n" + txt
    _LOG.debug("prompt=%s", prompt)
    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": instruction,
            },
            {
                "role": "user",
                "content": txt,
            }
        ],
        model="gpt-3.5-turbo",
    )
    _LOG.debug("response=%s", response)
    response = response.choices[0].message.content
    _LOG.debug("response=%s", response)
    return response


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--instruction", required=True)
    hparser.add_input_output_args(parser)
    hparser.add_verbosity_arg(parser)
    return parser


def _main(parser: argparse.ArgumentParser) -> None:
    args = parser.parse_args()
    print("cmd line: %s" % hdbg.get_command_line())
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    #
    in_file_name, out_file_name = hparser.parse_input_output_args(
        args, clear_screen=True
    )
    txt = hparser.read_file(in_file_name)
    txt = "\n".join(txt)
    hdbg.dassert_in(args.instruction, hchainst.instructions)
    instruction = hchainst.instructions[args.instruction]
    result = _process_text(txt, instruction)
    hparser.write_file(result, out_file_name)


if __name__ == "__main__":
    _main(_parse())
