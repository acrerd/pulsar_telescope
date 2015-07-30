"""
Data functions for the pulsar telescope at Acre Road.
"""

from pylightcurve import Lightcurve

import ephem, logging, os
import numpy as np
import matplotlib.pyplot as pl
from matplotlib import dates
import scipy
import datetime 
import scipy.signal

from collections import deque,Counter
from bisect import insort, bisect_left
from itertools import islice
import scipy.stats
from astropy.time import Time
#import astropysics
#import astropysics.coords

from copy import copy, deepcopy

import pmt
from gnuradio.blocks import parse_file_metadata
import pandas as pd
from functools import partial
import os.path

# Details of Acre Road observatory
Acre_Road = ephem.Observer()
Acre_Road.long, Acre_Road.lat, Acre_Road.elev = "-4:18:25.93", "55:54:8.29",50
Acre_Road.pressure = 0 #remove refraction

class TimeSeries(Lightcurve):

    coords = ephem.Equatorial('03:32:59.368', '+54:34:43.57', epoch='2000')

    def __init__(self, filepath, smoothing=3, window='hanning', sample=1, start=385000, title="Pulsar observations"):
        """Acre Road Telescope Pulsar Time Series
        -----------------------------------------
        
        This class is designed to handle the loading of radio
        astronomy time series produced by the GNU Radio toolkit, to
        conduct pre-processing, and to fold the resulting data.

        """
        data = scipy.fromfile(open(filepath), dtype=scipy.float32)

        self.default="total power"

        self.data_len = len(data)
        
        # Load the meta data, and detect any overruns
        meta, overs = self.parse_metadata(filepath)

        self.overs = overs
        
        filename = os.path.split(filepath)[-1]
        if 'rx_rate' in meta['total power']:
            samp_rate = meta['total power']['rx_rate']
        else:
            samp_rate=sample
            meta['total power']['samp_rate'] = samp_rate
        #samp_rate = meta['total power']['samp_rate']
        self.samp_rate=samp_rate
            
        if 'rx_time' in meta['total power']:
            if meta['total power']['rx_time']<100:
                gpstime = start
            else:
                rx = meta['total power']['rx_time']
                gpstime = Time(rx, format='unix').gps
        else:
            gpstime = np.float64(filename.split("-")[0])
                                            
        self.start = gpstime
        self.start_t = Time(self.start, format='gps')    
            
        if len(overs) > 0:
            first, first_t = np.float64(0), np.float64(0)
            times = np.array([])
            for over in overs:
                new, new_t = over['new_seg'], over['new_time']
                seg_len = new - first
                segment = np.linspace(first_t, first_t + new/np.float64(self.samp_rate), seg_len)
                times = np.append(times, segment)
                first, first_t = new, Time(new_t, format='unix').gps - self.start
            seg_len = len(data) - first
            segment = np.linspace(first_t, first_t + len(data)/np.float64(self.samp_rate), seg_len)
            times = np.append(times, segment)
        else:
            times = np.linspace(0,len(data)/np.float64(samp_rate), len(data))+self.start

        self.times = times
        times = Time(times, format='gps', scale='tai')
        dframe = pd.DataFrame({'total power':data}, index=times.value)
        self.import_data(dframe, meta, cts=times)


        
        self.time = times                   
        self.smoothing = smoothing
        self.window = window
        self.title = title

    @property
    def clc(self):
        return np.array(self.data[self.default])
        
    def parse_metadata(self, filepath):
        head_file = filepath+".hdr"
        hlen = parse_file_metadata.HEADER_LENGTH

        headers = []
        extra_tags = []

        overs = []

        if not os.path.isfile(head_file):
            return {'total power':{}}, []

        with open(head_file,'rb') as fd:
            for h_str in iter(partial(fd.read, hlen), ''):
                h_pmt = pmt.deserialize_str(h_str)
                h_parsed=parse_file_metadata.parse_header(h_pmt,False)
                headers.append(h_parsed)
                if(h_parsed["extra_len"] > 0):
            
                    extra_str = fd.read(h_parsed["extra_len"])
                    if(len(extra_str) == 0):
                        break
                    extra = pmt.deserialize_str(extra_str)
                    e_parsed = parse_file_metadata.parse_extra_dict(extra, h_parsed, False)
                    extra_tags.append(e_parsed)

        # Load the extra data into the tagging system for the LightCurve.
        tags = pd.DataFrame({'total power':[{} for _ in xrange(self.data_len)]})
        nums_done = 0 
        segment_start_time = headers[0]['rx_time']
        segments = 1
        for i  in xrange(len(extra_tags)):
            j = int(nums_done + extra_tags[i]['nitems'])
            if not extra_tags[i]['rx_time'] == segment_start_time:

                should = segment_start_time + j/extra_tags[i]['rx_rate']

                miss_sec = extra_tags[i]['rx_time']-should

                overs.append({'new_seg':j, 'new_time':extra_tags[i]['rx_time']})

                segment_start_time = extra_tags[i]['rx_time']
                segments += 1
            j = int(nums_done + extra_tags[i]['nitems'])
            tags['total power'][j] = extra_tags[i]
            nums_done += extra_tags[i]['nitems']
        new = self.import_tags(extra_tags, 'total power')
            
        return {'total power': headers[0]}, overs


    def remove_outlier(self, lower=0, upper=1000, **kwargs):
        """
        Replace data with values less than `lower` and greater than `higher` with NANs.

        Parameters
        ----------
        lower : float
           The lower value cutoff. Default is 0.
        upper : float
           The upper value cutoff. Default is 1000.
        inplace : bool, optional
           Replaces the data in the object with the filtered data. By default this is
           False.
        """
        new_object = deepcopy(self)
        data = new_object.data

        if "column" in kwargs:
            column = kwargs["column"]
            dataw = data[column].values
        else:
            dataw = data[self.default].values
        
        dataw[np.logical_or(dataw>upper, dataw<lower)] = np.nan
        #dataw[dataw<lower] = np.nan
        dataw = dataw - self._dcoffsets[self.default]
        
        if "column" in kwargs:
            column = kwargs['column']
            data[column]= dataw
        else:
            new_object.clc = dataw

        
        if "inplace" in kwargs:
            self.clc = dataw
            self.data = data
            return self
        else:
            return new_object

    def homogen(self):
        data = self.data
        data_h = np.zeros([data.size])

        # Let's reshape the array in preparation for homogenising
        sample = self.sample
        hour_s = int(3600*sample)
        #noise = [42,15,7,3,9,9,11,6,9,14,16,21,30]
        pad_size = np.ceil(float(data.size)/hour_s)*hour_s - data.size
        b_padded = np.append(data, np.zeros(pad_size)*np.nan)
        data_s = b_padded.reshape(-1,hour_s)   # The reshaped data
        #print data_s.shape
        for i in np.arange(data_s.shape[0]):
            #print i, scipy.stats.nanstd(data_s[i,:])
            data_s[i,:] = data_s[i,:]/(float(scipy.stats.nanstd(data_s[i,:])**2))
        
        self.data_h = np.delete(data_s.flatten(), np.arange(-pad_size,-1))

    def relativeVelocity(self,jdn):
        coords = self.coords
        coords = ephem.Ecliptic(coords)
        # Calculate the relative velocity of the Earth compared to an object at ecliptic 
        # coordinates coords on julian day number jdn
        cart_position = [ np.cos(coords.lat) * np.cos(coords.lon),
                          np.cos(coords.lat) * np.sin(coords.lon),
                          np.sin(coords.lat) ]
        s = astropysics.coords.earth_pos_vel(jdn, barycentric=False, kms=True)[1]*1000
        v = np.dot(np.array(s), cart_position)    # velocity relative to crab in m/s
        return [v, np.linalg.norm(s)]

    def relativeVelocityEQ(self, jdn):
        coords = self.coords
        # Calculate the relative velocity of the Earth compared to an object at equatorial 
        # coordinates coords on julian day number jdn
        cart_position = [ np.cos(coords.dec) * np.cos(coords.ra),
                          np.cos(coords.dec) * np.sin(coords.ra),
                          np.sin(coords.dec) ]
        s = astropysics.coords.earth_pos_vel(jdn, barycentric=False, kms=True)[1]*1000
        v = np.dot(np.array(s), cart_position)    # velocity relative to crab in m/s

    def doppler(self, v):
        # Calculate the redshifting caused by a velocity of v
        c = 299792458
        z = (1 + (v[0]/c)) / np.sqrt(  (1 - ((v[1]**2)/c**2)))
        return z

    def jdntodublin(self,jdn):
        # Convert the standard Julian Day Number to a Dublin Modified JDN
        return jdn - 2415020
        
    def dopplerCorrect(self):
        f = np.fft.fft(self.data)
        d = Time(self.time[0], format='gps')
        v = self.relativeVelocity(d.jd)
        f =  f/self.doppler(v)
        return np.fft.ifft(f)

    def get_f(self, time, ephemeris):
        """
        Returns the time, the pulsar frequency, 
        and the fractional difference between steps for a 
        pulsar given a time and an ephemeris file.
        """
        ephem = np.genfromtxt(ephemeris)
        hour = 3600
        f = np.interp(time, ephem[:,0], ephem[:,1])
        fdot = (np.interp(time, ephem[:,0], ephem[:,1]) - np.interp(time-hour, ephem[:,0], ephem[:,1]))/hour
        return time, f, fdot

    def save(self, filepath, **kwargs):
        """
        Saves data out in binary format.

        Parameters
        ----------
        filepath : str
           The location of the file the data will be written to.
        column : str
           The column which should be written out
        """
        data = self.data
        if "column" in kwargs:
            column = kwargs['column']
            dataw = data[column]
        else:
            dataw = data[self.default]
        output = dataw.values
        fd = open(filepath, 'wb')    
        output.tofile(fd)
        return self
        
        
    def fold(self, ephemeris):
        """
        Folds a lightcurve at a given frequency.
        """
        self.homogen()
        data = self.data_h

        data = scipy.signal.medfilt(data, 5)
        
        sample = self.sample
        time = self.time

        # Remove the DC Offset from the data
        data = data - np.median(data)
        data = self.correct_outliers(value=10)
         
        # Correct the frequencies for doppler shift
        # data = self.dopplerCorrect(data)

        # The folding period must be the inverse of the frequency
        # but we want the period in terms of bins, not of seconds
        # so need to multiply by the number of samples per second
        period = 1.0 / frequency
        period_s = int(np.floor(sample*period))
        
        # We now have the period, so need to work out how many periods
        # exist in the lightcurve
        number_p = int(np.floor(len(data)/period_s))
        
        phase   = frequency * (time-time[0])

        # Make an array for the stacked data
        self.stack = np.zeros((period_s, number_p+1))
        self.stackcount = np.zeros((period_s, number_p+1))
        for i in np.arange(len(phase)):
            # Calculate which period this is in
            phase_b  = int(np.round( (phase[i] % 1) *(1/frequency)*self.sample) )
            period = int(np.floor(phase_b / period_s))
            phasey  = int(phase_b % period_s)

            self.stack[phasey, period] += data[i]
            if data[i]!=0:
                self.stackcount[phasey, period] += 1
            #print period,phase
        
        return self.stack, self.stackcount
        
    def fold_naive(self, frequency):
        """
        Folds a lightcurve at a given frequency.
        """
        #self.homogen()
        
        data = self.data #/scipy.stats.nanstd(self.data)**2
        sample = self.sample
        time = self.time

        # Remove the DC Offset from the data
        data = data - np.median(data)

        # The folding period must be the inverse of the frequency
        # but we want the period in terms of bins, not of seconds
        # so need to multiply by the number of samples per second
        period = 1.0 / frequency
        period_s = int(np.floor(sample*period))

        # We now have the period, so need to work out how many periods
        # exist in the lightcurve
        number_p = int(np.floor(len(data)/period_s))
        
        folded = np.zeros(np.floor(period_s))
        folds  = np.zeros(np.floor(period_s))

        # Let's reshape the array in preparation for folding
        pad_size = np.ceil(float(data.size)/period_s)*period_s - data.size
        b_padded = np.append(data, np.ones(pad_size)*np.nan)
        data_s = b_padded.reshape(-1,period_s)   # The reshaped (thus stacked) data

        # We also need to 'normalise' the data, so that it represents a set
        # of means rather than just a total.

        counted = np.ones(data_s.shape)
        counted[np.isnan(data_s)] = 0
        
        self.data_s = data_s
        self.fold_counter = counted

        # Need to recalculate the time axis
        self.phase = np.linspace(0, period, np.shape(folded)[0])

    def find_freq_fold(self, frequency):
        """
        Finds the frequency by folding the lightcurve. An initial guess is required to speed this process.
        """
        #self.homogen()
        
        data = self.data #/scipy.stats.nanstd(self.data)**2
        sample = self.sample
        time = self.time

        # Remove the DC Offset from the data
        data = data - np.median(data)

        # The folding period must be the inverse of the frequency
        # but we want the period in terms of bins, not of seconds
        # so need to multiply by the number of samples per second
        period = 1.0 / frequency
        period_s = int(np.floor(sample*period))

        # We now have the period, so need to work out how many periods
        # exist in the lightcurve
        number_p = int(np.floor(len(data)/period_s))
        
        folded = np.zeros(np.floor(period_s))
        folds  = np.zeros(np.floor(period_s))

        # Let's reshape the array in preparation for folding
        pad_size = np.ceil(float(data.size)/period_s)*period_s - data.size
        b_padded = np.append(data, np.ones(pad_size)*np.nan)
        data_s = b_padded.reshape(-1,period_s)   # The reshaped (thus stacked) data

        means = data_s.mean(axis=0)
        maxi  = np.nanmax(means)

        # Try folding over a range of different periods close to
        # the guess frequency
        newperiod = period_s
        periods = np.arange(period_s-40, period_s+40)
        for period in periods:
            pad_size = np.ceil(float(data.size)/period_s)*period_s - data.size
            b_padded = np.append(data, np.ones(pad_size)*np.nan)
            data_s = b_padded.reshape(-1,period_s)   # The reshaped (thus stacked) data

            means = data_s.mean(axis=0)
            if np.nanmax(means)>maxi:
                newperiod = period
                maxi = np.nanmax(means)

        print period_s, ",", period
        # We also need to 'normalise' the data, so that it represents a set
        # of means rather than just a total.

        counted = np.ones(data_s.shape)
        counted[np.isnan(data_s)] = 0
        
        self.data_s = data_s
        self.fold_counter = counted

        # Need to recalculate the time axis
        self.phase = np.linspace(0, period, np.shape(folded)[0])

    # def smooth(self):
    #     """smooth the data using a window with requested size.

    #     This method is based on the convolution of a scaled window with the signal.
    #     The signal is prepared by introducing reflected copies of the signal 
    #     (with the window size) in both ends so that transient parts are minimized
    #     in the begining and end part of the output signal.

    #     input:
    #         x: the input signal 
    #         window_len: the dimension of the smoothing window; should be an odd integer
    #         window: the type of window from 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'
    #             flat window will produce a moving average smoothing.

    #     output:
    #         the smoothed signal

    #     example:

    #     t=linspace(-2,2,0.1)
    #     x=sin(t)+randn(len(t))*0.1
    #     y=smooth(x)

    #     see also: 

    #     numpy.hanning, numpy.hamming, numpy.bartlett, numpy.blackman, numpy.convolve
    #     scipy.signal.lfilter

    #     TODO: the window parameter could be the window itself if an array instead of a string
    #     NOTE: length(output) != length(input), to correct this: return y[(window_len/2-1):-(window_len/2)] instead of just y.
    #     """

    #     window_len = self.smoothing
    #     window = self.window
    #     x = self.data
    #     if x.ndim != 1:
    #         raise ValueError, "smooth only accepts 1 dimension arrays."

    #     if x.size < window_len:
    #         raise ValueError, "Input vector needs to be bigger than window size."


    #     if window_len<3:
    #         return x


    #     if not window in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
    #         raise ValueError, "Window is on of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'"


    #     s=np.r_[x[window_len-1:0:-1],x,x[-1:-window_len:-1]]
    #     #print(len(s))
    #     if window == 'flat': #moving average
    #         w=np.ones(window_len,'d')
    #     else:
    #         w=eval('np.'+window+'(window_len)')

    #     y=np.convolve(w/w.sum(),s,mode='valid')
    #     return y[(window_len-1)/2:-(window_len-1)/2]