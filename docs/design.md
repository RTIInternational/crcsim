# CRC Pilot Model - Design Document

This document describes the high-level design of the Python CRC pilot model. It includes the following sections:
1. Purpose
2. Specifications
3. Process Flow
4. Outstanding Questions


## 1. Pilot Model Purpose
Because of AnyLogic’s high cost, we are considering migrating the model to another modeling framework. To help decide which framework to migrate to, we will create small pilot models using each candidate. The pilot model is intended to serve the following purposes:

- **Feasibility:** Determine whether the full model can feasibly be implemented in the framework. 
- **Level of Effort Estimation:** Provide a better estimate for how long it will take to convert the full model to the framework.
- **Performance Measurement:** compare the performance of the new frameworks and AnyLogic in terms of speed and memory usage.


## 2. Pilot Model Specifications
We will build pilot models in each possible framework to the same specifications. This consistency will allow us to compare frameworks in terms of feasibility, level of effort, and performance. 

Pilot models must follow these specifications:
- The model accepts two input parameters: random seed and number of people. All other parameters will be hardcoded.
- A person has a numeric ID.
- A person has an expected lifespan chosen from a uniform(40, 90) distribution. At the expiration of this lifespan, they die of other causes if they haven’t already died of colon cancer.
- A person has zero or more lesions.
- Lesions are created at random intervals chosen from an exponential(mean=60) distribution.
- A lesion has a statechart with states Polyp, Cancer, and Dead. It starts in Polyp. It transitions from Polyp to Cancer after a random amount of time chosen from an exponential(mean=30) distribution. It transitions from Cancer to Dead after a random amount of time chosen from an exponential (mean=5) distribution.
- A person has a disease statechart with states Healthy, Polyp, Cancer, and Dead. It starts in the Healthy state. It transitions from Healthy to Polyp if any of the person's lesions transition to Polyp, and similarly for Cancer and Dead. It transitions from any state to Dead if the person dies of other causes. It transitions from Polyp or Cancer to Healthy if all lesions are removed after a positive test.
- A person has a testing statechart with states NoTesting and Routine. It starts in NoTesting and transitions to Routine at age 50. It transitions back to NoTesting at age 75. While in Routine, a test is performed every 5 years.
- If the person has lesions, the test returns a positive result 60% of the time. If the person doesn’t have lesions, the test returns a negative result 100% of the time.
- After a positive test, all lesions are removed.
- The output is a file listing all the state changes in the person’s disease statechart. It has columns named person_id, time, old state, new state.


## 3. Process Flow

Each model run simulates the lifespans of a population of N people (with N being a user-specified parameter). Each person’s lifespan is simulated in series. The process flow of a single person’s lifespan simulation is described below.

1.	The Scheduler class is initialized.
2.	The `Scheduler.add_event()` method is used to manually add the time of each person's non-cancer death as an event in the Scheduler queue. The time of non-cancer death is randomly sampled from a uniform distribution with range 40-90. 
3.	An `init` message is sent to each of the preson's statecharts to initialize them.
4.	The Scheduler loops through the queue, popping the next event and sending it to the appropriate "receiver". A receiver is a callable that accepts an event and performs some action in response to the event. This process continues until an `end_simulation` event is reached.
5.	When a person’s statecharts transition from one state to another, the `Person.write_state_change()` method is called, which appends a record of the state change to the person’s `state_changes` list.
6.	The `lesion_creator` statechart controls the addition of new lesions to a person. Lesions are created at random intervals chosen from an exponential (mean=60) distribution. When `lesion_creator` receives a `create_lesion` message, it triggers the `Person.create_lesion()` method. This method adds a new Lesion instance to the person.
7.	The other statecharts control the progression of lesions, a person’s disease state based on the state of their lesions, and a person’s testing regimen, which controls when lesions are detected and cured.
8.	Once the queue is empty, the person’s state change list is appended to a file containing all state changes of the population in the model run.

After the model run, the state change output file will contain each person’s state change history. The user can then use this history to generate summary statistics for the population, such as cancer death rate, average lifespan, etc.


## 4. Outstanding Questions

This section contains a running list of questions that remain to be addressed in our design of the pilot model. Once a question has been answered, remove it from the list and make any according changes to other sections of this document.

There are no currently outstanding questions.
