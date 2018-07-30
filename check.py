import regex as re
from urllib.request import urlopen 
from lxml import etree 

from utility import bcolors

class Inspector:

    def __init__(self, instructionMap):
        self.dockerdict = instructionMap

    # Check for unsafe RUN pipes
    def pipes(self):
        if "RUN" in self.dockerdict:
            for idx, inst in self.dockerdict["RUN"]:
                if "|" in inst and "set -o pipefail" not in inst:
                    print(bcolors.WARNING+"===> Unsafe pipe inside a RUN instruction detected (#"+str(idx)+")!\n"+bcolors.ENDC)
                    print("Explanation: if you want this command to fail due to an error at any stage in the pipe, prepend 'set -o pipefail &&' to ensure that an unexpected error prevents the build from inadvertently succeeding.\n")
                    print("Original instruction: " + inst)
                    print("Suggested edit: " + inst.replace("RUN", "RUN "+bcolors.HEADER+"set -o pipefail &&"+bcolors.ENDC) + "\n")

    # Help function: it retrieves the instructions associated to the main one (ADD) that fetches a compressed file remotely
    def getSubsequentExtractionInstructions(self,file, path, index):
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
                    print(bcolors.WARNING+"===> Unhealthy file download inside an ADD instruction detected (#"+str(idx)+")!\n"+bcolors.ENDC)
                    print("Explanation: because image size matters, using ADD to fetch packages from remote URLs is strongly discouraged; you should use curl or wget instead. That way you can delete the files you no longer need after they’ve been extracted and you don’t have to add another layer in your image.\n")
                    
                    url = parsedADD.group(1)
                    filename = parsedADD.group(2)
                    # Removing the last char, it could be and extra backslash
                    path = parsedADD.group(3)[:-1]
                    extralines = self.getSubsequentExtractionInstructions(filename,path,idx)
                    
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

                    print("\nSuggested edit (single RUN instruction):\n\t" + bcolors.HEADER + finalSuggestion + bcolors.ENDC +"\n")

    # Looks for FROM instructions that don't define a specific image version and use "latest" instead
    def undefinedImageVersions(self):
        if "FROM" in self.dockerdict:
            for idx, inst in self.dockerdict["FROM"]:
                parsedFROM = re.search(r'FROM (.+):latest',inst)
                if parsedFROM:
                    package =  parsedFROM.group(1)
                    print(bcolors.WARNING+"===> Undefined version of base image detected (#" + str(idx)+")!\n"+bcolors.ENDC)
                    print("Explanation: your build can suddenly break if that image gets updated, making the program not reproducible")
                    print("Original instruction: " + inst)
                    print("Suggested edit (example): loading..", end="\r")

                    # Not that useful but at least it's not a random suggestion
                    url = "https://hub.docker.com/r/library/"+package+"/tags/"            
                    response = urlopen(url)
                    htmlparser = etree.HTMLParser()
                    tree = etree.parse(response, htmlparser)
                    # Hoping that the xPath won't change in the near future
                    div = tree.xpath("/html/body/div/main/div[3]/div[2]/div[2]/div/div/div/div/div[2]/div[1]")[0]
                    
                    print("Suggested edit (example): FROM "+package+":"+bcolors.HEADER+div.text+bcolors.ENDC+ "\n")

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
                print("Suggested edit: RUN "+bcolors.HEADER+"apt-get update && "+bcolors.ENDC + inst[4:])
            # Merging multiple install commands and sorting alphabetically (removing duplicates)
            for idx, inst in aptgetInstructions:
                offset = len("apt-get install")+inst.find("apt-get install")
                print(inst[offset:])