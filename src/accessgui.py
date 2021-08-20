#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Copyright 2018 Kevin B. Hendricks, Stratford Ontario

# This plugin's source code is available under the GNU LGPL Version 2.1 or GNU LGPL Version 3 License.
# See https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html or
# https://www.gnu.org/licenses/lgpl.html for the complete text of the license.

from __future__ import unicode_literals, division, absolute_import, print_function

import sys
import os

from PIL import Image, ImageTk
import tkinter
import tkinter.ttk as tkinter_ttk
import tkinter.constants as tkinter_constants
from tkinter import PhotoImage

def resize_image_copy(basewidth, image):
    imgwidth, imgheight = image.size
    if imgwidth < basewidth:
        # no scaling needed, instead create a blank transparent image
        # with basewidth and image height and paste image centered on it
        size = (basewidth, imgheight)
        bg = Image.new('RGBA', size, (255, 255, 255, 0))
        bg.paste(image, (int((size[0] - image.size[0]) / 2), int((size[1] - image.size[1]) / 2)))
        return ImageTk.PhotoImage(bg) 
    scalefactor = basewidth/float(imgwidth)
    newheight = max(int((float(imgheight)*float(scalefactor))),1)
    return ImageTk.PhotoImage(image.resize((basewidth, newheight), Image.ANTIALIAS))


def GUIUpdateFromList(title, list, basewidth):
    localRoot = tkinter.Tk()
    ls = updateList(localRoot, title, list, basewidth)
    ls.pack(side="top", fill="both", expand=True)
    localRoot.withdraw()
    localRoot.update_idletasks()
    w = localRoot.winfo_screenwidth()
    h = localRoot.winfo_screenheight()
    # make sure our frame actually fits on the users screen
    framewidth = basewidth*2
    frameheight = basewidth*2
    if framewidth > w:
        framewidth = w
    if frameheight > h:
        frameheight = h
    framesize = (framewidth, frameheight)
    x = w//2 - framesize[0]//2
    y = h//2 - framesize[1]//2
    localRoot.geometry("%dx%d+%d+%d" % (framesize + (x,y)))
    localRoot.deiconify()
    localRoot.mainloop()
    # exits with quit but don't destroy until after read out results
    # and cleaned up
    results = []
    for (alabel, afield) in ls.cblist:
        imgpath = alabel.imgpath
        # attempt to prevent issues on Windows by explicitly closing
        # all original image files
        # alabel.origimg.close()
        altnew = afield.get(1.0,"end")
        altnew = altnew.strip()
        if not ls.cancelled:
            results.append([imgpath, altnew])
    localRoot.destroy()
    return results


class updateList(tkinter.Frame):
    def __init__(self, root, title, list, basewidth):
        tkinter.Frame.__init__(self, root)
        self.root = root
        self.list = list
        self.title = title
        self.listsize = len(list)
        self.basewidth = basewidth
        self.cancelled = False
        sticky = tkinter_constants.E + tkinter_constants.W
        ALL = tkinter_constants.E+tkinter_constants.W+tkinter_constants.N+tkinter_constants.S
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(self.listsize+4, weight=1)
        tkinter.Label(self, text=title).grid(row=0, columnspan=3, sticky=tkinter_constants.W)
        donbutton = tkinter.Button(self, text="Okay", command=self.quit)
        donbutton.grid(row=1, column=0, sticky=sticky)
        canbutton = tkinter.Button(self, text="Cancel", command=self.cancelout)
        canbutton.grid(row=1, column=1, sticky=sticky)
        lcb = tkinter.Frame(self)
        lcb.vsb = tkinter.Scrollbar(lcb, orient="vertical")
        lcb.text = tkinter.Text(lcb, width=800, height=600, yscrollcommand=lcb.vsb.set)
        lcb.vsb.config(command=lcb.text.yview)
        lcb.vsb.pack(side="right", fill="y")
        lcb.text.pack(side="left", fill="both", expand=True)
        self.cblist = []
        for aline in list:
            imagepath, alttext = aline
            with open(imagepath, "rb") as fp:
                img = Image.open(fp)
                aimg = resize_image_copy(self.basewidth, img)
                alabel = tkinter.Label(lcb, image=aimg)
                # to prevent segfaults due to garbage collection you need to keep
                # pointers to the original image and the resized image as some
                # internal dependency seems to exist
                alabel.image = aimg
                alabel.origimg = img
                alabel.imgpath = imagepath
                afield = tkinter.Text(lcb, width=50, height=5, borderwidth=2, relief="raised")
                afield.insert("end", alttext)
                self.cblist.append([alabel, afield])
                lcb.text.window_create("end", window=alabel)
                lcb.text.window_create("end", window=afield)
                lcb.text.insert("end", "\n") # to force one pair per line
        lcb.grid(row=3, rowspan=self.listsize+4, columnspan=3, sticky=sticky)

    def cancelout(self):
        self.cancelled = True
        self.quit()

