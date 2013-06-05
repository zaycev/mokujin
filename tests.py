#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

import random
import unittest

from mokujin import numencode


class TestNumCode(unittest.TestCase):
    """
    Test class for mokujin.numencode module.
    """

    def setUp(self):
        self.seq = range(10)

    def test_delta_codec(self):
        for _ in xrange(4):
            for sz in [0, 1, 10, 100, 1000, 10000, 100000]:
                sorted_sequence = [i + random.randint(0, 2 ** 8 - 1) for i in xrange(sz)]
                sorted_sequence.sort()
                encoded = sorted_sequence[:]
                numencode.delta_encode(encoded)
                decoded = encoded[:]
                numencode.delta_decode(decoded)
                self.assertEqual(sorted_sequence, decoded)

    def test_plist_codec(self):
        for _ in xrange(4):
            for sz in [0, 1, 10, 100, 1000, 10000, 2 ** 16 - 1]:
                tids = [i + random.randint(0, 2 ** 32 - 1) for i in xrange(sz)]
                poss = [random.randint(0, 2 ** 8 - 1) for _ in xrange(sz)]
                tids.sort()
                plist = zip(tids, poss)
                encoded = numencode.encode_plist(plist)
                decoded = numencode.decode_plist(encoded)
                self.assertEqual(decoded, plist)

    def test_plist_update(self):
        for _ in xrange(4):
            for sz in [0, 1, 10, 100, 1000, 10000, 2 ** 16 - 1]:
                tids = [i + random.randint(0, 2 ** 32 - 1) for i in xrange(sz)]
                poss = [random.randint(0, 2 ** 8 - 1) for _ in xrange(sz)]
                tids.sort()
                plist = zip(tids, poss)
                part_1 = plist[:len(plist) / 2]
                part_2 = plist[len(plist) / 2:]
                self.assertEqual(plist, part_1 + part_2)
                part_1_data = numencode.encode_plist(part_1)
                plist_data = numencode.encode_plist(plist)
                part_1_2_data = numencode.update_plist(part_1_data, part_2)
                part_1_2 = numencode.decode_plist(part_1_2_data)
                self.assertEqual(part_1_2_data, plist_data)
                self.assertEqual(part_1_2, plist)
