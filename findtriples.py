#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

"""
This script extracts relations triples from input LF-sentences count their frequencies and outputs
the triples with the frequencies in descending order.

DO NOT TRY TO USE THIS TO EXTRACT SOURCE WORDS
"""

import sys
import logging

from mokujin.logicalform import MetaphorAdpLF_Reader
from mokujin.triples import TripleExtractor, TripleFold, Triple
from mokujin.triples import ACTUAL_RELS as RELS


if __name__ == "__main__":
    
    logging.basicConfig(level=logging.INFO)
    logging.info("PLEASE, DO NOT TRY TO USE THIS SCRIPT TO EXTRACT SOURCE WORDS, USE findsources.py INSTEAD")

    if len(sys.argv) > 1:
        ifile = open(sys.argv[1], "r")
        if len(sys.argv) > 2:
            ofile = open(sys.argv[2], "w")
        else:
            ofile = open("%s.triples.csv" % sys.argv[1], "w")
    else:
        ifile = sys.stdin
        ofile = sys.stdout

    reader = MetaphorAdpLF_Reader(ifile)
    i_sents = reader.i_sentences()

    ex = TripleExtractor(triple_patterns=RELS)
    i_triple_sets = ex.i_extract_triples(i_sents)
    tfold = TripleFold()

    for triples in i_triple_sets:
        tfold.add_triples(triples)

    triples = tfold.i_triples()

    for triple_tuple in triples:
        ofile.write(Triple.to_row(triple_tuple).encode("utf-8"))
        ofile.write("\n")

    ofile.close()
    ifile.close()
