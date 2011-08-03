from collections import UserDict

class AttrDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    __init__ = dict.__init__

def gen_cmd_line(args):
    return ' '.join([(' ' in x or x == "") and \
                     ('"{0}"'.format(x)) or x for x in args])
