# needs PyEphem -- see http://pypi.python.org/pypi/pyephem/
import ephem, math, time

Acre_Road = ephem.Observer()
Acre_Road.long, Acre_Road.lat, Acre_Road.elev = "-4:18:25.93", "55:54:8.29",50
Acre_Road.pressure = 0 #remove refraction

crab = ephem.readdb("Crab pulsar,f|L,05:34:31.97,22:0:52.1,0,2000") #set up the target
crab.compute(Acre_Road) # compute its position at present epoch

hh = Acre_Road.sidereal_time() - crab.ra # calculate the current hh=lst-ra
print "Crab pulsar hour angle ", ephem.degrees(hh), "degrees"
print "Crab pulsar hour angle ", hh/math.pi*180, "degrees"
print "Crab pulsar hour angle ", ephem.hours(2*math.pi+hh), "hours"
print "at current time ", ephem.now()

print "The Crab will set at ", Acre_Road.next_setting(crab)
print "...and rise at ", Acre_Road.next_rising(crab)
