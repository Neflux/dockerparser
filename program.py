import regex as re
from urllib.request import urlopen
from utility import bcolors

from inspector import Inspector
ins = Inspector(scope="./docker")

# Looks for FROM instructions that don't define a specific image version and use "latest" instead
def undefined_image_versions(self):
    if "FROM" not in ins.dockerdict:
        return
    #TODO: Check if there can be multiple FROMs
    for idx, inst in ins.dockerdict["FROM"]:
        parsedFROM = re.search(r'FROM (.+):latest',inst)
        if not parsedFROM:
            continue
        package =  parsedFROM.group(1)
        message = bcolors.WARNING+"===> Undefined version of base image detected (#" + str(idx)+")!\n"+bcolors.ENDC
        message += "Explanation: your build can suddenly break if that image gets updated, making the program not reproducible"
        message += "Original instruction: " + inst
        try:
            # Not that useful but at least it's not a random suggestion
            url = "https://hub.docker.com/r/library/"+package+"/tags/"            
            response = urlopen(url)
            htmlparser = etree.HTMLParser()
            tree = etree.parse(response, htmlparser)
            # Hoping that the xPath won't change in the near future
            div = tree.xpath("/html/body/div/main/div[3]/div[2]/div[2]/div/div/div/div/div[2]/div[1]")[0]
            message += "Suggested edit (example): FROM "+package+":"+bcolors.HEADER+div.text+bcolors.ENDC+ "\n"
            ins.replace(inst,"FROM "+package+":"div.text)
        except:
            message += "Suggested edit (example): FROM "+package+":"+bcolors.HEADER+"<version>"+bcolors.ENDC+ "\n"                     
            ins.replace(inst,"FROM "+package+":"div.text)
#inspector.remoteFetches()
#inspector.aptget()

# Final checks
#inspector.pipes()
#inspector.longRuns(100)

ins.implement(undefined_image_versions)
ins.run()

"""ins.get_context_files()
ins.get_dockerfile_path()
ins.get_dockerfile_instruction_list()
ins.get_dockerfile_instruction_dict()"""