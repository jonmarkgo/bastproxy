"""
$Id$
"""

import glob, os, sys

from libs import exported

def get_module_name(filename):
  path, filename = os.path.split(filename)
  return os.path.splitext(filename)[0]

class PluginMgr:
  def __init__(self):
    self.plugins = {}
    self.load_modules()

  def load_modules(self):
    index = __file__.rfind(os.sep)
    if index == -1:
      path = "." + os.sep
    else:
      path = __file__[:index]

    _module_list = glob.glob( os.path.join(path, "*.py"))
    _module_list.sort()

    for mem in _module_list:
      # we skip over all files that start with a _
      # this allows hackers to be working on a module and not have
      # it die every time.
      mem2 = get_module_name(mem)
      if mem2.startswith("_"):
        continue

      try:
        name = "plugins." + mem2
        _module = __import__(name)
        _module = sys.modules[name]

        if _module.__dict__.has_key("load"):
          _module.load()

        _module.__dict__["proxy_import"] = 1
        self.plugins[name] = True
      except:
        exported.write_traceback("Module '%s' refuses to load." % name)
