#!/usr/bin/env python
#
# SOURCE:  ctfdemo.py 
#
# PURPOSE: Demonstration of CTF parameters
#
# Spider Python Library
# Copyright (C) 2006-2018  Health Research Inc., Menands, NY
# Email:    spider@health.ny.gov

import tkinter
from   tkinter import font
import math, os  #### from   math    import *
import Pmw
from matplotlib import figure
from matplotlib.backends import backend_tkagg
from Spider import Spiderutils

class CTFplot:
    " default values "
    def __init__(self, master,
                 cs        = 2.0,
                 defocus   = 20000,
                 kev       = 200,
                 pixelsize = 2.82,
                 src       = 0.0,    # Source size
                 spread    = 0.0,    # Defocus spread
                 acr       = 0.0,    # Amplitude contrast ratio
                 gep       = 2):     # Gaussian envelope parameter
        self.top = master
        self.top.title("ctfdemo")
        self.top.bind('<Control-t>', self.test)

        self.cs      = tkinter.StringVar(); self.cs.set(cs)
        self.defocus = tkinter.StringVar(); self.defocus.set(defocus)
        self.kev     = tkinter.StringVar(); self.kev.set(kev)
        self.pixsize = tkinter.StringVar(); self.pixsize.set(pixelsize)
        self.src     = tkinter.StringVar(); self.src.set(src)
        self.spread  = tkinter.StringVar(); self.spread.set(spread)
        self.acr     = tkinter.StringVar(); self.acr.set(acr)
        self.gep     = tkinter.StringVar(); self.gep.set(gep)

        self.vardict = {}

        self.gridShow = tkinter.IntVar()
        self.gridShow.set(0)
        self.envelopeShow = tkinter.IntVar()
        self.envelopeShow.set(0)
        self.squared      = tkinter.IntVar()
        self.squared.set(0)

        self.n             = 250  # number of samples
        self.max_spat_freq = 1.0 / (2.0 * float(self.pixsize.get()))
        self.X             = []
        self.Y             = []
        self.E             = []
        for i in range(self.n):
            self.X.append( (self.max_spat_freq / float(self.n)) * i)
            self.Y.append(0.0)
            self.E.append(0.0)

        self.kappa = -math.pi**2 / (16.0 * math.log(2.0))
        self.infinity = 1e50
        self.compute()
        acr = self.acr.get()
        if float(acr) == 0: self.acr.set(0.1)

        # ------- create the menu bar -------
        self.mBar = tkinter.Frame(master, relief='raised', borderwidth=1)
        self.mBar.pack(side='top', fill = 'x')

        # Make the File menu
        Filebtn = tkinter.Menubutton(self.mBar, text='File', underline=0,
                                 relief='flat')
        Filebtn.pack(side=tkinter.LEFT, padx=5, pady=5)
        Filebtn.menu = tkinter.Menu(Filebtn, tearoff=0)
        Filebtn.menu.add_separator()
        Filebtn.menu.add_command(label='Quit', underline=0,
                                     command=master.quit)
        Filebtn['menu'] = Filebtn.menu

        # Make the Option menu
        Optbtn = tkinter.Menubutton(self.mBar, text='Options', underline=0,
                                 relief='flat')
        Optbtn.pack(side=tkinter.LEFT, padx=5, pady=5)
        Optbtn.menu = tkinter.Menu(Optbtn, tearoff=0)

        Optbtn.menu.add_checkbutton(label='Grid', underline=0,
                                    command=self.showGrid)
        Optbtn.menu.add_checkbutton(label='Show Envelope', underline=0,
                                    command=self.showEnvelope)
        Optbtn.menu.add_checkbutton(label='Squared', underline=0,
                                    command=self.showSquared)
        Optbtn['menu'] = Optbtn.menu
       
        # ------- Widgets start here -------
        ff = tkinter.Frame(master)
        fg = tkinter.Frame(ff, relief='raised', borderwidth=2) # Upper left frame for plot

        # Create a Matplotlib Figure
        self.fig = figure.Figure(figsize=(5, 4), dpi=100)
        self.fig.suptitle("Transfer function demo")
        self.ax = self.fig.add_subplot(111)
        if self.gridShow.get() : self.ax.grid(True)
        #print("self.ax.xaxis._gridOnMajor", self.ax.xaxis._gridOnMajor)
        #print("self.ax.yaxis._gridOnMajor", self.ax.yaxis._gridOnMajor)
        self.ctf_model, = self.ax.plot(self.X, self.Y)  # model

        # Embed the Figure in the Tkinter Frame
        canvas = backend_tkagg.FigureCanvasTkAgg(self.fig, master=fg)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)

        self.envelope_line2d, = self.ax.plot(self.X, self.E)  # model
        if not self.envelopeShow.get() : self.envelope_line2d._visible = False

        self.g_height = 150 #int(self.g.extents("plotheight"))
        fg.columnconfigure(0, weight=1) 

        fp = tkinter.Frame(ff, relief='raised', borderwidth=2)  #Upper right frame for pixsize

        plabel = tkinter.Label(fp,text="pixelsize")
        pslider = tkinter.Scale(fp, orient='vertical', from_=0, to=6,
                       tickinterval = 1.00,
                       resolution = 0.01, label ="",
                       variable = self.pixsize,
                       length =  self.g_height,
                       showvalue=0,
                       command=self.pxsz_update)

        pentry = tkinter.Entry(fp, textvariable=self.pixsize, width=10, background='white')
        pentry.bind('<Return>', self.pxsz_update)
        plabel.grid(row=0, column=0)
        pentry.grid(row=1, column=0)
        pslider.grid(row=2, column=0)
   
        fg.grid(row=0, column=0, sticky='nsew')
        fp.grid(row=0, column=1, sticky='ns')
        ff.columnconfigure(0, weight=1)
        ff.rowconfigure(0, weight=1)
        ff.pack(side='top', fill='x') #, expand=1)

        # ------ the set of sliders -------

        self.sf = Pmw.ScrolledFrame(master, horizflex='expand', vertflex='fixed',
                                    vscrollmode='dynamic', hull_height=760)
        f = self.sf.interior()
        self.slider(f, start=0, end=50000, row=0,
                         label='defocus',
                         tickinterval=10000,
                         resolution=50,
                         variable = self.defocus)
        self.slider(f, start=0, end=500, row=1,
                         label='electron\nenergy (kev)',
                         tickinterval=100,
                         variable = self.kev)
        self.slider(f, start=0, end=5.0, row=2,
                         label='spherical\naberration',
                         tickinterval=1,
                         variable = self.cs)
        self.slider(f, start=0, end=0.005, row=3,
                         label='source\nsize',
                         tickinterval=0.001,
                         digits = 2,
                         variable = self.src)
        self.slider(f, start=0, end=500, row=4,
                         label='defocus\nspread',
                         tickinterval=100,
                         variable = self.spread)
        self.slider(f, start=0, end=0.5, row=5,
                         label='amplitude\ncontrast ratio',
                         tickinterval=0.1,resolution=0.01,
                         variable = self.acr)
        self.slider(f, start=0, end=2, row=6,
                         label='Gaussian\nenvelope',
                         tickinterval=0.5,
                         variable = self.gep)
        f.columnconfigure(2, weight=1) # makes column expandable
        self.sf.pack(side='bottom', expand=1, fill='both')

    def slider(self, master, start=0, end=10, row=0, label="",
               tickinterval=1, resolution=None, digits=0,variable = None):
        """
        Build sliders for a given parameter
        """

        lab = tkinter.Label(master, text=label)
        if resolution == None:
            resolution = float(tickinterval) / 50.0
        slider = tkinter.Scale(master, orient='horizontal', from_=start, to=end,
                       tickinterval = tickinterval,
                       resolution = resolution, label ="",
                       variable = variable,
                       showvalue=0,
                       #length = self.g_width,
                       digits = digits,
                       command=self.update_plot)
        ent = tkinter.Entry(master, textvariable=variable, width=10, background='white')
        ent.bind('<KeyPress>', self.update_plot)

        lab.grid(row=row, column=0, sticky='ne', padx=5, pady=5)
        ent.grid(row=row, column=1, sticky='n', padx=5, pady=5)
        slider.grid(row=row, column=2, sticky='ew', padx=5, pady=5)
        

    def compute(self):
        """
        Computes CTF as a function of spatial frequency
        Does NOT re-draw plots
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

        pixsize = float(self.pixsize.get())
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
        squared = self.squared.get()

        for i in range(self.n):
            ak = i * dk
            p  = ak**3 - dz1 * ak
            ch = math.exp(ak*4 * kappa)
            self.E[i] = (math.exp(f*q1*p**2)*ch)*2*math.exp(-env1*ak**2)
            qqt = 2.0*math.pi*(0.25*ak**4 - 0.5*dz1*ak**2)
            qqt1 = (1.0-acr)*math.sin(qqt)-acr*math.cos(qqt)
            self.Y[i] = self.E[i] * qqt1
            if squared:
                self.E[i] = (self.E[i])**2
                self.Y[i] = (self.Y[i])**2

    def update_plot(self, scalevalue=None):
        self.compute()
        self.ctf_model.set_ydata(self.Y)
        self.envelope_line2d.set_ydata(self.E)
        self.fig.canvas.draw_idle()

    def pxsz_update(self, scalevalue=None):
        # Updates pixel size

        ###Spiderutils.whocalledme(265)
        pixsize = float(self.pixsize.get())
        ###Spiderutils.whocalledme(267, "pixsize", pixsize)
        if pixsize != 0:
            self.max_spat_freq = 1.0 / (2.0 * pixsize)
            for i in range(self.n):
                self.X[i] = i* (self.max_spat_freq / float(self.n))

            # Pixel size is the only parameter that affects the x-axis, so we won't use update()
            ###self.update_plot()
            self.compute()
            self.ctf_model.set_xdata(self.X)
            self.ctf_model.set_ydata(self.Y)
            self.envelope_line2d.set_xdata(self.X)
            self.envelope_line2d.set_ydata(self.E)
            self.resetYaxis()

    def test(self, event=None):
        print('winfo_geometry:', self.top.geometry() )

    def resetYaxis(self):
        """
        We assume we will have re-computed the range when we run this function.
        """

        ymin = ymax = self.Y[0]
        for i in range(self.n):
            if ymin > self.Y[i]: ymin = self.Y[i]
            if ymax < self.Y[i]: ymax = self.Y[i]
        ###Spiderutils.printvars(['ymin','ymax'])

        # Redraw
        self.ax.relim()
        self.ax.autoscale_view()
        self.fig.canvas.draw_idle()

    def openFile(self):
        return("filename")
    
    def showGrid(self):
        ##print("self.ax.xaxis._major_tick_kw['gridOn']", self.ax.xaxis._major_tick_kw['gridOn'])
        ##print("self.ax.yaxis._major_tick_kw['gridOn']", self.ax.yaxis._major_tick_kw['gridOn'])
        do_show = not self.gridShow.get()
        self.gridShow.set(do_show)
        if do_show:
            ###print("Turning on grid")
            self.ax.grid(True)
        else:
            ###print("Turning off grid")
            self.ax.grid(False)
        ###is_toggled = self.gridShow.get() ; Spiderutils.printvars("is_toggled")

        self.fig.canvas.draw_idle()

    def showEnvelope(self):
        do_show = self.envelopeShow.get()
        self.envelopeShow.set(not do_show) #### = not self.envelopeShow  ####
        ###do_show = self.envelopeShow.get()

        if self.envelopeShow.get():
            ##print("Drawing envelope")
            self.envelope_line2d._visible = True
        else:
            ##print("Not drawing envelope")
            self.envelope_line2d._visible = False
        self.fig.canvas.draw()

    def showSquared(self):
        self.squared.set(not self.squared.get())
        self.compute()
        self.ctf_model.set_ydata(self.Y)
        self.resetYaxis()

# ------- end CTFplot class definition

if __name__ == '__main__':

    master = tkinter.Tk()
    master.option_add("*Font", "Helvetica 12 bold")

    c = CTFplot(master)
    master.geometry("574x819")
    master.mainloop()
