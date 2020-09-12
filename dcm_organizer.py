#!/usr/bin/python

# DCM organizer script:
#   - To organize directory full of DCM files into a subdirectories based on SeriesInstanceUID 
#     to be able to execute the dicom2stl script.
# Author: Juan F. Pinzon, Academgene LLC
# 09.2020

import os, shutil, sys, getopt, json, datetime, logging
import pydicom
from tqdm import tqdm


def organizer(SRC, OUT, MODALITY, BODYPART, LOG_FNAME, processed_dcms):

    totalFiles = 0
    counter = 0
    error_count = 0
    UID_count = 0
    
    input_dcms = os.listdir(SRC)
    totalFiles = len(input_dcms)

    #excluding already processed files
    input_dcms = [x for x in input_dcms if x not in processed_dcms]

    for i, dcm in tqdm(enumerate(input_dcms), total=len(input_dcms)):
        try:
            ds = pydicom.dcmread(SRC + input_dcms[i])
            if ds.Modality == MODALITY and ds.BodyPartExamined == BODYPART:
                out_dir = OUT + ds.SeriesInstanceUID
                src_path = SRC + dcm
                out_path = out_dir + '/' + dcm
                if not os.path.exists(out_dir):
                    os.makedirs(out_dir)
                    UID_count += 1
                shutil.move(src_path, out_path)
                counter += 1
                #if ds.SeriesInstanceUID not in seriesUID: 
                #    seriesUID.append(ds.SeriesInstanceUID)  
        except Exception as e:
            #print('Error processing file: ', dcm, str(e), '\n')
            error_count += 1
            continue
    
    return input_dcms, counter, error_count, totalFiles, UID_count

def main(argv):

    start = datetime.datetime.now()

    LOG_FNAME = os.getcwd() + '/logs/organized_dcms.log'
    #seriesUID = []
    SUBDIRS = False
    BODYPART = 'HEAD'
    MODALITY = 'CT'

    # Setting up Logging

    logs_dir = os.getcwd() + '/logs/'
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    run_log_name = logs_dir + 'log_dcm-organizer_' + str(start) + '.log'

    # set up logging to file - see previous section for more details
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%d-%m-%y %H:%M',
                        filename=run_log_name,
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

    #loading the log file in order to exclude already processed series
    try:
        with open(LOG_FNAME, 'r') as infile:
            processed_dcms = set(json.load(infile))
    except:
        processed_dcms = set()
    #print(processed_dcms)

    try:
        opts, args = getopt.getopt(argv,"hi:o:s:b:m:",["ifolder=","ofolder=","subdirs","bodypart=", "modality="])
    except getopt.GetoptError:
        print('USAGE: dcm_organizer.py -i <input_dicom_folder> -o <output_folder> -s <files are in subdirs> -b <BodyPart> -m <Modality>')
        sys.exit()
        exit()

    for opt, arg in opts:
        if opt == '-h':
            print('USAGE: dcm_organizer.py -i <input_dicom_folder> -o <output_folder> -s <files are in subdirs> -b <BodyPart> -m <Modality>')
            sys.exit()
        elif opt in ("-i", "--ifolder"):
            SRC = arg
        elif opt in ("-o", "--ofolder"):
            OUT = arg
        elif opt in ("-s", "--subdirs"):
            SUBDIRS = True
        elif opt in ("-b", "--bodypart"):
            BODYPART = str(arg)
        elif opt in ("-m", "--modality"):
            MODALITY = str(arg)

    #print(BODYPART, MODALITY)

    # call organizer function:
    if SUBDIRS:
        counter, error_count, totalFiles, UID_count = 0, 0, 0, 0
        sub_dirs = os.listdir(SRC)
        for sub_dir in tqdm(sub_dirs, total=len(sub_dirs)):
            logging.info('Procesing Directory: ' + sub_dir)
            #seriesUID = []
            SRC_subdir = SRC + sub_dir + '/'
            input_dcms_subdir, counter_subdir, error_count_subdir, totalFiles_subdir, UID_count_subdir = organizer(SRC_subdir, \
                OUT, MODALITY, BODYPART, LOG_FNAME, processed_dcms)
            # updating and writing the log
            processed_dcms.update(input_dcms_subdir)
            with open(LOG_FNAME, 'w') as infile:
                json.dump(list(processed_dcms), infile)
            #seriesUID.append(seriesUID_subdir)
            counter += counter_subdir
            error_count += error_count_subdir
            totalFiles += totalFiles_subdir
            UID_count += UID_count_subdir
    else:
        input_dcms, counter, error_count, totalFiles, UID_count = organizer(SRC, OUT, MODALITY, BODYPART, LOG_FNAME, processed_dcms)
        processed_dcms.update(input_dcms)
        with open(LOG_FNAME, 'w') as infile:
            json.dump(list(processed_dcms), infile)

    # updating and writing the log
    #processed_dcms.update(input_dcms)
        
    logging.info('')
    logging.info(str(totalFiles) + ' files scanned')
    logging.info(str(counter) + ' files organized')
    logging.info('Into ' + str(UID_count) + ' unique Series sub-directories')
    try:
        logging.info('# of Errors found: ' + str(error_count) + str(' - {0:.0%}'.format(error_count/totalFiles)))
    except ZeroDivisionError:
        logging.info('0 Errors found')
    logging.info('Execution Time: ' + str(datetime.datetime.now() - start))

if __name__ == "__main__":
    main(sys.argv[1:])