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

from mokujin.query import DomainSearchQuery
from mokujin.metaphorsearch import SentenceCrawler


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--idirp", default="data/*.txt.lf", type=str)

    parser.add_argument("-p", "--parsers", default=4, type=int)
    parser.add_argument("-s", "--searchers", default=8, type=int)
    parser.add_argument("-o", "--ofile", default=None)
    parser.add_argument("-q", "--queryfile", default="search-query.json", help="Search query file", type=str)
    args = parser.parse_args()
    o_file = open(args.ofile, "w") if args.ofile is not None else sys.stdout

    logging.info("INPUT: %s" % args.idirp)
    logging.info("OUTPUT: %s" % o_file)
    logging.info("QUERY FILE: %s" % args.queryfile)

    query = DomainSearchQuery.fromstring(open(args.queryfile).read())

    crawler = SentenceCrawler(args.idirp, o_file, query, n_jobs=(args.parsers, args.parsers))
    crawler.run()

    o_file.close()
