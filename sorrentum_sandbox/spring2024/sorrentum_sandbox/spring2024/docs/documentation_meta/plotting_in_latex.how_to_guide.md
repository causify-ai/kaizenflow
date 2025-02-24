

<!-- toc -->

  * [Tikz](#tikz)
  * [Pgfplots](#pgfplots)
  * [Asymptote](#asymptote)
- [Plotting in markdown](#plotting-in-markdown)
  * [How to draw in markdown](#how-to-draw-in-markdown)

<!-- tocstop -->

For plotting a certain classes of drawings (e.g., diagrams, graph) one should
use frameworks like dot, mermaid, plantuml

For technical drawing there are several solutions, as described below

## Tikz

- Language for producing vector graphics from a textual description
- Several drawing programs can export figures as Tikz format (e.g., Inkspace,
  matplotlib, gnuplot)

- Refs
  - https://en.wikipedia.org/wiki/PGF/TikZ
  - https://tikz.net/
  - https://tikz.org/
  - Examples
    - https://tikz.dev/
    - https://texample.net/tikz/examples/
    - https://tex.stackexchange.com/questions/175969/block-diagrams-using-tikz
  - Web application
    - https://tikzmaker.com/editor
  - Local editor
    - https://tikzit.github.io/
  - Misc
    - https://tex.stackexchange.com/?tags=tikz-pgf

## Pgfplots

- Plots functions directly in Tex/Latex
- Based on TikZ

- Refs
  - https://ctan.math.washington.edu/tex-archive/graphics/pgf/contrib/pgfplots/doc/pgfplots.pdf
  - https://www.overleaf.com/learn/latex/Pgfplots_package

## Asymptote

- A descriptive vector graphics language
- Provide a coordinate-based framework for technical drawing
- It has a Python frontend

- Refs
  - https://en.wikipedia.org/wiki/Asymptote_(vector_graphics_language)
  - https://asymptote.sourceforge.io/
  - Gallery
    - https://asymptote.sourceforge.io/gallery/
  - Asymptote web application
    - http://asymptote.ualberta.ca/

# Plotting in markdown

## How to draw in markdown

We would like to use the same plots for both Latex and Markdown documents

We can use pandoc

TODO(gp): Consider extending ./dev_scripts/documentation/render_md.py to render
also complex Latex, tikz

https://tex.stackexchange.com/questions/586285/pandoc-markdown-drawing-circuit-diagrams-using-circuitikz
