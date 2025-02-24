

<!-- toc -->

- [Asyncio Best Practices](#asyncio-best-practices)
  * [Nomenclature in asyncio](#nomenclature-in-asyncio)
  * [Common Pitfalls and Solutions](#common-pitfalls-and-solutions)
    + [1. Avoid Running Multiple Event Loops](#1-avoid-running-multiple-event-loops)
      - [Example Code](#example-code)
    + [2. time.sleep() vs asyncio.sleep()](#2-timesleep-vs-asynciosleep)

<!-- tocstop -->

# Asyncio Best Practices

Asynchronous programming is a powerful paradigm in Python that allows you to
write non-blocking, concurrent code that can greatly improve the efficiency of
your applications when I/O and computation can be overlapped.

The official documentation is https://docs.python.org/3/library/asyncio.html
This document provides an overview of how asyncio works and offers best
practices to avoid common pitfalls.

## Nomenclature in asyncio

- Event Loop

  - asyncio operates on an event loop that manages the execution of asynchronous
    tasks. Whenever one wants to execute the asynchronous tasks we do
    `asyncio.run()` or `asyncio.run_until_complete()`: both of these methods
    will start the event loop and it will be set to running yielding control to
    it.
  - In asyncio, you can obtain the event loop using either
    `asyncio.get_event_loop()` or `asyncio.get_running_loop()`. In the latest
    version of asyncio, both methods now serve the same purpose. However, it is
    recommended to use `get_running_loop` because `get_event_loop` has been
    deprecated since version 3.12. This change ensures consistency and future
    compatibility with asyncio.

- Coroutines (aka "async functions" defined with `async def`)

  - These functions can be paused and resumed without blocking other tasks.

- `await`
  - The `await` keyword is used only within coroutines to pause execution until
    an asynchronous operation (e.g., I/O) is completed. While waiting, the event
    loop can execute other tasks.

## Common Pitfalls and Solutions

### 1. Avoid Running Multiple Event Loops

One common error is `Event loop is already running`. When you use
`asyncio.run()` or `run_until_complete()`, the event loop is started. Attempting
to start a new event loop while one is already running will result in this
error.

To avoid this:

- Solution 1: use `nest_asyncio`

  - `nest_asyncio` is a library that allows you to create nested event loops.
    While this may seem like a solution but may lead to complex issues. This was
    mainly developed to run `asyncio` in Jupyter/ipython which already runs an
    event loop in backend. This library also does not support
    `asyncio_solipsism` so there is another trade-off.

  - Here's how nest_asyncio works:
    - It saves the current event loop, if any, that is running in the
      environment.
    - It sets up a new event loop specifically for running asyncio code.
    - You can run your asyncio code within this nested event loop.
    - When you're done running asyncio code, `nest_asyncio` restores the
      original event loop, ensuring compatibility with the environment.

- Solution 2: use threads

  - Instead of starting a new event loop, run that specific part of your code in
    a separate thread to prevent conflicts. This solves the issue but using
    thread has its own complications such as race conditions which can be
    difficult to debug

- Solution 3: embrace "async all the way up" approach
  - use `await` instead of nested call to `asyncio.run` and make your methods
    asynchronous using `async def` all the way

#### Example Code

Consider the following coroutines

- `A` that sleeps and then calls `B`
- `B` which calls `C`
- `C` sleeps

  ```mermaid
  graph TD
      A[async def A] --> B[def B]
      B -->C[ async def C]

      style A fill:#FFA07A, stroke:#FF6347
      style B fill:#98FB98, stroke:#2E8B57
      style C fill:#ADD8E6, stroke:#4682B4
  ```

  ```
  import asyncio
  import helpers.hasyncio as hasynci


  # Corresponds to `submit twap` in CmampTask5842
  async def A():
      print("IN A")
      await asyncio.sleep(2)
      print("ENTER B")
      B()


  # Corresponds to `get_fill_per_order`
  async def C():
      print("IN C")
      await asyncio.sleep(2)
      print("EXIT C")


  # get_fill
  def B():
      print("IN B")
      cor = C()
      asyncio.get_running_loop().run_until_complete(cor)
      print("EXIT B")


  # Call A.
  hasynci.run(A(), asyncio.get_event_loop(), close_event_loop=False)
  ```

- The code above won't work and will give

  ```
  Error: "Event loop is already running"
  ```

  This error arises because, when `run()` is invoked, it initializes the event
  loop on the current thread. Subsequently, if `run()` is called within the
  function `B()`, the system checks for the running state of the event loop. If
  the event loop is already in progress, the system raises the 'Event loop is
  already running' error."

- Adding

  ```
  import nest_asyncio

  nest_asyncio.apply()
  ```

  the code above will work

- If `nest_asyncio` is present the following code does not work
  ```
  with hasynci.solipsism_context() as event_loop:
    hasynci.run(A(), event_loop, close_event_loop=False)
  ```
  failing with the error
  ```
  Error: "Event loop is already running"
  ```

### 2. time.sleep() vs asyncio.sleep()

One common error is to use `time.sleep()` with asynchronous methods.

This blocks the execution of that method and the event loop cannot proceed to
task until the sleep period is over. This negates the primary purpose of the
asyncio and doesn't allow us to simulate systems with `solipsism`.

We should almost never use this, and use `asyncio.sleep` instead.
