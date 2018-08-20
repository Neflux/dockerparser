import os
import sys
import fnmatch
import regex as re
import logging as log

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
        self.removes = []

        if params.get("scope") is None:
            raise SystemExit('Specify Dockerfile directory with "scope" parameter of costructor')

        self.scope = params.get("scope")
        self.path = self.find_dockerfile()
        self.context, self.filecontext, self.dirscontext = self.get_context()
        self.dockerfile = self.extract_instructions()
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

            # Update dockerdict
            exit = False
            for key, array in self.dockerdict.items():
                for idx, tup in enumerate(array):
                    if tup[1] == x:
                        self.dockerdict[key][idx] = (tup[0], y)
                        exit = True
                        break
                if exit: break
            
            # Update dockefile
            idx = self.dockerfile.index(x)
            self.dockerfile[idx] = y

        for x in self.removes:

            # Update dockerdict
            exit = False
            for key, array in self.dockerdict.items():
                for idx, tup in enumerate(array):
                    if tup[1] == x:
                        self.dockerdict[key].remove(tup)
                        exit = True
                        break
                if exit: break
            
            # Update dockefile
            self.dockerfile.remove(x)

        self.replaces = []
        self.removes = []
    
    def replace(self,a,b):
        self.replaces.append((a,b))
    
    def remove(self,a):
        self.removes.append(a)

    def run(self, **params):
        log.info("Starting optimization routine")
        
        for check in self.checks:
            log.info("function: "+check.__name__)
            check(self)
            self.update()

        print("\nOptimized version:")
        for x in self.dockerfile:
            print("\t"+x)

    def format(self,**kwargs):
        if "title" not in kwargs:
            self.report = ""
            pass
        message = bcolors.WARNING+"\n===> " + str(kwargs["title"]) + bcolors.ENDC
        if "id" in kwargs:
            message += " (#" + str(kwargs["id"])+")!"+ bcolors.ENDC
        if "explanation" in kwargs:
            message += "\nExplanation: " + str(kwargs["explanation"])
        if "original" in kwargs and "optimization" in kwargs:
            message += "\n\nOriginal version: " + str(kwargs["original"])
            message += "\nSuggested edit: " + str(kwargs["optimization"])
        print(message)
        
"""   @property
    def dockerfile(self):
        log.info("Accessing dockerfile")
        return self._dockerfile"""

# Looks for FROM instructions that don't define a specific image version and use "latest" instead
def undefined_image_versions(inspector):
    if "FROM" not in inspector.dockerdict:
        return
    #TODO: Check if there can be multiple FROMs
    for idx, inst in inspector.dockerdict["FROM"]:
        parsedFROM = re.search(r'FROM (.+):latest',inst)
        if not parsedFROM:
            continue
        package =  parsedFROM.group(1)
        inspector.format(title="Undefined version of base image", id=idx, 
        explanation="Your build can suddenly break if that image gets updated, making the program not reproducible",
        original=inst, optimization="FROM "+package+":<version>")
        inspector.replace(inst,"FROM "+package+":<version>")

# Check for unsafe RUN pipes
def pipes(inspector):
    if "RUN" not in inspector.dockerdict:
        return
    for idx, inst in inspector.dockerdict["RUN"]:
        if "|" in inst and "set -o pipefail" not in inst:
            opt = inst.replace("RUN","RUN set -o pipefail &&")
            inspector.format(title="Unsafe pipe inside a RUN instruction", id=idx, 
            explanation="If you want this command to fail due to an error at any stage in the pipe, prepend 'set -o pipefail &&' to ensure that an unexpected error prevents the build from inadvertently succeeding.",
            original=inst, optimization=opt)
            inspector.replace(inst,opt)

# Check for unhealthy ADDs that fetch a compressed file from a remote origin
def remote_fetches(inspector):
    if "ADD" not in inspector.dockerdict:
        return
    for idx, inst in inspector.dockerdict["ADD"]:
        # This regex pattern needs to be improved
        parsedADD = re.search(r'ADD\s(.*\/(.*)\.(?:tar|xz|zip|gz))\s(.*)', inst)
        if not parsedADD:
            continue
        url = parsedADD.group(1)
        filename = parsedADD.group(2)
        path = parsedADD.group(3)[:-1]  # Removing the last char, it could be and extra backslash

        finalSuggestion = "RUN set -o pipefail && mkdir -p " + path + " \\\n\t&& curl -SL " + url + " \\\n\t*** your extraction instructions ***"
        inspector.format(title="Unhealthy file download inside an ADD instruction detected", id=idx,
            explanation="Because image size matters, using ADD to fetch packages from remote URLs is strongly discouraged; you should use curl or wget instead. That way you can delete the files you no longer need after they’ve been extracted and you don’t have to add another layer in your image.",
            original=inst, optimization=finalSuggestion)

# Help function: it retrieves the apt-get update instruction index
def getPrecedingUpdate(inspector, installIndex):
    result = 0
    if "RUN" not in inspector.dockerdict:
        return -2
    for idx, inst in inspector.dockerdict["RUN"]:
        # List update instruction always comes before the install
        if inst.find("apt-get update") != -1:
            # If there are multiple updates return an error integer
            if result != 0:
                result = -1
                break
            result = idx
    return result

def apt_get(inspector):
    if "RUN" not in inspector.dockerdict:
        return
    aptgetInstructions = [(idx, inst) for idx, inst in inspector.dockerdict["RUN"] if inst.find("apt-get install") != -1 ]
    idx = aptgetInstructions[0][0]
    inst = aptgetInstructions[0][1]
    
    # Checking update-install logic
    update = getPrecedingUpdate(inspector, idx)
    if update == -1:
        inspector.format(title="Multiple apt-get update commands",
        explanation="fix your Dockerfile")
    elif update != 0:
        inspector.format(title="Unhealthy apt-get logic inside RUN instructions",id=idx,
        explanation="Using apt-get update alone in a RUN statement causes caching issues and subsequent apt-get install instructions fail.")
    
    # Merging multiple install commands and sorting alphabetically (removing duplicates)
    packages = []
    for idx, inst in aptgetInstructions:
        offset = len("apt-get install")+inst.find("apt-get install")
        packages.extend([x for x in inst[offset:].strip().split(" ") if x[0] != "-"])
    packages = sorted(set(packages))
    first = packages[0]

    if len(packages) > 1:
        last = packages[len(packages)-1]
        packages = ["\t"+x+" \\\n" for x in packages[1:-1]]
        finalAppendix = "".join(packages)
        finalSuggestion = "RUN apt-get update && apt-get install -y " + first + " \\\n" + finalAppendix  + "\t" + last
        
        inspector.format(title="Unhealthy apt-get logic inside RUN instructions",id=idx,
        explanation="Using apt-get update alone in a RUN statement causes caching issues and subsequent apt-get install instructions fail.",
        original="\n\t".join(x[1] for x in aptgetInstructions), 
        optimization=finalSuggestion)

