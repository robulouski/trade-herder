#import sys
import logging
from eto import VERSION_STRING, APPLICATION_NAME


logger = logging.getLogger()


def init_logging(level=None, filename=None):
    if not level:
        level = logging.INFO
    formatter = logging.Formatter('%(levelname)s:\t%(message)s\t[%(name)s]')
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)
    if filename:
        logfile = logging.FileHandler('gencfdprocess.log')
        logfile.setLevel(logging.DEBUG)
        logfile.setFormatter(formatter)
        logger.addHandler(logfile)
    
    if level:
        logger.setLevel(level)
        logger.info("Starting %s v%s: setting log level to %d", 
                    APPLICATION_NAME, VERSION_STRING, level)
    else:
        logger.info("Starting " + APPLICATION_NAME + " " + VERSION_STRING)
