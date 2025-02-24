

<!-- toc -->

  * [Meta](#meta)
  * [To cut and paste](#to-cut-and-paste)
- [News for commodity prediction](#news-for-commodity-prediction)
  * [2015 - The role of news in commodity markets](#2015---the-role-of-news-in-commodity-markets)
- [Social sentiment](#social-sentiment)
  * [2015, Predicting global economic activity with media analytics](#2015-predicting-global-economic-activity-with-media-analytics)
  * [2018 - Twitter, Investor Sentiment and Capital Markets, what do we know?](#2018---twitter-investor-sentiment-and-capital-markets-what-do-we-know)
- [Time series](#time-series)
  * [On-Line Learning of Linear Dynamical Systems: Exponential Forgetting in Kalman Filters](#on-line-learning-of-linear-dynamical-systems-exponential-forgetting-in-kalman-filters)
  * [Predictive State Smoothing (PRESS): Scalable non-parametric regression for high-dimensional data with variable selection](#predictive-state-smoothing-press-scalable-non-parametric-regression-for-high-dimensional-data-with-variable-selection)
  * [2019, High-Dimensional Multivariate Forecasting with Low-Rank Gaussian Copula Processes](#2019-high-dimensional-multivariate-forecasting-with-low-rank-gaussian-copula-processes)
  * [2014, The topology of macro financial flow using stochastic flow diagrams](#2014-the-topology-of-macro-financial-flow-using-stochastic-flow-diagrams)
- [Computer engineering](#computer-engineering)
  * [2015, Hidden technical debt in machine learning systems](#2015-hidden-technical-debt-in-machine-learning-systems)

<!-- tocstop -->

## Meta

- Year - Title
- Paper authors:
- Link to the paper (ideally on gdrive)
- Review author / date
- Score in [0, 5], where:
  - 5/5: Must-read
  - 4/5: Some interesting ideas we can reuse
  - 3/5: Pretty much what one would have done as first experiment
  - 2/5: ...
  - 1/5: Horrible: same bullet-proof logic as in a politician speech
- Summary:
  - At most 5-10 bullet points explaining what the paper tries to accomplish
  - Describe the data used, setup, model formulation, ...
  - Good references
- Praises:
  - At most 5 bullet points
  - Focus on what is different, interesting, and not on the obvious
- Critiques:
  - At most 5 bullet points
  - Explain what is not solid in the analysis, suggestions on how to improve
- Next steps:
  - What next steps should we take, if any, e.g.,
    - Read the bibliography
    - Try experiments

## To cut and paste
```

## Year - Title
- Paper authors:
- [Link]()
- Review author / date:
- Score:
- Summary:
- Praises:
- Critiques:
- Next steps:
```

# News for commodity prediction

## 2015 - The role of news in commodity markets

- Paper authors: Borovkova
- [Link](https://drive.google.com/file/d/1p3Z6W5DPBrDyTGBK__uLE2gNkQDO6VTM/view?usp=sharing)
- Review author / date: GP, 2019-11-22
- Score: 4/5
- Summary:
  - Dataset: prepackaged Thomson-Reuters sentiment (TRNA)
  - Studies the effect of sentiment on commodities through event studies
  - Forecast prices and volatility
- Praises:
  - Decent statistics about the data set
  - States that one needs to understand if the sentiment is attached to demand
    and supply
    - Not sure if TR actually does that
  - Confirms our point about "momentum-related news" (i.e., news about the fact
    that the price is going up)
  - Confirms periodicity we are aware of
  - Interesting local level model to extract the hidden sentiment
    - Very similar to what we thought to do (including the idea of using Kalman
      smoother)
- Critiques:
  - Nothing really
- Next steps:
  - Understand if TR considers sentiment distinguishing supply or demand
    - We should do this (not sure how PR does that)
  - Remove carefully momentum-related news
  - Remove or count carefully repeated news (maybe use a measure of similarity
    between articles)
  - How to deliver "event study" models to customers? Should we "unroll the
    model" for them providing a stream of predictions?

# Social sentiment

## 2015, Predicting global economic activity with media analytics

- Paper authors: Peterson et al.
- Link: In `Tech/papers`
- Review author / date: GP, 2019/12/08
- Score: 2/5
- Summary:
  - Predict PMI indices (which are related to the
- Praises:
  - Interesting approach for going beyond polarity in sentiment considering
- Critiques:
  - No seasonal component
  - Usual problems with methodology OOS
- Next steps:
  - Consider the TRMI "indices" (optimism, fear, joy, trust, violence)
  - Consider the difference in professional news vs social news sentiment
    - What does it mean if there are large statistically significant difference?

## 2018 - Twitter, Investor Sentiment and Capital Markets, what do we know?

- Paper authors:
- Review author: GP, 2019-08-21
- Link:
- Score: 3 / 5
- Summary:
  - Good survey of the literature about social sentiment used for finance
  - Most authors report predictivity of social sentiment for:
  - Different metrics (returns, risk, trading volume)
  - Assets (US stocks, exchange rates, commodities)
  - Events (IPO, earnings)
- Next steps:
  - Read all the bibliography and reproduce some of the results
- TODO: Update this to new template

# Time series

## On-Line Learning of Linear Dynamical Systems: Exponential Forgetting in Kalman Filters

- Paper authors: Mark Kozdoba, Jakub Marecek, Tigran Tchrakian, and Shie Mannor
- Review author: Paul, 2019-12-02
- [arXiv](https://arxiv.org/abs/1809.05870),
  [AAAI](https://www.aaai.org/ojs/index.php/AAAI/article/view/4307)
- Score: 4/5
- Summary:
  - Interesting insight into how to approximate a non-convex optimization
    problem with an approximate convex one
  - Shows that for observable Linear Dynamical Systems with non-degenerate
    noise, the dependence of the Kalman filter on the past decays exponentially
  - For this class of systems, predictions may be modeled as autoregressions. In
    practice, not many terms are needed for a "good" approximation.
  - The algorithm is on-line
  - Comparison to the Kalman filter is formalized with regret bounds
  - IBM / Technion research
  - The setting is one where we are learning the best fixed but unknown
    autoregression coefficients (rather than one where we are interested in
    truly dynamic updates)
    - The learning rate decays like $1 / \sqrt{t}$, and so under some mild
      constraints on the time series being modeled, the autoregression
      coefficients converge
    - The linear dynamical system setup considered is one where the state
      transition matrix and the observation direction are time-independent
- Praises:
  - References standard big works in the time series literature, like West and
    Harrison (1997) and Hamilton (1994)
  - Introduces a relatively simple online technique that competes well with the
    more complex Kalman filter
- Critiques:
  - Bounds / constants aren't quantitative
- Next steps:
  - Look at the code accompanying the paper:
    https://github.com/jmarecek/OnlineLDS
  - Implement and compare to, e.g., z-scoring (a particularly simple case of
    Kalman filtering)
  - If we have a long history, it may be better to perform a single
    autoregression over the whole history
    - This suggests
  - What if we keep the learning rate fixed over time?
    - This would effectively allow for "drifting" dynamics
    - The proofs of the results of the paper would no longer apply
    - It isn't obvious how the learning rate ought to be chosen

## Predictive State Smoothing (PRESS): Scalable non-parametric regression for high-dimensional data with variable selection

- Paper author: Georg M. Goerg
- Review author: Paul, 2019-12-03
- [Link](https://storage.googleapis.com/pub-tools-public-publication-data/pdf/b91400f14e27ec9dacf0a389e72fd0e0fa9c2535.pdf)
- Score: 4/5
- Summary:
  - A kernel smoother, but unlike traditional ones, it
    - Allows non-local (with respect to the x-var space) pooling
    - Is scalable (e.g., computationally efficient)
  - PRESS is a generative, probabilistic model
  - States are interpretable
  - Compatible with deep neural networks (though experiments referenced in the
    paper suggest depth doesn't help, e.g., a wide net with one softmax is
    enough)
  - Competitive with SVMs, Random Forests, and DNN
  - > Predictive state representations are statistically and computationally
    > efficient for obtaining optimal forecasts of non-linear dynamical systems
    > (Shalizi and Crutchfield, 2001). Examples include time series forecasting
    > via epsilon-machines (Shalizi and Shalizi, 2004)...
- Praises:
  - Combines some clever insights
  - References a TensorFlow implementation and suggests that implementing in
    various frameworks is straightforward
- Critiques:
  - No pointers to actual implementations
  - Time series applications are referenced in Section 2, but many relevant (to
    our work) practical ts-specific points are not developed in the paper
- Next steps:
  - See if someone has already implemented PRESS publicly
  - If no implementation is available, scope out how much work a minimal
    pandas-compatible implementation would require

## 2019, High-Dimensional Multivariate Forecasting with Low-Rank Gaussian Copula Processes

- Paper authors: David Salinas, Michael Bohlke-Schneider, Laurent Callot,
  Roberto Medico, Jan Gasthaus
- Review author: Paul, 2019-12-28
- [arXiv](https://arxiv.org/abs/1910.03002)
- Score: 4/5
- Summary:
  - Learns covariance structure and model together
  - Handles series with time-varying, high-dimensional covariance structure
  - Simultaneously handles series at different scales (in terms of the range)
  - Uses a non-linear, deterministic state space model with transition dynamics
    parametrized using an LSTM-RNN
- Praises:
  - Implemented in GluonTS (https://github.com/awslabs/gluon-ts/pull/497) by one
    of the coauthors who works on time series forecasting at AWS
  - Code for the paper at
    https://github.com/mbohlkeschneider/gluon-ts/tree/mv_release
  - Good choice of baselines comparisons
  - Demonstrates the importance of data transformations
- Next steps:
  - Use in cases where we have a large number of time series known to have
    meaningful correlations

## 2014, The topology of macro financial flow using stochastic flow diagrams

- Paper authors: Calkin, De Prado
- [Link](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2379319)
- Review author / date: GP, 2020-01-17
- Score: 1 / 5
- Summary:
- Praises:
  - PCA on futures sectors
  - Interesting graphical representation
    - Width of the arc represents strength of relationship (in terms of $R^2$)
    - Color (green / red) and intensity represent sign and magnitude
    - Lags are delays
    - Geometric topology represents relationships better than tables
    - Connectivity of a vertex represents importance
  - Agreed that econometrics as it is, is close to a pseudo-science that more
    complex techniques are needed than inverting a matrix
- Critiques:
  - Various inflammatory remarks and very little content
- Next steps:
  - None

# Computer engineering

## 2015, Hidden technical debt in machine learning systems

- Paper authors: Sculler et al.
- [Link](http://papers.nips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems.pdf)
- Review author / date: GP, 2020-01-07
- Score: 4/5
- Summary:
  - Many interesting little observations about ML practices and engineering
- Praises:
  - Validates how approach of minimizing technical debt and paying it off the
    interest, e.g.,
    - Treat configuration as code, as we do
    - Design abstraction carefully
    - Routinely clean up the code
    - No distinction in quality between research and production
    - Use a single language for everything
    - Need for committing to the healthy engineering practices
- Critiques:
  - None
- Next steps:
  - None
