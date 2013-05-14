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

from mokujin.logicalform import MetaphorAdpLF_Reader, POS







class SourceTargetSearcher(object):

    def __init__(self, query):
        self.query = query
        self.compile_patterns()

    def compile_patterns(self):
        for domain in self.query["query"]:
            label = domain["label"]
            print "compiling %s domain" % label.encode("utf-8")
            source_w = domain["source"]
            target_w = domain["target"]
            domain["source_p"] = [(i, self.__compile(w)) for i, w in enumerate(source_w)]
            domain["target_p"] = [(i, self.__compile(w)) for i, w in enumerate(target_w)]
            domain["source_w"] = [(i, w.split(" ")) for i, w in enumerate(source_w)]
            domain["target_w"] = [(i, w.split(" ")) for i, w in enumerate(target_w)]

    @staticmethod
    def __compile(pattern_str):
        words = pattern_str.split(" ")
        return [re.compile(".*\s+" + word + "\s+.*") for word in words]

    def __find_occurances(self, sent, words):
        match = []
        for w in words:
            w_match = (w, [])
            for pred in sent:
                if pred.lemma == w:
                    w_match[1].append(pred)
            match.append(w_match)
        if all(map(lambda w_match: len(w_match[1]) > 0, match)):
            return match
        return None
        
    def __p_connected(self, sent, p1, p2, visited=set(), search_depth=4):
        # check if connected by args
        visited.add(id(p1))
        for arg1 in p1.args:
            for arg2 in p2.args:
                if arg1 == arg2:
                    return arg1
                for p in sent:
                    if p.pos.pos == POS.NONE:
                        if arg1 in p.args and arg2 in p.args:
                            return p
        for arg in p1.args:
            for p in sent.index.find(arg=arg):
                if id(p) not in visited:
                    result = self.__p_connected(sent, p, p2, visited, search_depth - 1)
                    if result is not False:
                        return result
        return False

    def __o_connected(self, sent, occs_1, occs_2):
        for w, occs1 in occs_1:
            for w, occs2 in occs_2:
                for p1 in occs1:
                    for p2 in occs2:
                        connection = self.__p_connected(sent, p1, p2)
                        if connection:
                            return p1, p2, connection
        return False

    def find_matches(self, sent):
        matches = []
        text = " ".join(sent.lemmas())
        for domain in self.query["query"]:
            label = domain["label"]
            source = domain["source"]
            target = domain["target"]
            source_p = domain["source_p"]
            target_p = domain["target_p"]
            source_i = None
            target_i = None

            for i, ps in source_p:
                full_match = True
                for p in ps:
                    if p.match(text) is None:
                        full_match = False
                        break
                if full_match:
                    source_i = i
                    break

            for i, ps in target_p:
                full_match = True
                for p in ps:
                    if p.match(text) is None:
                        full_match = False
                        break
                if full_match:
                    target_i = i
                    break

            if source_i is not None and target_i is not None:
                matches.append((label, source[source_i], target[target_i]))

        return matches

    def find_dep_matches(self, sent):
        matches = []
        for domain in self.query["query"]:
            label = domain["label"]
            source = domain["source"]
            target = domain["target"]
            source_w = domain["source_w"]
            target_w = domain["target_w"]
            source_i = None
            target_i = None

            for i, s_words in source_w:
                s_occ = self.__find_occurances(sent, s_words)
                for j, t_words in target_w:
                    t_occ = self.__find_occurances(sent, t_words)
                    if s_occ and t_occ and self.__o_connected(sent, s_occ, t_occ):
                        matches.append((label, source[i], target[j]))
        return matches

    def i_process_sentences(self, i_sentences):
        for sent in i_sentences:
            matches = self.find_dep_matches(sent)
            for label, source, target in matches:
                yield sent.sid, sent.raw_text, label, source, target


if __name__ == "__main__":

    if len(sys.argv) > 1:
        ifile = open(sys.argv[1], "r")
        if len(sys.argv) > 2:
            query_file = sys.argv[2]
        else:
            query_file = "search-query.json"
    else:
        ifile = sys.stdin
        query_file = "search-query.json"

    ofile = sys.stdout


    print "matching: %s" % query_file

    query = json.loads(open(query_file, "r").read().decode("utf-8"))

    reader = MetaphorAdpLF_Reader(ifile)
    i_sents = reader.i_sentences()
    searcher = SourceTargetSearcher(query)

    ofile.write("FILE: %s\n\n" % sys.argv[1] if len(sys.argv) > 1 else "STDIN")

    for sid, text, label, source, target in searcher.i_process_sentences(i_sents):
        ofile.write("[id:%d, domain:%s, source:%s, target:%s] " % (
            sid,
            label.encode("utf-8"),
            source.encode("utf-8"),
            target.encode("utf-8")
        ))
        ofile.write(text.encode("utf-8"))
        ofile.write("\n")

    ofile.close()
    ifile.close()
