import argparse
import os
import sys
import regex as re

from utility import bcolors
from check import Inspector

rows, columns = os.popen('stty size', 'r').read().split() # Useful for text formatting

__FILENAME__ = "Dockerfile"

# Argparse

parser = argparse.ArgumentParser(description='Dockerfile inspector')
parser.add_argument("p", nargs="?",default="./", help="Path of the subfolder containing the Dockerfile (default is ./)")
parser.add_argument("-v", "--verbose", help="Verbose mode",action="store_true")
args = parser.parse_args()

# Looking for Dockerfile

context = os.walk(args.p, topdown=True)
exclude = set([".git","__pycache__"])
for root, dirs, files in context:
    dirs[:] = [d for d in dirs if d not in exclude]
    if __FILENAME__ in files:
        dpath = root
        if(dpath[len(dpath)-1]) != "/":
            dpath += "/"
        break # Using the first one found

if dpath:
    if args.verbose:
        print("\nDebug info:")
        print("Dockerfile path: " + dpath)
else:
    raise SystemExit('Could not find any Dockerfile')

# Dockerfile context analysis (scraping)

context = os.walk(dpath, topdown=True)
dirscontext, filecontext = ([] for i in range(2))
exclude = set([]) #TODO: Needs .dockerignore support, feasible?
for root, dirs, files in context:
    dirs[:] = [d for d in dirs if d not in exclude]
    dirscontext.extend(dirs)
    if(root == dpath):
        filecontext.extend(x for x in files)
    else:
        filecontext.extend(root[len(dpath):] + "/"+ x for x in files)
        
if args.verbose:
    print("\nDirectories: " + str(len(dirscontext)))
    for dir in dirscontext:
        print("\t"+dir)

    print("\nFiles: " + str(len(filecontext)))
    for file in filecontext:
        print("\t"+file)

# Dockerfile loading, cleaning
with open(dpath+"/"+__FILENAME__) as f:
    content = f.readlines()

dockerfile = []
for line in content:
    newline = line.strip()
    if(len(newline) > 0):
        if(newline[0] != "#"):
            newline = line
            # Removing the \n
            dockerfile.append(newline[:-1])
if len(content) == 0:
    raise SystemExit("This Dockerfile looks empty, make sure you specified the appropriate subfolder")

if args.verbose and len(dockerfile) > 0:
    print("\nInstructions --> layers: "+ str(len(dockerfile)))
    for line in dockerfile:
        print("\t"+line)

# Dictionary based on instructions

dockerdict = {}
for idx, inst in enumerate(dockerfile):
    key = inst.split(" ")[0]
    dockerdict.setdefault(key,[]).append((idx+1, inst))

# Context & Docker intersection analysis (could be useful later on)

fileocc = []
dirsocc = []
for line in dockerfile:
    #TODO: Weak logic, needs improvement
    for file in filecontext:
        if file in line:
            fileocc.append((file,line))
    for dir in dirscontext:
        # Regex makes sure that files are not recognized as dirs (prefix)
        if re.match( r'.*'+re.escape(dir)+r'(?!\/).*', line):
            dirsocc.append((dir,line))

if args.verbose:
    if(len(fileocc) > 0) or (len(dirsocc) > 0):
        print("\nLayers that interact with context:")

    if(len(fileocc) > 0):
        print("\tFile usage: ")
        for file, line in fileocc:
            print("\t\t"+line.replace(file,bcolors.HEADER+file+bcolors.ENDC))        

    if(len(dirsocc) > 0):
        print("\tDirectory usage: ")
        for dir, line in dirsocc:
            print("\t\t"+line.replace(dir,bcolors.HEADER+dir+bcolors.ENDC))

if args.verbose:
    print()
    print("-" * int(columns))
    print("\tLooking for possibile Dockerfile improvements for reproducibility")
    print("-" * int(columns))

print()    

inspector = Inspector(dockerdict)

inspector.undefinedImageVersions()
inspector.remoteFetches()
inspector.pipes()
# ... 

print()


