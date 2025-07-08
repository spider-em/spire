#!/usr/bin/env python

# PURPOSE: Simple script to convert a single-column text file into a SPIDER doc file
#
# NOTE: Comment lines are not ignored

import os, sys
from   Spider import Spiderutils

if sys.argv[1:]:
    infile = sys.argv[1]
    outfile = sys.argv[2]

    F = {}  # initialize dictionary
    key = 0  # initialize key

    if os.path.exists(infile) :
        input = open(infile,'r')
        L = input.readlines()  # read line-by-line
        input.close()
    
        # read contents
        for line in L:
            filenum = Spiderutils.getfilenumber(line)
            key += 1
            F[key] = [filenum]
	
        headers = ['file_number']
        if Spiderutils.writeSpiderDocFile(outfile,F, headers=headers, append=0):
            print('Wrote', key, 'keys to %s' % os.path.basename(outfile))
        else:
            print("Error!", "Unable to write to %s" % os.path.basename(outfile))
    else:
        print("Error!", "Unable to read %s" % infile)
else:
    print("Syntax: makefilenums.py inputtextfile outputspiderdoc")
    
