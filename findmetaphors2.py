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

from itertools import imap
from createlfindex import sent_to_terms
from mokujin.index import SimpleObjectIndex
from mokujin.query import DomainSearchQuery
from mokujin.metaphorsearch import SentenceCrawler
from mokujin.metaphorsearch import SourceTargetSearcher


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--index", default="lfindex", help="LF sentences index directory", type=str)
    parser.add_argument("-o", "--ofile", default="found-metaphors.txt")
    parser.add_argument("-q", "--queryfile", default="resources/example.json", help="Search query file", type=str)
    args = parser.parse_args()
    o_file = open(args.ofile, "w") if args.ofile is not None else sys.stdout

    logging.info("INDEX DIR: %s" % args.index)
    logging.info("OUTPUT: %s" % o_file)
    logging.info("QUERY FILE: %s" % args.queryfile)

    obj_to_terms = sent_to_terms
    obj_to_str = pickle.dumps
    str_to_obj = pickle.loads


    query = DomainSearchQuery.fromstring(open(args.queryfile).read())
    index = SimpleObjectIndex(args.index, obj_to_terms, obj_to_str, str_to_obj)
    index.load_all()

    handled = set()
    term_pairs = []
    for domain in query:
        for target in domain.target_terms:
            for source in domain.source_terms:
                t_s_pair = source + target
                if t_s_pair in handled:
                    continue
                term_pairs.append((source, target))
                handled.add(t_s_pair)
    isentences = imap(lambda p: index.find(query_terms=p), term_pairs)

    searcher = SourceTargetSearcher(query)
    for sent_set in isentences:
        for sent in sent_set:
            matches = searcher.find_dep_matches(sent)
            for match in matches:
                o_file.write(SentenceCrawler.format_output(sent, match))
    o_file.close()
