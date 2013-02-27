#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

import sys

from extractors import MetaphorLF_Reader, TripleExtractor, TripleFold
from triples import SubjectTriplePattern


if __name__ == "__main__":


    reader = MetaphorLF_Reader("parsed.txt")

    ex = TripleExtractor(triple_patterns=[
        SubjectTriplePattern(),
    ])

    i_sents = reader.i_sentences()

    i_triple_sets = ex.i_extract_triples(i_sents)

    tfold = TripleFold()

    for t_set in i_triple_sets:
        tfold.add_triples(t_set)

    result = tfold.i_triples()

    for triple_info in result:
        sys.stdout.write(", ".join([unicode(tf).encode("utf-8")
                                    for tf in triple_info]))
        sys.stdout.write("\n")
