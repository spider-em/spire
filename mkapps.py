
# Find the Python executable for Spire, in spire_linux-1.5.3/bin/python.
# Create scripts for the *.py programs in the spire bin directory.
# Move the *.py programs into the scripts directory.
#
# Usage: mkapps.py BIN_DIR_FOR_EXECS TARGET_DIR_FOR_PY_PROGS

import os, sys
import shutil  #### from shutil import copy

apps = ['scatter.py', 'pyplot.py', 'ctfdemo.py', 'xplor.py', 'montagefromdoc.py',
        'ctfgroup.py', 'ctfcircle.py', 'ctfmatch.py', 'classavg.py', 'montage.py',
        'qview.py', 'verifybyview.py', 'backup.py', 'emancoords2spiderdoc.py', 'emanrctcoords2spiderdoc.py' ,
        'mkfilenums.py', 'spiconvert.py', 'binarytree.py', 'viewstack.py',
        'xmippsel2spiderdoc.py', 'circlestack.py', 'spire.py']

_TARGETDIR = 'scripts'
bindir = "bin"

# Find the Python executable for SPIRE

numargs = len(sys.argv[1:])

if numargs == 0:
    d = os.getcwd()    # this script is either in SPIREHOME or SPIREHOME/scripts
    path,basename = os.path.split(d)
    if basename.find("spire") > -1:
        ###print(f"'spire' in basename '{basename}'")
        spiredir = os.path.abspath( os.path.join(path, basename) )
        targetdir = os.path.join(path, spiredir, _TARGETDIR)
    else:
        old_base= basename
        path, basename = os.path.split(path)
        if basename.find("spire") > -1:
            ###print(f"'spire' not in '{old_base}' but in basename '{basename}'")
            spiredir = os.path.abspath( os.path.join(path, basename) )
            targetdir = os.path.join(spiredir, _TARGETDIR)
        else:
            print("Usage: mkapps.py spire_dir")
            sys.exit(1)
    Pythonprog = os.path.join(spiredir, bindir, "use-python3")

elif numargs  == 1:   # 1st arg is the bin directory
    bindir     = sys.argv[1]
    spiredir,basename = os.path.abspath( os.path.split(bindir) )
    targetdir  = os.path.abspath( os.path.join(spiredir,_TARGETDIR) )
    Pythonprog = os.path.abspath( os.path.join(bindir, "use-python3") )

else:   # 2nd arg is the target directory
    bindir     = sys.argv[1]
    spiredir,basename = os.path.abspath( os.path.split(bindir) )
    targetdir  = sys.argv[2]
    Pythonprog = os.path.abspath( os.path.join(bindir, "use-python3") )
            
##print("spiredir :",spiredir)
##exit()

if not os.path.exists(Pythonprog):
    print("Unable to find executable python in %s" % Pythonprog)
    sys.exit(1)
    
# TODO: Check libraries

bindir = os.path.abspath(bindir)
os.chdir(bindir)
if not os.path.exists(targetdir):
    os.makedirs(targetdir)
    print(f"\nCreated directory '{targetdir}'\n")
else:
    # Make sure it's a directory
    if not os.path.isdir(targetdir):
        print()
        print(f"ERROR!! Target destination '{targetdir}' is not a directory!")
        print( "  Fix and resume.")
        print( "  Exiting...\n")
        exit()

for app in apps:
    appscript, ext = os.path.splitext(app)
    if ext != ".py" or not os.path.exists(app):
        continue
    app_path = os.path.join(bindir,app)
    txt = "#!/bin/sh\n\n"
    txt += 'exec "%s" "%s" "$@"' % (Pythonprog, app_path)
    print("Creating %s script" % appscript)

    try:
        fp = open(appscript, 'w')
        fp.write(txt)
        fp.close()
        os.chmod(appscript, 0o775)
        try:
            shutil.copy(app,targetdir)
        except NotADirectoryError as nade:
            print("\nNotADirectoryError:", NotADirectoryError)
            print("  app :",app)
            print("  targetdir :",targetdir)
            exit()
        #print("  Copying %s to %s/" % (app, targetdir))
        #if os.path.exists(os.path.join(targetdir,app)):
            #os.remove(app)
    except:
        print("  Unable to create %s script" % appscript)


    
