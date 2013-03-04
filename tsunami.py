#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

import sys

from extractors import MetaphorLF_Reader, TripleExtractor, TripleFold
from triples import (
    SubjectTriplePattern,
    DirObjTriplePattern,
    IndirObjTriplePatern,
    AdjTriplePattern,
    AdvTriplePattern,
    VerbGovTriplePattern,
)


if __name__ == "__main__":


    reader = MetaphorLF_Reader("parsed.txt")

    ex = TripleExtractor(triple_patterns=[
        # SubjectTriplePattern(),
        # DirObjTriplePattern(),
        # IndirObjTriplePatern(),
        # AdjTriplePattern(),
        # AdvTriplePattern(),
        VerbGovTriplePattern(),
    ])

    i_sents = reader.i_sentences()

    i_triple_sets = ex.i_extract_triples(i_sents)

    tfold = TripleFold()
    
    for tset in i_triple_sets:
        for t_class, triples in tset:
            tfold.add_triples(t_class, triples)

    result = tfold.i_triples()

    for triple_info in result:
        sys.stdout.write(", ".join([unicode(tf).encode("utf-8")
                                    for tf in triple_info]))
        sys.stdout.write("\n")
