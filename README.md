# Project 2: RDT Protocol

*Original work by Joshua Shew (jts212). I referred to several websites while working on this project, but I did not copy any code.*

## Instructions

1. Start the receiver first:

        $ python3 receiver.py [port] [window size]

2. Then, start the sender:

        $ python3 sender.py [receiver ip] [receiver port] [window size]

3. Both the receiver and sender programs will print messages to the console to update the user of what packets are being sent and what packets have been lost

4. Run the following command to verify that the data was transferred without error

        $ diff download.txt alice.txt

## Documentation

The code is well documented and commented, so please see the individual files for an explanation of how the code is structured.