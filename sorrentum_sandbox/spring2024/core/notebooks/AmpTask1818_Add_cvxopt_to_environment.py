# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.7
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
# # !pip install cvxopt
import cvxpy as cp

# %%
import numpy as np

# %% [markdown]
# # Example 1

# %%
# Reproduce the example from `https://www.cvxpy.org/index.html`.

# Problem data.
m = 30
n = 20
np.random.seed(1)
A = np.random.randn(m, n)
b = np.random.randn(m)

# Construct the problem.
x = cp.Variable(n)
objective = cp.Minimize(cp.sum_squares(A @ x - b))
constraints = [0 <= x, x <= 1]
prob = cp.Problem(objective, constraints)

# The optimal objective value is returned by `prob.solve()`.
result = prob.solve()
# The optimal value for x is stored in `x.value`.
print(x.value)
# The optimal Lagrange multiplier for a constraint is stored in
# `constraint.dual_value`.
print(constraints[0].dual_value)

# %%
# https://www.cvxpy.org/tutorial/advanced/index.html#getting-the-standard-form
pd1, pd2, pd3 = prob.get_problem_data(cp.CVXOPT)

# %%
pd1

# %%
pd2

# %%
pd3

# %% [markdown]
# # Example 2

# %%
# https://druce.ai/2020/12/portfolio-opimization

# %%
# Problem data.
m = 100
n = 20
np.random.seed(1)
historical_mu = np.random.randn(m, n)

# %%
mu = np.random.randn(n)

# %%
# The `transpose()` is necessary.
covariance = np.cov(historical_mu.transpose())

# %%
weights = cp.Variable(n)

# %%
rets = mu.T @ weights

# %%
portfolio_variance = cp.quad_form(weights, covariance)

# %%
minimize_variance = cp.Problem(
    cp.Minimize(portfolio_variance), [cp.sum(weights) == 1]
)

# %%
minimize_variance.solve()

# %%
rets.value

# %%
weights.value

# %%
maximize_returns = cp.Problem(
    cp.Maximize(rets),
    [
        cp.sum(weights) == 1,
        # Long-short will try to increase leverage to infinity (and fail to converge)
        weights >= 0,
    ],
)

# %%
maximize_returns.solve()

# %%
portfolio_variance.value

# %%
maximize_returns_2 = cp.Problem(
    cp.Maximize(rets),
    [
        cp.norm(weights) <= 1.5,
        cp.sum(weights) == 1,
        portfolio_variance <= 0.05,
    ],
)

# %%
maximize_returns_2.solve()

# %%
portfolio_variance.value

# %% [markdown]
# # More examples

# %%
# https://nbviewer.org/github/cvxgrp/cvx_short_course/blob/master/applications/portfolio_optimization.ipynb

# %%
# https://github.com/druce/portfolio_optimization/blob/master/Portfolio%20optimization.ipynb
