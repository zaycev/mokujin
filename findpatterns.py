#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

import logging
import argparse

from mokujin.index import TripleIndex
from mokujin.resource import StopList
from mokujin.misc import transliterate_ru
from mokujin.resource import ConceptNetList
from mokujin.index import TripleSearchEngine
from mokujin.sourcesearch import TripleStoreExplorer
from mokujin.patternsearch import PatternCollection

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
                        help="Directory where script's ouput will be placed",  type=str)
    parser.add_argument("-q", "--queryterm", default=None, help="Query term", type=str)
    parser.add_argument("-s", "--stoplist", default="resources/word.freq.ru.csv", help="Stop list file", type=str)
    parser.add_argument("-ts", "--t_stop", default=500, help="Stop words frequency threshold", type=float)
    parser.add_argument("-tt", "--t_triple", default=5, help="Min frequency treshold for target triples", type=float)
    parser.add_argument("-k", "--k_top", default=100, help="Number of first top patterns to output. Specify 0 to output all "
                                                           "found patterns", type=int)
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
    parser.add_argument("-m", "--normalize", default=1, choices=(0, 1), help="Normalize patterns frequency", type=int)
    parser.add_argument("-b", "--debug", default=1, choices=(0, 1), help="Write debug output", type=int)

    args = parser.parse_args()

    logging.info("INDEX DIR: %s" % args.index)
    logging.info("OUTPUT DIR: %s" % args.outputdir)
    logging.info("QUERY TERM: %s" % args.queryterm)
    logging.info("NORMALIZE: %d" % args.normalize)
    logging.info("STOP LIST: %s" % args.stoplist)
    logging.info("STOP WORDS FREQ THRESHOLD: %f" % args.t_stop)
    logging.info("TRIPLES FREQ THRESHOLD: %f" % args.t_triple)
    logging.info("OUTPUT K FIRST SOURCES: k=%d" % args.k_top)
    logging.info("USE PKL COMPRESSION: %r (%s)" % (args.compress, comp_format))
    logging.info("OUTPUT FORMAT: %s" % args.format)
    logging.info("CONCEPT NET FILE: %s" % args.conceptnet)
    logging.info("CONCEPT NET RELATIONS: %s" % args.cn_rel)

    logging.info("LOADING INDEX")
    indexer = TripleIndex(args.index)
    engine = TripleSearchEngine(indexer)

    if args.stoplist:
        stop_list = StopList.load(args.stoplist, threshold=args.t_stop, engine=engine)
    else:
        stop_list = StopList([])
    if args.conceptnet and args.cn_rel:
        concept_net = ConceptNetList.load(args.conceptnet, rels=args.cn_rel, engine=engine)
    else:
        concept_net = ConceptNetList([])

    explorer = TripleStoreExplorer(engine, stop_terms=stop_list, concept_net=concept_net)
    
    term_id = explorer.engine.term_id_map.get(args.queryterm)
    
    if term_id is None:
        logging.info("QUERY TERM NOT FOUND")
        exit(1)
        
    term_triples = explorer.engine.search(arg_query=(term_id,))
    
    pattern_collection = PatternCollection(term_id, term_triples)
    pattern_collection.do_filter(stop_list)

    if args.normalize == 1:
        pattern_collection.do_norm_freq(engine)
        pattern_collection.sort(key=lambda pattern: -pattern.norm_freq)
    else: 
        pattern_collection.sort(key=lambda pattern: -pattern.freq)
    
    output_name = transliterate_ru(args.queryterm)

    
    if args.debug == 1:
        debug_fl_path = "%s/%s.debug.txt" % (args.outputdir, output_name)
        logging.info("WRITING DEBUG TO %s" % debug_fl_path)
        debug_fl = open(debug_fl_path, "wb")
        pattern_collection.debug_output(debug_fl, engine)
        debug_fl.close()
        
    matrix_fl_path = "%s/%s.matrix.txt" % (args.outputdir, output_name)
    patterns_fl_path = "%s/%s.patterns.txt" % (args.outputdir, output_name)
    terms_fl_path = "%s/%s.terms.txt" % (args.outputdir, output_name)
    logging.info("WRITING MATRIX TO %s" % matrix_fl_path)
    logging.info("WRITING PATTERNS TO %s" % patterns_fl_path)
    logging.info("WRITING TERMS TO %s" % terms_fl_path)

    matrix_fl = open(matrix_fl_path, "wb")
    patterns_fl = open(patterns_fl_path, "wb")
    terms_fl = open(terms_fl_path, "wb")
    
    
    pattern_collection.output_matrix(engine, matrix_fl, patterns_fl, terms_fl)
    
    matrix_fl.close()
    patterns_fl.close()
    terms_fl.close()
    logging.info("DONE")
