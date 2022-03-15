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

TABLE = {}                  #routing table 
Neighbour = []            #contain all neighbour router id:[cost port]
Sending_socket = None       #choise one of input port as Sending socket
Router_id_self = None       #router id of this instance
Router_outps = None
LOCAL_HOST = '127.0.0.1'

#*******************************************************************************

class Configure():
    ''' Class which reads and processes the configuration file of
    a router using filename. '''
    
    
    def __init__(self, config_file):
        """ Initiates the configuration file. """
        self.config_file = config_file
        self.router_info = {}
        self.neighbor = {}
        
        
        
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
    
        
def start_time_out(router_id):
    """start a time out timer for a entry in routing table"""
    t = threading.Timer(30, after_timeout,(router_id,)) #for every 180 will call not_reciving func
    t.start()                             #start the thread
    return t

def after_timeout(router_id):
    """need to solve if all table is empty_________________________"""
    #after timeout the router change metric of that entry and trigger updates 
    global TABLE
    print("time out for {}!!!!!!!!!!!!".format(router_id))
    print()    
    entry = TABLE.get(router_id)
    entry[0] = 16  #metic to 16
    entry[2] = True #change flag
    send_packet_to_neighbour() #trigger updates
    set_garbage_timer(router_id) #start a garbage timer
    entry[3].cancel() #close the timeout timer
    
def set_garbage_timer(router_id):
    #start a garbage timer
    TABLE.get(router_id)[4].start()

    
def delet_router(router_id):
    #upon garbage time it will pop the router
    global TABLE
    TABLE[router_id][3].cancel()
    TABLE[router_id][4].cancel()
    poped_router = TABLE.pop(router_id, 0)
    if poped_router == 0:
        return 
    print("------{} has been deleted from the routing table".format(poped_router))
    print_routing_table()
    
        
def create_rip_packet(send_to_neighbour_id):
    """create rip packet from routing table TO one of the neighbour_id 
       NEED TO IMP WHEN THE METRIC IS 16 HERE----------------
    """
    global TABLE
    packet = bytearray()
    #rip common header
    packet.append(2) #command
    packet.append(2) #version
    packet.append(Router_id_self &0xFF) #Router id
    packet.append((Router_id_self >> 8) &0xFF) #Router id
    #rip entrys
    if len(TABLE) > 20: #how to deal with this?
        return 
    if len(TABLE) == 0:
        return packet
    for dst_router_id, values in TABLE.items():
        if dst_router_id == send_to_neighbour_id:
            continue
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
        
        metric = values[0]
        next_hop = values[1]   
        #horzion split with posion reverse
        if send_to_neighbour_id != dst_router_id and next_hop == send_to_neighbour_id:
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
    print("packet ready for send to router{} from {}-----------------".format(send_to_neighbour_id, Router_id_self))
    print("")
    return packet


def recive_packet(packet):
    """process recive packet"""
    global TABLE
    #check hearder and entry
    len_packet = len(packet)
    if not rip_check_header(packet[:4]): 
        print("wrong header format  drop-----------------")
        return 
    
    neb_id = (int(packet[:4][2] & 0xFF)) + int((packet[:4][3] << 8))
    
    if TABLE.get(neb_id) == None:
        cost,_ = Neighbour.get(neb_id)
        TABLE[neb_id] = [cost, neb_id, False, start_time_out(neb_id), threading.Timer(20, delet_router, (neb_id,))]
        
    else:
        cost,_ = Neighbour.get(neb_id)
        TABLE[neb_id][0] = cost
        TABLE[neb_id][3].cancel()
        TABLE[neb_id][3] = start_time_out(neb_id)
        TABLE[neb_id][4].cancel()
        TABLE[neb_id][4] = threading.Timer(20, delet_router, (neb_id,))
    if len_packet == 4:
        print_routing_table()
        return
    #end for neb processing 
    
    for entry_start_index in range(4,len_packet,24):
        if not rip_check_entry(packet[entry_start_index:entry_start_index+24]):
            index_entry = (len_packet - 4) // 24
            print(f"wrong entry {index_entry} format-----------------")
            return 
    print("----------packet entry check pass----------")
    print()    
    
    #start for non_neb processing
    for entry_start_index in range(4,len_packet,24):
        index_entry = (len_packet - 4) // 24
        print(f"Processing entry{index_entry}-------------------")
        process_entry(packet[entry_start_index:entry_start_index+24],neb_id)
    print("-----------------end process packet-----------------")
    print()
    print_routing_table()
        
def print_routing_table():
    print(f"Roting table for router{Router_id_self}:")
    print("dst----------metric----------next_hop")
    for router_id, keys in TABLE.items():

        metric = keys[0]
        next_hop = keys[1]
        print("{}{:13}{:16}".format(router_id, metric, next_hop))

def process_entry(entry, neb_id):
    """NEED IMP LATER FOR CHANGE TABLE when recive cost 16"""
    global TABLE
    #router_id
    router_id = (int(entry[6] & 0xFF)) + int((entry[7] << 8))    
    #metric
    metric = int(entry[19])
    #next_hop   
    next_hop = (int(entry[22] & 0xFF)) + int((entry[23] << 8))
    
    total_cost = min(16, Neighbour.get(neb_id)[0] + metric)
    #change metric of the table
    if TABLE.get(router_id):
        if next_hop == neb_id:
            if total_cost != TABLE.get(router_id)[0]:
                TABLE.get(router_id)[3].cancel()
                TABLE.get(router_id)[3] = start_time_out(router_id)
                TABLE.get(router_id)[4].cancel()
                TABLE.get(router_id)[4] = threading.Timer(20, delet_router, (neb_id,))
                TABLE.get(router_id)[0] = total_cost                             
                TABLE.get(router_id)[2] = True
                if total_cost == 16:
                    set_garbage_timer(router_id) 
            else:
                if total_cost != 16:
                    TABLE.get(router_id)[3].cancel()
                    TABLE.get(router_id)[3] = start_time_out(router_id)
            
            
        else:
            if total_cost < TABLE.get(router_id)[0]:
                TABLE.get(router_id)[3].cancel()
                TABLE.get(router_id)[4].cancel()
                TABLE[router_id] = [total_cost, neb_id, False, start_time_out(router_id),threading.Timer(20, delet_router,(router_id,))]
        
    elif TABLE.get(router_id) == None and total_cost != 16:
        TABLE[router_id] = [total_cost, neb_id, False, start_time_out(router_id),threading.Timer(20, delet_router,(router_id,))]
    
        
    #else do onthing
    print_routing_table()

def rip_check_header(header):
    """check rip header"""
  
    command = int(header[0])
    version = int(header[1])
    rip_id_sent_from = (int(header[2] & 0xFF)) + int((header[3] << 8))
    
    print("----------recive packet from {}----------".format(rip_id_sent_from))
    if command != 2 or version != 2:
        return False
    else:
        
        return True

def rip_check_entry(entry):
    #address Family 0
    family_idfer = int(entry[0]) + int(entry[1]) 
    if family_idfer != 0:
        print("family_idfer wrong!!!")
        return False
    #zero_part 
    zero_part = int(entry[2]) + int(entry[3]) 
    if zero_part != 0:
        print("should be zero!!!")
        return False    
    
    #router_id
    zero_part = int(entry[4]) + int(entry[5]) 
    if zero_part != 0:
        print("should be zero!!!")
        return False      
    router_id = (int(entry[6] & 0xFF)) + int((entry[7] << 8))
  
    #must be zero
    zero_part = int(entry[8]) + int(entry[9]) + int(entry[10]) + int(entry[11]) 
    if zero_part != 0:
        print("should be zero!!!")
        return False    
    #must be zero
    zero_part = int(entry[12]) + int(entry[13]) + int(entry[14]) + int(entry[15]) 
    if zero_part != 0:
        print("should be zero!!!")
        return False  
    #metric
    zero_part = int(entry[16]) + int(entry[17]) + int(entry[18])
    if zero_part != 0:
        print("should be zero!!!")
        return False   
   
    metric = int(entry[19])
    if not(0 < metric and metric <= 16):
        print("metric wrong!!!")
        return False      
    
    #next_hop   
    zero_part = int(entry[20]) + int(entry[21]) 
    if zero_part != 0:
        print("should be zero!!!")
        return False  
    next_hop = (int(entry[22] & 0xFF)) + int((entry[23] << 8))

    return True


def send_packet_to_neighbour():
    #craete packet and send to neigbour
    for neighbor_id, values in Neighbour.items():
       
            
        rip_packet = create_rip_packet(neighbor_id)
        Sending_socket.sendto(rip_packet, (LOCAL_HOST, values[1])) #need input port and out port as gloabl
        print("sending to {}".format(values[1]))
  
    print("All packets to neighbors are sent")
    print()
    print_routing_table()

def perdic_send_to_neightr():
    send_packet_to_neighbour()
    #perdic send packet to neighbour
    t = threading.Timer(3+(random.randrange(0, 6)*random.randrange(-1, 2)),perdic_send_to_neightr)
    t.start()

# Currently being used for testing.
def main():
    """ This is the main function which runs the routing protocol. """
    global TABLE
    global Sending_socket
    global Router_id_self
    global Neighbour
    
    filename = sys.argv[1]
    router = Configure(filename)
    router.read_and_process_file() #create sockets and config 
    
    Router_outps = router.neighbor
    #get intance router id
    Router_id_self = router.router_info['router_id']
    #let first one input socket to send out packet
    send_socket_port = list(router.router_info['inputs'].keys())[0]
    Sending_socket = router.router_info['inputs'].get(send_socket_port) 
    Neighbour = router.neighbor
  
  
    #send packet to neighbor every 5s
    perdic_send_to_neightr()
    
    while True:
        all_input_socket = list(router.router_info['inputs'].values())
        r_list, w_list, e_list = select.select(all_input_socket,[],[],5)
   
        for sk in r_list:
            packet = sk.recvfrom(1024)[0]  
            recive_packet(packet)
        
main()