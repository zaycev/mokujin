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


import csv
import logging
import argparse
import cPickle as pickle

from mokujin.index import TripleIndex
from mokujin.index import TripleSearchEngine
from mokujin.query import DomainSearchQuery
from mokujin.sourcesearch import TripleStoreExplorer
from mokujin.misc import transliterate_ru


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
    parser.add_argument("-d", "--data", default="data/index", help="Triple store index directory", type=str)
    parser.add_argument("-o", "--outputdir", default="output",
                        help="Directory where potential source words will be placed",  type=str)
    parser.add_argument("-q", "--queryfile", default="query.json", help="Search query file", type=str)
    parser.add_argument("-s", "--stopterms", default="light_words_ru.csv", help="Path to the file with stop words",
                        type=str)
    parser.add_argument("-t1", "--threshold1", default=500, help="Max frequency treshold for light words", type=float)
    parser.add_argument("-t2", "--threshold2", default=5, help="Min frequency treshold for seed triples", type=float)
    parser.add_argument("-t3", "--threshold3", default=100, help="Number of first sources to output. Specify -1 to "
                                                                 "output all found potential sources", type=int)

    parser.add_argument("-f", "--format", default="pkl", choices=("pkl", "txt", ),
                        help="Number of first sources to output", type=str)

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

    if args.format == "pkl":

        for domain in query:
            logging.info("PROCESSING DOMAIN: %s (%d target terms)" % (domain.label, len(domain.target_terms)))
            for term in domain.target_terms:
                sources = explorer.find_potential_sources(term, threshold=args.threshold2)
                fl = open("%s/%s_%s.pkl" % (args.outputdir, domain.label, transliterate_ru(term)), "wb")

                if args.threshold3 > 0:
                    sources = sources[0:min(args.threshold3, len(sources))]

                pickle.dump(sources, fl)
                fl.close()

    elif args.format == "txt":

        for domain in query:
            logging.info("PROCESSING DOMAIN: %s (%d target terms)" % (domain.label, len(domain.target_terms)))
            for term in domain.target_terms:
                fl = open("%s/%s_%s.txt" % (args.outputdir, domain.label, transliterate_ru(term)), "wb")
                fl.write("potential_source, joined_freq, total_freq, joined_triple_freq, total_triple_freq, norm_freq\n")
                sources = explorer.find_potential_sources(term, threshold=args.threshold2)
                if sources is None:
                    print
                    print "\tFOUND POTENTIAL SOURCES FOR %s: %d" % (term, 0)
                    continue
                else:
                    print "\tFOUND POTENTIAL SOURCES FOR %s: %d" % (term, len(sources))
                for source in sources:
                    if args.threshold3 > 0:
                        sources = sources[0:min(args.threshold3, len(sources))]
                    fl.write("%s\n" % explorer.format_source_output_line(source))
                print
                fl.close()

    logging.info("DONE")