#!/usr/bin/python

"""
Script to remove unwanted objects from CT Scans input STL's and only 
extract skull object, as a new STL file.

Usage:
    - skull_extraction.py -i <input_folder> -o <output_folder>
    
Juan Fernando Pinzon 
Novel Software Systems
Novosibirsk, Russia
06.2020
"""

import os, sys, getopt, time, datetime
import trimesh
import numpy as np

start = datetime.datetime.now()

def skull_extraction(fname, stl_file, outputfolder):
    mesh = trimesh.load_mesh(fname)
    splitted_mesh = mesh.split(only_watertight=False)
    skull_position = np.argmax([x.faces.shape[0] for x in splitted_mesh])
    skull = mesh.split(only_watertight=False)[skull_position]
    outname = outputfolder + '/' + stl_file

    return skull.export(outname)

def main(argv):
    inputfolder = ''
    outputfolder = ''
    try:
        opts, args = getopt.getopt(argv,"hi:o:",["ifolder=","ofolder="])
    except getopt.GetoptError:
        print('USAGE: stl_post-processing.py -i <inputfolder> -o <outputfolder>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('USAGE: stl_post-processing.py -i <inputfolder> -o <outputfolder>')
            sys.exit()
        elif opt in ("-i", "--ifolder"):
            inputfolder = arg
        elif opt in ("-o", "--ofolder"):
            outputfolder = arg
    #print('Input folder is "', inputfolder)
    print('Output folder is "', outputfolder)

    if not os.path.exists(outputfolder):
        os.makedirs(outputfolder)

    parent_folder = os.listdir(inputfolder)
    files = [dir_ for dir_ in parent_folder if not dir_.startswith('.')]
    counter = 0
    errors = 0
    logfname = 'log_' + str(start) + '.txt'

    print('')
    print('################################################')
    print('############## STL POST-PROCESSING #############')
    print('################ SKULL EXTRACTION ##############')
    print('################################################')
    print('')
    print('CONVERTING ', len(files), 'STL FILES')
    print('')

    for stl_file in files:
        try:
            counter += 1
            print('##### PROCESSING STL # : ', counter)
            print('')

            begin_time = datetime.datetime.now()
            fname = inputfolder + stl_file
            print(fname)

            skull_extraction(fname, stl_file, outputfolder)

            print("")
            print('#####')
            print('STL FILE SAVED')
            print('Execution Time: ', datetime.datetime.now() - begin_time)
            print("Progress %: ", "{0:.0%}".format(counter/len(files)))
            print('#####')
            print("")
            print("")

        except Exception as e:
            errors += 1
            logf = open(logfname, 'a')
            logf.write("Error procesing file {0}: {1}\n\n".format(fname, str(e)))
            logf.close()
            continue

    print('################################################')
    print('BATCH PROCESSING COMPLETED')
    print((counter - errors), ' SCANS PROCESSED')
    print('TOTAL EXECUTION TIME: ', datetime.datetime.now() - start)
    print('################################################')

if __name__ == "__main__":
   main(sys.argv[1:])

