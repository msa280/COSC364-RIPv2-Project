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
        self.table = {}
        self.self_id = router_id
        self.timeout = 30
        self.garbage_time = 30
        self.neighbours = neighbours
        self.sending_socket = sending_socket
        
    def start_time_out(self, router_id):
        """start a time out timer for a entry in routing table""" #rememer when delet from table cancel this timer first*******
        t = threading.Timer(self.timeout, self.after_timeout,(router_id,)) #for every 30 will call not_reciving func
        t.start()    
        return t
    
    def after_timeout(self, router_id):
        """need to solve if all table is empty_________________________"""
        #after timeout the router change metric of that entry and trigger updates 
        print("time out for {}!!!!!!!!!!!!\n".format(router_id))
        entry = self.table.get(router_id)
        if entry[2] == False:
            entry[0] = 16  #metic to 16
            entry[2] = True #change flag
            self.send_packet_to_neighbour() #trigger updates when metric first become 16
        self.set_garbage_timer(router_id) #start a garbage timer
        entry[3].cancel() #close the timeout timer    
        
    def set_garbage_timer(self, router_id):
        '''start a garbage timer '''
        self.table.get(router_id)[4].start()    
        
    def delet_router(self, router_id):
        '''upon garbage time it will pop the router'''
        self.table[router_id][3].cancel() #cancel timer for the timeout and garbage
        self.table[router_id][4].cancel() #cancel timer for the timeout and garbage
        poped_router = self.table.pop(router_id, 0)
        if poped_router == 0:
            print(f"No such router_id:{router_id} in the routing table")
            return 
        print("------{} has been deleted from the routing table".format(router_id))
        print("NEW ROUTING TABLE: ")
        self.print_routing_table()    
    
                
    def create_rip_packet(self, send_to_neighbour_id):
        """create rip packet from routing table TO one of the neighbour_id 
        """
        packet = bytearray()
        
        #rip common header
        packet.append(2) #command
        packet.append(2) #version
        packet.append(self.self_id &0xFF) #Router id
        packet.append((self.self_id >> 8) &0xFF) #Routeprint_routing_tabler id
        
        #rip entrys
        if len(self.table) == 0: #no entry in table will only send header to neb
            return packet
        for dst_router_id, values in self.table.items():
            if dst_router_id == send_to_neighbour_id:
                continue
            #address Family 0
            packet.append(0)
            packet.append(0)
            #must be zero
            packet.append(0)
            packet.append(0)
            #Router id  of dst_router_id AS MAX ID 64000 < 2**16
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
        return packet   
    
    def rip_check_header(self, header):
        """check rip header"""
        command = int(header[0])
        version = int(header[1])
        id_send_from = (int(header[2] & 0xFF)) + int((header[3] << 8))
        if command != 2 or version != 2 or id_send_from < 1 or id_send_from > 6400 :
            print("Recing packet header check fail!!!")
            return False
        else:
            return id_send_from    
        
        
    def rip_check_entry(self, entry):
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
        return True    
    
    def init_timer(self,dst_id):
        self.table[dst_id][2] = False
        self.table[dst_id][3].cancel()
        self.table[dst_id][4].cancel()
        self.table[dst_id][3] = self.start_time_out(dst_id)
        self.table[dst_id][4] = threading.Timer(self.garbage_time, self.delet_router, (dst_id,))
       
        
    def recive_packet(self, packet):
        """process recived packet"""
        #check hearder and entry
        len_packet = len(packet)
        neb_id = self.rip_check_header(packet)
        if not neb_id: #header check fail
            print("Droped the packet")
            return
        for entry_start_index in range(4,len_packet,20): #every entry has 20byts
            if not self.rip_check_entry(packet[entry_start_index:entry_start_index+20]):
                index_entry = (len_packet - 4) // 20
                print(f"wrong entry for index_entry: {index_entry} format-----------------")
                print("Droped the packet")
                return         
        #end of check the packet
        
        #if table dun have neb in table 
        if self.table.get(neb_id) == None:
            cost,_ = self.neighbours.get(neb_id)
            self.table[neb_id] = [cost, neb_id, False, self.start_time_out(neb_id), threading.Timer(self.garbage_time, self.delet_router, (neb_id,))]
        #else reinitize timer of neb
        else:
            self.init_timer(neb_id)
        #if only recive header so stop
        if len_packet == 4:
            return
        #end for neb processing 
        
        #start for non_neb processing
        for entry_start_index in range(4,len_packet,20):
            index_entry = (len_packet - 4) // 20
            self.process_entry(packet[entry_start_index:entry_start_index+20],neb_id)
            
        self.print_routing_table()
    
    
    def process_entry(self, entry, neb_id):
        """NEED IMP LATER FOR CHANGE TABLE when recive cost 16"""
    
        #router_id
        router_id = (int(entry[6] & 0xFF)) + int((entry[7] << 8))    
        #metric
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
                        self.set_garbage_timer(router_id) 
                else:
                    #cost dun change but not 16
                    if total_cost != 16:
                        self.init_timer(router_id)
                
                
            else: #if next hop not from packet send from and it cost less
                if total_cost < self.table.get(router_id)[0]:
                    self.table[router_id][3].cancel()
                    self.table[router_id][4].cancel()
                    self.table[router_id] = [total_cost, neb_id, False, self.start_time_out(router_id),threading.Timer(self.garbage_time, self.delet_router,(router_id,))]
            
        elif self.table.get(router_id) == None and total_cost != 16:
            self.table[router_id] = [total_cost, neb_id, False, self.start_time_out(router_id),threading.Timer(self.garbage_time, self.delet_router,(router_id,))]
        
            
        #else do onthing
        
        
    def print_routing_table(self):
        """ Prints the routing table's current condition."""
        print("\n")
        print(" ___________________________________(Routing Table: Router {})______________________________________".format(self.self_id))
        print("|___________________________________________________________________________________________________|")
        print("| Router ID | Port | Cost |                Timeout             |           Garbage Timer            |")
        print("|-----------|------|------|------------------------------------|------------------------------------|")
        print("|     {0}     | {1} |  {2}   |   {3}       {4}".format(self.self_id, ' - ', 0, 0, 0))
        
        for router_id, keys in self.table.items():
            metric = keys[0]
            next_hop = keys[1]
            time_out = keys[3]
            garbage_time = keys[4]
            print("|     {0}     | {1} |  {2}   |   {3}       {4}".format(router_id, next_hop, metric, 0, 0)) 

        print("|___________________________________________________________________________________________________|\n")
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
