#!/usr/bin/env python
#
# SOURCE:  spider/spire/bin/ctfcircle.py
#
# PURPOSE: Uses a 1-bit BitmapImage as a dynamically updated overlay
#
# Spider Python Library
# Copyright (C) 2006-2018  Health Research Inc., Menands, NY
# Email:  spider@health.ny.gov

import sys
import tkinter  #### from   tkinter       import *
from   PIL           import Image, ImageTk, ImageDraw
###from   Spider        import SpiderImagePlugin  # 2018 al

class UI(tkinter.Frame):
    def __init__(self, master, im, value = 128):
        tkinter.Frame.__init__(self, master)

        self.image = im
        self.value = value
        self.size  = im.size
        self.cx    = im.size[0] / 2
        self.cy    = im.size[1] / 2
        width      = im.size[0]

        self.canvas   = tkinter.Canvas(self, width=im.size[0], height=im.size[1])
        self.backdrop = ImageTk.PhotoImage(im, palette=256)
        self.canvas.create_image(0, 0, image=self.backdrop, anchor='nw')
        self.canvas.pack()

        scale = tkinter.Scale(self, orient='horizontal', from_=0, to=width,
                      resolution=1, command=self.update, length=width+1)
        scale.set(value)
        scale.bind("<ButtonRelease-1>", self.redraw)
        scale.pack()

    def update(self, value):
        self.value = eval(value)
        self.redraw()

    def redraw(self, event = None):

        rad  = self.value/2
        ulx  = self.cx - rad
        uly  = self.cy - rad
        lrx  = self.cx + rad
        lry  = self.cx + rad
        im   = Image.new(mode="1", size=self.size)
        draw = ImageDraw.Draw(im)
        draw.ellipse((ulx,uly,lrx,lry), outline=1)
        draw.ellipse((ulx+1,uly+1,lrx-1,lry-1), outline=1)  # thicker line
        del draw
                     
        self.overlay = ImageTk.BitmapImage(im, foreground="green")

        # update canvas
        self.canvas.delete("overlay")
        self.canvas.create_image(0, 0, image=self.overlay, anchor='nw',
                tags="overlay")

# --------------------------------------------------------------------
# main
# 2018 al FAILED Image.register_open("SPIDER", SpiderImageFile)
root = tkinter.Tk()

im   = Image.open(sys.argv[1])

if im.mode != "L":
    im = im.convert2byte()

# im.thumbnail((320,200))

UI(root, im).pack()

root.mainloop()
