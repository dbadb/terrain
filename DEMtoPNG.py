#!/usr/bin/env python

# - read a usgs dem, 
# - convert first to rgba, 16 bit, single channel .png
#   - where we hit NODATA_value we apply an alpha of 0
# - write out the png file for inspection by, eg gimp
# - optionally convert resulting PNG buffer to OBJ

import os
import sys
import numpy as np
# import cv2 (doesn't support 2 channel pngs)
import png  # from pip3 install pypng

def usage(nm, msg=""):
    print(msg + "\nusage: %s DEMFILE "
     "[-subset colmin rowmin colmax rowmax] "
     "[-o outputfile (default is DEMFILE.PNG)] "
     "[-zmode all|negative|positive] "
     "[-info]" % nm)
    sys.exit(1)

def main():
    appnm = os.path.basename(sys.argv[0])  # 0 is python
    config = {}
    config["appnm"] = appnm
    config["subset"] = None
    config["demfile"] = None
    config["headeronly"] = False
    config["zmode"] = "all"
    config["downsample"] = 1
    demfile = None
    outfile = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        # print("%d:%s" % (i, a))
        if a == "-subset" or a ==  "-s":
            if (i + 4) < len(args):
                config["subset"] = [int(args[i+1]), int(args[i+2]),
                          int(args[i+3]), int(args[i+4])]
                if(config["subset"][0] >= config["subset"][2] or 
                   config["subset"][1] >= config["subset"][3]):
                    usage(appnm, "Invalid subset") # exits
                i += 5
            else:
                # print("len(args):%d i:%d" % (len(args), i))
                usage(appnm) # exits
        elif a == "-info" or a == "-i":
            config["headeronly"] = True
            i += 1
        elif a == "-downsample" or a == "-d":
            config["downsample"] = int(args[i+1])
            i += 2
        elif a == "-zmode" or a == "-z":
            config["zmode"] = args[i+1]
            i += 2
        elif a == "-o":
            outfile = args[i+1] 
            i += 2
        else:
            if demfile == None:
                demfile = a
                i += 1
            else:
                print("Unexpected param %s" % a)
                usage(appnm)

    if not demfile:
        usage(appnm)  #exits
    
    if not outfile:
        outfile = demfile + ".png"

    convertToPNG(config, demfile, outfile)

def convertToPNG(cfg, ifile, ofile):
    fin = open(ifile, "r")

    # Read the header     
    line = fin.readline().split()
    ncols = int(line[1])
    line = fin.readline().split()
    nrows = int(line[1])
    line = fin.readline().split()
    xllcorner = float(line[1])
    line = fin.readline().split()
    yllcorner = float(line[1])
    line = fin.readline().split()
    cellsize = float(line[1])
    line = fin.readline().split()
    NODATA_value = float(line[1])

    xllcorner_out = xllcorner
    yllcorner_out = xllcorner
    colmin = 0
    rowmin = 0
    colmax = ncols - 1
    rowmax = nrows - 1
    nrows_out = nrows
    ncols_out = ncols
    cellsize_out = cellsize
    if cfg["subset"] != None:
        # subset: [colmin, rowmin, colmax, rowmax]
        colmin = cfg["subset"][0]
        colmax = cfg["subset"][2] 
        rowmin = cfg["subset"][1]
        rowmax = cfg["subset"][3]
        xllcorner_out = xllcorner + colmin * cellsize
        yllcorner_out = yllcorner + rowmin * cellsize
        ncols_out = colmax - colmin + 1
        nrows_out = rowmax - rowmin + 1

    print("Input file has\n"
        "ncols: %d\n"
        "nrows: %d\n"
        "xllcorner: %d\n"
        "yllcorner: %d\n"
        "cellsize: %d\n"
        "NODATA_value: %d\n" %
        (ncols, nrows, xllcorner, yllcorner, cellsize, NODATA_value))

    if cfg["headeronly"]:
        sys.exit(0)

    print("\n-------------------\n"
        "Output file has\n"
        "ncols: %d\n"
        "nrows: %d\n"
        "xllcorner: %d\n"
        "yllcorner: %d\n"
        "cellsize: %d\n" %
        (ncols_out, nrows_out, xllcorner_out, yllcorner_out, 
            cellsize_out))
    
    # https://stackoverflow.com/questions/60772938
    # cv2.imwrite only supports 1, 3 and 4 channels
    # so we use pypng, which requires interleaved values (happens
    # after arrays are filled via magic np.reshape)
    img = np.zeros((nrows_out, ncols_out), dtype=np.uint16) 
    a = np.full((nrows_out, ncols_out), 65535, dtype=np.uint16) 

    zmode = cfg["zmode"]
    zmax = 0
    zmin = 65535
    y = 0 # rows
    ostream = None
    npixels = 0
    nbad = 0
    for row in range(nrows):
        if row >= rowmin and row <= rowmax:
            # write all the vertices
            # x, y are row and column scaled by cellsize
            # z is the elevation value (potentially scaled)
            lrow = row - rowmin
            if lrow > 0 and (lrow % 100) == 0:
                print("read %d/%d" % (lrow, nrows_out))
            heights = fin.readline().split()
            x = 0
            for col in range(ncols):
                if col >= colmin and col <= colmax:
                    lcol = col - colmin
                    z = int(heights[col])
                    if z == NODATA_value:
                        a[lrow][lcol] = 0 # <------
                        nbad += 1
                    else:
                        if zmode == "negative":
                            if z > 0:
                                z = 0
                        elif zmode == "positive":
                            if z < 0:
                                z = 0
                        if z > zmax:
                            zmax = z
                        if z < zmin:
                            zmin = z

                        img[lrow][lcol] = z # "all" fixes up negatives below
                    npixels += 1
                x += cellsize
        row += 1
        y += cellsize
    
    # negative numbers are possible, so we'll just offset by zmin
    if zmin < 0:
        zoff = -zmin
        zmin += zoff
        zmax += zoff
        print("offsetting by %d" % zoff)
        img += zoff # yay numpy!
    
    print("writing %d pixels zrange: [%d, %d], nbad: %d (%g)%%" % 
        (npixels, zmin, zmax, nbad, nbad/float(npixels)))
    img3d = np.dstack((img, a))
    print("img3d " + str(img3d.shape))
    img2d = np.reshape(img3d, (-1, ncols_out*2)) # interleave
    print("img2d " + str(img2d.shape))

    with open(ofile, "wb") as out:
        pngWrite = png.Writer(ncols_out, nrows_out, 
                greyscale=True, alpha=True, bitdepth=16)
        pngWrite.write(out, img2d)
        print("Wrote %s" % ofile)

if __name__ == "__main__":
    main() 
