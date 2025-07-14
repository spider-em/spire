#!/usr/bin/env python

import tkinter  #### from tkinter import *
from PIL import Image, ImageTk, ImageDraw
import os, sys

class Viewer:
    def __init__(self, master, filename, index=0):
        self.top = master
        self.top.title( os.path.basename(__file__) )
        self.filename = filename
        self.index = index  # NOT USED

        if not os.path.exists(filename):
            print("Unable to find %s" % filename)
            self.top.quit()

        labeltext = os.path.basename(filename)

        im = Image.open(filename)
        self.im = im
        if im.format == "SPIDER":
            if im.istack != 0:
                ###self.nimages = im.nimages
                # PIL changed the structure of SpiderImageFile
                if hasattr(im, 'nimages'):
                    self.nimages = im.nimages
                elif hasattr(im, '_nimages'):
                    self.nimages = im._nimages
                else:
                    print(f"ERROR!! {type(im)} has neither type 'nimages' nor '_nimages'!")
                    print()
                    print(vars(im))
                    print()
                    print("  Exiting...\n")
                    exit()
                labeltext += " : stack file with %d images" % self.nimages
                im.seek(index)
            bim = im.convert2byte()
        self.size = im.size
        self.cx = im.size[0] // 2
        self.cy = im.size[1] // 2
        self.value = min(self.size) // 4

        self.title = tkinter.Label( text=labeltext, font=("mincho 12") )
        self.title.pack()
                
        im_width= im.size[0]
        self.canvas = tkinter.Canvas(master, width=im_width, height=im.size[1])
        self.tkimage = ImageTk.PhotoImage(bim, palette=256)
        self.canvas.create_image(0, 0, image=self.tkimage, anchor=tkinter.NW)
        self.canvas.pack(side='top')

        scale = tkinter.Scale( master, orient=tkinter.HORIZONTAL, from_=0, to=im_width//2,
                      resolution=1, command=self.update, length=im_width+1, font=("mincho 12") )
        scale.set(self.value)
        scale.bind("<ButtonRelease-1>", self.redraw)
        scale.pack()

        # the button frame
        fr = tkinter.Frame(master)
        fr.pack(side='top', expand=1, fill='x')
        back = tkinter.Button( fr, text="back", command=self.backframe, font=("mincho 12") )
        back.grid(row=0, column=0, sticky="w", padx=4, pady=4)

        ilabel = tkinter.Label( fr, text="image number:", font=("mincho 12") )
        ilabel.grid(row=0, column=1, sticky="e", pady=4)

        self.evar = tkinter.IntVar()
        self.evar.set(index + 1)
        entry = tkinter.Entry(fr, textvariable=self.evar, width=6)
        entry.grid(row=0, column=2, sticky="w", pady=4)
        entry.bind('<Return>', self.getimgnum)
        
        next = tkinter.Button( fr, text="next", command=self.nextframe, font=("mincho 12") )
        next.grid(row=0, column=3, sticky="e", padx=4, pady=4)

        self.top.bind_all('<Up>', self.nextframe)
        self.top.bind_all('<Down>', self.backframe)

    def backframe(self, event=None):
        index = self.im.tell()
        index = index - 1  # back up one frame
        if index < 0:
            index = self.nimages-1
        self.im.seek(index)
        self.evar.set(index+1)
        self.toframe()

    def nextframe(self, event=None):
        index = self.im.tell()
        index = index + 1  # forward one frame
        if index >= self.nimages:
            index = 0
        self.im.seek(index)
        self.evar.set(index+1)
        self.toframe()

    def toframe(self):
        # this line needs to be in a separate function (?)
        self.tkimage.paste(self.im.convert2byte())

    def getimgnum(self, event=None):
        index = self.evar.get() - 1
        if index < 0 or index >= self.nimages:
            index = self.im.tell()
            self.evar.set(index+1)
        self.im.seek(index)
        self.toframe()
    def update(self, value):
        self.value = eval(value)
        self.redraw()

    def redraw(self, event = None):
        pass

        rad = self.value
        ulx = self.cx - rad
        uly = self.cy - rad
        lrx = self.cx + rad
        lry = self.cx + rad
        im = Image.new(mode="1", size=self.size)
        draw = ImageDraw.Draw(im)
        draw.ellipse((ulx,uly,lrx,lry), outline=1)
        #draw.ellipse((ulx+1,uly+1,lrx-1,lry-1), outline=1)  # thicker line
        del draw

        self.overlay = ImageTk.BitmapImage(im, foreground="green")

        # update canvas
        self.canvas.delete("overlay")
        self.canvas.create_image(0, 0, image=self.overlay, anchor=tkinter.NW,
                tags="overlay")


# --------------------------------------------------------------------
if __name__ == "__main__":

    ##print(sys.argv, len(sys.argv))
    ##exit()

    if not sys.argv[1:]:
        print("Usage: viewstack.py stackfile")
        sys.exit()
    filename = sys.argv[1]

    if len(sys.argv) >= 3:
        index= int(sys.argv[2]) - 1
    else:
        index= 0

    root = tkinter.Tk()
    app = Viewer(root, filename, index)
    root.mainloop()
