import time
import numpy as np
import pandas as pd
# from mms_curvature import DataLoad, Curvature
from mms_curvature.mms_curvature import Curvature
from mms_curvature.dataload_parallel import DataLoad
from mms_gyroradius import DataLoadMoments, CalcRadius
from mms_TQF import get_TQF
from pytplot import get_data

# Minimum verbosity for status; time-keeping
timeStart =  time.strftime("%H:%M:%S", time.localtime())
print("Files Loading:")

####################################################
# Set parameters here
trange=['2017-06-17/20:00', '2017-06-17/21:00']
data_rate='srvy'
prefix="CurveGSM_rg_tqf_"
suffix="_tim1"
save_csv=True
save_h5=False
####################################################

# Calculate some additional attributes for later use

def FleetPos(postime1, postime2, postime3, postime4, rm, t_master):
    '''
    First checks to make sure that all 4 S/C have the same MEC time series then 
    calculates the fleet postion in MLT and Radius(km)
    '''
    if any(postime1 != postime2) or any(postime2 != postime3) or any(postime3 != postime4): 
        print("MEC times not aligned!")
        return (None, None)

    posmlt1 = get_data('mms1_mec_mlt')[1]
    posmlt2 = get_data('mms2_mec_mlt')[1]
    posmlt3 = get_data('mms3_mec_mlt')[1]
    posmlt4 = get_data('mms4_mec_mlt')[1]
    
    #posmltdata = (1./4.)*(posmlt1 + posmlt2 + posmlt3 + posmlt4)
    posmltm = np.interp(t_master, postime1, ((1./4.)*(posmlt1 + posmlt2 + posmlt3 + posmlt4)))

    posrm = np.linalg.norm(rm, axis=1)

    return (posmltm, posrm)

def mesoGyroradius(trange=['2017-05-28', '2017-05-29'], data_rate='srvy', level='l2', t_master=None, bmag=None):
    '''
    Calculates the average gyroradius in the tetrahedron, assumed to be 
    representative of the gyroradius at the mesocenter.  Uses FPI data.

    inputs:
    trange:     2-element list of strings for start and end times 
                ex.['2017-05-28', '2017-05-29/12:02:01']
    data_rate:  Choices are 'srvy' or 'brst'
    level:      data level to use.  Use 'l2' unless you know for sure
    t_master:   Time series for the magnetic field data, assumed from mms_curvature.Curvature
    bmag:       |B| aligned with t_master.  Assumed from mms_curvature.Curvature

    outputs:
    (r_i, r_e) -- 2-element structure aligned with t_master time series where:
    r_i:        average gyroradius of ions (assumed protons) 
    r_e:        average gyroradius of electrons

    '''

    # constants for future use
    me = 9.1094e-31     # electron mass in kilograms
    mp = 1.6726e-27     # proton mass in kg; used as proxy for all ions

    # load all the needed plasma data
    distime1, distempperp1, destime1, destempperp1 = DataLoadMoments(trange=trange, data_rate=data_rate, level='l2', probe='1')
    distime2, distempperp2, destime2, destempperp2 = DataLoadMoments(trange=trange, data_rate=data_rate, level='l2', probe='2')
    distime3, distempperp3, destime3, destempperp3 = DataLoadMoments(trange=trange, data_rate=data_rate, level='l2', probe='3')
    distime4, distempperp4, destime4, destempperp4 = DataLoadMoments(trange=trange, data_rate=data_rate, level='l2', probe='4')

    # assume time_clip worked and use mms1 as the master clock.  Might swap this for a search later

    mitime = distime1   # master ion time
    distempperp2 = np.interp(mitime, distime2, distempperp2)
    distempperp3 = np.interp(mitime, distime3, distempperp3)
    distempperp4 = np.interp(mitime, distime4, distempperp4)

    metime = destime1   # master electron time
    destempperp2 = np.interp(metime, destime2, destempperp2)
    destempperp3 = np.interp(metime, destime3, destempperp3)
    destempperp4 = np.interp(metime, destime4, destempperp4)

    tiperp = np.average([distempperp1, distempperp2, distempperp3, distempperp4], axis=0)   # average ion T_perp
    teperp = np.average([destempperp1, destempperp2, destempperp3, destempperp4], axis=0)   # average electron T_perp

    r_i = CalcRadius(part_time=mitime, part_tempperp=tiperp, b_time=t_master, b_mag=bmag, part_mass=mp, part_q=1.602177e-19)
    r_e = CalcRadius(part_time=metime, part_tempperp=teperp, b_time=t_master, b_mag=bmag, part_mass=me, part_q=1.602177e-19)

    return (r_i, r_e)

############################################################################################################################


# Generate sane filename
if len(trange[0]) > 10 or len(trange[1]) > 10:
    filename = prefix+trange[0][:10]+"_"+trange[0][11:13]+trange[0][14:16]+"--"+trange[1][:10]+"_"+trange[1][11:13]+trange[1][14:16]+suffix+".csv"
else:
    filename = prefix+trange[0][:10]+"--"+trange[1][:10]+suffix+".csv"


# Get B-field data and calculate curvature
postime1, pos1, magtime1, mag1, postime2, pos2, magtime2, mag2, postime3, pos3, magtime3, mag3, postime4, pos4, magtime4, mag4 = DataLoad(trange=trange, data_rate=data_rate)

print("Time started: ", timeStart)
print("Time Loaded: ", time.strftime("%H:%M:%S", time.localtime()))

print("Calculating Curvature:")

t_master, grad_Harvey, curve_Harvey, rarr, barr, rm, bm, bmag= Curvature(postime1, pos1, magtime1, mag1, postime2, pos2, magtime2, mag2, postime3, pos3, magtime3, mag3, postime4, pos4, magtime4, mag4, report_all=True)[0:8]

print("Done calculating Curvature.")


# Calculate gyroradii
r_i, r_e = mesoGyroradius(trange=trange, data_rate=data_rate, level='l2', t_master=t_master, bmag=bmag)
r_i = r_i/1000
r_e = r_e/1000  # Convert from meters to km

# Get fleet position
posmltm, posrm = FleetPos(postime1, postime2, postime3, postime4, rm, t_master)


# Get Tetrahedron Quality Factor (TQF)
TQFarr = get_TQF(trange=trange)[1]
bcnt=0
while TQFarr[bcnt,0] < t_master[0]: bcnt = bcnt + 1     # find beginning of trange in TQFarr
ecnt = -1
while TQFarr[ecnt,0] > t_master[-1]: ecnt = ecnt -1     # find end of trange in TQFarr
print("\n\n*** bcnt= "+str(bcnt)+"   ecnt= "+str(ecnt)+"   ***\n\n")
TQF = np.interp(t_master, TQFarr[bcnt:ecnt,0].astype('float64'), TQFarr[bcnt:ecnt,1].astype('float64')) # interpolate to match t_master


# Calculate the magnitude of the curvature to find radius
curve_norm = np.linalg.norm(curve_Harvey, axis=1)


# Construct Pandas data frame of all calculated data for export 
curvedf = pd.DataFrame({'Rc(km)': 1/curve_norm, '|curve|': curve_norm, 'Curvature_X(GSM)': curve_Harvey.take(0,axis=1), 'Curvature_Y(GSM)': curve_Harvey.take(1,axis=1), 'Curvature_Z(GSM)': curve_Harvey.take(2,axis=1), '|B|': bmag, 'R_gi(km)': r_i, 'R_ge(km)': r_e, 'Position(MLT)': posmltm, 'Position_radius(km)': posrm, 'Position_Xgsm(km)': rm.take(0,axis=1), 'Position_Ygsm(km)': rm.take(1,axis=1), 'Position_Zgsm(km)': rm.take(2,axis=1), 'TQF': TQF}, index=t_master)

print("Writing File: "+filename)

curvedf.index.name="Time"
if save_csv: curvedf.to_csv(filename)
if save_h5: curvedf.to_hdf(filename[:-3]+'h5', key='df')

print("Time started: ", timeStart)
print("Time finished: ", time.strftime("%H:%M:%S", time.localtime()))
#mag_curve_frame.to_csv(filename)


#np.savetxt("t_master.csv", t_master, delimiter=",")
#np.savetxt("grad_Harvey.csv", grad_Harvey, delimiter=",")
#np.savetxt("curve_Harvey.csv", curve_Harvey, delimiter=",")
#np.save("grad_Harvey.npy", grad_Harvey)
# end
