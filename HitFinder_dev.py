#!/Library/Frameworks/Python.framework/Versions/Current/bin/python
##Cbf Pilatus 16 bits.
import os, fabio, h5py
import numpy as np
#from wx.lib.pubsub import Publisher as pub
from wx.lib.pubsub import pub
import pyFAI, pyFAI.distortion, pyFAI.detectors, pyFAI._distortion
from scipy.ndimage.filters import gaussian_filter
import peakfind as pf

try:
 from xfel.cxi.cspad_ana.cspad_tbx import dpack
 from xfel.command_line.cxi_image2pickle import crop_image_pickle#, evt_timestamp
 from libtbx import easy_pickle
 from scitbx.array_family import flex
except ImportError:
    pass



        
def HitFinder(IO,XSetup,HFParams,Frelon,DataCorr,AI,index):
      
      hit=0
      fname=IO.fname_list[index]
      peaks=[]
      peakslist=[]
      try :
		img = fabio.open(fname)
      except:
		print 'Warning : problem while opening file %s, file skiped '%fname
		return
      if img.data.shape == Frelon.resolution:
		
		#Apply the dark, flatfield and distortion correction (as specified by the user)
		img.data=DataCorr.apply_correction(img.data,HFParams.DoDarkCorr,HFParams.DoFlatCorr,HFParams.DoDist)
			 
		#Remove beam stop area (i.e = 0)
		extend=15
			 
		#BkgCorr with pyFAI Azimuthal Integrator
		working=AI.ai.separate(img.data,npt_rad=1024, npt_azim=512, unit="2th_deg",percentile=50, mask=AI.mask,restore_mask=False)[0]
		
		imgmax,imgmin,imgmed = np.max(working), np.min(working), np.median(working)
		working[XSetup.beam_y-extend:XSetup.beam_y+extend,XSetup.beam_x-extend:XSetup.beam_x+extend]=0
			 
		# Get number of peaks above threshold in the current frame
		cropped=working[20:Frelon.resolution[1]-20,20:Frelon.resolution[1]-20]
		#print cropped.shape
		peaks=cropped[np.where(cropped>float(HFParams.threshold))]
		#peaks=working[np.where(working[20:Frelon.resolution[1]-20][20:Frelon.resolution[0]-20]>float(HFParams.threshold))]
		#peaks=working[np.where(working>float(HFParams.threshold))]# If enough peaks in current frame - This is a hit - Save it !!
			 
		if len(peaks) >= HFParams.npixels:
			hit = 1
			root=os.path.basename(fname)
			root=os.path.splitext(root)[0]
			
			
			if HFParams.DoPeakSearch:
			    
			    local_max=pf.find_local_max(working[0:1023,0:1004].astype(np.float),d_rad=1,threshold=HFParams.threshold)
			    peakslist=np.array(pf.subpixel_centroid(working[0:1023,0:1004],local_max,3))
	
			    
			if IO.edf:
			    OutputFileName =os.path.join(IO.procdir, IO.EDFDir,"%s.edf" %root)
			    img.data = working
			    img.write(OutputFileName)
			    
			
			#Conversion to H5
			if IO.H5:
			    
			    OutputFileName =os.path.join(IO.procdir, IO.H5Dir,"%s.h5" %root)
			    #OutputFileName =os.path.join(IO.procdir, "HDF5/%s.h5" %root)
			    OutputFile = h5py.File(OutputFileName,'w')
			    working[0:1023,1004:1023]=0
			    OutputFile.create_dataset("data",data=working.astype(np.int32))
			    if HFParams.DoPeakSearch:
			     g1=OutputFile.create_group("processing")
                             g2=g1.create_group("hitfinder")
                             g2.create_dataset("peakinfo",data=peakslist.astype(np.int32))
			    OutputFile.close()
				 
			#if conversion to Pickle
			if IO.pickle:
				   pixels=flex.int(working.astype(np.int32))
				   pixel_size=Frelon.pixel_size
				   data = dpack(data=pixels,
				                distance=XSetup.distance,
					        pixel_size=pixel_size,
					        wavelength=XSetup.wavelength,
					        beam_center_x=XSetup.beam_y*pixel_size,
						beam_center_y=XSetup.beam_x*pixel_size,
						ccd_image_saturation=Frelon.overload,
						saturated_value=Frelon.overload)
				   data=crop_image_pickle(data)
				   OutputFileName =os.path.join(IO.procdir, IO.PicklesDir , "%s.pickle" %root)
				   easy_pickle.dump(OutputFileName,data)
				 
		else: working =0	 

					
      else:
			print 'Warning : data shape problem for file %s, file skiped '%fname
			#continue  
	
      return [hit,imgmax,imgmin,imgmed,index,peakslist,fname,working]
    
