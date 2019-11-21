# drive-telesope keeps the pulsar telesope tracking the Crab
#
import ephem, time, math, EasyDialogs

bar = EasyDialogs.ProgressBar()


west_stop = 175 # west software stop
east_stop = -175 #east software stop



# set up the crab ephemeris
Acre_Road = ephem.Observer()
Acre_Road.long, Acre_Road.lat, Acre_Road.elev = "-4:18:25.93", "55:54:8.29",50
Acre_Road.pressure = 0 #remove refraction
crab = ephem.readdb("Crab pulsar,f|L,05:34:31.97,22:0:52.1,0,2000") #set up the target

while True:
    Acre_Road.date = ephem.now()
    crab.compute(Acre_Road) # compute its position at present epoch
    hhc = Acre_Road.sidereal_time() - crab.ra # calculate the current hh=lst-ra
    hh = hhc/math.pi*180.0 # calculate the current hh=lst-ra

    try:
        bar.title('Pulsar telescope tracker: '+str(ephem.now()))
        bar.label("target hour angle:  %s \n              encoder: %7.2f degrees \n           difference: %7.2f degrees \nspeed: %7.2f \ndrive %s" %  (ephem.hours(hhc), 32, 1, 0.12 , 'string'))
        bar.set(10, 17)
    except KeyboardInterrupt:
        break





