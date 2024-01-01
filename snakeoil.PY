#!/usr/bin/python
# snakeoil.py
# Chris X Edwards <snakeoil@xed.ch>
# Snake Oil is a Python library for interfacing with a TORCS
# race car simulator which has been patched with the server
# extentions used in the Simulated Car Racing competitions.
# http://scr.geccocompetitions.com/
#
# To use it, you must import it and create a "drive()" function.
# This will take care of option handling and server connecting, etc.
# To see how to write your own client do something like this which is
# a complete working client:
# /-----------------------------------------------\
# |#!/usr/bin/python                              |
# |import snakeoil                                |
# |if __name__ == "__main__":                     |
# |    C= snakeoil.Client()                       |
# |    for step in xrange(C.maxSteps,0,-1):       |
# |        C.get_servers_input()                  |
# |        snakeoil.drive_example(C)              |
# |        C.respond_to_server()                  |
# |    C.shutdown()                               |
# \-----------------------------------------------/
# This should then be a full featured client. The next step is to
# replace 'snakeoil.drive_example()' with your own. There is a
# dictionary which holds various option values (see `default_options`
# variable for all the details) but you probably only need a few
# things from it. Mainly the `trackname` and `stage` are important
# when developing a strategic bot. 
#
# This dictionary also contains a ServerState object
# (key=S) and a DriverAction object (key=R for response). This allows
# you to get at all the information sent by the server and to easily
# formulate your reply. These objects contain a member dictionary "d"
# (for data dictionary) which contain key value pairs based on the
# server's syntax. Therefore, you can read the following:
#    angle, curLapTime, damage, distFromStart, distRaced, focus,
#    fuel, gear, lastLapTime, opponents, racePos, rpm,
#    speedX, speedY, speedZ, track, trackPos, wheelSpinVel, z
# The syntax specifically would be something like:
#    X= o[S.d['tracPos']]
# And you can set the following:
#    accel, brake, clutch, gear, steer, focus, meta 
# The syntax is:  
#     o[R.d['steer']]= X
# Note that it is 'steer' and not 'steering' as described in the manual!
# All values should be sensible for their type, including lists being lists.
# See the SCR manual or http://xed.ch/help/torcs.html for details.
#
# If you just run the snakeoil.py base library itself it will implement a
# serviceable client with a demonstration drive function that is
# sufficient for getting around most tracks.
# Try `snakeoil.py --help` to get started.

import socket 
import sys
import getopt
import PID
import json
import math
PI= 3.14159265359

# Initialize help messages
ophelp=  'Options:\n'
ophelp+= ' --host, -H <host>    TORCS server host. [localhost]\n'
ophelp+= ' --port, -p <port>    TORCS port. [3001]\n'
ophelp+= ' --id, -i <id>        ID for server. [SCR]\n'
ophelp+= ' --steps, -m <#>      Maximum simulation steps. 1 sec ~ 50 steps. [100000]\n'
ophelp+= ' --episodes, -e <#>   Maximum learning episodes. [1]\n'
ophelp+= ' --track, -t <track>  Your name for this track. Used for learning. [unknown]\n'
ophelp+= ' --stage, -s <#>      0=warm up, 1=qualifying, 2=race, 3=unknown. [3]\n'
ophelp+= ' --debug, -d          Output full telemetry.\n'
ophelp+= ' --help, -h           Show this help.\n'
ophelp+= ' --version, -v        Show current version.'
usage= 'Usage: %s [ophelp [optargs]] \n' % sys.argv[0]
usage= usage + ophelp
version= "20130505-2"
maxSpeedDist = 70
maxSpeed = 250
class Client():
    def __init__(self,H=None,p=None,i=None,e=None,t=None,s=None,d=None):
        # If you don't like the option defaults,  change them here.
        self.host= 'localhost'
        self.port= 3001
        self.sid= 'SCR'
        self.maxEpisodes=1
        self.trackname= 'unknown'
        self.stage= 3
        self.debug= False
        self.maxSteps= 100000  # 50steps/second
        self.parse_the_command_line()
        if H: self.host= H
        if p: self.port= p
        if i: self.sid= i
        if e: self.maxEpisodes= e
        if t: self.trackname= t
        if s: self.stage= s
        if d: self.debug= d
        self.S= ServerState()
        self.R= DriverAction()
        self.setup_connection()

    def setup_connection(self):
        # == Set Up UDP Socket ==
        try:
            self.so= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except socket.error:
            print ('Error: Could not create socket...')
            sys.exit(-1)
        # == Initialize Connection To Server ==
        self.so.settimeout(1)
        while True:
            a= "-90 -75 -60 -45 -30 -20 -15 -10 -5 0 5 10 15 20 30 45 60 75 90"
            initmsg='%s(init %s)' % (self.sid,a)
            initmsg= initmsg.encode('utf-8')

            try:
                self.so.sendto(initmsg, (self.host, self.port))
            except socket.error:
                sys.exit(-1)
            sockdata=bytes()
            try:
                sockdata,addr= self.so.recvfrom(1024)
            except socket.error:
                print( "Waiting for server............")
            if b'***identified***' in sockdata:
                print ("Client connected..............")
                break

    def parse_the_command_line(self):
        try:
            (opts, args) = getopt.getopt(sys.argv[1:], 'H:p:i:m:e:t:s:dhv',
                       ['host=','port=','id=','steps=',
                        'episodes=','track=','stage=',
                        'debug','help','version'])
        except getopt.error:
            print ('getopt error: %s\n%s' % (usage) )
            sys.exit(-1)
        try:
            for opt in opts:
                if opt[0] == '-h' or opt[0] == '--help':
                    print (usage)
                    sys.exit(0)
                if opt[0] == '-d' or opt[0] == '--debug':
                    self.debug= True
                if opt[0] == '-H' or opt[0] == '--host':
                    self.host= opt[1]
                if opt[0] == '-i' or opt[0] == '--id':
                    self.sid= opt[1]
                if opt[0] == '-t' or opt[0] == '--track':
                    self.trackname= opt[1]
                if opt[0] == '-s' or opt[0] == '--stage':
                    self.stage= opt[1]
                if opt[0] == '-p' or opt[0] == '--port':
                    self.port= int(opt[1])
                if opt[0] == '-e' or opt[0] == '--episodes':
                    self.maxEpisodes= int(opt[1])
                if opt[0] == '-m' or opt[0] == '--steps':
                    self.maxSteps= int(opt[1])
                if opt[0] == '-v' or opt[0] == '--version':
                    print ('%s %s' % (sys.argv[0], version) )
                    sys.exit(0)
        except ValueError:
            print ('Bad parameter \'%s\' for option %s: %s\n%s' % (
                                       opt[1], opt[0], usage))
            sys.exit(-1)
        if len(args) > 0:
            print ('Superflous input? %s\n%s' % (', '.join(args), usage) )
            sys.exit(-1)

    def get_servers_input(self):
        '''Server's input is stored in a ServerState object'''
        if not self.so: return
        sockdata= bytes()
        while True:
            try:
                # Receive server data 
                sockdata,addr= self.so.recvfrom(1024)
            except socket.error:
                print ("Waiting for data..............")
            if b'***identified***' in sockdata:
                print ("Client connected..............")
                continue
            elif b'***shutdown***' in sockdata:
                print ("Server has stopped the race. You were in %d place." % self.S.d['racePos'] )
                self.shutdown()
                return
            elif b'***restart***' in sockdata:
                # What do I do here?
                print ("Server has restarted the race.")
                # I haven't actually caught the server doing this.
                self.shutdown()
                return
            elif not sockdata: # Empty?
                continue       # Try again.
            else:
                self.S.parse_server_str(sockdata)
                if self.debug: print (self.S)
                break # Can now return from this function.

    def respond_to_server(self):
        if not self.so: return
        if self.debug: print (self.R)
        try:
            self.so.sendto(repr(self.R).encode('utf-8'), (self.host, self.port))
        except socket.error:
            print ("Error sending to server: %s Message %s" % (emsg[1],str(emsg[0])) )
            sys.exit(-1)

    def shutdown(self):
        if not self.so: return
        print ("Race terminated or %d steps elapsed. Shutting down." % self.maxSteps  )
        self.so.close()
        self.so= None
        #sys.exit() # No need for this really.

class ServerState():
    'What the server is reporting right now.'
    def __init__(self):
        self.servstr= str()
        self.d= dict()

    def parse_server_str(self, server_string):
        'parse the server string'
        self.servstr= server_string.strip()[:-1]
        sslisted= self.servstr.decode('utf-8').strip().lstrip('(').rstrip(')').split(')(')
        for i in sslisted:
            w= i.split(' ')
            self.d[w[0]]= destringify(w[1:])

    def __repr__(self):
        out= str()
        for k in sorted(self.d):
            strout= str(self.d[k])
            if type(self.d[k]) is list:
                strlist= [str(i) for i in self.d[k]]
                strout= ', '.join(strlist)
            out+= "%s: %s\n" % (k,strout)
        return out

class DriverAction():
    '''What the driver is intending to do (i.e. send to the server).
    Composes something like this for the server:
    (accel 1)(brake 0)(gear 1)(steer 0)(clutch 0)(focus 0)(meta 0) or
    (accel 1)(brake 0)(gear 1)(steer 0)(clutch 0)(focus -90 -45 0 45 90)(meta 0)'''
    def __init__(self):
       self.actionstr= str()
       # "d" is for data dictionary.
       self.d= { 'accel':0.2,
                   'brake':0,
                  'clutch':0,
                    'gear':1,
                   'steer':0,
                   'focus':[-90,-45,0,45,90],
                    'meta':0 
                    }
    def new_data(self , dic):
        self.d={ "accel" : dic['accel'],
               "brake" : dic['brake'],
            "clutch": dic['clutch'],
            "gear"  : dic['gear'],
            "steer" : dic['steer'],
            "focus" : dic['focus'],
            "meta"  : dic['meta']                            
            }
        
    def __repr__(self):
        out= str()
        for k in self.d:
            out+= '('+k+' '
            v= self.d[k]
            if not type(v) == list:
                out+= '%.3f' % v
            else:
                out+= ' '.join([str(x) for x in v])
            out+= ')'
        return out
        return out+'\n'

# == Misc Utility Functions
def destringify(s):
    '''makes a string into a value or a list of strings into a list of
    values (if possible)'''
    if not s: return s
    if type(s) is str:
        try:
            return float(s)
        except ValueError:
            print ("Could not find a value in %s" % s )
            return s
    elif type(s) is list:
        if len(s) < 2:
            return destringify(s[0])
        else:
            return [destringify(i) for i in s]

def clip(v,lo,hi):
    if v<lo: return lo
    elif v>hi: return hi
    else: return v


gearUp = [ 5000, 6000, 6000, 6500, 7000, 0 ]
gearDown = [0, 2500, 3000, 3000, 3500, 3500 ]

sin10 = 0.1736481777
cos10 = 0.984807753
Road_Width=20
targetSpeed = 300
targetAngle = 0
distance_from_center = 1
controllerofspeed = PID.PI_CONTROLLER(.5,.09,0,targetSpeed) #speedX
controllerofdistance = PID.PI_CONTROLLER(0.2,.002,.01,distance_from_center) #trackPos
def drive_example(c,cccc):

    #This is only an example. It will get around the track but the
    #correct thing to do is write your own `drive()` function.
    
    #create static variables
    if not hasattr(drive_example, "cur_time"):
        drive_example.cur_time = 0
    if not hasattr(drive_example, "prev_cur_time"):
        drive_example.prev_cur_time = -1


    S= c.S.d
    R= c.R.d

    #get current time
    drive_example.cur_time = S['curLapTime']

    if drive_example.prev_cur_time == -1:
        drive_example.prev_cur_time = drive_example.cur_time
        return   
    
    angle = S['angle']
    distance_from_edge = 0
    #get distance from edge
    if S['trackPos']>=0:     #left side
        distance_from_edge = abs(1-(S['trackPos']) )
    elif S['trackPos']<0:               #right side
        distance_from_edge = abs(-1+(S['trackPos']))
    #dt = drive_example.cur_time - drive_example.prev_cur_time
    dt = .01
    next_predicted_pos = distance_from_edge + ((S['speedX']*dt)*math.sin(angle)) 
    signal_pid_angle = controllerofdistance.output(next_predicted_pos,1,1.1)
    signal_pid_angle -=(S['trackPos']/Road_Width)+((S['track'][6]-S['track'][12])/(S['track'][9]*2))

    R['steer'] = clip(-signal_pid_angle,-1,1)
    if abs(R['steer'])>=.04 and S['speedX']>=100:
        R['clutch']=clip(R['clutch']+.001,0,1)
        R['brake']=clip(R['brake']+.0001,0,1)
        return
    elif S['speedX']>=150:
        R['clutch']=clip(R['clutch']+.001,0,1)
        R['brake']=0
    else:
        R['clutch']=0
        R['brake']=0

    signal_pid_speed=0
    if abs(S['trackPos'])<1:
        #change_refrance_speed(c)
        signal_pid_speed = controllerofspeed.output(S['speedX'],1,1.1)
        R['accel']=clip(R['accel']+signal_pid_speed,0,1)
    else:
        R['accel']=0.3
        print("out of road")


    '''if S['speedX']<50:
        R['gear']=1
    if S['speedX']>=50:
        R['gear']=2
    if S['speedX']>=80:
        R['gear']=3
    if S['speedX']>=110:
        R['gear']=4
    if S['speedX']>=130:
        R['gear']=5
    if S['speedX']>=160:
        R['gear']=6'''
    R['gear']=get_gear(c)
    clutching(c)

    #update prev time
    if drive_example.cur_time > drive_example.prev_cur_time:
        drive_example.prev_cur_time = drive_example.cur_time 
    else:
        drive_example.prev_cur_time = drive_example.cur_time - .022
    #print(signal_pid_angle, "   " , signal_pid_speed)
    return




def clutching(c):
    R= c.R.d
    if R['gear']<2:
        R['clutch']=.5
    else:
        R['clutch']-=.02
        R['clutch']=clip(R['clutch'],0,1)
    return


#calculate refrance speed
def change_refrance_speed(c):
    global targetSpeed
    S= c.S.d
    R_sensor = S['track'][10]
    L_sensor = S['track'][8]
    Zero_sensor = S['track'][9]
    if (Zero_sensor>maxSpeedDist) or (Zero_sensor >= L_sensor and Zero_sensor >= R_sensor):
        targetSpeed = maxSpeed
    else:
        if R_sensor >= L_sensor:
            h=Zero_sensor*sin10
            b=R_sensor - Zero_sensor*cos10
            sin_angle = (b*b)/(h*h+b*b)
            targetSpeed = maxSpeed * (Zero_sensor*sin_angle/maxSpeedDist)
        else:
            h=Zero_sensor*sin10
            b=L_sensor - Zero_sensor*cos10
            sin_angle = (b*b)/(h*h+b*b)
            targetSpeed = maxSpeed * (Zero_sensor*sin_angle/maxSpeedDist)

    return


def get_gear(c):
    global gearUp
    global gearDown
    S= c.S.d
    gear = int(S['gear'])
    rpm = int(S['rpm'])
    if gear<1:
        return 1
    
    if (gear<6) and (rpm >= gearUp[gear-1]):
        return gear + 1
    else:
        if (gear>1) and (rpm <= gearDown[gear-1]):
            return gear - 1
        else:
            return gear