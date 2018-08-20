import regex as re
from lxml import etree 
from utility import bcolors
from urllib.request import urlopen 

from inspector import *
ins = Inspector(scope="./docker")

ins.implement(undefined_image_versions)
ins.implement(pipes)
ins.implement(remote_fetches)
ins.implement(apt_get)

ins.run()