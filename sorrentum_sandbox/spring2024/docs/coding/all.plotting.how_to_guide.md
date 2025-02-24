

<!-- toc -->

- [Best practices for writing plotting functions](#best-practices-for-writing-plotting-functions)
  * [Cosmetic requirements](#cosmetic-requirements)
  * [Technical requirements](#technical-requirements)
  * [Multiple plots](#multiple-plots)

<!-- tocstop -->

# Best practices for writing plotting functions

## Cosmetic requirements

A plot should be easy to interpret. This means:

- It should have a title
- Axes should have labels
- Ticks should be placed in an interpretable way; if there are few of them,
  place their labels with zero rotation
- If there are several lines on the plot, it should have a legend

## Technical requirements

- Do not add `plt.show()` at the end of the function. It prevents the user from
  using this plot as a subplot and from tweaking it.
- Expose the `ax` parameter

## Multiple plots

- If the function plots multiple plots, it is usually better to create a single
  figure for them. This way, the output is more concise and can be copied as one
  image.
- In `amp/core/plotting.py`, there is a helper called `get_multiple_plots()`
  that is used for generating a figure and axes
- Add `plt.tight_layout()` in the end only if you are sure this figure will not
  be wrapped inside another figure
- If there is a possibility the figure will be wrapped, try passing in a list of
  axes
- To combine multiple figures with subplots into one, use
  [GridSpec](https://matplotlib.org/3.2.1/api/_as_gen/matplotlib.gridspec.GridSpec.html#matplotlib.gridspec.GridSpec)
