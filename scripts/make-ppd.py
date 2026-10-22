#!/usr/bin/env python3
"""Generate the CUPS PPD for the Xerox Phaser 3020 over raw USB.

The page geometry mirrors what the printer reports over IPP
(media-col-default: 440 centimilimetre margins on every edge = 12.4724 pt).
"""
import sys

FILTER = "/Library/Printers/Xerox/P3020/urftopjl"
MARGIN = 12.4724

# name, width pt, height pt
PAPERS = [
    ("A4",                 595.2756,  841.8898),
    ("Letter",             612.0000,  792.0000),
    ("Legal",              612.0000, 1008.0000),
    ("A5",                 419.5276,  595.2756),
    ("B5",                 515.9055,  728.5039),
    ("ISOB5",              498.8976,  708.6614),
    ("Executive",          522.0000,  756.0000),
    ("FanFoldGermanLegal", 612.0000,  936.0000),
    ("8.5x13.5",           612.0000,  972.0000),
    ("4x6",                288.0000,  432.0000),
    ("Env10",              296.9858,  684.0000),
    ("EnvC5",              459.2126,  649.1339),
    ("EnvDL",              311.8110,  623.6220),
    ("EnvMonarch",         278.9858,  540.0000),
]

DEFAULT_PAPER = "A4"

def setpagedevice(w, h):
    return f"<</PageSize[{w:.4f} {h:.4f}]/ImagingBBox null/Orientation 0>>setpagedevice"

def main(out):
    L = []
    add = L.append
    add('*PPD-Adobe: "4.3"')
    add('*% Xerox Phaser 3020 - raw USB (Apple Raster wrapped in PJL)')
    add('*% https://github.com/atilac/xerox-phaser-3020-macos')
    add('*% SPDX-License-Identifier: MIT')
    add('*FormatVersion: "4.3"')
    add('*FileVersion: "1.0"')
    add('*LanguageVersion: English')
    add('*LanguageEncoding: ISOLatin1')
    add('*PSVersion: "(3010.000) 0"')
    add('*LanguageLevel: "3"')
    add('*FileSystem: False')
    add('*PCFileName: "XRXP3020.PPD"')
    add('*Manufacturer: "Xerox"')
    add('*ModelName: "Xerox Phaser 3020"')
    add('*Product: (Xerox Phaser 3020)')
    add('*ShortNickName: "Xerox Phaser 3020 USB"')
    add('*NickName: "Xerox Phaser 3020 - USB (urftopjl)"')
    add('*Throughput: "21"')
    add('*cupsVersion: 2.0')
    add('*cupsModelNumber: 0')
    add('*cupsSNMPSupplies: False')
    add('*cupsSingleFile: True')
    add('*cupsMaxCopies: 255')
    add('')
    add('*% The printer accepts URF over USB only when PJL announces it.')
    add(f'*cupsFilter2: "image/urf image/urf 10 {FILTER}"')
    add('*APURFVersion: 1.3')
    add('*APAcceptsMixedURF: True')
    add('*cupsUrfSupported: "W8,RS600,IS1,CP1,IFU0,PQ4,OB10,V1.3"')
    add('')
    add('*ColorDevice: False')
    add('*DefaultColorSpace: Gray')
    add('*OpenUI *ColorModel/Color Mode: PickOne')
    add('*OrderDependency: 10 AnySetup *ColorModel')
    add('*DefaultColorModel: Gray')
    add('*ColorModel Gray/Grayscale: "<</cupsColorSpace 18/cupsBitsPerColor 8'
        '/cupsColorOrder 0/cupsCompression 0>>setpagedevice"')
    add('*CloseUI: *ColorModel')
    add('')
    add('*DefaultResolution: 600x600dpi')
    add('*OpenUI *cupsPrintQuality/Quality: PickOne')
    add('*OrderDependency: 10 AnySetup *cupsPrintQuality')
    add('*DefaultcupsPrintQuality: Normal')
    add('*cupsPrintQuality Normal: "<</cupsInteger1 4 /HWResolution[600 600]>>setpagedevice"')
    add('*CloseUI: *cupsPrintQuality')
    add('')
    add('*LandscapeOrientation: Plus90')
    add('*DefaultOutputOrder: Normal')
    add('')
    for key, label in (("PageSize", "Media Size"), ("PageRegion", "Media Size")):
        add(f'*OpenUI *{key}/{label}: PickOne')
        add(f'*OrderDependency: 10 AnySetup *{key}')
        add(f'*Default{key}: {DEFAULT_PAPER}')
        for name, w, h in PAPERS:
            add(f'*{key} {name}: "{setpagedevice(w, h)}"')
        add(f'*CloseUI: *{key}')
        add('')
    add(f'*DefaultImageableArea: {DEFAULT_PAPER}')
    add(f'*DefaultPaperDimension: {DEFAULT_PAPER}')
    for name, w, h in PAPERS:
        add(f'*PaperDimension {name}: "{w:.4f} {h:.4f}"')
        add(f'*ImageableArea {name}: "{MARGIN:.4f} {MARGIN:.4f} '
            f'{w - MARGIN:.4f} {h - MARGIN:.4f}"')
    add('')
    with open(out, "w") as fh:
        fh.write("\n".join(L) + "\n")
    print(f"wrote {out} ({len(L)} lines)")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "ppd/Xerox_Phaser_3020_USB.ppd")
