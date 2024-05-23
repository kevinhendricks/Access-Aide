**[Plugin] Access-Aide - help improve epub accessibility**

Updated: May 23, 2024

Current Version: "0.9.6"

License/Copying: GNU LGPL Version 2 or Version 3, your choice. Any other license terms are only available directly from the author in writing.

Minimum Sigil Version: 1.6.0.
Support for this plugin is provided for Sigil 1.6.0 and later using the Python 3.4 or later Python interpreter that supports Qt used in Python via PyQt5 or PySide6 for Qt6.


**Goal**
The goal of this program is to help improve the Accessibility of your epub to help meet ACE requirements. It strives to create an epub that meets the following criteria:

    schema:accessMode:              textual
    schema:accessMode:              visual
    schema:accessModeSufficient:    textual
    schema:accessibilityFeature:    structuralNavigation
    schema:accessibilitySummary:    This publication conforms to WCAG 2.0 AA.
    schema:accessibilityHazard:     none


**Before you run Access-Aide**
Before running AccessAide you should make sure your epub has passed epubcheck and that you have properly added the appropriate semantic tags to mark your ebook files appropriately. 


**How it Works**
This edit plugin will read/edit the content.opf to determine the primary language used, identify any nav or ncx and will add the appropriate metadata and add xml:lang to the OPF package tag if missing.
The ncx or nav is then parsed to collect titles for every xhtml file and in the case of the nav will also collect epub:type landmark information.

Then for each xhtml file, the plugin will:
1. add lang and xml:lang attributes to the html element
2. fill in any missing title tag that is a child of the head tag
3. will add empty alt attributes to any img tag where it is missing
4. collect a list of all image tags and their current alt text descriptions
5. add in appropriate epub:type semantic tags (for epub3 only)
6. map epub:type attributes to their appropriate aria role attribute

Then a graphical user interface is generated showing a thumbnail of every img tag image and its associated alt text description, so that the user can easily and quickly add or improve textual descriptions for each image used


**Limitations ...**
1. In able to properly achieve the schema:accessModeSufficient: textual critieria, Access-Aide will abort when provided with epubs that use javascripts, audio resources, video resources, and mathml because Access-Aide simply can not tell if the proper textual descriptions are provided in these cases.

2. The schema:accessibilityHazard set to none indicates you are using only **static** images with no Video and no animated gifs. You need to verify that or manually update that metadata in the opf.

3. svg:image tags are ignored as the "alt" attribute is not allowed on those tags. The proper way to handle svg:image tags is to provide the proper title and desc elements immediately after the svg start tag that contains the image element.

Access-Aide Plugin icon
This plugin includes a plugin icon that is in the public domain and provided by the The Accessible Icon Project that can be found at: https://accessibleicon.org for the express purpose for promoting accessibility.


Thanks to DiapDealer, Doitsu, and elibrarian with their help testing and debugging earlier versions of the this plugin and for elibrarian for for promoting the idea in the first place.


See the Sigil Plugin Index on MobileRead to find out more about this plugin and other plugins available for Sigil:
https://www.mobileread.com/forums/showthread.php?t=247431
