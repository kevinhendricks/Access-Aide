#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Copyright 2018-2023 Kevin B. Hendricks, Stratford Ontario

# This plugin's source code is available under the GNU LGPL Version 2.1 or GNU LGPL Version 3 License.
# See https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html or
# https://www.gnu.org/licenses/lgpl.html for the complete text of the license.

import sys
import os
import inspect

from plugin_utils import QtCore, QtGui, QtWidgets, QtSvg

from quickparser import QuickXHTMLParser

_THUMBNAIL_SIZE_INCREMENT = 50
_COL_ALTTEXT = 2

# strip out non displayed tags: desc, title and flowRoot as they interfere with QtSvg text tags
def FixupSvgForRendering(data):
    svgdata = []
    qp = QuickXHTMLParser()
    qp.setContent(data)
    skip = False
    for (text, tpath, tname, ttype, tattr) in qp.parse_iter():
        if tname and tname in ['desc', 'title', 'flowRoot', 'flowroot']:
            if ttype == 'single':
                continue
            elif ttype == 'begin':
                skip = True
                continue
            elif ttype == 'end':
                skip = False
                continue
        if not skip:
            if text:
                svgdata.append(text)
            else:
                svgdata.append(qp.tag_info_to_xml(tname, ttype, tattr))
    newdata = "".join(svgdata)
    return newdata


def RenderSvgToImage(fpath):
    svgdat = ""
    with open(fpath, 'rb') as f:
       bytedata = f.read()
       svgdat = bytedata.decode('utf-8', errors='replace')
    svgdata = FixupSvgForRendering(svgdat)
    renderer = QtSvg.QSvgRenderer()
    renderer.load(svgdata.encode('utf-8'))
    sz = renderer.defaultSize()
    svgimage = QtGui.QImage(sz, QtGui.QImage.Format_ARGB32)
    svgimage.fill(QtGui.QColor("white"))
    # svgimage.fill(QtGui.QColor("transparent")) # qRgba(0,0,0,0)
    painter = QtGui.QPainter(svgimage)
    renderer.render(painter)
    return svgimage


class AltTextDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent):
        super().__init__(parent)
        
    def createEditor(self, parent, options, index):
        if index.column() == _COL_ALTTEXT:
            return QtWidgets.QTextEdit(parent)
        return QtWidgets.QStylesItemDelegate.createEditor(option, index)

    def updateEditorGeometry(self, editor, option, index):
        if index.column() == _COL_ALTTEXT:
            editor.setGeometry(option.rect)
        else:
            QtWidgets.QStyledItemDelegate.updateEditorGeometry(editor, option, index)
            
    def sizeHint(self, option, index):
        if index.column() == _COL_ALTTEXT:
            return QtCore.QSize(200, 50)
        return QtWidgets.QStyledItemDelegate.sizeHint(option, index)
    
    def setEditorData(self, editor, index):
        if index.column() == _COL_ALTTEXT:
            editor.insertPlainText(str(index.data(QtCore.Qt.EditRole)))
        else:
            QtWidgets.QStyledItemDelegate.setEditorData(editor, index)
            
    def setModelData(self, editor, model, index):
        if index.column() == _COL_ALTTEXT:
            model.setData(index, editor.toPlainText(), QtCore.Qt.EditRole)
        else:
            QtWidgets.QStyledItemDelegate.setModelData(editor, model, index)    


class AltTextEditor(QtWidgets.QDialog):
    def __init__(self, resources, thumbnail_size):
        super().__init__()
        self.resources = resources
        self.ThumbnailSize = thumbnail_size
        self.altdata = {}
        self.setWindowTitle("Update Alt for Each Image")
        self.said_ok = False
        self.editModel = QtGui.QStandardItemModel(self)
        self.editModel.itemChanged.connect(self.UpdateAltTextForItem)
        self.altDelegate = AltTextDelegate(self)
        
        self.imageTree = QtWidgets.QTreeView(self)
        self.imageTree.setItemDelegateForColumn(_COL_ALTTEXT, self.altDelegate)
        self.imageTree.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        self.imageTree.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.imageTree.setSortingEnabled(False)
        self.imageTree.setWordWrap(True)
        self.imageTree.setTextElideMode(QtCore.Qt.ElideNone)
        self.imageTree.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        self.imageTree.setUniformRowHeights(False)
        self.imageTree.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.imageTree.setDropIndicatorShown(False)
        self.imageTree.setAlternatingRowColors(True)
        self.imageTree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.imageTree.setModel(self.editModel)

        self.ThumbnailDecrease = QtWidgets.QToolButton(self)
        self.ThumbnailDecrease.setText('-')
        self.ThumbnailDecrease.clicked.connect(self.DecreaseThumbnailSize)
        self.ThumbnailIncrease = QtWidgets.QToolButton(self)
        self.ThumbnailIncrease.setText('+')
        self.ThumbnailIncrease.clicked.connect(self.IncreaseThumbnailSize)

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok, self)
        self.buttonBox.accepted.connect(self.AcceptChanges)
        self.buttonBox.rejected.connect(self.reject)

        lbl = QtWidgets.QLabel("Thumbnail Size")
        vlay = QtWidgets.QVBoxLayout()
        vlay.addWidget(self.imageTree)
        hlay = QtWidgets.QHBoxLayout()
        hlay.addWidget(lbl)
        hlay.addWidget(self.ThumbnailDecrease)
        hlay.addWidget(self.ThumbnailIncrease)
        hlay.addStretch()
        vlay.addLayout(hlay)
        vlay.addWidget(self.buttonBox)
        self.setLayout(vlay)
        self.SetImages()

    def sizeHint(self):
        return QtCore.QSize(1000,800)
    
    def SetImages(self):
        self.editModel.clear();
        header = []
        header.append("Images In the Book")
        header.append("Thumbnails")
        header.append("Alt Text")
        self.editModel.setHorizontalHeaderLabels(header)
        for (apath, bkpath, mime, key, atext) in self.resources:
            rowItems = []
            self.altdata[key] = atext
            
            # image name item
            filepath = apath
            name_item = QtGui.QStandardItem()
            name_item.setText(bkpath)
            name_item.setData(filepath, QtCore.Qt.UserRole + 1)
            name_item.setData(mime, QtCore.Qt.UserRole + 2)
            name_item.setData(key, QtCore.Qt.UserRole + 3)
            name_item.setEditable(False)
            rowItems.append(name_item)
            
            # thumbnail item
            image = QtGui.QImage()
            if mime == "image/svg+xml":
                image = RenderSvgToImage(filepath)
            else:
                image = QtGui.QImage(filepath)
            pixmap = QtGui.QPixmap.fromImage(image)
            if pixmap.height() > self.ThumbnailSize or pixmap.width() > self.ThumbnailSize:
                pixmap = pixmap.scaled(QtCore.QSize(self.ThumbnailSize, self.ThumbnailSize), QtCore.Qt.KeepAspectRatio)
            icon_item = QtGui.QStandardItem()
            icon_item.setData(pixmap, QtCore.Qt.DecorationRole)
            icon_item.setEditable(False)
            rowItems.append(icon_item)

            # alt text item
            alt_item = QtGui.QStandardItem()
            alt_item.setText(atext)
            alt_item.setEditable(True)
            rowItems.append(alt_item)
            
            self.editModel.appendRow(rowItems)
    
        self.imageTree.header().setStretchLastSection(True)
        for i in range(0, self.imageTree.header().count()):
            self.imageTree.resizeColumnToContents(i)

    def DecreaseThumbnailSize(self):
        self.ThumbnailSize -= _THUMBNAIL_SIZE_INCREMENT;
        if self.ThumbnailSize <= 0:
            self.ThumbnailSize = 0
            self.ThumbnailDecrease.setEnabled(False)
        self.UpdateThumbnails();

    def IncreaseThumbnailSize(self):
        self.ThumbnailSize += _THUMBNAIL_SIZE_INCREMENT
        self.ThumbnailDecrease.setEnabled(True)
        self.UpdateThumbnails()

    def AcceptChanges(self):
        self.said_ok = True
        self.accept()

    def GetResults(self):
        if self.said_ok:
            return self.altdata
        return None
        
    def UpdateAltTextForItem(self, item):
        index = self.editModel.indexFromItem(item)
        if index.column() == _COL_ALTTEXT:
            path_index = index.siblingAtColumn(0)
            key = str(path_index.data(QtCore.Qt.UserRole+3))
            self.altdata[key] = str(index.data(QtCore.Qt.EditRole))

    def UpdateThumbnails(self):
        for r in range(0,self.editModel.rowCount()):
            name_item = self.editModel.item(r,0)
            filepath = str(name_item.data(QtCore.Qt.UserRole + 1))
            mime = str(name_item.data(QtCore.Qt.UserRole + 2))
            icon_item = self.editModel.item(r,1)
            image = QtGui.QImage()
            if mime == "image/svg+xml":
                image = RenderSvgToImage(filepath)
            else:
                image = QtGui.QImage(filepath)
            pixmap = QtGui.QPixmap.fromImage(image)
            if pixmap.height() > self.ThumbnailSize or pixmap.width() > self.ThumbnailSize:
                pixmap = pixmap.scaled(QtCore.QSize(self.ThumbnailSize, self.ThumbnailSize), QtCore.Qt.KeepAspectRatio)
            icon_item.setData(pixmap, QtCore.Qt.DecorationRole)
            icon_item.setEditable(False)

            
class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, resources, winflags):
        super().__init__(None,  winflags)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.resources = resources
        self.ateditor = AltTextEditor(self.resources, 300)

    def get_updated_alt_values(self):
        self.ateditor.show()
        self.ateditor.exec()
        return self.ateditor.GetResults()


def GUIUpdateFromList(resources, basewidth):
    app = QtWidgets.QApplication(sys.argv)
    mw = MainWindow(resources, QtCore.Qt.Widget | QtCore.Qt.FramelessWindowHint)
    mw.show()
    res = mw.get_updated_alt_values()
    mw.close()
    # app.exec() not needed since QDialog has its own event loop
    return res
