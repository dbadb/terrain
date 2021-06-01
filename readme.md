http://gis.ess.washington.edu/data/
https://www.ocean.washington.edu/data/pugetsound/datasets/psdem2000/rasters/complete/psdem_2000.zip
http://gis.ess.washington.edu/data/raster/thirtymeter/wabil30/index.html
http://pugetsoundlidar.org/
http://pugetsoundlidar.ess.washington.edu/lidardata/restricted/be_dem/be_hsd_qq_spn/index.html

Input file has
ncols: 6740
nrows: 7600

```bash
./DEMtoOBJ.py PugetSound.dem -subset 0 0 999 999 -zscale .1 -o section00.obj
./DEMtoOBJ.py PugetSound.dem -subset 1000 1000 1999 1999 -zscale .1 -o section11.obj

DEMtoPNG.py PugetSound.dem -o PugetSound.png [-zmode all]
DEMtoPNG.py PugetSound.dem -o PugetSound.Land.png -zmode positive
```

```bash
 # clamp all positive values to 0, then offset all by -zmin.
 # so data goes from 0 (deep) to -zmin (land)
 DEMtoPNG.py PugetSound.dem -o PugetSound.underwater.png -zmode negative
```

```bash
# to manufacture we'd like our obj file to reside in the units of
# our target stock 15"x13"x1" => 381 x 330.2 x 25.4 mm
# if the data is 870x870 = we map 870 to 330 (so the pixelsize is .379mm).
# for zrange we'd like to use 3/4 of the stock depth: 19mm
# input data is in decimeters to 
# zscale: .1 zmax: 1000 => zscale = .1/19,

PNGtoOBJ.py  Bainbridge.underwater.png \
    -pixelsize .379 \
    -zscale .00526 -zmax 19  \
    -o Bainbridge.underwater.obj
```
