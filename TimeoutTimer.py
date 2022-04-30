
import time  
from threading import Timer  
from RIP_CLASS import*





class TimeoutTimer():  
    
    def run(self):  
        global TIMEOUT
        
            TIMEOUT = TIMEOUT - self.interval
            print_routing_table(TIMEOUT)



def start_timeout(self, router_id):
    interval = 3 # or set interval randomly
    global TIMEOUT
    timer = TimeoutTimer(interval) 
    timer.start() #recalling run  
    print('Router timeout countdown started.') 
    print_routing_table(TIMEOUT)
    time.sleep(30) #It gets suspended for the given number of seconds  
    print('Router has timed out')  
    end_timeout(router_id)    
    TIMEOUT = 30


def main():
    start_timeout()
    
main()
        

