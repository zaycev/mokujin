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
    DepVerb_VerbPrepNoun,
    DepVerb_Verb,
    DepAdj_NounBePrepNoun,
    DepAdj_NounAdj,
    DepAdv_NounVerbAdvPrepNoun,
    DepAdv_VerbNounAdv,
    DepNoun_NounPrep,
    DepNoun_NounNoun,
    DepNoun_NounEqualPrepNoun,
    DepNoun_NounEqualNoun,
    DepNoun_NounPrepNoun,
    DepAny_Compl,
)


if __name__ == "__main__":

    ifile = sys.stdin
    ofile = sys.stdout

    reader = MetaphorLF_Reader(ifile)

    ex = TripleExtractor(triple_patterns=[
        DepVerb_SubjVerbDirobj(),
        DepVerb_SubjVerbIndirobj(),
        DepVerb_SubjVerbInstr(),
        DepVerb_SubjVerb(),
        DepVerb_PrepCompl(),
        DepVerb_VerbPrepNoun(),
        DepVerb_Verb(),
        DepAdj_NounBePrepNoun(),
        DepAdj_NounAdj(),
        DepAdv_NounVerbAdvPrepNoun(),
        DepAdv_VerbNounAdv(),
        DepNoun_NounPrep(),
        DepNoun_NounNoun(),
        DepNoun_NounEqualPrepNoun(),
        DepNoun_NounEqualNoun(),
        DepNoun_NounPrepNoun(),
        DepAny_Compl(),
    ])

    i_sents = reader.i_sentences()

    i_triple_sets = ex.i_extract_triples(i_sents)

    tfold = TripleFold()
    
    for triples in i_triple_sets:
        tfold.add_triples(triples)

    triples = tfold.i_triples()

    for triple_tuple in triples:
        ofile.write(Triple.to_row(triple_tuple).encode("utf-8"))
        ofile.stdout.write("\n")

    ifile.close()
    ofile.close()