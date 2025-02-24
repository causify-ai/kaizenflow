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
# # Description
#
# This notebook generates an animated plot.

# %% [markdown]
# # Imports

# %%
# %load_ext autoreload
# %autoreload 2
# %matplotlib inline


from typing import Tuple

import matplotlib
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import HTML

# %%
# Increase the animation limit so all the frames can be displayed.
matplotlib.rcParams["animation.embed_limit"] = 2**128


# %% [markdown]
# # Functions

# %%
def update_plot(
    frame: int, time_series: pd.Series
) -> Tuple[matplotlib.lines.Line2D]:
    """
    Update the plot for each frame as the slider moves.

    :param frame: frame number for which the plot should be updated
    :param time_series: time-series data to plot
    :return: tuple containing a `Line2D` object representing the plot's line
    """
    # Set `x` and `y` value upto that frame.
    x = time_series.index[:frame]
    y = time_series.iloc[:frame]
    x_value = time_series.index[frame]
    # Create a custom heading according to value of `x`.
    ax.set_title(f"Plot generated at {x_value}")
    line.set_data(x, y)
    return (line,)


# %% [markdown]
# # Generate Data

# %%
time_index = pd.date_range(start="2023-08-08", end="2023-08-09", freq="5T")
random_data = np.random.randn(len(time_index))
time_series = pd.Series(random_data, index=time_index)
time_series.head(3)

# %% [markdown]
# # Plotting

# %%
# Initialize a blank plot, set labels and do not display it.
plt.ioff()
fig, ax = plt.subplots(figsize=(10, 5))
ax.set_xlabel("time")
ax.set_ylabel("data")

# %%
# Set up the initial plot.
(line,) = ax.plot([], [])
# Freeze the axes so that do not move when animated.
ax.set_xlim(time_series.index[0], time_series.index[-1])
ax.set_ylim(time_series.min(), time_series.max())

# %%
# Create the animation.
# TODO(Samarth): the output size is too big ~25 MB. Consider using a different approach for animation or stripping the metadata before checking in again.
ani = animation.FuncAnimation(
    fig, update_plot, frames=len(time_series), fargs=(time_series,), blit=True
)
# Convert the animation to HTML and display.
html_video = ani.to_jshtml()
HTML(html_video)
