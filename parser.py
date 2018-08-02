import argparse
import os
import sys
import regex as re
import fnmatch

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

dockerignore = dpath+".dockerignore"
filterFiles = False
if os.path.isfile(dockerignore):
    if args.verbose:
        print(".dockerignore detected")
    with open(dpath+"/.dockerignore") as f:
        ignore_list = f.readlines()
    filterFiles = True

context = os.walk(dpath, topdown=True)
dirscontext, filecontext = ([] for i in range(2))
for root, dirs, files in context:
    dirscontext.extend(dirs)
    for f in files:
        if f == ".dockerignore" or f == "Dockerfile":
            continue
        ignorethisfile = False
        if filterFiles:
            for pattern in ignore_list:
                if fnmatch.fnmatch(f, pattern):
                    ignorethisfile = True
                    break
        if not ignorethisfile:
            if(root == dpath):
                filecontext.append(f)
            else:
                filecontext.append(root[len(dpath):] + "/"+ f)

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

dockerfile, multiline = ([] for i in range(2))
instructionList = []
for line in content:
    line = line.strip()
    if(len(line) > 0):
        # If it isn't a comment
        if line[0] != "#":
            if line[len(line)-1] == "\\":
                multiline.append(line.split("\\", 1)[0])
            elif len(multiline) > 0:
                multiline.append(line)
                multistring = "".join(multiline)
                dockerfile.append(multistring)
                instructionList.append(multistring)
                multiline = []
            else:
                dockerfile.append(line)
                instructionList.append(line)

if len(content) == 0:
    raise SystemExit("This Dockerfile looks empty, make sure you specified the appropriate subfolder")

# Dictionary based on instructions

layers = 0
dockerdict = {}
for idx, inst in enumerate(dockerfile):
    key = inst.split(" ")[0]
    dockerdict.setdefault(key,[]).append((idx+1, inst))
    if key in ["RUN","COPY","ADD"]:
        layers += 1

if args.verbose and len(dockerfile) > 0:
    print("\nInstructions: "+ str(len(dockerfile))+" --> layers: " + str(layers))
    for inst in dockerfile:
        print("\t"+inst)

# Context & Docker intersection analysis (could be useful later on)

fileocc = []
dirsocc = []
for inst in dockerfile:
    #TODO: Weak logic, needs improvement
    for file in filecontext:
        if file in inst:
            fileocc.append((file,inst))
    for dir in dirscontext:
        # Regex makes sure that files are not recognized as dirs (prefix)
        if re.match( r'.*'+re.escape(dir)+r'(?!\/).*', inst):
            dirsocc.append((dir,inst))

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

inspector = Inspector(dockerdict,instructionList)

#inspector.undefinedImageVersions()
inspector.remoteFetches()
#inspector.aptget()
inspector.pipes()
#inspector.longRuns(100)
# ... 

print()


