from inspector import Inspector
from examples import *

ins = Inspector(scope="../docker")

ins.implement(undefined_image_versions)
ins.implement(pipes)
ins.implement(remote_fetches)
ins.implement(apt_get)

ins.run()