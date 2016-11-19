# Survy HAS

Survy is an open source, multi-purpose, high-tech, low-cost home automation system.
Survy has been projected to smoothly run on a Raspberry PI or in any other hardware platforms supporting Linux Debian based distros.

## The idea

The idea behind Survy is quite simple, Survy is just a new generation PLC platform that can handle events and perform actions.
Its paradigm is EAC: **Events**, **Actions** and **Conditions**.

The other important thing to understand in Survy is that can be adapted to **almost
any existing home automation system**.
You can interface your home alarm as well as an IP camera or a remote light switch.

A variety of adapters can be added to support different inputs and outputs.
 
### Events:
It just means: anything that can happen that can be detected by Survy.

Examples:

- A door has been opened
- Alarm system has been armed
- A motion detector has been triggered
- A telegram message has been received
- Etc...

### Actions:
Anything can be performed by Survy.

Examples:

- Arm your home alarm system
- Take a camera snapshot
- Rotate your PTZ camera
- Send a message via Telegram
- Send a photo via Telegram
- Say something
- Etc... 

### Conditions:

Conditions required to perform an action after an event.
 
Example:

- If it is midnight and home alarm has not ben armed, then arm
- If motion is detected and home alarm system is armed, then send me a camera picture
- Etc...

## Modularity

Survy HAS is a **modular system** that can be plugged with add-ons, both local and remote.

If a feature does not exist, you can easily implement it with few Python code lines.

## Configuration

**Survy** has a very simple YAML based configuration that allows you to both configure and program the standard behaviours.
   
## Headless

Survy is an headless engine, it means it does not have any graphical interface.
I will probably build one very soon with ReactJS, so stay tuned ;)

# What do I need?

My solution is:

- Raspberry PI 3
- Arduino Nano 328
- 1x Aurel RX-4MM5 module (it is a 433mhz RX module)
- 1x Aurel RX-8ML5 module (it is a 868mhz RX module)
- 1x Aurel TX-AM868 MID module (it is a 868mhz TX module)
- 1x XY-FST 433mhz module (it is a 433mhz TX module)
- 1x 5V step up module

You can change the listed components if you know what you are doing.

You only need all this stuffs **if you are going to interface an existing home automation system**, a radio device
 or alarm system.
 
If you just need something **like a video surveillance** system or a fully IP based solution, then you just need a **Raspberry PI** or an **old PC** 

## How to assemble

TODO... (work in progress)

At the end it will look like this:

<img src="https://raw.githubusercontent.com/phoenix128/survy-has/master/pics/proto.jpg" />

Of course you can do a better job than mine ;)
