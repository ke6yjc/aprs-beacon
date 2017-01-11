# APRS-Beacon

This is a starter project for aprs-beaconing predominantly on a DVMega hotspot's running on a Raspberry PI. It never any sense to me why I could not beacon my location from my hotspot. So I finally decided to go do some poking around and found some starter code on github that was over a year old. I sat down and changed a few things (to the best of my abilities, I'm NOT a programmer by any means) and this is what I came up with. Please try not to beat me too hard as I'm still learning, but I'm sure with time I'll get better.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

* Python 2.x installed
* PySerial (for connecting to the GPS)
* python-gps
* git
* screen
* GPS Unit - Tested with Stratux Uk-162 -> (https://www.amazon.com/gp/product/B01EROIUEW)

Always make sure your pi is up-to-date!!

```
$ sudo apt-get update
$ sudo apt-get upgrade
```

Install some of those pesky prerequisites...

```
sudo apt-get install git screen python-gps
```

## Installing

The installation is pretty simple, just change to the /opt directory and clone the project. Everything should be installed into a folder named aprs-beacon.

1. Clone the aprs-beacon project onto your system

```
$ cd /opt
$ sudo git clone https://github.com/ke6yjc/aprs-beacon
```

2. Make sure beacon.py is executable

```
$ sudo chmod +x /opt/aprs-beacon/beacon.py
```

Yup it's that simple...

### Updating the script so it will start

I build in failsafe's so that if the default config is used the script will just blow quit(). All changes are made directly to the script. I will be breaking this apart in the future, but for now you just have to edit the entire script.

```
$ sudo nano /opt/aprs-beacon/beacon.py
```

### Mandatory Settings

1. Update your callsign

```
## Callsign of beacon <== CHANGE THIS
CALLSIGN = 'CHANGE ME'
```

2. Update your iGate password

```
## APRS Password <== CHANGE THIS
PASSWORD = "123456"
```

### Optional Settings

Update the Beacon Rate

One of the features I added was the dynamic beacon feature. This will allow your beacon interval to change based on speed. If your speed is below BEACON_SPEED_1 the system will use the BEACON_PERIOD value which defaults to 30 minutes. If your speed goes over BEACON_SPEED_1 then BEACON_RATE_1 will be used for as your next beacon interval. If your speed => BEACON_SPEED_2 then BEACON_RATE_2 will be used. COMMENT_PERIOD is how often your COMMENT will be sent. You will probably also want to update this to personalize it.

NOTE: If the DYNAMIC_BEACON = False (default) the system will use BEACON_PERIOD for it's beacon interval

```
## Beacon Interval - Control Beacon rate on speed
DYNAMIC_BEACON = False

# If speed is above BEACON_SPEED_1 then adjust the beacon interval to BEACON_RATE_1 in minutes
BEACON_SPEED_1 = 10
BEACON_RATE_1 = 2

# If speed is above BEACON_SPEED_2 then adjust the beacon interval to BEACON_RATE_2 in minutes
BEACON_SPEED_2 = 40
BEACON_RATE_2 = 1

# Default beacon rate
COMMENT_PERIOD = 15 # Period of sending comment in minutes

BEACON_PERIOD = 1 # Period of sending position beacon in minutes
```

GPS Settings

```
## GPS Port <== You might need to change this too should work though
GPS_PORT = "/dev/ttyACM0"

## GPS Port Speed
GPS_PORT_SPEED = 9600
```

## Misc. Stuff

If you want this to run as a service I've included pre-configured script files in the /service folder for you. If you did not use the default install directory you might need to tweak them a bit

###

Setup aprs-beacon as a service

1. Copy aprs-beacon files to /lib/systemd/system

```
$ sudo cp /opt/aprs-beacon/service/aprs-beacon.service /lib/systemd/system
$ sudo cp /opt/aprs-beacon/service/aprs-beacon.timer /lib/systemd/system
```

2. Enable the aprs-beacon service

```
$ sudo systemctl enable aprs-beacon.timer
```

3. Start the aprs-beacon service
```
$ sudo systemctl start aprs-beacon
```

## See what's going on

The aprs-beacon service runs under a "virtual" screen in the background. This way you can see what is going on at any time. Use the command below to re-attach to the session. Remember 

Command to attach to aprs-beacon service: 

```
sudo screen -r gps
```

Command to detatch from the aprs-beacon service:

* Remember to DETATCH from the service, DO NOT PRESS CTRL+C or the service will stop!!!!

```
Press CTRL+a, then press the letter 'd' to detatch
```

This will leave the service running in the background

## Authors

* **Ted G. Freitas / KE6YJC** - *Updated work* - [ke6yjc](https://github.com/ke6yjc)
* **Phil Crump / M0DNY** - *Initial work* - [philcrump](https://github.com/philcrump)


## License

This project is licensed under the GNU GENERAL PUBLIC LICENSE - see the [LICENSE.md](LICENSE.md) file for details
