"""
holds functions to import plugins and files
"""
import os
import fnmatch
import sys

def find_files(directory, filematch):
  """
  find files in a directory that match a filter
  """
  matches = []
  if os.sep in filematch:
    tstuff = filematch.split(os.sep)
    directory = os.path.join(directory, tstuff[0])
    filematch = tstuff[-1]
  for root, _, filenames in os.walk(directory, followlinks=True):
    for filename in fnmatch.filter(filenames, filematch):
      matches.append(os.path.join(root, filename))

  return matches

def get_module_name(modpath):
  """
  get a module name
  """
  filename = os.path.basename(modpath)
  dirname = os.path.dirname(modpath)
  base = dirname.replace(os.path.sep, '.')
  if base[0] == '.':
    base = base[1:]
  mod = os.path.splitext(filename)[0]
  if not base:
    value1 = '.'.join([mod])
    value2 = mod
  else:
    value1 = '.'.join([base, mod])
    value2 = mod

  return value1, value2

def findmodule(basepath, name):
  """
  find a module file
  """
  if '.' in name:
    tlist = name.split('.')
    name = tlist[-1]
    del tlist[-1]
    npath = os.sep.join(tlist)

  _module_list = find_files(basepath, name + ".py")

  if len(_module_list) == 1:
    return _module_list[0], basepath
  else:
    for i in _module_list:
      if npath in i:
        return i, basepath

  return '', ''

# import a module
def importmodule(modpath, basepath, plugin, impbase, silent=False):
  """
  import a single module
  """
  _module = None
  if basepath in modpath:
    modpath = modpath.replace(basepath, '')

  imploc, modname = get_module_name(modpath)
  fullimploc = impbase + '.' + imploc

  if modname.startswith("_"):
    if not silent:
      plugin.api('send.msg')('did not import %s because it is in development' % \
                               fullimploc)
    return False, 'dev', _module, fullimploc

  try:
    if fullimploc in sys.modules:
      return (True, 'already',
              sys.modules[fullimploc], fullimploc)

    if not silent:
      plugin.api('send.msg')('importing %s' % fullimploc, primary='plugins')
    _module = __import__(fullimploc)
    _module = sys.modules[fullimploc]
    if not silent:
      plugin.api('send.msg')('imported %s' % fullimploc, primary='plugins')
    return True, 'import', _module, fullimploc

  except Exception: # pylint: disable=broad-except
    if fullimploc in sys.modules:
      del sys.modules[fullimploc]

    plugin.api('send.traceback')(
        "Module '%s' refuses to import/load." % fullimploc)
    return False, 'error', _module, fullimploc

def deletemodule(fullimploc):
  """
  delete a module
  """
  if fullimploc in sys.modules:
    del sys.modules[fullimploc]
    return True

  return False
