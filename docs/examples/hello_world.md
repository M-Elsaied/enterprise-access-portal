# Hello World

The hello_world agent network is a simple agent network that returns a greeting when prompted.

## Description

Hello world is an agent network that tries to write an announcement on behalf of someone else.
The idea is to make it say "Hello, world".
It contains:

- a "frontman" agent, called `announcer`, which is the entry point to the agent network.
  Its job is to write a small greeting message.
- one tool at the disposal of the frontman, which is another agent called `synonymizer`.
  It tries to convert the greeting message to 5 letters words.

## Example conversation

```text
Human: I am travelling to a new planet and wish to send greetings to the orb.
AI: Hello, world.
```

... but you are dealing with LLMs. Your results will vary!
