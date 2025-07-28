#!/usr/bin/env python

import   os, sys, argparse
if int(sys.version[0]) == 2:
  from   Tkinter import Toplevel, Tk
elif int(sys.version[0]) == 3:
  from   tkinter import Toplevel, Tk

root = Tk()  # There are problems if this is not in the __main__ module

import Spire.GB as GB
import Spire.GG as GG
import Spire.spiderMain as spiderMain


USAGE = """
  %s <options> <project_file>

For explanation of options, enter:
  %s -h
or
  %s --help

""" % ( (os.path.basename(__file__),)*3 )
MODIFIED="Modified 2025 Jul 28"

def parse_command_line():
    """
    Parse the command line.  Adapted from classavg.py

    Arguments:
        None

    Returns:
        Parsed arguments object
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        usage=USAGE,
        epilog=MODIFIED
    )

    parser.add_argument(
        "--new", '-n',
        action="store_true",
        help='Flag to use small fonts (not implemented)')

    parser.add_argument(
        "--small", '-s',
        action="store_true",
        help='Flag to use small fonts (not yet implemented)')

    # Return unrecognized parameters too, might be filenames
    return parser.parse_known_args()

######################################################################

if __name__ == "__main__":

    args, project = parse_command_line()
    #print(args)
    #print('project',project)
    #exit()

    # Make sure files are actually files and not unrecognized arguments
    nonfiles = []
    for fn in project:
        if not os.path.exists(fn) : nonfiles.append(fn)

    if len(nonfiles) > 0:
        print()
        print( "ERROR!! The following are either unrecognized flags or non-existent files:")
        print( " ", " ".join(nonfiles) )
        print()
        print( "  Exiting...\n")
        exit()

    GG.topwindow = Toplevel(root)

    root.withdraw()

    #args    = sys.argv[1:]
    #project = 0
    #new = False
    #small   = 0    # Small font (not yet implemented)
    #if len(args) > 0:
        #if '-n' in args or '--new' in args:
            #new = True
            #i     = args.index('-s')
            #del args[i]
        #if '-s' in args:
            #small = 1
            #i     = args.index('-s')
            #del args[i]
        #if len(args) > 0: project = args[0]

    # Create instance of GUI
    GG.spidui = spiderMain.SpiderGUI(GG.topwindow, project, usesmallfont=args.small)

    if args.new:
        GG.spidui.newProject()
    elif len(project) > 0:
        GG.spidui.openProject(project[0])
        ###GG.spidui.readUserPrefs()

    root.mainloop()
