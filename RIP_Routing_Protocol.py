'''
    COSC364 (RIP Assignment)
    Authors: Haider Saeed, Drogo Shi
    Date: 07/03/2022
    
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
from RIP_CLASS import*

LOCAL_HOST = '127.0.0.1'


""" 
    neighbor[router_id] = [cost, port_num] #dict type
    router_info[port] = socket #all port socket for recive packet
    table[dst_id] = [cost, next_hop, flag, timeout, garbage_timer]
    

"""
#*******************************************************************************

class Configure():
    ''' Class which reads and processes the configuration file of
    a router using filename. '''
    
    
    def __init__(self, config_file):
        """ Initiates the configuration file. """
        self.config_file = config_file
        self.router_info = {} #i think it's better un pack this to self.input and self.router_id
        self.neighbor = {}  #I add this new more useable so the inf['outputs'] will not needed
        
        
        
    def router_id_check(self, router_id):
        """ Checks if the router_id is within 
        the supported parameter range. """
        
        if (1 <= int(router_id) <= 64000):
            return True
        else:
            print_msg('Router ID check failed.\n')
            raise Exception('Router ID is not valid.\n')
        
        
        
    def cost_check(self, cost):
        """ Checks if the cost is within 
        the supported parameter range. """
        
        if (1 <= int(cost) <= 15):
            return True
        else:
            print_msg('Output Router cost check failed.\n')
            raise Exception('Router cost is not valid.\n')
        
        
        
    def port_check(self, port):
        """ Checks if the port is within 
        the supported parameter range. """
        
        if (1 <= int(port) <= 64000):
            return True
        else:
            print_msg('Output Router ID check failed.\n')
            raise Exception('Output Router ID is not valid.\n')            
            
      
        
    def get_router_id(self, config):
        """ Gets the router id from the config file of the router after 
        performing sanity checks. """
        
        router_id = config['Router_Info']['router_id']
        
        if (self.router_id_check(router_id)):
            self.router_info['router_id'] = int(router_id)
            
     
        
    def get_output_ports(self, config):
        
        router_outputs = config['Router_Info']['outputs'].split(', ')
       
        output_params = []
        
        # Converting (5001-2-3) to (5001, 2, 3)
        for output in router_outputs: 
            params = output.split('-')
            output_params.append(params)
            
        output_ports = []
        self.router_info['outputs'] = []
            
        for param in output_params:
            
            port = param[0]
            cost = param[1]
            router_id = param[2]
            
            if (self.router_id_check(router_id) and 
                (int(port) not in output_ports)
                and self.cost_check(cost) and self.port_check(port)):
                
                output_ports.append(port)
                output = {'router_id': int(router_id), 'port': int(port),
                          'cost': int(cost)}
                self.router_info['outputs'].append(output)   
                self.neighbor[int(router_id)] = [int(cost), int(port)]
        
                
        router_inputs = config['Router_Info']['input_ports'].split(', ') 
        
        # Checks if any port number from output port exists in input ports
        for input_port in router_inputs:
            if (self.port_check(input_port) and int(input_port) not in output_ports):
                continue
            else:
                print_msg('No output port numbers can be in input ports.\n')
                raise Exception('Error - Output Port in Input Port\n') 
            
     
     
    def configure_inputs(self, config):
        """ Gets the input ports for the router and for each port opens a UDP
        socket and attempts to bind to it. """
        
        router_inputs = config['Router_Info']['input_ports'].split(', ')
        
        input_ports = []
        
        for input_port in router_inputs:
            self.port_check(input_port)
            input_port = int(input_port)
            input_ports.append(input_port)
        
        
        self.router_info['inputs'] = {}
        
        for port in input_ports:
            
            # Trying to create a UDP socket for each port.
            try:
                self.router_info['inputs'][port] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                print_msg('Success - Created socket for Port #' + str(port))
            except socket.error as message:
                print_msg('Failure - Unable to create socket. ' + str(message))
                sys.exit()     
                
            # Trying to bind each port to the socket. #try to move this to router class
            try:
                self.router_info['inputs'][port].bind((LOCAL_HOST, port))
                print_msg('Success - Bound Port #' + str(port) + 
                          ' to the socket')
            except socket.error as msg:
                print_msg('Failure - Unable to bind port to socket. ' + str(msg))
                sys.exit()            
        
        

        
    def read_and_process_file(self):
        """ Starts processing and reading the configuration file of the router
        while performing sanity checks. """
        
        config = configparser.ConfigParser()
        config.read(self.config_file)
        
        self.get_router_id(config)
        self.get_output_ports(config)
        
        print_msg('Success - All parameters passed the sanity checks')
        
        self.configure_inputs(config)
        
        
#*******************************************************************************

        
        
        
    
def print_msg(message):
    """ Prints the message and the time at which it was sent. """
    current_time = time.strftime("%Hh:%Mm:%Ss")
    print("[" + current_time + "]: " + message)
    
       
# Currently being used for testing.
def main():
    """ This is the main function which runs the routing protocol. """

    filename = sys.argv[1]
    router = Configure(filename)
    router.read_and_process_file() #create sockets and config 
    
    #get intance router id
    router_id_self = router.router_info['router_id']
    
    #let first one input socket to send out packet
    #send_socket_port = list(router.router_info['inputs'].keys())[0]
    #router.router_info['inputs'].get(send_socket_port) 
    sending_socket = list(router.router_info['inputs'].values())[0]
    rip_deamon = Rip_routing(router_id_self, router.neighbor, sending_socket)
  
    #send packet to neighbor
    rip_deamon.perdic_send_to_neightr()
    while True:
        all_input_socket = list(router.router_info['inputs'].values())
        r_list, w_list, e_list = select.select(all_input_socket,[],[],5)
        for sk in r_list:
            packet = sk.recvfrom(1024)[0]  
            rip_deamon.recive_packet(packet)
        
main()
