#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

import collections

from mokujin.index import REL_ID_MAP
from mokujin.index import ID_REL_MAP


class Query(object):

    def __init__(self, source_term_id, seed_triple):
        self.seed_triple = seed_triple
        self.rel_constraint = seed_triple[0]
        self.arg_constrains = []
        self.source_term_id = source_term_id
        self.source_term_pos = -1
        for i in range(1, len(seed_triple) - 1):
            if seed_triple[i] != source_term_id and seed_triple[i] >= 0:
                self.arg_constrains.append((seed_triple[i], i))
            else:
                self.source_term_pos = i

    def find_siblings(self, engine):
        duplicate_flt = lambda triple: triple[self.source_term_pos] != self.source_term_id
        siblings = engine.search(rel_type=self.rel_constraint, arg_query=self.arg_constrains)
        siblings = filter(duplicate_flt, siblings)
        return siblings


class GraphExplorer(object):

    def __init__(self, search_engine):
        self.engine = search_engine
        self.rel_id_map = REL_ID_MAP
        self.id_rel_map = ID_REL_MAP

    def compute_f1(self, seed_triples):
        f1_counter = collections.Counter()
        for triple in seed_triples:
            f1_counter[triple[0]] += 1  # += triple[-1]
        return f1_counter

    def compute_f2(self, novels):
        f2_counter = dict()
        for rel_type in self.id_rel_map.keys():
            f2_counter[rel_type] = collections.Counter()
        for novel in novels:
            triples = self.engine.search(arg_query=(novel,))
            for triple in triples:
                f2_counter[triple[0]][novel] += 1  # += triple[-1]
        return f2_counter

    def compute_f3(self, term_id, seed_triples):
        f3_counter = dict()
        for rel_type in self.id_rel_map.keys():
            f3_counter[rel_type] = collections.Counter()
        for seed_triple in seed_triples:
            query = Query(term_id, seed_triple)
            siblings = query.find_siblings(self.engine)
            for sibling in siblings:
                novel = sibling[query.source_term_pos]
                if novel >= 0:
                    f3_counter[sibling[0]][novel] += 1
        return f3_counter

    def compute_siblings(self, term_id, seed_triples, threshold=10):
        f4_triples = []
        for seed_triple in seed_triples:
            if seed_triple[-1] > threshold:
                query = Query(term_id, seed_triple)
                siblings = query.find_siblings(self.engine)
                for sibling in siblings:
                    novel = sibling[query.source_term_pos]
                    if sibling[-1] > threshold and novel >= 0:
                        f4_triples.append((term_id, novel, sibling, seed_triple[-1], sibling[-1]))
        return f4_triples

    def find_novels(self, term):
        term_id = self.engine.term_id_map.get(term)
        if term_id is None:
            return None
        seed_triples = self.engine.search(arg_query=(term_id,))
        siblings = self.compute_siblings(term_id, seed_triples)
        siblings.sort(key=lambda sibling: (sibling[3], sibling[4]))
        novels = reversed(siblings)
        return list(novels)

    def format_novel(self, novel):
        source, novel, triple, f1, f2 = novel
        triple_str = "<" + self.id_rel_map[triple[0]]
        for term_id in triple[1:(len(triple) - 1)]:
            if term_id >= 0:
                triple_str += ", " + self.engine.id_term_map[term_id]
            else:
                triple_str += ", NONE"
        triple_str += ">"
        return "%s, %s, %s, %d, %d" % (
            self.engine.id_term_map[source],
            self.engine.id_term_map[novel],
            triple_str,
            f1,
            f2
        )