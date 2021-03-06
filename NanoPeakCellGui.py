#!/Library/Frameworks/Python.framework/Versions/Current/bin/python

#Relies on wx, matplotlib, scipy, numpy
import wx 
import os, glob, sys, imp
try:
   from wx.lib.pubsub import pub
except: from wx.lib.pubsub import pub

import numpy as np
from matplotlib import use as mpl_use
mpl_use('WXAgg')
from matplotlib.patches import Circle
from matplotlib.figure import Figure
import matplotlib.font_manager as fm
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigCanvas, NavigationToolbar2WxAgg as NavigationToolbar
from matplotlib.ticker import MaxNLocator
from threading import Thread
import NanoPeakCell_dev as Hit
import wx.lib.buttons as buttons
import fabio, pyFAI, pyFAI.distortion, pyFAI.detectors
import peakfind as pf
import mynormalize
import matplotlib.pyplot as plt
import matplotlib

# These imports will make sure the user will only be able to select outputs its system can save
# TODO: Warning: Please install or source blabla to be able to export images in X format
try : 
    imp.find_module('h5py')
    H5=True
    import h5py
    
except ImportError:
    H5=False

try : 
    imp.find_module('xfel')
    cctbx=True
except ImportError:
    cctbx=False

cwd=os.getcwd()

def NPCVar():
    import os
    return os.environ['NPC']

		        


class XSetup():
    """ This class stores the exprimental parameters of the experiment.
    """
    wavelength=0.832
    distance=100.626
    beam_x=521.9095
    beam_y=516.923
    
class HFParams():
    """This class stores the parameters used in the Hit Finding procedure
       NB: Image correction should have their own class
    """
    threshold=40
    DoBkgCorr=True
    DoDarkCorr=True
    DoFlatCorr=True
    DoDist=True
    DoPeakSearch=True
    npixels=20
    nbkg=1
    bkg=1
    procs=1

class IO():   
    """ This class instantiates all directoriess and filenames (input/output)
        Also creates filename list
    """
    def __init__(self):
      self.ext=".edf"
      self.root=None
      #self.bkg=[]
      self.datadir=None
      self.procdir=None
      self.pickle=True
      self.H5=True
      self.edf=True
      self.bname_list = []
      self.fname_list=[]
      
    def get_all_frames(self):
        s="%s*%s"%(self.root,self.ext)
	return glob.glob(s)
	
    
    #def get_bkg(self):
    #    
#	try:self.bkg=self.bkg.split(',')
#	except: self.bkg=self.bkg
#	for img in self.bkg:
	   
	   
#	   img=str(img)
#	   if len(img) <= 3:
#	       self.bname_list.append(self.root+'_%s'%img.zfill(4)+self.ext)
#	   else: self.bname_list.append(self.root+'_%s'%img+self.ext)
#	#return self.bname_list
	
	
class HitView(wx.Panel):
    """
    """
    #----------------------------------------------------------------------
    def __init__(self, parent,log):
	wx.Panel.__init__(self, parent, id=wx.ID_ANY)
	self.mainframe=parent
	self.CreateMainPanel()
	self.path=cwd
	self.targetfile=""
	pub.subscribe(self.OnDone,'Done')
	
    
    #----------------------------------------------------------------------
    def OnDone(self):
	self.HitFinder.SetValue(False)

    
    #----------------------------------------------------------------------
    def CreateMainPanel(self):
   
	font1=wx.Font(11,wx.MODERN, wx.NORMAL, wx.NORMAL, False,'MS Shell Dlg 2')
	font2=wx.Font(10,wx.MODERN, wx.NORMAL, wx.NORMAL, False,'MS Shell Dlg 2')
	
	flags = flags_L = wx.ALIGN_LEFT | wx.ALL | wx.ALIGN_CENTER_VERTICAL
	flags_R = wx.ALIGN_RIGHT | wx.ALL | wx.ALIGN_CENTER_VERTICAL 
	proportion = 0
	TextCtrlSize = 75
	width=100
	#----------------------------------------------------------------------
	FrameSel=wx.StaticBox(self, 1, "Images selection", size=(width,100))	
	
	#Select the directory containing the frames
	sizer_dir=wx.BoxSizer(wx.HORIZONTAL)
	sizer_dir.AddSpacer(5)
	Dir=wx.StaticText(self,-1,"Directory   ")
	Dir.SetFont(font1)
	self.Dir=wx.TextCtrl(self,-1,"/Users/Nico/",size=(120,20))
	self.Dir.SetFont(font1)
	self.Browse=wx.Button(self,-1,"Browse",size=(75,-1))
	self.Browse.SetFont(font1)
	sizer_dir.Add(Dir,proportion, border =2,flag=flags_L)
	sizer_dir.Add(self.Dir,proportion, border =4,flag=flags_L)
	sizer_dir.AddSpacer(5)
	sizer_dir.Add(self.Browse,proportion, border =4,flag=flags_L)
	sizer_dir.AddSpacer(5)
	
	#Select dset (root name)
	sizer_dset=wx.BoxSizer(wx.HORIZONTAL)
	sizer_dset.AddSpacer(5)
	Dset=wx.StaticText(self, -1,"Dataset    ")
	Dset.SetFont(font1)
	self.Dset=wx.TextCtrl(self,-1,"lys2_3",size=(120,20))
	self.Dset.SetFont(font1)
	sizer_dset.Add(Dset,proportion, border =2,flag=flags_L)
	sizer_dset.AddSpacer(5)
	sizer_dset.Add(self.Dset,proportion, border =4,flag=flags_L)
	sizer_dset.AddSpacer(5)
	
	#Select procdir
	sizer_procdir=wx.BoxSizer(wx.HORIZONTAL)
	sizer_procdir.AddSpacer(5)
	ProcDir=wx.StaticText(self, -1,"OutPut Dir")
	ProcDir.SetFont(font1)
	self.PDir=wx.TextCtrl(self,-1,"/Users/Nico/prog/NPC",size=(120,20))
	self.PDir.SetFont(font1)
	self.Browse2=wx.Button(self,-1,"Browse",size=(75,-1))
	self.Browse2.SetFont(font1)
	sizer_procdir.Add(ProcDir,proportion, border =2,flag=flags_L)
	sizer_procdir.AddSpacer(5)
	sizer_procdir.Add(self.PDir,proportion, border =4,flag=flags_L)
	sizer_procdir.AddSpacer(5)
	sizer_procdir.Add(self.Browse2,proportion, border =4,flag=flags_L)
	sizer_procdir.AddSpacer(5)
	
	#Select file extension
	sizer_ext=wx.BoxSizer(wx.HORIZONTAL)
	sizer_ext.AddSpacer(5)
	Ext=wx.StaticText(self, -1,"File extension")
	Ext.SetFont(font1)
	self.Ext=wx.TextCtrl(self,-1,".edf",size=(102,20))
	self.Ext.SetFont(font1)
	sizer_ext.Add(Ext,proportion, border =2,flag=flags_L)
	sizer_ext.AddSpacer(5)
	sizer_ext.Add(self.Ext,proportion, border =4,flag=flags_L)
	sizer_ext.AddSpacer(5)

	sizer_v =  wx.StaticBoxSizer(FrameSel, wx.VERTICAL)
	sizer_v.AddSpacer(5)
	sizer_v.Add(sizer_dir,proportion)
	sizer_v.AddSpacer(5)
	sizer_v.Add(sizer_dset,proportion)
	sizer_v.AddSpacer(5)
	sizer_v.Add(sizer_procdir,proportion)
	sizer_v.AddSpacer(5)
	sizer_v.Add(sizer_ext)
	
	#----------------------------------------------------------------------
	XPBox = wx.StaticBox(self, 1, "Experimental Setup", (width,100))	
	
	#Distance
	sizer_dist=wx.BoxSizer(wx.HORIZONTAL)
	sizer_dist.AddSpacer(5)
	dist=wx.StaticText(self, -1,"Distance (mm) ")
	self.dist=wx.TextCtrl(self,-1,"100.5",size=(50,20))
	self.dist.SetFont(font1)
	dist.SetFont(font1)
	sizer_dist.Add(dist,proportion, border =2,flag=flags_L)
	sizer_dist.AddSpacer(10)
	sizer_dist.Add(self.dist,proportion, border =2,flag=flags_L)
	
	#Wavelength
	sizer_wl=wx.BoxSizer(wx.HORIZONTAL)
	sizer_wl.AddSpacer(5)
	wl=wx.StaticText(self, -1,"Wavelength (A)")
	self.wl=wx.TextCtrl(self,-1,"0.954",size=(50,20))
	self.wl.SetFont(font1)
	wl.SetFont(font1)
	sizer_wl.Add(wl,proportion, border =2,flag=flags_L)
	sizer_wl.AddSpacer(10)
	sizer_wl.Add(self.wl,proportion, border =2,flag=flags_L)
	
	#Beam center
	sizer_beamcenter=wx.BoxSizer(wx.HORIZONTAL)
	sizer_beamcenter.AddSpacer(5)
	BCX=wx.StaticText(self, -1,"Beam Center   X")
	BCX.SetFont(font1)
	self.X=wx.TextCtrl(self,-1,"545",size=(50,20))
	self.X.SetFont(font1)
	BCY=wx.StaticText(self, -1," Y")
	BCY.SetFont(font1)
	self.Y=wx.TextCtrl(self,-1,"503",size=(50,20))
	self.Y.SetFont(font1)
	sizer_beamcenter.Add(BCX,proportion, border =2,flag=flags_L)
	sizer_beamcenter.AddSpacer(5)
	sizer_beamcenter.Add(self.X,proportion, border =2,flag=flags_L)
	sizer_beamcenter.Add(BCY,proportion, border =2,flag=flags_L)
	sizer_beamcenter.AddSpacer(5)
	sizer_beamcenter.Add(self.Y,proportion, border =2,flag=flags_L)
	
	#----------------------------------------------------------------------
	sizer_v0 =  wx.StaticBoxSizer(XPBox,wx.VERTICAL)
	sizer_v0.AddSpacer(5)
	sizer_v0.Add(sizer_dist,proportion)
	sizer_v0.AddSpacer(5)
	sizer_v0.Add(sizer_wl,proportion)
	sizer_v0.AddSpacer(5)
	sizer_v0.Add(sizer_beamcenter)
	#----------------------------------------------------------------------
	
	
	
	HitBox = wx.StaticBox(self, proportion, "HitFinder Parameters", size=(100,300))	
	
	
	#Threshold
	sizer_threshold=wx.BoxSizer(wx.HORIZONTAL)
	sizer_threshold.AddSpacer(5)
	Thresh=wx.StaticText(self, -1,"Threshold:           ")
	Thresh.SetFont(font1)
	self.Thresh=wx.TextCtrl(self,-1,"100",size=(40,20))
	self.Thresh.SetFont(font1)
	sizer_threshold.Add(Thresh,proportion, border =2,flag=flags_L)
	sizer_threshold.AddSpacer(37)
	sizer_threshold.Add(self.Thresh,proportion, border =2,flag=flags_L)
	
	
	#Min # of peaks
	sizer_peaks=wx.BoxSizer(wx.HORIZONTAL)
	sizer_peaks.AddSpacer(5)
	NP=wx.StaticText(self, -1,"Min number of pixels:   ")
	self.NP=wx.TextCtrl(self,-1,"50",size=(40,20))
	NP.SetFont(font1)
	self.NP.SetFont(font1)
	sizer_peaks.Add(NP,proportion, border =2,flag=flags_L)
	sizer_peaks.AddSpacer(5)
	sizer_peaks.Add(self.NP,proportion, border =2,flag=flags_L)
	
	#Number of procs
	sizer_cpus=wx.BoxSizer(wx.HORIZONTAL)
	sizer_cpus.AddSpacer(5)
	cpus=wx.StaticText(self, -1,"Number of cpus to use: ")
	self.cpus=wx.TextCtrl(self,-1,"2",size=(40,20))
	cpus.SetFont(font1)
	self.cpus.SetFont(font1)
	sizer_cpus.Add(cpus,proportion, border =2,flag=flags_L)
	sizer_cpus.AddSpacer(5)
	sizer_cpus.Add(self.cpus,proportion, border =2,flag=flags_L)
	
        #Find Bp position
	sizer_Bp=wx.BoxSizer(wx.HORIZONTAL)
	sizer_Bp.AddSpacer(5)
	Bp=wx.StaticText(self, -1,"Find Bragg peaks position")
	Bp.SetFont(font1)
	self.Bp=wx.CheckBox(self,-1)
        self.Bp.SetValue(True)
        self.Bp.SetFont(font1)
        sizer_Bp.Add(self.Bp,proportion, border =2,flag=flags_L)
	sizer_Bp.AddSpacer(5)
	sizer_Bp.Add(Bp,proportion, border =2,flag=flags_L)
	
	
	ImageCorrection = wx.StaticBox(self, proportion, "Image Correction and Output format(s)",size=(100,300))
        

	# Detector Correction
	sizer_det=wx.BoxSizer(wx.HORIZONTAL)
        sizer_det.AddSpacer(5)
        det=wx.StaticText(self, -1,"Detector Correction (flatfield-distortion)")
        det.SetFont(font1)
	self.det=wx.CheckBox(self,-1)
        self.det.SetValue(True)
        self.det.SetFont(font1)
        sizer_det.Add(self.det, proportion,border=2, flag=flags_L)
        sizer_det.AddSpacer(3)
	sizer_det.Add(det, proportion, border=2, flag=flags_L)
	# Bkg Correction
	#sizer_corr=wx.BoxSizer(wx.HORIZONTAL)
	#sizer_corr.AddSpacer(5)
	#corr=wx.StaticText(self, -1,"Background Substraction")
	#self.corr=wx.CheckBox(self,-1)
	#self.corr.SetFont(font1)
	#self.corr.SetValue(True)
	#corr.SetFont(font1)
	#sizer_corr.Add(self.corr,proportion, border =2,flag=flags_L)
	#sizer_corr.AddSpacer(3)
	#sizer_corr.Add(corr,proportion, border =2,flag=flags_L)
	
	# Select images 
	#sizer_bkg=wx.BoxSizer(wx.HORIZONTAL)
	#sizer_bkg.AddSpacer(5)
	#bkg=wx.StaticText(self, -1,"Background images:")
	#self.bkg=wx.TextCtrl(self,-1,"0",size=(140,20))
	#self.bkg.SetFont(font1)
	#bkg.SetFont(font1)
	#sizer_bkg.Add(bkg,proportion, border =2,flag=flags_L)
	#sizer_bkg.AddSpacer(3)
	#sizer_bkg.Add(self.bkg,proportion, border =2,flag=flags_L)
	
	#Testset
	#sizer_nbkg=wx.BoxSizer(wx.HORIZONTAL)
	#sizer_nbkg.AddSpacer(5)
	#nbkg=wx.StaticText(self, -1,"Number of images for bkg:")
	#self.nbkg=wx.TextCtrl(self,-1,"1",size=(40,20))
	#self.nbkg.SetFont(font1)
	#nbkg.SetFont(font1)
	#sizer_nbkg.Add(nbkg,proportion, border =2,flag=flags_L)
	#sizer_nbkg.AddSpacer(3)
	#sizer_nbkg.Add(self.nbkg,proportion, border =2,flag=flags_L)
	
	sizer_hit=wx.BoxSizer(wx.HORIZONTAL)
	self.HitFinder=wx.ToggleButton(self,-1,"Find Hits",size=(75,-1))
	self.HitFinder.SetFont(font1)
	#self.Stop=wx.Button(self,-1,"  Stop ",size=(75,-1))
	#self.Stop.SetFont(font1)
	
	sizer_hit.Add(self.HitFinder,proportion, border =2,flag=flags_L)
	#sizer_hit.AddSpacer(5)
	#sizer_hit.Add(self.Stop,proportion, border =2,flag=flags_L)
	
	
	
        sizer_format=wx.BoxSizer(wx.HORIZONTAL)
        FormatStatic=wx.StaticText(self, -1,"Convert files in :")
	FormatStatic.SetFont(font1)
        sizer_format.AddSpacer(5)
	sizer_format.Add(FormatStatic, proportion, border=2, flag=flags_L)

	sizer_pickle=wx.BoxSizer(wx.HORIZONTAL)
	sizer_pickle.AddSpacer(5)
	self.pickle=wx.CheckBox(self,-1)
	if cctbx == False:
	    self.pickle.Disable()

	else:
	    self.pickle.SetValue(True)
	
	picklestatic=wx.StaticText(self, -1,"cctbx.xfel pickle format")
	picklestatic.SetFont(font1)
	sizer_pickle.Add(self.pickle,proportion, border =2,flag=flags_L)
	sizer_pickle.Add(picklestatic,proportion, border =2,flag=flags_L)
	
	sizer_h5=wx.BoxSizer(wx.HORIZONTAL)
	sizer_h5.AddSpacer(5)
	self.h5=wx.CheckBox(self,-1)
	if H5 == False:
	    self.h5.Disable()

	else:
	    self.h5.SetValue(True)
	h5static=wx.StaticText(self,-1,"H5 Crystfel format")
        h5static.SetFont(font1)
        sizer_h5.Add(self.h5,proportion, border=2, flag=flags_L)
        sizer_h5.Add(h5static,proportion,border=2,flag=flags_L)

	sizer_edf=wx.BoxSizer(wx.HORIZONTAL)
        sizer_edf.AddSpacer(5)
	self.edf=wx.CheckBox(self,-1)
        self.edf.SetValue(False)
        edfstatic=wx.StaticText(self, -1,"edf file format")
        edfstatic.SetFont(font1)
        sizer_edf.Add(self.edf, proportion, border=2, flag=flags_L)
        sizer_edf.Add(edfstatic, proportion, border=2, flag=flags_L)

	sizer_v1 =  wx.StaticBoxSizer(HitBox, wx.VERTICAL)
	sizer_v1.Add(sizer_threshold)
	sizer_v1.Add(sizer_peaks)
	sizer_v1.Add(sizer_cpus)
	sizer_v1.Add(sizer_Bp)
	
	
	
	sizer_v2= wx.StaticBoxSizer(ImageCorrection, wx.VERTICAL)
	sizer_v2.Add(sizer_det)	
	#sizer_v2.Add(sizer_corr)
	sizer_v2.AddSpacer(10)	
	#sizer_v2.Add(sizer_bkg)	
	#sizer_v2.AddSpacer(3)
	#sizer_v2.Add(sizer_nbkg)
	#sizer_v2.AddSpacer(10)
	sizer_v2.Add(sizer_format)
	sizer_v2.Add(sizer_pickle)
	sizer_v2.AddSpacer(2)
	sizer_v2.Add(sizer_h5)
	sizer_v2.AddSpacer(2)
        sizer_v2.Add(sizer_edf)

        sizer_v3=wx.BoxSizer(wx.VERTICAL)               
        sizer_v3.Add(sizer_hit,proportion, border =4,flag=wx.ALIGN_CENTER)
	sizer_v3.AddSpacer(10)
	sizer_v3.AddSpacer(10)
	
	mainsizer=wx.BoxSizer(wx.VERTICAL)
	mainsizer.AddSpacer(5)
	mainsizer.Add(sizer_v, 0, wx.EXPAND)
	mainsizer.AddSpacer(10)	
	mainsizer.Add(sizer_v0, 0, wx.EXPAND)
	mainsizer.AddSpacer(10)	
	mainsizer.Add(sizer_v1, 0, wx.EXPAND)
	mainsizer.AddSpacer(10)
        mainsizer.Add(sizer_v2, 0, wx.EXPAND)
        mainsizer.AddSpacer(10)
	mainsizer.Add(sizer_v3, 0, wx.EXPAND)
	self.SetSizerAndFit(mainsizer)
	
	#self.Bind(wx.EVT_CHECKBOX, self.OnCorr, self.corr)
	self.Bind(wx.EVT_TOGGLEBUTTON,  self.OnToggle,self.HitFinder)
        #self.Bind(wx.EVT_BUTTON, self.OnStop, self.Stop)
        self.Bind(wx.EVT_BUTTON, self.GetDir, self.Browse)
	self.Bind(wx.EVT_BUTTON, self.GetDir2, self.Browse2)
	
        
    
    def OnStop(self):
       self.HitFinder.Enable()
       pub.sendMessage('StopThreads')
       
    def OnToggle(self,e):
        if self.HitFinder.GetValue(): self.FindHits() 
	else: self.OnStop()
	# To be modified to create the objects of the dev version
    def FindHits(self):
       
       # Getting IO params
       self.IO=IO()
       self.IO.datadir=self.Dir.GetValue()
       
       self.IO.procdir=self.PDir.GetValue()
       self.IO.root=self.Dset.GetValue()
       
       self.IO.pickle=self.pickle.GetValue()
       self.IO.H5=self.h5.GetValue()
       self.IO.edf=self.edf.GetValue()
       self.IO.ext=self.Ext.GetValue()
       # Getting XP setup
       self.XSetup=XSetup()
       self.XSetup.beam_x=int(self.X.GetValue())
       self.XSetup.beam_y=int(self.Y.GetValue())
       
       self.XSetup.distance=float(self.dist.GetValue())
       self.XSetup.wavelength=float(self.wl.GetValue())
       
       
       self.HFParams=HFParams()
       self.HFParams.threshold=int(self.Thresh.GetValue())
       self.HFParams.npixels=int(self.NP.GetValue())
       self.HFParams.procs=int(self.cpus.GetValue())
       self.HFParams.DoDarkCorr=self.det.GetValue()
       self.HFParams.DoFlatCorr=self.det.GetValue()
       self.HFParams.DoDistCorr=self.det.GetValue()
       self.HFParams.DoPeakSearch=self.Bp.GetValue()
       #self.HFParams.DoBkgCorr=self.corr.GetValue()
       #self.IO.bkg=self.bkg.GetValue()
       #if bkg=='' and c==True:
       #   print 'Please provide the frame number you chose as bkg image'
#	  return
       #self.HFParams.nbkg=int(self.nbkg.GetValue())
           
       try:self.ht=HitThread(self.IO, self.XSetup,self.HFParams)
       except: print "You did something wrong here..."
    
    def GetDir(self, event):
       dlg = wx.DirDialog(self, "Choose a directory", style=1,defaultPath=self.Dir.GetValue())
       if dlg.ShowModal() == wx.ID_OK:
                  self.path = dlg.GetPath()
		  os.chdir(self.path)
		  self.Dir.SetValue(self.path)
       dlg.Destroy()
    def GetDir2(self, event):
        dlg = wx.DirDialog(self, "Choose a directory", style=1,defaultPath=self.PDir.GetValue())
        if dlg.ShowModal() == wx.ID_OK:
                 path = dlg.GetPath()
                 #os.chdir(self.path)
                 self.PDir.SetValue(path)
        dlg.Destroy()

    def OnCorr(self,e):
        if self.corr.GetValue() == True:
	    self.bkg.Enable()
	    self.nbkg.Enable()
	if self.corr.GetValue() == False:
	    self.bkg.Disable()
	    self.nbkg.Disable()
	
class HitThread(Thread):
    
    def __init__(self,IO,XSetup,HFParams):
        Thread.__init__(self)
	#self.daemon=True
        self.IO=IO
	self.XSetup=XSetup
	self.HFParams=HFParams
	self.start()
        
	
    #----------------------------------------------------------------------
    def run(self):
        self.Hit=Hit.main(self.IO,self.XSetup,self.HFParams, True)


class RightPanel(wx.Panel):
    """
    """
    #----------------------------------------------------------------------
    def __init__(self, parent,log):
	wx.Panel.__init__(self, parent, id=wx.ID_ANY)
	self.mainframe=parent
	self.path=cwd
	self.log = log
	self.cmap_list=['hot',
                        'gray',
                        'YlorBr_r',
			'YlGnBu_r',
			'Blues',
                        'Reds',
			'Blues_r',
			'Reds_r']
	self.frame=self.mainframe.panel.frame
	pub.subscribe(self.OnProgress,'Progress')
	self.root=NPCVar()
	self.CreateMainPanel()
	pub.subscribe(self.UpdateSpin,'Update Spins')
	
	
	
    #----------------------------------------------------------------------
    def OnProgress(self,percent, hitrate):
        #value1, value2 = message.data
	self.progress.SetValue(int(percent))
	self.HitRate.SetValue(int(hitrate))
	wx.Yield()
    
    #----------------------------------------------------------------------
    def CreateMainPanel(self):
   
	font1=wx.Font(11,wx.MODERN, wx.NORMAL, wx.NORMAL, False,'MS Shell Dlg 2')
	font2=wx.Font(10,wx.MODERN, wx.NORMAL, wx.NORMAL, False,'MS Shell Dlg 2')
	flags = flags_L = wx.ALIGN_LEFT | wx.ALL | wx.ALIGN_CENTER_VERTICAL
	flags_R = wx.ALIGN_RIGHT | wx.ALL | wx.ALIGN_CENTER_VERTICAL 
	proportion = 0
	TextCtrlSize = 75
	
	SliderBox = wx.StaticBox(self, proportion, "Viewer Settings", size=(100,300))
	
	sizer_sliderboost=wx.BoxSizer(wx.HORIZONTAL)
	SliderStatic=wx.StaticText(self,-1,"Intensity Boost")
	SliderStatic.SetFont(font1)
	#self.sld_boost=wx.Slider(self,-1,1,1,100,wx.DefaultPosition,(100, 10),wx.SL_HORIZONTAL | wx.SL_LABELS)
	self.boost=wx.SpinCtrl(self,-1,'1',wx.DefaultPosition,(70,-1))
	self.boost.SetFont(font1)
	self.boost.SetValue(1)
	sizer_sliderboost.Add(SliderStatic,0, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
	sizer_sliderboost.Add(self.boost,1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
	
	sizer_slidermin=wx.BoxSizer(wx.HORIZONTAL)
	SliderStatic=wx.StaticText(self,-1,"Min Value")
	SliderStatic.SetFont(font1)
	self.min=wx.SpinCtrl(self,-1,'1',wx.DefaultPosition,(70,-1))
	self.min.SetValue(1)
	#wx.Slider(self,-1,0,0,50,wx.DefaultPosition, (250, 20), wx.SL_HORIZONTAL | wx.SL_LABELS)
	sizer_slidermin.Add(SliderStatic,0, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
	sizer_slidermin.AddSpacer(25)
	sizer_slidermin.Add(self.min,1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
	
	sizer_slidermax=wx.BoxSizer(wx.HORIZONTAL)
	SliderStaticMax=wx.StaticText(self,-1,"Max Value")
	SliderStaticMax.SetFont(font1)
	self.max=wx.SpinCtrl(self,-1,'1',wx.DefaultPosition,(70,-1))
	self.max.SetValue(10)
	sizer_slidermax.Add(SliderStaticMax,0, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
	sizer_slidermax.AddSpacer(25)
	sizer_slidermax.Add(self.max,1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
	
	sizer_cmap=wx.BoxSizer(wx.HORIZONTAL)
	CmapStatic=wx.StaticText(self,-1,"Colour Mapping:")
	self.cmap=wx.Choice(self,-1,choices=self.cmap_list)
	CmapStatic.SetFont(font1)
	self.cmap.SetFont(font1)
	self.cmap.SetStringSelection('Blues')
	sizer_cmap.Add(CmapStatic,0, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL,1)
	sizer_cmap.AddSpacer(10)
	sizer_cmap.Add(self.cmap,0, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL,1)
	
	sizer_show_peaks=wx.BoxSizer(wx.HORIZONTAL)
	self.ShowBragg=wx.CheckBox(self,-1)
	
	PeakStatic=wx.StaticText(self,-1,'Show Bragg Peaks')
	PeakStatic.SetFont(font1)
	
	sizer_show_peaks.Add(self.ShowBragg)
	sizer_show_peaks.Add(PeakStatic)
	
	self.figure = Figure((3, 0.8), dpi=100,facecolor='white')
	self.canvas = FigCanvas(self, -1, self.figure)
        self.axes=self.figure.add_axes([0.10, 0.30, 0.8, 0.5])
	self.axes.xaxis.label.set_size(10)
	self.figure.subplots_adjust(left=0,right=1,top=1,bottom=0)
	self.axes.tick_params(axis='both',which='major',labelsize=9)
	self.axes.get_xaxis().set_major_locator(MaxNLocator(integer=True))
	
	self.cbar0 = matplotlib.colorbar.ColorbarBase(self.axes, format="%3i", cmap=matplotlib.cm.Blues,
                                   norm=matplotlib.colors.Normalize(vmin=0, vmax=10),
                                   orientation='horizontal')
	self.cbar0.set_norm(mynormalize.MyNormalize(vmin=1,vmax=10,stretch='log'))
	self.cbar0.locator=MaxNLocator(integer=True,nbins=8)
        self.cbar = DraggableColorbar(self.cbar0,self.frame,self.boost)
        self.cbar.connect()
	self.cbar0.draw_all()
	self.canvas.draw()

	
	sizer_v2 =  wx.StaticBoxSizer(SliderBox, wx.VERTICAL)
	sizer_v2.AddSpacer(8)
	sizer_v2.Add(sizer_sliderboost,proportion,border =2,flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
	sizer_v2.AddSpacer(8)
	sizer_v2.Add(sizer_slidermin,proportion,border =2,flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
	sizer_v2.AddSpacer(8)
	sizer_v2.Add(sizer_slidermax,proportion,border =2,flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
	sizer_v2.AddSpacer(8)
	sizer_v2.Add(sizer_cmap,proportion,border =2,flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
	sizer_v2.AddSpacer(8)
	sizer_v2.Add(self.canvas,proportion,border =2,flag=wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTER_VERTICAL)
        sizer_v2.AddSpacer(8)
	sizer_v2.Add(sizer_show_peaks,proportion,border =2,flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
	
	
	filebox = wx.StaticBox(self, proportion, "Progreesion and results", size=(100,300))
	
	self.progress = wx.Gauge(self, -1, 100, size=(250, 25))
	self.HitRate=wx.Gauge(self, -1, 100, size=(250, 25))
	
	
	sizer_dir=wx.BoxSizer(wx.HORIZONTAL)
	sizer_dir.AddSpacer(5)
	Dir=wx.StaticText(self,-1,"Load results:")
	Dir.SetFont(font1)
	#self.Dir=wx.TextCtrl(self,-1,"",size=(120,20))
	#self.Dir.SetFont(font1)
	
	self.Browse=wx.Button(self,-1,"Browse",size=(75,-1))
	self.Browse.SetFont(font1)
	self.fname_list=[]
	self.filelist = wx.ListBox(self, -1, wx.DefaultPosition, (250, 300), self.fname_list, wx.LB_SINGLE | wx.LB_ALWAYS_SB)
	JP=wx.StaticText(self,-1,"Job Progression")
	JP.SetFont(font1)
	HR=wx.StaticText(self,-1,"Current Hit Rate")
	HR.SetFont(font1)
	
	sizer_dir.Add(Dir,proportion, border =2,flag=flags_L)
	#sizer_dir.Add(self.Dir,proportion, border =4,flag=flags_L)
	sizer_dir.AddSpacer(5)
	sizer_dir.Add(self.Browse,proportion, border =4,flag=flags_L)
	sizer_dir.AddSpacer(5)
	
	
	sizer_movie=wx.BoxSizer(wx.HORIZONTAL)
	img = wx.Bitmap(os.path.join(self.root,"bitmaps", "player_play.png"))
        self.playPauseBtn = buttons.GenBitmapToggleButton(self, bitmap=img, name="play")
        self.playPauseBtn.Enable(True)
        
        img = wx.Bitmap(os.path.join(self.root,"bitmaps", "player_pause.png"))
        self.playPauseBtn.SetBitmapSelected(img)
        self.playPauseBtn.SetInitialSize()
	
	self.FindBraggs=wx.Button(self,-1,"Find Braggs",size=(100,30))
	self.FindBraggs.SetFont(font1)
	sizer_movie.Add(self.playPauseBtn,proportion, border =2,flag=flags_L)
	sizer_movie.AddSpacer(5)
	sizer_movie.Add(self.FindBraggs,proportion, border =4,flag=flags_L)
	sizer_movie.AddSpacer(5)
	
	sizer_v1 =  wx.StaticBoxSizer(filebox, wx.VERTICAL)
	sizer_v1.Add(JP,proportion, border =4,flag=wx.ALIGN_LEFT)
	sizer_v1.Add(self.progress,proportion, border =4,flag=wx.ALIGN_CENTER)
	sizer_v1.AddSpacer(10)
	sizer_v1.Add(HR,proportion, border =4,flag=wx.ALIGN_LEFT)
	sizer_v1.Add(self.HitRate,proportion, border =4,flag=wx.ALIGN_CENTER)
	sizer_v1.AddSpacer(25)
	
	sizer_v1.Add(sizer_dir,proportion,border =0,flag=wx.ALL)
	sizer_v1.AddSpacer(10)
	sizer_v1.Add(self.filelist,proportion,border =0,flag=wx.ALIGN_CENTER)
	sizer_v1.AddSpacer(10)
	sizer_v1.Add(sizer_movie,proportion, border =4,flag=wx.ALIGN_CENTER)
	
	hbox = wx.BoxSizer(wx.VERTICAL)
	hbox.AddSpacer(5)
	hbox.Add(sizer_v2,proportion,border= 2,flag=flags_L | wx.EXPAND)
        hbox.Add(sizer_v1,proportion,border =2,flag=flags_L | wx.EXPAND)
        self.SetSizerAndFit(hbox)
	
	self.Bind(wx.EVT_BUTTON, self.GetDir, self.Browse)
    
    #----------------------------------------------------------------------
    def UpdateSpin(self, mini,maxi):
        self.min.SetValue(int(mini+0.5))
	self.max.SetValue(int(maxi+0.5))
    
    #----------------------------------------------------------------------
    def SetMax(self,Max):
        self.cbar0.set_clim(vmax=Max)
	self.cbar0.draw_all()
	self.canvas.draw()
    
    #----------------------------------------------------------------------
    def SetMin(self,Min):
        self.cbar0.set_clim(vmin=Min)
	self.cbar0.draw_all()
	self.canvas.draw()
    #----------------------------------------------------------------------
    def SetCmap(self,cmap):
        self.cbar0.set_cmap(cmap)
	#self.cmap=cmap
	self.cbar0.draw_all()
	self.canvas.draw()
    
    #----------------------------------------------------------------------
    def GetDir(self, event):
       dlg = wx.DirDialog(self, "Choose a directory", style=1,defaultPath=self.path)
       if dlg.ShowModal() == wx.ID_OK:
                  self.path = dlg.GetPath()
		  os.chdir(self.path)
		  self.UpdateFileList(self.path)
       dlg.Destroy()
       
    #----------------------------------------------------------------------
    def UpdateFileList(self,path):
        self.fname_list = glob.glob("*.h5")
	self.filelist.Set(self.fname_list)
        self.log.WriteText("Found %i H5 files in directory %s\n" %(len(self.fname_list),path))
    
class MyToolbar(NavigationToolbar):
   mess="\tx:    \ty:    \t\tIntensity:      "
   def __init__(self, plotCanvas):
        NavigationToolbar.__init__(self, plotCanvas)
	self.Stat=wx.StaticText(self,-1,self.mess)
        self.AddControl(self.Stat)
                         #  'Pan to the right', 'Pan graph to the right')
class PlotStats(wx.Panel):
    
    #----------------------------------------------------------------------
    def __init__( self, parent, log, pos=wx.DefaultPosition,size=wx.DefaultSize):
        wx.Panel.__init__(self,parent)
        self.parent=parent
	self.log = log
	self.prop = fm.FontProperties(size=10)
	self.boost=1
	self.vmin=0
	self.vmax=10
	self.cmap='Blues'
        self.CreateMainPanel()
	self.filename=''
        pub.subscribe(self.DisplayHit,'Hit')
	
	self.peaks=None
	self.Bragg=False
	
    #----------------------------------------------------------------------
    def CreateMainPanel(self):
        """ Creates the main panel with all the subplots:
        """
        # 6.2x6.2 inches, 100 dots-per-inch
        self.dpi = 100
        self.figure = Figure((6.4, 6.4), dpi=self.dpi,facecolor='white')
	self.canvas = FigCanvas(self, -1, self.figure)
        self.axes=self.figure.add_subplot(111)
	self.axes.axis('off')
	self.figure.subplots_adjust(left=0,right=1,top=1,bottom=0)
	self.dset=[]
	self.frame=self.axes.imshow(np.zeros((1024,1024)),vmin=0, vmax=100,cmap='Blues')
	self.w=ShowNumbers(self,-1,'')
	#self.toolbar = NavigationToolbar(self.canvas)
	self.toolbar = MyToolbar(self.canvas)
	 
	
	self.vbox1 = wx.BoxSizer(wx.VERTICAL)
        self.vbox1.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW | wx.EXPAND)
        self.vbox1.Add(self.toolbar, 0, wx.EXPAND)
        self.SetSizer(self.vbox1)
        self.vbox1.Fit(self)
        cid = self.figure.canvas.mpl_connect('motion_notify_event', self.onmove)   
        cid2 = self.figure.canvas.mpl_connect('button_press_event', self.onclick)   
	self.canvas.draw()
	
    #----------------------------------------------------------------------
    def onclick(self,event):
      if event.xdata != None and event.ydata != None and event.button == 2:
        x=event.xdata
	y=event.ydata
	s=''
	try:
	  for i in range(0,20):
	    s=s+'\n'+'' .join(['%5i' %member for member in self.dset[y-10:y+9,x-10+i] ]) 
	  self.w.Show()
	  self.w.text.SetLabel(s)
	  		
        except:pass
    
    
    #----------------------------------------------------------------------
    def onmove(self,event):
      if event.xdata != None and event.ydata != None:
        try:
	  self.toolbar.Stat.SetLabel("\tx:%4i\ty:%4i\t\tIntensity:%6i" %(int(event.xdata+0.5), int(event.ydata+0.5), self.dset[int(event.ydata+0.5),int(event.xdata+0.5)]))
	  self.canvas.draw()
        except: pass
    
    
    
    #----------------------------------------------------------------------
    def DisplayHit(self,filename,peaks):
	wx.CallAfter(self.OpenH5,filename,peaks)
    
    #----------------------------------------------------------------------
    def display_peaks(self, axes,peaks,Bragg,color='y',radius=5,thickness=0):
      
       for peak in peaks:
        circle=Circle((peak[0],peak[1]),radius,color=color,fill=False,linewidth=1.5)
        circle.set_gid("circle")
        axes.add_artist(circle)
    
    #----------------------------------------------------------------------
    def clean_peaks(self):
        """ Remove any circle around Bragg peaks
	"""
        artists=self.axes.findobj()
        for artist in artists:
	     if artist.get_gid() == "circle": artist.remove() 
	  
    #----------------------------------------------------------------------
    def FindBraggs(self,threshold):
        """Find Position of Bragg peaks in the img
	   and display it on screen
	"""
	data=self.dset[0:1023,0:1004].astype(np.float)
        local_max=pf.find_local_max(data,d_rad=3,threshold=threshold)
	self.peaks=np.array(pf.subpixel_centroid(data,local_max,3))
	
	self.clean_peaks()
	self.display_peaks(self.axes,self.peaks,self.Bragg)
	self.canvas.draw()
	
	num_braggs=self.peaks.shape[0]
        self.log.WriteText("Found %4i Bragg peaks in file %s (threshold of %i)\n" %(num_braggs,self.filename,threshold))
    
    
    #----------------------------------------------------------------------
    def OpenH5(self,filename,peaks=None):
        self.filename=filename
	#Should pass the data along, not the file !!
	f=h5py.File(self.filename,'r')
	#vmin=self.vmin*np.sqrt(self.boost)
	#vmax=self.vmax*np.sqrt(self.boost)
	if self.dset== []:
	   self.dset=f['data'][:]
	   self.frame.set_data(self.dset*self.boost)
	   self.frame.set_clim(vmin=self.vmin*np.sqrt(self.boost), vmax=self.vmax*np.sqrt(self.boost))
	   #,cmap=self.cmap)
	   
	else:
	   self.dset=f[f.keys()[0]][:]
	   new_dset=self.dset*self.boost
	   self.frame.set_data(new_dset)
	
	#is there peaks in the h5file?
	try:self.peaks=f['processing/hitfinder/peakinfo'][:]
	except: self.peaks=None
	f.close()
	self.clean_peaks()
	if self.peaks != None and self.Bragg: self.display_peaks(self.axes,self.peaks,self.Bragg)
	self.canvas.draw()

    
    #----------------------------------------------------------------------
    def SetBragg(self,Bragg):
        self.Bragg=Bragg
	if self.peaks != None and self.Bragg == True: self.display_peaks(self.axes,self.peaks,self.Bragg)
	if self.Bragg == False: self.clean_peaks()
	self.canvas.draw()
    
    #----------------------------------------------------------------------
    def UpdateMin(self,boost,mini,maxi):
        vmin=mini*np.sqrt(boost)
	self.vmin=vmin
        self.frame.set_clim(vmin=self.vmin)
	self.canvas.draw()

    #----------------------------------------------------------------------
    def UpdateMax(self,boost,mini,maxi):
        vmax=maxi*np.sqrt(boost)
	self.vmax=vmax
	self.frame.set_clim(vmax=self.vmax)
	self.canvas.draw()
	
    #----------------------------------------------------------------------
    def UpdateBoost(self,boost,mini,maxi):
        self.vmin=mini*np.sqrt(boost)
	self.vmax=maxi*np.sqrt(boost)
	self.boost=boost
	self.frame.set_clim(vmin=self.vmin)
	self.frame.set_clim(vmax=self.vmax)
	new_dset=self.dset[:]*self.boost
	self.frame.set_data(new_dset)
	self.canvas.draw()

    #----------------------------------------------------------------------
    def SetCmap(self,cmap):
        self.frame.set_cmap(cmap)
	self.cmap=cmap
	self.canvas.draw()



        
    
    
class PlayThread(Thread):
    
    #----------------------------------------------------------------------
    def __init__(self,panel,panel1,fname_list,index):
        self.panel=panel
	self.panel1=panel1
	self.fname_list=fname_list
	self.index=index
	Thread.__init__(self)
	self.daemon=True
        self.signal = True
	self.start()    # start the thread
        
	
    #----------------------------------------------------------------------
    def run(self):
	for i in range(self.index,len(self.fname_list)):
	    if self.signal: 
	        self.panel.OpenH5(self.fname_list[i])
                self.panel1.filelist.SetSelection(i)
		self.panel1.filelist.EnsureVisible(min(i+7,len(self.fname_list)-1))
		
	    else: break
        #self.panel1.Play.Enable()
	self.panel1.playPauseBtn.SetValue(False)
    
class ShowNumbers(wx.Frame):

    def __init__(self,parent,id,s):
        font=wx.Font(11,wx.TELETYPE, wx.NORMAL, wx.NORMAL, False,'Courier New')
	wx.Frame.__init__(self, 
			  parent, 
			  id, 
			  'Intensities', 
			  size=(680,370),
			  style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)
        self.Show(False)	
	panel = wx.Panel(self, -1)
        self.text=wx.StaticText(panel, -1, s, (10, 10))
	self.text.SetFont(font)
        
    
        
class RedirectText(object):
    def __init__(self,aWxTextCtrl):
        self.out=aWxTextCtrl

    def write(self,string):
        
        self.out.WriteText(string)



class DraggableColorbar(object):
    def __init__(self, cbar, mappable,boost):
        self.boost=boost
        self.cbar = cbar
        self.mappable = mappable
        self.press = None
        self.cycle = sorted([i for i in dir(plt.cm) if hasattr(getattr(plt.cm,i),'N')])
	self.index = self.cycle.index(cbar.get_cmap().name)

    def connect(self):
        """connect to all the events we need"""
        self.cidpress = self.cbar.patch.figure.canvas.mpl_connect(
            'button_press_event', self.on_press)
        self.cidrelease = self.cbar.patch.figure.canvas.mpl_connect(
            'button_release_event', self.on_release)
        self.cidmotion = self.cbar.patch.figure.canvas.mpl_connect(
            'motion_notify_event', self.on_motion)
        self.keypress = self.cbar.patch.figure.canvas.mpl_connect(
            'key_press_event', self.key_press)

    def on_press(self, event):
        """on button press we will see if the mouse is over us and store some data"""
        if event.inaxes != self.cbar.ax: return
        self.press = event.x, event.y
	
    def key_press(self, event):
        if event.key=='down':
            self.index += 1
        elif event.key=='up':
            self.index -= 1
        if self.index<0:
            self.index = len(self.cycle)
        elif self.index>=len(self.cycle):
            self.index = 0
        
	cmap = self.cycle[self.index]
        self.cbar.set_cmap(cmap)
        self.cbar.draw_all()
        self.mappable.set_cmap(cmap)
	self.mappable.get_axes().set_title(cmap)
	self.mappable.get_axes().get_figure().canvas.draw()
        self.cbar.patch.figure.canvas.draw()
    
    def oncmap(self,cmap):
        self.cbar.set_cmap(cmap)
	self.cbar.draw_all()
	self.cbar.patch.figure.canvas.draw()
    
    def on_motion(self, event):
        'on motion we will move the rect if the mouse is over us'
        if self.press is None: return
        if event.inaxes != self.cbar.ax: return
        xprev, yprev = self.press
        dx = event.x - xprev
        dy = event.y - yprev
        self.press = event.x,event.y
        #print 'x0=%f, xpress=%f, event.xdata=%f, dx=%f, x0+dx=%f'%(x0, xpress, event.xdata, dx, x0+dx)
        scale = self.cbar.norm.vmax - self.cbar.norm.vmin
        perc = 0.05
        if event.button==1:
            self.cbar.norm.vmin -= (perc*scale)*np.sign(dx)
            self.cbar.norm.vmax -= (perc*scale)*np.sign(dx)
        elif event.button==3:
            self.cbar.norm.vmin -= (perc*scale)*np.sign(dx)
            self.cbar.norm.vmax += (perc*scale)*np.sign(dx)
        self.cbar.draw_all()
	#temp_norm=self.cbar.norm
	self.mappable.set_norm(self.cbar.norm)
	#self.mappable.set_clim(vmin=mini,vmax=maxi)
        self.cbar.patch.figure.canvas.draw()
        self.mappable.get_axes().get_figure().canvas.draw()
        

    def on_release(self, event):
        """on release we reset the press data"""
        self.press = None
        self.mappable.set_norm(self.cbar.norm)
	pub.sendMessage('Update Spins',mini=self.cbar.norm.vmin,maxi=self.cbar.norm.vmax)
        self.cbar.patch.figure.canvas.draw()
        self.mappable.get_axes().get_figure().canvas.draw()
        
    def disconnect(self):
        """disconnect all the stored connection ids"""
        self.cbar.patch.figure.canvas.mpl_disconnect(self.cidpress)
        self.cbar.patch.figure.canvas.mpl_disconnect(self.cidrelease)
        self.cbar.patch.figure.canvas.mpl_disconnect(self.cidmotion)

class MainFrame(wx.Frame):
    
    #Also Acts as the Controller here
    #----------------------------------------------------------------------
    def __init__(self,parent):
        """Constructor
	"""
        wx.Frame.__init__(self, None, wx.ID_ANY,
                          "NanoPeakCell",
                          size=(3000,1200))
	font2=wx.Font(11,wx.MODERN, wx.NORMAL, wx.NORMAL, False,'MS Shell Dlg 2')
	
	self.log = wx.TextCtrl(self, wx.ID_ANY, size=(300,100),
                          style = wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
	
	self.panel=PlotStats(self,self.log)
	self.panel1=RightPanel(self,self.log)
	self.left=HitView(self,self.log)
	
	self.MainSizer = wx.BoxSizer(wx.HORIZONTAL)
	self.MainSizer.Add(self.left, 0, wx.EXPAND | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL , 5)
        self.MainSizer.Add(self.panel, 1, wx.EXPAND | wx.ALIGN_CENTER | wx.ALIGN_CENTER_VERTICAL , 5)
	self.MainSizer.Add(self.panel1, 0, wx.EXPAND | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL , 5)
        
	self.sizer2=wx.BoxSizer(wx.VERTICAL)
	self.statusbar=wx.StaticText(self,-1,'Log Messages')
	self.statusbar.SetFont(font2)
	self.sizer2.Add(self.MainSizer,1, wx.EXPAND | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL , 5)
	self.sizer2.Add(self.statusbar,0,  wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL , 5)
	
	self.sizer2.Add(self.log, 0, wx.EXPAND | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL , 5)
	
	
	#self.redir=RedirectText(self.log)
	
        #sys.stdout=redir
	#Bindings
	self.panel1.boost.Bind(wx.EVT_SPINCTRL, self.Boost)
	self.panel1.min.Bind(wx.EVT_SPINCTRL, self.Min)
	self.panel1.max.Bind(wx.EVT_SPINCTRL, self.Max)
	self.panel1.filelist.Bind(wx.EVT_LISTBOX, self.OnSelect)
        #self.panel1.Play.Bind(wx.EVT_BUTTON, self.OnPlay)
	self.panel1.FindBraggs.Bind(wx.EVT_BUTTON, self.OnFindBragg)
        self.panel1.playPauseBtn.Bind(wx.EVT_BUTTON,self.OnPlay)
	#self.panel1.Stop.Bind(wx.EVT_BUTTON, self.OnStop)
	self.panel1.cmap.Bind(wx.EVT_CHOICE,self.OnCmap)
	self.panel1.ShowBragg.Bind(wx.EVT_CHECKBOX,self.OnBragg)
	self.panel.w.Bind(wx.EVT_CLOSE,self.onExit)
	self.SetSizerAndFit(self.sizer2)
	self.Centre()
	self.Show()

    
    #----------------------------------------------------------------------
    def onExit(self,e):
        self.panel.w.Hide()
	
    #----------------------------------------------------------------------
    def OnFindBragg(self,e):
        th=float(self.left.Thresh.GetValue())
	self.panel.FindBraggs(th)
    
    #----------------------------------------------------------------------
    def OnBragg(self,e):
        ShowBragg=self.panel1.ShowBragg.GetValue()
	self.panel.SetBragg(ShowBragg)
    
    #----------------------------------------------------------------------
    def OnCmap(self,e):
        cmap=self.panel1.cmap.GetStringSelection()
	self.panel.SetCmap(cmap)
	self.panel1.SetCmap(cmap)
    #----------------------------------------------------------------------
    def OnStop(self):
        try : 
	    self.t.signal=False
	    #self.panel1.Play.Enable()
	except: return
	
    #----------------------------------------------------------------------
    def OnPlay(self,e):
        if not e.GetIsDown():
            self.OnStop()
            return
        
        index=self.panel1.filelist.GetSelection()
	self.t=PlayThread(self.panel,self.panel1,self.panel1.fname_list,index)
       
    #----------------------------------------------------------------------
    def OnSelect(self,e):
        index = e.GetSelection()
	filename=self.panel1.filelist.GetString(index)
	self.panel.OpenH5(filename)

    #----------------------------------------------------------------------
    def Min(self,e):
        boost = self.panel1.boost.GetValue()
	mini = self.panel1.min.GetValue()
	maxi = self.panel1.max.GetValue()
	self.panel.UpdateMin(boost,mini,maxi)
        self.panel1.SetMin(mini)
    #----------------------------------------------------------------------
    def Max(self,e):
        boost = self.panel1.boost.GetValue()
	mini = self.panel1.min.GetValue()
	maxi = self.panel1.max.GetValue()
	self.panel.UpdateMax(boost,mini,maxi)
	self.panel1.SetMax(maxi)
	

    #----------------------------------------------------------------------
    def Boost(self,e):
        boost = self.panel1.boost.GetValue()
	mini = self.panel1.min.GetValue()
	maxi = self.panel1.max.GetValue()
	self.panel.UpdateBoost(boost,mini,maxi)

class Logo(wx.SplashScreen):

    def __init__(self, parent = None):
        self.root=NPCVar()
	Logo=wx.Image(name=os.path.join(self.root,"FILES",'NPC.png')).ConvertToBitmap()
	splashStyle = wx.SPLASH_CENTER_ON_SCREEN | wx.SPLASH_TIMEOUT
	splashDuration = 1500 #milliseconds
        wx.SplashScreen.__init__(self, Logo, splashStyle, splashDuration, None)
       
        self.Bind(wx.EVT_CLOSE, self.OnExit)

    def OnExit(self,e):
	self.Hide()
	MyFrame= MainFrame(None)
        app.SetTopWindow(MyFrame)
        MyFrame.Show(True)
        e.Skip()

if __name__ == "__main__":
    app = wx.App(False)
    controller=Logo(app)
    app.MainLoop()



