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
Neighbour = []            #contain all neighbour router id
Sending_socket = None       #choise one of input port as Sending socket
Router_id_self = None       #router id of this instance
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
        
        self.router_info['inputs'] = []
        
        for input_port in router_inputs:
            self.port_check(input_port)
            input_port = int(input_port)
            self.router_info['inputs'].append(input_port)
        
        
        

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
    
        
    
        
def create_rip_packet(send_to_neighbour_id):
    """create rip packet from routing table TO one of the neighbour_id 
       NEED TO IMP WHEN THE METRIC IS 16 HERE----------------
    """
    packet = bytearray()
    #rip common header
    packet.append(2) #command
    packet.append(2) #version
    packet.append(Router_id_self &0xFF) #Router id
    packet.append((Router_id_self >> 8) &0xFF) #Router id
    #rip entrys
    if len(TABLE) > 20:
        return 
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
        
        metric = values[1]
        next_hop = values[2]   
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
    #check hearder and entry
    if not rip_check_header(packet[:4]): 
        print("wrong header format-----------------")
        return
    len_packet = len(packet)
    rip_id_sent_from = (int(packet[:4][2] & 0xFF)) + int((packet[:4][3] << 8))
    print("----------packet header check pass----------")
    print() 
    
    for entry_start_index in range(4,len_packet,24):
        if not rip_check_entry(packet[entry_start_index:entry_start_index+24]):
            print("wrong entry format-----------------")
            return 
    print("----------packet entry check pass----------")
    print()    
    #process entry
    for entry_start_index in range(4,len_packet,24):
        process_entry(packet[entry_start_index:entry_start_index+24],rip_id_sent_from)
    print("-----------------end process packet-----------------")
    print()
        


def process_entry(entry, rip_id_sent_from):
    """NEED IMP LATER FOR CHANGE TABLE when recive cost 16"""
    #router_id
    router_id = (int(entry[6] & 0xFF)) + int((entry[7] << 8))    
    #metric
    metric = int(entry[19])
    #next_hop   
    next_hop = (int(entry[22] & 0xFF)) + int((entry[23] << 8))
    
    #change metric of the table
    if TABLE.get(router_id):
        cost = min(TABLE.get(router_id)[1], TABLE.get(rip_id_sent_from)[1]+metric)
        TABLE.get(router_id)[1] = cost
        TABLE.get(router_id)[3] = True
        
    else:
        cost = min(16, TABLE.get(rip_id_sent_from)[1]+metric)
        TABLE[router_id] = [None, cost, rip_id_sent_from,False, [start_time_out(router_id),threading.Timer(20, delet_router,(router_id,))]]
    print_routing_table()

    
    
def recived_update_router(rip_id_sent_from):
    """when recive updating packet from a router"""
    timeout_timer = TABLE.get(rip_id_sent_from)[4][0]
    timeout_timer.cancel() #means the router not time out 
    TABLE.get(rip_id_sent_from)[4][0] = start_time_out(rip_id_sent_from) #restart timing for time out
    
    TABLE.get(rip_id_sent_from)[4][1].cancel() #cancel garbage timer not care if it started 
    TABLE.get(rip_id_sent_from)[4][1] = threading.Timer(20, delet_router,(rip_id_sent_from,)) #create new garbage timer but it not started    
    print("----------reset time out timer----------")
    print()
    
    
    
def rip_check_header(header):
    """check rip header"""
  
    command = int(header[0])
    version = int(header[1])
    rip_id_sent_from = (int(header[2] & 0xFF)) + int((header[3] << 8))
    
    print("----------recive packet from {}----------".format(rip_id_sent_from))
    recived_update_router(rip_id_sent_from)
    
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
    for neighbor_id, values in TABLE.items():
        if neighbor_id in Neighbour:
            
            rip_packet = create_rip_packet(neighbor_id)
            Sending_socket.sendto(rip_packet, (LOCAL_HOST, values[0])) #need input port and out port as gloabl
            print("sending to {}".format(values[0]))
  
    print("All packets to neighbors are sent")
    print()

def perdic_send_to_neightr():
    send_packet_to_neighbour()
    #perdic send packet to neighbour
    t = threading.Timer(30+(random.randrange(0, 6)*random.randrange(-1, 2)),perdic_send_to_neightr)
    t.start()



#*******************************************************************************

class Router:
    
    """ A class definition of a single router. """
    
    def __init__(self, router_config_file):
        """ Router Initialiser """
        
        self.router_file = router_config_file
        
        self.router_id = None
        self.router_info = {}             # router raw info after running Config(router)
        self.router_op_data = []          # router's output data  ->  "{'router_id': 2, 'port': 1501, 'cost': 1}"
        self.router_ip_ports = []         # router's input ports 
        self.routing_table = {}           # router's own routing table
        self.neighbour_ids = []
        
        
        
    def configure_router(self):
        """ Runs the configuration file for the router. """
        
        router = Configure(self.router_file)                # Runs Config class on router config filename
        router.read_and_process_file()                      # Reads and processes the config file
        
        self.router_info = router.router_info               # Sets raw routing data from cConfig to current router after sanity checks are complete
        
        self.router_id = self.router_info['router_id']      # Sets the router id 
        
        for output in self.router_info['outputs']:          # Adds the router's output information to the router_op_data  
            self.router_op_data.append(output)
        
        for input_port in self.router_info['inputs']:       # Adds the router's input ports to the router_ip_ports
            self.router_ip_ports.append(input_port)
            
        self.create_sockets() 
    
        
    
    def create_routing_table(self):
        """{'router_id': 2, 'port': 1501, 'cost': 1} ==> dictionary 
        dst_rt_id: port_num, metric, next_hop_id, flag, [timeout, garbage_timer]"""
        
        for output in self.router_op_data:
            
            router_id = output['router_id']
            port = output['port']
            cost = output['cost']
            flag = False
            timeout = self.start_timeout(router_id)
            garbage_timer = threading.Timer(20, self.delete_router, (router_id))
            
            self.routing_table[router_id] = [port, cost, router_id, flag, [timeout, garbage_timer]] #flag and timer later implment
            self.neighbour_ids.append(router_id)     # Creates a list of id's for neighbouring routers
            
        print_msg("Routing Table created for Router: {}\n".format(self.router_id))   
        
        
        
    def create_sockets(self):
        """ Creates a UDP socket for each input port. """
        
        self.router_info['inputs'] = {}
        
        for port in self.router_ip_ports:
            
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
        
        
        
    def start_timeout(self, router_id):
        """ Starts a timeout for an entry in the routing table. """
        timeout = threading.Timer(30, self.after_timeout, (router_id,)) #for every 180 seconds will call not_reciving func
        timeout.start()       #start the thread
        return timeout
        
        
        
    def after_timeout(self, router_id):
        """need to solve if all table is empty_________________________"""
        #after timeout the router change metric of that entry and trigger updates 
        print_msg("WARNING - Router {} has timed out\n".format(router_id))
        
        entry = self.routing_table.get(router_id)
        entry[1] = 16  #set metic to 16
        entry[3] = True # change flag
        send_packet_to_neighbour() #trigger updates
        self.start_garbage_timer(router_id) #start a garbage timer
        entry[4][0].cancel() #close the timeout timer
        
        
        
    def delete_router(self, router_id):
        """ Pops the router if garbage timer expires. """
        popped_router = self.routing_table.pop(router_id)
        print_msg("Router {} has been deleted from the routing table".format(router_id))

            
            
    def start_garbage_timer(self, router_id):
        """ Starts a garbage timer for the router. """
        garbage_timer = self.routing_table[router_id][4][1]
        garbage_timer.start()    


    
    def print_routing_table(self):
        """ Prints the routing table. """ 
        print("\n")
        print(" _______________________________________(Routing Table: Router {})____________________________________________".format(self.router_id))
        print("|____________________________________________________________________________________________________________|")
        print("| Router ID | Port | Cost |  Flag  |                Timeout             |           Garbage Timer            |")
        print("|-----------|------|------|--------|------------------------------------|------------------------------------|")
        
        for router_id, output in self.routing_table.items():
            port = output[0]
            cost = output[1]
            router_id = output[2]     # ID for neighbour router
            flag = output[3]
            timeout = output[4][0]
            garbage_timer = output[4][1]
            
            print("|     {0}     | {1} |  {2}   |  {3} |   {4}       {5}".format(router_id, port, cost, flag, timeout, garbage_timer))
            
            
        print("|____________________________________________________________________________________________________________|\n")
        print("\n")
        
    
    
    
           
    def check_format(self):
        """ FOR US TO CHECK THE FROMAT OF THE GIVEN ROUTER AND ITS VALUES. """
        
        print("\n_____________ router_op_data _____________")                 
        for val in self.router_op_data:                 
            print(val)
        print("********************************************\n")
        
        print("\n_____________ router_ip_ports _____________")
        for val1 in self.router_ip_ports:
            print(val1)
        print("---------------------------------------------\n")
    
        print("\n_____________ router_id_____________")
        print(self.router_id)
        print("--------------------------------------\n")
        
        
              


# Currently being used for testing.
def main():
    """ This is the main function which runs the routing protocol. """
    global Table
    global Sending_socket
    global Router_id_self
    
    filename = "router1.txt"
    router = Router(filename)
    router.configure_router()  
    router.create_routing_table()
    #router.check_format()          #Run this to check format of values in Router class
    
    
    #initial routing table dst_rt_id: port_num, metric, next_hop_id, flag, timer
    router.create_routing_table()
    router.print_routing_table()
    #for key,values in table.items():
    #   print(key,values)
    
    #get intance router id
    Router_id_self = router.router_info['router_id']
    #let first one input socket to send out packet
    send_socket_port = list(router.router_info['inputs'].keys())[0]
    Sending_socket = router.router_info['inputs'].get(send_socket_port) 
    #send packet to neighbor every 5s
    perdic_send_to_neightr()
    
    while True:
        all_input_socket = list(router.router_info['inputs'].values())
        r_list, w_list, e_list = select.select(all_input_socket,[],[],5)
   
        for sk in r_list:
            packet = sk.recvfrom(1024)[0]  
            recive_packet(packet)
        
main()