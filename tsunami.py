#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

import sys

from logicalform import MetaphorLF_Reader
from triples import TripleExtractor, TripleFold, Triple
from triples import (
    DepVerb_SubjVerbDirobj,
    DepVerb_SubjVerbIndirobj,
    DepVerb_SubjVerbInstr,
    DepVerb_SubjVerb,
    DepVerb_PrepCompl,
    DepVerb_SubjVerbVerbPrepNoun,
    DepVerb_SubjVerbVerb,
    # DepAdj_NounBePrepNoun,
    DepAdj_NounAdj,
    DepAdv_NounVerbAdvPrepNoun,
    DepAdv_VerbNounAdv,
    # DepNoun_NounPrep,
    DepNoun_NounNoun,
    DepNoun_NounNounNoun,
    DepNoun_NounEqualPrepNoun,
    DepNoun_NounEqualNoun,
    DepNoun_NounPrepNoun,
    DepAny_Compl,
)


if __name__ == "__main__":


    relations = [
        DepVerb_SubjVerbDirobj(),
        DepVerb_SubjVerbIndirobj(),
        DepVerb_SubjVerbInstr(),
        DepVerb_SubjVerb(),
        DepVerb_PrepCompl(),
        DepVerb_SubjVerbVerbPrepNoun(),
        DepVerb_SubjVerbVerb(),
        DepAdj_NounAdj(),
        DepAdv_VerbNounAdv(),
        DepNoun_NounEqualPrepNoun(),
        DepNoun_NounNoun(),
        DepNoun_NounNounNoun(),
        DepNoun_NounEqualNoun(),
        DepNoun_NounPrepNoun(),
        DepAny_Compl(),
    ]

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

    ex = TripleExtractor(triple_patterns=relations)
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
