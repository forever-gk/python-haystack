#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for haystack.reverse.structure."""

from __future__ import print_function

import logging
import sys
import unittest

from haystack.allocators.win32 import win7heapwalker
from haystack.mappings import folder
from test.testfiles import putty_1_win7

log = logging.getLogger('testwin7walker')


class TestWin7HeapWalker(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # putty 1 was done under win7 32 bits ?
        cls._memory_handler = folder.load(putty_1_win7.dumpname)
        return

    @classmethod
    def tearDownClass(cls):
        cls._memory_handler.reset_mappings()
        cls._memory_handler = None
        return

    def setUp(self):
        self._heap_finder = self._memory_handler.get_heap_finder()
        return

    def tearDown(self):
        self._heap_finder = None
        return

    @unittest.expectedFailure #("we are still not good at counting free space")
    def test_freelists(self):
        """ List all free blocks """

        # FIXME: the sum calculation is per segment, not per mapping.

        self.assertNotEqual(self._memory_handler, None)
        # test the heaps
        walkers = self._heap_finder.list_heap_walkers()
        heap_sums = dict([(walker.get_heap_mapping(), list()) for walker in walkers])
        child_heaps = dict()
        for heap_walker in walkers:
            heap_addr = heap_walker.get_heap_address()
            heap = heap_walker.get_heap_mapping()
            log.debug(
                '==== walking heap num: %0.2d @ %0.8x',
                heap_walker.get_heap().ProcessHeapsListIndex, heap_addr)
            walker = self._heap_finder.get_heap_walker(heap)
            for x, s in walker._get_freelists():
                m = self._memory_handler.get_mapping_for_address(x)
                # Found new mmap outside of heaps mmaps
                if m not in heap_sums:
                    heap_sums[m] = []
                heap_sums[m].append((x, s))
            #self.assertEqual( free_size, walker.HEAP().TotalFreeSize)
            # save mmap hierarchy
            child_heaps[heap] = walker.list_used_mappings()

        # calcul cumulates
        for heap, children in child_heaps.items():
            # for each heap, look at all children
            freeblocks = map(lambda x: x[0], heap_sums[heap])
            free_size = sum(map(lambda x: x[1], heap_sums[heap]))
            finder = win7heapwalker.Win7HeapFinder(self._memory_handler)
            walker = finder.get_heap_walker(heap)
            cheap = walker.get_heap()
            log.debug('-- heap 0x%0.8x   free:%0.5x  expected: %0.5x', heap.start, free_size, cheap.TotalFreeSize)
            total = free_size
            for child in children:
                freeblocks = map(lambda x: x[0], heap_sums[child])
                self.assertEqual(len(freeblocks), len(set(freeblocks)))
                # print heap_sums[child]
                free_size = sum(map(lambda x: x[1], heap_sums[child]))
                log.debug('     \_ mmap 0x%0.8x   free:%0.5x ', child.start, free_size)
                self.assertEqual(len(freeblocks), len(set(freeblocks)))
                total += free_size
            log.debug('     \= total: free:%0.5x ', total)

            maxlen = len(heap)
            cheap = walker.get_heap()
            log.debug('heap: 0x%0.8x free: %0.5x  expected: %0.5x  mmap len:%0.5x',
                      heap.start, total, cheap.TotalFreeSize, maxlen)
            # if cheap.FrontEndHeapType == 0:
            blocksize = walker.get_target_platform().get_word_size() * 2
            # ??
            self.assertEqual(cheap.TotalFreeSize * blocksize, total)
            # print hex(heap.start), cheap.TotalFreeSize * blocksize == total, cheap.TotalFreeSize * blocksize, total
            # else:
            #    # FIXME
            #    log.warning('we are not good ar handling 64 b heaps :FH,. backend')

        return

    def test_sorted_heaps(self):
        """ check if memory_mapping gives heaps sorted by index. """
        # self.skipTest('known_ok')
        finder = win7heapwalker.Win7HeapFinder(self._memory_handler)
        walkers = finder.list_heap_walkers()
        self.assertEqual(len(walkers), len(putty_1_win7.known_heaps))
        last = 0
        for i, walker in enumerate(walkers):
            this = walker.get_heap_address()
            self.assertLess(last, this, "Heaps are ordered by base address")
            last = this
        return

    @unittest.expectedFailure #really, refactor this LFH TU. X32 and X64 have different expectation in flags.
    def test_get_frontendheap(self):
        finder = win7heapwalker.Win7HeapFinder(self._memory_handler)
        # heap = self._memory_handler.get_mapping_for_address(0x00390000)
        # for heap in finder.get_heap_mappings():
        for heap in [self._memory_handler.get_mapping_for_address(0x005c0000)]:
            allocs = list()
            walker = finder.get_heap_walker(heap)
            # helper
            win7heap = walker._heap_module
            heap_children = walker.list_used_mappings()
            committed, free = walker._get_frontend_chunks()
            # page 37
            # each UserBlock contain a 8 byte header ( first 4 encoded )
            #                                and then n-bytes of user data
            #
            # (in a free chunk)
            # the user data's first two bytes hold the next free chunk offset
            # UserBlocks + 8*NextOffset
            #     Its basically a forward pointer, offset.
            #
            # commited frontend chunks should have a flag at 0x5
            # previous chunk is at - 8*Chunk.SegmentOffset
            for chunk_addr, chunk_size in committed:
                self.assertGreaterEqual(chunk_size, 0x8, 'too small chunk_addr == 0x%0.8x' % chunk_addr)
                m = self._memory_handler.get_mapping_for_address(chunk_addr)
                if m != heap:
                    self.assertIn(m, heap_children)
                # should be aligned
                self.assertEqual(chunk_addr & 7, 0)  # page 40
                st = m.read_struct(chunk_addr, win7heap.HEAP_ENTRY) # HEAP_ENTRY
                # st.UnusedBytes == 0x5    ?
                if st._0._1.UnusedBytes == 0x05:
                    prev_header_addr -= 8 * st._0._1._0.SegmentOffset
                    log.debug('UnusedBytes == 0x5, SegmentOffset == %d' % st._0._1._0.SegmentOffset)

                # FIXME, in child of 0x005c0000. LFH. What are the flags already ?
                print(hex(chunk_addr))
                self.assertTrue(st._0._1.UnusedBytes & 0x80, 'UnusedBytes said this is a BACKEND chunk , Flags | 2')
                allocs.append((chunk_addr, chunk_size))  # with header

            # FIXME - UNITTEST- you need to validate that NextOffset in
            # userblock gives same answer
            oracle = committed[0]  # TODO
            for chunk_addr, chunk_size in committed:
                m = self._memory_handler.get_mapping_for_address(chunk_addr)
                if m != heap:
                    self.assertIn(m, heap_children)
                # should be aligned
                self.assertEqual(chunk_addr & 7, 0)  # page 40
                st = m.read_struct(chunk_addr, win7heap.HEAP_ENTRY)
                # NextOffset in userblock gives same answer

            for addr, s in allocs:
                m = self._memory_handler.get_mapping_for_address(addr)
                if addr + s > m.end:
                    self.fail('OVERFLOW @%0.8x-@%0.8x, @%0.8x size:%d end:@%0.8x' % (m.start, m.end, addr, s, addr + s))
        return

    def test_get_chunks(self):
        finder = win7heapwalker.Win7HeapFinder(self._memory_handler)
        # heap = self._memory_handler.get_mapping_for_address(0x00390000)
        # for heap in finder.get_heap_mappings():
        for heap in [self._memory_handler.get_mapping_for_address(0x005c0000)]:
            allocs = list()
            walker = finder.get_heap_walker(heap)
            allocated, free = walker._get_chunks()
            for chunk_addr, chunk_size in allocated:
                # self.assertLess(chunk_size, 0x800) # FIXME ???? sure ?
                self.assertGreaterEqual(
                    chunk_size, 0x8, 'too small chunk_addr == 0x%0.8x size: %d' %
                    (chunk_addr, chunk_size))
                allocs.append((chunk_addr, chunk_size))  # with header

            for addr, s in allocs:
                m = self._memory_handler.get_mapping_for_address(addr)
                if addr + s > m.end:
                    self.fail(
                        'OVERFLOW @%0.8x-@%0.8x, @%0.8x size:%d end:@%0.8x' %
                        (m.start, m.end, addr, s, addr + s))
        return

    def _chunks_in_mapping(self, lst, walker):
        for addr, s in lst:
            m = self._memory_handler.get_mapping_for_address(addr)
            if addr + s > m.end:
                self.fail(
                    'OVERFLOW @%0.8x-@%0.8x, @%0.8x size:%d end:@%0.8x' %
                    (m.start, m.end, addr, s, addr + s))
            ##self.assertEqual(mapping, m)
            # actually valid, if m is a children of mapping
            if m != walker._mapping:
                self.assertIn(m, walker.list_used_mappings())

    # a free chunks size jumps into unknown mmap address space..
    @unittest.expectedFailure
    def test_totalsize(self):
        """ check if there is an adequate allocation rate as per get_user_allocations """
        finder = win7heapwalker.Win7HeapFinder(self._memory_handler)

        #
        # While all allocations over 0xFE00 blocks are handled by VirtualAlloc()/VirtualFree(),
        # all memory management that is greater than 0x800 blocks is handled by the back-end;
        # along with any memory that cannot be serviced by the front-end.

        #

        #self.skipTest('overallocation clearly not working')

        self.assertEqual(self._memory_handler.get_target_system(), 'win32')

        full = list()
        for heap in finder.list_heap_walkers():
            walker = finder.get_heap_walker(heap)
            my_chunks = list()

            vallocs, va_free = walker._get_virtualallocations()
            self._chunks_in_mapping(vallocs, walker)
            vallocsize = sum([c[1] for c in vallocs])

            chunks, free_chunks = walker._get_chunks()
            self._chunks_in_mapping(chunks, walker)
            # Free chunks CAN be OVERFLOWING
            # self._chunks_in_mapping( free_chunks, walker)
            allocsize = sum([c[1] for c in chunks])
            freesize = sum([c[1] for c in free_chunks])

            fth_chunks, fth_free = walker._get_frontend_chunks()
            self._chunks_in_mapping(fth_chunks, walker)
            fth_allocsize = sum([c[1] for c in fth_chunks])

            free_lists = walker._get_freelists()
            # Free chunks CAN be OVERFLOWING
            #self._chunks_in_mapping( free_lists, walker)
            free_listssize = sum([c[1] for c in free_lists])

            my_chunks.extend(vallocs)
            my_chunks.extend(chunks)
            my_chunks.extend(free_chunks)
            my_chunks.extend(fth_chunks)
            my_chunks.extend(free_lists)

            myset = set(my_chunks)
            self.assertEqual(
                len(myset),
                len(my_chunks),
                'NON unique referenced chunks found.')

            full.extend(my_chunks)

        self.assertEqual(len(full), len(set(full)), 'duplicates allocs found')

        addrs = [addr for addr, s in full]
        self.assertEqual(
            len(addrs), len(
                set(addrs)), 'duplicates allocs found but different sizes')

        where = dict()
        for addr, s in full:
            m = self._memory_handler.get_mapping_for_address(addr)
            self.assertTrue(m, '0x%0.8x is not a valid address!' % (addr))
            if m not in where:
                where[m] = []
            if addr + s > m.end:
                log.debug(
                    'OVERFLOW 0x%0.8x-0x%0.8x, 0x%0.8x size: %d end: 0x%0.8x' %
                    (m.start, m.end, addr, s, addr + s))
                m2 = self._memory_handler.get_mapping_for_address(addr + s)
                self.assertTrue(
                    m2, '0x%0.8x is not a valid address 0x%0.8x + 0x%0.8x!' %
                    (addr + s, addr, s))
                if m2 not in where:
                    where[m2] = []
                where[m2].append(
                    (m2.start, s - m.end - addr))  # save second part
                s = m.end - addr  # save first part
            where[m].append((addr, s))

        # calculate allocated size
        for m, allocs in where.items():
            totalsize = sum([s for addr, s in allocs])
            log.debug(
                '@%0.8x size: %0.5x allocated: %0.5x = %0.2f %%' %
                (m.start, len(m), totalsize, 100 * totalsize / len(m)))
            allocs.sort()
            lastend = 0
            lasts = 0
            addsize = 0
            for addr, s in allocs:
                if addr < lastend:
                    # log.debug('0x%0.8x (%d) last:0x%0.8x-0x%0.8x (%d) new:0x%0.8x-0x%0.8x (%d)'%(m.start,
                    # len(m), lastend-lasts,lastend,lasts, addr, addr+s, s) )
                    addsize += s
                # keep last big chunk on the stack before moving to next one.
                else:
                    if addsize != 0:
                        #log.debug('previous fth_chunks cumulated to %d lasts:%d'%(addsize, lasts))
                        addsize = 0
                    lastend = addr + s
                    lasts = s
        # so chunks are englobing fth_chunks
        # _heap.ProcessHeapsListIndex give the order of heaps....
        return

    def test_search(self):
        """    Testing the loading of _HEAP in each memory mapping.
        Compare load_members results with known offsets. expect failures otherwise. """
        finder = win7heapwalker.Win7HeapFinder(self._memory_handler)

        found = []
        for heap_walker in finder.list_heap_walkers():
            validator = heap_walker.get_heap_validator()
            addr = heap_walker.get_heap_address()
            heap = heap_walker.get_heap()
            if addr in map(lambda x: x[0], putty_1_win7.known_heaps):
                self.assertTrue(
                    validator.load_members( heap, 50),
                    "We expected a valid hit at @ 0x%0.8x" %
                    (addr))
                found.append(addr, )
            else:
                try:
                    ret = validator.load_members(heap, 1)
                    self.assertFalse(
                        ret,
                        "We didnt expected a valid hit at @%x" %
                        addr)
                except Exception as e:
                    # should not raise an error
                    self.fail(
                        'Haystack should not raise an Exception. %s' %
                        e)

        found.sort()
        self.assertEqual(list(map(lambda x: x[0], putty_1_win7.known_heaps)), found)

        return

    def test_get_user_allocations(self):
        """ For each known _HEAP, load all user Allocation and compare the number of allocated bytes. """
        finder = win7heapwalker.Win7HeapFinder(self._memory_handler)

        for walker in finder.list_heap_walkers():
            #
            total = 0
            for chunk_addr, chunk_size in walker.get_user_allocations():
                self.assertTrue(chunk_addr in self._memory_handler)
                self.assertGreater(
                    chunk_size,
                    0,
                    'chunk_addr == 0x%0.8x' %
                    (chunk_addr))
                total += chunk_size

        return


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    # logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    logging.getLogger('testwin7walker').setLevel(level=logging.DEBUG)
    unittest.main(verbosity=2)
    # suite = unittest.TestLoader().loadTestsFromTestCase(TestFunctions)
    # unittest.TextTestRunner(verbosity=2).run(suite)
