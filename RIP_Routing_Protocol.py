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

LOCAL_HOST = '127.0.0.1'

#*******************************************************************************

class Configure():
    ''' Class which reads and processes the configuration file of
    a router using filename. '''
    
    
    def __init__(self, config_file):
        """ Initiates the configuration file. """
        self.config_file = config_file
        self.router_info = {}
        
        
        
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
                
            # Trying to bind each port to the socket.
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
    
        
    
    

def create_routing_table(neighbours):
    """{'router_id': 2, 'port': 1501, 'cost': 1} ==> dictionary 
        dst_rt_id: port_num, metric, next_hop_id, flag, timer"""
    routing_table = {}
    for neighbour in neighbours:
        routing_table[neighbour['router_id']] = [neighbour['port'],neighbour['cost'], neighbour['router_id'], False, False] #flag and timer later implment
    return routing_table
        



def create_rip_packet(routing_table, router_id_self, pakcet_send_to):
    """create rip packet from routing table"""
    packet = bytearray()
    #rip common header
    packet.append(2) #command
    packet.append(2) #version
    packet.append(router_id_self &0xFF) #Router id
    packet.append((router_id_self >> 8) &0xFF) #Router id
    #rip entrys
    if len(routing_table) > 20:
        return 
    for dst_router_id, values in routing_table.items():
        #address Family 0
        packet.append(0)
        packet.append(0)
        #must be zero
        packet.append(0)
        packet.append(0)
        #Router id  of dst_router_id
        packet.append(0)
        packet.append(0)
        packet.append(dst_router_id &0xFF) 
        packet.append((dst_router_id >> 8) &0xFF)   
        #must be zero
        packet.append(0)
        packet.append(0)
        packet.append(0)
        packet.append(0)        
        #must be zero
        packet.append(0)
        packet.append(0)
        packet.append(0)
        packet.append(0)     
        
        metric = values[1]
        next_hop = values[2]   
        #horzion split with posion reverse
        if pakcet_send_to != dst_router_id and next_hop == pakcet_send_to:
            #metric
            packet.append(0)
            packet.append(0)
            packet.append(0)
            packet.append(16 &0xFF)                      
        else:
            #metric
            packet.append(0)
            packet.append(0)
            packet.append(0)
            packet.append(metric &0xFF) 
        #next_hop
        packet.append(0)
        packet.append(0)
        packet.append(next_hop &0xFF) 
        packet.append((next_hop >> 8) &0xFF)             
    return packet



def recive_packet(packet, rip_id_self):
    """process recive packet"""
    if not rip_check_header(packet[:4], rip_id_self):
        return
    len_packet = len(packet)
    
    for entry_start_index in range(4,len_packet,24):
        if not rip_check_entry(packet[entry_start_index:entry_start_index+24]):
            return 
    print("recived")
        
        



def rip_check_header(header, rip_id_self):
    """check rip header"""
  
    command = int(header[0])
    version = int(header[1])
    rip_id_self_from_packet = (int(header[2] & 0xFF)) + int((header[3] << 8))
    
    print("recive from {}".format(rip_id_self_from_packet))
    
    if command != 2 or version != 2 or rip_id_self_from_packet != rip_id_self:
        return False
    else:
        return True

def rip_check_entry(entry):
    #address Family 0
    family_idfer = int(entry[0]) + int(entry[1]) 
    if family_idfer != 0:
        return False
    #zero_part 
    zero_part = int(entry[2]) + int(entry[3]) 
    if zero_part != 0:
        return False    
    
    #router_id
    zero_part = int(entry[4]) + int(entry[5]) 
    if zero_part != 0:
        return False      
    router_id = (int(entry[6] & 0xFF)) + int((entry[7] << 8))
  
    #must be zero
    zero_part = int(entry[8]) + int(entry[9]) + int(entry[10]) + int(entry[11]) 
    if zero_part != 0:
        return False    
    #must be zero
    zero_part = int(entry[12]) + int(entry[13]) + int(entry[14]) + int(entry[15]) 
    if zero_part != 0:
        return False  
    #metric
    zero_part = int(entry[16]) + int(entry[17]) + int(entry[18])
    if zero_part != 0:
        return False   
   
    metric = int(entry[19])
    if not(0 < metric and metric <= 16):
        return False      
    
    #next_hop   
    zero_part = int(entry[20]) + int(entry[21]) 
    if zero_part != 0:
        return False  
    next_hop = (int(entry[22] & 0xFF)) + int((entry[23] << 8))
    return True

# Currently being used for testing.
def main():
    """ This is the main function which runs the routing protocol. """
    filename = sys.argv[1]
    router = Configure(filename)
    router.read_and_process_file()  
    
    #initial routing table dst_rt_id: port_num, metric, next_hop_id, flag, timer
    table = create_routing_table(router.router_info['outputs'])
    #for key,values in table.items():
    #   print(key,values)
    
    #get intance router id
    router_id_self = router.router_info['router_id']
    
    #let first one input socket to send out packet
    send_socket_port = list(router.router_info['inputs'].keys())[0]
    send_socket = router.router_info['inputs'].get(send_socket_port)
    
    #craete packet and send to neigbour
    for neighbor_id, values in table.items():
        rip_packet = create_rip_packet(table,router_id_self,neighbor_id)
        send_socket.sendto(rip_packet, (LOCAL_HOST, values[0])) #need input port and out port as gloabl
        print("send to {}".format(values[0]))
    print("All packets to neighbors are sent")
    
    while True:
        all_input_socket = list(router.router_info['inputs'].values())
        r_list, w_list, e_list = select.select(all_input_socket,[],[],5)
   
        for sk in r_list:
            packet = sk.recvfrom(1024)[0]  
            recive_packet(packet, router_id_self)
        
main()
