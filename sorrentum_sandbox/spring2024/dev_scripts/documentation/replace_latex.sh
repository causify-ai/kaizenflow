#!/bin/bash -xe

filename=$1

if [[ 0 == 1 ]]; then
  git checkout -- $filename
fi;

# #############################################################################
if [[ 0 == 1 ]]; then
  pandoc.sh $filename
fi;

# TODO:
# \textit{...}
# - ___Algo___
# - ___Proof___

# #############################################################################
# Old abbreviation
# #############################################################################

# Convert long form to (old) abbreviations.
if [[ 0 == 1 ]]; then
  perl -i -pe 's/\\vv{a}/\\aaa/g' $filename
  perl -i -pe 's/\\vv{\\alpha}/\\aalpha/g' $filename
  perl -i -pe 's/\\vv{b}/\\bb/g' $filename
  perl -i -pe 's/\\vv{\\beta}/\\bbeta/g' $filename
  perl -i -pe 's/\\vv{c}/\\cc/g' $filename
  perl -i -pe 's/\\vv{d}/\\dd/g' $filename
  perl -i -pe 's/\\vv{\\delta}/\\ddelta/g' $filename
  perl -i -pe 's/\\vv{e}/\\eee/g' $filename
  perl -i -pe 's/\\vv{f}/\\ff/g' $filename
  perl -i -pe 's/\\vv{\\gamma}/\\ggamma/g' $filename
  perl -i -pe 's/\\vv{h}/\\hh/g' $filename
  perl -i -pe 's/\\vv{\\mu}/\\mmu/g' $filename
  perl -i -pe 's/\\vv{\\omega}/\\oomega/g' $filename
  perl -i -pe 's/\\vv{p}/\\pp/g' $filename
  perl -i -pe 's/\\vv{q}/\\qq/g' $filename
  perl -i -pe 's/\\vv{r}/\\rr/g' $filename
  perl -i -pe 's/\\vv{\\sigma}/\\ssigma/g' $filename
  perl -i -pe 's/\\vv{s}/\\sss/g' $filename
  perl -i -pe 's/\\vv{\\theta}/\\ttheta/g' $filename
  perl -i -pe 's/\\vv{u}/\\uu/g' $filename
  perl -i -pe 's/\\vv{A}/\\vvA/g' $filename
  perl -i -pe 's/\\vv{B}/\\vvB/g' $filename
  perl -i -pe 's/\\vv{F}/\\vvF/g' $filename
  perl -i -pe 's/\\vv{P}/\\vvP/g' $filename
  perl -i -pe 's/\\vv{U}/\\vvU/g' $filename
  perl -i -pe 's/\\vv{X}/\\vvX/g' $filename
  perl -i -pe 's/\\vv{Y}/\\vvY/g' $filename
  perl -i -pe 's/\\vv{\\varepsilon}/\\vvarepsilon/g' $filename
  perl -i -pe 's/\\vv{v}/\\vvv/g' $filename
  perl -i -pe 's/\\vv{w}/\\ww/g' $filename
  perl -i -pe 's/\\vv{x}/\\xx/g' $filename
  perl -i -pe 's/\\vv{y}/\\yy/g' $filename
  perl -i -pe 's/\\vv{z}/\\zz/g' $filename
fi;


# Convert from old to new abbreviations.
if [[ 0 == 1 ]]; then
  perl -i -pe 's/\\aaa/\\va/g' $filename
  perl -i -pe 's/\\aalpha/\\valpha/g' $filename
  perl -i -pe 's/\\bb(?![RCNZ])/\\vb/g' $filename
  perl -i -pe 's/\\bbeta/\\vbeta/g' $filename
  perl -i -pe 's/\\ggamma/\\vgamma/g' $filename
  perl -i -pe 's/\\cc/\\vc/g' $filename
  perl -i -pe 's/\\dd/\\vd/g' $filename
  perl -i -pe 's/\\ddelta/\\vdelta/g' $filename
  perl -i -pe 's/\\eee/\\ve/g' $filename
  perl -i -pe 's/\\ff/\\vf/g' $filename
  perl -i -pe 's/\\hh/\\vh/g' $filename
  perl -i -pe 's/\\mmu/\\vmu/g' $filename
  perl -i -pe 's/\\oomega/\\vomega/g' $filename
  perl -i -pe 's/\\pp/\\vp/g' $filename
  perl -i -pe 's/\\qq/\\vq/g' $filename
  perl -i -pe 's/\\rr/\\vr/g' $filename
  perl -i -pe 's/\\ssigma/\\vsigma/g' $filename
  perl -i -pe 's/\\sss/\\vs/g' $filename
  perl -i -pe 's/\\ttheta/\\vtheta/g' $filename
  perl -i -pe 's/\\uu(?!hat)/\\vu/g' $filename
  perl -i -pe 's/\\vvv(?!hat)/\\vvv/g' $filename
  perl -i -pe 's/\\vvarepsilon/\\vvarepsilon/g' $filename
  perl -i -pe 's/\\vvA/\\vA/g' $filename
  perl -i -pe 's/\\vvB/\\vB/g' $filename
  perl -i -pe 's/\\vvF/\\vF/g' $filename
  perl -i -pe 's/\\vvP/\\vP/g' $filename
  perl -i -pe 's/\\vvU/\\vU/g' $filename
  perl -i -pe 's/\\vvX/\\vX/g' $filename
  perl -i -pe 's/\\vvY/\\vY/g' $filename
  perl -i -pe 's/\\ww/\\vw/g' $filename
  perl -i -pe 's/\\xx(?!hat)/\\vx/g' $filename
  perl -i -pe 's/\\yy/\\vy/g' $filename
  perl -i -pe 's/\\zz/\\vz/g' $filename

  # Fix mistakes made in the past.
  perl -i -pe 's/\\vuhat/\\uuhat/g' $filename
  perl -i -pe 's/\\vxhat/\\vvvhat/g' $filename
  perl -i -pe 's/\\vxhat/\\xxhat/g' $filename
fi;


if [[ 0 == 1 ]]; then
  # Generate perl from old to new abbreviations.
  perl -i -pe 's/\\AAA/\\mA/g' $filename
  perl -i -pe 's/\\BB/\\mB/g' $filename
  perl -i -pe 's/\\CC/\\mC/g' $filename
  perl -i -pe 's/\\II/\\mI/g' $filename
  perl -i -pe 's/\\FF/\\mF/g' $filename
  perl -i -pe 's/\\LL/\\mL/g' $filename
  perl -i -pe 's/\\MM/\\mM/g' $filename
  perl -i -pe 's/\\NN/\\mN/g' $filename
  perl -i -pe 's/\\PP/\\mP/g' $filename
  perl -i -pe 's/\\QQ/\\mQ/g' $filename
  perl -i -pe 's/\\RR/\\mR/g' $filename
  perl -i -pe 's/\\SSS/\\mS/g' $filename
  perl -i -pe 's/\\SSigma/\\mSigma/g' $filename
  perl -i -pe 's/\\UU/\\mU/g' $filename
  perl -i -pe 's/\\VVV/\\mV/g' $filename
  perl -i -pe 's/\\XX/\\mX/g' $filename
  perl -i -pe 's/\\ZZ/\\mZ/g' $filename
  perl -i -pe 's/\\WW/\\mW/g' $filename
fi;

if [[ 1 == 1 ]]; then
  # \Det
  perl -i -pe 's/\\text\{det\}/\\Det/g' $filename
  perl -i -pe 's/\\det/\\Det/g' $filename
  # \Tr
  perl -i -pe 's/\\text\{tr\}/\\Tr/g' $filename
  perl -i -pe 's/\\tr/\\Tr/g' $filename
  # \Tr
  perl -i -pe 's/\\text\{diag\}/\\Diag/g' $filename
  perl -i -pe 's/\\diag/\\Diag/g' $filename
fi;

# #############################################################################
# New abbreviation
# #############################################################################


if [[ 0 == 1 ]]; then
  # Convert long form to new abbreviations.
  perl -i -pe 's/\\mat{A}/\\mA/g' $filename
  perl -i -pe 's/\\mat{B}/\\mB/g' $filename
  perl -i -pe 's/\\mat{C}/\\mC/g' $filename
  perl -i -pe 's/\\mat{D}/\\mD/g' $filename
  perl -i -pe 's/\\mat{\\Delta}/\\mDelta/g' $filename
  perl -i -pe 's/\\mat{E}/\\mE/g' $filename
  perl -i -pe 's/\\mat{F}/\\mF/g' $filename
  perl -i -pe 's/\\mat{G}/\\mG/g' $filename
  perl -i -pe 's/\\mat{\\Gamma}/\\mGamma/g' $filename
  perl -i -pe 's/\\mat{H}/\\mH/g' $filename
  perl -i -pe 's/\\mat{I}/\\mI/g' $filename
  perl -i -pe 's/\\mat{J}/\\mJ/g' $filename
  perl -i -pe 's/\\mat{K}/\\mK/g' $filename
  perl -i -pe 's/\\mat{L}/\\mL/g' $filename
  perl -i -pe 's/\\mat{\\Lambda}/\\mLambda/g' $filename
  perl -i -pe 's/\\mat{M}/\\mM/g' $filename
  perl -i -pe 's/\\mat{N}/\\mN/g' $filename
  perl -i -pe 's/\\mat{O}/\\mO/g' $filename
  perl -i -pe 's/\\mat{\\Omega}/\\mOmega/g' $filename
  perl -i -pe 's/\\mat{P}/\\mP/g' $filename
  perl -i -pe 's/\\mat{\\Pi}/\\mPi/g' $filename
  perl -i -pe 's/\\mat{\\Psi}/\\mPsi/g' $filename
  perl -i -pe 's/\\mat{Q}/\\mQ/g' $filename
  perl -i -pe 's/\\mat{R}/\\mR/g' $filename
  perl -i -pe 's/\\mat{S}/\\mS/g' $filename
  perl -i -pe 's/\\mat{\\Sigma}/\\mSigma/g' $filename
  perl -i -pe 's/\\mat{T}/\\mT/g' $filename
  perl -i -pe 's/\\mat{U}/\\mU/g' $filename
  perl -i -pe 's/\\mat{\\Upsilon}/\\mUpsilon/g' $filename
  perl -i -pe 's/\\mat{V}/\\mV/g' $filename
  perl -i -pe 's/\\mat{W}/\\mW/g' $filename
  perl -i -pe 's/\\mat{X}/\\mX/g' $filename
  perl -i -pe 's/\\mat{\\Xi}/\\mXi/g' $filename
  perl -i -pe 's/\\mat{Y}/\\mY/g' $filename
  perl -i -pe 's/\\mat{Z}/\\mZ/g' $filename
fi;

# Convert long form to new abbreviations.
if [[ 0 == 1 ]]; then
  perl -i -pe 's/\\vv{A}/\\vA/g' $filename
  perl -i -pe 's/\\vv{B}/\\vB/g' $filename
  perl -i -pe 's/\\vv{C}/\\vC/g' $filename
  perl -i -pe 's/\\vv{D}/\\vD/g' $filename
  perl -i -pe 's/\\vv{\\Delta}/\\vDelta/g' $filename
  perl -i -pe 's/\\vv{E}/\\vE/g' $filename
  perl -i -pe 's/\\vv{F}/\\vF/g' $filename
  perl -i -pe 's/\\vv{G}/\\vG/g' $filename
  perl -i -pe 's/\\vv{\\Gamma}/\\vGamma/g' $filename
  perl -i -pe 's/\\vv{H}/\\vH/g' $filename
  perl -i -pe 's/\\vv{I}/\\vI/g' $filename
  perl -i -pe 's/\\vv{J}/\\vJ/g' $filename
  perl -i -pe 's/\\vv{K}/\\vK/g' $filename
  perl -i -pe 's/\\vv{L}/\\vL/g' $filename
  perl -i -pe 's/\\vv{\\Lambda}/\\vLambda/g' $filename
  perl -i -pe 's/\\vv{M}/\\vM/g' $filename
  perl -i -pe 's/\\vv{N}/\\vN/g' $filename
  perl -i -pe 's/\\vv{O}/\\vO/g' $filename
  perl -i -pe 's/\\vv{\\Omega}/\\vOmega/g' $filename
  perl -i -pe 's/\\vv{P}/\\vP/g' $filename
  perl -i -pe 's/\\vv{\\Phi}/\\vPhi/g' $filename
  perl -i -pe 's/\\vv{\\Pi}/\\vPi/g' $filename
  perl -i -pe 's/\\vv{\\Psi}/\\vPsi/g' $filename
  perl -i -pe 's/\\vv{Q}/\\vQ/g' $filename
  perl -i -pe 's/\\vv{R}/\\vR/g' $filename
  perl -i -pe 's/\\vv{S}/\\vS/g' $filename
  perl -i -pe 's/\\vv{\\Sigma}/\\vSigma/g' $filename
  perl -i -pe 's/\\vv{T}/\\vT/g' $filename
  perl -i -pe 's/\\vv{U}/\\vU/g' $filename
  perl -i -pe 's/\\vv{\\Upsilon}/\\vUpsilon/g' $filename
  perl -i -pe 's/\\vv{V}/\\vV/g' $filename
  perl -i -pe 's/\\vv{W}/\\vW/g' $filename
  perl -i -pe 's/\\vv{X}/\\vX/g' $filename
  perl -i -pe 's/\\vv{\\Xi}/\\vXi/g' $filename
  perl -i -pe 's/\\vv{Y}/\\vY/g' $filename
  perl -i -pe 's/\\vv{Z}/\\vZ/g' $filename
  perl -i -pe 's/\\vv{a}/\\va/g' $filename
  perl -i -pe 's/\\vv{\\alpha}/\\valpha/g' $filename
  perl -i -pe 's/\\vv{b}/\\vb/g' $filename
  perl -i -pe 's/\\vv{\\beta}/\\vbeta/g' $filename
  perl -i -pe 's/\\vv{c}/\\vc/g' $filename
  perl -i -pe 's/\\vv{\\chi}/\\vchi/g' $filename
  perl -i -pe 's/\\vv{d}/\\vd/g' $filename
  perl -i -pe 's/\\vv{\\delta}/\\vdelta/g' $filename
  perl -i -pe 's/\\vv{e}/\\ve/g' $filename
  perl -i -pe 's/\\vv{\\epsilon}/\\vepsilon/g' $filename
  perl -i -pe 's/\\vv{\\eta}/\\veta/g' $filename
  perl -i -pe 's/\\vv{f}/\\vf/g' $filename
  perl -i -pe 's/\\vv{g}/\\vg/g' $filename
  perl -i -pe 's/\\vv{\\gamma}/\\vgamma/g' $filename
  perl -i -pe 's/\\vv{h}/\\vh/g' $filename
  perl -i -pe 's/\\vv{i}/\\vi/g' $filename
  perl -i -pe 's/\\vv{\\iota}/\\viota/g' $filename
  perl -i -pe 's/\\vv{j}/\\vj/g' $filename
  perl -i -pe 's/\\vv{k}/\\vk/g' $filename
  perl -i -pe 's/\\vv{\\kappa}/\\vkappa/g' $filename
  perl -i -pe 's/\\vv{l}/\\vl/g' $filename
  perl -i -pe 's/\\vv{\\lambda}/\\vlambda/g' $filename
  perl -i -pe 's/\\vv{m}/\\vm/g' $filename
  perl -i -pe 's/\\vv{\\mu}/\\vmu/g' $filename
  perl -i -pe 's/\\vv{n}/\\vn/g' $filename
  perl -i -pe 's/\\vv{\\nu}/\\vnu/g' $filename
  perl -i -pe 's/\\vv{o}/\\vo/g' $filename
  perl -i -pe 's/\\vv{\\omega}/\\vomega/g' $filename
  perl -i -pe 's/\\vv{p}/\\vp/g' $filename
  perl -i -pe 's/\\vv{\\phi}/\\vphi/g' $filename
  perl -i -pe 's/\\vv{\\pi}/\\vpi/g' $filename
  perl -i -pe 's/\\vv{\\psi}/\\vpsi/g' $filename
  perl -i -pe 's/\\vv{q}/\\vq/g' $filename
  perl -i -pe 's/\\vv{r}/\\vr/g' $filename
  perl -i -pe 's/\\vv{\\rho}/\\vrho/g' $filename
  perl -i -pe 's/\\vv{s}/\\vs/g' $filename
  perl -i -pe 's/\\vv{\\sigma}/\\vsigma/g' $filename
  perl -i -pe 's/\\vv{t}/\\vt/g' $filename
  perl -i -pe 's/\\vv{\\tau}/\\vtau/g' $filename
  perl -i -pe 's/\\vv{\\theta}/\\vtheta/g' $filename
  perl -i -pe 's/\\vv{u}/\\vu/g' $filename
  perl -i -pe 's/\\vv{\\upsilon}/\\vupsilon/g' $filename
  perl -i -pe 's/\\vv{\\varepsilon}/\\vvarepsilon/g' $filename
  perl -i -pe 's/\\vv{\\varphi}/\\vvarphi/g' $filename
  perl -i -pe 's/\\vv{\\varrho}/\\vvarrho/g' $filename
  perl -i -pe 's/\\vv{\\vartheta}/\\vvartheta/g' $filename
  perl -i -pe 's/\\vv{v}/\\vvv/g' $filename
  perl -i -pe 's/\\vv{w}/\\vw/g' $filename
  perl -i -pe 's/\\vv{x}/\\vx/g' $filename
  perl -i -pe 's/\\vv{\\xi}/\\vxi/g' $filename
  perl -i -pe 's/\\vv{y}/\\vy/g' $filename
  perl -i -pe 's/\\vv{z}/\\vz/g' $filename
  perl -i -pe 's/\\vv{\\zeta}/\\vzeta/g' $filename
fi;

#perl -i -pe 's/\\vv\{A\}/\\vvA/g' $filename
#perl -i -pe 's/\\vv\{B\}/\\vvB/g' $filename
#perl -i -pe 's/\\vv\{X\}/\\vvX/g' $filename
#perl -i -pe 's/\\vv\{Y\}/\\vvY/g' $filename
#perl -i -pe 's/\\vv\{U\}/\\vvU/g' $filename

# \vv{x} -> \xx
# \vv{v} -> \vvv

# \mathcal{V} \calV

# \mathbb{R} -> \bbR
if [[ 0 == 1 ]]; then
  perl -i -pe 's/\\mathbb\{(\S)\}/\\bb$1/g' $filename
fi;

if [[ 0 == 1 ]]; then
  # \def\scD{\mathcal{D}}
  # \scD{ -> \calD
  #perl -i -pe 's/\\sc(\S)/\\cal$1/g; s/\\sc(\S)/\\cal$1/g; s/\\sc(\S)/\\cal$1/g; ' $filename
  perl -i -pe 's/\\sc(\S)/\\cal$1/g' $filename
  perl -i -pe 's/\\mathcal\{(\S)\}/\\cal$1/g' $filename
fi;

# \text{Poisson}
if [[ 0 == 1 ]]; then
  perl -i -pe 's/\sim N/\\sim \\N/g' $filename

  perl -i -pe 's/\\text\{Exp\}/\\Exponential/g' $filename
  perl -i -pe 's/\\text\{Exponential\}/\\Exponential/g' $filename

  perl -i -pe 's/\\text\{Poisson\}/\\Poisson/g' $filename
  perl -i -pe 's/sim Poisson/sim \\Poisson/g' $filename

  perl -i -pe 's/sim LogN/sim \\LogNormal/g' $filename
  perl -i -pe 's/\\text\{LogN\}/\\LogNormal/g' $filename
fi;

if [[ 0 == 1 ]]; then
  perl -i -pe 's/\\tilde{y}/\\ty/g' $filename
fi;

if [[ 0 == 1 ]]; then
  #perl -i -pe 's/cartesian/Cartesian/g' $filename
  #perl -i -pe 's/^  -/    -/g' $filename

  perl -i -pe 's/\\mathbb\{(\S)\}/\\bb$1/g' $filename
  perl -i -pe 's/\\mathcal\{(\S)\}/\\cal$1/g' $filename

  # Conditioning
  # perl -i -pe 's/\s*\|\s*(?!\|)/ \| /g' $filename
  # Government
  perl -i -pe 's/government/Government/g' $filename
  # doesn't -> does not
  # can't -> cannot 
  # it's -> it is
  # with respect to
  perl -i -pe "s/doesn't/does not/g; s/can't/cannot/g; s/it's/it is/g; s/they're/they are/g; s/isn't/is not/g; s/aren't/ are not/g; s/wrt /with respect to /g" $filename

  # Empty chars at the end.
  #perl -i -pe 's/^(.*\S)\s+$/$1/g' $filename
  # Two empty lines.
  #perl -i -pe 's/^(.*\S)\s+$/$1/g' $filename

  # One line for $$ ... $$
  #perl -i -pe 's/^\s*\$\$(.*)\$\$/    \$\$$1\$\$/g' $filename
  #perl -i -pe 's/^\s*=/    =/g' $filename
  #perl -i -pe 's/^\s+(.*)\\\\\s*$/    $1\\\\\n/g' $filename

  # ||.|| -> norm
  perl -i -pe 's/\|\|(.*?)\|\|/\\norm{$1}/g' $filename

fi;

if [[ 0 == 1 ]]; then
  perl -i -pe 's/\\verb\|(.*?)\|/`$1`/g' $filename
  perl -i -pe 's/\\verb\?(.*?)\?/`$1`/g' $filename
  perl -i -pe 's/\\texttt\{(.*?)\}/`$1`/g' $filename
  # \begin{small}\begin{verbatim}
  perl -i -pe 's/^.*\\begin\{verbatim\}.*$/```/g' $filename
  # \end{verbatim}\end{small}
  perl -i -pe 's/^.*\\end\{verbatim\}.*$/```/g' $filename
  # `a'
  #perl -i -pe 's/`(\S+)\'/"$1"/g' $filename

  perl -i -pe 's/\\text{[dD]et\}/\\Det/g' $filename
  perl -i -pe 's/\\text\{[tT]r\}/\\Tr/g' $filename
  perl -i -pe 's/\\text\{[dD]iag\}/\\Diag/g' $filename
fi;

#perl -i -pe 's/\`(.*)\'/"$1"/g' $filename

perl -i -pe 's/^\\textit\{(.*)\}/- ___$1___/g'

# #############################################################################
if [[ 1 == 1 ]]; then
  pandoc.sh --no_open_pdf $filename
fi;
