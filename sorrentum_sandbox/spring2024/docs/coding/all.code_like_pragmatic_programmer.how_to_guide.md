

<!-- toc -->

- [A pragmatic philosophy](#a-pragmatic-philosophy)
  * [PP_Tip 1: Care about your craft](#pp_tip-1-care-about-your-craft)
  * [PP_Tip 2: Think! About your work](#pp_tip-2-think-about-your-work)
  * [PP_Tip 3: Provide options, don't make lame excuses](#pp_tip-3-provide-options-dont-make-lame-excuses)
  * [Broken windows](#broken-windows)
  * [PP_Tip 4: Don't live with broken windows](#pp_tip-4-dont-live-with-broken-windows)
  * [PP_Tip 5: Be a catalyst for change](#pp_tip-5-be-a-catalyst-for-change)
  * [PP_Tip 6: Remember the big picture](#pp_tip-6-remember-the-big-picture)
  * [PP_Tip 7: Make quality a requirement issue](#pp_tip-7-make-quality-a-requirement-issue)
  * [PP_Tip 8: Invest regularly in your knowledge portfolio](#pp_tip-8-invest-regularly-in-your-knowledge-portfolio)
  * [PP_Tip 9: Critically analyze what you read and hear](#pp_tip-9-critically-analyze-what-you-read-and-hear)
  * [PP_Tip 10: It's both what you say and the way you say it](#pp_tip-10-its-both-what-you-say-and-the-way-you-say-it)
  * [PP_Tip 10: Remember the WISDOM acrostic](#pp_tip-10-remember-the-wisdom-acrostic)
- [A pragmatic approach](#a-pragmatic-approach)
  * [PP_Tip 11: DRY - Don't repeat yourself](#pp_tip-11-dry---dont-repeat-yourself)
  * [PP_Tip 11: Programs = knowledge](#pp_tip-11-programs--knowledge)
  * [PP_Tip 11: How does duplication arise?](#pp_tip-11-how-does-duplication-arise)
  * [PP_Tip 11: Imposed duplication](#pp_tip-11-imposed-duplication)
  * [PP_Tip 11: Inadvertent duplication](#pp_tip-11-inadvertent-duplication)
  * [PP_Tip 11: Impatient duplication](#pp_tip-11-impatient-duplication)
  * [PP_Tip 11: Inter-developer duplication](#pp_tip-11-inter-developer-duplication)
  * [PP_Tip 12: Make it easy to reuse](#pp_tip-12-make-it-easy-to-reuse)
  * [Orthogonality](#orthogonality)
  * [PP_Tip 13: Eliminate effects between unrelated things](#pp_tip-13-eliminate-effects-between-unrelated-things)
  * [PP_Tip 13: Orthogonality: pros](#pp_tip-13-orthogonality-pros)
  * [PP_Tip 13: How to maintain orthogonality](#pp_tip-13-how-to-maintain-orthogonality)
  * [PP_Tip 14: There are no final decisions](#pp_tip-14-there-are-no-final-decisions)
  * [PP_Tip 14: There are no final decisions: why](#pp_tip-14-there-are-no-final-decisions-why)
  * [PP_Tip 15: Use tracer bullets to find the target](#pp_tip-15-use-tracer-bullets-to-find-the-target)
  * [Analogy between shooting bullets in the dark and software engineering](#analogy-between-shooting-bullets-in-the-dark-and-software-engineering)
  * [PP_Tip 15: Tracer bullets: pros](#pp_tip-15-tracer-bullets-pros)
  * [PP_Tip 15: Tracer bullets: cons](#pp_tip-15-tracer-bullets-cons)
  * [PP_Tip 16: Prototype to learn](#pp_tip-16-prototype-to-learn)
  * [PP_Tip 16: Prototype to learn: cons](#pp_tip-16-prototype-to-learn-cons)
  * [PP_Tip 16: Tracer code vs prototyping](#pp_tip-16-tracer-code-vs-prototyping)
  * [PP_Tip 17: Program close to the problem domain](#pp_tip-17-program-close-to-the-problem-domain)
  * [PP_Tip 18: Estimate to avoid surprises](#pp_tip-18-estimate-to-avoid-surprises)
  * [PP_Tip 18: How to make estimates](#pp_tip-18-how-to-make-estimates)
  * [PP_Tip 19: Iterate the schedule with the code](#pp_tip-19-iterate-the-schedule-with-the-code)
  * [PP_Tip 19: Estimates at the coffee machine](#pp_tip-19-estimates-at-the-coffee-machine)
- [The basic tools](#the-basic-tools)
  * [PP_Tip 20: Keep knowledge in plain text](#pp_tip-20-keep-knowledge-in-plain-text)
  * [PP_Tip 21: Use the power of command shells](#pp_tip-21-use-the-power-of-command-shells)
  * [PP_Tip 22: Use a single editor well](#pp_tip-22-use-a-single-editor-well)
  * [PP_Tip 23: Always use source code control](#pp_tip-23-always-use-source-code-control)
  * [PP_Tip 23: Advantages of source code control](#pp_tip-23-advantages-of-source-code-control)
  * [PP_Tip 24: Fix the problem, not the blame](#pp_tip-24-fix-the-problem-not-the-blame)
  * [PP_Tip 25: Don't panic](#pp_tip-25-dont-panic)
  * [PP_Tip 25: How to debug](#pp_tip-25-how-to-debug)
  * [PP_Tip 25: Rubber ducking](#pp_tip-25-rubber-ducking)
  * [PP_Tip 25: Why rubber ducking works?](#pp_tip-25-why-rubber-ducking-works)
  * [PP_Tip 26: `select` is not broken](#pp_tip-26-select-is-not-broken)
  * [PP_Tip 27: Don't assume it: prove it](#pp_tip-27-dont-assume-it-prove-it)
  * [PP_Tip 28: Learn a text manipulation language](#pp_tip-28-learn-a-text-manipulation-language)
  * [PP_Tip 29: Write code that writes code](#pp_tip-29-write-code-that-writes-code)
- [Pragmatic paranoia](#pragmatic-paranoia)
  * [PP_Tip 30: You cannot write perfect software](#pp_tip-30-you-cannot-write-perfect-software)
  * [Know when to stop](#know-when-to-stop)
  * [Don't trust others](#dont-trust-others)
  * [Don't trust yourself](#dont-trust-yourself)
  * [Preconditions](#preconditions)
  * [Postconditions](#postconditions)
  * [Class invariants](#class-invariants)
  * [Contracts](#contracts)
  * [PP_Tip 31: Design with contracts](#pp_tip-31-design-with-contracts)
  * [PP_Tip 32: Crash early](#pp_tip-32-crash-early)
  * [PP_Tip 33: If it cannot happen, use assertions to ensure that it won't](#pp_tip-33-if-it-cannot-happen-use-assertions-to-ensure-that-it-wont)
  * [Leave assertions enabled](#leave-assertions-enabled)
  * [PP_Tip 34: Use exceptions for exceptional problems](#pp_tip-34-use-exceptions-for-exceptional-problems)
  * [Exceptions are for unexpected events](#exceptions-are-for-unexpected-events)
  * [PP_Tip 35: Finish what you start](#pp_tip-35-finish-what-you-start)
- [Bend or break](#bend-or-break)
  * [PP_Tip 36: Minimize coupling between modules](#pp_tip-36-minimize-coupling-between-modules)
  * [PP_Tip 36: Law of Demeter for functions](#pp_tip-36-law-of-demeter-for-functions)
  * [PP_Tip 36: Intuition of the Law of Demeter](#pp_tip-36-intuition-of-the-law-of-demeter)
  * [PP_Tip 36: Law of Demeter as general contractor](#pp_tip-36-law-of-demeter-as-general-contractor)
  * [PP_Tip 37: Configure, don't integrate](#pp_tip-37-configure-dont-integrate)
  * [PP_Tip 38: Put abstractions in code, details in metadata](#pp_tip-38-put-abstractions-in-code-details-in-metadata)
  * [Mechanisms vs policies](#mechanisms-vs-policies)
  * [PP_Tip 38: Advantages of splitting mechanisms and policies](#pp_tip-38-advantages-of-splitting-mechanisms-and-policies)
  * [PP_Tip 38: Put business logic in metadata](#pp_tip-38-put-business-logic-in-metadata)
  * [PP_Tip 39: Analyze workflow to improve concurrency](#pp_tip-39-analyze-workflow-to-improve-concurrency)
  * [PP_Tip 40: Temporal coupling](#pp_tip-40-temporal-coupling)
  * [PP_Tip 40: UML activity diagram](#pp_tip-40-uml-activity-diagram)
  * [Service](#service)
  * [PP_Tip 40: Design using services](#pp_tip-40-design-using-services)
  * [PP_Tip 41: Hungry consumer model](#pp_tip-41-hungry-consumer-model)
  * [PP_Tip 41: Always design for concurrency](#pp_tip-41-always-design-for-concurrency)
  * [Examples of problems with concurrency](#examples-of-problems-with-concurrency)
  * [Event](#event)
  * [PP_Tip 42: Objects communicating through events](#pp_tip-42-objects-communicating-through-events)
  * [PP_Tip 42: All events through a single routine approach](#pp_tip-42-all-events-through-a-single-routine-approach)
  * [PP_Tip 42: Publish / subscribe model](#pp_tip-42-publish--subscribe-model)
  * [PP_Tip 42: Sequence diagram](#pp_tip-42-sequence-diagram)
  * [PP_Tip 42: Push / pull model for event services](#pp_tip-42-push--pull-model-for-event-services)
  * [PP_Tip 42: Separate views from models](#pp_tip-42-separate-views-from-models)
  * [PP_Tip 43: Use blackboards to coordinate workflow](#pp_tip-43-use-blackboards-to-coordinate-workflow)
  * [PP_Tip 43: Example of blackboard implementation](#pp_tip-43-example-of-blackboard-implementation)
  * [PP_Tip 43: Example of blackboard application](#pp_tip-43-example-of-blackboard-application)
- [While you are coding](#while-you-are-coding)
  * [PP_Tip 44: Don't program by coincidence](#pp_tip-44-dont-program-by-coincidence)
  * [PP_Tip 44: How to program by coincidence](#pp_tip-44-how-to-program-by-coincidence)
  * [PP_Tip 44: Why program by coincidence seems to work?](#pp_tip-44-why-program-by-coincidence-seems-to-work)
  * [PP_Tip 44: How to program deliberately](#pp_tip-44-how-to-program-deliberately)
  * [PP_Tip 45: Estimate the order of your algorithms](#pp_tip-45-estimate-the-order-of-your-algorithms)
  * [Big-Oh notation](#big-oh-notation)
  * [Estimating Big-Oh](#estimating-big-oh)
  * [Big-Oh in the real world](#big-oh-in-the-real-world)
  * [PP_Tip 46: Test your estimate](#pp_tip-46-test-your-estimate)
  * [Be wary of premature optimization](#be-wary-of-premature-optimization)
  * [Refactoring](#refactoring)
  * [PP_Tip 47: Refactor early, refactor often](#pp_tip-47-refactor-early-refactor-often)
  * [How to refactor](#how-to-refactor)
  * [PP_Tip 47: Software development is more gardening than building](#pp_tip-47-software-development-is-more-gardening-than-building)
  * [PP_Tip 47: When to refactor?](#pp_tip-47-when-to-refactor)
  * [PP_Tip 47: Management and refactoring](#pp_tip-47-management-and-refactoring)
  * [PP_Tip 48: Design to test](#pp_tip-48-design-to-test)
  * [PP_Tip 48: Testing against contract](#pp_tip-48-testing-against-contract)
  * [Test-driven development](#test-driven-development)
  * [PP_Tip 48: Where to put unit tests?](#pp_tip-48-where-to-put-unit-tests)
  * [PP_Tip 48: Provide a test harness](#pp_tip-48-provide-a-test-harness)
  * [PP_Tip 48: Build a test backdoor](#pp_tip-48-build-a-test-backdoor)
  * [PP_Tip 49: Test your software or your users will](#pp_tip-49-test-your-software-or-your-users-will)
  * [PP_Tip 50: Don't use wizard code you don't understand](#pp_tip-50-dont-use-wizard-code-you-dont-understand)
- [Before the project](#before-the-project)
  * [Requirement](#requirement)
  * [PP_Tip 51: Don't gather requirements: dig for them](#pp_tip-51-dont-gather-requirements-dig-for-them)
  * [PP_Tip 51: Example of tricky requirements](#pp_tip-51-example-of-tricky-requirements)
  * [PP_Tip 52: Work with a user to think like a user](#pp_tip-52-work-with-a-user-to-think-like-a-user)
  * [Use cases](#use-cases)
  * [PP_Tip 53: Use cases](#pp_tip-53-use-cases)
  * [PP_Tip 53: Abstractions live longer than details](#pp_tip-53-abstractions-live-longer-than-details)
  * [PP_Tip 53: Feature-itis](#pp_tip-53-feature-itis)
  * [Project glossary](#project-glossary)
  * [PP_Tip 54: Use a project glossary](#pp_tip-54-use-a-project-glossary)
  * [PP_Tip 55: Don't think outside the box: find the box](#pp_tip-55-dont-think-outside-the-box-find-the-box)
  * [PP_Tip 55: Impossible problems](#pp_tip-55-impossible-problems)
  * [PP_Tip 56: Listen to nagging doubts: start when you are ready](#pp_tip-56-listen-to-nagging-doubts-start-when-you-are-ready)
  * [PP_Tip 57: Some things are better done than described](#pp_tip-57-some-things-are-better-done-than-described)
  * [PP_Tip 58: Don't be a slave to formal methods](#pp_tip-58-dont-be-a-slave-to-formal-methods)
  * [PP_Tip 59: Expensive tools do not produce better designs](#pp_tip-59-expensive-tools-do-not-produce-better-designs)
- [Pragmatic projects](#pragmatic-projects)
  * [PP_Tip 60: Pragmatic teams](#pp_tip-60-pragmatic-teams)
  * [PP_Tip 60: Organize around functionality, not job functions](#pp_tip-60-organize-around-functionality-not-job-functions)
  * [PP_Tip 61: Don't use manual procedures](#pp_tip-61-dont-use-manual-procedures)
  * [PP_Tip 62: Test early](#pp_tip-62-test-early)
  * [PP_Tip 62: Test often](#pp_tip-62-test-often)
  * [PP_Tip 62: Test automatically](#pp_tip-62-test-automatically)
  * [PP Top 63: Coding ain't done 'til all the tests run](#pp-top-63-coding-aint-done-til-all-the-tests-run)
  * [PP_Tip 63: What to test](#pp_tip-63-what-to-test)
  * [Unit test](#unit-test)
  * [Integration test](#integration-test)
  * [Validation and verification test](#validation-and-verification-test)
  * [Resource exhaustion, errors, and recovery test](#resource-exhaustion-errors-and-recovery-test)
  * [Performance test](#performance-test)
  * [Usability test](#usability-test)
  * [PP_Tip 63: How to test](#pp_tip-63-how-to-test)
  * [Regression testing](#regression-testing)
  * [Test data](#test-data)
  * [Exercising GUI systems](#exercising-gui-systems)
  * [Testing the tests](#testing-the-tests)
  * [Testing thoroughly](#testing-thoroughly)
  * [PP_Tip 64: Use saboteurs to test your testing](#pp_tip-64-use-saboteurs-to-test-your-testing)
  * [PP_Tip 65: Test state coverage, not code coverage](#pp_tip-65-test-state-coverage-not-code-coverage)
  * [PP_Tip 65: When to test](#pp_tip-65-when-to-test)
  * [PP_Tip 66: Find bugs once](#pp_tip-66-find-bugs-once)
  * [PP_Tip 67: Treat English as just another programming language](#pp_tip-67-treat-english-as-just-another-programming-language)
  * [PP_Tip 68: Internal documentation](#pp_tip-68-internal-documentation)
  * [External documentation](#external-documentation)
  * [Documentation vs code](#documentation-vs-code)
  * [PP_Tip 68: Comments](#pp_tip-68-comments)
  * [Naming concepts](#naming-concepts)
  * [PP_Tip 68: Automatically generated documentation](#pp_tip-68-automatically-generated-documentation)
  * [PP_Tip 69: Gently exceed your users' expectations](#pp_tip-69-gently-exceed-your-users-expectations)
  * [Examples of difference between actual and expected results](#examples-of-difference-between-actual-and-expected-results)
  * [PP_Tip 69: Communicating expectations](#pp_tip-69-communicating-expectations)
  * [Manage expectations](#manage-expectations)
  * [Go the extra mile](#go-the-extra-mile)
  * [PP_Tip 70: Sign your work](#pp_tip-70-sign-your-work)
  * [PP_Tip 70: Code ownership vs anonymity](#pp_tip-70-code-ownership-vs-anonymity)

<!-- tocstop -->

# A pragmatic philosophy

## PP_Tip 1: Care about your craft

- Why spending your life developing software unless you care doing it well?

## PP_Tip 2: Think! About your work

- Turn off the autopilot and take control
- Constantly critique and evaluate your work

## PP_Tip 3: Provide options, don't make lame excuses

- Things go wrong:
  - Deliverables are late
  - Unforeseen technical problems come up
  - Specs are misunderstood
  - ...

- Don't be afraid to admit ignorance or error
- Before saying that something cannot be done, consider what the other people
  are likely to say
  - "Have you tried this?"
  - "Did you consider that?"
  - ...

## Broken windows

- = bad designs, wrong decisions, poor code, rotten software

## PP_Tip 4: Don't live with broken windows

- A broken window left un-repaired instills a sense of abandonment
- Don't live with broken windows un-repaired
  - If there is no time, board it up
  - Take action to show that you are on top of the situation

## PP_Tip 5: Be a catalyst for change

- Sometimes you know what is right, but if you ask for permissions you will be
  slowed down
  - Request for feedback
  - Committees, budgets, ...
  - It's the so-called "startup fatigue"

- It's easier to ask forgiveness, than it is to get permission

## PP_Tip 6: Remember the big picture

- Projects slowly and inexorably get totally out of hand
- Missing a deadline happens one day at a time

## PP_Tip 7: Make quality a requirement issue

- One of the requirements from the user should be "how good do you want the
  software to be?"
- Good software today is better than perfect software tomorrow

## PP_Tip 8: Invest regularly in your knowledge portfolio

- Your knowledge and experience are your most important professional assets
  - Unfortunately they are expiring assets

- It's like investing for retirement

  1. Invest as a habit
     - Study every day
  2. Diversify
     - The more different things you know, the more valuable you are
  3. Balance conservative and high-risk / high-reward investments
     - Don't put all the technical eggs in one basket
  4. Review and rebalance periodically

## PP_Tip 9: Critically analyze what you read and hear

- Beware of media hype
- Beware of zealots who insist that their dogma provides the only answer
- A best seller book is not necessarily a good book

## PP_Tip 10: It's both what you say and the way you say it

- Plan what you want to say: write an outline
- Choose the right moment
- Choose a style; if in doubt, ask)
- Make it look good
- Involve your audience in early drafts
- Be a listener
- Get back to people

## PP_Tip 10: Remember the WISDOM acrostic

- What do you *W*ant them to learn?
- What is their *I*nterest in what you've got to say?
- How *S*ophisticated are they?
- How much *D*etail do they want?
- Whom do you want to *O*wn the information?
- How can you *M*otivate them to listen?

# A pragmatic approach

## PP_Tip 11: DRY - Don't repeat yourself

- Every piece of information must have a:
  - Single
  - Unambiguous
  - Authoritative representation within a system

- Information is duplicated in multiple places -> maintenance nightmare

## PP_Tip 11: Programs = knowledge

- Programs are made of knowledge (e.g., requirements, specifications, code,
  internal and external documentation)
- Knowledge is unstable
  - Over time one gets better understanding of requirements
  - Requirements change
  - The solution to a problem changes over time
    - E.g., tests show that an algorithm is not general or does not work

## PP_Tip 11: How does duplication arise?

- There are 4 I's of duplication:

1. Imposed
   - The environment seems to require duplication
2. Inadvertent
   - A developer does not realize that he/she is duplicating information
3. Impatient
   - A developer gets lazy and duplicates code because it is easy
4. Inter-developer
   - Multiple developers duplicate a piece of info

## PP_Tip 11: Imposed duplication

- Multiple representations of the same piece of info
  - E.g., same info in two pieces of code written in different languages
  - Solution: write a filter or code generator

- Internal documentation and code
  - Solution: comments should not duplicate info present in the code
  - Comments should be for why, code for how

- External documentation and code
  - Solution: be careful, generate it automatically

- Language issues
  - Some languages require duplication (e.g., C/C++ header vs cpp)
  - Solution: at least warnings and errors are reported
  - Do not duplicate comments in headers and code

## PP_Tip 11: Inadvertent duplication

- Un-normalized data structures
  - E.g.,
  - A `Truck` has a type, maker, a license plate, and a driver
  - A `DeliveryRoute` has a route, a truck, and a driver
  - Now if the driver of a truck is changed, this info needs to be changed in
    two objects
  - Solution: use a 3rd object to bind `DeliveryRoute`, `Truck`, `Driver`

- Data elements that are mutually dependent for perf reason
  - E.g., a line has `startPoint` and `endPoint`, and a field `length` is
    redundant
  - Solution: use accessors to read/write object attributes

## PP_Tip 11: Impatient duplication

- The temptation is always to cut-and-paste code and then modify it
  - It increases the technical debt: shortcuts end up in long delays
  - Solution: re-factor and then change it

## PP_Tip 11: Inter-developer duplication

- It is hard to detect

- Solutions:
  - Encourage communication
  - Do code reviews
  - Project libraries: central place for utility and scripts (so one knows where
    to look before writing a routine)
  - Project librarian to supervise the reuse

## PP_Tip 12: Make it easy to reuse

- If something is not easy to find, use, reuse, people won't reuse

## Orthogonality

- = independence, decoupling

## PP_Tip 13: Eliminate effects between unrelated things

- Systems are orthogonal when changes in one sub-system don't affect other
  sub-systems
  - E.g., helicopter controls are not orthogonal

## PP_Tip 13: Orthogonality: pros

1. Easier to change
   - Changes are localized
   - Changes are easier to be unit tested
2. Gain productivity
   - Less overlap means more useful function per unit of code
   - Promote reuse
3. Reduce risk
   - Easier to change design
   - Not being tied to a particular vendor / product / platform

## PP_Tip 13: How to maintain orthogonality

1. Avoid global state (e.g., singletons)
2. Write shy code
   - Modules / objects that don't reveal anything unnecessary
3. Pass required context to modules, objects, functions
   - Avoid coupling (e.g., law of Demeter)
4. Always look for opportunities to refactor
   - Reorganize
   - Improve structure
   - Increase orthogonality

## PP_Tip 14: There are no final decisions

- Do not carve decisions into stone
- Think of them as being written on the sand

## PP_Tip 14: There are no final decisions: why

1. Requirements can change on us
2. The first decision is not always the best one
3. Change 3rd party components

## PP_Tip 15: Use tracer bullets to find the target

- Ready, fire, aim!

## Analogy between shooting bullets in the dark and software engineering

- How to shoot a bullet to a target in the dark?

  1. Open loop approach
     - Compute all the interesting quantities (wind, angles, distance)
     - Hope that the conditions don't change at all
  2. Closed loop approach
     - Use tracer bullets
     - They leave trace in the dark so one can see if they are hitting the
       target
     - If not, adjust the aim
     - If they hit the target, other bullets will also hit the target

- Software engineering:

  1. Open loop approach
     - Specify the system to death
  2. Closed loop approach
     - Achieve end-to-end connection among components with minimal functionality
     - Then adjust, re-aim, ... until you are on target

## PP_Tip 15: Tracer bullets: pros

- Users see something working early
- You have an integration platform, instead of big-bang integration

## PP_Tip 15: Tracer bullets: cons

- Tracer bullets don't always hit their target
- Still imagine the result using a waterfall approach

## PP_Tip 16: Prototype to learn

- The value of prototype lies not in the code produced, but in the lessons
  learned

## PP_Tip 16: Prototype to learn: cons

- Set the right expectations
- Make sure everyone understands that you are writing disposable code
- Otherwise management might insist on deploying the prototype or a cleaned up
  version of it

## PP_Tip 16: Tracer code vs prototyping

- Prototype:
  - When experimentation is done, the prototype is thrown away and it is
    reimplemented using the lessons learned
  - E.g., write prototype in Python and then code the production system in C++

- Tracer code:
  - Build architectural skeleton
  - Components have minimal implementation
  - Over time stubbed routines are completed
  - The framework stays intact

## PP_Tip 17: Program close to the problem domain

- Always try to write code using the vocabulary of the application domain
- So you are free to concentrate on solving domain problems and ignore petty
  implementation details

- Use mini-languages
  - Other people can implement business logic
- Code can issue domain specific errors
- Create metadata compiled or read-in by the main application

## PP_Tip 18: Estimate to avoid surprises

- All answers are estimates: some are more accurate than others

- Do we need a high accuracy or a ballpark figure?
  - The unit of measurement of the estimate conveys a message about accuracy
  - E.g., 130 working days vs 6 months

## PP_Tip 18: How to make estimates

1. Ask people that have done a similar project before
2. Specify what's the scope of an estimate: "under assumptions X and Y, the
   estimate is Z"
3. Break the system in pieces, understand which parameters they take, assign a
   value to each parameter
4. Understand which are the critical parameters and try to estimate them
   properly
5. When estimates are wrong, understand why

## PP_Tip 19: Iterate the schedule with the code

- Management often wants a single estimate for the schedule before the project
  starts

- In reality:
  - Team
  - Productivity
  - Environment will determine the schedule

## PP_Tip 19: Estimates at the coffee machine

- Estimates given at the coffee machine will come back to haunt you
- When asked for an estimate, answer "I'll get back to you"

# The basic tools

## PP_Tip 20: Keep knowledge in plain text

- The base material for a programmer is knowledge

- Knowledge is made of:
  - Requirements
  - Specifications
  - Documentation
  - Design
  - Implementation
  - Test

- The best format to store knowledge is plain text
- Plain text can be manipulated manually and programmatically using virtually
  any tool (e.g., source code control, editors, stand-alone filters)
- Human-readable self-describing data will outlive
  - All other forms of data; and
  - The application that created it

## PP_Tip 21: Use the power of command shells

- GUIs
  - Are great
  - Allow to do only what they were designed for

- In life one does not know what exactly will be needed
- Shells allow to automate and combine tools in ways that one didn't intended or
  planned for

## PP_Tip 22: Use a single editor well

- Better to know one editor very well than knowing many editors superficially
- Use the same editor for all editing tasks

## PP_Tip 23: Always use source code control

- Source control is like an undo key, a time machine
- Use it always: even if you are a single person team, even if you are working
  on a throw-away prototype

## PP_Tip 23: Advantages of source code control

- It allows to answer questions like:
  - Who made changes to this line of code?
  - What are the difference between this release and the previous one?
- It allows to work on a new release, while fixing bugs in the previous (i.e.,
  branches)
- It can connect to automatic repeatable builds and regressions

## PP_Tip 24: Fix the problem, not the blame

- No one writes perfect software so debugging will take up a major portion of
  your day
- Attack debugging as a puzzle to be solved
- Avoid denial, finger pointing, lame excuses

## PP_Tip 25: Don't panic

- Before you start debugging, adopt the right mindset:
  - Turn off defenses that protect your ego
  - Tune out project pressure
  - Get comfortable
- Don't panic while you debug, even if you have your nervous boss or your client
  breathing on your neck

## PP_Tip 25: How to debug

- Don't waste time thinking "this cannot happen"
  - Obviously it is happening

- Make the bug reproducible with a single command
  - So you know you are fixing the right problem
  - So you know when it is fixed
  - You can easily add a unit test for that bug

- What could be causing the symptoms?
- Check for warnings from the compiler
  - Always set all the compiler warnings so the compiler can find issues for you
- Step through the code with a debugger
- Add tracing statements
- Corrupt variables?
  - Check their neighborhood variables, use `valgrind`

## PP_Tip 25: Rubber ducking

- = explain the issue step-by-step to someone else, even to a yellow rubber duck

## PP_Tip 25: Why rubber ducking works?

- The simple act of explaining the issue often uncovers the problem
- You state things that you may take for granted
- Verbalizing your assumptions lets you gain new insights into the problem

## PP_Tip 26: `select` is not broken

- Do not assume that the library is broken
- Assume that you are calling the library in the wrong way

## PP_Tip 27: Don't assume it: prove it

- Don't assume that a piece of code works in any condition
  - Avoid statements like "that piece of code has been used for years: it cannot
    be wrong!"
- Prove that the code works:
  - In this context
  - With this data
  - With these boundary conditions

- After you find a surprising error, are there any other places in the code that
  may be susceptible to the same bug?
- Make sure that whatever happened, never happens again

## PP_Tip 28: Learn a text manipulation language

- Spending 30 mins trying out a crazy idea is better than spending 5 hours
- With scripting languages (e.g., Python, perl) you can quickly prototype ideas
  instead of using a production language (e.g., C, C++)

## PP_Tip 29: Write code that writes code

- **_Passive code generators_**
- They are run once and the origin of the code is forgotten
  - E.g., parameterized templates, boilerplate
- They can be 90\% accurate and the rest is done by hand

- **_Active code generators_**
- They convert a single representation of knowledge into all the forms that are
  needed
- This is not duplication, it is the DRY principle in action

# Pragmatic paranoia

## PP_Tip 30: You cannot write perfect software

- Accept it and celebrate it
  - Unless you accept it, you'll end up wasting time chasing an impossible dream

## Know when to stop

- A painter needs to know when to stop adding layers of paint

## Don't trust others

- Code defensively
- Anticipate the unexpected

## Don't trust yourself

- Code defensively against your own mistakes

## Preconditions

- = what must be true in order for the routine to be called
- It is caller's responsibility to pass good data

## Postconditions

- = what the routine is guaranteed to do

## Class invariants

- = a class ensures that some conditions are always true
  - E.g., between invocations to public methods

## Contracts

- If all routines' preconditions are met
  - => the routine guarantees that all postconditions and invariants will be
    true when it completes

## PP_Tip 31: Design with contracts

- Some languages support design by contract:
  - In the compiler (e.g., static assertion, type system)
  - In the runtime systems (e.g., assertions)

## PP_Tip 32: Crash early

- Better to crash than to thrash (=corrupting the state of the system)
- When something unexpected happens throw a runtime exception
  - The exception, if not caught, will percolate up to the top level halting the
    program

## PP_Tip 33: If it cannot happen, use assertions to ensure that it won't

- Assertions check for things that should never happen
  - E.g., at the end of a sorting routine the data is not sorted
- Don't use assertions in place of real error handling

## Leave assertions enabled

- Assertions should be left on even after the system is tested and shipped
- The assumption that testing will find all the bugs is wrong
  - Testing tests a miniscule percentage of possible real-world conditions

## PP_Tip 34: Use exceptions for exceptional problems

- Interleaving normal control flow code and error handling code leads to ugly
  code
  - With exceptions one can split the code neatly into two parts
  - Exceptions are like `goto`

## Exceptions are for unexpected events

- Use exceptions only for truly unexpected events
- The code should still run in normal conditions if one removes all the
  exception handlers

## PP_Tip 35: Finish what you start

- Resources (e.g., memory, DB transactions, threads, files, timers) follow a
  pattern:
  - Allocate
  - Use
  - Deallocate
- Routine or objects that allocate resources are responsible for deallocating
  them
- To avoid deadlocks always deallocate resources in the opposite order to that
  in which you allocate them

# Bend or break

## PP_Tip 36: Minimize coupling between modules

- We want to limit the interaction between modules
  - If one modules has to be replaced / is broken, the other modules can carry
    on
- Traversing relationships between objects can quickly lead to a combinatorial
  explosion of dependencies

## PP_Tip 36: Law of Demeter for functions

- Any method `O.m(A, B, C)` of an object `O` should call only methods belonging
  to:
  - Object `O` itself
  - Objects through parameters passed to the method (e.g., `A`)
  - Objects instantiated within `m`

- A rule of thumb in OOP is to use a single dot, e.g., `a.m()` and avoid
  multiple dots, e.g., `a.b.m()`

## PP_Tip 36: Intuition of the Law of Demeter

- Object `A` can call a method of `B`
- `A` cannot reach through `B` to access an object `C`
  - Otherwise `A` knows about the internal structure of `B`
- `B` needs to be changed to expose the interface of `C`
  - Cons: lots of wrapper methods to forward requests to delegates

## PP_Tip 36: Law of Demeter as general contractor

- It's like using a general contractor

- Pros
  - You ask a job to be done, but you don't deal with subcontractors directly
- Cons
  - The client needs to go through the general contractor all the times

## PP_Tip 37: Configure, don't integrate

- Every time we change the code to accommodate a change in business logic we
  risk to break the system or to introduce a new bug

- Make the system highly configurable
- Always use metadata, i.e., data about data (e.g., choice of algorithm,
  database, middleware, user-interface style, ...)
- Use `.ini` files

## PP_Tip 38: Put abstractions in code, details in metadata

- The goal is to think declaratively: specify what to do, not how to do it
- We want to configure and drive the application via metadata as much as
  possible
- So we program for the general case and put the specifics outside the compiled
  code

## Mechanisms vs policies

- Mechanisms = primitives, what can be done
- Policies = how to put together primitives

## PP_Tip 38: Advantages of splitting mechanisms and policies

1. Decouple components in the design, resulting in more flexible and adaptable
   programs
2. Customize the application without recompiling it
3. Metadata can be expressed in a form closer to problem domain
4. Anybody can change the behavior without understanding the code

## PP_Tip 38: Put business logic in metadata

- Business logic and rules are the parts that are most likely to change
- So we want to maintain them in a flexible format, e.g., metadata
- Metadata should be encoded in plain text

## PP_Tip 39: Analyze workflow to improve concurrency

- Avoid temporal coupling
- Use activity diagrams to identify activities that could be performed in
  parallel

## PP_Tip 40: Temporal coupling

- Time is often ignored when designing a software architecture
- We tend to think in a linear sequential fashion: "do this, then do that"
- This leads to temporal coupling, i.e., coupling in time

- When designing an architecture, we need to think about:
  - Concurrency = things happening at the same time
  - Ordering = `A` must occur before `B`

## PP_Tip 40: UML activity diagram

- Actions are represented by rounded boxes
- Arrows between actions mean "temporal ordering"
- Actions with no incoming arrows can be started at any time
- Synchronization points are represented by a thick bar:
  - Once all the actions leading to a barrier are done, one can proceed with the
    arrows leaving the synchronization point

## Service

- = independent, concurrent objects behind well-defined, consistent interfaces

## PP_Tip 40: Design using services

- Using services allows to avoid temporal coupling

## PP_Tip 41: Hungry consumer model

- There are multiple independent consumers and a centralized work queue
- Each consumer grabs a task from the work queue and processes it
- Load balancing: if a consumer task gets bogged down or it is slower, the
  others can pick up the slack

* PP_Tip 41: Example of 3-tier architecture with hungry consumer model
- **_Goal_**
- Read a request from multiple lines and process the transactions against the
  database

- **_Constraints_**
- DB operations are slow
- We need to keep accepting service requests even when waiting on DB
- DB performance suffers with too many concurrent sessions

- **_Solution_**
- 3 tier, multi-processing distributed application
- Tier 1: input tasks monitor the input lines and add requests to application
  queue
  - Application queue
- Tier 2: read application queue, apply business logic, add transaction to DB
  queue
  - DB queue
- Tier 3: read transactions from DB queue and apply it to DB

- Each component is an independent entity, running concurrently (on the same
  machine or on multiple machines)
- Actions are asynchronous: as soon as a request is handled by a process and put
  on next queue, the process goes back to monitor inputs

## PP_Tip 41: Always design for concurrency

- Programming with threads imposes some design constraints
- Concurrency forces you to think things more carefully

## Examples of problems with concurrency

- Global or static variables must be protected from concurrent access
  - Do you really need a global variable?
- Objects must always be in a valid state when called
  - Classes with separate constructor and initialization routines are
    problematic
- Interfaces should not keep state
  - Make services stateless

## Event

- = special message that says "something interesting just happened"

## PP_Tip 42: Objects communicating through events

- We know that we need to separate a program in modules / classes
  - A module / class has a single, well-defined responsibility

- At run-time how do objects talk to each other?
- We don't want objects to know too much about each other
  - E.g., how does object `A` know which objects to talk to?
- By using events one can minimize coupling between objects: objects are
  interested in events and not in other objects

## PP_Tip 42: All events through a single routine approach

- One approach is to send all events to a single routine that dispatches them to
  the objects
- This is bad!
  - A single routing needs to know all interactions among objects
  - It's like a huge case statement
  - It violates encapsulation, increases coupling

## PP_Tip 42: Publish / subscribe model

- Objects should only receive events they want (do no spam objects!)
  - Subscribers register themselves with publisher objects for interesting
    events
  - Publisher calls all subscribers when a corresponding event occurs
- Organization can be:
  - Peer-to-peer
  - Software bus (a centralized object maintains DB of listeners and dispatches
    messages)

## PP_Tip 42: Sequence diagram

- It shows the flow of messages among several objects
- Objects are arranged in columns
- Each message is an arrow from sender's column to receiver's column
- Timing relationship between messages is captured by vertical ordering

## PP_Tip 42: Push / pull model for event services

- **_Push mode_**
- Event producers inform the event channel that event has occurred
- Event channel distributes event to all client objects registered for that
  event

- **_Pull mode_**
- Event consumers poll the event channel periodically
- Event channel polls possible suppliers and report interesting events

## PP_Tip 42: Separate views from models

- Model-View-Controller design pattern

- Model:
  - It stores the data
  - It has methods to change its state, to report changes (through events), and
    to report data
  - It is like a DB
- View:
  - A way to interpret the Model
  - It subscribes to changes in the Model
  - It subscribes to events from the Controller to change representation
- Controller:
  - It controls the View
  - It provides new data to the Model

- One can even have a network of MVCs: e.g., a View for one Model can be the
  Model for another View

* PP_Tip 42: Examples of MVC
- Almost any GUI
- Tree widget = a clickable, traversable tree
- Spreadsheet with a graph attached to represent data as bar charts, running
  totals, ...; controllers allow to zoom in / out, enter new data, ...
- System reporting interesting information about a baseball game
  - Model is a DB with all possible information
  - New data from the Controller: a pitcher is changed, a player strikes out, it
    starts raining
  - A View reports the score
  - A View reports info about current batter
  - A View looks for new world records
  - A View posts information on the web

## PP_Tip 43: Use blackboards to coordinate workflow

- A blackboard system lets decouple objects from each other completely
- There is even less coupling that publish / subscribe model
- Consumers and producers exchange data anonymously and asynchronously

## PP_Tip 43: Example of blackboard implementation

- Blackboard is like a DB providing atomic and distributed storage of objects

- One can store any object, not just data
- Objects can be retrieved by partial matching fields (templates and wildcards)
  or by subtypes
- Operations can be:
  - Read = search and retrieve item from blackboard
  - Write = put an item on the blackboard
  - Take = read + remove from blackboard
  - Notify = set up notification when an object matching a template is written
- Advantage is a single and consistent interface to blackboard, instead of
  different APIs for every transaction / interaction in the system

## PP_Tip 43: Example of blackboard application

- Program that accepts and process loan applications

- **_Constrains_**
- The laws are very complex
- There is no guarantee on the order in which data arrives
- Data is gathered by different people
- Certain data is dependent on other data
- Arrival of new data may raise request for more data and policies
- As regulation change, the workflow must be re-organized

- **_Solutions_**
- Encoding all the workflow is a nightmare
- A better solution is a blackboard + rules engine
- Any time new data arrives, a new rule is triggered
- Rules can output more data on the blackboard, triggering more rules and so on

# While you are coding

## PP_Tip 44: Don't program by coincidence

- Do not program by coincidence (= relying on luck and accidental successes)
- Program deliberately

## PP_Tip 44: How to program by coincidence

- You type some code, try it, and it seems to work
- Type more code and still works
- After few weeks the program stops to work
- You don't know why the code is failing, because you didn't know why it worked
  in the first place
- The code seemed to work, given the (limited) testing did, but it was just a
  coincidence

## PP_Tip 44: Why program by coincidence seems to work?

- One ends up relying on undocumented boundary conditions and when the code is
  fixed / changed, our code breaks
- One tries until something works, then it does not wonder why it works: "it
  works now, better leave it alone"

## PP_Tip 44: How to program deliberately

- Rely only on reliable things
- Document your assumptions (e.g., design by contract)
- Add assertions to test assumptions
- Don't just test your code, test your assumptions as well (e.g., with small
  unit tests)
- Don't let existing code (even your own code) dictate future code

## PP_Tip 45: Estimate the order of your algorithms

- We always want to estimate the resources (e.g., time, memory) required by
  algorithms
- E.g., "Would the algorithm scale up from 1k records to 1M records?"

## Big-Oh notation

- Big-Oh notation represents the worst-case time taken by an algorithm
  - Simple loops: $O(n)$
  - Nested loops: $O(n^k)$
  - Binary chop (e.g., binary search): $O(\log(n))$
  - Divide and conquer (split, recurse, combine): $O(n \log(n))$
  - Combinatoric: $O(2^n)$

## Estimating Big-Oh

- If you are not sure about Big Oh, vary input record size and plot the resource
  needed (e.g., time, memory) against the input size

## Big-Oh in the real world

- It is possible that a $O(n^2)$ algorithm is faster than a $O(n \log(n))$ for
  small inputs
- Even if runtime looks linear, the machine might start trashing for lack of
  memory and thus not scale linearly in the real world

## PP_Tip 46: Test your estimate

- It's tricky to get accurate execution times
- Use code profilers to count the number of times different steps of your
  algorithm get executed and plot against the input size

## Be wary of premature optimization

- Make sure an algorithm is really the bottleneck before investing precious time
  trying to improve it

## Refactoring

- = re-writing, re-working, re-architecting code

## PP_Tip 47: Refactor early, refactor often

- If you cannot refactor immediately
  - Make space in the schedule
  - File a bug
  - Limit the spread of the virus

## How to refactor

- Refactoring needs to be undertaken slowly, deliberately, and carefully
- Don't refactor and add functionality at the same time
- Make sure you have good tests before refactoring
- Take baby steps to avoid prolonged debugging

## PP_Tip 47: Software development is more gardening than building

- Unfortunately the most common metaphor for software development is building
  construction: blueprints, build, release, maintenance, ...

- As a program evolves, it is necessary to rethink earlier decisions and rework
  portions of the code
- Software is more like gardening:
  - Start with a plan
  - Some plants die
  - Move plants to get in the sun / shade
  - Pull weeds
  - Monitor health of the plants
  - Make adjustments

## PP_Tip 47: When to refactor?

- It is time to refactor when you notice:
  - Duplication
  - Non-orthogonal design
  - Outdated knowledge
  - Bad performance

## PP_Tip 47: Management and refactoring

- How do you explain to your boss that "the code works, but it needs to be
  refactored?"
- Fail to refactor now and the investment to fix the problem later on will be
  larger
- It's like accumulating debt: at some point it will need to be repaid, with
  interests!

## PP_Tip 48: Design to test

- Chips are designed to be tested
  - At the factory
  - When they are installed
  - When they are deployed in the field

- BIST (Built-In Self Test) features
- TAM (Test Access Mechanism) = test harness to provide stimuli and collect
  responses

- We need to build testability into the software from the very beginning
- Test each piece thoroughly (unit testing) before wiring them together
  (integration testing)

## PP_Tip 48: Testing against contract

- Write test cases that ensure that a unit honors its contract
  - This also checks whether the contract means what we think it means

- We need to check over a wide range of test cases and boundary conditions
- There's no better way to fix errors than by avoiding them in the first place

## Test-driven development

- By building the tests before you implement the code, you try out the interface
  before you commit to it

## PP_Tip 48: Where to put unit tests?

- Unit tests should be somehow close to the code they test
  - E.g., in a parallel directory
- If something is not easy to find and use, it won't be used

- By making the test code readily accessible, one provides:
  - Examples of how to use a module
  - A means to validate any future changes to code

## PP_Tip 48: Provide a test harness

- It's good to have a way to:
  - Select tests to run
  - Pass arguments on the command line to control the testing
  - Analyze the test output
  - Automatically find all the unit tests (instead of having a list of tests, so
    that we can honor the DRY principle)
- Test harness can be built using OOP
  - E.g., objects provide setup and cleanup methods, standard form of failure
    report, ...
- There are standard test harness (e.g., `unittest` for Python, `cppunit` for
  C++)

## PP_Tip 48: Build a test backdoor

- No piece of software is perfect and bugs show up in real world
- Have log files containing trace messages
- Log messages should be in a regular, consistent format
- An interesting technique is to have a built-in web server in the application
  - Pointing to a certain port of the machine one can see internal status, log
    entries, a debug control panel

## PP_Tip 49: Test your software or your users will

- All software you write will be tested
  - If not by you, then by the eventual users
- It is better to test it thoroughly than being swamped in help desk calls

## PP_Tip 50: Don't use wizard code you don't understand

- Applications are getting harder and harder to write
  - User interfaces are becoming increasingly sophisticated
  - The underlying applications are getting more complex
- One can use wizards to generate code to perform most functions, but one must
  understand all of it (otherwise one is programming by coincidence)

- One could argue that we routinely rely on things we don't understand
  - E.g., quantum mechanics in integrated circuits
  - What we don't understand is behind a tidy interface
  - Wizard code is interwoven with our application

# Before the project

## Requirement

- = a statement about something that needs to be accomplished

## PP_Tip 51: Don't gather requirements: dig for them

- Gathering requirements implies that the requirements are already there
- In reality they are buried deep beneath layers of
  - Assumptions
  - Misconceptions
  - Politics

## PP_Tip 51: Example of tricky requirements

- A requirements can sound like: "Only an employee's supervisors and HR may view
  an employee's records"
- This requirement has a policy embedded in it
  - We don't want to hard-wire policies into requirements, since policies change
    all the time
- Requirements should be a general statement: "An employee record may be viewed
  only by a nominated group of people"
- Give the policy as an example of what should be supported
- Policies should eventually go in the metadata of the application

## PP_Tip 52: Work with a user to think like a user

- We need to discover the underlying reason why users do a thing, rather than
  just the way they currently do it
- We want to solve a business problem, not just check off requirements
- You can ask the user to sit with him for a week while he does his job
  - See how the system will be really used, not how management intended to be
    used
  - Build trust and establish communication with your users

## Use cases

- = capture requirements through a particular use of the system

## PP_Tip 53: Use cases

- While sitting with the user, you see a few interesting scenarios that describe
  what the application needs to do
- Write the scenarios in a document that everyone (developers, end users,
  project sponsor, management) can discuss

## PP_Tip 53: Abstractions live longer than details

- Good requirement docs should remain abstract
- They reflect the business needs, not architecture, not design, not user
  interface, ...

## PP_Tip 53: Feature-itis

- Aka feature bloat
- The issue is that by adding "just one more feature", the scope of the project
  keeps growing
- One should track the number of bugs reported and fixed, the number of
  additional features requested and who approved them

## Project glossary

- = one place that defines all the specific terms and vocabulary used in a
  project

## PP_Tip 54: Use a project glossary

- It's hard to succeed if users and developers
  - Refer to the same thing with different names, or
  - Refer to different things with the same name
- Create and maintain a project glossary

## PP_Tip 55: Don't think outside the box: find the box

- The secret to solve a puzzle is to identify the real (not imagined)
  constraints and find a solution therein
- Some constraints are preconceived notions
- E.g., "the Gordian knot"

- E.g., the Trojan horse:
  - How do you get troops into a walled city?
  - Would you have dismissed the idea of getting troops "through the front
    door"?

- To solve a problem enumerate all the possible avenues
  - Don't dismiss anything, then explain why a certain path cannot be taken. Can
    you prove it?

## PP_Tip 55: Impossible problems

- You are stuck on a problem that seems "impossible"
- You are late on the schedule
- Step back and ask yourself:
  - Is there an easier way?
  - What is that makes this problem so hard to solve?
  - Does it have to be done this way?
  - Does it have to be done _at all_?

## PP_Tip 56: Listen to nagging doubts: start when you are ready

- When you experience some reluctance when faced with a task, take notice
- Sometimes your instinct is right on the spot, although you cannot put a finger
  on it
- How can you tell that is not just procrastination?
  - You can start prototyping and verify if some basic premises were wrong

* Program specification
- = process of reducing requirements to the point where coding can start
- The goal is to remove major ambiguities

## PP_Tip 57: Some things are better done than described

- Program specification is an agreement with the user
- It's important to stop increasing level of detail and start coding,
  prototyping, tracer bullet, because:
  - It is naive to assume that a specification will ever capture every detail
  - Once the system is running, users will ask for changes
  - Natural language is not expressive enough to clarify everything

## PP_Tip 58: Don't be a slave to formal methods

- Many methods have been developed to make programming more like engineering
  (e.g., waterfall development, UML, ...)
- These formal methods use a combination of diagrams and supporting words
- The user typically does not understand them and cannot provide feedback
- It's better to give the users a prototype and let them play with it

## PP_Tip 59: Expensive tools do not produce better designs

- Never give in into a methodology just because it is the hot new fad
- Do not think about how much a tool costs when you look at its output

# Pragmatic projects

## PP_Tip 60: Pragmatic teams

- Most of the pragmatic programming principles apply to teams, as much as they
  apply to an individual

1. No broken windows
   - Quality is a team issue
   - Team as a whole should not tolerate broken windows (= small imperfections
     that no one fixes)

2. Boiled frogs
   - People assume that someone is handling an issue or that someone must have
     OK-ed a change request from the user
   - Fight this: everyone must actively monitor the environment for changes

3. Communicate
   - Great teams speak with one voice and are always prepared

4. Don't repeat yourself (DRY)
   - Some teams appoint a member as the project librarian, responsible for
     checking on duplication, coordinating documentation, ...

5. Orthogonality
   - Traditional team organization is based on the old-fashioned waterfall
     method of software construction
     - Individuals are assigned roles based on their job function, e.g.,
       - Business analysts
       - Architects
       - Designers
       - Programmers
       - Testers
   - Different activities of a project (analysis, design, coding, testing) can't
     happen in isolation

## PP_Tip 60: Organize around functionality, not job functions

- Organize people in the same way one organizes code
  - Design by contract
  - Decoupling
  - Orthogonality

- Split teams by functionality not by job function (e.g., architect, programmer,
  tester)
  - We look for cohesive, self-contained teams of people

- Let each team organize themselves internally
  - Each team has agreed upon responsibilities and commitments to the other
    teams
  - Of course this approach works only with responsible developers and strong
    project management

## PP_Tip 61: Don't use manual procedures

- We want to ensure consistency and repeatability in the project
  - Manual procedures leave consistency up to chance
  - Let the computer do the mundane jobs: it will do a better job than we do

- Compiling the project should be reliable and repeatable
- We want to check out, build, test, ship with a single command
- `make` and `cronjobs` are the solutions

## PP_Tip 62: Test early

- Look for your bugs now, so you don't have to endure the shame of others
  finding your bugs later
- Start testing as soon as you have code
- Code a little, test a little

## PP_Tip 62: Test often

- The earlier a bug is found, the cheaper it is to remedy

## PP_Tip 62: Test automatically

- Tests that run with every build are better than test plans that sit on a shelf
- A good project may well have more test code than production code

## PP Top 63: Coding ain't done 'til all the tests run

- Just because you finished coding, you cannot tell that the code is done
- You cannot claim that the code is done until it passes all the available tests
- Code is never really done

## PP_Tip 63: What to test

- There are multiple types of tests:
  - Unit
  - Integration
  - Validation
  - Performance
  - Usability tests

## Unit test

- = exercise a module
- If the parts don't work by themselves, they won't work together

## Integration test

- = show that the major subsystems work well together
- Integration is the largest source of bugs in the system
  - Test that the entire system honors its contract

## Validation and verification test

- = the users told you what they wanted, but is it what they really need?
- A bug-free system that answers the wrong question is not useful

## Resource exhaustion, errors, and recovery test

- Resources are limited in the real world, e.g.:
  - Memory
  - Disk space / bandwidth
  - CPU
  - Network bandwidth
  - Video resolution
- How will the system behave under real-world conditions?

## Performance test

- = testing under a given load (e.g., expected number of users, connections,
  transactions per second)
- Does the system scale?

## Usability test

- = performed with real users, under real environmental conditions

## PP_Tip 63: How to test

- Run regression tests for all types of tests

## Regression testing

- = compare output of current test with previous known values
- It ensures that fixes for today's bugs don't break things that were working
  yesterday
- All types of tests can be run as regression tests
  - Unit
  - Integration
  - Validation
  - Performance
  - Usability tests

## Test data

- Test data is either real-world data or synthetic data
  - One needs to use both, since they expose different kind of bugs
- Synthetic data
  - Stresses boundary conditions
  - Can have certain statistical properties (e.g., data to sort is already
    sorted or inversely sorted)

## Exercising GUI systems

- Often specialized testing tools are required, e.g.,
  - Event capture / playback model
  - A data processing application with GUI front end should be decoupled so that
    one can test each component by itself

## Testing the tests

- We cannot write perfect software
- We need to test the tests and the test infrastructure

## Testing thoroughly

- Use coverage analysis tools to keep track of which lines of the code have been
  / not been executed

## PP_Tip 64: Use saboteurs to test your testing

- If the system is a security system, test the system by trying to break in
- After you have written a test to detect a particular bug, cause the bug
  deliberately and make sure the tests catch it
- Write test for both positive and negative cases

## PP_Tip 65: Test state coverage, not code coverage

- Knowing that you executed all code does not tell you if you tested all states
- This is a combinatorial problem
- You can tame the complexity thinking about:
  - Boundary conditions
  - Structure of the code

## PP_Tip 65: When to test

- As soon as any code exists, it must be tested
- Testing should be done automatically as often as we can (e.g., before code is
  committed to the repository)
- Also results should be easy to interpret: ideally the outcome is binary `ok` /
  `not_ok`
- Expensive / special tests can be run less frequently, but on a regular basis

## PP_Tip 66: Find bugs once

- Once a human tester finds a bug, a new test should be created to check for
  that bug every time
- You don't want to keep chasing the same bugs that the automated tests could
  find for you

## PP_Tip 67: Treat English as just another programming language

- Embrace documentation as an integral part of software development
- Keep the documentation in the code itself as much as possible
- Treat code and documentation as two views of the same model
- Apply all the principles learned for coding (DRY principle, orthogonality,
  ...) to English as well

## PP_Tip 68: Internal documentation

- Source code comments
- Design documents
- Test documents

## External documentation

- = anything that is shipped or published to the outside world together with the
  software product (e.g., user manuals)

## Documentation vs code

- Documentation and code are different views of the same underlying model
- If there is a discrepancy, the code is what matters

## PP_Tip 68: Comments

- Code should have comments, but too many comments are as bad as too few
  - Comments should discuss \textit{why} something is done (e.g, engineering
    trade-offs, why decisions were made)
  - The code already shows \textit{how} it is done
- Modules, class, methods should have comments describing what is not obvious
- Javadoc notation is useful (`\@param`, `\@return`, ...) to extract information
  from the code automatically

## Naming concepts

- Variable names should be meaningful
- Remember that you will be writing the code once, but reading it hundreds of
  time: avoid write-only code
- Misleading names are worse than meaningless names

## PP_Tip 68: Automatically generated documentation

- Also for documentation we want to use pragmatic principles
  - DRY principle
  - Orthogonality
  - Model-view-controller
  - Automation

- Printed material is out of date as soon as it is printed
  - Publish documents on-line
- There should be a single command to generate and publish the documents on-line
- Use a timestamp or review number for each page

## PP_Tip 69: Gently exceed your users' expectations

- Success of a project is measured by how well it meets the expectations of its
  users

## Examples of difference between actual and expected results

- A company announces record profits, and its share price drops 20\%
  - It didn't meet analysts' expectations
- A child opens an expensive present and bursts into tears
  - It wasn't the cheap doll that she wanted
- A team works miracles to implement a complex application
  - The users don't like it because it does not have an help system

## PP_Tip 69: Communicating expectations

- Users come to you with some vision of what they want
- It may be
  - Incomplete
  - Inconsistent
  - Impossible
- They are invested in it: you cannot ignore this

## Manage expectations

- Work with your users so that they understand what you are delivering
- Never lose sight of the business problems your application is intended to
  solve

## Go the extra mile

- Surprise and delight your users
- E.g., balloon help, colorization, automatic installation, splash screen
  customized for their organization, ...

## PP_Tip 70: Sign your work

- Craftsmen of earlier ages were proud to sign their work
- Your signature should come to be recognized as an indicator of quality

## PP_Tip 70: Code ownership vs anonymity

- Code ownership can cause cooperation problems: people become territorial
- Anonymity can enable sloppiness, laziness
