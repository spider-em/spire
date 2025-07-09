#!/usr/bin/env python
#
# SOURCE:  spider/spire/bin/montage.py 
#
# PURPOSE: Display a set of SPIDER images files in a window.
#
# Spider Python Library
# Copyright (C) 2006-2018  Health Research Inc., Menands, NY
# Email:  spider@health.ny.gov

import Pmw
import os,sys

try:
    import PIL
except ImportError as e:
    print(f"\nERROR!! {e}")
    print(  f"  Please install 'pillow' using conda or pip")
    print(   "  Exiting...\n")
    exit()

from   PIL     import ImageTk  # for some reason, PIL.ImageTk doesn't work
import tkinter
from   tkinter import filedialog, messagebox, font
import math
from Spider    import SpiderImageSeries, Spiderutils  #### import Spider

class selectionClass:
    def __init__(self, value, key, color, label, activecolor=None):
        self.value  = value   # Int
        self.key    = key     # String of a number
        self.color  = color
        self.label  = label   # For radiobutton menu
        self.active = ""
        if activecolor != None:
            self.active = activecolor

COLORS = { 1 : ('green', 'light green'),
           2 : ('red', 'FF7F7F'),
           3 : ('blue', 'light blue'),
           4 : ('yellow', '#FFFF7F'),
           5 : ('brown', '#A68064'),
           6 : ('purple', '#FF7fFF'),
           7 : ('black', 'gray'),
           8 : ('orange', "#E47833")
           }

def newcolor(value):
    keys = list(COLORS.keys())
    if value > max(keys) or value < min(keys):
        return ("gray", "gray")
    else:
        return COLORS[value]

# when is this used?
def volume2imagelist(filename):
    " Converts a Spider volume into a list of PIL images"

    import Spiderarray
    import numpy as np

    imlist = []
    V = Spiderarray.spider2array(filename)
    x = V.flat    # flatten to 1D array to get extrema
    amax = max(x)
    amin = min(x)
    m = 255.0 / (amax-amin)
    b = -m * amin
    ###N = ((m*V)+b).astype(Numeric.UnsignedInt8) # mV+b returns an array
    N = ((m*V)+b).astype(np.uint8) # mV+b returns an array

    zsize, ysize, xsize = N.shape
    for z in range(zsize):
        im = Spiderarray.array2image(N[z])
        im.info['filename'] = str(z)
        imlist.append(im)
    return imlist

# ******************************************************************************
# class montage
#       Input image list can be a list of filenames or a previously loaded
#       list of Image.images
#       Create the toplevel window outside and pass it in

class montage:
    def __init__(self, master, imagelist, title=None,
                 ncol=None, useLabels=0, savefilename=None, startkey="1"):
        self.top = master   #Toplevel(master)
        ##import inspect
        ##print(f"{os.path.splitext( os.path.basename(__file__) )[0]}:82:\t{inspect.stack()[0][3]}() called by {inspect.stack()[1][3]}()")
        if imagelist == None:
            filelist = filedialog.askopenfilename(multiple=1, title='Select a set of images')
            if len(filelist) < 1:
                print("No images loaded, exiting...")
                exit()
            self.imagelist = SpiderImageSeries.loadImageSeries(filelist)
        elif type(imagelist[0]) == type("string"):  # i.e., a filename
            self.imagelist = SpiderImageSeries.loadImageSeries(imagelist)
        else:
            import inspect ; print(f"{os.path.splitext( os.path.basename(__file__) )[0]}:93:\t{inspect.stack()[0][3]}() :\ttype(imagelist[0]) = {type(imagelist[0])}")
            self.imagelist = SpiderImageSeries.loadImageSeries(imagelist)

        if len(self.imagelist) < 1:
            print("No images loaded")
            return
            
        if title == None: title = "Images"
        self.top.title(title)
        self.useLabels = useLabels
        # set some size variables
        self.xmax, self.ymax = self.top.winfo_screenwidth(), self.top.winfo_screenheight()
        # get size of a single image
        im = self.imagelist[0]
        self.xsize,self.ysize = im.size
        if ncol == None:
            self.ncol = self.montagesize()
        else:
            self.ncol = ncol
            
        self.font = font.Font(family="mincho", size=12)
        self.startkey = tkinter.StringVar()
        self.startkey.set(startkey)
        
        if savefilename != None:
            self.savefilename = savefilename
        else:
            self.savefilename = ""

        # some Tk Variables
        self.ncolVar = tkinter.StringVar()
        self.sizeVar = tkinter.IntVar()
        self.sizeVar.set(1)
        self.showVar = tkinter.IntVar()
        self.showVar.set(self.useLabels)
        self.bd = 2  # Border around images
        sysbgd = self.systembackground = "#d9d9d9"
        actbgd = "#ececec"

        # a selection class = ( int(value), 'color', 'key', 'label')

        self.selectClasses = {}
        self.selectClasses['0'] = selectionClass(0,'0',sysbgd,'deselect', actbgd)
        self.selectClasses['1'] = selectionClass(1,'1','green','class 1', 'light green')
        self.selectClasses['2'] = selectionClass(2,'2','red','class 2', 'pink')
        self.selectClasses['3'] = selectionClass(3,'3','blue','class 3', 'light blue')
        self.selectedColor = tkinter.StringVar()
        self.selectedColor.set('1')
        self.selectedColor.trace_variable('w', self.selectcallback)

        # call these methods explicitly or override them
        #self.makeMenus()
        #self.createMontage()

    def selectcallback(self, name, index, mode):
        "Called whenever self.selectedColor changes "
        key = self.selectedColor.get()
        sc = self.selectClasses[key]
        self.ClassButton.configure(text=sc.label, background=sc.color)
        
    def makeMenus(self):
        # ------- Create the menu bar -------
        self.mBar = tkinter.Frame(self.top, relief='raised', borderwidth=1)
        self.mBar.pack(side='top', fill = 'x')
        self.balloon = Pmw.Balloon(self.top)

        # Make the Display menu
        Dspbtn = tkinter.Menubutton(self.mBar, text='Display', relief='flat', font=self.font)
        ###import inspect; print(f"{os.path.splitext( os.path.basename(__file__) )[0]}:169:\t{inspect.stack()[0][3]}() :\tDspbtn.cget('font') = '{Dspbtn.cget('font')}'")
        Dspbtn.pack(side=tkinter.LEFT, padx=5, pady=5)
        Dspbtn.menu = tkinter.Menu(Dspbtn, tearoff=0)

        Dspbtn.menu.add_command(label='no. columns', underline=0,
                                    command=self.displayParms, font=self.font)
        Dspbtn.menu.add_checkbutton(label='show filenames', underline=0,
                                    variable=self.showVar,
                                    command=self.displayParms_1, font=self.font)

        # 'size' has a submenu of checkbuttons
        Dspbtn.menu.sizes = tkinter.Menu(Dspbtn.menu, tearoff=0)
        Dspbtn.menu.sizes.add_radiobutton(label='1/2', underline=0,
                                          variable=self.sizeVar, value=0,
                                          command=self.displayParms_2, font=self.font)
        Dspbtn.menu.sizes.add_radiobutton(label='1x', underline=0,
                                          variable=self.sizeVar, value=1,
                                          command=self.displayParms_2, font=self.font)
        Dspbtn.menu.sizes.add_radiobutton(label='2x', underline=0,
                                          variable=self.sizeVar, value=2,
                                          command=self.displayParms_2, font=self.font)
        Dspbtn.menu.add_cascade(label='image size', menu=Dspbtn.menu.sizes, font=self.font)
        Dspbtn.menu.add_separator()
        Dspbtn.menu.add_command(label='Quit', underline=0,
                                     command=self.top.destroy, font=self.font)
        Dspbtn['menu'] = Dspbtn.menu
        
        # Make the Select menu
        Selbtn = tkinter.Menubutton(self.mBar, text='Select', relief='flat', font=self.font)
        Selbtn.pack(side=tkinter.LEFT, padx=5, pady=5)
        Selbtn.menu = tkinter.Menu(Selbtn, tearoff=0)
        Selbtn.menu.add_command(label='Save selections', underline=0,
                                command=self.saveSelections, font=self.font)
        Selbtn.menu.add_command(label='Add a class', underline=0,
                                command=self.addClass, font=self.font)
        Selbtn['menu'] = Selbtn.menu
        
        # Make the Class menu
        sc = self.selectClasses[self.selectedColor.get()]
        Classbtn = tkinter.Menubutton(self.mBar, text=sc.label, relief='flat',
                              background=sc.color, font=self.font)
        Classbtn.pack(side=tkinter.LEFT, padx=5, pady=5)
        Classbtn.menu = tkinter.Menu(Classbtn, tearoff=0)
        keys = list(self.selectClasses.keys())
        keys.sort()
        for key in keys:
            sc = self.selectClasses[key]
            Classbtn.menu.add_radiobutton(label = sc.label, underline=0,
                                        value = sc.value,
                                        foreground = 'white',
                                        background = sc.color,
                                        activebackground= sc.active,
                                        activeforeground= 'black',
                                        variable=self.selectedColor,
                                        font=self.font)
        Classbtn['menu'] = Classbtn.menu
        self.ClassMenu = Classbtn.menu  # for adding stuff later
        self.ClassButton = Classbtn

        # startkey
        sklabel = tkinter.Label(self.mBar, text='    start key:', font=self.font)
        sklabel.pack(side='left',padx=2, pady=5)
        skentry = tkinter.Entry(self.mBar, textvariable=self.startkey, width=5, font=self.font)
        skentry.pack(side='left',padx=8, pady=5) 

    def montagesize(self):
        " Returns number of columns to use "
        nimgs = len(self.imagelist)
        labelheight = 0
        if self.useLabels != 0:
            labelheight = 20 # pixels
        aspect = self.xsize / float(self.ysize + labelheight)
        # approximate a 1.5:1 wd:ht
        nrows = math.sqrt( 2*nimgs*aspect / 3.0)
        f = nimgs / nrows
        i = int(f)
        if f%i > 0.5:
            i += 1
        ncols = i
        return ncols
    
    def createMontage(self):
        if hasattr(self,'sf'): self.sf.destroy()
        
        self.sf = Pmw.ScrolledFrame(self.top)
        self.fr = self.sf.interior()
        self.display(self.fr)
        self.sf.pack(fill=tkinter.BOTH, expand=1)
        
        ht = self.fr.winfo_reqheight()
        wd = self.fr.winfo_reqwidth()
        if ht == 1 or wd == 1:
            self.fr.after(500, self.frsize)
        else:
            if ht < self.xmax and wd < self.ymax:
                self.sf.component("clipper").configure(height=ht)
                self.sf.component("clipper").configure(width=wd)
        self.top.lift()

    # Resizing: if the user changes the window size with the mouse, then the calls
    # below to configure the frame size have no effect
    # sizefrom(who="program") didn't help on SGI

    def frsize(self):
        " try to resize the window after the mainloop starts "
        ht = self.fr.winfo_reqheight()
        wd = self.fr.winfo_reqwidth()
        if ht == 1 or wd == 1:
            self.fr.after(500, self.frsize)
        else:
            if ht < self.xmax and wd < self.ymax:
                self.sf.component("clipper").configure(height=ht)
                self.sf.component("clipper").configure(width=wd)
        

    def display(self, parent):
        size   = self.sizeVar.get()
        xhalf  = int(self.xsize/2)
        xtwice = 2*self.xsize
        yhalf  = int(self.ysize/2)
        ytwice = 2*self.ysize
        if size != 1:
            if size == 0:
                x,y = xhalf, yhalf
            elif size == 2:
                x,y = xtwice,ytwice
        else:
            x,y = self.xsize, self.ysize
            
        useLabels = self.useLabels
        self.photolist = []
        i = 0
        j = 0
        for im in self.imagelist:
            ix,iy = im.size
            if ix != x or iy != y:
                icpy = im.copy()  # o.w. orig is resized
                img = icpy.resize( (x,y) )
            else:
                img = im

            photo = PIL.ImageTk.PhotoImage(img, palette=256, master=parent)
            if hasattr(im,'selectvalue'):
                sc = self.selectClasses[im.selectvalue]
                ib = tkinter.Label(parent, image=photo, bd=self.bd, background=sc.color)
            else:
                ib = tkinter.Label(parent, image=photo, bd=self.bd)
            ib.photo = photo
            filename = im.info['filename']
            ib.filename = filename
            ib.grid(row=j, column=i)
            ib.bind('<Button-1>', lambda event, w=ib, i=im: self.select(w,i))
            self.photolist.append(ib)
            
            if useLabels:
                lb = tkinter.Label(parent, text=os.path.basename(filename), font=self.font)
                lb.grid(row=j+1, column=i)
            i += 1
            if i > self.ncol-1:
                i = 0
                j += 1
                if useLabels: j += 1 # incr j twice for labels

    def select(self, widget, image):
        key = self.selectedColor.get()
        sc = self.selectClasses[key]
        widget.configure(background=sc.color)
        widget.selectvalue = sc.key
        image.selectvalue = sc.key

    def saveSelections(self):
        """
        Savasfilename can't append to a file - if the file exists an error
        message pops up.
        if output specified, don't ask (put it in window in menubar?)
        """
        filename = filedialog.asksaveasfilename(title="Save points into a doc file",
                                     initialfile=self.savefilename)
        if len(filename) == 0:
            return

        # Construct a dictionary to pass to writedocfile
        headers = ['file_number', 'class']
        F = {}
        key = self.startkey.get()
        try:
            key = int(key)
        except:
            key = 1

        for photo in self.photolist:
            filenumber = Spiderutils.getfilenumber(photo.filename)
            try:
                int(filenumber)
                if hasattr(photo, 'selectvalue'):
                    val = photo.selectvalue
                else:
                    val = '0'
                F[key] = [filenumber, val]
                key = key + 1
            except:
                print(("error getting file number from %s" % photo.filename))
                continue

        if Spiderutils.writedoc(filename, F, headers=headers, mode='a'):
            messagebox.showinfo("Data saved to file", "Data written to %s" % os.path.basename(filename))
        else:
            messagebox.showerror("Error!", "Unable to write to %s" % os.path.basename(filename))
            

    def addClass(self):
        # eg something like
        keys = list(self.selectClasses.keys())
        m = max(list(map(int,keys)))
        n = m + 1
        value = n
        key = str(n)
        color, activecolor = newcolor(value)
        label = 'class ' + str(n)
        sc = selectionClass(value,key,color,label,activecolor)
        self.selectClasses[key] = sc
        self.ClassMenu.add_radiobutton(label = sc.label, underline=0,
                                       value = sc.value,
                                       foreground = 'white',
                                       background = sc.color,
                                       activebackground= sc.active,
                                       activeforeground= 'black',
                                       variable=self.selectedColor)

    def displayParms_1(self):
        q = self.showVar.get()
        if q != self.useLabels:
            self.useLabels = q
            self.createMontage()
        
    def displayParms_2(self):
        self.createMontage()
        
    def displayParms(self):
        self.ncolVar.set(str(self.ncol))
        w = tkinter.Toplevel(self.top)
        w.title("Montage")
        self.parmWindow(w)
        self.top.wait_window(w) # Wait for window to be destroyed
        try:
            i = int(self.ncolVar.get())
            if i != self.ncol:
                self.ncol = i
                self.createMontage()
        except:
            print("Number of columns must be an integer")
            return

    def parmWindow(self,win):
        fe = tkinter.Frame(win)

        # Number of columns
        tkinter.Label(fe,text="no. columns:", font=self.font).pack(side='left', padx=2, pady=2)
        e = tkinter.Entry(fe, textvariable=self.ncolVar, font=self.font)
        e.pack(side='left', fill='x', expand=1, pady=2, padx=2)
        fe.pack(side='top',fill='both', expand=1)
        e.bind('<Return>', lambda e, w=win: self.parmquit(w))
	
        # Bottom
        fbut = tkinter.Frame(win, borderwidth=2) #relief='raised',
        tkinter.Button(fbut, text='Ok', command=win.destroy, font=self.font).pack(padx=2,pady=2)
        fbut.pack(side='bottom', fill='x', expand=1)

    def parmquit(self,win):
        win.destroy()

# -------------------------------------------------------------------

if __name__ == "__main__":

    root = tkinter.Tk()
    root.title('Montage.py')
        
	
    if sys.argv[1:]:
        filelist = sys.argv[1:]
    else:
        filelist = None
    
    mn = montage(root, filelist, useLabels=1)
    mn.makeMenus()
    mn.createMontage()

    root.mainloop()
