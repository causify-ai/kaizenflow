#!/usr/bin/env python

"""
Import as:

import dev_scripts.string_to_file as dssttofi
"""

# > amp/dev_scripts/string_to_file.py Effect of pessimism on long-, short- term equilibrium for aggregate- demand and supply
# Effect_of_pessimism_on_long_short_term_equilibrium_for_aggregate_demand_and_supply

# To test:
# > amp/dev_scripts/string_to_file.py

import re
import sys


def _transform(string: str) -> str:
    for v in ("'", "-", '"', ",", ":"):
        string = string.replace(v, " ")
    # TODO(gp): Use regex.
    string = re.sub("\s+", "_", string)
    return string


def _check(inp: str, act: str, exp: str) -> None:
    assert act == exp, "inp=%s\nact=%s\nexp=%s" % (inp, act, exp)


def _test1() -> None:
    inp = "Effect of pessimism on long-, short- term equilibrium for aggregate- demand and supply"
    act = _transform(inp)
    exp = "Effect_of_pessimism_on_long_short_term_equilibrium_for_aggregate_demand_and_supply"
    _check(inp, act, exp)


def _test2() -> None:
    inp = "Effects of a shift in aggregate-supply: accommodating shift in AS"
    act = _transform(inp)
    exp = "Effects_of_a_shift_in_aggregate_supply_accommodating_shift_in_AS"
    _check(inp, act, exp)


def _test() -> None:
    print("Testing ...")
    _test1()
    _test2()
    print("Test PASSED")
    sys.exit(0)


def _main() -> None:
    string = " ".join(sys.argv[1:])
    if string == "":
        _test()
    string = _transform(string)
    print(string)


if __name__ == "__main__":
    _main()
