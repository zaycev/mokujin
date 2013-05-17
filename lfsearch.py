#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE


import sys
import logging
import argparse
import cPickle as pickle


from mokujin.index import SimpleObjectIndex
from createlfindex import sent_to_terms


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputdir", default="lfindex", type=str)
    parser.add_argument("-o", "--output", default=None, type=str)
    parser.add_argument("-q", "--query", default=None, type=str)
    args = parser.parse_args()

    i_dir = args.inputdir
    o_file = open(args.output, "w") if args.output is not None else sys.stdout
    query_term = args.query
    
    logging.info("INPUT DIR: %r" % i_dir)
    logging.info("OUT FILE: %r" % o_file)
    logging.info("QUERY: %s" % query_term)

    obj_to_terms = sent_to_terms
    obj_to_str = pickle.dumps
    str_to_obj = pickle.loads

    index = SimpleObjectIndex(i_dir, obj_to_terms, obj_to_str, str_to_obj)
    index.load_all()
    results = index.find(query_term=query_term)

    o_file.write("FOUND (%d):\n" % len(results))
    for sent in results:
        o_file.write(sent.raw_text.encode("utf-8"))
        o_file.write("\n")