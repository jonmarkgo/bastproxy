"""
This plugin has a simple queue class
"""
import sys
import argparse

class ArgumentParser(argparse.ArgumentParser):
  """
  argparse class that doesn't exit on error
  """
  def error(self, message):
    """
    override the error class to raise an error and not exit
    """
    exc = sys.exc_info()[1]
    if exc:
      exc.errormsg = message
      raise exc

RawDescriptionHelpFormatter = argparse.RawDescriptionHelpFormatter
HelpFormatter = argparse.HelpFormatter
SUPPRESS = argparse.SUPPRESS
OPTIONAL = argparse.OPTIONAL
ZERO_OR_MORE = argparse.ZERO_OR_MORE
ArgumentError = argparse.ArgumentError
