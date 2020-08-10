# RIP
COSC364 Assignment - Implementing RIP Routing Protocol

rip.py implaments a routing demon as a normal userspace under Liinux. The routing demon sends routing packets to its peer demons running parallel on the same machine.
Each routing demon is set up by running rip.py and supplying it with a configuration file from the command line. The configuration file supplies each demon the port numbers used to communicate with its peers and the ports which it recieves packets from its peers.

config1.txt gives an example configuration file for node 1 in network.png.
RIP Assignment Specifications.pdf lays out the assignment and the functionality of rip.py
