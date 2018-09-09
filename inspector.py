import os
import fnmatch
import queue
import regex as re
import logging as log
from utility import *

log.basicConfig(filename='inspector.log', level=log.DEBUG)
            
class Inspector():
    def __init__(self, **params):
        self.console_rows, self.console_columns = os.popen('stty size', 'r').read().split()
        self.checks = []
        self.actions = queue.Queue()

        if params.get("scope") is None:
            raise SystemExit('Specify Dockerfile directory with "scope" parameter of costructor')

        self.scope = params.get("scope")
        self.path = self.find_dockerfile()
        self.context, self.filecontext, self.dirscontext = self.get_context()
        self.dockerfile = self.extract_instructions()
        #self.intersection_analysis()

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

        dockerfile = Dockerfile()
        multiline = []
        shift = 0
        for idx, original_line in enumerate(content):
            line = original_line.strip()
            if(len(line) > 0):
                if line[0] != "#":
                    if line[len(line)-1] == "\\":
                        multiline.append(line.split("\\", 1)[0])
                    elif len(multiline) > 0:
                        shift += len(multiline)
                        multiline.append(line)
                        dockerfile.append(Instruction("".join(multiline),idx-shift))
                        multiline = []
                    else:
                        dockerfile.append(Instruction(line,idx-shift))
                else:
                    dockerfile.append(Instruction(line,idx-shift))
            else:
                dockerfile.append(Instruction("< empty line >",idx-shift))
        
        if len(content) == 0:
            log.critical("This Dockerfile looks empty, make sure you specified the appropriate subfolder")
            raise SystemExit("This Dockerfile looks empty, make sure you specified the appropriate subfolder")

        if len(dockerfile) > 0:
            print("\nInstructions: "+ str(dockerfile.len)+" --> layers: " + str(dockerfile.layers))
            print(dockerfile)

        return dockerfile

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

    def apply(self):
        while not self.actions.empty():
            items = self.actions.get()
            func = items[0]
            args = items[1:]
            func(*args)

    # Replace Instruction x with string y
    def replace(self,x,y):
        self.actions.put((self.dockerfile.replace,x,y))
    
    # Remove Instruction x
    def remove(self, x):
        self.actions.put((self.dockerfile.remove,x))

    # Insert Instruction x
    def insert(self, idx, x):
        self.actions.put((self.dockerfile.insert,idx,x))

    def run(self, **params):
        log.info("Starting optimization routine")
        
        for check in self.checks:
            log.info("function: "+check.__name__)
            check(self)
            if not self.actions.empty():
                if query_yes_no("\n["+check.__name__+"] Do you want to apply this optimization?"):
                    self.apply()

        print("\nOptimized version:")
        print(self.dockerfile)

        with open("Dockerfile.opt","w") as updated_file:
            updated_file.write("\n".join("" if x.key == "<" else x for x in self.dockerfile))

        print("\nUpdated list of istructions saved at Dockerfile.opt")

    def format(self,**kwargs):
        if "title" not in kwargs:
            self.report = ""
            pass
        message = bcolors.WARNING+"\n===> " + str(kwargs["title"]) + bcolors.ENDC
        if "id" in kwargs:
            message += "(# "+str(kwargs["id"])+")!"+bcolors.ENDC
        if "original" in kwargs and "optimization" in kwargs:
            message += "\nInstruction: " + str(kwargs["original"]) +"\n"
        if "explanation" in kwargs:
            message += "\nExplanation: " + str(kwargs["explanation"])
        if "original" in kwargs and "optimization" in kwargs:
            message += "\n\nSuggested edit: " + str(kwargs["optimization"])
        print(message)
