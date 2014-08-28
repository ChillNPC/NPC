#!/Library/Frameworks/Python.framework/Versions/Current/bin/python
##Cbf Pilatus 16 bits.
import os, fabio, h5py
import numpy as np
#from wx.lib.pubsub import Publisher as pub
from wx.lib.pubsub import pub
import pyFAI, pyFAI.distortion, pyFAI.detectors, pyFAI._distortion

try:
 from xfel.cxi.cspad_ana.cspad_tbx import dpack
 from xfel.command_line.cxi_image2pickle import crop_image_pickle#, evt_timestamp
 from libtbx import easy_pickle
 from scitbx.array_family import flex
except ImportError:
    pass



    
def HitFinder(IO,XSetup,HFParams,Frelon,DataCorr,BKG,index):
      
      hit=0
      fname=IO.fname_list[index]
      try :
		img = fabio.open(fname)
      except:
		print 'Warning : problem while opening file %s, file skiped '%fname
		return
		
      if img.data.shape == Frelon.resolution:
		#if HFParams.DoBkgCorr:
			 
			 # Substract dark image
			 #Substracting the dark and dividing by the flatfield
			 #img.data=(img.data.astype(np.float32) - Params.dark)/flatfield
			 #Correction of the distortion
			 #img.data=dist.correct(img.data)
			 
		#Apply the dark, flatfield and distortion correction (as specified by the user)
		img.data=DataCorr.apply_correction(img.data,HFParams.DoDarkCorr,HFParams.DoFlatCorr,HFParams.DoDist)
			 
		#Remove beam stop area (i.e = 0)
		img.data[XSetup.beam_y-15:XSetup.beam_y+15,XSetup.beam_x-15:XSetup.beam_x+15]=0
			 
		if HFParams.DoBkgCorr:
		
			 #Image integration  
			 scaleimg = fabio.fabioimage.fabioimage.integrate_area(img,[50,50,250,250]) 
			
			 #Difference between all bkg img and current img
			 scalesdiff = BKG.scales - np.float(scaleimg)
                         #Get the correct bkg img id
			 minid = np.where(np.abs(scalesdiff)<=np.min(np.abs(scalesdiff)))[0]
			
			 #Calculating scaling factor
			 scale = scaleimg / BKG.scales[minid]
			 
			 # Calculating bkg corrected img
			 working = img.data.astype(np.float32) -  scale * BKG.data[minid].data.astype(np.float32)
			 #working = img.data.astype(np.float32)
			 #Do max proj - Not used in current script
			 #maxids = np.where(working>self.param.max_proj)
			 #self.param.max_proj[maxids] = working[maxids]
			 imgmax,imgmin,imgmed,imgscalebkg, imgtypebkg= np.max(working), np.min(working), np.median(working), scale, minid[0]
		else:
			 working=img.data.astype(np.float32)
			 
			 #Get ids of negative peaks
			 #negids = np.where(working<0)
			 #Setting these neg valus to 0
			 #working[negids]=0
			 
			 # Setting these neg value to 0
			 imgmax,imgmin,imgmed,imgscalebkg, imgtypebkg= np.max(working), np.min(working), np.median(working), 0, 0
			 
		# Get Max, min, med, scaling factor, and bkg matching frame id of current frame
		#imgmax,imgmin,imgmed,imgscalebkg, imgtypebkg= np.max(working), np.min(working), np.median(working), scale, minid[0]
			 
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
				   #OutputFileName =os.path.join(IO.procdir, "%s.pickle" %root)
			 	   OutputFileName =os.path.join(IO.procdir, IO.PicklesDir , "%s.pickle" %root)
				   easy_pickle.dump(OutputFileName,data)
				 
				       
				 
				 
		else: working =0	 

					
      else:
			print 'Warning : data shape problem for file %s, file skiped '%fname
			#continue  
	
      return [hit,imgmax,imgmin,imgmed,imgscalebkg, imgtypebkg,index,len(peaks),fname,working]
    
