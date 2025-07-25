#!/usr/bin/env python
#
# SOURCE:   spider/spire/bin/classavg.py 
#
# PURPOSE:  Tool for creating & viewing class averages
#
# Spider Python Library
# Copyright (C) 2006-2018  Health Research Inc., Menands, NY
# Email:  spider@health.ny.gov

import os,sys
import montage
import Pmw
import argparse
import glob

import tkinter  #### from   tkinter           import *
from   tkinter      import filedialog
from   PIL          import ImageTk

from   Spider       import Spiderutils, SpiderImageSeries
###from   Spider       import SpiderImagePlugin # 2018 al import *

USAGE = """
  %s <class_averages> <options>

Class averages can be delimited by spaces and/or expanded with wild cards, e.g.:
  %s classavg*.spi
  %s classavg064.spi classavg068.spi

If a template is used for class docs or particle images, enclose it in quotes, e.g.:
  %s classavg*.spi --doc "docclass*.spi"
The correct number of asterisks will be generated automatically.

Options can be displayed with one of the following:
  %s -h
  %s --help


""" % ( (os.path.basename(__file__),)*6 )
MODIFIED="Modified 2025 Jul 25"

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
        "--doc",
        type=str,
        default=None,
        help="SPIDER doc file example")

    parser.add_argument(
        "--img",
        type=str,
        default=None,
        help="Single image example")

    parser.add_argument(
        "--ncol",
        type=int,
        default=None,
        help="Number of columns")

    parser.add_argument(
        '--label',
        action="store_true",
        help='Flag to show filenames in particle images')

    return parser.parse_known_args()

# -------------------------------------------------------------------
# classAverages:  Inherits from support.montage
#                 overrides makeMenus() and display()

class classAverages(montage.montage): 
    
    def __init__(self, master, imagelist,
                 title="Class Averages",
                 ncol=None, args=None):
        
        if len(imagelist) < 1: return
        self.master = master
        montage.montage.__init__(self, master,
                                imagelist=imagelist,
                                title=title,
                                ncol=ncol,
                                useLabels=True)
        self.top.protocol("WM_DELETE_WINDOW", master.quit)

        self.args= args
        self.docfile = self.parseTemplates('doc')
        self.serfile = self.parseTemplates('img')

        # set up some templates
        self.doctemplate = tkinter.StringVar()
        self.doctemplate.set(self.docfile)   # display only the basename
        self.sertemplate = tkinter.StringVar()
        self.sertemplate.set(self.serfile)        # particle images
        
        self.extension = os.path.splitext(imagelist[0])[1]
        if self.extension != "":
            ext = self.extension
            self.filetypes = [ ("", "*"+ext), ("All files", "*") ]
        else:
            self.filetypes = [ ("All files", "*") ]

        self.makeMenus()
        self.createMontage()

    def parseTemplates(self, tag):
        # Parse templates from command line

        # Default is empty
        value = ""
        if tag in vars(self.args):
            tag_value= vars(self.args)[tag]
            if tag_value:
                # Look for single file vs wild cards
                if tag_value.find("*") < 0 and tag_value.find("?") < 0:
                    value= Spiderutils.name2template(tag_value)

                    # Check if text file vs stack
                    if not Spiderutils.istextfile(tag_value):
                        dtype = Spiderutils.spiderInfo(tag_value)[0]

                        # If it's a stack, don't convert it to a template
                        if dtype == "stack":
                            value= tag_value
                    # End text0file IF-THEN
                # Expand wild card
                else:
                    filelist= glob.glob(tag_value)
                    if len(filelist) == 0:
                        print(f"\nERROR!! No files present with the pattern '{tag_value}'")
                        print(    "  Exiting...\n")
                        exit()
                    else:
                        value= Spiderutils.name2template(filelist[0])
                # End wild-card IF-THEN
            # End non-empty-tag IF-THEN
        # End tag-found IF-THEN

        return value

    # ------- override the menu bar functions -------
    def makeMenus(self):
        self.mBar = tkinter.Frame(self.top, relief='raised', borderwidth=1)
        self.mBar.pack(side='top', fill = 'x')
        self.balloon = Pmw.Balloon(self.top)
        
        # Make the File menu
        Filebtn = tkinter.Menubutton(self.mBar, text='File', underline=0,
                                 relief='flat')
        Filebtn.pack(side='left', padx=5, pady=5)
        Filebtn.menu = tkinter.Menu(Filebtn, tearoff=0)
        Filebtn.menu.add_command(label='Class avgs',
                                 command=self.getClassAverages)
        Filebtn.menu.add_command(label='Templates',
                                 command=self.callTemplates)
        Filebtn.menu.add_command(label='Close all windows',
                                 command=self.closeWindows)
        Filebtn.menu.add_separator()
        Filebtn.menu.add_command(label='Quit', underline=0,
                                     command=self.master.quit)
        Filebtn['menu'] = Filebtn.menu
    
        # Make the Display menu (same as montage.py)
        Dspbtn = tkinter.Menubutton(self.mBar, text='Display', relief='flat')
        Dspbtn.pack(side='left', padx=5, pady=5)
        Dspbtn.menu = tkinter.Menu(Dspbtn, tearoff=0)

        Dspbtn.menu.add_command(label='no. columns', underline=0,
                                    command=self.displayParms)
        Dspbtn.menu.add_checkbutton(label='show filenames', underline=0,
                                    variable=self.showVar,
                                    command=self.displayParms_1)
        # 'size' has a submenu of checkbuttons
        Dspbtn.menu.sizes = tkinter.Menu(Dspbtn.menu)
        Dspbtn.menu.sizes.add_radiobutton(label='1/2', underline=0,
                                          variable=self.sizeVar, value=0,
                                          command=self.displayParms_2)
        Dspbtn.menu.sizes.add_radiobutton(label='1x', underline=0,
                                          variable=self.sizeVar, value=1,
                                          command=self.displayParms_2)
        Dspbtn.menu.sizes.add_radiobutton(label='2x', underline=0,
                                          variable=self.sizeVar, value=2,
                                          command=self.displayParms_2)
        Dspbtn.menu.add_cascade(label='image size', menu=Dspbtn.menu.sizes)
        Dspbtn['menu'] = Dspbtn.menu

    def closeWindows(self):
        winlist = self.top.winfo_children()
        for win in winlist:
            if win.winfo_exists():
                if win.winfo_class() == 'Toplevel':
                    win.destroy()        

    def hello(self, im):
        " filename is the classavg image "
        if self.docfile == "" or self.serfile == "":
            self.callTemplates()
            Spiderutils.whocalledme(116, ['doctemplate','sertemplate'], [self.doctemplate.get(),self.sertemplate.get()])

        filename = im.info['filename']
        title = "images for class: " + os.path.basename(filename)
        newtop = tkinter.Toplevel(self.top)

        tmp = self.doctemplate.get()
        doc = Spiderutils.template2filename(tmp, os.path.basename(filename))
        if len(doc) < 1:
            return
        if not os.path.exists(doc):
            print(("Unable to find " + doc))
            return
        D = Spiderutils.readdoc(doc, keys='all')
        plist = []
        files = list(D.keys())

        # If particle file exists without converting to a template, it might be a stack
        is_stack= False
        ###print(os.path.basename(__file__),":147:serfile:",self.serfile,os.path.exists(self.serfile))
        if os.path.exists(self.serfile):
            filetype= Spiderutils.spiderInfo(self.serfile)[0]
            if filetype == 'stack':
                is_stack= True

        if is_stack:
            ###print(os.path.basename(__file__),":155:is_stack:",is_stack)
            # We only need to pass the stack file once, along with the selection file
            m = montage.montage(newtop, [self.serfile], title=title, useLabels=self.args.label, selectdoc=doc)
        else:
            for f in files:
                num = int(D[f][0])  # each element is a list (of column data)
                imgfilename = Spiderutils.template2filename(self.serfile, num)
                plist.append(imgfilename)
            m = montage.montage(newtop, imagelist=plist, title=title,
                                useLabels=self.args.label)

        # If no imagelist can be loaded above, the following will not work
        if len(m.imagelist) > 0:
            m.makeMenus()
            m.createMontage()

    def callTemplates(self):
        gtwin = tkinter.Toplevel(self.top)
        self.getTemplates(gtwin)
        self.top.wait_window(gtwin)  # wait til template window gone
        # if they typed in w/o asterisks..
        doc = self.doctemplate.get()
        if len(doc) > 0:
            self.docfile = doc
            if doc.find("*") < 0:
                tmp = Spiderutils.name2template(doc)
                self.doctemplate.set(tmp)
        ser = self.sertemplate.get()
        if len(ser) > 0:
            self.serfile = ser
            if ser.find("*") < 0:
                tmp = Spiderutils.name2template(ser)
                self.sertemplate.set(tmp)

    def getTemplates(self, win):
        win.title("Templates")
        ftop = tkinter.Frame(win)
        bdoc = tkinter.Button(ftop, text="Doc file template: ",
                      command = lambda w=win, d='doc': self.setTemplates(w,d))
        edoc = tkinter.Entry(ftop, textvariable = self.doctemplate)
        bser = tkinter.Button(ftop, text="Particle template: ",
                      command = lambda w=win, d='ser': self.setTemplates(w,d))
        eser = tkinter.Entry(ftop, textvariable = self.sertemplate)
        bdoc.grid(row=0, column=0, sticky='w')
        edoc.grid(row=0, column=1, sticky='nsew')
        ftop.columnconfigure(1, weight=1)  # make entry expand
        bser.grid(row=1, column=0, sticky='w')
        eser.grid(row=1, column=1, sticky='nsew')
        ftop.pack(side='top', fill='both', expand=1)
        
        fbut = tkinter.Frame(win)
        tkinter.Button(fbut, text="Done", command=win.destroy).pack(padx=5, pady=5)
        fbut.pack()

    def setTemplates(self, parent, which='doc'):
        filename = filedialog.askopenfilename(parent=parent, filetypes=self.filetypes)
        if len(filename) < 1:
            return
        tmp = Spiderutils.name2template(filename)
        if which == 'doc':
            self.doctemplate.set(tmp)
        else:
            self.sertemplate.set(tmp)

    def getClassAverages(self):
        filenames = filedialog.askopenfilename(filetypes=self.filetypes, multiple=1)
        if len(filenames) < 1:
            return
        self.imagelist = SpiderImageSeries.loadImageSeries(filenames)
        self.ncol = self.montagesize()
        self.createMontage()

    # display here overrides definition in montage class
    def display(self, parent):
        size = self.sizeVar.get()
        xhalf = int(self.xsize/2)
        xtwice = 2*self.xsize
        yhalf = int(self.ysize/2)
        ytwice = 2*self.ysize
        if size != 1:
            if size == 0:
                x,y = xhalf, yhalf
            elif size == 2:
                x,y = xtwice,ytwice
        else:
            x,y = self.xsize, self.ysize
            
        useLabels = self.useLabels
        i = 0
        j = 0
        for im in self.imagelist:
            ix,iy = im.size
            if ix != x or iy != y:
                icpy = im.copy()  # o.w. orig is resized
                img = icpy.resize( (x,y) )
            else:
                img = im

            photo = ImageTk.PhotoImage(img, palette=256, master=parent)
            b = tkinter.Button(parent,image=photo, command=lambda f=img: self.hello(f))
            b.photo = photo
            filename = im.info['filename']
            b.grid(row=j, column=i)
            if useLabels:
                lb = tkinter.Label(parent, text=os.path.basename(filename))
                lb.grid(row=j+1, column=i)
            i += 1
            if i > self.ncol-1:
                i = 0
                j += 1
                if useLabels: j += 1 # incr j twice for labels

# -------------------------------------------------------------------
if __name__ == "__main__":

    args, filelist = parse_command_line()
    #print(args)
    #print('filelist',filelist)
    #exit()

    # Make sure files are actually files and not unrecognized arguments
    nonfiles = []
    for fn in filelist:
        if not os.path.exists(fn) : nonfiles.append(fn)

    if len(nonfiles) > 0:
        print()
        print( "ERROR!! The following are either unrecognized flags or non-existent files:")
        print( " ", " ".join(nonfiles) )
        print()
        print( "  Exiting...\n")
        exit()

    if not len(filelist):
        filelist = filedialog.askopenfilename(multiple=1)
        if len(filelist) < 1:
            print("Usage:")
            print(USAGE)
            sys.exit(1)
    
    root = tkinter.Tk()
    root.option_add("*Font", "Helvetica 12 bold")
    mn = classAverages(root, filelist, ncol=args.ncol, args=args)
    root.mainloop()
    
