

<!-- toc -->

- [Reading other people code](#reading-other-people-code)
- [What not to do](#what-not-to-do)
  * [Rewrite coding](#rewrite-coding)
  * [Incremental renovation](#incremental-renovation)
  * [It's harder to read code than to write it](#its-harder-to-read-code-than-to-write-it)
  * [Respect old code!](#respect-old-code)
  * [What makes code a mess?](#what-makes-code-a-mess)
- [What to do](#what-to-do)
  * [Get into the right attitude](#get-into-the-right-attitude)
  * [Reading other people code is painful](#reading-other-people-code-is-painful)
  * [Suggestions on how to read code](#suggestions-on-how-to-read-code)
- [Refs](#refs)

<!-- tocstop -->

# Reading other people code

- People don't like reading other people's code
  - Still reading existing code needs to be done
  - Nobody can code in a vacuum

- When done with the right attitude, reading code can be enjoyable, and you can
  actually learn and improve as a coder
  - E.g., writers read and study other writers' book to improve

# What not to do

## Rewrite coding

- You think "This code is a complete ugly mess. It needs to be rewritten"
  - The answer is: ABSOLUTELY NO!

- The best case of a code rewrite is to have:
  - The same code (in reality is likely that new bugs entered the system)
  - With a different complexity that you only now understand
  - After a long time and effort

- In other terms, there is no reason to believe that you are going to do a
  better job than others did

## Incremental renovation

- The first thing that programmers want to do is to bulldoze the place flat and
  build something great

- Nobody is excited about incremental renovation:
  - Improving
  - Refactoring
  - Cleaning out
  - Adding unit tests
- In reality, 99.9% of work is incremental

## It's harder to read code than to write it

- For this reason code reuse is hard
- For this reason, everybody on the team has the same function to do the same
  thing
- It's easier and more fun to write new code than figuring out how the old code
  works

## Respect old code!

- When you think "the old code is a mess", you are probably wrong

- The idea that new code is better than old code is absurd
  - Old code has been used
  - Old code has been tested
  - Lots of bugs in old code have been found and fixed

- When the code looks a mess is because it handles many corner cases you didn't
  even think about, you didn't even know were possible
  - Each of that bug took a long time to be discovered and fixed it

- When you throw away code and start from scratch, you are throwing away all the
  knowledge, all the bug fixes, all the hard thinking

## What makes code a mess?

- What makes the code a "mess" (at least according to your expert opinion as
  world-class coder):

1. Architectural problems
   - E.g.,
     - Code is not split into pieces in a way that makes sense
     - Interfaces that are too broad and brittle

- These problems can be easily fixed!

2. Inefficiency
   - Profile and find what is the problem and fix that

3. Ugly
   - E.g., horrible variable and function names
   - It takes 5 minutes of search-and-replace

- All these problems can be easily fixed in 100x less time than rewriting

# What to do

## Get into the right attitude

1. Assume that whoever wrote the code knew what he/she was doing
   - If that's not the case, he/she would have already been fired from the team
   - Therefore he/she is as competent than you

2. Sorry for the bad news, but no, you are not the best coder on planet Earth
   - So be humble

3. "Why is the code so complicated? I would have done XYZ and make it much
   simpler?"
   - There is no reason to believe that you can write the code in a simpler way
   - The complexity is almost always needed to solve the complex problem we have

## Reading other people code is painful

- The problem is that code reflects the thought process of the person who wrote
  the code
  - The goal of the style guide, code writing guide, linter is precisely to push
    us to write code consistently so that it's less painful to read

- When you write code first hand, you think about it, and you build your mental
  model
  - You see the problems, understand them, and then appreciate why a complex
    solution is needed

- Maybe some constraints and specs were not adequately documented
- Maybe there were multiple iterations and compromise between different
  solutions
- Maybe several people were involved
- Maybe a hack solution needed to be added to ship and get the \$1m from the
  customers

## Suggestions on how to read code

- Use `git blame` to understand who wrote the code and over what period of time
  - Knowing the author can help you ask him/her questions directly

- Use the same approach as for a code review

- Budget some time, like a few hours and stick to the process for that amount of
  time
  - Otherwise, after 5 mins you are like "Argh! I can't do this!" and you give
    up

- Read the specs
  - What is the code supposed to do?
  - What are the edge cases to handle?
  - How is it integrated into the rest of the code base?

- Skim through the entire code, top to bottom without reading line-by-line
  - What's the goal?
  - What are the specs?
  - What are the functions?
  - What are the interfaces?
  - What is the structure?

- Read and execute the unit tests, if present

- Run the code with debug output `-v DEBUG` on simple examples to see what it
  does

- Use PyCharm to navigate the code and jump around

- Add comments, when missing, to functions, to chunks of code, to each file
  - Watch out for confusing comments
  - Sometimes a comment can be out of date

- Add TODOs in the code for yourself

- Remember the coding conventions:
  - Global variables are capital letters
  - Functions starting with `_` are just for internals
  - We have all the conventions to convey information about the thought process
    of who wrote the code

- Take down notes about the code
  - Write down the questions about what you don't understand
    - Maybe you will find the answer later (feel free to congratulate yourself!)
    - Send an email to the author with the questions

- Approach reading code as an active form
  - Start writing unit tests for each piece that is not unit tested
  - Step through the code with PyCharm

- Factor out the code
  - Make sure you have plenty of unit tests before touching the code

- Expect to find garbage

- Don't feel bad when you get lost
  - Reading code is not linear, like reading a book
  - Instead, it's about building a mental model of how the code is structured,
    how it works and why it's done in a certain way

- The more code you read, the more comfortable you will become

# Refs

- [How to Read Code (Eight Things to Remember)](https://spin.atomicobject.com/2017/06/01/how-to-read-code`)
- [Things you should never do](https://www.joelonsoftware.com/2000/04/06/things-you-should-never-do-part-i)
