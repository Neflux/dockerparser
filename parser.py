import os
import regex as re

import requests
from bs4 import BeautifulSoup
from urllib.request import urlopen
from lxml import etree

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

rows, columns = os.popen('stty size', 'r').read().split()

# Dir file analysis

context = os.walk("./")
dirscontext = []
filecontext = []
for root, dirs, files in context:
    dirscontext.extend(dirs)
    if(root == "./"):
        filecontext.extend(x for x in files)
    else:
        filecontext.extend(root[2:]+"/"+x for x in files)

print("Directories: " + str(len(dirscontext)))
for dir in dirscontext:
    print("\t"+dir)

print("Files: " + str(len(filecontext)))
for file in filecontext:
    print("\t"+file)

# Dockerfile loading and cleaning

__FILENAME__ = "Dockerfile"

with open(__FILENAME__) as f:
    content = f.readlines()

dockerfile = []
for line in content:
    newline = line.strip()
    if(len(newline) > 0):
        if(newline[0] != "#"):
            newline = line
            # Removing the \n
            dockerfile.append(newline[:-1])
print("Layers: "+ str(len(dockerfile)))

for line in dockerfile:
    print("\t"+line)

# Dictionary based on instructions

dockerdict = {}
for idx, inst in enumerate(dockerfile):
    key = inst.split(" ")[0]
    dockerdict.setdefault(key,[]).append((idx+1, inst))

# Context & Docker intersection analysis

print("Layers that use context:")
fileocc = []
dirsocc = []
for line in dockerfile:
    for file in filecontext:
        if file in line:
            fileocc.append((file,line))
    for dir in dirscontext:
        # Regex makes sure that files are not recognized as dirs
        if re.match( r'.*'+re.escape(dir)+r'(?!\/).*', line):
            dirsocc.append((dir,line))

if(len(fileocc) > 0):
    print("\tFile usage: ")
    for file, line in fileocc:
        print("\t\t"+line.replace(file,bcolors.HEADER+file+bcolors.ENDC))        

if(len(dirsocc) > 0):
    print("\tDirectory usage: ")
    for dir, line in dirsocc:
        print("\t\t"+line.replace(dir,bcolors.HEADER+dir+bcolors.ENDC))


print()
print("-" * int(columns))
print("Looking for possibile dockerfile reproducibility improvements")
print("-" * int(columns))
print()

# Check for unsafe RUN pipes

if "RUN" in dockerdict:
    for idx, inst in dockerdict["RUN"]:
        if "|" in inst and "set -o pipefail" not in inst:
            print("===> Unsafe pipe inside a RUN instruction detected at line "+str(idx)+"!\n")
            print("Explanation: if you want this command to fail due to an error at any stage in the pipe, prepend 'set -o pipefail &&' to ensure that an unexpected error prevents the build from inadvertently succeeding.\n")
            print("Original instruction: " + inst)
            print("Suggested edit: " + inst.replace("RUN", "RUN "+bcolors.HEADER+"set -o pipefail &&"+bcolors.ENDC) + "\n")

# Check for unhealthy ADDs that fetch a compressed file from a remote origin

def getSubsequentExtractionInstructions(file, path, index):
    result = []
    if "RUN" in dockerdict:
        for idx, inst in dockerdict["RUN"]:
            # Extraction instructions always come later than the download
            if idx > index and (file in inst or path in inst):
                result.append((idx, inst))
    return result

if "ADD" in dockerdict:
    for idx, inst in dockerdict["ADD"]:
        parsedADD = re.search(r'ADD\s(.*\/(.*)\.(?:tar|xz|zip|gz))\s(.*)', inst)
        if parsedADD:
            print("===> Unhealthy file download inside an ADD instruction detected at line "+str(idx)+"!\n")
            print("Explanation: because image size matters, using ADD to fetch packages from remote URLs is strongly discouraged; you should use curl or wget instead. That way you can delete the files you no longer need after they’ve been extracted and you don’t have to add another layer in your image.\n")
            url = parsedADD.group(1)
            filename = parsedADD.group(2)
            # Removing the last char, it could be and extra backslash
            path = parsedADD.group(3)[:-1]
            extralines = getSubsequentExtractionInstructions(filename,path,idx)
            
            print("Original instruction/s:\n\t" + inst)

            newSuggestedInstructions = []
            incompleteSuggestion = 0
            for x,y in extralines:
                # Print those extra lines
                print("\t"+y)
                if re.match( r'RUN tar -xJf (?:.+) -C (?:.+)$', y):
                    newSuggestedInstructions.append("tar -xJC "+ path)
                elif re.match( r'RUN make -C (?:.+) all$', y):
                    newSuggestedInstructions.append("make -C "+ path +" all")
                #elif ... appendable modular support
                else:
                    newSuggestedInstructions.append(" ... ")
                    incompleteSuggestion += 1

            if not extralines:
                print("\t???\nCould not find extraction directives")
                finalSuggestion = "RUN mkdir -p " + path + " \\\n\t&& curl -SL " + url + " \\\n\t*** your extraction instructions ***"
            else:
                finalSuggestion = "RUN mkdir -p " + path + " \\\n\t&& curl -SL " + url
                # Pipe the first extraction
                if len(newSuggestedInstructions) > 0:
                    finalSuggestion += " \\\n\t| "+newSuggestedInstructions[0]
                
                for newInstruction in newSuggestedInstructions[1:]:
                    finalSuggestion += " \\\n\t&& " + newInstruction
                
                if incompleteSuggestion > 0:
                    print("Couldn't come up with a complete conversion (missing " + str(incompleteSuggestion) + " operation/s)\n")

            print("\nSuggested edit (single RUN instruction):\n\t" + finalSuggestion + "\n")

"""def convertLatestToVersion(package):
    url = "https://hub.docker.com/r/library/"+package+"/tags/"
    code = requests.get(url)
    plain = code.text
    s = BeautifulSoup(plain, "html.parser")
    for link in s.find(id="link3"):
        tet = link.get('title')
        print(tet)
        tet_2 = link.get('href')
        print(tet_2)"""


if "FROM" in dockerdict:
    for idx, inst in dockerdict["FROM"]:
        parsedFROM = re.search(r'FROM (.+):latest',inst)
        if parsedFROM:
            package =  parsedFROM.group(1)
            print("===> Undefined version of base image detected at line " + str(idx)+"!\n")
            print("Explanation: your build can suddenly break if that image gets updated, making the program not reproducible")
            print("Original instruction: " + inst)
            url = "https://hub.docker.com/r/library/"+package+"/tags/"            
            response = urlopen(url)
            htmlparser = etree.HTMLParser()
            tree = etree.parse(response, htmlparser)
            div = tree.xpath("/html/body/div/main/div[3]/div[2]/div[2]/div/div/div/div/div[2]/div[1]")[0]
            print("Suggested edit (example): FROM "+package+":"+div.text)


