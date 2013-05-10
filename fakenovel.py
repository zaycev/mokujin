#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

# Usage
#
#
#

import csv
import sys
import logging
import argparse

from mokujin.index import ID_REL_MAP
from mokujin.index import TripleIndex
from mokujin.index import SearchEngine
from mokujin.query import MetaphoricQuery
from mokujin.novel import MetaphorExplorer
from mokujin.misc import transliterate_ru

FILES = dict()


def load_stop_terms(file_path, threshold=500.0):
    stop_terms_set = set()
    try:
        with open(file_path, "rb") as csvfile:
            stop_terms = csv.reader(csvfile, delimiter=",")
            for rank, freq, lemma, pos in stop_terms:
                freq = float(freq)
                if freq >= threshold:
                    stop_terms_set.add(lemma)
                else:
                    break
    except IOError:
        pass
    logging.info("LOADED %d STOP WORDS" % len(stop_terms_set))
    return stop_terms_set


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)



    parser = argparse.ArgumentParser()

    parser.add_argument("-d", "--data", default="data/index", help="Mokujin data dir directory", type=str)
    parser.add_argument("-o", "--outputdir", default="output",
                        help="Directory where fake novel source words willbe placed",  type=str)
    parser.add_argument("-q", "--queryfile", default="query.json", help="Search query file", type=str)
    parser.add_argument("-s", "--stopterms", default="light_words_ru.csv", help="Path to the file with stop words",
                        type=str)
    parser.add_argument("-t1", "--threshold1", default=500, help="Max frequecy treshold for light words", type=float)
    parser.add_argument("-t2", "--threshold2", default=5, help="Min frequecy treshold for seed triples", type=float)

    args = parser.parse_args()

    logging.info("DATA DIR: %s" % args.data)
    logging.info("OUT DIR: %s" % args.outputdir)
    logging.info("QUERY FILE: %s" % args.queryfile)
    logging.info("STOP TERMS: %s" % args.stopterms)
    logging.info("T1: %f" % args.threshold1)
    logging.info("T2: %f" % args.threshold2)

    stop_terms = load_stop_terms(args.stopterms, threshold=args.threshold1)
    novel_query = MetaphoricQuery.fromstring(open(args.queryfile).read())
    logging.info("LOADING INDEX")
    indexer = TripleIndex(args.data)
    engine = SearchEngine(indexer)
    explorer = MetaphorExplorer(engine, lights=stop_terms)

    for domain in novel_query:
        logging.info("PROCESSING DOMAIN: %s (%d target terms)" % (domain.label, len(domain.target_terms)))
        for term in domain.target_terms:
            fl = open("%s/%s_%s.txt" % (args.outputdir, domain.label, transliterate_ru(term)), "wb")
            novels = explorer.find_novels2(term)
            if novels is None:
                print
                print "\tFOUND NOVELS FOR %s: %d" % (term, 0)
                continue
            else:
                print "\tFOUND NOVELS FOR %s: %d" % (term, len(novels))
            for novel in novels:
                novel_term_id, freq, total_freq, rel_id, triples = novel
                fl.write("%s\n" % explorer.format_novel2(novel))
            print

            fl.close()