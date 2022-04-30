
                        COSC364 (RIP Assignment)
                Authors: Haider Saeed (msa280), Drogo Shi
                            Date: 07/03/2022


File Definition: README file for the project.

This is the RIPV2 Routing Protocol program instructions. You have a list of 7 routers you can run.
The router configuration filenames are available in the 'Routers' folder. 
To start a router complete the following steps:



1) Open terminal in Linux and change directory to project workspace. 
   You can use the following command to change directory:
   
   labbox>cd "project folder name"


2) Once directory is changed, run the following command to start up a router:

   python3 RIPV2_Daemon.py Routers/router"X".txt 

   where "X" is any number between 1 and 7 inclusive. 

3) Once done, you will see the routing table of the router being printed. 
   This means that the router is alive.


4) To close the router, simply close the terminal.


