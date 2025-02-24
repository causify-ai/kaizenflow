

<!-- toc -->

- [Time semantics](#time-semantics)
- [How clock is handled](#how-clock-is-handled)
  * [Asynchronous mode](#asynchronous-mode)
  * [Synchronous mode](#synchronous-mode)
  * [Async vs sync simulation](#async-vs-sync-simulation)
  * [Some cross-products of the 3 directions](#some-cross-products-of-the-3-directions)
  * [Research mode](#research-mode)
  * [Real-time mode](#real-time-mode)
  * [Historical](#historical)
- [Flows](#flows)
  * [Forecast flow](#forecast-flow)
  * [Pnl (profit and loss) flow](#pnl-profit-and-loss-flow)
  * [Research flow](#research-flow)
  * [Real-time flow](#real-time-flow)

<!-- tocstop -->

# Time semantics

**Time semantics**. Any DataFlow component can be executed in real-time or
simulated accounting for different ways to represent the passing of time.

E.g., it can be simulated depending on how data is delivered to the system

- A streaming (aka timed simulation according to knowledge time) or
- Batch (non-timed simulation, with different tile chunking)

**Clock.** A function that reports the current timestamp. There are 3 versions
of clock:

1.  Static clock. A clock that remains the same during a system run.

    a. Future peeking is allowed

2.  Replayed clock. A moving clock that can be in the past or future with
    respect to a real clock

    a. Use time passing at the same pace of real-time wall-clock or

    b. Simulate time based on events, e.g., as soon as the workload
    corresponding to one timestamp is complete we move to the next timestamp,
    without waiting for the actual time to pass

    c. Future peeking is technically possible but is prohibited

3.  Real clock. The wall-clock time matches what we observe in real-life, data
    is provided to processing units as it is produced by systems.

    a. Future peeking is not possible in principle

**Knowledge time.** It is the time when data becomes available (e.g., downloaded
or computed) to a system. Each row of data is tagged with the corresponding
knowledge time. Data with knowledge time after the current clock time must not
be observable in order to avoid future peeking.

**Timed simulation**. Sometimes referred to as historical, vectorized, bulk,
batch simulation. In a timed simulation the data is provided with a clock that
reports the current timestamp. Data with knowledge time after the current
timestamp must not be observable in order to avoid future peeking.

TODO(gp): Add an example of df with forecasts explaining the timing

**Non-timed simulation**. (Sometimes referred to as event-based, reactive
simulation). Clock type is "static clock". Typically wall-clock time is a
timestamp that corresponds to the latest knowledge time (or greater) in a
dataframe. In this way all data in a dataframe is available because every row
has a knowledge time that is less than or equal to the wall-clock time. Note
that the clock is static, i.e. not moving. In a non-timed simulation, the data
is provided in a dataframe for the entire period of interest.

E.g., for a system predicting every 5 mins, all the input data are equally
spaced on a 5-min grid and indexed with knowledge time.

TODO(gp): Add an example of df with forecasts explaining the timing

```python
df["c"] = (df["a"] + df["b"]).shift(1)
```

**Real-time execution**. In real-time the clock type is "real clock".

E.g., for a system predicting every 5 mins, one forecast is delivered every 5
mins of wall-clock.

TODO(Grisha): add an example.

**Replayed simulation**. In replayed simulation, the data is provided in the
same "format" and with the same timing as it would be provided in real-time, but
the clock type is "replayed clock".

# How clock is handled

## Asynchronous mode

- In asynchronous mode there are multiple things happening at the same time
  - E.g., DAG computes, orders are sent to the market, some components wait
- It is implemented using Python `asyncio`
  - In general one should need multiple CPUs to simulate/execute a truly
    asynchronous system
  - E.g, one CPU executes/simulates the DAG, another CPU executes/simulates the
    `Portfolio`, etc.

## Synchronous mode

- In synchronous mode only one thing happens at the same time
  - E.g., executing a piece of code using Pandas

## Async vs sync simulation

- We can simulate the same system in sync or async mode

- Sync
  - The DAG computes
  - Passes the df to OMS
  - The OMS executes orders, updates the Portfolio, ...

- Async
  - Create different objects that are always active and need to block on each
    other
  - Under certain constraints (e.g., when I/O overlaps with computation) a
    single CPU can run/simulate a truly asynchronous system

## Some cross-products of the 3 directions

- Not all the combinations are possible of mixing:
  - Historical vs replayed vs real-time
  - Reference vs mocked vs implemented
  - Async vs sync

- The execution of a DAG can be historical + synchronous
  - We feed the entire history of data as a single DataFrame
  - The computation is vectorized and synchronous (in one shot)

- The execution of a DAG can be replayed and async
  - The DAG waits for new data to come in
  - 5-mins of (historical) data arrives every 5 minutes
  - The computation is carried out only for that period of time
  - The DAG goes back to waiting

- The execution of a DAG can be real-time and async
  - Same as above but the data comes from a real-time source (e.g., DB)

A system is composed of

- Intermediate step: RT / Mocked EG

- RT / EG

- We have the part that places orders

- We don't have the part that reads the state back

) Historical / EG

- We can't do this since they don't provide the right interface

6\) Historical / Mocked EG

- It is possible

- INV: portfolio persists across invocations of `place_orders()` in RT mode
- It doesn't make a difference for batch mode, since there is a single
  invocation of `place_orders`

- INV: portfolio is created and passed inside the config. It doesn't need to be
  passed back since the "pointer" to it is passed back-and-forth
- For batch mode, we have all the forecasts (they are computed in one shot) the
  Portfolio can be populated with all the trades and then discarded.
- In fact we have a loop that does exactly that
- We can run the portfolio in "debug mode" where we have a precomputed df

## Research mode

- Run the DAG without `process_forecast`
- Save ResultBundles
- Use the notebook to read the ResultBundle and compute pnl
- "Research pnl" is the pnl we compute from the research mode
  - Dot product + volatility normalization + target GMV + other magic
  - TODO(Paul): to formally defined

## Real-time mode

- Run DAG one step at the time using RealTimeDataSource and MarketDataInterface
- Save ResultBundle / intermediate state
- Compute rolling pnl

## Historical

- Do all the predictions and then run the SimulatedPortfolio
  (DataFramePortfolio) one step at the time
- Maybe useful for "looping" around the Optimizer

# Flows

- Evaluating a model requires computing forecasts and then the corresponding PnL

## Forecast flow

- = compute forecasts from data using the DAG
- It can be historical, replayed, real-time
- The outcome is a data frame with all the forecasts

## Pnl (profit and loss) flow

- = given forecasts and prices compute the corresponding PnL
- It can be computed using:
  - Dot product approach (pnl = \\sum f^T \\dot rets\_{t-2})
  - Prices and positions
    - Without Portfolio and Broker, but a simplified approach
  - Order by order
    - Using Portfolio and Broker

Some configurations are used more often than others, and so we give them a
specific name

## Research flow

- = historical flow for computing + dot product
- We use it to assess the presence of alpha

## Real-time flow

- All components are:
  - Vendor-specific implemented (e.g., TalosImClient, TalosBroker)
  - Executed in real-time and asynchronous
