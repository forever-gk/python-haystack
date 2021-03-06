#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests haystack.types."""

__author__ = "Loic Jaquemet"
__copyright__ = "Copyright (C) 2013 Loic Jaquemet"
__email__ = "loic.jaquemet+python@gmail.com"
__license__ = "GPL"
__maintainer__ = "Loic Jaquemet"
__status__ = "Production"


import logging
import unittest

from haystack import types


def make_types(ctypes):
    # make some allocators.

    class St(ctypes.Structure):
        _fields_ = [('a', ctypes.c_int)]

    class St2(ctypes.Structure):
        _fields_ = [('a', ctypes.c_long)]

    class SubSt2(ctypes.Structure):
        _fields_ = [('a', ctypes.c_longlong)]

    class Union(ctypes.Union):
        _fields_ = [('l', ctypes.c_longlong), ('f', ctypes.c_float)]
    #
    btype = ctypes.c_int
    longt = ctypes.c_long
    voidp = ctypes.c_void_p
    stp = ctypes.POINTER(St)
    stpvoid = ctypes.POINTER(None)
    arra1 = (ctypes.c_long * 4)
    arra2 = (St * 4)
    arra3 = (ctypes.POINTER(St) * 4)
    charp = ctypes.c_char_p
    string = ctypes.CString
    fptr = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_uint)
    arra4 = (fptr * 256)
    double = ctypes.c_longdouble
    arra5 = ctypes.c_ubyte * 8
    arra6 = ctypes.c_char * 32
    ptrUnion = ctypes.POINTER(Union)
    return locals()


class TestReload(unittest.TestCase):

    """Tests sizes after ctypes changes."""

    def setUp(self):
        pass

    # test ctypes._pointer_type_cache
    def test_pointer_type_cache(self):
        """test the comportment of _pointer_type_cache"""
        # between reset(), we keep the reference to the ctypes modules
        # and we don't the pointer cache, that we only share with the default
        # ctypes proxy instance
        ctypes = types.load_ctypes_default()

        class X(ctypes.Structure):
            pass

        self.assertNotIn(X, ctypes._pointer_type_cache.keys())
        ctypes.POINTER(X)
        self.assertIn(X, ctypes._pointer_type_cache.keys())

        # we keep the cache
        self.assertIn(X, ctypes._pointer_type_cache.keys())

        c4 = types.build_ctypes_proxy(4, 4, 8)
        c8 = types.build_ctypes_proxy(8, 8, 16)
        cd = types.load_ctypes_default()
        if c4 != cd:
            newarch = c4
        elif c8 != cd:
            newarch = c4
        else:
            raise RuntimeError("unmanaged case")

        # cd and ctypes share a cache
        self.assertIn(X, cd._pointer_type_cache.keys())
        # and cd.POINTER is actually ctypes.POINTER
        self.assertEqual(cd.POINTER, ctypes.POINTER)
        self.assertEqual(cd._pointer_type_cache, ctypes._pointer_type_cache)

        # but not other proxies
        self.assertNotIn(X, newarch._pointer_type_cache.keys())

        class Y(newarch.Structure):
            pass
        self.assertNotIn(Y, cd._pointer_type_cache.keys())
        self.assertNotIn(Y, ctypes._pointer_type_cache.keys())
        self.assertNotIn(Y, newarch._pointer_type_cache.keys())
        newarch.POINTER(Y)
        self.assertNotIn(Y, cd._pointer_type_cache.keys())
        self.assertNotIn(Y, ctypes._pointer_type_cache.keys())
        self.assertIn(Y, newarch._pointer_type_cache.keys())

        pass

    def test_reset_ctypes(self):
        """Test if reset gives the original types"""
        ctypes = types.build_ctypes_proxy(4, 4, 8)
        for name, value in make_types(ctypes).items():
            globals()[name] = value
        self.assertEqual(ctypes.sizeof(stp), 4)
        self.assertEqual(ctypes.sizeof(arra1), 4 * 4)

        import ctypes
        # no CString.
        self.assertRaises(AttributeError, make_types, ctypes)
        self.assertIn('ctypes', '%s' % (ctypes))
        self.assertFalse(hasattr(ctypes, 'proxy'))
        return

    def test_load_ctypes_default(self):
        """Test if the default proxy works"""
        ctypes = types.build_ctypes_proxy(4, 4, 8)
        self.assertTrue(ctypes.proxy)
        # test
        ctypes = types.load_ctypes_default()
        self.assertTrue(ctypes.proxy)
        for name, value in make_types(ctypes).items():
            globals()[name] = value
        # default ctypes should be similar to host ctypes.
        self.assertEqual(
            ctypes.sizeof(arra1),
            4 *
            ctypes.sizeof(
                ctypes.get_real_ctypes_member('c_long')))
        self.assertEqual(
            ctypes.sizeof(stp),
            ctypes.sizeof(
                ctypes.get_real_ctypes_member('c_void_p')))
        self.assertEqual(
            ctypes.sizeof(arra1),
            4 *
            ctypes.sizeof(
                ctypes.c_long))
        self.assertEqual(ctypes.sizeof(stp), ctypes.sizeof(ctypes.c_void_p))
        return

    def test_reload_ctypes(self):
        """Tests loading of specific arch ctypes."""
        ctypes = types.build_ctypes_proxy(4, 4, 8)
        for name, value in make_types(ctypes).items():
            globals()[name] = value
        self.assertTrue(ctypes.proxy)
        self.assertEqual(ctypes.sizeof(arra1), 4 * 4)
        self.assertEqual(ctypes.sizeof(stp), 4)
        self.assertEqual(ctypes.sizeof(double), 8)

        # other arch
        ctypes = types.build_ctypes_proxy(4, 8, 8)
        for name, value in make_types(ctypes).items():
            globals()[name] = value
        self.assertTrue(ctypes.proxy)
        self.assertEqual(ctypes.sizeof(arra1), 4 * 4)
        self.assertEqual(ctypes.sizeof(stp), 8)
        self.assertEqual(ctypes.sizeof(double), 8)

        # other arch
        ctypes = types.build_ctypes_proxy(8, 4, 8)
        for name, value in make_types(ctypes).items():
            globals()[name] = value
        self.assertTrue(ctypes.proxy)
        self.assertEqual(ctypes.sizeof(arra1), 4 * 8)
        self.assertEqual(ctypes.sizeof(stp), 4)
        self.assertEqual(ctypes.sizeof(double), 8)

        # other arch
        ctypes = types.build_ctypes_proxy(8, 4, 16)
        for name, value in make_types(ctypes).items():
            globals()[name] = value
        self.assertTrue(ctypes.proxy)
        self.assertEqual(ctypes.sizeof(arra1), 4 * 8)
        self.assertEqual(ctypes.sizeof(stp), 4)
        self.assertEqual(ctypes.sizeof(double), 16)

        # other arch
        self.assertRaises(NotImplementedError, types.build_ctypes_proxy, 16, 8, 16)
        return

    def test_set_ctypes(self):
        """Test reloading of previous defined arch-ctypes."""
        x32 = types.build_ctypes_proxy(4, 4, 8)
        x64 = types.build_ctypes_proxy(8, 8, 16)
        win = types.build_ctypes_proxy(8, 8, 8)
        ctypes = types.load_ctypes_default()

        ctypes = x32
        for name, value in make_types(ctypes).items():
            globals()[name] = value
        self.assertTrue(ctypes.proxy)
        self.assertEqual(ctypes, x32)
        self.assertEqual(ctypes.sizeof(arra1), 4 * 4)
        self.assertEqual(ctypes.sizeof(stp), 4)
        self.assertEqual(ctypes.sizeof(double), 8)

        ctypes = x64
        for name, value in make_types(ctypes).items():
            globals()[name] = value
        self.assertTrue(ctypes.proxy)
        self.assertEqual(ctypes, x64)
        self.assertEqual(ctypes.sizeof(arra1), 4 * 8)
        self.assertEqual(ctypes.sizeof(stp), 8)
        self.assertEqual(ctypes.sizeof(double), 16)

        ctypes = win
        for name, value in make_types(ctypes).items():
            globals()[name] = value
        self.assertTrue(ctypes.proxy)
        self.assertEqual(ctypes, win)
        self.assertEqual(ctypes.sizeof(arra1), 4 * 8)
        self.assertEqual(ctypes.sizeof(stp), 8)
        self.assertEqual(ctypes.sizeof(double), 8)

        ctypes = x32
        for name, value in make_types(ctypes).items():
            globals()[name] = value
        self.assertTrue(ctypes.proxy)
        self.assertEqual(ctypes, x32)
        self.assertEqual(ctypes.sizeof(arra1), 4 * 4)
        self.assertEqual(ctypes.sizeof(stp), 4)
        self.assertEqual(ctypes.sizeof(double), 8)

        return


class TestBasicFunctions(unittest.TestCase):

    """Tests basic haystack.types functions on base types."""

    def setUp(self):
        ctypes = types.load_ctypes_default()
        for name, value in make_types(ctypes).items():
            globals()[name] = value
        self.tests = [St, St2, SubSt2, btype, longt, voidp, stp, stpvoid, arra1,
                      arra2, arra3, charp, string, fptr, arra4, double, arra5,
                      arra6, Union, ptrUnion]

    def _testMe(self, fn, valids, invalids):
        for var in valids:
            self.assertTrue(fn(var), var)
        for var in invalids:
            self.assertFalse(fn(var), var)

    def test_is_basic_type(self):
        self.assertTrue(ctypes.c_uint)  # TODO FIXME
        valids = [btype, longt, double]
        invalids = [v for v in self.tests if v not in valids]
        self._testMe(ctypes.is_basic_type, valids, invalids)
        return

    def test_is_struct_type(self):
        valids = [St, St2, SubSt2]
        invalids = [v for v in self.tests if v not in valids]
        self._testMe(ctypes.is_struct_type, valids, invalids)
        return

    def test_is_union_type(self):
        valids = [Union]
        invalids = [v for v in self.tests if v not in valids]
        self._testMe(ctypes.is_union_type, valids, invalids)
        return

    def test_is_pointer_type(self):
        valids = [voidp, stp, stpvoid, fptr, charp, string, ptrUnion]
        invalids = [v for v in self.tests if v not in valids]
        self._testMe(ctypes.is_pointer_type, valids, invalids)
        return

    def test_is_pointer_to_struct_type(self):
        valids = [stp]
        invalids = [v for v in self.tests if v not in valids]
        self._testMe(ctypes.is_pointer_to_struct_type, valids, invalids)
        return

    def test_is_pointer_to_union_type(self):
        valids = [ptrUnion]
        invalids = [v for v in self.tests if v not in valids]
        self._testMe(ctypes.is_pointer_to_union_type, valids, invalids)
        return

    def test_is_pointer_to_void_type(self):
        valids = [voidp, stpvoid, charp]
        invalids = [v for v in self.tests if v not in valids]
        self._testMe(ctypes.is_pointer_to_void_type, valids, invalids)
        return

    def test_is_function_type(self):
        valids = [fptr]
        invalids = [v for v in self.tests if v not in valids]
        self._testMe(ctypes.is_function_type, valids, invalids)
        return

    def test_is_array_of_basic_instance(self):
        valids = [arra1(), arra5(), arra6()]
        invalids = [v for v in self.tests if v not in valids]
        # we need instances to be invalid
        invalids.extend([arra2(), arra3(), arra4(), ])
        for var in valids:
            self.assertTrue(ctypes.is_array_of_basic_instance(var), var)
        for var in invalids:
            self.assertFalse(ctypes.is_array_of_basic_instance(var), var)
        return

    def test_is_array_of_basic_type(self):
        valids = [arra1, arra5, arra6]
        invalids = [v for v in self.tests if v not in valids]
        for var in valids:
            self.assertTrue(ctypes.is_array_of_basic_type(var), var)
        for var in invalids:
            self.assertFalse(ctypes.is_array_of_basic_type(var), var)
        return

    def test_is_array_type(self):
        valids = [arra1, arra2, arra3, arra4, arra5, arra6]
        invalids = [v for v in self.tests if v not in valids]
        self._testMe(ctypes.is_array_type, valids, invalids)
        return

    def test_is_cstring_type(self):
        valids = [string]
        invalids = [v for v in self.tests if v not in valids]
        self._testMe(ctypes.is_cstring_type, valids, invalids)
        return

    def test_is_ctypes(self):
        valids = [St(), St2(), SubSt2()]
        invalids = [v for v in self.tests if v not in valids]
        self._testMe(types.is_ctypes_instance, valids, invalids)
        return


class TestProxyCTypesAPI(unittest.TestCase):

    """Tests that the ctypes API is respected."""

    def setUp(self):
        ctypes = types.load_ctypes_default()
        for name, value in make_types(ctypes).items():
            globals()[name] = value
        self.tests = [St, St2, SubSt2, btype, longt, voidp, stp, stpvoid, arra1,
                      arra2, arra3, charp, string, fptr, arra4, double, arra5,
                      arra6, Union, ptrUnion]

    def test_import(self):
        #''' Do not replace c_char_p '''
        ctypes = types.load_ctypes_default()
        from haystack import basicmodel
        self.assertEqual(
            ctypes.c_char_p.__name__,
            'c_char_p',
            'c_char_p should not be changed')
        self.assertFalse(
            issubclass(
                ctypes.Structure,
                basicmodel.CTypesRecordConstraintValidator))
        self.assertFalse(issubclass(ctypes.Union, basicmodel.CTypesRecordConstraintValidator))
        self.assertIn(ctypes.CString, ctypes.__dict__.values())

    def test_cast(self):
        ctypes = types.load_ctypes_default()
        i = ctypes.c_int(42)
        a = ctypes.c_void_p(ctypes.addressof(i))
        p = ctypes.cast(a, ctypes.POINTER(ctypes.c_int))
        # ctypes is 32bits, local is 64, pointer is 64 bytes
        # pointer value is truncated.
        # why is ctypes 32 bites in the first place ? because its called
        # in the 32 bits unit test class that inherits this one
        if ctypes.sizeof(ctypes.c_void_p) != ctypes.sizeof(
                ctypes.get_real_ctypes_member("c_void_p")):
            self.skipTest('cant cast memory pointer cross platform')
        self.assertEqual(ctypes.addressof(i), a.value)
        self.assertEqual(ctypes.addressof(i), ctypes.addressof(p.contents))

        i = St()
        a = ctypes.c_void_p(ctypes.addressof(i))
        p = ctypes.cast(a, stp)
        self.assertEqual(ctypes.addressof(i), a.value)
        self.assertEqual(ctypes.addressof(i), ctypes.addressof(p.contents))
        # print fptr
        #x = fptr
        # print ctypes.is_pointer_type(fptr)
        # print ctypes.is_function_type(fptr)
        # print ctypes.POINTER(ctypes.c_int).__bases__
        # print ctypes._cfuncptrt
        # print ctypes._ptrt
        # print
        #import code
        # code.interact(local=locals())

    def test_cfunctype(self):
        #verify this is our proxy module
        self.assertTrue(hasattr(ctypes,'get_real_ctypes_member'))
        self.assertTrue(hasattr(ctypes,'CFUNCTYPE'))
        self.assertEqual(ctypes.get_real_ctypes_member('CFUNCTYPE'),
                          ctypes.CFUNCTYPE)


class TestBasicFunctions32(TestBasicFunctions):

    """Tests basic haystack.utils functions on base types for x32 arch."""

    def setUp(self):
        """Have to reload that at every test. classmethod will not work"""
        # use the host ctypes with modif
        ctypes = types.build_ctypes_proxy(4, 4, 8)
        self.assertTrue(ctypes.proxy)
        self._ctypes = ctypes
        for name, value in make_types(self._ctypes).items():
            globals()[name] = value
        # reload test list after globals have been changed
        self.tests = [St, St2, SubSt2, btype, longt, voidp, stp, stpvoid, arra1,
                      arra2, arra3, charp, string, fptr, arra4, double, arra5,
                      arra6, Union, ptrUnion]

    def test_sizes(self):
        self.assertEqual(self._ctypes.sizeof(self._ctypes.c_long), 4)
        self.assertEqual(self._ctypes.sizeof(self._ctypes.c_void_p), 4)
        self.assertEqual(self._ctypes.sizeof(self._ctypes.POINTER(self._ctypes.c_int)), 4)
        self.assertEqual(self._ctypes.sizeof(self._ctypes.c_char_p), 4)
        self.assertEqual(self._ctypes.sizeof(self._ctypes.c_wchar_p), 4)
        self.assertEqual(self._ctypes.sizeof(arra1), 4 * 4)
        self.assertEqual(self._ctypes.sizeof(double), 8)
        self.assertEqual(self._ctypes.sizeof(fptr), 4)

        return

    def test_import(self):
        from haystack import basicmodel
        self.assertFalse(
            issubclass(
                self._ctypes.Structure,
                basicmodel.CTypesRecordConstraintValidator))
        self.assertFalse(issubclass(self._ctypes.Union, basicmodel.CTypesRecordConstraintValidator))
        self.assertIn(self._ctypes.CString, self._ctypes.__dict__.values())


class TestBasicFunctionsWin(TestBasicFunctions):

    """Tests basic haystack.utils functions on base types for x64 arch."""

    def setUp(self):
        """Have to reload that at every test. classmethod will not work"""
        # use the host self._ctypes with modif
        ctypes = types.build_ctypes_proxy(8, 8, 8)
        self.assertTrue(ctypes.proxy)
        self._ctypes = ctypes
        for name, value in make_types(ctypes).items():
            globals()[name] = value
        #
        self.tests = [St, St2, SubSt2, btype, longt, voidp, stp, stpvoid, arra1,
                      arra2, arra3, charp, string, fptr, arra4, double, arra5,
                      arra6, Union, ptrUnion]

    def test_sizes(self):
        self.assertEqual(self._ctypes.sizeof(self._ctypes.c_long), 8)
        self.assertEqual(self._ctypes.sizeof(self._ctypes.c_void_p), 8)
        self.assertEqual(self._ctypes.sizeof(self._ctypes.c_char_p), 8)
        self.assertEqual(self._ctypes.sizeof(self._ctypes.c_wchar_p), 8)
        self.assertEqual(self._ctypes.sizeof(arra1), 4 * 8)
        self.assertEqual(self._ctypes.sizeof(double), 8)
        self.assertEqual(self._ctypes.sizeof(fptr), 8)
        return

    def test_import(self):
        from haystack import basicmodel
        self.assertFalse(
            issubclass(
                self._ctypes.Structure,
                basicmodel.CTypesRecordConstraintValidator))
        self.assertFalse(issubclass(self._ctypes.Union, basicmodel.CTypesRecordConstraintValidator))
        self.assertIn(self._ctypes.CString, self._ctypes.__dict__.values())


class TestBasicFunctions64(TestBasicFunctions):

    """Tests basic haystack.utils functions on base types for x64 arch."""

    def setUp(self):
        """Have to reload that at every test. classmethod will not work"""
        # use the host ctypes with modif
        ctypes = types.build_ctypes_proxy(8, 8, 16)
        self.assertTrue(ctypes.proxy)
        self._ctypes = ctypes
        for name, value in make_types(ctypes).items():
            globals()[name] = value
        #
        self.tests = [St, St2, SubSt2, btype, longt, voidp, stp, stpvoid, arra1,
                      arra2, arra3, charp, string, fptr, arra4, double, arra5,
                      arra6, Union, ptrUnion]

    def test_sizes(self):
        self.assertEqual(self._ctypes.sizeof(self._ctypes.c_long), 8)
        self.assertEqual(self._ctypes.sizeof(self._ctypes.c_void_p), 8)
        self.assertEqual(self._ctypes.sizeof(self._ctypes.c_char_p), 8)
        self.assertEqual(self._ctypes.sizeof(self._ctypes.c_wchar_p), 8)
        self.assertEqual(self._ctypes.sizeof(arra1), 4 * 8)
        self.assertEqual(self._ctypes.sizeof(double), 16)
        self.assertEqual(self._ctypes.sizeof(fptr), 8)
        return

    def test_import(self):
        from haystack import basicmodel
        self.assertFalse(
            issubclass(
                self._ctypes.Structure,
                basicmodel.CTypesRecordConstraintValidator))
        self.assertFalse(issubclass(self._ctypes.Union, basicmodel.CTypesRecordConstraintValidator))
        self.assertIn(self._ctypes.CString, self._ctypes.__dict__.values())


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    unittest.main(verbosity=2)
