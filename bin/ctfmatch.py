#!/usr/bin/env python
#
# SOURCE:  ctfmatch.py
# 
# PURPOSE: Display CTF doc files 
#
# Spider Python Library
# Copyright (C) 2006-2018  Health Research Inc., Menands, NY
# Email:    spider@health.ny.gov

import tkinter
from   tkinter import filedialog, messagebox
import Pmw
import string
import os
import math
import subprocess
from matplotlib import figure
from matplotlib.backends import backend_tkagg
import numpy as np
from scipy import interpolate, signal
import argparse

from Spider    import Spiderutils

import webbrowser
webpage = "http://www.wadsworth.org/spider_doc/spider/spire/tools-docs/ctfmatch.html"

# Constants & defaults
MODIFIED="Modified 2025 Jul 24"
MAX_VERBOSITY=2
SPHERICAL_ABERRATION=2.0
VOLTAGE=200
PIXSIZE=2.82
SOURCE_SIZE=0.0
DEFOCUS_SPREAD=0.0
GAUSSIAN_ENV=2.0
AMP_CONTRAST=0.1

# For spline-fitting
WIN_SIZE=11    # Window size for filtering CTF profile using Savitzky-Golay filter
POLY_ORDER=1   # Polynomial order for filtering CTF profile using Savitzky-Golay filter
MIN_RES=30     # CTF minima will be ignored before this resolution (in A)
SMOOTH_BKGD=1  # Smoothening factor for background during spline-fitting
SMOOTH_ENV=1   # Smoothening factor for envelope during spline-fitting

USAGE = """
  %s <options> <optional_profile_docfiiles>

Wild cards can be used for doc files, e.g.:
  %s -defocus defocus.dat power/roo_doc_00*

Providing both the pixel size and voltage will bypass the initial parameter window, e.g.:
  %s  -pixsize 2.82 -kev 200


""" % ( (os.path.basename(__file__),)*3 )

def parse_command_line():
    """
    Parse the command line.  Adapted from sxmask.py

    Arguments:
        None

    Returns:
        Parsed arguments object
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        usage=USAGE,
        epilog=MODIFIED
    )

    parser.add_argument(
        "-defocus",
        type=str,
        default='',
        help="SPIDER doc file with defocus values")

    parser.add_argument(
        "-verbose", "-v", "-verbosity",
        type=int,
        default=1,
        help=f"Screen verbosity [0..{MAX_VERBOSITY}]")


    parameters= parser.add_argument_group(
        title="Optical parameters")

    parameters.add_argument(
        "-cs",
        type=float,
        default=SPHERICAL_ABERRATION,
        help="Spherical aberration constant (mm)")

    parameters.add_argument(
        "-kev",
        type=float,
        default=argparse.SUPPRESS,
        help=f"Electron energy (keV) (default: {VOLTAGE})")

    parameters.add_argument(
        "-pixsize",
        type=float,
        default=argparse.SUPPRESS,
        help=f"Pixel size (A/pixel) (default: {PIXSIZE})")

    parameters.add_argument(
        "-src",
        type=float,
        default=SOURCE_SIZE,
        help="Source size (1/A)")

    parameters.add_argument(
        "-spread",
        type=float,
        default=DEFOCUS_SPREAD,
        help="Defocus spread (A)")

    parameters.add_argument(
        "-acr",
        type=float,
        default=AMP_CONTRAST,
        help="Amplitude contrast ratio")

    parameters.add_argument(
        "-gep",
        type=float,
        default=GAUSSIAN_ENV,
        help="Gaussian envelope parameter")


    spliner= parser.add_argument_group(
        title="Spline-fitting parameters for background subtraction of CTF FIND output")

    spliner.add_argument(
        "-winsize",
        type=int,
        default=WIN_SIZE,
        help="Window size for filtering CTF profile using Savitzky-Golay filter")

    spliner.add_argument(
        "-poly",
        type=int,
        default=POLY_ORDER,
        help="Polynomial order for filtering CTF profile using Savitzky-Golay filter")

    spliner.add_argument(
        "-minres",
        type=float,
        default=MIN_RES,
        help="CTF minima will be ignored before this resolution (in A)")

    spliner.add_argument(
        "-smoothbkgd",
        type=float,
        default=SMOOTH_BKGD,
        help="Smoothening factor for background during spline-fitting")

    spliner.add_argument(
        "-smoothenv",
        type=float,
        default=SMOOTH_ENV,
        help="Smoothening factor for envelope during spline-fitting")

    advanced= parser.add_argument_group(
        title="Advanced settings")

    advanced.add_argument(
        "-maxdf",
        type=float,
        default=60000.,
        help="Maximum defocus value for slide bar, Angstroms")

    advanced.add_argument(
        "-defaultdf",
        type=float,
        default=20000.,
        help="Default starting defocus value, Angstroms")

    advanced.add_argument(
        "-nsam", "-n",
        type=int,
        default=250,
        help="Number of sampling points in spatial frequency")

    advanced.add_argument(
        "-expmult",
        type=float,
        default=1.,
        help="Multiplcation factor for experimental data")

    return parser.parse_known_args()

def ctfhelp():
    try:
        webbrowser.open(webpage,1)
    except:
        pass

def ctfabout():
    s = "CTFmatch 2.0\n\n" + \
        "A tool for analyzing the output " +\
        "from SPIDER's CTF FIND command."
    messagebox.showinfo("About CTFmatch 2.0", s)

def readDefocus(filename):
    " returns list of (mic#, defocus) pairs (mic=int defocus=string)"
#    F = spiderutils.readSpiderDocFile(filename, col_list=(1,2))
    F = Spiderutils.readdoc(filename, keys='all')
    if F == None: return []
    keys = list(F.keys())
    keys.sort()
    
    M = []
    for key in keys:
        mic     = int(F[key][0])
        defocus = str(int(F[key][1]))
        M.append( (mic, defocus) )
    return M
            
    
def readCtfDoc(filename, factor=1.0, squared=1):
    """
    In previous versions, only 1-column ("roo") and 4-column (TF ED) CTF docs were recognized.
    Now, there is CTF FIND format with three columns.
    So we will consider each of these cases now based on the number of columns.
    """

    F = Spiderutils.readdoc(filename, keys='all')
    if F == None: return []
    A = []; B = []; C = []; D = []; E = []
    keys = list(F.keys())
    keys.sort()
    
    # get the 1st line of data, test if roo (cols 3 & 4 = 1)
    k = keys[0]
    vals = F[k]
    vlen = len(vals)
            
    # get the data
    for key in keys:
        # "roo" format
        if vlen == 1:
            a = factor * F[key][0]
            D.append(a)

        # TF ED format
        elif vlen== 4 or (vals[2] == 1 and vals[3] == 1):
            freq = F[key][0] 
            bgd  = factor * F[key][1]
            sub  = factor * F[key][2]
            env  = factor * F[key][3]
            roo  = bgd + sub     # get original spectrum
            if squared == 1:
                k = env + bgd  
                roo = roo * roo  # square the spectrum
                bgd = bgd * bgd  # square the background
                sub = roo - bgd  # new subtracted curve
                env = k*k - bgd  # new envelope
            A.append(freq)
            B.append(bgd)
            C.append(sub)
            D.append(env)
            E.append(roo)

        # CTF FIND format
        elif vlen== 3:
            # NOTE: CTF FIND shows spatial frequency in reciprocal pixels, not Angstroms
            roo= factor * F[key][0]
            freq = F[key][2]

            A.append(freq)
            E.append(roo)

        else:
            return []  # openRooDoc() will print an error if there is one

    if vlen == 1:  #### if roofile:
        return [D]
    elif vlen== 4 or (vals[2] == 1 and vals[3] == 1):
        return [A,B,C,D,E]
    elif vlen== 3:
        return [A,E]

def getFiles(filetypes=None):
    ft = []
    if filetypes != None:
        ft.append( (filetypes,filetypes )) # "*.dat" --> ("*.dat", "*.dat")
    ft.append(("All files", "*"))
    f = filedialog.askopenfilename(multiple=1, filetypes=ft)
    "f is a long string under irix, but a tuple of strings in linux. Neat, huh?"
    if type(f) == type("string"):
        return string.split(f)
    else:
        return f  # hopefully a tuple or a list

def fitSpline(sp_freq_list, exp_amp_list, window_size=11, poly_order=1, start_res=30, backgd_smooth=1, envelope_smooth=1, verbosity=0):
    """
    Subtract background from experimental curve
    and apply envelope to theoretical curve
    by fitting relative extrema to a spline

    Adapted from SPHIRE's sp_gui_cter.py

    Input parameters:
        sp_freq_list : spatial frequency
        exp_amp_list : experimental profile
        window_size : window size for Savitzky-Golay filter
        poly_order : polynomial order for Savitzky-Golay filter
        start_res : CTF minima will be ignored before this resolution (in Angstroms, not reciprocal Angstroms)
        backgd_smooth : smoothening factor for background
        envelope_smooth : smoothening factor for envelope
    """

    # Smoothen experimental curve (adapted from https://medium.com/pythoneers/introduction-to-the-savitzky-golay-filter-a-comprehensive-guide-using-python-b2dd07a8e2ce)
    smooth_list = signal.savgol_filter(exp_amp_list, window_size, poly_order)

    # initialize lists of extrema
    exp_max_x = []
    exp_max_y = []
    exp_min_x = []
    exp_min_y = []

    def add_point(xcoords, ycoords, key, xvalue, yvalue, verbosity, min_max):
        xcoords.append(xvalue)
        ycoords.append(yvalue)
        if min_max == 'Maximum' and verbosity == 3:
            print('  Maximum', key, xvalue, yvalue)
        if min_max == 'Minimum' and verbosity == 4:
            print('  Minimum', key, xvalue, yvalue)

    # Search experimental and theoretical curves for extrema (skipping lowest-resolution values)
    for key in range(2, len(sp_freq_list) - 2):
        # Check if smoothened curve is at a minimum (skipping low-resolution values)
        if (smooth_list[key] < smooth_list[key - 2] and smooth_list[key] < smooth_list[key + 2]):
            # Ignore low-resolution minima
            if sp_freq_list[key] > 1/start_res :
                # If first point, then prepend the same value at x=0
                if len(exp_min_y) == 0:
                    add_point(exp_min_x, exp_min_y, key, sp_freq_list[0], exp_amp_list[key], verbosity, 'Minimum')

                add_point(exp_min_x, exp_min_y, key, sp_freq_list[key], exp_amp_list[key], verbosity, 'Minimum')

        # Check if smoothened curve is at a maximum
        if (smooth_list[key] > smooth_list[key - 2] and smooth_list[key] > smooth_list[key + 2]):
            add_point(exp_max_x, exp_max_y, key, sp_freq_list[key], exp_amp_list[key], verbosity, 'Maximum')
            last_max_key = key


    # If there's a big gap, add a point halfway
    if last_max_key/len(sp_freq_list) < 0.5 :
        halfway = (len(sp_freq_list) - last_max_key)//2 + last_max_key
        average = (exp_max_y[-1] + exp_amp_list[-1])/2
        ###Spiderutils.whocalledme(387, ['halfway', 'average'], [halfway, average])
        add_point(exp_max_x, exp_max_y, key, sp_freq_list[halfway], average, verbosity, 'Maximum')
    add_point(exp_max_x, exp_max_y, key, sp_freq_list[-1], exp_amp_list[-1], verbosity, 'Maximum')
    add_point(exp_min_x, exp_min_y, key, sp_freq_list[-1], exp_amp_list[-1], verbosity, 'Minimum')

    # Change to arrays
    exp_max_x_np = np.array(exp_max_x)
    exp_max_y_np = np.array(exp_max_y)
    exp_min_x_np = np.array(exp_min_x)
    exp_min_y_np = np.array(exp_min_y)

    X_np = np.array(sp_freq_list)

    # Splinefit extrema
    exp_min_tck = interpolate.splrep(exp_min_x_np, exp_min_y_np, s=backgd_smooth)
    exp_max_tck = interpolate.splrep(exp_max_x_np, exp_max_y_np, s=envelope_smooth)
    # s==smoothing factor

    # Evaluate splines
    exp_min_spline = interpolate.splev(X_np, exp_min_tck)
    exp_max_spline = interpolate.splev(X_np, exp_max_tck)

    # will subtract background and apply envelope
    exp_subtract = []
    exp_envelope = []

    # Subtract minimum and multiply by envelope
    for key in range(0, len(sp_freq_list)):
        diff = exp_amp_list[key] - exp_min_spline[key]
        exp_subtract.append(diff)
        exp_envelope.append(exp_max_spline[key] - exp_min_spline[key])

    return exp_min_spline, exp_subtract, exp_envelope


###################################################################
#
# CTF plot

class CTFplot:
    " default values "
    ###def __init__(self, master, filename=None, args=None):
    def __init__(self, master, filename=None, args=None, roo=None):
        ###Spiderutils.whocalledme( 297,'pixsize', 'pixsize' in args.__dict__ ) ; exit ()
        # first set defaults
        self.top = master
        self.cs = tkinter.StringVar();      self.cs.set(args.cs)
        self.defocus = tkinter.StringVar(); self.defocus.set( min(args.defaultdf, args.maxdf) )
        self.kev = tkinter.StringVar()
        self.pixsize = tkinter.DoubleVar()
        self.src = tkinter.StringVar();     self.src.set(args.src)
        self.spread = tkinter.StringVar();  self.spread.set(args.spread)
        self.acr = tkinter.StringVar();     self.acr.set(args.acr)
        self.gep = tkinter.StringVar();     self.gep.set(args.gep)
        self.defocusfile = args.defocus  #### ""
        self.tfed = roo  #### []
        self.verbose = args.verbose
        self.args = args

        # If pixel size and voltage were provided on command line, you can bypass the initial parameter window
        if 'kev' in args.__dict__:
            self.kev.set(args.kev)
        else:
            self.kev.set(VOLTAGE)

        if 'pixsize' in args.__dict__:
            self.pixsize.set(args.pixsize)
        else:
            self.pixsize.set(PIXSIZE)

        if 'pixsize' in args.__dict__ and 'kev' in args.__dict__ :
            self.askParms = 0
        else:
            self.askParms = 1

        max_defocus = args.maxdf
        self.expmult = args.expmult
        self.modmult = 1.0  # I don't know what this does

        self.max_spat_freq = 1.0 / ( 2.0 * self.pixsize.get() )
        self.kappa = -math.pi**2 / (16.0 * math.log(2.0))
        self.infinity = 1e50
        self.ymax = tkinter.DoubleVar()  #### StringVar()
        self.xmin = tkinter.StringVar() ; self.xmin.set(0)
        self.modymax = tkinter.StringVar()
        self.n = args.nsam

        # arrays for holding data columns
        self.arr = {'frq':[], 'bgd':[], 'sub':[], 'env':[], 'roo':[]}
        self.showlist = {'bgd':1, 'sub':1, 'env':1, 'roo':1, 'model':1}

        # variables for checkbuttons in menus
        self.showRoo = tkinter.IntVar() ; self.showRoo.set(1)
        self.showBgd = tkinter.IntVar() ; self.showBgd.set(1)
        self.showSub = tkinter.IntVar() ; self.showSub.set(1)
        self.showEnv = tkinter.IntVar() ; self.showEnv.set(1)
        self.showMod = tkinter.IntVar() ; self.showMod.set(1)
        self.gridShow= tkinter.IntVar() ; self.gridShow.set(0)

        # colors from https://jfly.uni-koeln.de/color/
        self.colors = {'bgd':'#009e74', 'sub':'#cc79a7', 'env':'#9999ff',
                       'roo':'#e69d00',  'model':'white'}

        # by default, data are squared
        self.squared = tkinter.IntVar() ; self.squared.set(1)

        # whether to use the empirical envelope
        self.envelope = tkinter.IntVar() ; self.envelope.set(0)
        self.roofile = ""
        self.tfedfile = ""
        self.savefile = ""
        self.defDict = {}   # [micno] = defocus
        self.fileDict = {}   # [micno] = (basename, fullpath)
            
        # set up model data and read file
        self.X = []
        self.Y = []
        self.E = []

        if filename != None:
            if not self.openRooDoc(filename):
                filename = None

        if len(self.arr['frq']) > 0:
            self.X = self.arr['frq']
        else:
            for i in range(self.n):
                self.X.append((self.max_spat_freq / float(self.n)) * i)
        for i in range(self.n):
            self.Y.append(0.0)
            self.E.append(0.0)

        if filename != None:
            self.newymax()
        else:
            self.ymax.set(1.)  #### ('1.0')
        self.modymax.set(1.0)
        self.computeModelCtf() # generate the model

        # ------- create the menu bar -------
        self.mBar = tkinter.Frame(master, relief='raised', borderwidth=1)
        self.mBar.pack(side='top', fill = 'x')
        self.balloon = Pmw.Balloon(self.top)
        
        # Make the File menu
        Filebtn = tkinter.Menubutton(self.mBar, text='File', underline=0,
                                 relief='flat')
        Filebtn.pack(side=tkinter.LEFT, padx=5, pady=5)
        Filebtn.menu = tkinter.Menu(Filebtn, tearoff=0)
        Filebtn.menu.add_command(label='Open defocus file',
                                 command=self.openDefocus)
        Filebtn.menu.add_command(label='Open TF ED profile',
                                 command=self.plotCtfProfile)
        Filebtn.menu.add_command(label='Open 1D profile series',
                                 command=self.fileSeries)
        Filebtn.menu.add_command(label='Save defocus as...',
                                 command=self.saveDefocusAs)
        Filebtn.menu.add_separator()
        Filebtn.menu.add_command(label='Quit', underline=0,
                                     command=self.quit)
        Filebtn['menu'] = Filebtn.menu

        
        # Make the Option menu
        Optbtn = tkinter.Menubutton(self.mBar, text='Options', relief='flat')
        Optbtn.pack(side=tkinter.LEFT, padx=5, pady=5)
        Optbtn.menu = tkinter.Menu(Optbtn, tearoff=0)

        Optbtn.menu.add_command(label='Parameters', underline=0,
                                    command=self.callSetParms)
        Optbtn.menu.add_checkbutton(label='Squared data', underline=0,
                                    variable=self.squared,
                                    command=self.showSquared)
        Optbtn.menu.add_checkbutton(label='Grid', underline=0,
                                    variable=self.gridShow,
                                    command=self.showGrid)
        Optbtn.menu.add_checkbutton(label='Use empirical envelope',
                                    variable=self.envelope,
                                    command=self.replot)
        Optbtn['menu'] = Optbtn.menu
       
        # Parameter menu
        #menuBar.addmenuitem('Model', 'checkbutton', 'reset yscale',
                            #indicatoron=0,
                            #label='Reset Ymax', command=self.showGrid)
        
        # Make the Show menu
        Showbtn = tkinter.Menubutton(self.mBar, text='Show', relief='flat')
        Showbtn.pack(side=tkinter.LEFT, padx=5, pady=5)
        Showbtn.menu = tkinter.Menu(Showbtn, tearoff=0)

        Showbtn.menu.add_checkbutton(label='1D spectrum', 
                                    background = 'black',
                                    foreground = self.colors['roo'],
                                    selectcolor='red',
                                    activeforeground = self.colors['roo'],
                                    variable = self.showRoo,
                                    command=self.replot)
        Showbtn.menu.add_checkbutton(label='Background',
                                    background = 'black',
                                    foreground = self.colors['bgd'],
                                    selectcolor='red',
                                    activeforeground = self.colors['bgd'],
                                    variable = self.showBgd,
                                    command=self.replot)
        Showbtn.menu.add_checkbutton(label='Subtracted data',
                                    background = 'black',
                                    foreground = self.colors['sub'],
                                    selectcolor='red',
                                    activeforeground = self.colors['sub'],
                                    variable = self.showSub,
                                    command=self.replot)
        Showbtn.menu.add_checkbutton(label='Envelope',
                                    background = 'black',
                                    foreground = self.colors['env'],
                                    selectcolor='red',
                                    activeforeground = self.colors['env'],
                                    variable = self.showEnv,
                                    command=self.replot)
        Showbtn.menu.add_checkbutton(label='Model', 
                                    background = 'black',
                                    foreground = self.colors['model'],
                                    selectcolor='red',
                                    activeforeground = self.colors['model'],
                                    variable = self.showMod,
                                    command=self.replot)
        Showbtn['menu'] = Showbtn.menu
        
        # Help menu
        Helpbtn = tkinter.Menubutton(self.mBar, text='Help', relief='flat')
        Helpbtn.pack(side=tkinter.RIGHT, padx=5, pady=5)
        Helpbtn.menu = tkinter.Menu(Helpbtn, tearoff=0)

        Helpbtn.menu.add_command(label='Help', command=ctfhelp)
        Helpbtn.menu.add_command(label='About', command=ctfabout)
        Helpbtn['menu'] = Helpbtn.menu
        
        
        # ------- widgets start here -------
        self.g_width = 446 #int(self.g.extents("plotwidth"))
        self.g_height = 150 #int(self.g.extents("plotheight"))

        ff = tkinter.Frame(master) # frame that holds everything
        
        " yscale slider "
        fy = tkinter.Frame(ff, relief='raised', borderwidth=2)
        ylabel = tkinter.Label(fy,text="y max")
        ymax = self.ymax.get()  #### float(self.ymax.get())

        self.yslider = tkinter.Scale(fy, orient='vertical', from_= ymax, to=0.0,
                       tickinterval = ymax/6.0,
                       resolution = 0.01,   #ymax/30.0,
                       label ="",
                       variable = self.ymax,
                       length =  self.g_height,
                       showvalue=0,
                       command=self.yupdate)

        " model height scale "
        mlabel = tkinter.Label(fy,text="model\nheight")
        mmax = 1.0   #string.atof(self.modymax.get())

        self.mslider = tkinter.Scale(fy, orient='vertical', from_= mmax, to=0.0,
                       tickinterval = mmax/5.0,
                       resolution = mmax/50.0,
                       label ="",
                       variable = self.modymax,
                       length =  self.g_height,
                       showvalue=0,
                       command=lambda v: self.update("model height", v) )
        
        ylabel.pack(side='top')
        self.yslider.pack(side='top', padx=5, pady=5)
        self.mslider.pack(side='bottom', padx=5, pady=5)
        mlabel.pack(side='bottom')


        self.curves = ['bgd','sub','env', 'roo']

        " the main plot "
        fg = tkinter.Frame(ff, relief='raised', borderwidth=2)
        self.fig = figure.Figure(figsize=(6.5, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.ticklabel_format( axis='y', style='sci', scilimits=(0,0) )  # can't get exponential notation to work

        self.ax.set_facecolor("black")
        self.ax.set_xlabel("Spatial frequency, 1/Å")
        self.ax.set_ylabel("Amplitude")
        self.fig.subplots_adjust(left=0.125, bottom=0.125, top=0.95, right=0.95)  # manually pads the margins
        self.ax.yaxis.major.formatter._useMathText = True

        # the model curve
        self.plotdict = {}
        self.plotdict['model'], = self.ax.plot(self.X, self.Y, color = self.colors['model'])

        # Embed the Figure in the Tkinter Frame
        self.canvas = backend_tkagg.FigureCanvasTkAgg(self.fig, master=fg)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)

        self.xmin.set(0)
        xmax = self.max_spat_freq
        xmin=float( self.xmin.get() )

        xslider = tkinter.Scale(fg, orient='horizontal', from_= xmin, to=xmax,
                       tickinterval = xmax/4.0,
                       resolution = 0.001,
                       label ="x min",
                       variable = self.xmin,
                       length =  int(self.g_width) / 2,
                       showvalue=0,
                       command=self.xminupdate)

        xbutton = tkinter.Button(fg, text="reset ymax", command=self.resetYmax)

        saveBut = tkinter.Button(fg, text='Save Defocus', command=self.saveDefocus)
        
        fl = tkinter.Frame(fg, relief='sunken', borderwidth=2)
        self.tfedlabel = tkinter.Label(fl, text=os.path.basename(self.tfedfile))
        self.defocuslabel = tkinter.Label(fl, text=os.path.basename(self.defocusfile))
        self.savelabel = tkinter.Label(fl, text=os.path.basename(self.savefile))
        self.tfedlabel.pack(side='top', padx=10, pady=5)
        self.defocuslabel.pack(side='top', padx=10, pady=5)
        self.savelabel.pack(side='top', padx=10, pady=5)

        xslider.pack(side='left', padx=5, pady=5)
        xbutton.pack(side='left', padx=5, pady=5)
        fl.pack(side='right', padx=10, pady=10)
        saveBut.pack(side='right', padx=10, pady=10)
        
        # ------ the set of sliders -------

        f = tkinter.Frame(ff, relief='raised', borderwidth=2)
        self.sliderlist = []
        self.slider(f, start=0, end=max_defocus, row=0,
                         label='defocus',
                         tickinterval=10000,
                         resolution = 50,
                         variable = self.defocus)
        self.slider(f, start=0, end=0.005, row=3,
                         label='source\nsize',
                         tickinterval=0.001,
                         digits = 2,
                         variable = self.src)
        self.slider(f, start=0, end=500, row=4,
                         label='defocus\nspread',
                         tickinterval=100,
                         variable = self.spread)
        self.slider(f, start=0, end=2, row=6,
                         label='Gaussian\nenvelope',
                         tickinterval=0.5,resolution=0.01,
                         variable = self.gep)
        f.columnconfigure(2, weight=1) # makes column expandable

        # fy, fg on top; f on bottom
        fy.grid(row=0, column=0, sticky='ns')
        fg.grid(row=0, column=1, sticky='nsew')
        f.grid(row=1, column=0, columnspan=2, sticky='ew')
        ff.columnconfigure(1, weight=1)  # make fg expand
        ff.rowconfigure(1, weight=1)     # make f expand
        
        ff.pack(expand=1, fill='both')
        self.top.update_idletasks()

        if self.askParms == 1:
            self.callSetParms()

        # if called with a list of tfed files
        if len(self.tfed) > 0:
            self.fileSeries(self.tfed)
        if self.defocusfile != "":
            self.openDefocus(self.defocusfile)

        ###### end init ------------------------------------------

    def callSetParms(self):
        w = tkinter.Toplevel(self.top)
        self.ParmWindow = w
        self.ParmWindow.geometry('300x140')
        self.setParms(w)
        self.top.wait_window(w) # wait for window to be destroyed
        self.xupdate()
        self.replot()

    def setParms(self, win=None):
        win.title('Set parameters')
        f = tkinter.Frame(win)
        labpx = tkinter.Label(f,text='pixel size(A): ')
        labkv = tkinter.Label(f,text='electron energy (kev): ')
        labcs = tkinter.Label(f,text='spherical aberration: ')
        labac = tkinter.Label(f,text='amplitude contrast ratio: ')
        entpx = tkinter.Entry(f, textvariable=self.pixsize, width=10, background='white')
        entkv = tkinter.Entry(f, textvariable=self.kev, width=10, background='white')
        entcs = tkinter.Entry(f, textvariable=self.cs, width=10, background='white')
        entac = tkinter.Entry(f, textvariable=self.acr, width=10, background='white')
        labpx.grid(row=0, column=0, sticky='e')
        labkv.grid(row=1, column=0, sticky='e')
        labcs.grid(row=2, column=0, sticky='e')
        labac.grid(row=3, column=0, sticky='e')
        entpx.grid(row=0, column=1)
        entkv.grid(row=1, column=1)
        entcs.grid(row=2, column=1)
        entac.grid(row=3, column=1)
        win.bind( '<Return>', lambda e, w=win: self.parmQuit(w) )
        win.bind( '<Control-g>', lambda e, w=win: self.getSize(w) )
        f.pack(side='top')
        fb = tkinter.Frame(win)
        b = tkinter.Button(fb, text='ok', command=win.destroy)
        b.pack(padx=5, pady=5)
        fb.pack()
        self.askParms = 0

    def parmQuit(self, win):
        win.destroy()

    def getSize(self, win):
        print('geometry:', win.geometry() )

    def slider(self, master, start=0, end=10, row=0, label="",
               tickinterval=1, resolution=None, digits=0,variable = None):

        lab = tkinter.Label(master, text=label)
        if resolution == None:
            resolution = float(tickinterval) / 20.0
        slider = tkinter.Scale(master, orient='horizontal', from_=start, to=end,
                       tickinterval = tickinterval,
                       resolution = resolution, label ="",
                       variable = variable,
                       showvalue=0,
                       digits = digits,
                       command=lambda v: self.update(label, v) )
        self.sliderlist.append(slider)
        ent = tkinter.Entry(master, textvariable=variable, width=10, background='white')
        ent.bind('<KeyPress>', lambda v: self.update(label, v) )

        lab.grid(row=row, column=0, sticky='w', padx=5, pady=5)
        ent.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        slider.grid(row=row, column=2, sticky='ew', padx=5, pady=5)

    def computeModelCtf(self):
        """
        Computes model CTF
        """

        cs    = 1e7 * float(self.cs.get())
        kv = float(self.kev.get())
        if kv != 0:
            lmbda = 12.398 / math.sqrt(kv* (1022+kv))
        else:
            lmbda = self.infinity
        if cs != 0:
            f1    = 1.0 / math.sqrt(cs*lmbda)
            f2    = math.sqrt(math.sqrt(cs*lmbda**3))
        else:
            f1 = self.infinity
            f2 = self.infinity

        pixsize = self.pixsize.get()
        if pixsize != 0:
            self.max_spat_freq = 1.0 / (2.0 * pixsize)
        km1   = f2 * self.max_spat_freq
        dk    = km1 / float(self.n)
        q1    = (float(self.src.get()) * f2)**2
        gep = float(self.gep.get())
        if gep != 0:
            env   = 1.0/gep**2
        else:
            env = self.infinity
        env1  = env/f2**2
        f     = -math.pi**2
        ds1   = f1 * float(self.spread.get())
        kappa = ds1 * self.kappa
        dz1   = f1 * float(self.defocus.get())

        acr = float(self.acr.get())
        squared = 1
        use_emp_envelope = self.envelope.get()
        if use_emp_envelope:  # use empirical envelope 
            self.modymax.set(1)

        for i in range(self.n):
            ak = i * dk
            p  = ak**3 - dz1 * ak
            ch = math.exp(ak*4 * kappa)
            self.E[i] = (math.exp(f*q1*p**2)*ch)*2*math.exp(-env1*ak**2)
            qqt = 2.0*math.pi*(0.25*ak**4 - 0.5*dz1*ak**2)
            qqt1 = (1.0-acr)*math.sin(qqt)-acr*math.cos(qqt)
            if not use_emp_envelope:
                self.Y[i] = self.E[i] * qqt1
            else:
                self.Y[i] = qqt1
            if squared:
                self.E[i] = (self.E[i])**2
                self.Y[i] = (self.Y[i])**2

        # height of model is always modelheight(0..1) times ymax
        # (unless use_emp_envelope)

        ymax = max(self.Y)
        if use_emp_envelope and len(self.arr['env']) > 0:
            if ymax != 0:
                env = self.arr['env']
                for i in range(self.n):
                    self.Y[i] = (self.Y[i] * env[i]) / ymax
        else:
            if ymax != 0:
                f = float(self.modymax.get()) * self.ymax.get()  #### float(self.ymax.get())
                self.modmult = f / ymax
            for i in range(self.n):
                self.Y[i] = self.Y[i] * self.modmult

        if hasattr(self,'plotdict'):
            self.plotdict['model'].set_ydata(self.Y)

    def update(self, slider_name, value):
        slider_nocr=slider_name.replace('\n',' ')

        if slider_nocr == "model height" and self.envelope.get():
            messagebox.showerror('ERROR!!', 'Model height cannot be adjusted when using empircal envelope')
            return
        self.computeModelCtf()
        self.fig.canvas.draw_idle()

    def replot(self):
        " replots data based on which curves are in display list "
        self.showlist['roo'] = self.showRoo.get()
        self.showlist['bgd'] = self.showBgd.get()
        self.showlist['sub'] = self.showSub.get()
        self.showlist['env'] = self.showEnv.get()
        self.showlist['model'] = self.showMod.get()
        self.newymax()
        if self.verbose>=2 : print("replot: ymax", self.ymax.get())
        self.computeModelCtf()
        self.showCurves()
        if self.verbose>=2 : print("replot: get_ylim", self.ax.get_ylim(), '\n' )

    def showCurves(self):
        # In case model is invisible...
        if self.showlist['model']:
            for curve in self.curves:
                if curve in self.plotdict: self.plotdict[curve].set_visible(False)

        # Axis limits are weird unless I hide all but the model
        self.ax.relim(visible_only=True)
        self.ax.autoscale_view()

        # Restore visibility
        for curve in self.curves+['model']:
            if curve in self.plotdict and self.showlist[curve]:
                self.plotdict[curve].set_visible(True)
            elif curve in self.plotdict:
                self.plotdict[curve].set_visible(False)

        self.fig.canvas.draw_idle()

    def newymax(self):
        " compute ymax over all curves except model "
        # get xmin and index into self.X
        if self.verbose>=2 : print("newymax: self.tfedfile", self.tfedfile)
        xmin = float(self.xmin.get())
        for i in range(self.n):
            if self.X[i] > xmin:
                break

        # i is index
        M = []
        ymax = 0

        for curr_key in self.showlist.keys():
            if curr_key != 'frq' and curr_key != 'model':
                if self.showlist[curr_key] and len(self.arr[curr_key]) > i:
                    newlist = self.arr[curr_key][i:]
                    M.append(max(newlist))
                    if max(newlist) > ymax:
                        ymax = max(newlist)

        if len(M) == 0: return
        ymax =  max(M)
        if ymax == 0: ymax = 1.0
        self.ymax.set(ymax)

        if hasattr(self,'yslider'):       
            self.yslider.configure(from_= ymax, to=0.0,
                                   tickinterval = ymax/5.0,
                                   resolution = ymax/50.0)
            self.yslider.set(ymax)

    def resetYmax(self):
        self.newymax()
        ymin= self.ax.get_ylim()[0]
        ymax= self.ymax.get()*1.05
        self.ax.set_ylim(ymin, ymax)
        self.fig.canvas.draw_idle()

    def xupdate(self, scalevalue=None):
        pixsize = self.pixsize.get()
        if pixsize == 0:
            return
        self.max_spat_freq = 1.0 / (2.0 * pixsize)
        for i in range(self.n):
            self.X[i] = i* (self.max_spat_freq / float(self.n))

        # Before the first file is selected, self.arr will have zero length
        for curve in self.curves:
            # If dictionary entry not yet present, then create new plot, else replace x_data
            if curve not in self.plotdict:
                if len(self.arr[curve]) == len(self.X):
                    self.plotdict[curve], = self.ax.plot(self.X, self.arr[curve], color = self.colors[curve])
                elif len(self.arr[curve]) != 0 :
                    print(f"WARNING! Unknown state: Number of sampling points ({len(self.X)}), is neither number of entries in the file ({len(self.arr[curve])}) nor zero")
                    return
            else:
                self.plotdict[curve].set_xdata(self.X)

        #self.g.element_configure('model', xdata=tuple(self.X))
        #self.g.axis_configure("x", max=self.max_spat_freq)

    def xminupdate(self, scalevalue=None):
        xmin = float(self.xmin.get())
        if xmin < self.max_spat_freq:
            if self.verbose>=2 : print("xminupdate: xmin", xmin)
            self.ax.set_xlim(xmin)
            self.fig.canvas.draw_idle()
        
    def yupdate(self, scalevalue=None):
        ymax = self.ymax.get()  #### float(self.ymax.get())
        ##if ymax > 0:
            ##self.g.axis_configure("y", max=ymax)
        self.ax.set_ylim(self.ax.get_ylim()[0], ymax)
        self.fig.canvas.draw_idle()
            
    def setFileLabels(self):
        if type(self.savefile) == type(""):
            self.savelabel.configure(text=os.path.basename(self.savefile))
        if type(self.tfedfile) == type(""):
            self.tfedlabel.configure(text=os.path.basename(self.tfedfile))
    
    def plotCtfProfile(self, filename=None):
        if not self.openRooDoc(filename=filename):
            return
        self.xupdate()

        # Replace y values
        for curve in self.curves:
            self.plotdict[curve].set_ydata(self.arr[curve])
        self.replot()
        self.resetYmax()  # I don't know why I need this
        self.setFileLabels()

    def openRooDoc(self, filename=None):
        if filename == None or filename == "":
            filename = filedialog.askopenfilename()
            if filename == None or filename == "":
                return 0
        A = readCtfDoc(filename, self.expmult, self.squared.get())

        if len(A) == 0:
            print("openRooDoc: error - readCtfDoc failed")
            return 0

        # single-column CTF doc file
        elif len(A) == 1:  # roofile
            self.arr['roo'] = A[0] ; self.showRoo.set(1)
            self.roofile = filename

        # TF ED file
        elif len(A) == 5:
            self.arr['frq'] = A[0] ; self.X = self.arr['frq']
            self.arr['bgd'] = A[1]
            self.arr['sub'] = A[2]
            self.arr['env'] = A[3]
            self.arr['roo'] = A[4]
            self.curves = ['bgd','sub','env', 'roo']
            self.tfedfile = filename

        # CTF FIND file
        elif len(A) == 2:
            self.tfedfile = filename

            # CTF FIND shows spatial frequency in reciprocal pixels, not Angstroms
            self.arr['frq'] = [ f/self.pixsize.get() for f in A[0] ]
            self.X = self.arr['frq']
            self.arr['roo'] = A[1]

            # Perform background subtraction
            self.arr['bgd'], self.arr['sub'], self.arr['env'] = fitSpline(
                self.arr['frq'],
                self.arr['roo'],
                window_size=self.args.winsize,
                poly_order=self.args.poly,
                start_res=self.args.minres,
                backgd_smooth=self.args.smoothbkgd,
                envelope_smooth=self.args.smoothenv,
                verbosity=self.verbose
                )

        else:
            print(f"Don't recognize {filename} with {len(A)} columns")
            os.system(f"head {filename}")
            return 0

        self.n = len(A[0])

        self.E = []
        self.Y = []
        for i in range(self.n):
            self.E.append(0.0)
            self.Y.append(0.0)
        return 1

    def filenumber(self, filename):
        " returns an integer "
        i = filename.rfind('.')
        if i < 0: return -1

        x = i  
        while i > 0:
            i = i-1
            try:
                int(filename[i])
            except:
                break
        try:
            n = int(filename[i+1:x])
        except:
            n = -1
        return n

    def makedisplaylist(self, sort=None):
        if sort == 'defocus' and len(self.defDict) == 0:
            return []
        displaylist = []
        if self.defDict:
            dkeys = list(self.defDict.keys())
            fkeys = list(self.fileDict.keys())
            if sort == 'defocus':
                # create a list of (defocus, file) pairs, and sort it
                deflist = []
                for key in dkeys:
                    if key in fkeys:
                        file = self.fileDict[key][0] # base name
                        defocus = self.defDict[key]
                        deflist.append((defocus, file))
                deflist.sort()
                for d in deflist:
                    file = d[1] 
                    defocus = d[0]
                    displaylist.append("%s     %s" % (file, defocus))
            else: # sort == 'file' or None
                for fn in fkeys:
                    if fn in dkeys:
                        file = self.fileDict[fn][0]
                        defocus = self.defDict[fn]
                        displaylist.append("%s     %s" % (file, defocus))
        else:
            # no defocus info, only filenames
            fkeys = list(self.fileDict.keys())
            fkeys.sort()
            for file in fkeys:
                displaylist.append(self.fileDict[file][0])

        self.displaylist = displaylist
                
        if hasattr(self,'boxwin') and self.boxwin.winfo_exists():
            self.box.setlist(self.displaylist)
            self.boxwin.lift()
            
        return displaylist
            
    def fileSeries(self, flist=None):
        "create a listbox from a user-specified set of files"
        # get the file list
        if flist == None: flist = getFiles()
        if len(flist) < 1: return

        # add basename, fullname to the file dictionary
        self.fileDict = {}
        
        for f in flist:
            basename = os.path.basename(f)
            fn = self.filenumber(basename)
            if fn != -1:
                self.fileDict[fn] = [basename, f]
        self.filelist = flist  # full path

        self.displaylist = self.makedisplaylist()                

        # put the filenames in a scrolled list box
        if hasattr(self,'boxwin') and self.boxwin.winfo_exists():
            self.makedisplaylist()
        else:
            self.boxwin = tkinter.Toplevel(self.top)
            self.boxwin.title("File series")
            self.boxwin.geometry('288x288')
            self.boxwin.bind( '<Control-g>', lambda e, w=self.boxwin: self.getSize(w) )
            flabels = tkinter.Frame(self.boxwin)
            bf = tkinter.Button(flabels, text='Sort by file',
                        command=lambda self=self,s='files':self.makedisplaylist(sort=s))
            bf.pack(side='left',padx=5,pady=5)
            bd = tkinter.Button(flabels, text='Sort by defocus',
                        command=self.defocusButtonfunc)
            bd.pack(side='right',padx=5,pady=5)
            flabels.pack(side='top')
            self.box = Pmw.ScrolledListBox(self.boxwin,
                                           items = self.displaylist,
                                           selectioncommand=self.select)
            self.box.pack(side='top', padx=5, pady=5, fill='both', expand=1)
            b = tkinter.Button(self.boxwin, text='Done', command=self.boxwin.destroy)
            b.pack(side='bottom', padx=5, pady=5)

    def select(self):
        sels = self.box.getcurselection()
        if len(sels) < 1: return
        
        f = sels[0].split()
        fn = self.filenumber(f[0])  # get number from basename
        filename = self.fileDict[fn][1]  # full path
        if len(f) == 2: # "filename   defocus"
            self.defocus.set(f[1])
        self.plotCtfProfile(filename=filename)

    def defocusButtonfunc(self):
        " if defocus data loaded, sorts on that column; else loads data"
        if len(self.defDict) == 0:
            self.openDefocus()
        else:
            self.makedisplaylist(sort='defocus')

    def openDefocus(self, filename=None):
        " expects 1st column=mic#, 2nd col=defocus "
        if filename == None:
            filename = filedialog.askopenfilename(title="Open doc file with defocus values")
        if filename == "" or filename == None or len(filename) == 0:
            return 0
        if not os.path.exists(filename):
            print("Unable to find defocus file: %s" % filename)
            return 0

        D = readDefocus(filename) # list of (mic#, defocus) pairs
        if len(D) == 0:
            self.defDict = {}
            cmd=f"head {os.path.relpath(filename)}"
            print(cmd, '\n')
            os.system(cmd)
            messagebox.showerror('WARNING!', f"Defocus file '{os.path.relpath(filename)}' had no valid entries. See log window for details.")
            return 0
        for item in D:
            micnum = item[0]
            defocus = item[1]
            self.defDict[micnum] = defocus
        self.defocusfile = filename
        self.defocuslabel.configure(text=os.path.basename(filename))

        self.makedisplaylist()
        return 1

    def saveDefocusAs(self):
        filename = filedialog.asksaveasfilename()
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except:
                print("unable to write to %s" % filename)
        if filename != "":
            self.saveDefocus(filename=filename)

    def saveDefocus(self, filename=None):
        "save current defocus and file number to a doc file"
        if filename != None:
            self.savefile = filename
        if self.savefile == "":
            filename = filedialog.asksaveasfilename()
            if filename == "":
                return 
            self.savefile = filename
        self.setFileLabels()

        if self.tfedfile == "":
            if self.verbose>=1 : print("defocus data will be saved to %s" % self.savefile)
            return

        micnum = self.filenumber(os.path.basename(self.tfedfile))
        defocus = int(float(self.defocus.get()))
        outfile = self.savefile

        if os.path.exists(outfile):
            headers = Spiderutils.getDocfileHeaders(outfile)

            # try to replace the line
            d = Spiderutils.readdoc(outfile, keys='all')
            keys = list(d.keys())
            found = 0
            for k in keys:
                mic = d[k][0]
                if mic == micnum:
                    d[k][1] = defocus
                    found = 1
                    break
            if found:
                Spiderutils.writedoc(outfile,columns=d)
            else:
                Spiderutils.writedoc(outfile,columns=[[micnum],[defocus]],mode='a')
        else:
            headers = ['MICROGRAPH','DEFOCUS']
            Spiderutils.writedoc(outfile,columns=[[micnum],[defocus]],headers=headers)
        if self.verbose>=1 : print("defocus %s saved to %s" % (defocus, outfile))
    
    def showGrid(self):
        if self.gridShow.get():
            self.ax.grid(True)
        else:
            self.ax.grid(False)

        self.fig.canvas.draw_idle()

    def showSquared(self):
        " variable changed automatically in checkbutton "
        if self.tfedfile != "":
            self.plotCtfProfile(filename=self.tfedfile)

    def quit(self):
        if hasattr(self,'ParmWindow'):
            try:
                self.ParmWindow.destroy()
            except:
                pass
        self.top.quit()

# ------- end CTFplot class definition

if __name__ == '__main__':

    args, tfed = parse_command_line()
    #print(args)
    #print('tfed',tfed)
    #exit()

    master = tkinter.Tk()
    master.title("CTF Match")
    master.option_add("*Font", "Helvetica 12 bold")
    CTFplot(master, args=args, roo=tfed)
    master.mainloop()
