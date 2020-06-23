dicom2stl
=========

[![CircleCI](https://circleci.com/gh/dave3d/dicom2stl.svg?style=svg)](https://circleci.com/gh/dave3d/dicom2stl)

dicom2stl.py is a script that takes a [Dicom](https://www.dicomstandard.org/about/)
series and generates a STL surface mesh.

Written by David T. Chen from the National Institute of Allergy & Infectious Diseases (NIAID), 
dchen@mail.nih.gov It is covered by the Apache License, Version 2.0:
> http://www.apache.org/licenses/LICENSE-2.0

Required packages
=================
The script is written in Python and uses 2 external packages, [VTK](https://vtk.org) and [SimpleITK](https://simpleitk.readthedocs.io/en/master/).

vtk can be downloaded and built from the following repository:
> https://github.com/Kitware/VTK

Alternatively, on some Linux distributions it can be installed with the following command:
> sudo apt-get install vtk

SimpleITK can be installed via the following command:
> pip SimpleITK

The options for the script can be seen by running it:
> python dicom2stl.py --help

Trimesh (for STL Post-processing (Skull extraction)):
> pip trimesh


How it works
============
First the script reads in a series of 2-d images or a simple 3-d image.  It can read
any format supported by ITK.  If the input name is a zip file or a directory name,
the script expects a single series of DCM images, all with the ".dcm" suffix.

Note: if you run this script with the individual Dicom slices provided on the
command line, they might not be ordered in the correct order.  You are better
off providing a zip file or a directory.  Dicom slices are not necessarily
ordered the same alphabetically as they are physically.  In the case of a zip file
or directory, the script loads using the
[SimpleITK ImageSeriesReader](https://simpleitk.readthedocs.io/en/master/Examples/DicomSeriesReader/Documentation.html)
class, which orders the slices by their physical layout, not their alphabetical names.

The primary image processing pipeline is as follows:
* [Shrink](https://itk.org/SimpleITKDoxygen/html/classitk_1_1simple_1_1ShrinkImageFilter.html) the volume to 256 max dim (enabled by default)
* [Anisotropic smoothing](https://itk.org/SimpleITKDoxygen/html/classitk_1_1simple_1_1CurvatureAnisotropicDiffusionImageFilter.html) (disabled by default)
* [Double threshold filter](https://itk.org/SimpleITKDoxygen/html/classitk_1_1simple_1_1DoubleThresholdImageFilter.html) (enabled when tissue types are used)
* [Median filter](https://itk.org/SimpleITKDoxygen/html/classitk_1_1simple_1_1MedianImageFilter.html) (enabled for 'soft' and 'fat' tissue types)
* [Pad](https://itk.org/SimpleITKDoxygen/html/classitk_1_1simple_1_1ConstantPadImageFilter.html) the volume

The script has built in double threshold values for the 4 different tissue types (bone, skin, muscle, soft).
These values assume the input is DICOM with standard CT Hounsfield units.  I determined these values experimentally
on a few DICOM test sets I had, so how well they work for others is in question.

The volume is shrunk to 256 cubed or less for speed and polygon count reasons.

After all the image processing is finished, the volume is converted to a VTK image using sitk2vtk.py.

Then the following VTK pipeline is executed:
* [Extract a surface mesh](https://vtk.org/doc/nightly/html/classvtkContourFilter.html) from the VTK image
* Apply the [clean mesh filter](https://vtk.org/doc/nightly/html/classvtkCleanPolyData.html)
* Apply the [smooth mesh filter](https://vtk.org/doc/nightly/html/classvtkSmoothPolyDataFilter.html)
* Apply the [reduce mesh filter](https://vtk.org/doc/nightly/html/classvtkQuadricDecimation.html)
* [Write out an STL file](https://vtk.org/doc/nightly/html/classvtkSTLWriter.html)

The amount of smoothing and mesh reduction can be adjusted via command line options.  By default
25 iterations of smoothing is applied and the number of vertices is reduced by 90%.


Examples
========

To extract the bone from a zip of dicom images:
> python dicom2stl.py -t bone -o bone.stl dicom.zip

To extract the skin from a NRRD volume:
> python dicom2stl.py -t skin -o skin.stl volume.nrrd

To extract a specific iso-value from a VTK volume:
> python dicom2stl.py -i 128 -o iso.stl volume.vtk

To extract soft tissue from a dicom series in directory and
apply a 180 degree Y axis rotation:
> python dicom2stl.py --enable rotation -t soft_tissue -o soft.stl dicom_dir


Modifications for NOVEL Software Systems - SkullNet Project:
========

Modifications:
* Baked-in best parameters for processing Skulls CT Scans for SkullNet project:
    * Isocountering (Isovalue) = 150
    * Smooth Iterations = 5,0000
    * Reduction factor (quad) = 0.75 
* Added folder/subfolder batch processing loop
* Added Error handling and logging.

Usage:
> python dicom2stl_tuned.py -o output_folder input_parent_folder


STL POST-PROCESSING:
========

Script to remove unwanted objects from CT Scans input STL's and only 
extract skull object, as a new STL file.

Usage:
> python skull_extraction.py -i <input_folder> -o <output_folder>

PIPELINE DICOM 2 SKULL:
========

Pipeline script that executes both dicom2stl_tuned.py and skull_extraction.py scripts.

Usage:
> python dicom2skull.py -i <input_dicom_parent_folder> -o <output_folder> -n <no_clean (to keep intermediate stage STL files (optional))>