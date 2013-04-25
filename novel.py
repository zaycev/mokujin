#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

import sys
import logging

from mokujin.index import ID_REL_MAP
from mokujin.index import TripleIndex
from mokujin.index import SearchEngine
from mokujin.query import MetaphoricQuery
from mokujin.novel import MetaphorExplorer
from mokujin.misc import transliterate_ru

FILES = dict()


def get_file(domain, term, rel_type):
    term = transliterate_ru(term)
    fl_name = "/Users/zvm/code/mokujin/novels/%s_%s_%s.txt" % (domain.label, term, ID_REL_MAP[rel_type])
    if fl_name in FILES:
        return FILES[fl_name]
    else:
        fl = open(fl_name, "w")
        FILES[fl_name] = fl
        return fl

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    query_file = sys.argv[1]
    threshold = int(sys.argv[2])
    data_dir = sys.argv[3]
    out_dir = sys.argv[4]




    logging.info("LOADING QUERY")
    query_json = open(query_file).read()
    novel_query = MetaphoricQuery.fromstring(query_json)

    logging.info("LOADING TRIPLES INDEX")
    indexer = TripleIndex(data_dir)
    engine = SearchEngine(indexer)
    explorer = MetaphorExplorer(engine)

    term = u"бедность".encode("utf-8")
    term_id = engine.term_id_map[term]

    # print term, explorer.total_freq(term_id)

    # novels = explorer.find_novels2(term, threshold=10)
    # for novel_term_id, freq, total_freq, rel_id, triples in novels:
    #     print engine.id_term_map[novel_term_id], freq, total_freq

    for domain in novel_query:
        logging.info("PROCESSING DOMAIN: %s (%d target terms)" % (domain.label, len(domain.target_terms)))
        print
        for term in domain.target_terms:
            novels = explorer.find_novels2(term)
            if novels is None:
                print "\tFOUND NOVELS FOR %s: %d" % (term, 0)
                continue
            else:
                print "\tFOUND NOVELS FOR %s: %d" % (term, len(novels))
            for novel in novels:
                novel_term_id, freq, total_freq, rel_id, triples = novel
                fl = get_file(domain, term, rel_id)
                fl.write("%s\n" % explorer.format_novel2(novel))
            print
        for fl in FILES.values():
            fl.close()