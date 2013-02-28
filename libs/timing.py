import time
from libs import exported

exported.logger.adddtype('timing')

def timeit(func):
    def wrapper(*arg):
        t1 = time.time()
        res = func(*arg)
        t2 = time.time()
        exported.msg('%s took %0.3f ms' % (func.func_name, (t2-t1)*1000.0), 'timing')
        return res
    return wrapper