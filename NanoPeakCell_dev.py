#!/Library/Frameworks/Python.framework/Versions/Current/bin/python
####################################################################################################
# EDF Hit finder and HDF5 Converter - Colletier, IBS, 2014
#####################################################################################################

#from wx.lib.pubsub import Publisher as pub 
try:
   from wx.lib.pubsub import pub
except ImportError: from pubsub import pub
from HitFinder_dev import HitFinder
import sys, fabio, glob, numpy as np, h5py, time, math, shutil, os
import optparse
import pyFAI, pyFAI.distortion, pyFAI.detectors
#import matplotlib
#import matplotlib.mlab as mlab
#from mpl_toolkits.mplot3d import Axes3D
#from matplotlib import cm
#from matplotlib.ticker import LinearLocator, FixedLocator, FormatStrFormatter
from scipy.interpolate import Rbf
import multiprocessing
from scipy import ndimage
import datetime
from threading import Thread


import warnings
warnings.simplefilter("ignore")

def NPCVar():
    import os
    return os.environ['NPC']

#flatfield=fabio.open("/mntdirect/_data_opid13_inhouse1/SRC_SERIAL/nanopeakcell/flatfield_1024.edf").data.astype(np.float32)
#frelon=pyFAI.detectors.FReLoN(splineFile="/mntdirect/_data_opid13_inhouse1/SRC_SERIAL/nanopeakcell/distorsion_1024.spline")
#darkpath="/mntdirect/_data_visitor/ls2253/id13/DATA/lys2/"

class Correction():
    
    
    def __init__(self, resolution):
        self.resolution=resolution
	self.root=NPCVar()
    
    def load_all(self):
    	try:
	  self.ff=os.path.join(self.root,"FILES","flatfield_%i.edf"%self.resolution)
	  self.flatfield=fabio.open(self.ff).data.astype(np.float32)
	except : 
	   return False
	   print "Error with flatfield image"
        
	try:
	   self.d=os.path.join(self.root,"FILES","dark.edf")
	   self.dark=fabio.open(self.d).data.astype(np.float32)
	except: 
	  return False
	  print "Please provide a dark image"
	  
	
        try:
	  self.sf=os.path.join(self.root,"FILES","distorsion_%i.spline"%self.resolution)
	  frelon=pyFAI.detectors.FReLoN(splineFile=self.sf)
          self.dist=pyFAI.distortion.Distortion(frelon)
          print "Calculating Distortion Look-Up Table"
          self.dist.calc_LUT()
	  return True
	except: 
	  print "Error with distortion correction"
	  return False
	  
    def apply_correction(self,data,apply_dark,apply_ff,apply_dist):
        if apply_dark:
	    tmp=data.astype(np.float32) - self.dark
	else: tmp=data.astype(np.float32) 
	
	if apply_ff:
	    tmp=tmp/self.flatfield 
	
	if apply_dist:
	    tmp=self.dist.correct(tmp)
	
	return tmp
	
class AI():
    """ This class instanti
    """
    def __init__(self, XSetup,Detector):
        self.root=NPCVar()
	self.distance=XSetup.distance/1000.
	self.psx=Detector.pixel_size/1000.
	self.psy=Detector.pixel_size/1000.
	self.bcx=XSetup.beam_y*self.psx
	self.bcy=XSetup.beam_x*self.psy
	self.resolution=Detector.resolution
	#self.sf=os.path.join(self.root,"FILES","distorsion_%i.spline"%self.resolution)
	self.spline=os.path.join(self.root,"FILES","distorsion_%i.spline"%self.resolution[0])
	self.detector=Detector
	self.wl=XSetup.wavelength
	self.ai=pyFAI.AzimuthalIntegrator(dist=self.distance,
			                  poni1=self.bcx,
					  poni2=self.bcy,
					  rot1=0,
					  rot2=0,
					  rot3=0,
					  pixel1=self.psx,
					  pixel2=self.psy,
					  splineFile=self.spline,
					  detector=self.detector.name,
					  wavelength=self.wl)
	#We should remove the beam stop				  
	self.mask=np.zeros(self.resolution,dtype=bool)
	extend=15
	#self.mask[XSetup.beam_y-extend:XSetup.beam_y+extend,XSetup.beam_x-extend:XSetup.beam_x+extend]=True
    def test(self):
	    print "Distance (m): %s" %str(self.distance)
	    print "Beam center X (m): %s" %str(self.bcx)
	    print "Beam center Y (m): %s" %str(self.bcy)	
	    print "Pixel Size  X (m): %s" %str(self.psx)
	    print "Pixel Size  Y (m): %s" %str(self.psy)
	 	
	    	        
class Detector():
    def __init__(self):
        self.name=''
	self.pixel_size=0.1 #(mm)
	self.overload=65535
	self.resolution=(2048,2048)
	self.binning=1
	
    def set_resolution(self,img):
        self.resolution=img.data.shape
	if self.name == 'Frelon': 
	   self.binning=int(2048/self.resolution[0])
	   self.pixel_size=self.pixel_size*self.binning
	
class Frelon(Detector):
    def __init__(self):
        Detector.__init__(self)
        self.name='Frelon'
        self.pixel_size=0.05131 #(mm)
	
    
class Pilatus6M(Detector):
    def __init__(self):
        Detector.__init__()
        self.name='Pilatus6M'
	self.resolution=(2463,2527)
	self.pixel_size=0.172
        #self.pixel_size=0.05131 #(mm)
           

class XSetup():

    wavelength=0.832
    distance=100.626
    beam_x=523.2544
    beam_y=512.7213
    
class HFParams():

    threshold=30
    DoBkgCorr=True
    DoDarkCorr=True
    DoFlatCorr=True
    DoDist=True
    DoPeakSearch=True
    npixels=20
    nbkg=1
    bkg=1
    procs=8

class IO():   
    # This class instantiates all dirs and filenames
    # Also creates background and filename list
    def __init__(self):
      self.ext=".edf"
      self.root=None
      self.bkg=[]
      self.datadir=None
      self.procdir=None
      self.pickle=False
      self.H5=True
      self.edf=False
      self.bname_list = []
      self.fname_list=[]
      
    def get_all_frames(self):
        return glob.glob(self.root+"*.edf")
	
    
    #def get_bkg(self):
        
#	try:self.bkg=self.bkg.split(',')
#	except: self.bkg=self.bkg
#	for img in self.bkg:
#	   img=str(img)
#	   if len(img) <= 3:
#	       self.bname_list.append(self.root+'_%s.edf'%img.zfill(4))
#	   else: self.bname_list.append(self.root+'_%s.edf'%img)
#	return self.bname_list
	
	
class Projection():

    def __init__(self,filename):

        max_proj = np.zeros_like(fabio.open(filename).data).astype(np.int32)
	avg = np.zeros_like(filename).astype(np.int32)
	#bkg = np.zeros_like(self.max_proj).astype(np.int32)
	cleanmax = np.zeros_like(filename).astype(np.int32)
	hitmax = np.zeros_like(filename).astype(np.int32)
	cleanhit = np.zeros_like(filename).astype(np.int32)


	#avg = avg//nbfile
	#print "Max, Min and Median of average"
	#print np.max(avg), np.min(avg), np.median(avg)
	#print "Max, Min and Median of maxproj"
	#print np.max(max_proj), np.min(max_proj), np.median(max_proj)

	#cleanmax = max_proj
	#cleanhit = hitmax - avg
	#diff = self.max_proj.astype(np.int32) - hitmax.astype(np.int32)
	#print ""
	#print "Diff. map between all images and hits: max= %5.1f ; median= %5.1f ; std= %5.1f:" %(np.max(diff), np.median(diff), np.std(diff))
	#print ""
	
	#hitmax = smooth(hitmax.astype(np.int32)) #, light_background=False,smoothing=False)
	#dograph(max_proj.astype(np.int32),hitmax.astype(np.int32),diff.astype(np.int32),float(threshold),np.median(hitmax))
	
	# Output maximum projection in edf format

	#if correct:
	#	outmax_proj = fabio.edfimage.edfimage(data = max_proj.astype(np.int32), header = img.header ) 
	#	outmax_proj.write('max_proj_corrected.edf')
	#	outhitmax = fabio.edfimage.edfimage(data = hitmax.astype(np.int32), header = img.header )
	#	outhitmax.write('hitmax_corrected.edf')
	#	outhitmax = fabio.edfimage.edfimage(data = diff.astype(np.int32), header = img.header )
	#	outhitmax.write('diff_corrected.edf')
	#else :
	#	outmax_proj = fabio.edfimage.edfimage(data = max_proj.astype(np.int32), header = img.header ) 
	#	outmax_proj.write('max_proj.edf')
	#	outhitmax = fabio.edfimage.edfimage(data = hitmax.astype(np.int32), header = img.header )
	#	outhitmax.write('hitmax.edf')
	#	outhitmax = fabio.edfimage.edfimage(data = diff.astype(np.int32), header = img.header )
	#	outhitmax.write('diff.edf')
	
	
	# Should we write the max proj and average as HDF5 files???
	#OutputFileName = "./MAX/" +str(fname)+"_cleanmax.h5"
	#OutputFile = h5py.File(OutputFileName,'w')
	#OutputFile.create_dataset("photon_energy_in_eV",data=input_photon_energy_in_eV)
	#OutputFile.create_dataset("data",data=img.data)
	#OutputFile.close()

	
#To go from 2048 spline to 1024
#import pyFAI.spline
#s=pyFAI.spline.Spline()
#s.read("distorsion.spline")
#s.bin(2)
#s.write("distorsion_1024.spline")
	
class MProcess(multiprocessing.Process):
    
    def __init__(self, task_queue,result_queue, IO, XSetup,HFParams, Frelon, DataCorr, ai):
      multiprocessing.Process.__init__(self)
      self.task_queue = task_queue
      self.result_queue = result_queue
      self.IO=IO
      self.XSetup=XSetup
      self.HFParams=HFParams
      self.Frelon=Frelon
      self.DataCorr=DataCorr
      self.ai=ai
      self.signal=True
      pub.subscribe(self.OnStop,'StopThreads')

    def run(self):
      proc_name = self.name
      while self.signal :
	  next_task = self.task_queue.get()
	  if next_task is None:
	      self.task_queue.task_done()
	      break
	  else: res=HitFinder(self.IO,self.XSetup,self.HFParams, self.Frelon,self.DataCorr, self.ai,next_task)
	  self.result_queue.put(res)
	  self.task_queue.task_done()
      return

    def OnStop(self):
        try : 
	   self.signal=False
        except: return

	

class main():

    def __init__(self,IO,XSetup,HFParams,doclean):
	self.t1=time.time()
        self.signal=True
	self.IO=IO
	self.XSetup=XSetup
	self.HFParams=HFParams
	self.Frelon=Frelon()
	self.DataCorr=Correction(1024)
	#self.BKG=Bkg()
	
	#Get all frames to process
	self.IO.fname_list=self.IO.get_all_frames()
	
	#Setup resolution for detector and correction:
	tmp=fabio.open(self.IO.fname_list[0])
	self.Frelon.set_resolution(tmp)
	self.DataCorr.resolution=self.Frelon.resolution[0]
	#tmp.close()
	
	self.ai=AI(self.XSetup,self.Frelon)
	#self.ai.test()
	#Chdir to the processing path
	os.chdir(self.IO.datadir)
	
	self.OutPutDirs()
	
	
	    
	if self.IO.ext == '.edf':
	  if not self.DataCorr.load_all():
	    print "Error with files needed for data correction. Aborted"
	    return
	
	
	pub.subscribe(self.OnStop,'StopThreads')
	
	self.SaveStatsStart()
	
	   
	self.StartMP()
	self.FindHits()
	#self.SaveStatsEnd()
	
    def OnStop(self):
        self.signal=False

    ###############################################
    def OutPutDirs(self):
        HDF5=glob.glob1(self.IO.procdir,"HDF5*")
	PICKLES=glob.glob1(self.IO.procdir,"PICKLES*")
	EDF=glob.glob1(self.IO.procdir,"EDF*")
	self.num = str(max(len(HDF5),len(PICKLES),len(EDF))+1)
	#print self.num
        if self.IO.H5:
	  H5Dir="HDF5_%s" %self.num.zfill(3)
	  os.mkdir(os.path.join(self.IO.procdir,H5Dir))
	  self.IO.H5Dir=H5Dir
        if self.IO.pickle:
	  Dir="PICKLES_%s" %self.num.zfill(3)
	  os.mkdir(os.path.join(self.IO.procdir,Dir))
	  self.IO.PicklesDir=Dir
	        
	if self.IO.edf:
	  Dir="EDF_%s" %self.num.zfill(3)
	  os.mkdir(os.path.join(self.IO.procdir,Dir))
	  self.IO.EDFDir=Dir

    ###############################################	
    def SaveStatsStart(self):	
	stat=open(os.path.join(self.IO.procdir,'stats_%s.dat'%self.num.zfill(3)),'w')
	now=datetime.datetime.now()
	print >> stat, "Job started on: %s\n" %now
	print >> stat, "Job performed in directory: %s" %self.IO.procdir
	print >> stat, "Data from : %s" %self.IO.datadir
	print >> stat, "Files: %s" %self.IO.root
	print >> stat, "Threshold: %s" %self.HFParams.threshold
	#print >> stat, "Bkg correction: %s" %self.HFParams.DoDarkCorr
	#if self.HFParams.DoDarkCorr:
	#  print >> stat, "Bkg img: %s" %' '.join(self.IO.bname_list)
	#  print >> stat, "Number of bkg images used: %s" %self.HFParams.bkg
	print >> stat, "Beam X: %i" %self.XSetup.beam_x
	print >> stat, "Beam Y: %i" %self.XSetup.beam_y
	print >> stat, "Minimal number of peaks in frame: %i" %self.HFParams.npixels
	print >> stat, "Number of procs: %i" %self.HFParams.procs
        stat.close
 
    ###############################################	
    def StartMP(self):	
	""" Start as many processes as set by the user
	"""	
	self.tasks = multiprocessing.JoinableQueue()
	self.results= multiprocessing.Queue()
	
	self.consumers = [ MProcess(self.tasks,self.results,self.IO,self.XSetup,self.HFParams,self.Frelon,self.DataCorr,self.ai) for i in xrange(self.HFParams.procs) ]
	print len(self.consumers)
	for w in self.consumers:
          w.start()
     
    ###############################################
    def BkgCalc(self):
	""" Average the background and apply correction
	    Not used anymore
	"""
	
	print 'Starting Background Averaging and Correction'
	for bname in self.IO.bname_list :
		bkg=np.zeros(shape=self.Frelon.resolution)
		countbkg=fabio.getnum(bname)
		for i in range(countbkg,countbkg+self.HFParams.nbkg):
		    bname = "%s_%04d%s" %(self.IO.root,i,self.IO.ext)
		    try :
			img = fabio.open(bname)
		    except:
			print 'Warning : problem while opening file %s, file skiped '%bname
			continue
		    if img.data.shape == self.Frelon.resolution:
			bkg += img.data.astype(np.float32)
		    else : 
			print 'Warning : data shape problem for file %s, file skiped '%bname
			continue
		
		#Get the average bkg and apply a median filter
		bkg = bkg.astype(np.float32) / np.float(self.HFParams.nbkg)
		bkg = ndimage.filters.median_filter(bkg.astype(np.float32), 11)
		
		#Apply the dark, flatfield and distortion correction (as specified by the user) 	
		bkg = self.DataCorr.apply_correction(bkg,self.HFParams.DoDarkCorr,self.HFParams.DoFlatCorr,self.HFParams.DoDist)
		
		#Remove center of the frame
		bkg[self.XSetup.beam_y-15:self.XSetup.beam_y+15,self.XSetup.beam_x-15:self.XSetup.beam_x+15]=0
		bkg = fabio.edfimage.edfimage(data = bkg.astype(np.float32), header = img.header ) 
		integration=np.float(fabio.fabioimage.fabioimage.integrate_area(bkg,[50,50,250,250]))
		if integration not in self.BKG.scales:
		  
		  self.BKG.scales.append(integration)
		  self.BKG.data.append(bkg)
	
		print "Max, Min and Median of corrected bkg image: %i %i %i  " %(int(np.max(bkg.data)), int(np.min(bkg.data)), int(np.median(bkg.data)))
		print 'Bkg integration:',self.BKG.scales
		
	self.BKG.scales = np.array(self.BKG.scales)
	#print self.BKG.scales
    
    
    
    
    ###############################################
    def FindHits(self):
    	self.total=len(self.IO.fname_list)
	print '\n= Job progression = Hit rate =    Max   =   Min   = Median = #Peaks '
	self.hit=0
	self.nbfile=0
	self.peaks_all_frame=[]
	index=0
	for fname in self.IO.fname_list:
	  if self.signal:
		#self.tasks.put(HitFinder(self.IO,self.XSetup,self.HFParams,self.Frelon,self.DataCorr,self.ai,self.nbfile))
		self.tasks.put(self.nbfile)
		self.nbfile +=1
		
		if self.total / 10 == self.nbfile:
		   	hit, imgmax, imgmin, imgmed, index,  peaks, fname, working = self.results.get()   
	  		self.hit += hit
			percent = (float(index)/(self.total))*100.
	  		hitrate= (float(self.hit)/float(index+1))*100.
	  		print '     %6.2f %%       %5.1f %%    %8.2f    %7.2f  %6.2f %4d   \r'%(percent,hitrate,imgmax,imgmin,imgmed,len(peaks)),#while True:
	  		sys.stdout.flush()
		
		#	    OutputFileName =os.path.join(self.IO.procdir,self.IO.H5Dir, os.path.splitext(str(fname))[0]+".h5")
		#	    pub.sendMessage('Hit',filename=OutputFileName,peaks=peaks)
		#	
		#     	self.peaks_all_frame.append([len(peaks),fname])
	        #	pub.sendMessage('Progress',percent=percent, hitrate=hitrate)
			
 		     	
		#except: break
	  else:break	
	for i in xrange(self.HFParams.procs+1):
	  self.tasks.put(None)
        while True:
	  hit, imgmax, imgmin, imgmed, index,  peaks, fname, working = self.results.get()   
	  self.hit += hit
	  percent = (float(index)/(self.total))*100.
	  hitrate= (float(self.hit)/float(index+1))*100.
	  if index % 10 == 1: print '     %6.2f %%       %5.1f %%    %8.2f    %7.2f  %6.2f %4d  (%i out of %i images) \r'%(percent,hitrate,imgmax,imgmin,imgmed,len(peaks), index, self.total),#while True:
	  sys.stdout.flush()
	  if index == self.total -1 : 
	    break
	
	
#while index != self.total -1:
#	    if self.signal:
#	     try:
#	             	hit, imgmax, imgmin, imgmed, index,  peaks, fname, working = self.results.get(block=True, timeout=0.1)
#			self.hit = self.hit + hit
#			if hit == 1: 
#			    
#			    OutputFileName =os.path.join(self.IO.procdir,self.IO.H5Dir, os.path.splitext(str(fname))[0]+".h5")
#			    pub.sendMessage('Hit',filename=OutputFileName)
#			
#		     	self.peaks_all_frame.append([len(peaks),fname])
#	                percent = (float(index)/(self.total))*100.
#			hitrate= (float(self.hit)/float(index+1))*100.
#			print '     %6.2f %%       %5.1f %%    %8.2f    %7.2f  %6.2f %4d   \r'%(percent,hitrate,imgmax,imgmin,imgmed,len(peaks)),
#	             	sys.stdout.flush()
#			pub.sendMessage('Progress',percent=percent, hitrate=hitrate)
#			
# 		     	
#	     except: pass
#		     
#	    else: break    
	#print 'Job progression... %5.1f %% --- Current hit-rate... %5.1f %% \r'%((float(res[6])/(total))*100.,((float(hit)/(total))*100.)),    		
	#sys.stdout.flush()
	
	
	
	#self.peaks_all_frame_sorted=sorted(self.peaks_all_frame, key=lambda x:x[0], reverse=True)
	#best=open(self.IO.procdir+"/best.lst","w")
	#for i in range(0,500):
	#   try: print >> best, 'HDF5'+self.peaks_all_frame_sorted[i][1]+'.h5'	    
	#   
	#   except IndexError: break
	#   
	#   else: pass
	
				
	#Move the different files into the MAX folder
	#c=''
	#for f in ['max_proj','hitmax','diff']:
	#    if self.correct== True: c='_corrected'
	#    image_name=f+c+'.edf'
	#    shutil.move(image_name,'MAX/'+self.root+'_'+image_name)
	
	print 'Overall, found %s hits in %s files --> %5.1f %% hit rate with a threshold of %s'%(self.hit,self.total,((float(self.hit)/(self.total))*100.),self.HFParams.threshold)
	print ""
	pub.sendMessage('Done')
	self.t2=time.time()
	print "It took %4.2f seconds to deal with %i images (i.e %4.2f images per second)" %((self.t2-self.t1),len(self.IO.fname_list),float(len(self.IO.fname_list)/(self.t2-self.t1)))
	
    def SaveStatsEnd(self):	
	stat=open('stats.dat','a')
	now=datetime.datetime.now()
	print >> stat, "Job finished on: %s\n" %now	
	stat.close()

        

        
	
#===================================================================================================================	
def presenter():
	print """                                 THIS IS THE HIT FINDING MODULE OF"""
	print """            	 						        """
	print """              ()_() v0.99                                                   """
	print """  _   _       (o o)         _____           _       _____     _ _          """
	print """ | \ | |  ooO--`o'--Ooo    |  __ \         | |     / ____|   | | |         """
	print """ |  \| | __ _ _ __   ___   | |__) |__  __ _| | __ | |     ___| | |         """
	print """ | . ` |/ _` | '_ \ / _ \  |  ___/ _ \/ _` | |/ / | |    / _ \ | |         """
	print """ | |\  | (_| | | | | (_) | | |  |  __/ (_| |   <  | |___|  __/ | |         """
	print """ |_| \_|\__,_|_| |_|\___/  |_|   \___|\__,_|_|\_\  \_____\___|_|_|         """
	print """                           By Jacques-Ph. Colletier           """
	print """ """
	print """ 					"""														

#===================================================================================================================

########################################################################################		
## NOT WORKING
def dograph (cleanmax,cleanhit,diff,threshold,median):	
	
	print "thinking, not crashing....\n"
	title1 = 'Cleaned Maximum Projection - All'
	title2 = 'Cleaned Maximum Projection - Hits'
	title3 = 'Difference map'

	fig=plt.figure()
	ax1 = fig.add_subplot(131)
	ax1.imshow(cleanmax,vmin=median, vmax=threshold, cmap='jet')
	ax1.colorbar(orientation="horizontal",fraction=0.07)
	ax1.set_title('%s' %title1,fontsize=12)

	ax2 = fig.add_subplot(132)
	ax2.imshow(cleanhit, vmin=median, vmax=threshold, cmap='jet')
	ax2.colorbar(orientation="horizontal",fraction=0.07)
	ax2.set_title('%s' %title2,fontsize=12)
	
	ax3 = fig.add_subplot(133)
	ax3.imshow(diff,vmin=median, vmax=threshold, cmap='jet')
	ax3.colorbar(orientation="horizontal",fraction=0.07)
	ax3.set_title('%s' %title3,fontsize=12)
	plt.show()# plot the shit...
	
########################################################################################		

############### FROM WEB
"""
Ported to Python from ImageJ's Background Subtractor.
Only works for 8-bit greyscale images currently.
Does not perform shrinking/enlarging for larger radius sizes.

Based on the concept of the rolling ball algorithm described
in Stanley Sternberg's article,
"Biomedical Image Processing", IEEE Computer, January 1983.

Imagine that the 2D grayscale image has a third (height) dimension by the image
value at every point in the image, creating a surface. A ball of given radius
is rolled over the bottom side of this surface; the hull of the volume
reachable by the ball is the background.

http://rsbweb.nih.gov/ij/developer/source/ij/plugin/filter/BackgroundSubtracter.java.html
"""


def smooth(array, window=3.0):
    """
    Applies a 3x3 mean filter to specified array.
    """
    dx, dy = array.shape
    new_array = np.copy(array)
    edgex = int(math.floor(window / 2.0))
    edgey = int(math.floor(window / 2.0))
    for i in range(dx):
        for j in range(dy):
            window_array = array[max(i - edgex, 0):min(i + edgex + 1, dx),
                                 max(j - edgey, 0):min(j + edgey + 1, dy)]
            new_array[i, j] = window_array.mean()
    return new_array


def rolling_ball_background(array, radius, light_background=True,
                            smoothing=True):
    """
    Calculates and subtracts background from array.

    Arguments:
    array - uint8 np array representing image
    radius - radius of the rolling ball creating the background
    light_background - Does image have light background
    smoothing - Whether the image should be smoothed before creating the
                background.
    """
    invert = False
    if light_background:
        invert = True

    ball = RollingBall(radius)
    float_array = array
    float_array = rolling_ball_float_background(float_array, radius, invert,
                                                smoothing, ball)
    background_pixels = float_array.flatten()

    if invert:
        offset = 255.5
    else:
        offset = 0.5
    pixels = np.int8(array.flatten())

    for p in range(len(pixels)):
        value = (pixels[p] & 0xff) - (background_pixels[p] + 255) + offset
        if value < 0:
            value = 0
        if value > 255:
            value = 255

        pixels[p] = np.int8(value)

    return np.reshape(pixels, array.shape)


def rolling_ball_float_background(float_array, radius, invert, smoothing,
                                  ball):
    """
    Create background for a float image by rolling a ball over the image
    """
    pixels = float_array.flatten()
    shrink = ball.shrink_factor > 1

    if invert:
        for i in range(len(pixels)):
            pixels[i] = -pixels[i]

    if smoothing:
        smoothed_pixels = smooth(np.reshape(pixels, float_array.shape))
        pixels = smoothed_pixels.flatten()

    pixels = roll_ball(ball, np.reshape(pixels, float_array.shape))

    if invert:
        for i in range(len(pixels)):
            pixels[i] = -pixels[i]
    return np.reshape(pixels, float_array.shape)


def roll_ball(ball, array):
    """
    Rolls a filtering object over an image in order to find the
    image's smooth continuous background.  For the purpose of explaining this
    algorithm, imagine that the 2D grayscale image has a third (height)
    dimension defined by the intensity value at every point in the image.  The
    center of the filtering object, a patch from the top of a sphere having
    radius 'radius', is moved along each scan line of the image so that the
    patch is tangent to the image at one or more points with every other point
    on the patch below the corresponding (x,y) point of the image.  Any point
    either on or below the patch during this process is considered part of the
    background.
    """
    height, width = array.shape
    pixels = np.float32(array.flatten())
    z_ball = ball.data
    ball_width = ball.width
    radius = ball_width / 2
    cache = np.zeros(width * ball_width)

    for y in range(-radius, height + radius):
        next_line_to_write_in_cache = (y + radius) % ball_width
        next_line_to_read = y + radius
        if next_line_to_read < height:
            src = next_line_to_read * width
            dest = next_line_to_write_in_cache * width
            cache[dest:dest + width] = pixels[src:src + width]
            p = next_line_to_read * width
            for x in range(width):
                pixels[p] = -float('inf')
                p += 1
        y_0 = y - radius
        if y_0 < 0:
            y_0 = 0
        y_ball_0 = y_0 - y + radius
        y_end = y + radius
        if y_end >= height:
            y_end = height - 1
        for x in range(-radius, width + radius):
            z = float('inf')
            x_0 = x - radius
            if x_0 < 0:
                x_0 = 0
            x_ball_0 = x_0 - x + radius
            x_end = x + radius
            if x_end >= width:
                x_end = width - 1
            y_ball = y_ball_0
            for yp in range(y_0, y_end + 1):
                cache_pointer = (yp % ball_width) * width + x_0
                bp = x_ball_0 + y_ball * ball_width
                for xp in range(x_0, x_end + 1):
                    z_reduced = cache[cache_pointer] - z_ball[bp]
                    if z > z_reduced:
                        z = z_reduced
                    cache_pointer += 1
                    bp += 1
                y_ball += 1

            y_ball = y_ball_0
            for yp in range(y_0, y_end + 1):
                p = x_0 + yp * width
                bp = x_ball_0 + y_ball * ball_width
                for xp in range(x_0, x_end + 1):
                    z_min = z + z_ball[bp]
                    if pixels[p] < z_min:
                        pixels[p] = z_min
                    p += 1
                    bp += 1
                y_ball += 1

    return np.reshape(pixels, array.shape)


class RollingBall(object):
    """
    A rolling ball (or actually a square part thereof).
    """
    def __init__(self, radius):
        if radius <= 10:
            self.shrink_factor = 1
            arc_trim_per = 24
        elif radius <= 30:
            self.shrink_factor = 2
            arc_trim_per = 24
        elif radius <= 100:
            self.shrink_factor = 4
            arc_trim_per = 32
        else:
            self.shrink_factor = 8
            arc_trim_per = 40
        self.build(radius, arc_trim_per)

    def build(self, ball_radius, arc_trim_per):
        small_ball_radius = ball_radius / self.shrink_factor
        if small_ball_radius < 1:
            small_ball_radius = 1
        rsquare = small_ball_radius * small_ball_radius
        xtrim = int(arc_trim_per * small_ball_radius) / 100
        half_width = int(round(small_ball_radius - xtrim))
        self.width = (2 * half_width) + 1
        self.data = [0.0] * (self.width * self.width)

        p = 0
        for y in range(self.width):
            for x in range(self.width):
                xval = x - half_width
                yval = y - half_width
                temp = rsquare - (xval * xval) - (yval * yval)

                if temp > 0:
                    self.data[p] = float(math.sqrt(temp))
                p += 1




def cleanup(path, erase):
        
	for d in ['MAX','HDF5']:
	        path2=os.path.join(path,d)
		if os.path.exists(path2) and erase==True:
		        shutil.rmtree(path2)
	        os.mkdir(path2)

#################	
if __name__ == '__main__':
	#pass
	argv = sys.argv[1:]
	HitFinderParser=optparse.OptionParser(description="This is the hit finding module of NanoPeakCell")
	HitFinderParser.add_option('-r','--root' ,dest='root', metavar='<image root name>', help='Root name of the images')
	HitFinderParser.add_option('-t','--threshold',dest='threshold', nargs=1, type=int, metavar='<value>', help='Peak threshold')
	HitFinderParser.add_option('-n','--num-bkg',dest='testset', metavar='<testset>', nargs=1, default=1, help='Number of frame for background substraction')
	HitFinderParser.add_option('-c','--correct',action='store_true',default=True, help='Apply background correction for each frame')
	HitFinderParser.add_option('-x','--beamX',dest='beamx',metavar='<value>',nargs=1,type=int, help='X position of beam (pixel)')
	HitFinderParser.add_option('-y','--beamY',dest='beamy',metavar='<value>',nargs=1,type=int, help='Y position of beam (pixel)')
	HitFinderParser.add_option('-b',nargs='+',help='Frames used for background correction')
	HitFinderParser.add_option('-j','--jobs'  ,dest='procs', nargs=1, type=int, metavar='<value>', default=1,help='Number of processors used (default = 1)')
	HitFinderParser.add_option('-p','--peaks'  ,dest='peaks', nargs=1, type=int, metavar='<value>', default=20,help='Minimal number of peaks in a frame (default = 20)')
	HitFinderParser.add_option('--debug' ,action='store_true',help='Used only for debugging')
	
	(options,args)=HitFinderParser.parse_args(argv)
        
	t1=time.time()
	IO=IO()
	X=XSetup()
	HF=HFParams()
	presenter()
	start=10770
        #for i in range(0,1):
        #num=start+i*10
	IO.datadir='/Volumes/verlaine/LYS_ID13/BEFORE_LS2253/edf_sorted/edf/'#os.getcwd()
	os.chdir(IO.datadir)
        IO.procdir='/Users/Nico'
	IO.root='lys2_3'
	XSetup.wavelength=0.954
	#Lys2
	XSetup.beam_x=545
	XSetup.beam_y=504
	#Mount5
	#XSetup.beam_x=518
	#XSetup.beam_y=504
	XSetup.distance=106.37
        HFParams.threshold=50
	HFParams.npixels=20
	HFParams.DoPeakSearch=True
	print "============================================\n" 
   	print "Now Hit Finding in %s" %IO.datadir
	main(IO,XSetup,HFParams,True)
	print "Finished  Hit Finding in %s\n" %IO.datadir
	print "============================================\n" 
	#else  :
        #  print "Scan not finished... Waiting up"
        #  time.sleep(60)
	t2=time.time()
	
    

