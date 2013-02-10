import fnmatch
import os

def find_files(directory, filematch):
  matches = []
  for root, dirnames, filenames in os.walk(directory):
    for filename in fnmatch.filter(filenames, filematch):
        matches.append(os.path.join(root, filename))
        
  return matches