import regex as re
from urllib.request import urlopen 
from lxml import etree 

from utility import bcolors

# Populated by Inspector

class Improvement:

    def __init__(self, message, explanation, originalLines, suggestedEdit="", highlightedPart=""):
        self.message = message
        self.explanation = explanation
        self.originalLines = originalLines
        self.suggestedEdit = suggestedEdit
        self.highlightedPart = highlightedPart

    def __str__(self):
        result =    bcolors.WARNING+"===> " + self.message + " (#" + ", #".join(str(x) for x in self.originalLines) +")"+bcolors.ENDC
        result +=   "\nExplanation: " + self.explanation
        result +=   "\n\nOriginal instruction"+("s" if len(self.originalLines) > 1 else "")+":\n\t" + "\n\t".join(self.instructionList[x-1] for x in self.originalLines)
        result +=   "\n\nSuggested edit:\n\t" + self.suggestedEdit
        return result
        

class Inspector:

    def __init__(self, _dict, _list):
        self.dockerdict = _dict
        Improvement.instructionList = _list
        self.improvements = []

    # Check for unsafe RUN pipes
    def pipes(self):
        if "RUN" in self.dockerdict:
            for idx, inst in self.dockerdict["RUN"]:
                if "|" in inst and "set -o pipefail" not in inst:
                    self.improvements.append(Improvement(
                        "Unsafe pipe inside a RUN instruction detected",
                        "If you want this command to fail due to an error at any stage in the pipe, prepend 'set -o pipefail &&' to ensure that an unexpected error prevents the build from inadvertently succeeding.",
                        [idx], inst, "set -o pipefail &&"
                    ))

    # Help function: it retrieves the instructions associated to the main one (ADD) that fetches a compressed file remotely
    def getSubsequentExtractionInstructions(self, file, path, index):
        results = []
        if "RUN" in self.dockerdict:
            for idx, inst in self.dockerdict["RUN"]:
                # Extraction instructions always come after the download
                if idx > index and (file in inst or path in inst): # Weak logic, needs improvement
                    results.append((idx, inst))
        return results

    # Check for unhealthy ADDs that fetch a compressed file from a remote origin
    def remoteFetches(self):
        if "ADD" in self.dockerdict:
            for idx, inst in self.dockerdict["ADD"]:
                # This regex pattern needs to be improved
                parsedADD = re.search(r'ADD\s(.*\/(.*)\.(?:tar|xz|zip|gz))\s(.*)', inst)
                if parsedADD:
                    url = parsedADD.group(1)
                    filename = parsedADD.group(2)
                    # Removing the last char, it could be and extra backslash
                    path = parsedADD.group(3)[:-1]
                    extralines = self.getSubsequentExtractionInstructions(filename,path,idx)
                    newSuggestedInstructions = []
                    incompleteSuggestion = 0
                    for x,y in extralines:
                        # Print those extra lines
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
                        finalSuggestion = "RUN set -o pipefail && mkdir -p " + path + " \\\n\t&& curl -SL " + url + " \\\n\t*** your extraction instructions ***"
                    else:
                        finalSuggestion = "RUN set -o pipefail && mkdir -p " + path + " \\\n\t&& curl -SL " + url
                        # Pipe the first extraction
                        if len(newSuggestedInstructions) > 0:
                            finalSuggestion += " \\\n\t| "+newSuggestedInstructions[0]
                        
                        for newInstruction in newSuggestedInstructions[1:]:
                            finalSuggestion += " \\\n\t&& " + newInstruction
                        
                        if incompleteSuggestion > 0:
                            print("Couldn't come up with a complete conversion (missing " + str(incompleteSuggestion) + " operation/s)\n")

                    #self.improvements.append
                    
                    originalLines = [x-1 for x,y in extralines]
                    originalLines.append(idx)
                    print(Improvement("Unhealthy file download inside an ADD instruction detected",
                        "because image size matters, using ADD to fetch packages from remote URLs is strongly discouraged; you should use curl or wget instead. That way you can delete the files you no longer need after they’ve been extracted and you don’t have to add another layer in your image.",
                        originalLines, finalSuggestion, ""))
                    

    
    def longRuns(self,maxChars):
        if "RUN" in self.dockerdict:
            for idx, inst in self.dockerdict["RUN"]:
                if len(inst) > maxChars:
                    print(bcolors.WARNING+"===> This RUN instruction line is too long (#" + str(idx)+")!\n"+bcolors.ENDC)
                    print("Explanation: split long or complex RUN statements on multiple lines separated with backslashes to make your Dockerfile more readable, understandable, and maintainable.")
                    print("Original instruction: " + inst)
                    #TODO: first sort and split apt-gets

    # Help function: it retrieves the apt-get update instruction index
    def getPrecedingUpdate(self, installIndex):
        result = 0
        if "RUN" in self.dockerdict:
            for idx, inst in self.dockerdict["RUN"]:
                # List update instruction always comes before the install
                if inst.find("apt-get update") != -1:
                    # If there are multiple updates return an error integer
                    if result != 0:
                        result = -1
                        break
                    result = idx
        return result

    def aptget(self):
        if "RUN" in self.dockerdict:
            aptgetInstructions = [(idx, inst) for idx, inst in self.dockerdict["RUN"] if inst.find("apt-get install") != -1 ]
            idx = aptgetInstructions[0][0]
            inst = aptgetInstructions[0][1]
            # Checking update-install logic
            update = self.getPrecedingUpdate(idx)
            if update == -1:
                print(bcolors.WARNING+"===> Multiple apt-get update commands found, fix your Dockerfile (#" + str(update)+")!\n"+bcolors.ENDC)
            elif update != 0:
                print(bcolors.WARNING+"===> Unhealthy apt-get logic inside RUN instructions detected (#" + str(update)+" and #"+str(idx)+")!\n"+bcolors.ENDC)
                print("Explanation: Using apt-get update alone in a RUN statement causes caching issues and subsequent apt-get install instructions fail.")
                print("Original instruction: " + inst)
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
                finalSuggestion = "RUN apt-get update && apt-get install -y " + first + " \\\n" + finalAppendix
                print("Suggested edit: " + finalSuggestion + "\t" + last)
