import sys
import configparser     # ConfigParser class which implements a basic configuration language
import time
import socket
import select
import threading    # use timer here so sys load will not affect the time
import random

LOCAL_HOST = '127.0.0.1'


class Rip_routing():
    

    def __init__(self, router_id, neighbours, sending_socket):
        """ Initialises the router. """
        self.table = {}
        self.self_id = router_id
        self.neighbours = neighbours
        self.sending_socket = sending_socket        
        self.timeout = 30
        self.garbage_time = 30
        
        
    def init_timer(self, dst_id):
        """ Initializes the timer. """
        (flag, timeout_timer, garbage_timer) = (self.table[dst_id][2], self.table[dst_id][3], self.table[dst_id][4])
        self.table[dst_id][2] = False
        self.table[dst_id][3].cancel()
        self.table[dst_id][4].cancel()
        self.table[dst_id][3] = self.start_timeout(dst_id)
        self.table[dst_id][4] = threading.Timer(self.garbage_time, self.delete_router, (dst_id,))
    
        
        
   
    def start_timeout(self, router_id):
        """Starts a timeout timer for an entry in the routing table""" 
        # Remember when deleting from the table, cancel this timer first
        time = threading.Timer(self.timeout, self.end_timeout,(router_id,)) #for every 30 will call not_reciving func
        time.start()    
        return time
    
    
    
    
    def end_timeout(self, router_id):
        """ Updates the routing table after a router has timed out. """
        # After timeout, the router changes the metric of that entry and triggers updates 
        give_msg("Router {} has timed out!\n".format(router_id))
        entry = self.table.get(router_id)
        if entry[2] == False:
            entry[0] = 16  # Change metric to 16
            entry[2] = True # Change Flag
            self.send_packet_to_neighbour() # Triggers updates when metric first becomes 16
        self.start_garbage_timer(router_id) # Start a garbage timer
        entry[3].cancel() # Closes the timeout timer   
        
        
        
        
    def start_garbage_timer(self, router_id):
        '''Starts a garbage timer. '''
        self.table.get(router_id)[4].start()    
        

        
        
    def delete_router(self, router_id):
        '''Upon completion of garbage timer, it pops the router from the table.'''
        timeout_timer, garbage_timer = (self.table[router_id][3], self.table[router_id][4])
        #cancel timer for the timeout and garbage
        timeout_timer.cancel() 
        garbage_timer.cancel()
    
        popped_router = self.table.pop(router_id, 0)
        
        # 
        if popped_router == 0:
            give_msg(f"No such router_id:{router_id} in the routing table")
            return 
        #
        
        give_msg("Router {} has been deleted from the routing table.".format(router_id))
        give_msg("New Routing Table: ")
        self.print_routing_table()    
    
                
                
                
    def create_rip_packet(self, send_to_neighbour_id):
        """ Creates a RIP Packet from the routing table to send to one of the neighbours. """
        
        packet = bytearray()
        
        # RIP Common Header
        packet.append(2) # Command
        packet.append(2) # Version
        packet.append(self.self_id &0xFF) # Router id
        packet.append((self.self_id >> 8) &0xFF) #R outeprint_routing_table ID
        
        # RIP Entries
        if (len(self.table) == 0): #If no entry in table, only header will be sent to the table
            return packet
        
        for dst_router_id, values in self.table.items():
            if dst_router_id == send_to_neighbour_id:
                continue
            
            # Address family identifier 
            packet.append(0)
            packet.append(0)
            
            # Route tag
            packet.append(0)
            packet.append(0)
            
            # Router ID/IP
            packet.append(0)
            packet.append(0)
            packet.append(dst_router_id &0xFF) 
            packet.append((dst_router_id >> 8) &0xFF)   
            # Subnet mask
            packet.append(0)
            packet.append(0)
            packet.append(0)
            packet.append(0)        
            # Next Hop
            packet.append(0)
            packet.append(0)
            packet.append(0)
            packet.append(0)     
            
            
            metric = values[0]
            next_hop = values[1]             
            
            # Implementing split horzion with posioned reverse. Updating metric accordingly.
            # Metric
            if ((send_to_neighbour_id != dst_router_id) and (next_hop == send_to_neighbour_id)):
                packet.append(0)
                packet.append(0)
                packet.append(0)
                packet.append(16 &0xFF)                      
            else:
                packet.append(0)
                packet.append(0)
                packet.append(0)
                packet.append(metric &0xFF) 
                
        return packet   
    
    
    
    
    
    
    def check_rip_header(self, header):
        """ Checks if the RIP header is correct. If it is correct, it returns
        the id of the router it received from."""
        
        command = int(header[0])
        version = int(header[1])
        received_from_router_id = (int(header[2] & 0xFF)) + int((header[3] << 8))
        
        if ((command != 2 or version != 2) or (received_from_router_id < 1 or received_from_router_id > 6400)) :
            print_msg("Wrong Packet Received!\n")
            return False
        else:
            return received_from_router_id   
        
        
        
        
        
    def check_rip_entry(self, entry):
        """  Checks the incoming packet for correctness and returns True if 
        check passed. """
        
        address_family_id = (int(entry[0]), int(entry[1]))
        route_tag = (int(entry[2]), int(entry[3])) 
        router_id = (int(entry[4]), int(entry[5])) 
        subnet_mask = (int(entry[8]), int(entry[9]), int(entry[10]), int(entry[11])) 
        next_hop = (int(entry[12]), int(entry[13]), int(entry[14]), int(entry[15])) 
        metric_zero_part = (int(entry[16]), int(entry[17]), int(entry[18]))
        metric = (int(entry[19]))
        
        entry_check_passed = False
        
        # Check address family identifier 
        if (address_family_id != (0,0)):
            print_msg("\nIncorrect Packet. Wrong address family identifier value.")
        # Check route tag
        elif (route_tag != (0,0)):
            print_msg("\nIncorrect Packet. Wrong route tag value.")
        # Check router id
        elif (router_id != (0,0)):
            print_msg("\nIncorrect Packet. Wrong router id value.")
        # Check subnet mask    
        elif (subnet_mask != (0,0,0,0)):
            print_msg("\nIncorrect Packet. Wrong subnet mask value.")
        # Check next_hop
        elif (next_hop != (0,0,0,0)):
            print_msg("\nIncorrect Packet. Wrong next hop value.")
        # Check metric 
        elif (metric_zero_part != (0,0,0)):
            print_msg("\nIncorrect Packet. Wrong metric value.")
        elif (metric > 16 or metric < 0):
            print_msg("\nIncorrect Packet. Metric value out of range.")
        else:
            entry_check_passed = True
            
        return entry_check_passed
            
      
    
     
       
       
        
    def receive_packet(self, packet):
        """ Process a received packet. """
        
        # Check header and entries
        len_packet = len(packet)
        neb_id = self.check_rip_header(packet)
        
        # If header check fails, then the packet is dropped.
        if (neb_id == False): 
            print_msg("\nIncorrect packet header. Packet dropped!")
            return
        
        #
        for entry_start_index in range(4,len_packet,20): #every entry has 20byts
            if not self.check_rip_entry(packet[entry_start_index:entry_start_index+20]):
                index_entry = (len_packet - 4) // 20
                print_msg(f"wrong entry for index_entry: {index_entry} format-----------------")
                print_msg("\nDropped the packet!")
                return         
        #    
            
        # Packet checking ends.
        
        # If table doesn't have neighbour
        if (self.table.get(neb_id) == None):
            cost,_ = self.neighbours.get(neb_id)
            self.table[neb_id] = [cost, neb_id, False, self.start_timeout(neb_id), threading.Timer(self.garbage_time, self.delete_router, (neb_id,))]
        # Else, reinitialise the timer
        else:
            self.init_timer(neb_id)
            
        # Stops furthur processing if only the header is received.
        if (len_packet == 4):
            return
        # End of neighbour processing
        
        # Start for non-neighbour processing
        for entry_start_index in range(4,len_packet,20):
            index_entry = (len_packet - 4) // 20
            self.process_entry(packet[entry_start_index:entry_start_index+20],neb_id)
            
        # Prints routing table after receiving and processing packet.    
        self.print_routing_table()
    
    
    
    
    
    def process_entry(self, entry, neb_id):
        """NEED IMP LATER FOR CHANGE TABLE when recive cost 16"""
    
        router_id = (int(entry[6] & 0xFF)) + int((entry[7] << 8))    
        metric = int(entry[19])
        total_cost = min(16, self.neighbours.get(neb_id)[0] + metric)
        
        #change metric of the table  
        if self.table.get(router_id):
            #next_hop   
            next_hop = self.table.get(router_id)[1]               
            if next_hop == neb_id: #next hop is packet from
                          
                if total_cost != self.table.get(router_id)[0]: #if cost diff reinital timer and change cost
                    self.init_timer(router_id)
                    self.table.get(router_id)[0] = total_cost                             
                    
                    if total_cost == 16: #trigger event first time to 16
                        self.table.get(router_id)[2] = True
                        self.table[router_id][3].cancel()
                        self.send_packet_to_neighbour()
                        self.start_garbage_timer(router_id) 
                else:
                    #cost dun change but not 16
                    if total_cost != 16:
                        self.init_timer(router_id)
                
                
            else: #if next hop not from packet send from and it cost less
                if total_cost < self.table.get(router_id)[0]:
                    self.table[router_id][3].cancel()
                    self.table[router_id][4].cancel()
                    self.table[router_id] = [total_cost, neb_id, False, self.start_timeout(router_id),threading.Timer(self.garbage_time, self.delete_router,(router_id,))]
            
        elif self.table.get(router_id) == None and total_cost != 16:
            self.table[router_id] = [total_cost, neb_id, False, self.start_timeout(router_id),threading.Timer(self.garbage_time, self.delete_router,(router_id,))]
        
            
        #else do onthing
        
        
        
        
        
        
        
        
        
        
    def print_routing_table(self):
        """ Prints the routing table's current condition."""
        print("\n")
        print(" _________________(Routing Table: Router {})___________________".format(self.self_id))
        print("|__________________        Time          ______________________|")
        print("|______________________________________________________________|")
        print("| Router ID | Next Hop | Cost |    Timeout   |  Garbage Timer  |")
        print("|-----------|----------|------|--------------|-----------------|")
        print("|{:^11}|{:^10}|{:^6}|{:^14.2f}|{:^17}|".format(self.self_id, '-', 0, 0, 0))

        
        for router_id, keys in self.table.items():
            metric = keys[0]
            next_hop = keys[1]
            time_out = keys[3]
            garbage_time = keys[4]
            print("|{:^11}|{:^10}|{:^6}|{:^14.2f}|{:^17}|".format(router_id, next_hop, metric, 0, 0))

        print("|___________|__________|______|______________|_________________|")
        print("\n")
             
   
   
    def send_packet_to_neighbour(self):
        #craete packet and send to neigbour
        for neighbor_id, values in self.neighbours.items():
            rip_packet = self.create_rip_packet(neighbor_id)
            self.sending_socket.sendto(rip_packet, (LOCAL_HOST, values[1])) #need input port and out port as gloabl
        print()
        self.print_routing_table()
    
    
    def perdic_send_to_neightr(self):
        self.send_packet_to_neighbour()
        #perdic send packet to neighbour
        t = threading.Timer(3+(random.randrange(0, 6)*random.randrange(-1, 2)),self.perdic_send_to_neightr) #3+(random.randrange(0, 6)*random.randrange(-1, 2))
        t.start() 


        
def give_msg(message):
    """ Prints the message and the time at which it was sent. """
    current_time = time.strftime("%Hh:%Mm:%Ss")
    print("[" + current_time + "]: " + message)   


