'''
                    COSC364 (RIPv2 Routing Protocol)
             Authors: Haider Saeed (msa280), Drogo Shi (msh217)
                           Date: 07/03/2022
                      Filename: RIPv2_Daemon.py
                           
Program Definition: Configures RIP routing protocol based on the specifications
                   outlined in RIP Version 2 (RFC2453). (Section 4 not included) 
'''


import sys
import configparser     # ConfigParser class which implements a basic configuration language
import time
import socket
import select
import threading    # use timer here so sys load will not affect the time
import random
from RIPv2_Router import*
from RIPv2_ConfigureFile import*



LOCAL_HOST = '127.0.0.1'



def start_daemon():
    """Starts up the router."""
    # Gets the name of file from the command line. Example (python3 RIPV2_Daemon.py router1.txt)
    filename = sys.argv[1]
    
    file = RIPv2_ConfigureFile(filename)
    # Configures and creates and binds to sockets 
    file.read_and_process_file() 
    
    router_id_self = file.router_info['router_id']

    #let first one input socket to send out packet
    #send_socket_port = list(file.router_info['inputs'].keys())[0]
    #file.router_info['inputs'].get(send_socket_port) 

    sending_socket = list(file.router_info['inputs'].values())[0]
    
    # Create a new router 
    router = RIPv2_Router(router_id_self, file.neighbor, sending_socket)
    
    # Send packet to neighbour
    router.periodically_send_packets()
    
    while True:
        
        all_input_sockets = list(file.router_info['inputs'].values())

        socket_list, w_list, e_list = select.select(all_input_sockets, [], [], 5)

        for socket in socket_list:
            packet = socket.recvfrom(1024)[0]  
            router.receive_packet(packet)




def main():
    """ This is the main function which runs the routing protocol."""
    start_daemon()
    
main()

