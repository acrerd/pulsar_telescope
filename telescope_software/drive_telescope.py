# drive-telesope keeps the pulsar telesope tracking the Crab
#
from __future__ import division, print_function
import urllib, ephem, time, math
from visual import *
import wx

##bar = EasyDialogs.ProgressBar()
# for debugging offline
connection = False

#base address of the Netiom device.  This can be changed using the null modem
#cable connected to the card, with the jumper in.
url = 'http://192.168.0.6/'

west_stop = 175 # west software stop
east_stop = -175 #east software stop

##############
def sendstr(stringlist):
    # send the string command s to the contoller.  stringlist is a list of commands
    # so could be somethingi like ['T00'] or ['A01','A02','A09'].
    for s in stringlist:
        if connection:
            try:
                f = urllib.urlopen(url+'?'+s)
                f.close()
            except IOError:
                print("I/O error opening web page to send command to controller")
##        else:
##            print(url+'?'+s)
    return
##############
def enable_drive():
    # enable the output of the servo controller.  The telescope will start
    # driving if a non-zero speed has been set (see set_speed)
    sendstr(['A09']) #set pin 9 high
    return
##############
def disable_drive():
    # disable the output of the servo controller.  The telescope will stop
    # driving. Alway disable the drive when not intending to drive to prevent
    # creep and to remove any residual current in the motor.
    sendstr(['B09']) #set pin 9 low
    return
##############
def set_speed(v):
    # setup the controller to drive the telescope at a speed v ( any value -1 to 1).
    # A speed of 1 drives clockwise (ahead) at the maximum rate, -0.5 drives
    # backwards at half speed etc... The telescope will only start driving once
    # enable_drive is set.  The speed is set by the 8-bit DAC outout voltage.
    speed = int((1.0-v)/2.0*255) # put in the range 0-255
    vlist = []
    for i in range(7,-1,-1):
        if speed & 2**i:
             vlist.append('B0'+str(i+1))
        else:
            vlist.append('A0'+str(i+1))
    # disable DAC inputs (pin 10 is connected to WR on the DAC. When this input
    # is low, data is read.  When high the analogue voltage is fixed.)
    sendstr(['B10'])
    sendstr(vlist)
    sendstr(['A10','B10']) # enable/disable DAC inputs
    return
###############
def read_position():
    # The Netiom card serves files uploaded to it using the serial interface.
    # If the filename extension is ".cgi", then %xx strings are replaced with
    # values.  The encoder uses gray codes, indexed by graycode.txt
    if connection:
     try:
        g = urllib.urlopen(url+'digitalinputs.cgi')
        status_str = g.readline()
        g.close()
     except IOError:
        print("I/O error reading the encoder")
        status_str = '0000000000000'
    else:
        status_str = '0000000000000'
    # bugger! The netiom reports the lowest bit (bit 1) first, so we have to
    # reverse the string
    s2=''
    for i in range(0,13):
        s2 += status_str[12-i]
    # now turn it into a graycode base 10 integer
    gray = int(s2, base=2)
    # ... and find the content of this element in grayindex (removing the
    # trailing ".0\n".  Also, convert to degrees
    position = grayindex[gray][:-3]
    pos_degree = int(position)*360.0/8192.0
    if pos_degree >180.0:
        pos_degree -= 360.0
    return pos_degree
####################
def motor():
# reports on whether the motor is running
    if connection:
     try:
        g = urllib.urlopen(url+'digitaloutputs.cgi')
        status_str = g.readline()
        status_str = g.readline()
        g.close()
     except IOError:
        print("I/O error reading digitalinputs.cgi to find motor status")
        status_str = '0000000000'
    if status_str[0]=='1':
        status = 'on'
    else:
        status='off'
    return status
################################################################################

def setleft(evt): # called on "Rotate left" button event
    cube.dir = -1

def setright(evt): # called on "Rotate right" button event
    cube.dir = 1

def setred(evt): # called by "Make red" menu item
    cube.color = color.red
    t1.SetSelection(0) # set the top radio box button (red)

def setcyan(evt): # called by "Make cyan" menu item
    cube.color = color.cyan
    t1.SetSelection(1) # set the bottom radio box button (cyan)

def togglecubecolor(evt): # called by radio box (a set of two radio buttons)
    choice = t1.GetSelection()
    if choice == 0: # upper radio button (choice = 0)
        cube.color = color.red
    else: # lower radio button (choice = 1)
        cube.color = color.cyan

def cuberate(value):
    cube.dtheta = 2*value*pi/1e5

def setrate(evt): # called on slider events
    value = s1.GetValue()
    cuberate(value) # value is min-max slider position, 0 to 100

L = 320
w = window(width=2*(L+window.dwidth), height=L+window.dheight+window.menuheight,
           menus=True, title='Pulsar telesope controller')
# Place a 3D display widget in the left half of the window.
d = 20
display(window=w, x=d, y=d, width=L-2*d, height=L-2*d, forward=-vector(0,1,2))
cube = box(color=color.red)
p = w.panel # Refers to the full region of the window in which to place widgets

wx.StaticText(p, pos=(d,4), size=(L-2*d,d), label='telescope orientation',
              style=wx.ALIGN_CENTRE | wx.ST_NO_AUTORESIZE)

left = wx.Button(p, label='drive east', pos=(L+10,15))
left.Bind(wx.EVT_BUTTON, setleft)

right = wx.Button(p, label='drive right', pos=(1.5*L+10,15))
right.Bind(wx.EVT_BUTTON, setright)

t1 = wx.RadioBox(p, pos=(1.0*L,0.3*L), size=(0.25*L, 0.25*L),
                 choices = ['Red', 'Cyan'], style=wx.RA_SPECIFY_ROWS)
t1.Bind(wx.EVT_RADIOBOX, togglecubecolor)

tc = wx.TextCtrl(p, pos=(1.4*L,90), value='You can type here:\n',
            size=(150,90), style=wx.TE_MULTILINE)
tc.SetInsertionPoint(len(tc.GetValue())+1) # position cursor at end of text
tc.SetFocus() # so that keypresses go to the TextCtrl without clicking it

s1 = wx.Slider(p, pos=(1.0*L,0.8*L), size=(0.9*L,20), minValue=0, maxValue=100)
s1.Bind(wx.EVT_SCROLL, setrate)
wx.StaticText(p, pos=(1.0*L,0.75*L), label='speed')

##m = w.menubar # Refers to the menubar, which can have several menus
##
##menu = wx.Menu()
##item = menu.Append(-1, 'Rotate left', 'Make box rotate to the left')
##w.win.Bind(wx.EVT_MENU, setleft, item)
##
##item = menu.Append(-1, 'Rotate right', 'Make box rotate to the right')
##w.win.Bind(wx.EVT_MENU, setright, item)
##
##item = menu.Append(-1, 'Make red', 'Make box red')
##w.win.Bind(wx.EVT_MENU, setred, item)
##
##item = menu.Append(-1, 'Make cyan', 'Make box cyan')
##w.win.Bind(wx.EVT_MENU, setcyan, item)
##
### Add this menu to an Options menu next to the default File menu in the menubar
##m.Append(menu, 'Options')

# Initializations
s1.SetValue(70) # update the slider
cuberate(s1.GetValue()) # set the rotation rate of the cube
cube.dir = -1 # set the rotation direction of the cube





# read in the graycode lookup table.  This was generated by graycode.py
graycodefile = open('graycode.txt', 'r')
grayindex = graycodefile.readlines()
graycodefile.close()

# set up the crab ephemeris
Acre_Road = ephem.Observer()
Acre_Road.long, Acre_Road.lat, Acre_Road.elev = "-4:18:25.93", "55:54:8.29",50
Acre_Road.pressure = 0 #remove refraction
crab = ephem.readdb("Crab pulsar,f|L,05:34:31.97,22:0:52.1,0,2000") #set up the target
crab = ephem.Sun()
# slew to the Crab
speed = 0.0
set_speed(speed)
enable_drive()
pos = 0.0







self = wx.StaticText(p, pos=(1.0*L,0.75*L-45), label="")
self.SetForegroundColour(wx.RED)



while True:
    rate(1)


    Acre_Road.date = ephem.now()
    crab.compute(Acre_Road) # compute its position at present epoch
    hh = (Acre_Road.sidereal_time() - crab.ra)/math.pi*180.0 # calculate the current hh=lst-ra
    if hh>180.0: hh = hh-360.0
    if hh<-180.0: hh = hh+360
#    hh =0.0   # force the hour angle to a value
    if hh>west_stop: hh=0.0
    if hh<east_stop: hh=0.0
    if connection:
        pos = read_position()
    else:
        pos = pos + (hh-pos)*.4 # fake the driving
    diff = hh - pos
    if abs(diff)>0.0001:
        sign = diff/abs(diff)
    else:
        sign = 1
    diff = abs(diff)
    if diff>1:
        enable_drive()
        speed = sign*(diff/360)**(0.3)
        set_speed(speed)
    else:
        disable_drive()
    print("%s hour angle %.2f , encoder %.2f, diff %.2f , speed, %.2f" %  (ephem.now(), hh, pos, sign*diff, speed))
##    print("%s hour angle %.2f " %  (ephem.now(), hh))
##    try:
##        bar.title('Crab pulsar tracker: '+str(ephem.now()))
##        bar.label("hh %.2f, encoder %.2f, diff %.2f , speed %.2f, drive %s" %  (hh, pos, diff, speed, motor()))
##        bar.set(diff, 17)
##    except KeyboardInterrupt:
##        break
    self.SetLabel("%s UTC" % ephem.now())
##    wx.StaticText(p, pos=(1.0*L,0.75*L-45), label="%s UTC" % ephem.now())
##    wx.StaticText(p, pos=(1.0*L,0.75*L-30), label="   encoder position %.2f degrees" % pos)
##    wx.StaticText(p, pos=(1.0*L,0.75*L-15), label="drive to hour angle %.2f degrees" % hh)

    cube.rotate(axis=(0,1,0), angle=diff/180*pi)

    if connection == False:
        time.sleep(0)
disable_drive()




