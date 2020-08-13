#! /usr/bin/env python

"""
Script to take a Dicom series and generate an STL surface mesh.

Written by David T. Chen from the National Institute of Allergy
and Infectious Diseases, dchen@mail.nih.gov.
It is covered by the Apache License, Version 2.0:
http://www.apache.org/licenses/LICENSE-2.0

Note: if you run this script with the individual Dicom slices provided on the
command line, they might not be ordered in the correct order.  You are better
off providing a zip file or a directory.  Dicom slices are not necessarily
ordered the same alphabetically as they are physically.

Modifications:
    - Baked-in best parameters for processing Skulls CT Scans for SkullNet project
        - Isocountering (Isovalue) = 150
        - Smooth Iterations = 5,0000
        - Reduction factor (quad) = 0.75 
    - Added folder/subfolder batch processing loop
    - Added Error handling and logging.
Usage:
    - python dicom2stl_tuned.py -o output_folder input_parent_folder
    
Juan Fernando Pinzon 
Novel Software Systems
Novosibirsk, Russia
06.2020
"""

from __future__ import print_function
import sys, os, getopt, time, gc, glob, math, datetime, logging
import zipfile, tempfile

start = datetime.datetime.now()

# Global variables
#
verbose = 1
debug = 0

zipFlag = False
dicomString = ""
cleanUp = True
tempDir = ""
dirFlag = False

isovalue = 150
CTonly = False
doubleThreshold = False
thresholds = []
tissueType = ""
shrinkFlag = False

smoothIterations = 5000
quad = .75
outname = "results.stl"
connectivityFilter = False
anisotropicSmoothing = False
medianFilter = False
metadataFile = ""
modality = ""

rotFlag = False
rotAxis = 1
rotAngle = 180

options = []


def usage():
    print("""
    dicom2stl.py: [options] dicom_directory
    
        -h, --help          This help message
        -v, --verbose       Verbose output
        -D, --debug         Debug mode

        -o string           Output file name (default=result.stl)
        -m string           Metadata file name (default=\"\")
        --ct                Only allow CT images
        -c, --clean         Clean up temp files
        -T string, --temp string      Directory to place temporary files
        -s string, --search string    Dicom series search string

        Volume processing options:

        -t string, --type string      CT Tissue type [skin, bone, soft_tissue, fat]
        -a, --anisotropic             Apply anisotropic smoothing to the volume
        -i num, --isovalue num        Iso-surface value
        -d string, --double string    Double threshold with 4 values in a string seperated by semicolons

        Mesh options:

        --rotaxis int       Rotation axis (default=1, Y-axis)")
        --rotangle float    Rotation angle (default=180 degrees)")
        --smooth int        Smoothing iterations (default=25)")
        --reduce float      Polygon reduction factor (default=.9)

        Enable/Disable various filtering options")
    
        --disable string    Disable an option [anisotropic, shrink, median, largest, rotation]")
        --enable  string    Enable an option [anisotropic, shrink, median, largest, rotation]")
    """)

# Parse the command line arguments
#

try:
    opts, args = getopt.getopt(sys.argv[1:], "vDhacli:s:t:d:o:m:T:",
                               ["verbose", "help", "debug", "anisotropic", "clean", "ct", "isovalue=", "search=", "type=",
                                "double=", "disable=", "enable=", "largest", "metadata", "rotaxis=", "rotangle=", "smooth=",

                                "reduce=", "temp="])
except getopt.GetoptError as err:
    print(str(err))
    usage()
    sys.exit(2)


for o, a in opts:
    if o in ("-v", "--verbose"):
        verbose = verbose + 1
    elif o in ("-D", "--debug"):
        print("Debug")
        debug = debug + 1
        cleanFlag = False
    elif o in ("-h", "--help"):
        usage()
        sys.exit()
    elif o in ("-c", "--clean"):
        cleanUp = True
    elif o in ("-T", "--temp"):
        tempDir = a
    elif o in ("-a", "--anisotropic"):
        anisotropicSmoothing = True
    elif o in ("-i", "--isovalue"):
        isovalue = float(a)
    elif o in ("--ct"):
        CTonly = True
    elif o in ("-l", "--largest"):
        connectivityFilter = True
    elif o in ("-s", "--search"):
        dicomString = a
    elif o in ("-t", "--type"):
        tissueType = a
        doubleThreshold = True
    elif o in ("-o", "--output"):
        outname = a
    elif o in ("-m", "--metadata"):
        metadataFile = a
    elif o in ("-d", "--double"):
        vals = a.split(';')
        for v in vals:
            thresholds.append(float(v))
        thresholds.sort()
        doubleThreshold = True
    elif o in ("--rotaxis"):
        rotAxis = int(a)
    elif o in ("--rotangle"):
        rotAngle = float(a)
    elif o in ("--smooth"):
        smoothIterations = int(a)
    elif o in ("--reduce"):
        quad = float(a)
    elif o in ("--disable"):
        options.append("no"+a)
    elif o in ("--enable"):
        options.append(a)
    else:
        assert False, "unhandled options"

# Handle enable/disable options

for x in options:
    val = True
    y = x
    if x[:2] == "no":
        val = False
        y = x[2:]
    if y.startswith("shrink"):
        shrinkFlag = val
    if y.startswith("aniso"):
        anisotropicSmoothing = val
    if y.startswith("median"):
        medianFilter = val
    if y.startswith("large"):
        connectivityFilter = val
    if y.startswith("rotat"):
        rotFlag = val



# Process all subfolders of given input folder
parent_dir = args
dirs = os.listdir(parent_dir[0])
sub_dirs = [dir_ for dir_ in dirs if not dir_.startswith('.')]
counter = 0
errors = 0

# Setting up Logging

logs_dir = os.getcwd() + '/logs/'
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)
logfname = logs_dir + 'log_dicom2stl_' + str(start) + '.log'

# set up logging to file - see previous section for more details
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename=logfname,
                    filemode='w')
# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.INFO)
# set a format which is simpler for console use
formatter = logging.Formatter('%(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger().addHandler(console)

logging.info('')
logging.info('################################################')
logging.info('############ DICOM 2 STL CONVERSION ############')
logging.info('################################################')
logging.info('')
logging.info('CONVERTING ' + str(len(sub_dirs)) + ' SCANS')
logging.info('')

for sub_dir in sub_dirs:
    try:
        counter += 1
        logging.info(str('##### PROCESSING SCAN # : ' + str(counter)))
        logging.info('')

        begin_time = datetime.datetime.now()
        fname = [parent_dir[0] + '/' + sub_dir]
        outname_subdir = outname + sub_dir + '.stl'

        print("")
        if tempDir == "":
            tempDir = tempfile.mkdtemp()
        logging.info("Temp dir: " + tempDir)

        if tissueType:
            # Convert tissue type name to threshold values
            print("Tissue type: ", tissueType)
            if tissueType.find("bone") > -1:
                thresholds = [150., 800., 1500., 2000.]  #default values: [200., 800., 1300., 1500.]
            elif tissueType.find("skin") > -1:
                thresholds = [-200., 0., 500., 1500.]
            elif tissueType.find("soft") > -1:
                thresholds = [-15., 30., 58., 100.]
                medianFilter = True
            elif tissueType.find("fat") > -1:
                thresholds = [-122., -112., -96., -70.]
                medianFilter = True


        if doubleThreshold:
            # check that there are 4 threshold values.
            logging.info("Thresholds: " + str(thresholds))
            if len(thresholds) != 4:
                logging.error("Error: Threshold is not of size 4." + str(thresholds))
                sys.exit(3)
        else:
            logging.info("Isovalue = " + str(isovalue))


        if len(fname) == 0:
            logging.error("Error: no input given.")
            sys.exit(4)

        if zipfile.is_zipfile(fname[0]):
            zipFlag = True

        if os.path.isdir(fname[0]):
            dirFlag = True


        else:
            l = len(fname)
            if l > 1:
                logging.info("File names: ", fname[0], fname[1], "...", fname[l-1], "\n")
            else:
                logging.info("File names: ", fname, "\n")

        import SimpleITK as sitk

        if debug:
            print("SimpleITK version: ", sitk.Version.VersionString())
            print("SimpleITK: ", sitk, "\n")

        img = sitk.Image(100, 100, 100, sitk.sitkUInt8)
        dcmnames = []
        metasrc = img

        from utils import dicomutils

        #  Load our Dicom data
        #
        if zipFlag:
            # Case for a zip file of images
            if verbose:
                print("zip")
            img, modality = dicomutils.loadZipDicom(fname[0], tempDir)


        else:
            if dirFlag:
                if verbose:
                    logging.info("directory")
                    logging.info(fname[0])
                img, modality = dicomutils.loadLargestSeries(fname[0])

            else:
                # Case for a single volume image
                if len(fname) == 1:
                    if verbose:
                        print("Reading volume: ", fname[0])
                    img = sitk.ReadImage(fname[0])
                    modality = dicomutils.getModality(img)

                else:
                    # Case for a series of image files
                    if verbose:
                        if verbose > 1:
                            print("Reading images: ", fname)
                        else:
                            l = len(fname)
                            print("Reading images: ",
                                fname[0], fname[1], "...", fname[l-1])
                    isr = sitk.ImageSeriesReader()
                    isr.SetFileNames(fname)
                    img = isr.Execute()
                    firstslice = sitk.ReadImage(fname[0])
                    modality = dicomutils.getModality(firstslice)

        if CTonly and ((sitk.Version.MinorVersion() > 8) or (sitk.Version.MajorVersion() > 0)):
            # Check the metadata for CT image type.  Note that this only works with
            # SimpleITK version 0.8.0 or later.  For earlier versions there is no GetMetaDataKeys method

            if modality.find("CT") == -1:
                logging.error("Imaging modality is not CT.  Exiting.")
                sys.exit(1)


        #vtkname =  tempDir+"/vol0.vtk"
        #sitk.WriteImage( img, vtkname )

        def roundThousand(x):
            y = int(1000.0*x+0.5)
            return str(float(y) * .001)


        def elapsedTime(start_time):
            dt = roundThousand(time.clock()-start_time)
            print("    ", dt, "seconds")


        # Write out the metadata text file
        #
        if len(metadataFile):
            FP = open(metadataFile, "w")
            size = img.GetSize()
            spacing = img.GetSpacing()
            FP.write('xdimension ' + str(size[0]) + '\n')
            FP.write('ydimension ' + str(size[1]) + '\n')
            FP.write('zdimension ' + str(size[2]) + '\n')
            FP.write('xspacing ' + roundThousand(spacing[0]) + '\n')
            FP.write('yspacing ' + roundThousand(spacing[1]) + '\n')
            FP.write('zspacing ' + roundThousand(spacing[2]) + '\n')
            FP.close()


        #
        # shrink the volume to 256 cubed
        if shrinkFlag:
            sfactor = []
            size = img.GetSize()
            sum = 0
            for s in size:
                x = int(math.ceil(s/256.0))
                sfactor.append(x)
                sum = sum + x

            if sum > 3:
                # if sum==3, no shrink happens
                t = time.clock()
                print("Shrink factors: ", sfactor)
                img = sitk.Shrink(img, sfactor)
                newsize = img.GetSize()
                print(size, "->", newsize)
                elapsedTime(t)

        gc.collect()


        # Apply anisotropic smoothing to the volume image.  That's a smoothing filter
        # that preserves edges.
        #
        if anisotropicSmoothing:
            print("Anisotropic Smoothing")
            t = time.clock()
            pixelType = img.GetPixelID()
            img = sitk.Cast(img, sitk.sitkFloat32)
            img = sitk.CurvatureAnisotropicDiffusion(img, .03)
            img = sitk.Cast(img, pixelType)
            elapsedTime(t)
            gc.collect()

        # Apply the double threshold filter to the volume
        #
        if doubleThreshold:
            print("Double Threshold")
            t = time.clock()
            img = sitk.DoubleThreshold(
                img, thresholds[0], thresholds[1], thresholds[2], thresholds[3], 255, 0)
            isovalue = 64.0
            elapsedTime(t)
            gc.collect()

        # Apply a 3x3x1 median filter.  I only use 1 in the Z direction so it's not so slow.
        #
        if medianFilter:
            print("Median filter")
            t = time.clock()
            img = sitk.Median(img, [3, 3, 1])
            elapsedTime(t)
            gc.collect()

        # Pad black to the boundaries of the image
        #
        pad = [5, 5, 5]
        img = sitk.ConstantPad(img, pad, pad)
        gc.collect()

        if verbose:
            logging.info("Image for isocontouring")
            logging.info(str(img.GetSize()))
            logging.info(str(img.GetPixelIDTypeAsString()))
            logging.info(str(img.GetSpacing()))
            logging.info(str(img.GetOrigin()))
            if verbose > 1:
                print(img)
            print("")

        #vtkname =  tempDir+"/vol.vtk"
        #sitk.WriteImage( img, vtkname )

        import platform
        from utils import sitk2vtk
        import vtk
        vtkimg = None

        if platform.system() == "Windows":
            # hacky work-around to avoid a crash on Windows
            vtkimg = vtk.vtkImageData()
            vtkimg.SetDimensions(10, 10, 10)
            vtkimg.AllocateScalars(vtk.VTK_CHAR, 1)
            sitk2vtk.sitk2vtk(img, vtkimg, False)
        else:
            vtkimg = sitk2vtk.sitk2vtk(img)

        img = None
        gc.collect()

        import traceback
        import vtk

        if debug:
            print("\nVTK version: ", vtk.vtkVersion.GetVTKVersion())
            print("VTK: ", vtk, "\n")


        from utils import vtkutils

        if debug:
            print("Extracting surface")
        mesh = vtkutils.extractSurface(vtkimg, isovalue)
        vtkimg = None
        gc.collect()
        if debug:
            print("Cleaning mesh")
        mesh2 = vtkutils.cleanMesh(mesh, connectivityFilter)
        mesh = None
        gc.collect()
        if debug:
            print("Smoothing mesh", smoothIterations, "iterations")
        mesh3 = vtkutils.smoothMesh(mesh2, smoothIterations)
        mesh2 = None
        gc.collect()
        if debug:
            print("Simplifying mesh")
        mesh4 = vtkutils.reduceMesh(mesh3, quad)
        mesh3 = None
        gc.collect()

        if rotFlag:
            mesh5 = vtkutils.rotateMesh(mesh4, rotAxis, rotAngle)
        else:
            mesh5 = mesh4
        vtkutils.writeMesh(mesh5, outname_subdir)
        mesh4 = None
        gc.collect()


        # remove the temp directory
        import shutil
        if cleanUp:
            shutil.rmtree(tempDir)
            tempDir = ""

        logging.info("")
        logging.info('#####')
        logging.info('STL FILE SAVED: ' + outname_subdir)
        logging.info('Execution Time: ' + str(datetime.datetime.now() - begin_time))
        logging.info(str("Progress %:  {0:.0%}".format(counter/len(sub_dirs))))
        logging.info('#####')
        logging.info("")
        print("")

    except Exception as e:
        errors += 1
        #logf = open(logfname, 'a')
        logging.error(str("Error procesing file {0}: {1}\n\n".format(fname[0], str(e))))
        #logf.close()
        continue

logging.info('################################################')
logging.info('BATCH PROCESSING COMPLETED')
logging.info(str(counter - errors) + ' SCANS PROCESSED')
logging.info(str(errors) + ' ERRORS FOUND' )
logging.info('TOTAL EXECUTION TIME: ' + str(datetime.datetime.now() - start))
logging.info('################################################')