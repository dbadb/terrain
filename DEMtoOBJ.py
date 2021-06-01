#!/usr/bin/env python

import os
import sys

def usage(nm, msg=""):
    print(msg + "\nusage: %s DEMFILE "
     "[-subset colmin rowmin colmax rowmax] "
     "[-downsample int] "
     "[-info] (output is DEMFILE.obj)" % nm)
    sys.exit(1)

def main():
    appnm = os.path.basename(sys.argv[0])  # 0 is python
    config = {}
    config["appnm"] = appnm
    config["subset"] = None
    config["demfile"] = None
    config["headeronly"] = False
    config["zscale"] = 1.
    config["downsample"] = 1
    demfile = None
    objfile = None
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
        elif a == "-zscale" or a == "-z":
            config["zscale"] = float(args[i+1])
            i += 2
        elif a == "-o":
            objfile = args[i+1] 
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
    
    if not objfile:
        objfile = demfile + ".obj"

    convertToOBJ(config, demfile, objfile)

def createOBJFile(ofile, header):
    ostream = open(ofile, "w")
    ostream.write("# DEMtoOBJ \n")
    ostream.write("# ncols: %d\n" % header["ncols"])
    ostream.write("# nrows: %d\n" % header["nrows"])
    ostream.write("# cellsize: %d\n" % header["cellsize"])
    ostream.write("# xllcorner: %d\n" % header["xllcorner"])
    ostream.write("# yllcorner: %d\n" % header["yllcorner"])
    ostream.write("# zscale: %g\n" % header["zscale"]);
    if header["subset"]:
        ostream.write("# subset: %s\n" % str(header["subset"]))
    return ostream

# OBJ file 
#   https://en.wikipedia.org/wiki/Wavefront_.obj_file
# 
# v: vertex
# vt: texture coords
# vn: vertex normals
# faces require vertex _indices_
# f: v1 v2 v3
# or:  v1/vt1 v2/vt2 v3/vt3
# or:  v1//vn1 v2//vn2 v3//vn3
# or:  v1/vt1/vn1 v2/vt2/vn2 v3/vt3/vn3
def convertToOBJ(cfg, ifile, ofile):
    # https://nodejs.org/api/readline.html#readline_example_read_file_stream_line_by_line
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

    zoom = cfg["downsample"]
    if zoom != 1:
        # A cell (ie pixel) represents a larger area when downsampled.
        # The center of a downsampled cell should be the avg of all hi-res
        # cells centers.  Currently we're a little sloppy with coordinate
        # preservation.
        cellsize_out = cellsize * zoom
        ncols_out = ncols / zoom
        nrows_out = nrows / zoom

    print("Input file has\n"
        "ncols: %d\n"
        "nrows: %d\n"
        "xllcorner: %d\n"
        "yllcorner: %d\n"
        "cellsize: %d\n"
        "NODATA_value: %d\n"
        "downsample: %d" %
        (ncols, nrows, xllcorner, yllcorner, cellsize, NODATA_value, zoom))

    if cfg["headeronly"]:
        sys.exit(0)

    print("\n-------------------\n"
        "Output file has\n"
        "ncols: %d\n"
        "nrows: %d\n"
        "xllcorner: %d\n"
        "yllcorner: %d\n"
        "cellsize: %d\n"
        "downsample: %d" %
        (ncols_out, nrows_out, xllcorner_out, yllcorner_out, 
            cellsize_out, zoom))

    header_out = {}
    header_out["ncols"] = ncols_out
    header_out["nrows"] = nrows_out
    header_out["xllcorner"] = xllcorner_out
    header_out["yllcorner"] = yllcorner_out
    header_out["cellsize"] = cellsize_out
    header_out["NODATA_value"] = NODATA_value
    header_out["subset"] = cfg["subset"]
    header_out["downsample"] = zoom
    header_out["zscale"] = cfg["zscale"]

    y = 0 # rows
    ostream = None

    nverts = 0
    zscale = cfg["zscale"]
    if zoom == 1:
        for row in range(nrows):
            if row == 0:
                ostream = createOBJFile(ofile, header_out)

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
                        nverts += 1
                        z = float(heights[col]) * zscale
                        ostream.write("v %g %g %g\n" % (x,y,z))
                    x += cellsize
            row += 1
            y += cellsize
        print("Wrote %d vertices" % (nverts))
        print("Now onto faces ...") 

        # OBJ: vertex index origin is 1
        #  two triangles per cell, alternating
        #  v1  v2  v3
        #  |\  |  /|   top
        #  | \ | / |
        #  |  \|/  |   bottom
        #  v4  v5  v6
        #  +===+===+
        #  |\  |  /|   top
        #  | \ | / |
        #  |  \|/  |   bottom
        #  v7  v8  v9

        # f 1 5 4, f 1 2 5, f 2 3 5, f 3 6 5
        # f 4 8 7, f 4 5 8, f 5 6 8, f 6 9 8
        topV = 1
        bottomV = 0
        nfaces = 0
        for row in range(nrows_out-1): # excludes endrow
            topV = row * ncols_out + 1
            bottomV = topV + ncols_out
            even = True
            for col in range(ncols_out-1): # excludes endcol
                if even:
                    ostream.write("f %d %d %d\n" % (topV, bottomV+1, bottomV))
                    ostream.write("f %d %d %d\n" % (topV, topV+1, bottomV+1))
                else:
                    ostream.write("f %d %d %d\n" % (topV, topV+1, bottomV))
                    ostream.write("f %d %d %d\n" % (topV+1, bottomV+1, bottomV))
                nfaces += 2
                even = not even
                topV += 1
                bottomV += 1
            if (row != 0 and row % 500) == 0:
                print("%d faces" % nfaces)
        print("Wrote %d faces" % nfaces)
    else:
        print("zoom implementation lacking")

if __name__ == "__main__":
    main() 
