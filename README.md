# Firewall Introduction


## Test Instruction

1. run `make` to install the table in topo for switches.
2. use command `h1 ping h2` in the `mininet` to set up the connection between h1,h2 switches as the example, this should also work for any switches between h1 to h4.
3. run `sudo python3 controller.py` to disconnect the h1, h2, you should see there's no ping record flashing in the mininet anymore.
