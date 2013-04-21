#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

import sys

from mokujin.logicalform import MetaphorLF_Reader
from mokujin.triples import TripleExtractor, TripleFold, Triple
from mokujin.triples import ACTUAL_RELS as RELS

_ = """
  __  __  ___  _  ___   _     _ ___ _   _
 |  \/  |/ _ \| |/ / | | |   | |_ _| \ | |
 | |\/| | | | | ' /| | | |_  | || ||  \| |
 | |  | | |_| | . \| |_| | |_| || || |\  |
 |_|  |_|\___/|_|\_\\\\___/ \___/|___|_| \_|

"""


if __name__ == "__main__":

    print _

    if len(sys.argv) > 1:
        ifile = open(sys.argv[1], "r")
        if len(sys.argv) > 2:
            ofile = open(sys.argv[2], "w")
        else:
            ofile = open("%s.triples.csv" % sys.argv[1], "w")
    else:
        ifile = sys.stdin
        ofile = sys.stdout

    reader = MetaphorLF_Reader(ifile)
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
