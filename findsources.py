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
from mokujin.resource import StopList
from mokujin.resource import ConceptNetList
from mokujin.query import DomainSearchQuery
from mokujin.index import TripleSearchEngine
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

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--index", default="data/index", help="Triple store index directory", type=str)
    parser.add_argument("-o", "--outputdir", default="output",
                        help="Directory where potential source words will be placed",  type=str)
    parser.add_argument("-q", "--queryfile", default="resources/example.json", help="Search query file. See "
                                                                                    "resources/example.json", type=str)
    parser.add_argument("-s", "--stoplist", default="resources/word.freq.ru.csv", help="Stop list file", type=str)
    parser.add_argument("-ts", "--t_stop", default=500, help="Stop words frequency threshold", type=float)
    parser.add_argument("-tt", "--t_triple", default=5, help="Min frequency treshold for target triples", type=float)
    parser.add_argument("-k", "--k_top", default=100, help="Number of first sources to output. Specify 0 to output all "
                                                           "found potential sources", type=int)
    parser.add_argument("-z", "--compress", default=1, choices=(0, 1), help="Compress output plk", type=int)
    parser.add_argument("-f", "--format", default="all", choices=("pkl", "txt", "all"),
                        help="Output format", type=str)
    parser.add_argument("-c", "--conceptnet", default="resources/conceptnet.ru.csv",
                        help="Path to the conceptnet file", type=str)
    parser.add_argument("-r", "--cn_rel", default="cds", type=str,
                        help="Types of concept net relation which should be filtered: \n"
                             "'c' for ConceptuallyRelatedTo\n"
                             "'d' for DerivedFrom\n"
                             "'s' for Synonym")
    parser.add_argument("-lm", "--lda_model", default=None, type=str,
                        help="A path to GENSIM LDA model file.")
    parser.add_argument("-ld", "--lda_dict", default=None, type=str,
                        help="A path to GENSIM LDA model dictionary file.")
    parser.add_argument("-lt", "--lda_threshold", default=0.5, type=float,
                        help="LDA filter threshold. Default is 0.5")

    args = parser.parse_args()

    logging.info("INDEX DIR: %s" % args.index)
    logging.info("OUTPUT DIR: %s" % args.outputdir)
    logging.info("QUERY FILE: %s" % args.queryfile)
    logging.info("STOP LIST: %s" % args.stoplist)
    logging.info("STOP WORDS FREQ THRESHOLD: %f" % args.t_stop)
    logging.info("TRIPLES FREQ THRESHOLD: %f" % args.t_triple)
    logging.info("OUTPUT K FIRST SOURCES: k=%d" % args.k_top)
    logging.info("USE PKL COMPRESSION: %r (%s)" % (args.compress, comp_format))
    logging.info("OUTPUT FORMAT: %s" % args.format)
    logging.info("CONCEPT NET FILE: %s" % args.conceptnet)
    logging.info("LDA MODEL: %s" % args.lda_model)
    logging.info("LDA DICT: %s" % args.lda_dict)
    logging.info("LDA THRESHOLD: %s" % args.lda_threshold)

    if args.lda_model is not None and args.lda_dict is not None and args.lda_threshold > 0:
        from mokujin.filters import lda_similarity
        from gensim import corpora
        from gensim import models
        lda_model = models.ldamodel.LdaModel.load(args.lda_model)
        lda_dict = corpora.Dictionary.load(args.lda_dict)
        lda_threshold = args.lda_threshold
    else:
        lda_model = None

    stop_list = None
    concept_net = None
    if args.stoplist:
        stop_list = StopList.load(args.stoplist, threshold=args.t_stop)
    if args.conceptnet and args.cn_rel:
        concept_net = ConceptNetList.load(args.conceptnet, rels=args.cn_rel)

    query = DomainSearchQuery.fromstring(open(args.queryfile).read())
    logging.info("LOADING INDEX")
    indexer = TripleIndex(args.index)
    engine = TripleSearchEngine(indexer)

    explorer = TripleStoreExplorer(engine, stop_terms=stop_list, concept_net=concept_net)

    for domain in query:
        logging.info("PROCESSING DOMAIN: %s (%d target terms)" % (domain.label, len(domain.target_terms)))
        for term in domain.target_terms:
            target_term = term
            sources = explorer.find_potential_sources(term, threshold=args.t_triple)

            if sources is None:
                print
                print "\tFOUND POTENTIAL SOURCES FOR %s: %d" % (term, 0)
                continue
            else:
                print "\tFOUND POTENTIAL SOURCES FOR %s: %d" % (term, len(sources))

            if args.k_top > 0:
                sources = sources[0:min(args.k_top, len(sources))]

            if args.format == "pkl" or args.format == "all":
                sources_str = pickle.dumps(sources)
                if args.compress == 1:
                    sources_str = compress(pickle.dumps(sources))
                fl = open("%s/%s_%s.pkl" % (args.outputdir, domain.label, transliterate_ru(term)), "wb")
                fl.write(sources_str)
                fl.close()

            if args.format == "txt" or args.format == "all":
                file_name = transliterate_ru(unicode(term))
                fl = open("%s/%s_%s.txt" % (args.outputdir, domain.label, file_name), "wb")
                fl.write("source"
                         "\tsum_of_source_norm_freq"
                         "\tsum_of_target_norm_freq"
                         "\tnumber_of_triples"
                         "\ttotal_pattern_source_triple_freq"
                         "\ttotal_pattern_target_triple_freq"
                         "\ttriples"
                         "\n")
                for source in sources:

                    if lda_model is not None:
                        source_term = explorer.engine.id_term_map[source.source_id]
                        similarity = lda_similarity(target_term,
                                                    source_term,
                                                    lda_dict,
                                                    lda_model)
                        if similarity < lda_threshold:
                            continue

                    fl.write("%s\n" % explorer.format_source_output_line(source))
                print
                fl.close()

    logging.info("DONE")