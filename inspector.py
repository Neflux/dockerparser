import os
import sys
import fnmatch
import regex as re
import logging as log
from lxml import etree 
from urllib.request import urlopen 

from utility import bcolors

log.basicConfig(filename='inspector.log', level=log.DEBUG)

class Instruction(str):
    def __init__(self, text, multiline=[]):
        self.text = str(text)
        self.multiline = multiline

    def __get__(self, instance, owner):
        return self.text

    def __set__(self, instance, value):
        self.new_text = value

    def get_updated_instruction(self):
        return self.new_text

class Inspector():

    def __init__(self, **params):
        self.console_rows, self.console_columns = os.popen('stty size', 'r').read().split()
        self.checks = []
        self.replaces = []

        if params.get("scope") is None:
            raise SystemExit('Specify Dockerfile directory with "scope" parameter of costructor')

        self.scope = params.get("scope")
        self.path = self.find_dockerfile()
        self.context, self.filecontext, self.dirscontext = self.get_context()
        self.dockerdict = self.process_instructions()
        self.intersection_analysis()

    def find_dockerfile(self):
        context = os.walk(self.scope, topdown=True)
        exclude = set([".git","__pycache__"])
        for root, dirs, files in context:
            dirs[:] = [d for d in dirs if d not in exclude]
            if "Dockerfile" in files:
                path = root
                if(path[len(path)-1]) != "/":
                    path += "/"
                break # Using the first one found
        if not path:
            log.critical("Could not find any Dockerfile")
            raise SystemExit('Could not find any Dockerfile')
        log.info("Dockerfile path: " + path)
        return path

    def get_context(self):
        dockerignore = self.path+"/.dockerignore"
        filterFiles = False
        if os.path.isfile(dockerignore):
            log.info(".dockerignore detected")
            with open(dockerignore) as f:
                ignore_list = f.readlines()
            filterFiles = True

        context = os.walk(self.path, topdown=True)
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
                    if(root == self.path):
                        filecontext.append(f)
                    else:
                        filecontext.append(root[len(self.path):] + "/"+ f)

        print("\nDirectories: " + str(len(dirscontext)))
        for dir in dirscontext:
            print("\t"+dir)

        print("\nFiles: " + str(len(filecontext)))
        for file in filecontext:
            print("\t"+file)

        return context, filecontext, dirscontext

    def extract_instructions(self):
        with open(self.path+"/Dockerfile") as f:
            content = f.readlines()

        dockerfile, multiline = ([] for i in range(2))
        #instructionList = []
        for line in content:
            line = line.strip()
            if(len(line) > 0):
                if line[0] != "#":
                    if line[len(line)-1] == "\\":
                        multiline.append(line.split("\\", 1)[0])
                    elif len(multiline) > 0:
                        multiline.append(line)
                        dockerfile.append(Instruction("".join(multiline),multiline))
                        multiline = []
                    else:
                        dockerfile.append(Instruction(line))
        
        if len(content) == 0:
            log.critical("This Dockerfile looks empty, make sure you specified the appropriate subfolder")
            raise SystemExit("This Dockerfile looks empty, make sure you specified the appropriate subfolder")

        return dockerfile

    def process_instructions(self):
        layers = 0
        dockerdict = {}
        for idx, inst in enumerate(self.dockerfile):
            key = inst.split(" ")[0]
            dockerdict.setdefault(key,[]).append((idx+1, inst))
            if key in ["RUN","COPY","ADD"]:
                layers += 1

        if len(self.dockerfile) > 0:
            print("\nInstructions: "+ str(len(self.dockerfile))+" --> layers: " + str(layers))
            for inst in self.dockerfile:
                print("\t"+inst)

        return dockerdict

    def intersection_analysis(self):
        fileocc, dirsocc = ([] for i in range(2))
        for inst in self.dockerfile:
            #TODO: Weak logic, needs improvement
            for file in self.filecontext:
                if file in inst:
                    fileocc.append((file,inst))
            for dir in self.dirscontext:
                # Regex makes sure that files are not recognized as dirs (prefix)
                if re.match( r'.*'+re.escape(dir)+r'(?!\/).*', inst):
                    dirsocc.append((dir,inst))

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

    def implement(self, func):
        self.checks.append(func)

    def update(self):
        for x,y in self.replaces:
            for key, value in self.dockerdict.items():
                if value == x
                    self.dockerdict[key] = y
                    break

        self.replaces = []
    
    def replace(a,b):
        self.replaces.append((a,b))

    def run(self, **params):
        log.info("Starting optimization routine")
        print(self.dockerdict)
        for fnc in self.checks:
            fnc(self)
            self.update()
        
    @property
    def dockerfile(self):
        log.info("Accessing dockerfile")
        return self._dockerfile

