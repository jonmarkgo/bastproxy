"""
This plugin has a simple queue class
"""
class SimpleQueue(object):
  """
  a simple queue class
  """
  def __init__(self, length=10):
    """
    initialize the class

    len is the length of the queue
    """
    self.len = length
    self.items = []
    self.snapshot = None

  def isempty(self):
    """
    return True for an empty queue
    """
    return self.items == []

  def enqueue(self, item):
    """
    queue an item
    """
    self.items.append(item)
    while len(self.items) > self.len:
      self.items.pop(0)

  def dequeue(self):
    """
    dequeue an item
    """
    return self.items.pop(0)

  def size(self):
    """
    return the size of the queue
    """
    return len(self.items)

  def takesnapshot(self):
    """
    take a snapshot of the current queue
    """
    self.snapshot = self.items[:]

  def getsnapshot(self):
    """
    return the current snapshot
    """
    return self.snapshot
