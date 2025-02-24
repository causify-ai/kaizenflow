# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.14.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Maple
#
# https://www.sagemath.org/

# %%
# !sudo /bin/bash -c "(source /venv/bin/activate; pip install sagemath)"

# %%

# %% [markdown]
# # Sympy

# %%
# !sudo /bin/bash -c "(source /venv/bin/activate; pip install sympy)"

# %% [markdown]
# ## Features
#
# https://docs.sympy.org/latest/tutorials/intro-tutorial/features.html#

# %% [markdown]
# ## Logic
#
# https://docs.sympy.org/latest/tutorials/intro-tutorial/intro.html#what-is-symbolic-computation

# %%
from sympy import *

# %%
x, y = symbols('x,y')
y | (x & y)

# %%
x >> y

# %%
# Evaluate an expression.
(y & x).subs({x: True, y: True})

# %%
w, x, y, z = symbols('w x y z')
minterms = [{w: 0, x: 1}, {y: 1, z: 1, x:0}]
SOPform([w, x, y, z], minterms)

# %%
b = (~x & ~y & ~z) | ( ~x & ~y & z)
simplify_logic(b)

# %%
# Compute truth table.
from sympy.logic.boolalg import truth_table

table = truth_table(x >> y, [x, y])
for t in table:
    print(f"{t[0]} -> {t[1]}")

# %%
satisfiable(x & ~x)

# %%
satisfiable((x | y) & (x | ~y) & (~x | y))

# %%
# - (not L => Q and B and N)
# - (N => not L)
# - not Q => B
# - not B

L, N, Q, B = symbols('L N Q B')

C = Implies(~L, Q & B & N) & Implies(N, ~L) & Implies(~Q, B) & ~B
satisfiable(C)

# %%
## Stats

https://docs.sympy.org/latest/modules/stats.html#
