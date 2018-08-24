import regex as re
from lxml import etree 
from utility import bcolors
from urllib.request import urlopen 

# Looks for FROM instructions that don't define a specific image version and use "latest" instead
def undefined_image_versions(inspector):
    for idx, inst in enumerate(inspector.dockerfile["FROM"]):
        parsedFROM = re.search(r'FROM (.+):latest',inst)
        if not parsedFROM:
            continue
        package = parsedFROM.group(1)
        inspector.format(title="Undefined version of base image", id=idx, 
        explanation="Your build can suddenly break if that image gets updated, making the program not reproducible",
        original=inst, optimization="FROM "+package+":<version>")
        inspector.replace(inst,"FROM "+package+":<version>")

# Check for unsafe RUN pipes
def pipes(inspector):
    for idx, inst in enumerate(inspector.dockerfile["RUN"]):
        if "|" in inst and "set -o pipefail" not in inst:
            opt = inst.replace("RUN","RUN set -o pipefail &&")
            inspector.format(title="Unsafe pipe inside a RUN instruction", id=idx, 
            explanation="If you want this command to fail due to an error at any stage in the pipe, prepend 'set -o pipefail &&' to ensure that an unexpected error prevents the build from inadvertently succeeding.",
            original=inst, optimization=opt)
            inspector.replace(inst,opt)

# Check for unhealthy ADDs that fetch a compressed file from a remote origin
def remote_fetches(inspector):
    for idx, inst in enumerate(inspector.dockerfile["ADD"]):
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

def apt_get(inspector):

    if not inspector.dockerfile["RUN"]: 
        return

    first_idx = -1
    for inst in inspector.dockerfile["RUN"]:
        if inst.find("apt-get update") != -1:
            if inst.find(" install ") == -1:
                if first_idx == -1:
                    first_idx = inst.index
                inspector.format(title="Unhealthy apt-get logic inside RUN instructions",id=inst.index,
                explanation="Using apt-get update alone in a RUN statement causes caching issues and subsequent apt-get install instructions fail.")
                inspector.remove(inst)

    aptget_instructions = [inst for inst in inspector.dockerfile["RUN"] if inst.find("apt-get install") != -1 ]
        
    # Merging multiple install commands and sorting alphabetically (removing duplicates)
    packages = []
    for inst in aptget_instructions:
        if first_idx == -1:
            first_idx = inst.index
        inspector.remove(inst)
        offset = len("apt-get install")+inst.find("apt-get install")
        packages.extend([x for x in inst[offset:].strip().split(" ") if x[0] != "-"])

    packages = sorted(set(packages))
    first = packages[0]

    if len(packages) > 1:
        last = packages[len(packages)-1]
        packages = ["\t"+x+" \\\n" for x in packages[1:-1]]
        finalAppendix = "".join(packages)
        finalSuggestion = "RUN apt-get update && apt-get install -y " + first + " \\\n" + finalAppendix  + "\t" + last
        
        inspector.format(title="Unsorted packages of 'apt-get install' operation",id=0,
        explanation="Whenever possible, ease later changes by sorting multi-line arguments alphanumerically. This helps to avoid duplication of packages and make the list much easier to update. This also makes PRs a lot easier to read and review. Adding a space before a backslash (\) helps as well.",
        original="\n\t".join(aptget_instructions), 
        optimization=finalSuggestion)

        inspector.insert(first_idx, finalSuggestion)