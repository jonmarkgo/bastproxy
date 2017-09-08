"""
this module is for timing functions
"""
from timeit import default_timer
from libs.api import API as BASEAPI
API = BASEAPI()

def timeit(func):
  """
  a decorator to time a function
  """
  def wrapper(*arg):
    """
    the wrapper to time a function
    """
    time1 = default_timer()
    API('send.msg')('%s: started %s' % (func.func_name, arg), 'timing')
    res = func(*arg)
    time2 = default_timer()
    API('log.adddtype')('timing')
    API('send.msg')('%s: %0.3f ms' % \
              (func.func_name, (time2-time1)*1000.0), 'timing')
    return res
  return wrapper
