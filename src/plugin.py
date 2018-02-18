#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Copyright 2015-2017 Kevin B. Hendricks, Stratford Ontario

# This plugin's source code is available under the GNU LGPL Version 2.1 or GNU LGPL Version 3 License.
# See https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html or
# https://www.gnu.org/licenses/lgpl.html for the complete text of the license.

from __future__ import unicode_literals, division, absolute_import, print_function

import sys
import os
import tempfile, shutil
import inspect
import subprocess
from subprocess import Popen, PIPE

# Conditionalize imports to revent failure without feedback on python 2.7
PY3 = sys.version_info[0] == 3
if PY3:
    from accessgui import GUIUpdateFromList
    from urllib.parse import unquote
    from urllib.parse import urlparse


# use subprocess to run a commandline utility
# that converts svg to png if needed. 
# also ensures you have execute rights for unix based platforms
SCRIPT_DIR = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
target = None
xname = None
is_64bit = sys.maxsize > 2**32
if sys.platform.startswith('win'):
    target = "win32"
    xname = 'nsvg2png32.exe'
    if is_64bit:
        target = 'win64'
        xname = 'nsvg2png64.exe'
elif sys.platform.startswith('darwin'):
    target = 'osx'
    xname = 'nsvg2png'
else:
    target = 'unx32'
    if is_64bit:
        target = 'unx64'
    xname = 'nsvg2png'

exe_path = os.path.join(SCRIPT_DIR, target, xname)

if target == 'osx' or target.startswith('unx'):
    os.chmod(exe_path,0o744)


_epubtype_aria_map = {
    "abstract"        : "doc-abstract",
    "acknowledgments" : "doc-acknowledgments",
    "afterword"       : "doc-afterword",
    "appendix"        : "doc-appendix",
    "biblioentry"     : "doc-biblioentry",
    "bibliography"    : "doc-bibliography",
    "biblioref"       : "doc-biblioref",
    "chapter"         : "doc-chapter",
    "colophon"        : "doc-colophon",
    "conclusion"      : "doc-conclusion",
    "cover"           : "doc-cover",
    "credit"          : "doc-credit",
    "credits"         : "doc-credits",
    "dedication"      : "doc-dedication",
    "endnote"         : "doc-endnote",
    "endnotes"        : "doc-endnotes",
    "epigraph"        : "doc-epigraph",
    "epilogue"        : "doc-epilogue",
    "errata"          : "doc-errata",
    "figure"          : "figure",
    "footnote"        : "doc-footnote",
    "foreword"        : "doc-foreword",
    "glossary"        : "doc-glossary",
    "glossterm"       : "term",
    "glossdef"        : "definition",
    "glossref"        : "doc-glossref",
    "introduction"    : "doc-introduction",
    "landmarks"       : "directory",
    "list"            : "list",
    "list-item"       : "listitem",
    "noteref"         : "doc-noteref",
    "notice"          : "doc-notice",
    "pagebreak"       : "doc-pagebreak",
    "page-list"       : "doc-pagelist",
    "part"            : "doc-part",
    "preface"         : "doc-preface",
    "prologue"        : "doc-prologue",
    "pullquote"       : "doc-pullquote",
    "qna"             : "doc-qna",
    "referrer"        : "doc-backlink",
    "subtitle"        : "doc-subtitle",
    "table"           : "table",
    "table-row"       : "row",
    "table-cell"      : "cell",
    "tip"             : "doc-tip",
    "toc"             : "doc-toc",
}

_USER_HOME = os.path.expanduser("~")

# default

# encode strings for xml
def xmlencode(data):
    if data is None:
        return ''
    newdata = data
    newdata = newdata.replace('&', '&amp;')
    newdata = newdata.replace('<', '&lt;')
    newdata = newdata.replace('>', '&gt;')
    newdata = newdata.replace('"', '&quot;')
    return newdata

# decode xml encoded strings
def xmldecode(data):
    if data is None:
        return ''
    newdata = data
    newdata = newdata.replace('&quot;', '"')
    newdata = newdata.replace('&gt;', '>')
    newdata = newdata.replace('&lt;', '<')
    newdata = newdata.replace('&amp;', '&')
    return newdata


# the plugin entry point
def run(bk):

    # epub2 epubs support only a subset of aria
    epubversion = "2.0"
    if bk.launcher_version() >= 20160102:
        epubversion = bk.epub_version()
    E3 = epubversion.startswith("3")
    print("Processing an epub with version: ", epubversion)

    # get users preferences and set defaults for width of images in gui (in pixels)
    prefs = bk.getPrefs()
    prefs.defaults['basewidth'] = 500

    # before anything check for video and audio files and abort if they exist
    has_audio_video = False
    for mid, href, mime in bk.media_iter():
        if mime.startswith('audio') or mime.startswith('video'):
            has_audio_video = True
    if has_audio_video:
        print("Error: Access-Aide can not handle epubs with audio and video resources")
        return -1


    # find the primary language (first dc:language metadata value)
    # and update it to include the accessibility metadata
    print("\nUpdating the content.opf with accessibility schema")
    plang = None
    res = []
    has_access_meta = False
    qp = bk.qp
    metaxml = bk.getmetadataxml()
    qp.setContent(metaxml)
    for text, tagprefix, tagname, tagtype, tagattr in qp.parse_iter():
        if text is not None:
            res.append(text)
            if tagprefix.endswith("dc:language"):
                if plang is None:
                    plang = text
                    if "-" in text:
                        plang, region = text.split("-")
        else:
            if tagname == "meta" and tagtype == "begin":
                if "property" in tagattr:
                    prop = tagattr["property"]
                    if prop.startswith("schema:access"):
                        has_access_meta = True
                if "name" in tagattr:
                    name = tagattr["name"]
                    if name.startswith("schema:access"):
                        has_access_meta = True
            if tagname == "metadata" and tagtype == "end":
                # insert accessibility metadata if needed (assumes schema:accessModeSufficient="textual")
                # which is why we abort if audio or video used, javascript, etc
                if E3 and not has_access_meta:
                    res.append('<meta property="schema:accessibilitySummary">This publication conforms to WCAG 2.0 AA.</meta>\n')
                    res.append('<meta property="schema:accessMode">textual</meta>\n')
                    res.append('<meta property="schema:accessMode">visual</meta>\n')
                    res.append('<meta property="schema:accessModeSufficient">textual</meta>\n')
                    res.append('<meta property="schema:accessibilityFeature">structuralNavigation</meta>\n')
                if not E3 and not has_access_meta:
                    res.append('<meta name="schema:accessibilitySummary" content="This publication conforms to WCAG 2.0 AA."/>\n')
                    res.append('<meta name="schema:accessMode" content="textual"/>\n')
                    res.append('<meta name="schema:accessModeSufficient" content="textual"/>\n')
                    res.append('<meta name="schema:accessibilityFeature" content="structuralNavigation"/>\n')
            res.append(qp.tag_info_to_xml(tagname, tagtype, tagattr))
    metaxml = "".join(res)
    bk.setmetadataxml(metaxml)

    if plang is None:
        print("Error: at least one dc:language must be specified in the opf")
        return -1

    # Assume no mathml or javascript in epub2 for the time being until a real
    # test can be determined walking all of the xhtml files.
    # For E3 we can use the manifest properties
    navid = None
    navfilename = None
    if E3:
        uses_mathml = False
        uses_script = False
        for mid, href, mtype, mprops, fallback, moverlay in bk.manifest_epub3_iter():
            if mprops is not None and "mathml" in mprops:
                uses_mathml = True
            if mprops is not None and "scripted" in mprops:
                uses_script = True
            if mprops is not None and "nav" in mprops:
                navid = mid
                urlobj = urlparse(href)
                path = unquote(urlobj.path)
                path = os.path.normcase(path)
                navfilename = os.path.basename(path)
        if navid is None:
            print("Error: nav property missing from the opf manifest propertiese")
            return -1
        if uses_mathml:
            print("Error: accessibility schema metadata is not set to handle mathml ... aborting")
            return -1
        if uses_script:
            print("Error: proper aria accessibility roles can not be set for javascripted applications .... aborting")
            return -1

    titlemap = {}
    etypemap = {}
    if E3:
        # epub3 - collect titlemap and etypemap from the nav
        titlemap, etypemap = parse_nav(bk, navid, navfilename)
    else:
        # epub2 - collect titlemap from the ncx
        tocid = bk.gettocid()
        titlemap = parse_ncx(bk, tocid)

    # now process every xhtml file (including the nav for E3)
    # adding primary language to html tag, setting the title,
    # and building up a list of image links so that alt attributes 
    # can be more easily added by the ebook developer.
    # and for E3 adding known nav landmark semantics epub:types 
    print("\nProcessing all xhtml files to add accessibility features")
    imglst = []
    for mid, href in bk.text_iter():
        print("   ... updating: ", href, " with manifest id: ", mid)
        xhtmldata, ilst = convert_xhtml(bk, mid, href, plang, titlemap, etypemap, E3)
        bk.writefile(mid, xhtmldata)
        if len(ilst) > 0:
            imglst.extend(ilst)

    # allow user to update alt info for each image tag
    print("\nBuilding a GUI to speed image alt attribute updates")

    # first prevent unsafe access of any files within Sigil 
    # by creating a temporary copy of each image in their own Images directory
    temp_dir = tempfile.mkdtemp()
    os.makedirs(os.path.join(temp_dir, "Images"))
    run_nsvg2png = False
    for mid, href, mime in bk.image_iter():
        imgdata = bk.readfile(mid)
        if mime == "image/svg+xml":
            imgdata = imgdata.encode('utf-8')
            run_nsvg2png = True
        filename = bk.href_to_basename(href)
        filepath = os.path.join(temp_dir, "Images", filename)
        with open(filepath, "wb") as f:
            f.write(imgdata)
        if run_nsvg2png:
            args=[exe_path, filepath]
            try: 
                process = Popen(args, stdout=PIPE, stderr=PIPE)
                res_out, res_err = process.communicate()
                retcode = process.returncode
            except:
                retcode = -1
            if retcode != 0:
                with open(os.path.join(SCRIPT_DIR, "missing_image.png"),"rb") as f:
                    imgdata = f.read()
                    filepath = filepath + ".png"
                    with open(filepath, "wb") as f:
                        f.write(imgdata)
            run_nsvg2png = False


    # now build a list of images and current alt text to pass to the gui
    altlist = []
    for (mid, filename, imgcnt, imgsrc, alttext) in imglst:
        print("   ... ", filename, " #", imgcnt, " src:", imgsrc, " alt text:", alttext)
        urlobj = urlparse(imgsrc)
        path = unquote(urlobj.path)
        path = os.path.normcase(path)
        if path.startswith('..'):
            path = path[3:]
        path = os.path.join(temp_dir, path)
        # handle svg that have been converted to pngs
        if path.endswith(".svg"):
            path = path + ".png"
        alttxt = xmldecode(alttext)
        altlist.append([path, alttxt])

    # Allow the User to Change Any alt text strings they desire
    basewidth = prefs['basewidth']
    naltlist = GUIUpdateFromList("Update Alt Text for Each Image", altlist, basewidth)

    # done with temp folder so clean up after yourself
    shutil.rmtree(temp_dir)


    # process results of alt text gui updates and update the actual xhtml
    print("\n\n Updating any changed alt attributes for img tags")
    ptr = 0
    for imgpath, altnew in naltlist:
        mid, filename, imgcnt, imgsrc, alttext = imglst[ptr]
        if alttext != altnew:
            print("    ... alt text needs to be updated in: ", filename, imgsrc, altnew)
            data = bk.readfile(mid)
            data = update_alt_text(bk, data, imgcnt, imgsrc, altnew)
            bk.writefile(mid, data)
        ptr += 1
    
    print("Updating Complete")
    bk.savePrefs(prefs)

    # Setting the proper Return value is important.
    # 0 - means success
    # anything else means failure
    return 0
 

# parse the nav, building up a list of first toc titles for each new xhtml file
# to use as html head title tags, also parse the first h1 tag to get a potential 
# title for the nav file itself
# and parse the landmarks to collect epub:type semantics set on files and fragments
# returns the dictioanry of titles by filename and dictionary of epub:type landmarks
def parse_nav(bk, navid, navfilename):
    print("\nParsing the nav to collect landmark epub:type info and titles for each xhtml file")
    titlemap = {}
    etypemap = {}
    qp = bk.qp
    qp.setContent(bk.readfile(navid))
    in_toc = False
    in_lms = False
    getlabel = False
    navtitle = None
    tochref = None
    prevfilename = ""
    for text, tagprefix, tagname, tagtype, tagattr in qp.parse_iter():
        if text is None:
            if tagname == "nav" and tagtype == "begin":
                if tagattr is not None and "epub:type" in tagattr:
                    in_toc = tagattr["epub:type"] == "toc"
                    in_lms = tagattr["epub:type"] == "landmarks"
            if in_toc and tagname == "a" and tagtype == "begin":
                if tagattr is not None and "href" in tagattr:
                    tochref = tagattr["href"]
                    getlabel = True
            if in_lms and tagname == "a" and tagtype == "begin":
                if tagattr is not None and "href" in tagattr:
                    lmhref = tagattr["href"]
                    if "epub:type" in tagattr:
                        etype = tagattr["epub:type"]
                        urlobj = urlparse(lmhref)
                        path = unquote(urlobj.path)
                        path = os.path.normcase(path)
                        filename = os.path.basename(path)
                        fragment = urlobj.fragment
                        if fragment == '':
                            etypemap[filename] = ("body", '', etype)
                        else:
                            etypemap[filename] = ("id", fragment, etype)
        else:
            if navtitle is None and tagprefix.endswith("h1"):
                navtitle = text
                titlemap[navfilename] = navtitle
            if in_toc and getlabel:
                if tochref is not None:
                    urlobj = urlparse(tochref)
                    path = unquote(urlobj.path)
                    path = os.path.normcase(path)
                    filename = os.path.basename(path)
                    if filename != prevfilename:
                        titlemap[filename] = text
                    prevfilename = filename
                tochref = None
                getlabel = False

    return titlemap, etypemap


# parse the current toc.ncx to create a titlemap
def parse_ncx(bk, tocid):
    ncxdata = bk.readfile(tocid)
    bk.qp.setContent(ncxdata)
    titlemap = {}
    navlable = None
    skip_if_newline = False
    lvl = 0
    prevfilename = ""
    for txt, tp, tname, ttype, tattr in bk.qp.parse_iter():
        if txt is not None:
            if tp.endswith('.navpoint.navlabel.text'):
                navlabel = txt.strip()
        else:            
            if tname == "content" and tattr is not None and "src" in tattr and tp.endswith("navpoint"):
                href =  tattr["src"]
                urlobj = urlparse(href)
                path = unquote(urlobj.path)
                path = os.path.normcase(path)
                filename = os.path.basename(path)
                if filename != prevfilename:
                    titlemap[filename] = navlabel
                prevfilename = filename
                navlabel = None
    return titlemap


# convert xhtml to be more Accessibility friendly
#  - add lang and xml:lang to html tag attributes
#  - add title info to head title tag
#  - collect info on image use and contents of related alt attributes
#  - add known epub:type semantics from nav landmarks to body tag or tag with "fragment" 
#  - add aria role attributes to complement existing epub:type attributes
# returns updated xhtml and list of lists for images (manifest_id, filename, image_count, image_src, alt_text)
def convert_xhtml(bk, mid, href, plang, titlemap, etypemap, E3):
    res = []
    #parse the xhtml, converting on the fly to update it
    qp = bk.qp
    qp.setContent(bk.readfile(mid))
    filename = bk.href_to_basename(href)
    maintitle = None
    loctype = ""
    fragment = ""
    etype = ""
    if filename in etypemap:
        (loctype, fragment, etype) = etypemap[filename] 
    imgcnt = 0
    imglst = []
    for text, tprefix, tname, ttype, tattr in qp.parse_iter():
        if text is not None:
            # get any existing title in head
            if "head" in tprefix and tprefix.endswith("title"):
                if text != "":
                    maintitle = text
            res.append(text)
        else:
            # add missing epub:type for nav landmarks that point to fragments
            if E3 and loctype == "id" and ttype in ("single", "begin"):
                if "id" in tattr:
                    id = tattr["id"]
                    if id == fragment and "epub:type" not in tattr:
                        tattr["epub:type"] = etype

            # add mssing epub:type for nav landmarks that have no fragments
            if E3 and loctype == "body" and tname == "body" and ttype == "begin":
                    if "epub:type" not in tattr:
                        tattr["epub:type"] = etype

            # add primary language attributes to html tag
            if tname == "html" and ttype=="begin":
                tattr["lang"] = plang
                tattr["xml:lang"] = plang

            # add missing alt text attributes on img tags
            # build up list of img links and current alt text
            if tname == "img" and ttype in ("single", "begin"):
                imgcnt += 1
                alttext = tattr.get("alt", "")
                tattr["alt"] = alttext
                imgsrc = tattr.get("src","")
                imglst.append((mid,filename,imgcnt,imgsrc,alttext)) 

            # build add any aria roles you know based on epub:type attributes
            if E3:
                if ttype in ["begin", "single"] and "epub:type" in tattr and "role" not in tattr:
                    epubtype = tattr["epub:type"]
                    if epubtype in _epubtype_aria_map:
                        ariarole = _epubtype_aria_map[epubtype]
                        tattr["role"] = ariarole

            # inject any missing titles if possible
            if tname == "title" and ttype == "end" and "head" in tprefix:
                if maintitle is None:
                    res.append(titlemap.get(filename,""))

            res.append(qp.tag_info_to_xml(tname, ttype, tattr))

    return "".join(res), imglst


# update xhtml img tag alt attribute text
# returns updated xhtml
def update_alt_text(bk, xhtmldata, imgcnt, imgsrc, alttext):
    res = []
    imgptr = 0
    #parse the xhtml, converting on the fly to update it
    qp = bk.qp
    qp.setContent(xhtmldata)
    for text, tprefix, tname, ttype, tattr in qp.parse_iter():
        if text is not None:
            res.append(text)
        else:
            # add missing alt text attributes on img tags
            # build up list of img links and current alt text
            if tname == "img" and ttype in ("single", "begin"):
                imgptr += 1
                if imgptr == imgcnt:
                    tattr["alt"] = xmlencode(alttext)
            res.append(qp.tag_info_to_xml(tname, ttype, tattr))
    return "".join(res)


def main():
    print("I reached main when I should not have\n")
    return -1
    
if __name__ == "__main__":
    sys.exit(main())

