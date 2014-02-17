#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

"""
Simple dictionary lookup script.
Finds given word in mokujin dictionary and returns its id.

Usage:
    $ python lookupdict.py <path_to_index> <word>
"""

import sys
import logging
import argparse

from mokujin.index import DepTupleIndex


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    try:
        _, index_path, term = sys.argv
    except:
        logging.error("Wrong syntax. Usage:\n\t lookupdict.py <path_to_index> <word>")
        exit(0)

    indexer = DepTupleIndex(index_path)

    term_id = indexer.term2id.get(term)

    if term_id is not None:
        sys.stdout.write("\n\tFound term '%s' with id=%d\n\n" % (term, term_id))
    else:
        sys.stedout.write("\n\tTerm '%s' not found in dictionary.\n\n" % term)

