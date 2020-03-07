#!/usr/bin/env python3
#
# Loads provinces from the specified file.
# See https://download.geonames.org/export/dump/admin1CodesASCII.txt
#
# Copyright (c) 2020 Carlos Torchia
#
import os
import sys
_dir_path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'src')
sys.path.append(_dir_path)

import geonames
import climatedb

def get_args(arguments):
    '''
    Determines command line arguments
    '''
    num_arguments = len(arguments)
    if num_arguments != 2:
        print('Usage: ' + arguments[0] + ' <filename>\n', file=sys.stderr)
        sys.exit(1)

    filename = arguments[1]

    return filename

def main(args):
    '''
    The main function
    '''
    filename = get_args(args)

    climatedb.connect()

    geonames.load_provinces(filename)

    climatedb.close()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
