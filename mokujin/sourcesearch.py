#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

import logging

from mokujin.logicalform import POS
from mokujin.index import REL_ID_MAP
from mokujin.index import ID_REL_MAP
from mokujin.index import REL_POS_MAP


class PotentialSource(object):

    def __init__(self, target_id, source_id, triples):
        self.target_id = target_id
        self.source_id = source_id
        self.triples = triples
        self.total_freq = -1
        self.total_triple_freq = -1
        self.joined_freq = -1
        self.joined_triple_freq = -1
        self.norm_freq = -1

    def calculate_freqs(self, store_explorer, threshold):
        self.total_freq, self.total_triple_freq = store_explorer.calc_term_freq(self.source_id, threshold)
        self.joined_freq = len(self.triples)
        self.joined_triple_freq = 0
        norm_freqs = []
        triples = []
        for seed_triple, source_triple, seed_triple_pattern_freq in self.triples:
            source_triple_freq = seed_triple[-1]
            source_patterns_freq = seed_triple_pattern_freq + source_triple[-1]
            norm_freq = float(source_triple_freq) / float(source_patterns_freq)
            norm_freqs.append(norm_freq)
            triples.append((source_triple, norm_freq))
        self.norm_freq = sum(norm_freqs)
        self.triples = triples
        self.triples.sort(key=lambda t: -t[1])


class Query(object):

    def __init__(self, source_term_id, seed_triple):
        self.seed_triple = seed_triple
        self.rel_constraint = seed_triple[0]
        self.arg_constrains = []
        self.source_term_id = source_term_id
        self.source_term_pos = -1
        self.duplicate_flt = lambda triple: triple[self.source_term_pos] != self.source_term_id
        self.len_constraint_flt = lambda triple: len(triple) == len(self.seed_triple)
        for i in xrange(1, len(seed_triple) - 1):
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

    def find_siblings(self, engine, strict=True):
        siblings = engine.search(rel_type=self.rel_constraint, arg_query=self.arg_constrains)
        siblings = filter(self.duplicate_flt, siblings)
        if strict:
            siblings = filter(self.len_constraint_flt, siblings)
            siblings = filter(lambda triple: self.exact(triple), siblings)
        return siblings


class TripleStoreExplorer(object):

    def __init__(self, search_engine, stop_terms=set()):
        self.engine = search_engine
        self.rel_id_map = REL_ID_MAP
        self.id_rel_map = ID_REL_MAP
        self.stop_terms = self.map_stop_terms(stop_terms)

    def calc_term_freq(self, term_id, threshold=0.0):
        freq = 0.0
        triple_freq = 0.0
        triples = self.engine.search(arg_query=(term_id,))
        triples = filter(lambda tr: not self.is_light_triple(tr), triples)
        for triple in triples:
            triple_freq = triple[-1]
            if triple_freq > threshold:
                freq += 1
                triple_freq += triple[-1]
        return freq, triple_freq

    def is_light_triple(self, triple):
        pos_tags = REL_POS_MAP[triple[0]]
        not_light = 0
        for i in range(1, len(triple) - 1):
            if triple[i] not in self.stop_terms and pos_tags[i - 1] is not POS.PREP:
                not_light += 1
            if not_light == 2:
                return False
        return True

    def find_siblings(self, term_id, seed_triples):
        siblings_dict = dict()
        siblings_num = 0
        for seed_triple in seed_triples:
            query = Query(term_id, seed_triple)
            siblings = query.find_siblings(self.engine, strict=False)
            siblings = filter(lambda tr: not self.is_light_triple(tr), siblings)
            siblings_num += len(siblings)
            pattern_freq = sum([triple[-1] for triple in siblings])
            for sibling in siblings:
                source_id = sibling[query.source_term_pos]
                if source_id >= 0:
                    if source_id in siblings_dict:
                        siblings_dict[source_id].append((seed_triple, sibling, pattern_freq))
                    else:
                        siblings_dict[source_id] = [(seed_triple, sibling, pattern_freq)]
        return siblings_dict, siblings_num

    def map_stop_terms(self, stop_terms):
        stop_terms_ids = set()
        for term in stop_terms:
            term_id = self.engine.term_id_map.get(term, -1)
            if term_id != -1:
                stop_terms_ids.add(term_id)
        logging.info("MAPPED %d/%d STOP TERMS" % (len(stop_terms_ids), len(stop_terms)))
        for term in stop_terms:
            term_id = self.engine.term_id_map.get(term, -1)
            if term_id == -1:
                print "\tNOT FOUND: %s" % term
        stop_terms_ids.add(-1)
        return stop_terms_ids

    def find_potential_sources(self, term, threshold=0):
        """
        Find all potential sources for given target term and calculate their frequencies.
        """

        target_term_id = self.engine.term_id_map.get(term)
        if target_term_id is None:
            return None
        # retrieving all triples containing target term
        seed_triples = self.engine.search(arg_query=(target_term_id,))
        # calculating their frequency
        target_freq = len(seed_triples)
        # calculating their total frequency
        target_tfreq = sum([seed[-1] for seed in seed_triples])
        print "\tTARGET FREQ: %d, %d" % (target_freq, target_tfreq)
        print "\tFOUND SEEDS FOR %s: %d" % (term, len(seed_triples))
        # remove all triples with frequency less then the threshold
        seed_triples = filter(lambda s: s[-1] >= threshold, seed_triples)
        print "\tAFTER FILTERING (f>=%f): %d" % (threshold, len(seed_triples))
        # remove all triples containing less than 2 non-stop words (light triples)
        seed_triples = filter(lambda tr: not self.is_light_triple(tr), seed_triples)
        print "\tAFTER IGNORING LIGHT TRIPLES: %d" % len(seed_triples)
        # retrieve siblings - triples containing the same arguments as seed triples
        # sibling(target, source) is triple (a_1, .., source, .., a_n) such as: exist triple (a_1, .., target, .., a_n)
        siblings, siblings_num = self.find_siblings(target_term_id, seed_triples)
        print "\tFOUND SIBLINGS FOR %s: %d" % (term, siblings_num)
        potential_sources = []
        ignored = 0

        # calculating normalized frequencies
        # joined_freq   - number of siblings for given source and target terms
        # joined_tfreq  - total frequency of siblings for given source and target terms
        for source_term_id, triples in siblings.iteritems():
            if source_term_id in self.stop_terms:
                ignored += 1
                continue
            new_source = PotentialSource(target_term_id, source_term_id, triples)
            new_source.calculate_freqs(self, threshold)
            potential_sources.append(new_source)
        print "\tSTOPS IGNORED: %d" % ignored
        # sort output by norm_freq, other options:
        # total_freq
        # total_triple_freq
        # joined_freq
        # joined_triple_freq
        # norm_freq
        # norm_freq
        potential_sources.sort(key=lambda source: -source.norm_freq)
        return potential_sources

    def format_source_output_line(self, potential_source):
        triples = [triple for triple, norm_freq in potential_source.triples]
        triples_str = ""
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
        return "%s, %d, %d, %d, %d, %.6f // %s" % (
            self.engine.id_term_map[potential_source.source_id],
            potential_source.joined_freq, potential_source.total_freq,
            potential_source.joined_triple_freq, potential_source.total_triple_freq, potential_source.norm_freq,
            triples_str,
        )
