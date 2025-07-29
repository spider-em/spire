#!/usr/bin/env python
#
# SOURCE:  spider/spire/bin/montagefromdoc.py
#
# PURPOSE: Display montage of images listed in document file
#
# MONDIFICATIONS:
#    TO DO: read volumes
#    TO DO: parse non-docfile command-line argument as image series
#    TO DO: if stack file is selected with file browser, don't convert to template
#    TO DO: link right-click to external viewer
#    TO DO: invert should look for deselected particles instead of particles not of the current class (in case of 3 classes)
#    2025-07-09 -- updated to Python3
#    2012-04-10 -- labels greater than one million written in exponential notation
#    2012-03-19 -- writes to screen the directory of output doc, if specified
#    2009-12-04 -- exits from initial popup gracefully
#    2009-11-30 -- in readOutputDoc, unselected images are now colored (e.g., in red)
#    2009-11-20 -- bug fix for index in readOutputDoc
#    2009-10-31 -- can read pre-existing selection file with CTRL-r
#    2009-07-14 -- bug fix: under some circumstances, was overriding command-line image filename
#    2009-07-10 -- if label_col is 0, label is slice# (stacked) or filename (unstacked)
#    2009-05-11 -- looks for filenumber in directory name if not in filename
#    2009-04-23 -- linked CTRL-v to invert (CTRL-i still works)
#    2008-09-29 -- sorts keys in output doc-file
#    2008-09-29 -- image size recalculated for each new page
#    2008-09-29 -- file-number from command-line doc-file input carried to other files
#    2008-04-28 -- bug fix when labeling stacks
#    2007-12-20 -- attached GNU GPL
#    2007-12-17 -- added 1/4th size display option
#    2007-12-14 -- restored brightness slider
#    2007-11-27 -- shows pop-up window if doc file not found
#    2007-11-27 -- shortcuts CTRL-N and CTRL-P increment and decrement filenumber in Open Selections
#    2007-11-10 -- can use arbitrary doc-file column for particle-number
#    2007-10-11 -- can label with arbitrary column
#    2007-10-05 -- can use stacks now
#    2007-08-06 -- internally converts SPIDER images to "luminosity" format
#    2007-07-11 -- gets settings from ".montagefromdoc"
#    2007-07-07 -- added "undo filters" button, help pop-up window for keyboard shortcuts
#    2007-06-29 -- added "smooth" button -- removed incompatible (?) contrast slidebar

print("montagefromdoc.py, Modified 2025 Jul 29")

# Spider Python Library
# Copyright (C) 2006-2018  Health Research Inc., Menands, NY
# Email:  spider@health.ny.gov

import Pmw

import tkinter
from tkinter import messagebox, filedialog
import os, sys
from   Spider            import Spiderutils
try:
    from PIL import Image, ImageTk, ImageEnhance, ImageFilter
except ImportError as e:
    print(f"\nERROR!! {e}")
    print(   "  Please install 'pillow' using conda or pip")
    print(   "  Exiting...\n")
    exit()

def backup(filename):
    if os.path.exists(filename):
        found_vacancy = 0
        tiebreaker = 0
        shortdir = os.path.basename(os.path.dirname(filename))
        while not found_vacancy:
            test_filename = filename + '_' + str(tiebreaker)
            if os.path.exists(test_filename):
                tiebreaker += 1
            else:
                found_vacancy = 1
                short_old = os.path.join(shortdir, os.path.basename(filename))
                short_new = os.path.join(shortdir, os.path.basename(test_filename))
                print('Renamed', short_old, 'to', short_new)
                os.rename(filename, test_filename)

def renumberFromTemplate(infile,file2renumber,increment=0):
    # Similar like Spiderutils.template2filename
    # but substitutes numbers in parent directory in none in filename
    #
    # SYNTAX: 
    # (new_file_name, new_file_number) =
    # renumberFromTemplate(get_number_from, apply_number_to, plus_optional_increment)

    # Defaults
    renumbered_file = file2renumber
    newnumber = ''

    # Get filenumber from input file
    filenumber = Spiderutils.getfilenumber(infile)

    # if input doc has a number
    if filenumber:
        newnumber = int(filenumber) + increment
        template2renumber = Spiderutils.name2template(file2renumber)
        outfilenumber = Spiderutils.getfilenumber(file2renumber)
        if outfilenumber: renumbered_file = Spiderutils.template2filename(template2renumber,newnumber)
    # If input has no filenumber, check directory for number
    else:
        infiledir = os.path.dirname(infile)
        input_dirnum = Spiderutils.getfilenumber(infiledir)

        # If directory has a number...
        if input_dirnum:
            outfiledir = os.path.dirname(file2renumber)
            newnumber = int(input_dirnum) + increment
            output_dir_template = Spiderutils.name2template(outfiledir)
            renumbered_dir = Spiderutils.template2filename(output_dir_template,newnumber)
            outfilebase = os.path.basename(file2renumber)
            renumbered_file = os.path.join(renumbered_dir,outfilebase)

    return renumbered_file, newnumber

def clickOK(parent,win):
    win.destroy()

class selectionClass:
    def __init__(self, value, key, color, label, activecolor=None):
        self.value = value   # int
        self.key = key       # string of a number
        self.color = color
        self.label = label   # for radiobutton menu
        self.active = ""
        if activecolor != None:
            self.active = activecolor

class tmontage:
    # ******************************************************************************
    # class tmontage
    #   Purpose:
    #     input image list can be a list of filenames or a previously loaded
    #     list of Image.images
    #     Create the toplevel window outside and pass it in
    #
    #   Functions:
    #     __init__
    #     select
    #     invertSelect
    #     selectAll
    #     clearAll
    #     shiftSelect
    #     selectcallback
    #     test : to make sure that events are working
    #     saveSelections
    #     closeWindow
    #     openSelections
    #     setTitle
    #     increaseFilenum
    #     decreaseFilenum
    #     askSelections
    #     loadImageList
    #     readInputDoc
    #     readOutputDoc
    #     nextPage
    #     prevPage
    #     updatePage
    #     makeMenus
    #     saveClose
    #     shortcuts
    #     createMontage
    #     frsize : try to resize the window after the mainloop starts
    #     checksize
    #     display
    #     smooth
    #     updateSmooth
    #     updateBrightness
    #     orig2 : reset values
    #     displayParms_label
    #     showLabels
    #     labelWindow
    #     displayParms_size
    #     displayParms_colrow
    #     parmWindow
    #
    # ******************************************************************************

    def __init__(self, master, prefs,
                 title=None, # reverse=0, contrast=1.0,
                 brightness=1.0, selectedColor='1', deselectedColor='Red'):

        self.prefs = prefs
        self.docfile = prefs.docfile
        self.doc_var = tkinter.StringVar()
        self.doc_var.set(self.docfile)
        self.docdir = os.path.dirname(self.docfile)

        self.ncol = prefs.ncol
        self.maxrow = prefs.maxrow
        self.montage_size = self.ncol * self.maxrow

        self.page_var = tkinter.StringVar()
        print('Opening', self.docfile, prefs.serfile)

        self.particle_col = prefs.particle_col
        self.particle_var = tkinter.IntVar()
        self.particle_var.set(self.particle_col)

        self.readInputDoc()
        self.loadImageList()

        # check if stacked from first image
        fn = Spiderutils.template2filename(prefs.serfile,self.imagelist[0])
        im = Image.open(fn)
        if im.istack:
            self.isStack = True
            print("Particles are stacks")
            self.serfile = prefs.serfile
        else:
            self.isStack = False
            print("Particles are unstacked")
            self.serfile = Spiderutils.name2template(prefs.serfile)
        self.sertemplate = tkinter.StringVar()
        self.sertemplate.set(self.serfile)        # particle images

        # draw window
        self.top = master
        if title == None: 
            self.setTitle()

        self.useLabels = prefs.use_labels
        self.showVar = tkinter.IntVar()
        self.showVar.set(self.useLabels)

        self.text_label = prefs.text_label
        self.text_var = tkinter.StringVar()
        self.text_var.set(self.text_label)

        self.label_col = prefs.label_col
        self.column_var = tkinter.IntVar()
        self.column_var.set(self.label_col)

        # set some size variables
        self.xmax, self.ymax = self.top.winfo_screenwidth(), self.top.winfo_screenheight()

        # get size of a single image
        self.xsize,self.ysize = im.size

        # some Tk Variables
        self.ncolVar = tkinter.IntVar()
        self.maxrowVar = tkinter.IntVar()
        self.maxrowVar.set(self.maxrow)
        self.sizeVar = tkinter.IntVar()
        self.sizeVar.set(prefs.size)
        self.bd = 2  # border around images
        sysbgd = self.systembackground = "#d9d9d9"
        ###actbgd = "#ececec"
        self.last = 0

        self.savefilename = prefs.outfile
        self.savefile_var = tkinter.StringVar()
        self.savefile_var.set(self.savefilename)

#        self.reverse = reverse
#        if reverse == 1: self.revOrder()

        # contrast stuff
#        self.contrast = tkinter.DoubleVar()
#        self.contrast.set(contrast)

        self.brightness = tkinter.DoubleVar()
        self.brightness.set(brightness)

        self.num_smooths = 0

        self.havereaddoc_boolean = False

        self.top.bind('<Next>'     , self.nextPage)
        self.top.bind('<Prior>'    , self.prevPage)
        self.top.bind('<Control-o>', self.openSelections)
        self.top.bind('<Control-w>', self.closeWindow)
        self.top.bind('<Control-t>', self.test)
        self.top.bind('<Control-s>', self.saveSelections)
        self.top.bind('<Control-r>', self.readOutputDoc)
        self.top.bind('<Control-a>', self.selectAll)
        self.top.bind('<Control-i>', self.invertSelect)
        self.top.bind('<Control-v>', self.invertSelect)
        self.top.bind('<Control-p>', self.prefs.printSettings)
        self.top.bind('<Control-f>', self.showLabels)
        self.top.bind('<Delete>'   , self.clearAll)
        self.top.bind('<Return>'   , self.updatePage)

        self.actbgd = "#ececec"
        self.selectClasses = {}

        # colors from https://jfly.uni-koeln.de/color/
        #                       selectionClass value,key,color,   label,      active
        self.selectClasses['0'] = selectionClass(0,'0', sysbgd,  'Deselect',  self.actbgd)
        self.selectClasses['1'] = selectionClass(1,'1','#009e73','Turquoise','#6a9e90')
        self.selectClasses['2'] = selectionClass(2,'2','black',  'Black',    'gray50')
        self.selectClasses['3'] = selectionClass(3,'3','#0072b2','Blue',     '#789db3')
        self.selectClasses['4'] = selectionClass(4,'4','gray75', 'Lt gray',  'gray50')
        self.selectedColor = tkinter.StringVar()
        self.selectedColor.set(selectedColor)
        self.deselectedColor = tkinter.StringVar()
        self.deselectedColor.set(deselectedColor)
        self.selectedColor.trace_variable('w', self.selectcallback)

        self.sel_dictionary = {}

    def select(self, widget, image):
        goodcolor = self.selectedColor.get()
        sc = self.selectClasses[goodcolor]
        badcolor = self.deselectedColor.get()
        newcolor = sc.color
        currentcolor = widget.cget('background')
        if currentcolor == newcolor:              # then deselect
            sc = self.selectClasses['0']
            widget.configure(background=badcolor)
            widget.selectvalue = sc.key
            image.selectvalue = sc.key
            del self.sel_dictionary[widget.num]
        else:                              # o.w. select with new color
            widget.configure(background=sc.color)
            self.sel_dictionary[widget.num] = sc.key
        widget.selectvalue = sc.key
        image.selectvalue = sc.key

        # update last
        self.last = widget.order

    def invertSelect(self, event=None):
        goodcolor = self.selectedColor.get()
        sc = self.selectClasses[goodcolor]
        badcolor = self.deselectedColor.get()
        newcolor = sc.color
        for counter in range(len(self.photolist)):
            photo = self.photolist[counter]
            currentcolor = photo.cget('background')
            if currentcolor == newcolor:              # then deselect
                sc = self.selectClasses['0']
                photo.configure(background=badcolor)
                del self.sel_dictionary[photo.num]
            else:                              # o.w. select with new color
                sc = self.selectClasses[goodcolor]
                photo.configure(background=sc.color)
                self.sel_dictionary[photo.num] = sc.key
            photo.selectvalue = sc.key

    def selectAll(self, event=None):
        key = self.selectedColor.get()
        sc = self.selectClasses[key]

        for counter in range(len(self.photolist)):
            photo = self.photolist[counter]
            photo.configure(background=sc.color)
            photo.selectvalue = sc.key
            self.sel_dictionary[photo.num] = sc.key

    def clearAll(self, event=None):
        sc = self.selectClasses['0']
        for counter in range(len(self.photolist)):
            photo = self.photolist[counter]
            photo.configure(background=sc.color)
            photo.selectvalue = sc.key
            if photo.num in self.sel_dictionary :
                del self.sel_dictionary[photo.num]

    def shiftSelect(self, widget, image):
        # widget order is numbered from 1..n

        # check if selecting forward or backward
        if widget.order > self.last:
            start = self.last
            end = widget.order
        else:
            # backwards
            start = widget.order - 1
            end = self.last

        key = self.selectedColor.get()
        sc = self.selectClasses[key]

        # loop through keys in range
        for counter in range(start, end):
            photo = self.photolist[counter]
            photo.selectvalue = sc.key
            photo.configure(background=sc.color)
            self.sel_dictionary[photo.num] = sc.key
        self.last = widget.order

    def selectcallback(self, name, index, mode):
        "called whenever self.selectedColor changes "
        key = self.selectedColor.get()
        print('New color:', self.selectClasses[key].label)

    def test(self, event=None):
        import inspect ; print(f"{os.path.splitext( os.path.basename(__file__) )[0]}:\t{inspect.stack()[0][3]}() called by {inspect.stack()[1][3]}()")

    def saveSelections(self, event=None):
        # construct a dictionary to pass to writedocfile
        filename = self.savefilename
        headers = ['file_number', 'class']
        F = {}
        key = 0
        dict_keys = list(self.sel_dictionary.keys())
        dict_keys.sort()

        for num in dict_keys:
            key = key +1
            F[key] = [num, self.sel_dictionary[num]]

        backup(filename)
        if Spiderutils.writeSpiderDocFile(filename,F, headers=headers, append=1):
            print('Wrote', key, 'keys to %s' % filename)
        else:
            messagebox.showerror("Error!", "Unable to write to %s" % filename)


    def closeWindow(self, event=None):
        self.top.destroy()

    def openSelections(self, event=None):
        doc_win = tkinter.Toplevel(self.top)
        doc_win.title("Open montage doc")
        doc_frame = tkinter.Frame(doc_win, padx=5, pady=5)

        doc_button = tkinter.Button(doc_frame, text='Choose montage doc',
            command = lambda w=doc_win, d='doc' : self.askSelections(w,d))
        doc_entry = tkinter.Entry(doc_frame, textvariable=self.doc_var, width=24)

        ser_button = tkinter.Button(doc_frame, text='Choose image template',
            command = lambda w=doc_win, d='ser' : self.askSelections(w,d))
        ser_entry = tkinter.Entry(doc_frame, textvariable=self.sertemplate, width=24)

        out_button = tkinter.Button(doc_frame, text='Choose output doc',
            command = lambda w=doc_win, d='out' : self.askSelections(w,d))
        out_entry = tkinter.Entry(doc_frame, textvariable=self.savefile_var, width=24)

        doc_button.grid(row=0, column=0)
        doc_entry.grid(row=0, column=1)
        ser_button.grid(row=1, column=0)
        ser_entry.grid(row=1, column=1)
        out_button.grid(row=2, column=0)
        out_entry.grid(row=2, column=1)
        doc_frame.pack()

        # Done
        quit_frame = tkinter.Frame(doc_win, padx=40)
        decr_button = tkinter.Button(quit_frame, text="Decr.", command = lambda w=doc_win: self.decreaseFilenum(w))
        decr_button.pack(side='left', pady=4)
        incr_button = tkinter.Button(quit_frame, text="Incr.", command = lambda w=doc_win: self.increaseFilenum(w))
        incr_button.pack(side='left', pady=4)
        tkinter.Button(quit_frame, text="Done", command=doc_win.destroy).pack(side='right', pady=4)
        quit_frame.pack(fill='x')

        doc_win.bind('<Return>',    lambda p=self.top, w=doc_win: clickOK(p,w))
        doc_win.bind('<Control-p>', lambda w=doc_win: self.decreaseFilenum(w))
        doc_win.bind('<Control-n>', lambda w=doc_win: self.increaseFilenum(w))
        self.top.wait_window(doc_win)

        # if inputs have changed
        if self.doc_var.get() != self.docfile or self.sertemplate.get() != self.serfile : 
            self.docfile = self.prefs.docfile = self.doc_var.get()
            self.serfile = self.prefs.serfile = self.sertemplate.get()
            self.docdir = os.path.dirname(self.docfile)
            print('Opening', self.docfile, self.serfile)
            self.prefs.saveSettings()

            self.setTitle()  # self.top.title("Montage from " + os.path.basename(self.docfile))

            if os.path.exists(self.docfile):
                self.readInputDoc()
                self.loadImageList()
                self.havereaddoc_boolean = False
                self.createMontage()
                self.updateSmooth()
            else:
                messagebox.showerror("Error!", "Unable to read %s" % os.path.basename(self.docfile))

        if self.savefile_var.get() != self.savefilename :
            self.savefilename = self.prefs.outfile = self.savefile_var.get()
            self.prefs.saveSettings()

    def setTitle(self):
        # check for filenumber in input doc file name
        doc_num_string = Spiderutils.getfilenumber(self.docfile)

        # if input doc has a number
        if doc_num_string != '' :
            title = "Montage from " + os.path.basename(self.docfile)
        else :
            # check directory for number
            doc_dir = os.path.dirname(self.docfile)
            doc_dirnum_string = Spiderutils.getfilenumber(doc_dir)
            doc_base = os.path.basename(self.docfile)

            # if directory has a number
            if doc_dirnum_string != '' :
                title = "Montage from " + os.path.join(doc_dir, doc_base)
            else:
                title = "Montage from " + os.path.basename(self.docfile)  # default

        # set title
        self.top.title(title)

    def increaseFilenum(self, win):
        # set input selection doc name
        docfile = self.doc_var.get()
        (doc_new,doc_num) = renumberFromTemplate(docfile,docfile,1)
        self.doc_var.set(doc_new)

        # set particle template
        serfile = self.sertemplate.get()
        ser_new = renumberFromTemplate(docfile,serfile,1)[0]
        self.sertemplate.set(ser_new)

        # set output doc name
        outfile = self.savefile_var.get()
        out_new = renumberFromTemplate(docfile,outfile,1)[0]
        self.savefile_var.set(out_new)

    def decreaseFilenum(self, win):
        # set input selection doc name
        docfile = self.doc_var.get()
        doc_new = docfile  # default

        # determine if filenumber >= 1
        doc_num = renumberFromTemplate(docfile,docfile)[1]
        if doc_num > 1: doc_new = renumberFromTemplate(docfile,docfile,-1)[0]
        self.doc_var.set(doc_new)

        # set particle template -- depends on whether particles are stacked, etc.
        serfile = self.sertemplate.get()
        ser_new = serfile  # default

        # determine if filenumber >= 1
        ser_num = renumberFromTemplate(serfile,serfile)[1]
        if ser_num > 1 and ser_num == doc_num :
            ser_new = renumberFromTemplate(serfile,serfile,-1)[0]
        self.sertemplate.set(ser_new)

        # set output doc name
        outfile = self.savefile_var.get()
        out_new = outfile  # default

        # determine if filenumber >= 1
        out_num = renumberFromTemplate(outfile,outfile)[1]
        if out_num > 1 and out_num == doc_num :
            out_new = renumberFromTemplate(outfile,outfile,-1)[0]
        self.savefile_var.set(out_new)

    def askSelections(self, parent, which) : 
        filename = filedialog.askopenfilename(parent=parent) # , initialdir=self.docdir)
        if len(filename) < 1:
            return
        if which == 'doc':
            self.doc_var.set(filename)
        if which == 'ser':
            self.sertemplate.set(Spiderutils.name2template(filename))
        if which == 'out':
            self.savefile_var.set(filename)

    def loadImageList(self):
        # Get particle numbers for current pageful of images

        partdoc = self.docfile
        if len(partdoc) < 1:
            return
        if not os.path.exists(partdoc):
            print("Unable to find " + partdoc)
            return
        D = self.docfile_spi  # Spiderutils.readSpiderDocFile(partdoc)
        self.imagelist = []

        spi_col = self.particle_col - 1

        for f in range(self.first_key,self.last_key+1):
            if self.particle_col == 0 : 
                num = f                   # then use key
            else :
                num = int(D[f][spi_col])  # each element is a list (of column data)

            self.imagelist.append(num)

        if len(self.imagelist) < 1:
            print("no images loaded")
            self.error = True
            ###master.destroy()  ### I don't know what this was supposed to do?
            return
        else: 
            self.error = False
            self.last = 0

    def readInputDoc (self) :
        self.docfile_spi = Spiderutils.readSpiderDocFile(self.docfile)
        self.num_keys = len(list(self.docfile_spi.keys()))
        self.first_key = 1
        self.pagenum = 1
        self.page_var.set(self.pagenum)
        self.sel_dictionary = {}

        if self.num_keys > self.montage_size :
            self.last_key = self.montage_size

            # calculate number pages
            self.num_pages = int((self.num_keys-1)/self.montage_size) + 1
        else:
            self.last_key = self.num_keys
            self.num_pages = 1

        print('Page', self.pagenum, 'of', self.num_pages)
        print('Loading particles', self.first_key, 'to', self.last_key, 'of', self.num_keys)

    def readOutputDoc(self, event=None):
        if os.path.exists(self.savefilename):
            # read doc file
            savefile = Spiderutils.readSpiderDocFile(self.savefilename)

            # loop through keys
            for key in list(savefile.keys()):
                imgnum   = int(savefile[key][0])
                classnum = str(int(savefile[key][1]))
                self.sel_dictionary[imgnum] = classnum

            num_keys = len(list(savefile.keys()))
            print("Read", num_keys, "keys from", os.path.basename(self.savefilename))
            self.havereaddoc_boolean = True

            # refresh display
            self.loadImageList()
            self.createMontage()
            self.updateSmooth()
        else:
            messagebox.showerror("Error!", "Unable to read %s" % os.path.basename(self.savefilename))

    def nextPage(self, event=None):
        # check if there are any more images to display
        if self.last_key >= self.num_keys :
            print('Already last page', self.last_key, self.num_keys)
        else :
            self.first_key = self.first_key+self.montage_size
            self.last_key = self.last_key+self.montage_size
            if self.last_key > self.num_keys : self.last_key = self.num_keys

            self.loadImageList()
            self.createMontage()
            self.updateSmooth()
            self.pagenum += 1
            self.page_var.set(self.pagenum)

            print('Page', self.pagenum, 'of', self.num_pages)

    def prevPage(self, event=None):
        # check if there are any more images to display
        if self.first_key == 1 :
            print('Already first page')
        else :
            self.first_key = self.first_key-self.montage_size
            self.last_key = self.first_key+self.montage_size-1

            self.loadImageList()
            self.createMontage()
            self.updateSmooth()
            self.pagenum -= 1
            self.page_var.set(self.pagenum)

            print('Page', self.pagenum, 'of', self.num_pages)

    def updatePage(self, event=None):
        pagenum = int(self.page_var.get())
        if pagenum > self.num_pages : 
            print('Only', self.num_pages, 'pages')
            self.page_var.set(self.pagenum)
            return

        if pagenum < 1 or pagenum == self.pagenum: 
            print('Ignoring')
            self.page_var.set(self.pagenum)
            return

        self.first_key = (pagenum-1)*self.montage_size + 1
        self.last_key = pagenum*self.montage_size
        if self.last_key > self.num_keys : self.last_key = self.num_keys
        self.pagenum = pagenum

        print('Page', self.pagenum, 'of', self.num_pages)
        self.loadImageList()
        self.createMontage()
        self.updateSmooth()

    def makeMenus(self):
        # ------- create the menu bar -------
        self.mBar = tkinter.Frame(self.top, relief='raised', borderwidth=1)
        self.balloon = Pmw.Balloon(self.top)

        self.leftframe = tkinter.Frame(self.mBar) # , relief='raised', borderwidth=1)

        # Make the File menu
        Filebtn = tkinter.Menubutton(self.leftframe, text='File', relief='flat')
        Filebtn.pack(side='left', padx=5, pady=5)
        Filebtn.menu = tkinter.Menu(Filebtn, tearoff=0)

        Filebtn.menu.add_command(label='Set filenames', command=self.openSelections)
        Filebtn.menu.add_command(label='Save selection', underline=0,
                                command=self.saveSelections)
        Filebtn.menu.add_command(label='Read selection', underline=0,
                                command=self.readOutputDoc)
        Filebtn.menu.add_command(label='Close', underline=0,
                                     command=self.top.destroy)

        # Finish
        Filebtn['menu'] = Filebtn.menu


        # Make the Display menu
        Dspbtn = tkinter.Menubutton(self.leftframe, text='Display', relief='flat')
        Dspbtn.pack(side='left', padx=5, pady=5)
        Dspbtn.menu = tkinter.Menu(Dspbtn, tearoff=0)

        Dspbtn.menu.add_command(label='no. columns & rows', underline=0,
                                    command=self.displayParms_colrow)
        Dspbtn.menu.add_command(label='change label', underline=0,
                                    command=self.displayParms_label)
#        Dspbtn.menu.add_command(label='reverse order', command=self.revRedisplay)

        # 'size' has a submenu of checkbuttons
        Dspbtn.menu.sizes = tkinter.Menu(Dspbtn.menu, tearoff=0)
        for size_label, size_value in zip(['1/4','1/2','1x','2x'],[4,0,1,2]):
            Dspbtn.menu.sizes.add_radiobutton(label=size_label, underline=0,
                                              variable=self.sizeVar, value=size_value,
                                              command=self.displayParms_size)
        Dspbtn.menu.add_cascade(label='image size', menu=Dspbtn.menu.sizes)

        # Make the Color submenu
        Dspbtn.menu.colors = tkinter.Menu(Dspbtn.menu, tearoff=0)
        keys = list(self.selectClasses.keys())
        keys.sort()
        Dspbtn.menu.colors.good = tkinter.Menu(Dspbtn.menu.colors, tearoff=0)
        Dspbtn.menu.colors.bad =  tkinter.Menu(Dspbtn.menu.colors, tearoff=0)
        for key in range(1,4):  # selected colors
            sc = self.selectClasses[str(key)]
            Dspbtn.menu.colors.good.add_radiobutton(label = sc.label, underline=0,
                                        value = sc.value,
                                        foreground = 'white',
                                        background = sc.color,
                                        activebackground= sc.active,
                                        activeforeground= 'black',
                                        variable=self.selectedColor)#,
            # selection class : value, key, color, label, active

        Dspbtn.menu.colors.bad.add_radiobutton(label = 'Deselect', underline=0,
            value = self.systembackground, foreground = 'white', background = self.systembackground, 
            activebackground = self.actbgd, activeforeground= 'black', variable=self.deselectedColor)
        Dspbtn.menu.colors.bad.add_radiobutton(label = 'Vermillion', underline=0,
            value = 'Red', foreground = 'white', background = '#d55e00',
            activebackground = '#d6ae90', activeforeground= 'black', variable=self.deselectedColor)
        Dspbtn.menu.colors.add_cascade(label='selected',   menu=Dspbtn.menu.colors.good)
        Dspbtn.menu.colors.add_cascade(label='deselected', menu=Dspbtn.menu.colors.bad)
        Dspbtn.menu.add_cascade(label='colors', menu=Dspbtn.menu.colors)

        # Finish
#        Dspbtn.menu.add_separator()
        Dspbtn['menu'] = Dspbtn.menu

        # Make the Select menu
        Selectbtn = tkinter.Menubutton(self.leftframe, text='Select', relief='flat')
        Selectbtn.pack(side='left', padx=5, pady=5)
        Selectbtn.menu = tkinter.Menu(Selectbtn, tearoff=0)

        Selectbtn.menu.add_command(label='Select all', underline=0,
                                    command=self.selectAll)
        Selectbtn.menu.add_command(label='Clear all', underline=0,
                                    command=self.clearAll)
        Selectbtn.menu.add_command(label='Invert', underline=0,
                                    command=self.invertSelect)

        Selectbtn['menu'] = Selectbtn.menu

        # Make the Invert button
        key = self.selectedColor.get()
        sc = self.selectClasses[key]
        badcolor = self.deselectedColor.get()
        Invbtn = tkinter.Button(self.leftframe, text='Invert', command=self.invertSelect,
            background = sc.color, foreground = badcolor, 
            activeforeground = sc.color, activebackground = badcolor)
        Invbtn.pack(side='left', padx=5, pady=5)

        # Make the Close button
        Clsbtn = tkinter.Button(self.leftframe, text='Close', command=self.top.destroy)
        Clsbtn.pack(side='left', padx=5, pady=5)

        # Make the Save+Close button
        Selbtn = tkinter.Button(self.leftframe, text='Save+Close', command=self.saveClose)
        Selbtn.pack(side='left', padx=5, pady=5)

        # Make help menu
        Helpbtn = tkinter.Menubutton(self.leftframe, text='Help', underline=0, relief='flat')
        Helpbtn.menu = tkinter.Menu(Helpbtn, tearoff=0)
        Helpbtn.menu.add_command(label='Keyboard shortcuts', underline=0, 
                                 command=self.shortcuts)
        Helpbtn['menu'] = Helpbtn.menu
        Helpbtn.pack(side='right', padx=5, pady=5)

        # Pack menu bar
        self.leftframe.pack(side='left') # , padx=5, pady=5)

        # Make the page bar
        self.pagebar = tkinter.Frame(self.mBar) # , relief='sunken', borderwidth=1)
        tkinter.Label(self.pagebar, text='Page').pack(side='left')
        page_entry = tkinter.Entry(self.pagebar, textvariable=self.page_var, width=3)
        page_entry.pack(side='left')
        page_button = tkinter.Button(self.pagebar, text='Update', command=self.updatePage)
        page_button.pack(side='left')
        self.pagebar.pack(side='right', padx=5, pady=5)

        self.mBar.pack(side='top', fill = 'x')

        # Make the contrast slidebars
        f2 = tkinter.Frame(self.top)
        sbri = tkinter.Scale(f2, label='brightness', orient='horizontal',
                     from_=0, to=3, resolution=0.1, # sliderlength=width,
                     variable=self.brightness, command=self.updateBrightness)
        sbri.pack(side='left', padx=5)

#        scon = Scale(f2, label='contrast', orient=HORIZONTAL,
#                     from_=-1, to=3, resolution=0.1, #sliderlength=width,
#                     variable=self.contrast, command=self.updateContrast)
#        scon.pack(side='right', padx=5)

        Smthbtn = tkinter.Button(f2, text='Smooth', command=self.smooth)
        Smthbtn.pack(side='left', padx=5, pady=5)

        origb = tkinter.Button(f2, text='Undo filters', command=self.orig2)
        origb.pack(side='right', padx=5, pady=5)

        f2.pack(side='bottom', fill='x', expand=0)

    def saveClose(self, event=None):
        self.saveSelections()
        self.closeWindow()

    def shortcuts(self):
        sc = tkinter.Toplevel(self.top)
        sc.title("Shortcuts")
        self.sc_rownum = 0
        self.scmain = tkinter.Frame(sc, borderwidth=2, relief='ridge')
        tkinter.Label(self.scmain, text='Main window:').grid(row=self.sc_rownum, sticky='w')

        self.addShortcut('Page down', 'Next page')
        self.addShortcut('Page up', 'Previous page')
        self.addShortcut('Control-o', 'Open selection doc')
        self.addShortcut('Control-w', 'Close window')
        self.addShortcut('Control-s', 'Save selections')
        self.addShortcut('Control-r', 'Read selections')
        self.addShortcut('Control-v', 'Invert selections')
        self.addShortcut('DELETE', 'Clear selections')
        self.addShortcut('Control-a', 'Select all')
        self.addShortcut('Return', 'Update')
        self.addShortcut('Control-p', 'Print settings')
        self.addShortcut('Control-f', 'Show labels')
        self.scmain.pack(padx=5, pady=5, expand=1)

        scopen = tkinter.Frame(sc, borderwidth=2, relief='ridge')
        tkinter.Label(scopen, text='Open Selections:').grid(row=0, sticky='w')

        tkinter.Label(scopen, text='Control-n'          ).grid(row=1, column=0, sticky='w')
        tkinter.Label(scopen, text='Increase filenumber').grid(row=1, column=1, sticky='w')

        tkinter.Label(scopen, text='Control-p'          ).grid(row=2, column=0, sticky='w')
        tkinter.Label(scopen, text='Decrease filenumber').grid(row=2, column=1, sticky='w')
        scopen.pack(padx=5, pady=5)

        okframe = tkinter.Frame(sc)
        tkinter.Button(okframe, text="OK", command=sc.destroy).pack()
        sc.bind('<Return>', lambda p=self.top, w=sc: clickOK(p,w))
        okframe.pack()

    def addShortcut(self, sc_combo, sc_descr):
        # Add single line to shortcut table
        self.sc_rownum+= 1
        tkinter.Label(self.scmain, text=sc_combo).grid(row=self.sc_rownum, column=0, sticky='w')
        tkinter.Label(self.scmain, text=sc_descr).grid(row=self.sc_rownum, column=1, sticky='w')

    def createMontage(self):
        if hasattr(self,'sf'): self.sf.destroy()

        self.sf = Pmw.ScrolledFrame(self.top)
        self.fr = self.sf.interior()
        self.display(self.fr)
        self.sf.pack(fill='both', expand=1)

        ht = self.fr.winfo_reqheight()
        wd = self.fr.winfo_reqwidth()
        if ht == 1 or wd == 1:
            self.fr.after(500, self.frsize)
        else:
            if ht < self.xmax and wd < self.ymax:
                self.sf.component("clipper").configure(height=ht)
                self.sf.component("clipper").configure(width=wd)

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

    def checksize(self):
        size = self.sizeVar.get()
        if size != 1:
            if size == 0:
                xhalf = int(self.xsize/2)
                yhalf = int(self.ysize/2)
                x,y = xhalf, yhalf
            elif size == 2:
                xtwice = 2*self.xsize
                ytwice = 2*self.ysize
                x,y = xtwice,ytwice
            elif size == 4:
                xquarter = int(self.xsize/4)
                yquarter = int(self.ysize/4)
                x,y = xquarter,yquarter
        else:
            x,y = self.xsize, self.ysize

        return x,y

    def display(self, parent):
        useLabels = self.useLabels
        self.particle2label = {}
        self.photolist = []
        i = 0
        j = 0
        order = 0

        D = self.docfile_spi
        spi_col = self.label_col - 1

        if self.isStack: im = Image.open(self.serfile)
        badcolor = self.deselectedColor.get()

        for key in range(self.first_key,self.last_key+1):
            order += 1  # increment counter
            num = self.imagelist[order-1]

            if self.isStack:
                index = num - 1
                im.seek(index)
            else:
                filename = Spiderutils.template2filename(self.serfile, num)
                im = Image.open(filename)

            img = im.convert2byte()
            img.convert("L")

            # check image size for first image of each page
            if order == 1:
                self.xsize,self.ysize = im.size
                x,y = self.checksize()

            # compare current image size to fixed size
            ix,iy = im.size
            if ix != x or iy != y:
                icpy = img.copy()  # o.w. orig is resized
                img = icpy.resize( (x,y) )

            photo = ImageTk.PhotoImage(img, palette=256, master=parent)
            fim = img.copy()
            photo.paste(fim)

            if num in self.sel_dictionary :
                im.selectvalue = self.sel_dictionary[num]
                sc = self.selectClasses[im.selectvalue]
                ib = tkinter.Label(parent, image=photo, bd=self.bd, borderwidth=3,
                    background=sc.color)
            else:
                im.selectvalue = self.selectClasses['0'].key
                if not self.havereaddoc_boolean :
                    ib = tkinter.Label(parent, image=photo, bd=self.bd, borderwidth=3)
                else :
                    ib = tkinter.Label(parent, image=photo, bd=self.bd, borderwidth=3,
                        background=badcolor)

            ib.fim = fim
            ib.bim = img.copy()
            ib.photo = photo

            if self.isStack:
                if self.label_col == 0 :
                    stat = num  # slice#
                else :
                    stat = D[key][spi_col]
                    if stat == int(stat) : stat=int(stat)  # strip ".0"
                    if stat > 100000 : stat = '%E' % stat

                ib.label = self.text_label + str(stat)
            else:  # not a stack
                if self.label_col == 0 :
                    ib.label = filename
                else :
                    stat = D[key][spi_col]
                    if stat == int(stat) : stat=int(stat)  # strip ".0"
                    if stat > 100000 : stat = '%E' % stat
                    ib.label = self.text_label + str(stat)

            ib.grid(row=j, column=i, padx=2, pady=2)
            ib.bind('<Button-1>', lambda event, w=ib, i=im: self.select(w,i))
            ib.bind('<Shift-Button-1>', lambda event, 
                w=ib, i=im: self.shiftSelect(w,i))

            ib.num = num      # particle number
            ib.order = order  # numbered from 1..n

            self.photolist.append(ib)

            # particle-to-label lookup table
            filenumber = int(Spiderutils.getfilenumber(ib.label))
            self.particle2label[filenumber] = ib

            if useLabels:
                lb = tkinter.Label(parent, text=os.path.basename(ib.label))
                lb.grid(row=j+1, column=i)
            i += 1
            if i > self.ncol-1:
                i = 0
                j += 1
                if useLabels: j += 1 # incr j twice for labels

#        self.updateContrast(self.contrast.get())
        self.updateBrightness(self.brightness.get())

    def smooth(self):
        self.num_smooths += 1
        print('smoothing =', self.num_smooths)
        self.updateSmooth()

    def updateSmooth(self):
        x,y = self.checksize()

        for counter in range(len(self.photolist)):
            img = self.photolist[counter].bim

            # check size
            ix,iy = img.size
            if ix != x or iy != y:
                icpy = img.copy()  # o.w. orig is resized
                img = icpy.resize( (x,y) )

            if self.num_smooths:
                for smoothcounter in range(self.num_smooths):
                    img = img.filter(ImageFilter.SMOOTH)

            self.photolist[counter].fim = img
            self.photolist[counter].photo.paste(self.photolist[counter].fim)

    def updateBrightness(self, value):
        x,y = self.checksize()

        for counter in range(len(self.photolist)):
            img = self.photolist[counter].fim

            # check size
            ix,iy = img.size
            if ix != x or iy != y:
                icpy = img.copy()  # o.w. orig is resized
                img = icpy.resize( (x,y) )

            brightness=float(value)
            self.photolist[counter].bim = ImageEnhance.Brightness(img).enhance(brightness)
            self.photolist[counter].photo.paste(self.photolist[counter].bim)

    def orig2(self):
        # reset values

        self.num_smooths = 0
        print('smoothing = 0')
        self.brightness.set(1)
        x,y = self.checksize()

        if self.isStack: im = Image.open(self.serfile)

        for counter in range(len(self.photolist)):
            num = self.imagelist[counter]

            if self.isStack:
                index = num - 1
                im.seek(index)
            else:
                filename = Spiderutils.template2filename(self.serfile, num)
                im = Image.open(filename)

            img = im.convert2byte()
            img.convert("L")

           # check size
            ix,iy = img.size
            if ix != x or iy != y:
                icpy = img.copy()  # o.w. orig is resized
                img = icpy.resize( (x,y) )

            # restore original
            self.photolist[counter].fim = img

        self.updateBrightness(self.brightness.get())

    def displayParms_label(self):
        changed = False  # initialize

        w = tkinter.Toplevel(self.top)
        w.title("Labels")
        self.labelWindow(w)
        w.bind('<Return>', lambda p=self.top, w=w: clickOK(p,w)) 
        self.top.wait_window(w)  # wait for window to be destroyed

        if self.showVar.get() != self.useLabels : changed = True
        if self.column_var.get() != self.label_col : changed = True
        if self.text_var.get() != self.text_label : changed = True
        if self.particle_var.get() != self.particle_col : changed = True

        if changed : 
            self.useLabels = self.prefs.use_labels = self.showVar.get()
            self.label_col = self.prefs.label_col = self.column_var.get()
            self.text_label  = self.prefs.text_label = self.text_var.get()
            self.particle_col = self.prefs.particle_col = self.particle_var.get()

            self.createMontage()
            self.prefs.saveSettings()

    def showLabels(self, event=None):
        q = self.showVar.get()
        self.showVar.set(1-q)
        self.useLabels = self.prefs.use_labels = 1-q

        self.createMontage()
        self.prefs.saveSettings()

    def labelWindow(self,win):
        label_frame = tkinter.Frame(win, relief='groove', borderwidth=2)
        tkinter.Checkbutton(label_frame, text='show labels', state='normal',
            variable=self.showVar).grid(row=0, column=0)

        # doc file column number
        tkinter.Label(label_frame, text="doc file column for label").grid(row=1, column=0)
        tkinter.Entry(label_frame, width=6, textvariable=self.column_var).grid(row=1, column=1)

        # text label
        tkinter.Label(label_frame, text="label text").grid(row=2, column=0, sticky='e')
        tkinter.Entry(label_frame, width=6, textvariable=self.text_var).grid(row=2, column=1)

        # particle column
        tkinter.Label(label_frame, text="doc file column for particle").grid(row=3, column=0, sticky='e')
        tkinter.Entry(label_frame, width=6, textvariable=self.particle_var).grid(row=3, column=1)

        # finish labels frame
        label_frame.pack()

        fbut = tkinter.Frame(win, borderwidth=2) #relief='raised',
        tkinter.Button(fbut, text='Ok', command=win.destroy).pack(padx=2,pady=2)
        fbut.pack(side='bottom', fill='x', expand=1)

    def displayParms_size(self):
        self.createMontage()
        self.prefs.size = self.sizeVar.get()
        self.prefs.saveSettings()

    def displayParms_colrow(self):
        self.ncolVar.set(self.ncol)
        w = tkinter.Toplevel(self.top)
        w.title("Dimensions")
        self.parmWindow(w)
        w.bind('<Return>', lambda p=self.top, w=w: clickOK(p,w)) 
        self.top.wait_window(w) # wait for window to be destroyed

        i = int(self.ncolVar.get())
        j = int(self.maxrowVar.get())
        if i != self.ncol or j != self.maxrow :
            self.ncol = self.prefs.ncol = i
            self.maxrow = self.prefs.maxrow = j

            self.montage_size = self.ncol * self.maxrow
            if self.num_keys > self.montage_size :
                self.last_key = self.montage_size
            else:
                self.last_key = self.num_keys
            self.num_pages = int((self.num_keys-1)/self.montage_size) + 1

            # restart from first page
            self.first_key = 1
            self.pagenum = 1
            self.page_var.set(self.pagenum)
            print('Page', self.pagenum, 'of', self.num_pages)

            self.loadImageList()
            self.createMontage()
            self.updateSmooth()
            self.prefs.saveSettings()

    def parmWindow(self,win):
        fe = tkinter.Frame(win)

        # number of columns
        tkinter.Label(fe,text="no. columns:").grid(row=0, column=0, padx=2, pady=2)
        e = tkinter.Entry(fe, textvariable=self.ncolVar)
        e.grid(row=0, column=1, pady=2, padx=2)

        # maximum number of rows
        tkinter.Label(fe,text="max. rows:").grid(row=1, column=0, padx=2, pady=2)
        m = tkinter.Entry(fe, textvariable=self.maxrowVar)
        m.grid(row=1, column=1, pady=2, padx=2)

        # finish
        fe.pack(side='top',fill='both', expand=1)        
        fbut = tkinter.Frame(win, borderwidth=2) #relief='raised',
        tkinter.Button(fbut, text='Ok', command=win.destroy).pack(padx=2,pady=2)
        fbut.pack(side='bottom', fill='x', expand=1)


# -------------------------------------------------------------------
def initTemplate(parent,which):
    filename = filedialog.askopenfilename(parent=parent)
    if len(filename) < 1:
        return
    if which == 'ser':
        im = Image.open(filename)
        if im.istack:
            sertemplate.set(filename)
        else: 
            sertemplate.set(Spiderutils.name2template(filename))
    if which == 'doc':
        docvar.set(filename)
    # TO DO: use relative path
    if which == 'out':
        outvar.set(filename)

def buttonExit(win):
    win.destroy()
    prefs1.do_continue = False
#    return do_continue
#    sys.exit()

class settings:
    # defaults
    docfile      = "doc0001.dat"
    serfile      = "flt/flt******.dat"
    ncol         = 14
    maxrow       = 6
    size         = 1
    use_labels   = 1
    label_col    = 1
    text_label   = "image "
    particle_col = 1
    outfile      = "out0001.dat"

    def readSettings(self):
        file = '.montagefromdoc'
        map = {}  # initialize dictionary

        if os.path.exists(file) : 
            input = open(file,'r')
            L = input.readlines()  # read line-by-line
            input.close()

            # read contents
            for line in L:
                first  = line.split()[0]
                second = line.split()[1]
                map[first] = second

            if 'doc_file' in map:          self.docfile = map['doc_file']
            if 'particle_template' in map: self.serfile = map['particle_template']
            if 'num_columns' in map:       self.ncol = int(map['num_columns'])
            if 'max_rows' in map:          self.maxrow = int(map['max_rows'])
            if 'image_size' in map:        self.size = int(map['image_size'])
            if 'use_labels' in map:        self.use_labels = int(map['use_labels'])
            if 'label_column' in map:      self.label_col = int(map['label_column'])
            if 'text_label' in map:        self.text_label = map['text_label']
            if 'particle_col' in map:      self.particle_col = map['particle_col']
            if 'output_file' in map:       self.outfile = map['output_file']

    def saveSettings(self):
        list = []
        list.append('doc_file           ' + self.docfile           + '\n')
        list.append('particle_template  ' + self.serfile           + '\n')
        list.append('num_columns        ' + str(self.ncol)         + '\n')
        list.append('max_rows           ' + str(self.maxrow)       + '\n')
        list.append('image_size         ' + str(self.size)         + '\n')
        list.append('use_labels         ' + str(self.use_labels)   + '\n')
        list.append('label_column       ' + str(self.label_col)    + '\n')
        list.append('text_label         ' + self.text_label        + '\n')
        list.append('particle_col       ' + str(self.particle_col) + '\n')
        list.append('output_file        ' + str(self.outfile) + '\n')

        output = open('.montagefromdoc','w')
        output.writelines(list)

    def printSettings(self, event=None):
        print()
        print('doc_file           ' + self.docfile)           
        print('particle_template  ' + self.serfile)           
        print('num_columns        ' + str(self.ncol))         
        print('max_rows           ' + str(self.maxrow))       
        print('image_size         ' + str(self.size))         
        print('use_labels         ' + str(self.use_labels))   
        print('label_column       ' + str(self.label_col))    
        print('text_label         ' + self.text_label)        
        print('particle_col       ' + str(self.particle_col)) 
        print('output_file        ' + str(self.outfile)) 
     

if __name__ == "__main__":
    """
    tmontage montagedoc 'sertemplate'  
    """

    root = tkinter.Tk()
    root.title('montagefromdoc.py')
    root.option_add("*Font", "Helvetica 12 bold")
    root.geometry('+%d+%d' % (1,1))  # window placement

    prefs1=settings()
    prefs1.readSettings()

    # optionally get doc file from command line
    if sys.argv[1:]:
        prefs1.docfile = sys.argv[1]
    docfilenumber = Spiderutils.getfilenumber(prefs1.docfile)
    extension = os.path.splitext(prefs1.docfile)[1]

    # parameter window/frame
    param_win = tkinter.Toplevel(root)
#    param_win.lift(root)  # doesn't do anything?
    param_win.title("parameters")
    param_win.option_add("*Font", "Helvetica 12 bold")
    param_frame = tkinter.Frame(param_win, relief='ridge', borderwidth=2)

    # docfile entry
    tkinter.Button(param_frame, text='Doc file', command = lambda
        w=param_win, d='doc': initTemplate(w,d)).grid(row=0, column=0, sticky='ew')
    docvar = tkinter.StringVar()
    docvar.set(os.path.splitext(prefs1.docfile)[0] + extension)
    doc_entry = tkinter.Entry(param_frame, textvariable=docvar, width=20)
    doc_entry.grid(row=0, column=1)

    # particle entry
    tkinter.Button(param_frame, text='Particle template',
        command = lambda w=param_win, d='ser': initTemplate(w,d)).grid(row=1, column=0)

    if sys.argv[2:]: 
        prefs1.serfile = sys.argv[2]
    else :
        prefs1.serfile = renumberFromTemplate(prefs1.docfile,prefs1.serfile)[0]

    sertemplate = tkinter.StringVar()
    sertemplate.set(os.path.splitext(prefs1.serfile)[0] + extension)
    ser_entry = tkinter.Entry(param_frame, textvariable=sertemplate, width=20)
    ser_entry.grid(row=1, column=1)

    # outfile entry
    tkinter.Button(param_frame, text='Output doc file', command = lambda
        w=param_win, d='out': initTemplate(w,d)).grid(row=2, column=0, sticky='ew')

    prefs1.outfile = renumberFromTemplate(prefs1.docfile,prefs1.outfile)[0]

    outvar = tkinter.StringVar()
    outvar.set(os.path.splitext(prefs1.outfile)[0] + extension)
    out_entry = tkinter.Entry(param_frame, textvariable=outvar, width=20)
    out_entry.grid(row=2, column=1)

    # column-number entry
    ncol_frame = tkinter.Frame(param_frame)
    ncol_var = tkinter.IntVar()
    ncol_var.set(prefs1.ncol)
    tkinter.Label(ncol_frame, text="no. columns:").pack(side='left')
    ncol_entry = tkinter.Entry(ncol_frame, width=4, textvariable=ncol_var)
    ncol_entry.pack(side='left')
    ncol_frame.grid(row=3, column=0, pady=2)  # in param_frame

    # maxrow frame/entry
    maxrow_frame = tkinter.Frame(param_frame)
    maxrow_var = tkinter.IntVar()
    maxrow_var.set(prefs1.maxrow)
    tkinter.Label(maxrow_frame, text="max. rows:").pack(side='left')
    maxrow_entry = tkinter.Entry(maxrow_frame, width=4, textvariable=maxrow_var)
    maxrow_entry.pack(side='left')
    maxrow_frame.grid(row=3, column=1, pady=2)  # in param_frame

    # display-size radiobutton
    size_frame = tkinter.Frame(param_frame, relief='groove', borderwidth=2)
    tkinter.Label(size_frame, text='image size').pack(side='left')
    size_var = tkinter.IntVar()
    size_var.set(prefs1.size)
    for text, value in [('1/4',4), ('1/2',0), ('1x',1), ('2x',2)] :
        tkinter.Radiobutton(size_frame, text=text, value=value, variable=size_var).pack(side='top')
    size_frame.grid(row=4, column=0, padx=2, pady=2)

    # labels frame
    label_frame = tkinter.Frame(param_frame, relief='groove', borderwidth=2)
    show_var = tkinter.IntVar()
    show_var.set(prefs1.use_labels)
    tkinter.Checkbutton(label_frame, text='show labels', state='normal',
        variable=show_var).grid(row=0, column=0, sticky='e')

    # doc file column number
    tkinter.Label(label_frame, text="doc file column for label").grid(row=1, column=0, sticky='e')
    column_var = tkinter.IntVar()
    column_var.set(prefs1.label_col)
    tkinter.Entry(label_frame, width=6, textvariable=column_var).grid(row=1, column=1)

    # text label
    tkinter.Label(label_frame, text="label text").grid(row=2, column=0, sticky='e')
    text_var = tkinter.StringVar()
    text_var.set(prefs1.text_label)
    tkinter.Entry(label_frame, width=6, textvariable=text_var).grid(row=2, column=1)

    # particle column
    tkinter.Label(label_frame, text="column for particle number").grid(row=3, column=0)
    particle_var = tkinter.IntVar()
    particle_var.set(prefs1.particle_col)
    tkinter.Entry(label_frame, width=6, textvariable=particle_var).grid(row=3, column=1)

    # finish labels frame
    label_frame.grid(row=4, column=1)

    # finish parameter window/frame
    param_frame.pack(padx=5, pady=5, ipadx=2, ipady=2)
    quit_frame  = tkinter.Frame(param_win, padx=40)
    done_button = tkinter.Button(quit_frame, text="Continue", command=param_win.destroy)
    done_button.pack(side='left')
    prefs1.do_continue = True
    exit_button = tkinter.Button(quit_frame, text="Exit", command=lambda w=param_win: buttonExit(w))
    exit_button.pack(side='right')
    quit_frame.pack(fill='x')
    param_win.bind('<Return>', lambda p=root, w=param_win: clickOK(p,w))

    # Wait for initial window
    root.withdraw()
    root.wait_window(param_win)
    root.deiconify()
    if not prefs1.do_continue : sys.exit()

    # set variables
    prefs1.docfile      = docvar.get()
    prefs1.serfile      = sertemplate.get()
    prefs1.ncol         = ncol_var.get()
    prefs1.maxrow       = maxrow_var.get()
    prefs1.size         = size_var.get()
    prefs1.use_labels   = show_var.get()
    prefs1.label_col    = column_var.get()
    prefs1.text_label   = text_var.get()
    prefs1.particle_col = particle_var.get()
    prefs1.outfile      = outvar.get()

#   prefs1.printSettings()
    prefs1.saveSettings()

    mn = tmontage(root, prefs1)
    mn.makeMenus()
    mn.createMontage()

    root.mainloop()
