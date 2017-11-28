"""
This plugin has a simple queue class
"""
import sys
from argparse import ArgumentError, ArgumentParser

class ArgParser(ArgumentParser):
  """
  argparse class that doesn't exit on error
  """
  def error(self, message):
    """
    override the error class to not exit
    """
    exc = sys.exc_info()[1]
    if exc:
      exc.errormsg = message
      raise exc
