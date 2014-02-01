#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Loic Jaquemet loic.jaquemet+python@gmail.com
#

import logging
import numbers
import sys

from haystack import utils
from haystack import constraints
from haystack.utils import get_subtype
from haystack.outputters import Outputter

__author__ = "Loic Jaquemet"
__copyright__ = "Copyright (C) 2012 Loic Jaquemet"
__email__ = "loic.jaquemet+python@gmail.com"
__license__ = "GPL"
__maintainer__ = "Loic Jaquemet"
__status__ = "Production"

log = logging.getLogger('python')

class PythonOutputter(Outputter): 
    """ Parse a ctypes structure and outputs a pure python object."""

    def parse(self, obj, prefix='', depth=50): 
        """ 
        Returns a Plain Old python object as a perfect copy of this ctypes object.
        array would be lists, pointers, inner structures, and circular 
        reference should be handled nicely.
        """
        import ctypes
        # get self class.
        try:
            my_class = getattr(sys.modules[obj.__class__.__module__],"%s_py"%(obj.__class__.__name__) )
        except AttributeError as e:
            log.warning('did you forget to register your python structures ?')
            raise
        my_self = my_class()
        my_address = ctypes.addressof(obj)
        # keep ref of the POPO too.
        if self.mappings.hasRef(my_class, my_address):
            return self.mappings.getRef(my_class, my_address)
        # save our POPO in a partially resolved state, to keep from loops.
        self.mappings.keepRef(my_self, my_class, my_address)
        for field,typ in obj.getFields():
            attr = getattr(obj, field)
            try:
                member = self._attrToPyObject(attr,field,typ)
            except NameError as e:
                raise NameError('%s %s\n%s'%(field,typ,e))

            setattr(my_self, field, member)
        # save the original type (me) and the field
        setattr(my_self, '_ctype_', type(obj))
        return my_self
        
    def _attrToPyObject(self, attr, field, attrtype):
        import ctypes
        if ctypes.is_basic_type(attrtype):
            if ctypes.is_basic_ctype(type(attr)):
                obj = attr.value
            else:
                obj = attr
        elif ctypes.is_struct_type(attrtype) or ctypes.is_union_type(attrtype):
            attr._mappings_ = self.mappings
            obj = self.parse(attr)
        elif ctypes.is_array_of_basic_type(attrtype):
            # return a list of int, float, or a char[] to str
            obj = utils.ctypes_to_python_array(attr)
        elif ctypes.is_array_type(attrtype): 
            ## array of something else than int/byte
            obj = []
            eltyp = type(attr[0])
            for i in range(0,len(attr)):
                obj.append(self._attrToPyObject( attr[i], i, eltyp) )
        elif ctypes.is_cstring_type(attrtype):
            obj = self.mappings.getRef(ctypes.CString, utils.get_pointee_address(attr.ptr))
        elif ctypes.is_function_type(attrtype):
            obj = repr(attr)
        elif ctypes.is_pointer_type(attrtype):
            # get the cached Value of the LP.
            _subtype = get_subtype(attrtype)
            _address = utils.get_pointee_address(attr)
            if _address == 0:
                # Null pointer
                obj = None
            elif ctypes.is_pointer_to_void_type(attrtype):
                # TODO: make a prototype for c_void_p loading
                # void types a rereturned as None
                obj = None 
            elif ctypes.is_array_of_basic_type(attrtype):
                log.error('basic Type array - %s'%(field))
                obj = 'BasicType array'
            else:
                # get the cached Value of the LP.
                _subtype = get_subtype(attrtype)
                cache = self.mappings.getRef(_subtype, _address)
                if cache is not None: # struct, union...
                    obj = self._attrToPyObject(cache, field, _subtype )
                else:
                    # you got here because your pointer is not loaded:
                    #  did you ignore it in expectedValues ?
                    #  is it in the middle of a struct ? 
                    #  is that a linked list ?
                    #  is it a invalid instance ?
                    log.debug('Pointer for field:%s %s/%s not in cache '
                              '0x%x'%(field, attrtype, get_subtype(attrtype), 
                                    _address))
                    return (None,None)
        elif isinstance(attr, numbers.Number): 
            # case for int, long. But needs to be after c_void_p pointers case
            obj = attr
        else:
            log.error('toPyObj default to return attr %s'%( type(attr) ))
            obj = attr
        return obj

def json_encode_pyobj(obj):
    if hasattr(obj, '_ctype_'):
        return obj.__dict__
    elif type(obj).__name__ == 'int':
        log.warning('found an int')
        return str(obj)
    else:
        return obj
        
class pyObj(object):
    """ 
    Base class for a plain old python object.
    all haystack/ctypes classes will be translated in this format before pickling.
    
    Operations :
        - toString(self, prefix):    print a nicely formatted data structure
                :param prefix: str to insert before each line (\t after that)
        - findCtypes(self) : checks if a ctypes is to be found somewhere is the object.
                                            Useful to check if the object can be pickled.
    """
    def toString(self, prefix='',maxDepth=10):
        if maxDepth < 0:
            return '#(- not printed by Excessive recursion - )'
        s='{\n'
        if hasattr(self, '_ctype_'):
            items = [n for n,t in self._ctype_.getFields()]
        else:
            log.warning('no _ctype_')
            items = [n for n in self.__dict__.keys() if n != '_ctype_']
        for attrname in items:
            attr = getattr(self, attrname)
            typ = type(attr)
            s += "%s%s: %s\n"%( prefix, attrname, self._attrToString(attr, attrname, typ, prefix+'\t', maxDepth=maxDepth-1) )
        s+='}'
        return s

    def _attrToString(self, attr, attrname, typ, prefix, maxDepth):
        s=''
        if type(attr) is tuple or type(attr) is list:
            for i in xrange(0,len(attr)):
                s += '%s,'%(self._attrToString(attr[i], i ,None, prefix+'\t', maxDepth) )
            s = "[%s],"%(s)
        elif not hasattr(attr,'__dict__'):
            s = '%s,'%( repr(attr) )
        elif isinstance( attr , pyObj):
            s = '%s,'%( attr.toString(prefix,maxDepth) )
        else:
            s = '%s,'%(repr(attr) )
        return s

    def __len__(self):
        return self._len_
        
    def findCtypes(self, cache=set()):
        """ recurse on members to check for ctypes object. """
        ret = False
        for attrname,attr in self.__dict__.items():
            if id(attr) in cache: # do not recurse in already parsed
                continue
            if attrname == '_ctype_' : # ignore _ctype_, it's a ctype class type, we know that.
                cache.add(id(attr))
                continue
            typ = type(attr)
            attr = getattr(self, attrname)
            log.debug('findCtypes on attr %s'% attrname)
            if self._attrFindCtypes(attr, attrname, typ, cache ):
                log.warning('Found a ctypes in %s'%(attrname))
                ret = True
        return ret

    def _attrFindCtypes(self, attr, attrname, typ, cache):
        import ctypes
        ret = False
        cache.add(id(attr))
        if hasattr(attr, '_ctype_'): # a pyobj
            return attr.findCtypes(cache)
        elif type(attr) is tuple or type(attr) is list:
            for el in attr:
                if self._attrFindCtypes(el, 'element', None, cache):
                    log.warning('Found a ctypes in array/tuple')
                    return True
        elif ctypes.is_ctypes_instance(attr):
            log.warning('Found a ctypes in self %s'%(attr))
            return True
        else: # int, long, str ...
            ret = False
        return ret

    def __iter__(self):
        """ iterate on a instance's type's _fields_ members following the original type field order """
        for k,typ in self._ctype_.getFields():
            v = getattr(self,k)
            yield (k,v,typ)
        pass

def findCtypesInPyObj(obj):
    """ check function to help in unpickling errors correction """
    import ctypes
    ret = False
    if hasattr(obj, 'findCtypes'):
        if obj.findCtypes():
            log.warning('Found a ctypes in array/tuple')
            return True
    elif type(obj) is tuple or type(obj) is list:
        for el in obj:
            if findCtypesInPyObj(el):
                log.warning('Found a ctypes in array/tuple')
                return True
    elif ctypes.is_ctypes_instance(obj):
        return True
    return False


