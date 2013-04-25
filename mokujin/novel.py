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

    def exact(self, triple):
        if len(self.seed_triple) != len(triple):
            return False
        for i in xrange(len(self.seed_triple)):
            if i != self.source_term_pos and self.seed_triple[i] != triple[i]:
                return False
        return True

    def find_siblings(self, engine):
        duplicate_flt = lambda triple: triple[self.source_term_pos] != self.source_term_id
        len_constraint = lambda triple: len(triple) == len(self.seed_triple)
        siblings = engine.search(rel_type=self.rel_constraint, arg_query=self.arg_constrains)
        siblings = filter(duplicate_flt, siblings)
        # siblings = filter(len_constraint, siblings)
        # siblings = filter(lambda triple: self.exact(triple), siblings)
        return siblings


class MetaphorExplorer(object):

    def __init__(self, search_engine, lights=None):
        self.engine = search_engine
        self.rel_id_map = REL_ID_MAP
        self.id_rel_map = ID_REL_MAP
        self.lights = set()
        if lights is not None:
            for light_term in lights:
                term_id = self.engine.term_id_map.get(light_term)
                if term_id is not None:
                    self.lights.add(term_id)

    def total_freq(self, term_id):
        freq = 0
        triples = self.engine.search(arg_query=(term_id,))
        for triple in triples:
            freq += triple[-1]
        return freq

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
        for rel_id in self.id_rel_map.keys():
            f3_counter[rel_id] = dict()
        siblings_num = 0
        for seed_triple in seed_triples:
            query = Query(term_id, seed_triple)
            siblings = query.find_siblings(self.engine)
            siblings_num += len(siblings)
            for sibling in siblings:
                novel_id = sibling[query.source_term_pos]
                if novel_id >= 0:
                    rel_id = sibling[0]
                    if novel_id in f3_counter[rel_id]:
                        f3_counter[rel_id][novel_id][0] += 1
                        f3_counter[rel_id][novel_id][1] += seed_triple[-1] #sibling[-1]
                        f3_counter[rel_id][novel_id][2].append(sibling)
                    else:
                        f3_counter[rel_id][novel_id] = [1, sibling[-1], [sibling]]
        return f3_counter, siblings_num

    def compute_siblings(self, term_id, seed_triples, threshold=10):
        f4_triples = []
        for seed_triple in seed_triples:
            if seed_triple[-1] > threshold:
                query = Query(term_id, seed_triple)
                siblings = query.find_siblings(self.engine)
                for sibling in siblings:
                    novel_id = sibling[query.source_term_pos]
                    if sibling[-1] > threshold and novel_id >= 0:
                        f4_triples.append((term_id, novel_id, sibling, seed_triple[-1], sibling[-1]))
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

    def find_novels2(self, term, threshold=0):
        term_id = self.engine.term_id_map.get(term)
        if term_id is None:
            return None
        seed_triples = self.engine.search(arg_query=(term_id,))
        print "\tFOUND SEEDS FOR %s: %d" % (term, len(seed_triples))
        siblings, siblings_num = self.compute_f3(term_id, seed_triples)
        print "\tFOUND SIBLINGS FOR %s: %d" % (term, siblings_num)
        novels = []
        for rel_id in siblings.keys():
            siblings_by_rel_id = siblings[rel_id]
            for novel_term_id, [novel_freq, total_freq, triples] in siblings_by_rel_id.iteritems():
                if novel_freq > threshold and novel_term_id not in self.lights:
                    novels.append((novel_term_id, novel_freq, total_freq, rel_id, triples))
        novels.sort(key=lambda novel: -novel[2])
        return novels

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

    def format_novel2(self, novel):
        novel_term_id, f1, f2, rel_id, triples = novel
        triples.sort(key=lambda triple: -triple[-1])
        triples_str = " // triples(%d) " % len(triples)
        for triple in triples:
            if triple[1] >= 0:
                triples_str += "{%s" % self.engine.id_term_map[triple[1]]
            else:
                triples_str += "{NONE"
            for term_id in triple[2:(len(triple) - 1)]:
                if term_id >= 0:
                    triples_str += "; " + self.engine.id_term_map[term_id]
                else:
                    triples_str += "NONE"
            triples_str += ", %d}  " % triple[-1]
        return "%s, %d, %d %s" % (
            self.engine.id_term_map[novel_term_id],
            f1,
            f2,
            triples_str,
        )
