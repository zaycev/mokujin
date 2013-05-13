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


class Query(object):

    def __init__(self, source_term_id, seed_triple):
        self.seed_triple = seed_triple
        self.rel_constraint = seed_triple[0]
        self.arg_constrains = []
        self.source_term_id = source_term_id
        self.source_term_pos = -1
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

    def find_siblings(self, engine):
        duplicate_flt = lambda triple: triple[self.source_term_pos] != self.source_term_id
        # len_constraint = lambda triple: len(triple) == len(self.seed_triple)
        siblings = engine.search(rel_type=self.rel_constraint, arg_query=self.arg_constrains)
        siblings = filter(duplicate_flt, siblings)
        # siblings = filter(len_constraint, siblings)
        # siblings = filter(lambda triple: self.exact(triple), siblings)
        return siblings


class MetaphorExplorer(object):

    def __init__(self, search_engine, stop_terms=set()):
        self.engine = search_engine
        self.rel_id_map = REL_ID_MAP
        self.id_rel_map = ID_REL_MAP
        self.stop_terms = self.map_stop_terms(stop_terms)

    def term_freq(self, term_id, threshold=0.0):
        freq = 0.0
        tfreq = 0.0
        triples = self.engine.search(arg_query=(term_id,))
        triples = filter(lambda tr: not self.is_light_triple(tr), triples)
        for triple in triples:
            triple_freq = triple[-1]
            if triple_freq > threshold:
                freq += 1
                tfreq += triple[-1]
        return freq, tfreq

    def is_light_triple(self, triple):
        pos_tags = REL_POS_MAP[triple[0]]
        not_light = 0
        for i in range(1, len(triple) - 1):
            if triple[i] not in self.stop_terms and pos_tags[i - 1] is not POS.PREP:
                not_light += 1
            if not_light == 2:
                return False
        # print
        # for term_id in triple[1:(len(triple) - 1)]:
        #     print self.engine.id_term_map[term_id]
        return True

    def compute_f3(self, term_id, seed_triples):
        f3_counter = dict()
        siblings_num = 0
        for seed_triple in seed_triples:
            query = Query(term_id, seed_triple)
            siblings = query.find_siblings(self.engine)
            siblings = filter(lambda tr: not self.is_light_triple(tr), siblings)
            siblings_num += len(siblings)
            for sibling in siblings:
                novel_id = sibling[query.source_term_pos]
                if novel_id >= 0:
                    if novel_id in f3_counter:
                        f3_counter[novel_id][0] += 1
                        f3_counter[novel_id][1] += seed_triple[-1]
                        f3_counter[novel_id][2].append(sibling)
                    else:
                        f3_counter[novel_id] = [1, sibling[-1], [sibling]]
        return f3_counter, siblings_num

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
        return stop_terms_ids

    def find_potential_sources(self, term, threshold=0):
        """
        Find all potential sources for given target term and calculate their frequencies.
        """

        term_id = self.engine.term_id_map.get(term)
        if term_id is None:
            return None
        # retrieving all triples containing target term
        seed_triples = self.engine.search(arg_query=(term_id,))
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
        siblings, siblings_num = self.compute_f3(term_id, seed_triples)
        print "\tFOUND SIBLINGS FOR %s: %d" % (term, siblings_num)
        potential_sources = []
        ignored = 0

        # calculating normalized frequencies
        # joined_freq   - number of siblings for given source and target terms
        # joined_tfreq  - total frequency of siblings for given source and target terms
        for source_term_id, [joined_freq, joined_tfreq, triples] in siblings.iteritems():
            if source_term_id in self.stop_terms:
                ignored += 1
                continue
            total_freq, total_tfreq = self.term_freq(source_term_id, threshold=threshold)
            norm_freq = float(joined_freq) / float(total_freq)
            norm_tfreq = float(joined_tfreq) / float(total_tfreq)
            potential_sources.append((
                source_term_id,
                joined_freq, total_freq, norm_freq,
                joined_tfreq, total_tfreq, norm_tfreq,
                triples
            ))
        print "\tSTOPS IGNORED: %d" % ignored
        # sort output by <total_tfreq> value (#5), other options
        # 0 - source_term_id
        # 1 - joined_freq
        # 2 - total_freq
        # 3 - norm_freq
        # 4 - joined_tfreq
        # 5 - total_tfreq
        # 6 - norm_tfreq
        potential_sources.sort(key=lambda source_row: -source_row[5])
        return potential_sources

    def format_source_output_line(self, source_row):
        potential_source_term_id, \
        joined_freq, total_freq, norm_freq, \
        joined_tfreq, total_tfreq, norm_tfreq, \
        triples = source_row
        triples.sort(key=lambda triple: -triple[-1])
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
        return "%s, %d, %d, %.6f, %d, %d, %.6f // %s" % (
            self.engine.id_term_map[potential_source_term_id],
            joined_freq, total_freq, norm_freq,
            joined_tfreq, total_tfreq, norm_tfreq,
            triples_str,
        )
