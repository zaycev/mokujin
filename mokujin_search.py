#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

import re
import sys
import json

from logicalform import MetaphorLF_Reader


class SourceTargetSearcher(object):

    def __init__(self, query):
        self.query = query
        self.compile_patterns()

    def compile_patterns(self):
        for domain in query["query"]:
            label = domain["label"]
            print "compiling %s domain" % label.encode("utf-8")
            source_w = domain["source"]
            target_w = domain["target"]
            domain["source_p"] = [(i, self.__compile(w)) for i, w in enumerate(source_w)]
            domain["target_p"] = [(i, self.__compile(w)) for i, w in enumerate(target_w)]

    @staticmethod
    def __compile(word):
        return re.compile(".*\s+" + word.replace(" ", ".*\s+.*") + "\s+.*")

    def find_matches(self, text):
        matches = []
        for domain in query["query"]:
            label = domain["label"]
            source = domain["source"]
            target = domain["target"]
            source_p = domain["source_p"]
            target_p = domain["target_p"]
            source_i = None
            target_i = None
            for i, p in source_p:
                if p.match(text):
                    source_i = i
                    break
            for i, p in target_p:
                if p.match(text):
                    target_i = i
                    break
            if source_i is not None and target_i is not None:
                matches.append((label, source[source_i], target[target_i]))
        return matches

    def i_process_sentences(self, i_sentences):
        for sent in i_sentences:
            text = " ".join(sent.lemmas())
            matches = self.find_matches(text)
            for label, source, target in matches:
                yield sent.sid, text, label, source, target


if __name__ == "__main__":

    if len(sys.argv) > 1:
        ifile = open(sys.argv[1], "r")
        if len(sys.argv) > 2:
            ofile = open(sys.argv[2], "w")
        else:
            ofile = sys.stdout #open("%s.triples.csv" % sys.argv[1], "w")
    else:
        ifile = sys.stdin
        ofile = sys.stdout

    if len(sys.argv) > 3:
        query_file = sys.argv[3]
    else:
        query_file = "search-query.json"

    print "matching: %s" % query_file

    query = json.loads(open(query_file, "r").read().decode("utf-8"))

    reader = MetaphorLF_Reader(ifile)
    i_sents = reader.i_sentences()
    searcher = SourceTargetSearcher(query)

    ofile.write("FILE: %s\n\n" % ofile)

    for sid, text, label, source, target in searcher.i_process_sentences(i_sents):
        ofile.write("[id:%d,domain:%s] " % (sid, label.encode("utf-8")))
        ofile.write(text.encode("utf-8"))
        ofile.write(" // (source:%s, target:%s)\n".encode("utf-8") %
                    (source.encode("utf-8"), target.encode("utf-8")))

    ofile.close()
    ifile.close()
