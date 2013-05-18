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

try:
    import lz4 as comp
    comp_format = "lz4"
    compress = comp.compressHC
    decompress = comp.decompress
except ImportError:
    import zlib as comp
    comp_format = "zip"
    compress = lambda string: comp.compress(string, 9)
    decompress = comp.decompress


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
    parser.add_argument("-t2", "--threshold2", default=5, help="Min frequency treshold for target triples", type=float)
    parser.add_argument("-t3", "--threshold3", default=100, help="Number of first sources to output. Specify 0 to "
                                                                 "output all found potential sources", type=int)
    parser.add_argument("-c", "--compress", default=1, choices=(0, 1), help="Compress output plk", type=int)

    parser.add_argument("-f", "--format", default="all", choices=("pkl", "txt", "all"),
                        help="Number of first sources to output", type=str)

    args = parser.parse_args()

    logging.info("INDEX DIR: %s" % args.data)
    logging.info("OUTPUT DIR: %s" % args.outputdir)
    logging.info("QUERY FILE: %s" % args.queryfile)
    logging.info("STOP TERMS: %s" % args.stopterms)
    logging.info("FORMAT: %s" % args.format)
    logging.info("COMPRESSION: %r" % args.compress)
    logging.info("T1: %f" % args.threshold1)
    logging.info("T2: %f" % args.threshold2)
    logging.info("T3: %f" % args.threshold3)

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

            if sources is None:
                print
                print "\tFOUND POTENTIAL SOURCES FOR %s: %d" % (term, 0)
                continue
            else:
                print "\tFOUND POTENTIAL SOURCES FOR %s: %d" % (term, len(sources))

            if args.threshold3 > 0:
                sources = sources[0:min(args.threshold3, len(sources))]

            if args.format == "pkl" or args.format == "all":
                sources_str = pickle.dumps(sources)
                if args.compress == 1:
                    sources_str = compress(pickle.dumps(sources))
                fl = open("%s/%s_%s.pkl" % (args.outputdir, domain.label, transliterate_ru(term)), "wb")
                fl.write(sources_str)
                fl.close()

            if args.format == "txt" or args.format == "all":
                fl = open("%s/%s_%s.txt" % (args.outputdir, domain.label, transliterate_ru(term)), "wb")
                fl.write("source, norm_freq, triples\n")
                for source in sources:
                    fl.write("%s\n" % explorer.format_source_output_line(source))
                print
                fl.close()

    logging.info("DONE")