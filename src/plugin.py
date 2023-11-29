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
import re
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
    "cover-image"     : "doc-cover",
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
    "glossdef"        : "definition",
    "glossref"        : "doc-glossref",
    "glossterm"       : "term",
    "index"           : "doc-index",
    "introduction"    : "doc-introduction",
    "landmarks"       : "directory",
    "list"            : "list",
    "list-item"       : "listitem",
    "noteref"         : "doc-noteref",
    "notice"          : "doc-notice",
    "page-list"       : "doc-pagelist",
    "pagebreak"       : "doc-pagebreak",
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

_aria_role_allowed_tags = {
    "doc-abstract"       : ("section"),
    "doc-acknowledgments": ("section"),
    "doc-afterword"      : ("section"),
    "doc-appendix"       : ("section"),
    "doc-biblioentry"    : ("li"),
    "doc-bibliography"   : ("section"),
    "doc-biblioref"      : ("a"),
    "doc-chapter"        : ("section"),
    "doc-colophon"       : ("section"),
    "doc-conclusion"     : ("section"),
    "doc-cover"          : ("img"),
    "doc-credit"         : ("section"),
    "doc-credits"        : ("section"),
    "doc-dedication"     : ("section"),
    "doc-endnote"        : ("li"),
    "doc-endnotes"       : ("section"),
    "doc-epigraph"       : (),
    "doc-epilogue"       : ("section"),
    "doc-errata"         : ("section"),
    "figure"             : (),
    "doc-footnote"       : ("aside","footer","header"),
    "doc-foreword"       : ("section"),
    "doc-glossary"       : ("section"),
    "definition"         : (),
    "doc-glossref"       : ("a"),
    "term"               : (),
    "doc-index"          : ("nav","section"),
    "doc-introduction"   : ("section"),
    "directory"          : ("ol","ul"),
    "list"               : (),
    "listitem"           : (),
    "doc-noteref"        : ("a"),
    "doc-notice"         : ("section"),
    "doc-pagelist"       : ("nav","section"),
    "doc-pagebreak"      : ("hr"),
    "doc-part"           : ("section"),
    "doc-preface"        : ("section"),
    "doc-prologue"       : ("section"),
    "doc-pullquote"      : ("aside","section"),
    "doc-qna"            : ("section"),
    "doc-backlink"       : ("a"),
    "doc-subtitle"       : ("h1","h2","h3","h4","h5","h6"),
    "table"              : (),
    "cell"               : (),
    "row"                : (),
    "doc-tip"            : ("aside"),
    "doc-toc"            : ("nav","section"),
}

# these tags allow all aria roles
# subject to some conditions
# conditions field: (href_allowed, need_alt)
_all_role_tags = {
    "a"          : (False, False),
    "abbr"       : (True, False),
    "address"    : (True, False),
    "b"          : (True, False),
    "bdi"        : (True, False),
    "bdo"        : (True, False),
    "blockquote" : (True, False),
    "br"         : (True, False),
    "canvas"     : (True, False),
    "cite"       : (True, False),
    "code"       : (True, False),
    "del"        : (True, False),
    "dfn"        : (True, False),
    "div"        : (True, False),
    "em"         : (True, False),
    "i"          : (True, False),
    "img"        : (False, True),
    "ins"        : (True, False),
    "kbd"        : (True, False),
    "mark"       : (True, False),
    "output"     : (True, False),
    "p"          : (True, False),
    "pre"        : (True, False),
    "q"          : (True, False),
    "rp"         : (True, False),
    "rt"         : (True, False),
    "ruby"       : (True, False),
    "s"          : (True, False),
    "samp"       : (True, False),
    "small"      : (True, False),
    "span"       : (True, False),
    "strong"     : (True, False),
    "sub"        : (True, False),
    "sup"        : (True, False),
    "table"      : (True, False),
    "tbody"      : (True, False),
    "td"         : (True, False),
    "tfoot"      : (True, False),
    "thead"      : (True, False),
    "th"         : (True, False),
    "tr"         : (True, False),
    "time"       : (True, False),
    "u"          : (True, False),
    "var"        : (True, False),
    "wbr"        : (True, False)
}

# epub 3.2 and aria rules makes this quite a mess
def _role_from_etype(etype, tname, has_href, has_alt):
    # first get role for epub type from map
    role = _epubtype_aria_map.get(etype, None)
    if role is None:
        return role
    # a possible role exists, check if allowed
    allowed = False
    # check if role would be in a tag that allows all roles
    # subject to conditions
    if tname in _all_role_tags:
        allowed = True
        (href_allowed, need_alt) = _all_role_tags[tname]
        if not href_allowed and has_href:
            allowed = False
        if need_alt and not has_alt:
            allowed = False
    if allowed:
        return role
    # still need to check for specifc additions/exceptions
    if role in _aria_role_allowed_tags:
        tagset = _aria_role_allowed_tags[role]
        if tname in tagset:
            return role
    return None

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

whitespace_re = re.compile("\s+")

# handle possible space delimtied multiple attribute values
def parse_attribute(avalue):
    vals = []
    if avalue is None:
        return vals
    val = avalue.strip()
    if " " in val:
        vals = whitespace_re.split(val)
    else:
        if val != "":
            vals.append(val)
    return vals

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
    print("\nUpdating the OPF with accessibility schema")
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
                    # if "-" in text:
                    #     plang, region = text.split("-")
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
                    res.append('<meta property="schema:accessibilityHazard">none</meta>\n')
                if not E3 and not has_access_meta:
                    res.append('<meta name="schema:accessibilitySummary" content="This publication conforms to WCAG 2.0 AA."/>\n')
                    res.append('<meta name="schema:accessMode" content="textual"/>\n')
                    res.append('<meta name="schema:accessModeSufficient" content="textual"/>\n')
                    res.append('<meta name="schema:accessibilityFeature" content="structuralNavigation"/>\n')
                    res.append('<meta name="schema:accessibilityHazard" content="none"/>\n')
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
                navfilename = os.path.basename(path)
                navbookpath = "OEBPS/Text/" + navfilename
                if bk.launcher_version() >= 20190927:
                    navbookpath = bk.id_to_bookpath(navid)
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
        # epub3 - collect titlemap and etypemap from the nav (key is file bookpath)
        titlemap, etypemap = parse_nav(bk, navid, navbookpath)
    else:
        # epub2 - collect titlemap from the ncx (key is file bookpath)
        tocid = bk.gettocid()
        ncxbookpath = "OEBPS/toc.ncx"
        if bk.launcher_version() >= 20190927:
            ncxbookpath = bk.id_to_bookpath(tocid)
        titlemap = parse_ncx(bk, tocid, ncxbookpath)

    # now process every xhtml file (including the nav for E3)
    # adding primary language to html tag, setting the title,
    # and building up a list of image links so that alt attributes 
    # can be more easily added by the ebook developer.
    # and for E3 adding known nav landmark semantics epub:types 
    print("\nProcessing all xhtml files to add accessibility features")
    imglst = []
    for mid, href in bk.text_iter():
        bookpath = "OEBPS/" + href
        if bk.launcher_version() >= 20190927:
            bookpath = bk.id_to_bookpath(mid)
    
        print("   ... updating: ", bookpath, " with manifest id: ", mid)
        xhtmldata, ilst = convert_xhtml(bk, mid, bookpath, plang, titlemap, etypemap, E3)
        bk.writefile(mid, xhtmldata)
        if len(ilst) > 0:
            imglst.extend(ilst)

    # allow user to update alt info for each image tag
    print("\nBuilding a GUI to speed image alt attribute updates")

    # first prevent unsafe access of any files within Sigil 
    # by creating a temporary copy of each image in temp_dir
    temp_dir = tempfile.mkdtemp()
    run_nsvg2png = False
    for mid, href, mime in bk.image_iter():
        imgdata = bk.readfile(mid)
        bookpath = "OEBPS/" + href
        if bk.launcher_version() >= 20190927:
            bookpath = bk.id_to_bookpath(mid)
        if mime == "image/svg+xml":
            imgdata = imgdata.encode('utf-8')
            run_nsvg2png = True
        filepath = os.path.join(temp_dir, bookpath.replace("/",os.sep))
        destdir = os.path.dirname(filepath)
        if not os.path.exists(destdir):
            os.makedirs(destdir)
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
    for (mid, bookpath, imgcnt, imgsrc, alttext) in imglst:
        print("   ... ", bookpath, " #", imgcnt, " src:", imgsrc, " alt text:", alttext)
        urlobj = urlparse(imgsrc)
        apath = unquote(urlobj.path)
        filename = os.path.basename(apath)
        imgbookpath = "OEBPS/Images/" + filename
        if bk.launcher_version() >= 20190927:
            imgbookpath = bk.build_bookpath(apath, bk.get_startingdir(bookpath))
        imgpath = os.path.join(temp_dir, imgbookpath.replace("/",os.sep))
        # handle svg that have been converted to pngs
        if imgpath.endswith(".svg"):
            imgpath = imgpath + ".png"
        alttxt = xmldecode(alttext)
        altlist.append([imgpath, alttxt])

    # Allow the User to Change Any alt text strings they desire
    basewidth = prefs['basewidth']
    naltlist = []
    if len(altlist) > 0:
       naltlist = GUIUpdateFromList("Update Alt Text for Each Image", altlist, basewidth)

    # done with temp folder so clean up after yourself
    shutil.rmtree(temp_dir)


    # process results of alt text gui updates and update the actual xhtml
    print("\n\nUpdating any changed alt attributes for img tags")
    ptr = 0
    for imgpath, altnew in naltlist:
        mid, bookpath, imgcnt, imgsrc, alttext = imglst[ptr]
        if alttext != altnew:
            print("    ... alt text needs to be updated in: ", bookpath, imgsrc, altnew)
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
# returns the dictionary of titles by bookpath and dictionary of epub:type landmarks
def parse_nav(bk, navid, navbookpath):
    print("\nParsing the nav to collect landmark epub:type info and titles for each xhtml file")
    nav_base = "OEBPS/Text"
    if bk.launcher_version() >= 20190927:
        nav_base = bk.get_startingdir(navbookpath)
    titlemap = {}
    etypemap = {}
    qp = bk.qp
    qp.setContent(bk.readfile(navid))
    in_toc = False
    in_lms = False
    getlabel = False
    navtitle = None
    tochref = None
    prevbookpath = ""
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
                        apath = unquote(urlobj.path)
                        filename = os.path.basename(apath)
                        bookpath = "OEBPS/Text/" + filename
                        if bk.launcher_version() >= 20190927:
                           bookpath = bk.build_bookpath(apath, nav_base)
                        fragment = urlobj.fragment
                        if fragment != '':
                            etypemap[bookpath] = ("id", fragment, etype)
                        # else:
                            # Arrgghhh! - epub:type tags on body tags 
                            # are now "strongly discouraged"
                            # etypemap[bookpath] = ("body", '', etype)
        else:
            if navtitle is None and tagprefix.endswith("h1"):
                navtitle = text
                titlemap[navbookpath] = navtitle
            if in_toc and getlabel:
                if tochref is not None:
                    urlobj = urlparse(tochref)
                    apath = unquote(urlobj.path)
                    filename = os.path.basename(apath)
                    bookpath = "OEBPS/Text/" + filename;
                    if bk.launcher_version() >= 20190927:
                        bookpath = bk.build_bookpath(apath, nav_base)
                    if bookpath != prevbookpath:
                        titlemap[bookpath] = text
                    prevbookpath = bookpath
                tochref = None
                getlabel = False

    return titlemap, etypemap


# parse the current toc.ncx to create a titlemap of bookpath to nav label
def parse_ncx(bk, tocid, ncxbookpath):
    ncx_base = "OEBPS"
    if bk.launcher_version() >= 20190927:
        ncx_base = bk.get_startingdir(ncxbookpath)
    ncxdata = bk.readfile(tocid)
    bk.qp.setContent(ncxdata)
    titlemap = {}
    navlable = None
    skip_if_newline = False
    lvl = 0
    prevbookpath = ""
    for txt, tp, tname, ttype, tattr in bk.qp.parse_iter():
        if txt is not None:
            if tp.endswith('.navpoint.navlabel.text'):
                navlabel = txt.strip()
        else:            
            if tname == "content" and tattr is not None and "src" in tattr and tp.endswith("navpoint"):
                href =  tattr["src"]
                urlobj = urlparse(href)
                apath = unquote(urlobj.path)
                filename = os.path.basename(apath)
                bookpath = "OEBPS/Text/" + filename
                if bk.launcher_version() >= 20190927:
                    bookpath = bk.build_bookpath(apath, ncx_base)
                if bookpath != prevbookpath:
                    titlemap[bookpath] = navlabel
                prevbookpath = bookpath
                navlabel = None
    return titlemap


# convert xhtml to be more Accessibility friendly
#  - add lang and xml:lang to html tag attributes
#  - add title info to head title tag
#  - collect info on image use and contents of related alt attributes
#  - add known epub:type semantics from nav landmarks to body tag or tag with "fragment" 
#  - add aria role attributes to complement existing epub:type attributes
# returns updated xhtml and list of lists for images (manifest_id, bookpath, image_count, image_src, alt_text)
def convert_xhtml(bk, mid, bookpath, plang, titlemap, etypemap, E3):
    res = []
    #parse the xhtml, converting on the fly to update it
    qp = bk.qp
    qp.setContent(bk.readfile(mid))
    maintitle = None
    loctype = ""
    fragment = ""
    etype = ""
    if bookpath in etypemap:
        (loctype, fragment, etype) = etypemap[bookpath] 
    imgcnt = 0
    imglst = []
    for text, tprefix, tname, ttype, tattr in qp.parse_iter():
        # bug in quickparser does not properly trim attribute names
        if tattr:
            nattr = {}
            for attname, attval in tattr.items():
                attname = attname.strip(' \v\t\n\r\f')
                nattr[attname] = attval
            tattr.clear()
            tattr = nattr
        if text is not None:
            # get any existing title in head, ignore whitespace
            if "head" in tprefix and tprefix.endswith("title"):
                if text.strip() != "":
                    maintitle = text
            res.append(text)
        else:
            # add missing epub:type for nav landmarks that point to fragments
            if E3 and loctype == "id" and ttype in ("single", "begin"):
                if "id" in tattr:
                    id = tattr["id"]
                    if id == fragment:
                        # handle epub:type possible multiple attribute values
                        vals = parse_attribute(tattr.get("epub:type",""))
                        if etype not in vals:
                            vals.append(etype)
                            tattr["epub:type"] = " ".join(vals)

            # This has been "strongly discouraged" so disabling it

            # add missing epub:type for nav landmarks that have no fragments
            # if E3 and loctype == "body" and tname == "body" and ttype == "begin":
            #     # handle epub:type possible multiple attribute values
            #     vals = parse_attribute(tattr.get("epub:type",""))
            #     if etype not in vals:
            #         vals.append(etype)
            #         tattr["epub:type"] = " ".join(vals)

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
                imglst.append((mid,bookpath,imgcnt,imgsrc,alttext)) 

            # build add any aria roles you know based on epub:type attributes
            # handle multiple epub:type attribute values
            # handle multiple aria role attribute values
            if E3:
                if ttype in ["begin", "single"] and "epub:type" in tattr:
                    evals = parse_attribute(tattr["epub:type"])
                    rvals = parse_attribute(tattr.get("role",""))
                    has_href = "href" in tattr
                    has_alt = "alt" in tattr
                    for ept in evals:
                        ariarole = _role_from_etype(ept, tname, has_href, has_alt)
                        if ariarole is not None:
                            if ariarole not in rvals:
                                rvals.append(ariarole)
                    # multiple aria roles are discouraged only first
                    # will be used
                    if len(rvals) > 0:
                        tattr["role"] = " ".join(rvals)

            # inject any missing titles if possible
            if tname == "title" and ttype == "end" and "head" in tprefix:
                if maintitle is None:
                    res.append(titlemap.get(bookpath,""))

            # inject any missing titles in self closed title tags  if needed
            if tname == "title" and ttype == "single" and "head" in tprefix:
                ttype = "begin"
                res.append(qp.tag_info_to_xml(tname, ttype, tattr))
                res.append(titlemap.get(bookpath,""))
                tattr = {}
                ttype = "end"

            # work around quickparser serialization bug in Sigil 1.4.3 and earlier
            if bk.launcher_version() < 20210203:
                if ttype == "xmlheader":
                    if tattr and "special" in tattr:
                        tattr["special"] = tattr["special"].strip()
                        
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

