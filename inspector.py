import os
import sys
import fnmatch
import regex as re
import logging as log
from utility import bcolors

log.basicConfig(filename='inspector.log', level=log.DEBUG)

class Instruction(str):
    def __new__(cls, text, original_indexes):
        return super(Instruction, cls).__new__(cls, text)

    def __init__(self, text, original_indexes):
        self.key = text.split(" ")[0]
        if not isinstance(original_indexes, list):
            original_indexes = [original_indexes]
        self.original_indexes = original_indexes

    def __repr__(self):
        return super(Instruction, self).__repr__()
    
    def __str__(self):
        return super(Instruction, self).__str__()

    def __get__(self, instance, owner):
        return super(Instruction, self).__get__()

    @property
    def index(self):
        return self.original_indexes

    """def __set__(self, instance, value):
        self.new_text = value

    def get_updated_instruction(self):
        return self.new_text"""

class Dockerfile(list):
    def __init__(self):
        pass

    def __repr__(self):
        final_repr = bcolors.BOLD+"\nline\tinstruction"+bcolors.ENDC
        for inst in self:
            final_repr += "\n"+",".join(str(x+1) for x in inst.index)+"\t"
            if inst.key == "#":
                final_repr += bcolors.OKGREEN+inst+bcolors.ENDC
            elif inst.key in ["RUN","COPY","ADD"]:
                final_repr += bcolors.HEADER+inst+bcolors.ENDC
            else:
                final_repr += inst
        return final_repr
    
    def __str__(self):
        return self.__repr__()                                                                                                         

    def __getitem__(self, key):
        if isinstance(key, int):
            return super(Dockerfile, self).__getitem__(key)
        elif isinstance(key, str):
            return [x for x in self if x.key == key]

    def replace(self, x, y):
        for idx, inst in enumerate(self):
            if inst == x:
                self[idx] = Instruction(y, inst.index)
                break

    # Number of instructions generating a layer
    @property
    def layers(self):
        return len([x for x in self if x.key in ["RUN","COPY","ADD"]])
    
    # Number of non-comment instructions
    @property
    def len(self):
        return len([x for x in self if x.key != "#"])
            
class Inspector():
    def __init__(self, **params):
        self.console_rows, self.console_columns = os.popen('stty size', 'r').read().split()
        self.checks, self.replaces, self.removes, self.inserts = ([] for i in range(4))

        if params.get("scope") is None:
            raise SystemExit('Specify Dockerfile directory with "scope" parameter of costructor')

        self.scope = params.get("scope")
        self.path = self.find_dockerfile()
        self.context, self.filecontext, self.dirscontext = self.get_context()
        self.dockerfile = self.extract_instructions()
        """self.intersection_analysis()"""

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
        start_index = -1
        for idx, original_line in enumerate(content):
            line = original_line.strip()
            if(len(line) > 0):
                if line[0] != "#":
                    if line[len(line)-1] == "\\":
                        multiline.append(line.split("\\", 1)[0])
                        if start_index == -1: start_index = idx
                    elif len(multiline) > 0:
                        multiline.append(line)
                        dockerfile.append(Instruction("".join(multiline),[i for i in range(start_index,idx)]))
                        multiline = []
                        start_index = -1
                    else:
                        dockerfile.append(Instruction(line,idx))
                else:
                    dockerfile.append(Instruction(line,idx))
        
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

    def update(self):
        for x,y in self.replaces:
            self.dockerfile.replace(x,y)

        for x in self.removes:
            self.dockerfile.remove(x)

        for x,y in self.inserts:
            self.dockerfile.insert_at(x,y)

        self.replaces = []
        self.removes = []
        self.inserts = []
    
    def replace(self,a,b):
        self.replaces.append((a,b))
    
    def remove(self,a):
        self.removes.append(a)

    def insert_at(self, a, idx):
        self.inserts.append((a, idx))

    def run(self, **params):
        log.info("Starting optimization routine")
        
        for check in self.checks:
            log.info("function: "+check.__name__)
            check(self)
            self.update()

        print("\nOptimized version:")
        print(self.dockerfile)

    def format(self,**kwargs):
        if "title" not in kwargs:
            self.report = ""
            pass
        message = bcolors.WARNING+"\n===> " + str(kwargs["title"]) + bcolors.ENDC
        if "id" in kwargs:
            message += "("+"#".join(str(x+1) for x in kwargs["id"]) + ")!"+ bcolors.ENDC
        if "explanation" in kwargs:
            message += "\nExplanation: " + str(kwargs["explanation"])
        if "original" in kwargs and "optimization" in kwargs:
            message += "\n\nOriginal version: " + str(kwargs["original"])
            message += "\nSuggested edit: " + str(kwargs["optimization"])
        print(message)
        
""" @property
    def dockerfile(self):
        log.info("Accessing dockerfile")
        return self._dockerfile"""
