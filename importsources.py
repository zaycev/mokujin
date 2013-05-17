#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE


#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE


import logging
import argparse
import cPickle as pickle

from mokujin.index import TripleIndex
from mokujin.index import TripleSearchEngine
from mokujin.query import DomainSearchQuery
from mokujin.sourcesearch import TripleStoreExplorer
from mokujin.misc import transliterate_ru
from findsources import load_stop_terms


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--data", default="data/index", help="Triple store index directory", type=str)
    parser.add_argument("-o", "--outputdir", default="output",
                        help="Directory where potential source words will be placed",  type=str)
    parser.add_argument("-q", "--queryfile", default="query.json", help="Search query file", type=str)
    parser.add_argument("-s", "--stopterms", default="light_words_ru.csv", help="Path to the file with stop words",
                        type=str)
    parser.add_argument("-t1", "--threshold1", default=500, help="Max frequency treshold for light words", type=float)
    parser.add_argument("-t2", "--threshold2", default=5, help="Min frequency treshold for seed triples", type=float)
    args = parser.parse_args()

    logging.info("INDEX DIR: %s" % args.data)
    logging.info("OUTPUT DIR: %s" % args.outputdir)
    logging.info("QUERY FILE: %s" % args.queryfile)
    logging.info("STOP TERMS: %s" % args.stopterms)
    logging.info("T1: %f" % args.threshold1)
    logging.info("T2: %f" % args.threshold2)

    stop_terms = load_stop_terms(args.stopterms, threshold=args.threshold1)
    query = DomainSearchQuery.fromstring(open(args.queryfile).read())
    logging.info("LOADING INDEX")
    indexer = TripleIndex(args.data)
    engine = TripleSearchEngine(indexer)
    explorer = TripleStoreExplorer(engine, stop_terms=stop_terms)

    for domain in query:
        logging.info("PROCESSING DOMAIN: %s (%d target terms)" % (domain.label, len(domain.target_terms)))
        for term in domain.target_terms:
            sources = explorer.find_potential_sources(term, threshold=args.threshold2)
            fl = open("%s/%s_%s.pkl" % (args.outputdir, domain.label, transliterate_ru(term)), "wb")
            pickle.dump(sources, fl)
            fl.close()

    logging.info("DONE")