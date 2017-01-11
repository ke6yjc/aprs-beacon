#! /usr/bin/python
#-*- coding: utf-8 -*-

## Copyright 2017 Ted G. Freitas KE6YJC <ted.freitas@me.com>

## Original code forked via github from Philip Crump M0DNY <pdc1g09@ecs.soton.ac.uk>
## GPS control code copied from ukhas wiki: http://ukhas.org.uk/guides:ublox6

## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.

## Use : Beacon your location via IP to aprs2.net network

## Change Log

# 2017.01.08 - Added restart script counter as sometimes the program bombs out
# 2017.01.08 - Added speed to the display screen
# 2017.01.08 - Added Preflight checks... Always good to make sure things are in order
# 2017.01.08 - Added logging to beacon_log.txt
# 2017.01.10 - Fixed GPS GPTXT issue
# 2017.01.10 - Added MMDVM Last Heard TG injection into beacon comment

import os, sys, random
import gps, os, time, math, threading, re, serial, socket, datetime
import ConfigParser

config = ConfigParser.ConfigParser()
config.readfp(open(r'beacon.ini'))

### MYINFO
CALLSIGN = config.get('MYINFO', 'CALLSIGN')
MY_CALLSIGN = config.get('MYINFO', 'MY_CALLSIGN')

### APRS-IS
COMMENT = config.get('APRS-IS', 'COMMENT')
UDP = config.get('APRS-IS', 'UDP')
UDP_ADDRESS = config.get('APRS-IS', 'UDP_ADDRESS')
UDP_PORT = config.get('APRS-IS', 'UDP_PORT')
PASSWORD = config.get('APRS-IS', 'PASSWORD')

### BEACON
PATH = config.get('BEACON', 'PATH')
SYMBOL = config.get('BEACON', 'SYMBOL')
SYMBOL_TABLE = config.get('BEACON', 'SYMBOL_TABLE')
US_METRIC = config.get('BEACON', 'US_METRIC')
BEACON_PERIOD = config.get('BEACON', 'BEACON_PERIOD')
COMMENT_PERIOD = config.get('BEACON', 'COMMENT_PERIOD')
DYNAMIC_BEACON = config.get('BEACON', 'DYNAMIC_BEACON')
BEACON_SPEED_1 = config.get('BEACON', 'BEACON_SPEED_1')
BEACON_RATE_1 = config.get('BEACON', 'BEACON_RATE_1')
BEACON_SPEED_2 = config.get('BEACON', 'BEACON_SPEED_2')
BEACON_SPEED_2 = config.get('BEACON', 'BEACON_RATE_2')
BEACON_LASTHEARD = config.get('BEACON', 'BEACON_LASTHEARD')
MMDVM_LOGS_PATH = config.get('BEACON', 'MMDVM_LOGS_PATH')

### Restart
RESTART_COUNTER = config.get('RESTART', 'RESTART_COUNTER')

### Debug
DEBUG = config.get('DEBUGGING', 'DEBUG')
DEBUG = True
### GPS
GPS_PORT = config.get('GPS_SETTINGS', 'GPS_PORT')
GPS_PORT_SPEED = config.get('GPS_SETTINGS', 'GPS_PORT_SPEED')

### Logging
LOG_PATH = config.get('LOGGING', 'LOG_PATH')

### Misc.
TIMESTAMP = config.get('MISC', 'TIMESTAMP')
ALTITUDE = config.get('MISC', 'ALTITUDE')
APRX = config.get('MISC', 'APRX')
APRX_PATH = config.get('MISC', 'APRX_PATH')
REAL_COMMENT_PERIOD = config.get('MISC', 'REAL_COMMENT_PERIOD')

### END OF CONFIG ###

# Setup Logging
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# create a file handler
handler = logging.FileHandler('beacon_log.txt') # FILE THAT WILL HOLD THE LOGS
handler.setLevel(logging.INFO)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)

## Preflight Check
print 'Preflight check...'
if CALLSIGN=='CHANGE ME': print 'You need to change the callsign', logger.error('Default Callsign detected, please update'), quit()
if PASSWORD=='123456': print 'You need to change your password', logger.error('Default Password detected, please update'), quit()
if BEACON_PERIOD==30: print 'NOTICE: You are running the default Beacon Rate of 30 minutes, you might want to adjust this', logger.info('Default Beacon Rate of 30 minutes will be used')
print 'Preflight looks good! All settings are a go, lets launch the main program...'
time.sleep(3)
os.system('clear')

# Restart program
def restart_program():
   print 'Restarting Program...'
   logger.error('We were told to restart... Be right back...')
   python = sys.executable
   os.execl(python, python, * sys.argv)

# Function to encode (shorten) the lat,lon values in the packets
def latlon_encode(value):
   div1 = math.floor(value/math.pow(91,3))
   remainder1 = math.fmod(value, math.pow(91,3))
   div2 = math.floor(remainder1/math.pow(91,2))
   remainder2 = math.fmod(remainder1, math.pow(91,2))
   div3 = math.floor(remainder2/91)
   remainder3 = math.fmod(remainder2, 91)
   return chr(math.trunc(div1+33)) + chr(math.trunc(div2+33)) + chr(math.trunc(div3+33)) + chr(math.trunc(remainder3+33))

# Thread that keeps a connection to gpsd, holds current GPS state dictionary
class GpsPoller(threading.Thread):
    
    def __init__(self):
       threading.Thread.__init__(self)
       self.ser = serial.Serial(GPS_PORT, GPS_PORT_SPEED, timeout=1)
       self.ser.write("$PUBX,40,GLL,0,0,0,0*5C\r\n");
       self.ser.write("$PUBX,40,GGA,0,0,0,0*5A\r\n");
       self.ser.write("$PUBX,40,GSA,0,0,0,0*4E\r\n");
       self.ser.write("$PUBX,40,RMC,0,0,0,0*47\r\n");
       self.ser.write("$PUBX,40,GSV,0,0,0,0*59\r\n");
       self.ser.write("$PUBX,40,VTG,0,0,0,0*5E\r\n");
       self.ser.write("$PUBX,41,TXT,0,0,0,0*67\r\n"); # disable GPTXT
       ## TODO: Set Nav Mode airborne 1G --------------------------- TODO
       ## Clear buffer
       dummy = self.ser.readline()
       self.current_value = None
       self.stopped = False
       self.restart_counter = RESTART_COUNTER
       self.gps_error_count = 0
       self.fix = 'GPS Starting'
       self.sats = 'GPS Starting'
       time.sleep(0.5)
       

    def stop(self): # Stop the thread at the next opportunity
        self.stopped = True

    def get_current_value(self): # Return GPS state dictionary
        return self.current_value

    def gps_error(self):
        if RESTART_COUNTER > 0:
            if self.gps_error_count >= RESTART_COUNTER: 
                logger.error('Restart Counter reacheched... Be right back...')
                restart_program()
        self.fix = 'GPS ERROR'
        time.sleep(1)
        self.ser.flush()
        #self.ser.write("$PUBX,00*33\n");
        line = self.ser.readline()
        self.gps_error_count +=1
        #print "Missing GPS Data, retrying in 1 seconds..."
        if DEBUG==True:
            logger.error('No PUBX line detected from GPS.')
            print 'Error count: ', self.gps_error_count
            print "No PUBX line detected from GPS, retrying in 1 seconds..."


    def get_restart_counter(self):
        return self.restart_counter

    def get_gps_error_count(self):
        return self.gps_error_count

    def run(self):
        try:
            while not self.stopped:
		self.ser.flush()
		time.sleep(0.2)
                self.ser.write("$PUBX,00*33\n");
                line = self.ser.readline()
                try:
                    if not line.startswith("$PUBX"): # while we don't have a sentence.
			if DEBUG==True:
			    logger.error('Bad GPS Response: ' + line)
			    print 'Bad Respnse: ', line
                        self.gps_error()
                    else:
                        #print "GpsPoller Debug line: " + str(line)
                        self.full_string = line # used for debugging
                        fields = line.split(",")
                        #time = int(round(float(fields[2])))
                        #self.time_hour=(time/10000);
                        #self.time_minute=((time-(time_hour*10000))/100);
                        #self.time_second=(time-(time_hour*10000)-(time_minute*100));
                        #print str(self.time_hour) + ":" + str(self.time_minute) + ":" + str(self.time_second)
                        lat_minutes=int(math.floor(float(fields[3])/100))
                        lat_seconds=float(fields[3])-(lat_minutes*100)
                        self.gps_lat=lat_minutes+(lat_seconds/60.0)
                        if(fields[4]=='S'):
                            self.gps_lat = -self.gps_lat
                        #print "Latitude: " + str(self.gps_lat)
                        lon_minutes=int(math.floor(float(fields[5])/100))
                        lon_seconds=float(fields[5])-(lon_minutes*100)
                        self.gps_lon=lon_minutes+(lon_seconds/60.0)
                        if(fields[6]=='W'):
                            self.gps_lon = -self.gps_lon
                        #print "Lontitude: " + str(self.gps_lon)
                        self.altitude = float(fields[7]) # m
                        self.fix = fields[8] # "G3" = 3D fix
                        self.hacc = float(fields[9]) # m
                        self.vacc = float(fields[10]) # m
                        self.speed = float(fields[11]) # km/h
			#self.speed = random.randint(5,99) # Random speed testing
			#print 'UK Speed: ' + str(self.speed)
			if US_METRIC==True:
			    self.speed = round((self.speed*0.621371),2) # Convert for MPH
			#print 'MPH Speed : ' + str(self.speed)
                        self.heading = float(fields[12]) # degrees
                        self.climb = -float(fields[13]) # m/s
                        self.sats = int(fields[18])
                        if (abs(self.speed)<2):
                            self.speed = 0
                except ValueError:
                    print "Invalid String"
        except StopIteration:
            pass

# Main beacon thread, gets position from GpsPoller
class Beaconer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        logger.info('Log Opened.')
        self.sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM ) #Open UDP socket
        self.status = "Starting"
        self.stopped = False
        self.no_gps_timer = 0
        self.beacon_timer = 0
        self.comment_timer = 0
        self.last_beacon = '' # DEBUG
        self.beacon_period = BEACON_PERIOD*60 # convert to seconds
        self.comment_period = REAL_COMMENT_PERIOD*60 # convert to seconds
        #self.restart_counter = RESTART_COUNTER
        #self.gps_error_count = 0
        self.full_string = 'Starting'

    def stop(self): # Stop the thread at the next opportunity
        self.stopped = True
        logger.info('Log Closed')
        #logfile.write(sttime + 'Log Closed.\n')
        #logfile.flush()
        #logfile.close()
    
    def update_position(self):
        ## Updates this thread's variables from the poller thread
        self.fix = gpsp.fix
        if(gpsp.fix=='G3' or gpsp.fix=='G2' or gpsp.fix=='D3' or gpsp.fix=='D2'):
        	self.lat = gpsp.gps_lat
        	self.lon = gpsp.gps_lon
        	self.alt = gpsp.altitude
        	self.hacc = gpsp.hacc
        	self.speed = gpsp.speed
        	self.heading = gpsp.heading
        	self.sats = gpsp.sats
        	self.full_string = gpsp.full_string
        	self.update_beacon_interval() # Update Beacon Rate if enabled DYNAMIC_BEACON
    
    def update_beacon_interval(self):
        if DYNAMIC_BEACON==True:
            if gpsp.speed >= BEACON_SPEED_2:
                self.beacon_period = BEACON_RATE_2*60
            if gpsp.speed >= BEACON_SPEED_1 and gpsp.speed <= BEACON_SPEED_2:
                self.beacon_period = BEACON_RATE_1*60
        else:
            self.beacon_period = BEACON_PERIOD*60 # convert to seconds

    def get_lastheard(self):
	self.last_tg = "Not Active"
	#cs = CALLSIGN.split('-')
	#self.callsign = cs[0].rstrip()
	#return(self.callsign[0].rstrip())
	#self.mmdvm_logs_path = MMDMV_LOGS_PATH
	for filename in os.listdir(MMDVM_LOGS_PATH):
        	for line in reversed(open(MMDVM_LOGS_PATH+filename).readlines()):
                	if "from "+str(MY_CALLSIGN) in line:
                        	tg = line.split(' to ')
       	                	return(tg[1].rstrip())
				#self.lastheard = tg[1]
               	        	break
    
    def get_last_beacon(self): # Provides a timer since last beacon sent
        return self.beacon_timer
        
    def get_last_comment(self): # Provides a timer since last comment sent
        return self.comment_timer
        
    def get_last_fix(self): # Provides a timer since the last known 3D fix
        return self.no_gps_timer
    
    def get_fix(self):
        return self.fix
    
    def get_lat(self):
        return self.lat
    
    def get_lon(self):
        return self.lon
    
    def get_speed(self):
         return self.speed
    
    def get_debug(self):
        return self.full_string.rstrip()
        
    def get_beacon_period(self): # Returns the beacon interval in seconds
        return self.beacon_period
        
    def get_comment_period(self): # Returns the comment interval in seconds
        return self.comment_period
        
    def get_beacon_debug(self): # Returns last aprs string sent 
       return self.last_beacon

    def get_datetime(self,str_epoc): # clea up the time from epoc
	self.str_datetime = datetime.datetime.fromtimestamp(str_epoc).strftime('%H:%M:%S %m-%d-%Y')
	return self.str_datetime
        
    def runbeacon(self):
        if APRX==True: # APRX - Always send comment
           beacon_string = self.short_beacon()+COMMENT
           self.comment_timer = time.time()
        elif math.trunc(time.time() - self.comment_timer)>=self.comment_period:
           if BEACON_LASTHEARD==True:
              beacon_string = self.short_beacon()+COMMENT+" | Sats: "+str(self.sats)+" | LH: "+str(shout.get_lastheard())
           else:
              beacon_string = self.short_beacon()+COMMENT+" | Sats: "+str(self.sats)
           self.comment_timer = time.time()
        else:
           beacon_string = self.short_beacon()
        self.last_beacon = beacon_string
        if APRX==True:
           self.save_beacon(beacon_string)
        elif UDP:
            self.udp_beacon(beacon_string)
        else:
           self.send_beacon(beacon_string)
        self.beacon_timer = time.time()
        
    def send_beacon(self,aprs_string): # Sends beacon using system 'beacon'
        system_string = "/usr/sbin/beacon -c "+CALLSIGN+" -d '"+PATH+"' -s sm0 "+re.escape(aprs_string)
        os.system(system_string)
        #logfile.write(time.strftime("%H:%M:%S") + ' ' + time.strftime("%m/%d/%Y") + ' - ' + 'Beacon sent: ', aprs_string)
    
    def udp_beacon(self,aprs_string): # Sends beacon using system 'beacon'
        udp_string = "user " + CALLSIGN + " pass " + PASSWORD + " vers M0DNY-PiBeacon 0.1\n"
        udp_string += CALLSIGN + ">APRS,TCPIP*:" + aprs_string
        self.sock.sendto( udp_string, (UDP_ADDRESS, UDP_PORT))
        logger.info('UDP Beacon sent: ' + aprs_string)
    
    def save_beacon(self,aprs_string): # Used for aprx, saves to file
        fout = open(APRX_PATH, "w")
        fout.truncate()
        fout.write(aprs_string)
        fout.close()
        #logfile.write('Beacon saved: ', aprs_string)
    
    def short_beacon(self): # Compressed beacon format
        if TIMESTAMP==True:
           aprs_prefix = '/' # According to the APRS spec (Position, timestamp, no messaging)
        else:
           aprs_prefix = '!' # According to the APRS spec (Position, no timestamp, no messaging)
        ## Sort out time strings
        #utctime = str(self.gps_status['time'])
        #day = utctime[8::10]
        #hour = utctime[11:13]
        #minute = utctime[14:16]
        #second = utctime[17:19]
        ## Sort out Latitude and Longitude
        lat_bytes = latlon_encode(380926*(90-self.lat))
        lon_bytes = latlon_encode(190463*(180+self.lon))
        short_packet_string = aprs_prefix + SYMBOL_TABLE
        if TIMESTAMP==True:
           short_packet_string += hour + minute + second + 'h'
        short_packet_string += lat_bytes + lon_bytes + SYMBOL
        if ALTITUDE==True:
           type_byte = chr(33+int('00110010',2)) # Set to GGA to enable altitude
           alt_value = math.log(math.trunc(self.alt*3.28))/math.log(1.002)
           alt_div = math.floor(alt_value/91)
           alt_remainder = math.fmod(math.trunc(alt_value), 91)
           alt_bytes = chr(33+math.trunc(alt_div)) + chr(33+math.trunc(alt_remainder))
           short_packet_string += alt_bytes + type_byte
        else:
           type_byte = chr(33+int('00111010',2)) # Set to RMC to enable course/speed
           course_byte = chr(33+math.trunc(self.heading/4))
           speed_byte = chr(33+math.trunc(math.log((self.speed*1.9438)+1)/math.log(1.08)))
           short_packet_string += course_byte + speed_byte + type_byte
        return short_packet_string
    
    def run(self):
        try:
            time.sleep(0.5) # let's pause for a few seconds to get the data
            while not self.stopped:
            	self.update_position()
                if self.fix=='G3' or self.fix=='G2' or self.fix=='D2' or self.fix=='D2': # Do we have a GPS fix?
                    self.no_gps_timer = math.trunc(time.time())
                    if APRX==True:
                        self.runbeacon()
                    elif math.trunc(time.time() - self.beacon_timer)>=self.beacon_period:
                        self.runbeacon()
                    #else: # No GPS fix
                    #    if self.no_gps_timer==0: self.no_gps_timer = 0
                time.sleep(0.5)
        except StopIteration:
            pass

## Main foreground process, just draws to the screen, grabs info from Beaconer thread
if __name__ == "__main__":
   try:
      gpsp = GpsPoller()
      gpsp.start()
      shout = Beaconer()
      shout.start()
      print "Waiting for GPS..\n"
      time.sleep(2)
      while 1:
         os.system('clear') # Clear the screen
         # Now draw screen depending on GPS status
         if shout.get_fix()=='G3' or shout.get_fix()=='G2' or shout.get_fix()=='D3' or shout.get_fix()=='D2':
            print 'Got GPS Fix!'
            print 'Lat:   ', shout.get_lat()
            print 'Lon:   ', shout.get_lon()
	    print 'Speed: ', shout.get_speed()
            print 'LH:    ', shout.get_lastheard()
         elif shout.get_fix()=='Starting': # Beacon thread not yet initialised
            print 'Beacon starting up..'
         else:
	    print 'No fix.'
         print ''
         if shout.get_last_beacon()==0: # No beacon yet sent
            print 'No beacon sent yet.'
         else:
            if APRX==True:
               print APRX_PATH, ' updated ', math.trunc(time.time() - shout.get_last_beacon()), 'seconds ago.'
            else:
               print 'Beacon timer: ', math.trunc(time.time() - shout.get_last_beacon()), '/', shout.get_beacon_period(), ' seconds.'
         print ''
         print 'Current comment: ', COMMENT
         if shout.get_last_comment()==0: # No comment yet sent
            print 'No comment sent yet.'
         else:
            if APRX==False: ## Can I do this with '!APRS' ?
               print 'Comment timer: ', math.trunc((time.time() - shout.get_last_comment())/60), '/', shout.get_comment_period()/60, ' minutes.'
	 if RESTART_COUNTER > 0:
	       print ''
	       print 'Restart counter: ', gpsp.get_gps_error_count(), '/', gpsp.get_restart_counter()
         if DEBUG==True:
            #print shout.get_beacon_debug()
            #print shout.get_last_beacon()
	    print ''
	    print 'Debug is enabled...'
	    print ''
	    print 'GPS Debugging'
            print '---'
	    print 'Last GPS Info:     ', shout.get_debug()
	    print 'Last good GPS Fix: ', shout.get_datetime(shout.get_last_fix())
	    print 'GPS Fix:           ', gpsp.fix
	    print 'No. of Satelites:  ', gpsp.sats
	    print ''
	    print 'Beacon Information'
	    print '---'
	    print 'The time is:       ', shout.get_datetime(math.trunc(time.time()))
            print ''
	    print 'Last Beacon Time:  ', shout.get_datetime(math.trunc(shout.get_last_beacon()))
	    print 'Last Comment Time: ', shout.get_datetime(math.trunc(shout.get_last_comment()))
	    print ''
            print 'Next Beacon Time:  ', shout.get_datetime(math.trunc(shout.get_last_beacon() + shout.get_beacon_period()))
	    print 'Next Comment Time: ', shout.get_datetime(math.trunc(shout.get_last_comment() + shout.get_comment_period()))
         time.sleep(1) # Give the CPU some time to breathe
   except KeyboardInterrupt: # Catch Ctrl+C, stop both threads
      logger.info('Caught a Ctrl+C command, exiting...')
      shout.stop()
      gpsp.stop()
      pass

