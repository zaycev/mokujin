#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

import glob
import logging
import argparse
import cPickle as pickle

from mokujin.logicalform import POS
from mokujin.index import SimpleObjectIndex
from mokujin.logicalform import MetaphorAdpLF_Reader


def sent_to_terms(sent):
    for p in sent:
        if p.pos.pos != POS.NONE:
            yield p.lemma.encode("utf-8")

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", default="resources/*.lf.txt", type=str)
    parser.add_argument("-o", "--outdir", default="lfindex", type=str)
    args = parser.parse_args()

    i_files = glob.glob(args.input)
    o_dir = args.outdir

    logging.info("INPUT FILE: %r" % i_files)
    logging.info("OUT DIR: %r" % o_dir)

    obj_to_terms = sent_to_terms
    obj_to_str = pickle.dumps
    str_to_obj = pickle.loads

    index = SimpleObjectIndex(o_dir, obj_to_terms, obj_to_str, str_to_obj)
    index.load_all()
    
    for fl in i_files:
        i_file = open(fl, "r")
        reader = MetaphorAdpLF_Reader(i_file)
        i_sents = reader.i_sentences()
        index.update_index(i_sents)

    logging.info("DONE")
