"""Drive functions

The drive on the pulsar telescope is currently controlled via an http
server, with command strings sent via an ethernet cable to the
controller located on the telescope mount.

...

This sub-module contains the following classes:

1. drive()
   A module to control the driving of the pulsar telescope

...


"""
import urllib, ephem, time, math, logging, sys, os


# Details of Acre Road observatory
Acre_Road = ephem.Observer()
Acre_Road.long, Acre_Road.lat, Acre_Road.elev = "-4:18:25.93", "55:54:8.29",50
Acre_Road.pressure = 0 #remove refraction



class Drive():
    """
    A class to handle all of the interactions between software and the drive hardware on the telescope.

    """

    simulate = 0
    url = ""

    def __init__(self,
                 debug=0,
                 simulate=0,
                 logfile=None,
                 observatory=Acre_Road
             ):
            
        # Set up debugging and simulation
        self.logger = logging.getLogger('PT.Drive')
        self.switch_simulate(simulate)
        # Configuration information
        # this should probably be moved to its own file!
        self.url = "http://192.168.0.6/"
        self.east_stop = -110 # mechanically is -117.0
        self.west_stop = 110  # mechanically is 112
        # Load in the gray codes
        grayfile = os.path.join(os.path.dirname(__file__), 'graycode.txt')
        graycodefile = open(grayfile, 'r')
        grayindex = graycodefile.readlines()
        graycodefile.close()

        
    def sendstr(self, stringlist):
        """
        Send the string command s to the contoller.  stringlist is a list of commands
        so could be something like ['T00'] or ['A01','A02','A09'].

        
        """
        for s in stringlist:
            # Form the command url
            command = "{0}?{1}".format(self.url,s)
            
            # If the module has de-bugging enabled the command will be printed
            self.logger.info("{0}".format(command))
            
            # if simulation is turned on it is not forwarded to the telescope.
            if self.simulate:
                return 0
            
            try:
                f = urllib.urlopen(command)
                f.close()
            except IOError:
                self.logger.error("I/O error opening web page to send command to controller")
                return 1

        return 0
        #
        

    def switch_simulate(self, status):
        """
        Turn simulation mode on or off. In simulation mode commands are not sent to the controller.
        """
        if status==0:
            self.simulate=0
        else:
            self.simulate=1
        #
                    
                
    def switch_debug(self, status, logfile=None):
        """
        Turn on debugging and information statements, including
        outputting the url commands sent to the controller.

        """
        if logfile==None:
            logfile=sys.stderr

        fh = logging.FileHandler(logfile)
        formatter = logging.Formatter('[%(asctime)s] %(name)s [%(levelname)s] %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        if status==0:
            self.logger.setLevel(logging.WARNING)
            #logging.basicConfig(stream=logfile, level=logging.WARNING)
        else:
            self.logger.setLevel(logging.DEBUG)
            #logging.basicConfig(stream=logfile, level=logging.DEBUG)
            self.logger.info("Debug logging enabled")
    

    def enable(self):
        """
        Enable the output of the servo controller.  The telescope will start
        driving if a non-zero speed has been set (see set_speed)
        """
        self.logger.info("Drive activated")
        return self.sendstr(['A09']) #set pin 9 high

        
    def disable(self):
        """
        Disable the output of the servo controller.  The telescope will stop
        driving. Alway disable the drive when not intending to drive to prevent
        creep and to remove any residual current in the motor.
        """
        self.logger.info("Drive deactivated")
        return self.sendstr(['B09']) #set pin 9 low
        
    def set_speed(self, v):
        """
        Setup the controller to drive the telescope at a speed v ( any value -1 to 1).
        A speed of 1 drives clockwise (ahead) at the maximum rate, -0.5 drives
        backwards at half speed etc... The telescope will only start driving once
        enable_drive is set.  The speed is set by the 8-bit DAC outout voltage.
        """

        if v>1.0:
            v=1
            self.logger.warning("The speed has been set to 1.")
        elif v<-1.0:
            v = -1
            self.logger.warning("The speed has been set to -1.")
            
        
        speed = int((1.0-v)/2.0*255) # put in the range 0-255
        vlist = []
        for i in range(7,-1,-1):
            if speed & 2**i:
                vlist.append('B0'+str(i+1))
            else:
                vlist.append('A0'+str(i+1))
        # disable DAC inputs (pin 10 is connected to WR on the DAC. When this input
        # is low, data is read.  When high the analogue voltage is fixed.)
        self.sendstr(['B10'])
        self.sendstr(vlist)
        self.sendstr(['A10','B10']) # enable/disable DAC inputs
        self.logger.info("The speed has been set to {0}".format(speed))
        return 0

    def read_position(self):
        """
        The Netiom card serves files uploaded to it using the serial interface.
        If the filename extension is ".cgi", then %xx strings are replaced with
        values.  The encoder uses gray codes, indexed by graycode.txt
        """

        command ="{0}digitalinputs.cgi".format(self.url)
        self.logger.debug(command)
        
        if self.simulate:
            self.logger.warning("The module cannot read positions in simulation mode.")
            return 0

        try:
            g = urllib.urlopen(command)
            status_str = g.readline()
            g.close()
        except IOError:
            self.logger.error("I/O error reading the encoder.")
            status_str = '0000000000000'
        # The netiom reports the lowest bit (bit 1) first, so we have to
        # reverse the string
        # now turn it into a graycode base 10 integer
        gray = int(status_str[::-1], base=2)
        # ... and find the content of this element in grayindex (removing the
        # trailing ".0\n".  Also, convert to degrees
        position = self.grayindex[gray][:-3]
        pos_degree = int(float(position))*360.0/8192.0
        if pos_degree >180.0:
            pos_degree -= 360.0

        self.logger.info("Position is {0}".format(pos_degree))
        return pos_degree

    def motor(self):
        """
        Reports on whether the motor is running.
        """

        command = "{0}digitaloutputs.cgi".format(url)
        self.logger.debug(command)
        
        if self.simulate:
            self.logger.warning("The module cannot report on the motor in simulation mode.")
            return 0
        try:
            g = urllib.urlopen(command)
            status_str = g.readline()
            status_str = g.readline()
            g.close()
        except IOError:
            self.logger.error('I/O error reading digitalinputs.cgi to find motor status')
            status_str = '0000000000'
        if status_str[0]=='1':
            status = 'on'
        else:
            status='off'
            return status

    def diff(self, hh):
        """
        Calculate the difference between the current position and the given hour angle
        """
        pos = self.read_position()
        diff = hh - pos
        if abs(diff)>0.0001:
            sign = diff/abs(diff)
        else:
            sign = 1

        diff = abs(diff)
        speed = sign*(diff/360)**(0.25)    
        return diff, speed    

    def slew(self, hh):
        """
        Slews the telescope to the requested hour angle.
        """

        diff,speed = self.diff(hh)
        if diff>0.2: self.enable()
        while diff>0.2:
            speed = sign*(diff/360)**(0.25)
            self.set_speed(speed)
            diff,speed = self.diff(hh)
        self.disable()
        
    def park(self):
        """
        Moves the telescope into a parking position, pointing along the meridian.
        """
        self.slew(0)


class Track():
    def __init__(drive, observatory, object):

        # Observatory
        self.observatory = observatory
        
    def hour_angle(self, source):
        observatory.date = ephem.now()
        source.compute(observatory)
        hh = (observatory.sidereal_time() - source.ra)/math.pi*180.0
        return hh

    