import sys
sys.path.append(r'C:\Program Files\JetBrains\PyCharm 2017.1.4\helpers\pydev')
import pydevd
pydevd.settrace('localhost', port=56266, stdoutToServer=True, stderrToServer=True, suspend=False)

from ._conf import *
from ._handler import *
