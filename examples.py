import regex as re
from lxml import etree 
from utility import bcolors
from urllib.request import urlopen 

# Looks for FROM instructions that don't define a specific image version and use "latest" instead
def undefined_image_versions(inspector):
    for inst in inspector.dockerfile["FROM"]:
        parsedFROM = re.search(r'FROM (.+):latest',inst)
        if not parsedFROM:
            continue
        package = parsedFROM.group(1)
        inspector.format(title="Undefined version of base image", id=inst.index, 
        explanation="Your build can suddenly break if that image gets updated, making the program not reproducible",
        original=inst, optimization="FROM "+package+":<version>")
        inspector.replace(inst,"FROM "+package+":<version>")

# Check for unsafe RUN pipes
def pipes(inspector):
    for inst in inspector.dockerfile["RUN"]:
        if "|" in inst and "set -o pipefail" not in inst:
            opt = inst.replace("RUN","RUN set -o pipefail &&")
            inspector.format(title="Unsafe pipe inside a RUN instruction", id=inst.index, 
            explanation="If you want this command to fail due to an error at any stage in the pipe, prepend 'set -o pipefail &&' to ensure that an unexpected error prevents the build from inadvertently succeeding.",
            original=inst, optimization=opt)
            inspector.replace(inst,opt)

# Check for unhealthy ADDs that fetch a compressed file from a remote origin
def remote_fetches(inspector):
    for inst in inspector.dockerfile["ADD"]:
        # This regex pattern needs to be improved
        parsedADD = re.search(r'ADD\s(.*\/(.*)\.(?:tar|xz|zip|gz))\s(.*)', inst)
        if not parsedADD:
            continue
        url = parsedADD.group(1)
        filename = parsedADD.group(2)
        path = parsedADD.group(3)[:-1]  # Removing the last char, it could be and extra backslash

        finalSuggestion = "RUN set -o pipefail && mkdir -p " + path + " \\\n\t&& curl -SL " + url + " \\\n\t*** your extraction instructions ***"
        inspector.format(title="Unhealthy file download inside an ADD instruction detected", id=inst.index,
            explanation="Because image size matters, using ADD to fetch packages from remote URLs is strongly discouraged; you should use curl or wget instead. That way you can delete the files you no longer need after they’ve been extracted and you don’t have to add another layer in your image.",
            original=inst, optimization=finalSuggestion)

# Help function: it retrieves the apt-get update instruction index
def get_preceding_update(inspector, installIndex):
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
    update = get_preceding_update(inspector, idx)
    if update == -1 or update == -2:
        log.info("Multiple apt-get update commands")
    elif update != 0:
        inspector.format(title="Unhealthy apt-get logic inside RUN instructions",id=idx,
        explanation="Using apt-get update alone in a RUN statement causes caching issues and subsequent apt-get install instructions fail.")
    
    # Merging multiple install commands and sorting alphabetically (removing duplicates)
    packages = []
    firstid = -1
    for idx, inst in aptgetInstructions:
        if firstid == -1:
            firstid = idx
        offset = len("apt-get install")+inst.find("apt-get install")
        packages.extend([x for x in inst[offset:].strip().split(" ") if x[0] != "-"])
        inspector.remove(inst)
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

        inspector.remove(inspector.dockerfile[update-1])
        inspector.insert_at(finalSuggestion,firstid)