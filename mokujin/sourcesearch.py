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

    def __init__(self, source_id, triples):
        self.source_id = source_id
        self.triples = triples
        self.triples_count = -1
        self.total_pattern_source_triple_freq = -1
        self.total_pattern_target_triple_freq = -1
        self.norm_freq = -1

    def calculate_freqs(self):
        self.triples_count = len(self.triples)
        self.total_pattern_source_triple_freq = 0
        norm_freqs = []
        triples = []

        for target_triple, source_triple, target_triple_pattern_freq in self.triples:
            source_triple_freq = source_triple[-1]
            target_triple_freq = target_triple[-1]
            self.total_pattern_source_triple_freq += source_triple_freq
            self.total_pattern_target_triple_freq += target_triple_freq
            source_patterns_freq = target_triple_pattern_freq + source_triple[-1]
            norm_freq = float(source_triple_freq) / float(source_patterns_freq)
            norm_freqs.append(norm_freq)
            triples.append((source_triple, norm_freq))

        self.norm_freq = sum(norm_freqs)
        self.triples = triples
        self.triples.sort(key=lambda triple: -triple[1])


class Query(object):

    def __init__(self, source_term_id, target_triple):
        self.target_triple = target_triple
        self.rel_constraint = target_triple[0]
        self.arg_constrains = []
        self.source_term_id = source_term_id
        self.source_term_pos = -1
        self.duplicate_filter = lambda triple: triple[self.source_term_pos] != self.source_term_id
        self.len_constraint_flt = lambda triple: len(triple) == len(self.target_triple)
        for i in xrange(1, len(target_triple) - 1):
            if target_triple[i] != source_term_id and target_triple[i] >= 0:
                self.arg_constrains.append((target_triple[i], i))
            else:
                self.source_term_pos = i

    def exact_pattern_match(self, triple):
        if len(self.target_triple) != len(triple):
            return False
        for i in xrange(len(self.target_triple)):
            if i != self.source_term_pos and self.target_triple[i] != triple[i]:
                return False
        return True

    def find_triples(self, engine, strict=True):
        triples = engine.search(rel_type=self.rel_constraint, arg_query=self.arg_constrains)
        triples = filter(self.duplicate_filter, triples)
        if strict:
            triples = filter(self.len_constraint_flt, triples)
            triples = filter(self.exact_pattern_match, triples)
        return triples


class TripleStoreExplorer(object):

    def __init__(self, search_engine, stop_terms=(), concept_net=()):
        self.engine = search_engine
        self.rel_id_map = REL_ID_MAP
        self.id_rel_map = ID_REL_MAP
        self.stop_terms = self.map_stop_terms(stop_terms)
        self.concept_net = self.map_concept_net(concept_net)

    def calc_term_triples_freq(self, term_id, threshold=0.0):
        triples_count = 0.0
        triples_freq = 0.0
        triples = self.engine.search(arg_query=(term_id,))
        triples = filter(lambda tr: not self.is_light_triple(tr), triples)
        for triple in triples:
            triples_freq = triple[-1]
            if triples_freq > threshold:
                triples_count += 1
                triples_freq += triple[-1]
        return triples_count, triples_freq

    def is_light_triple(self, triple):
        pos_tags = REL_POS_MAP[triple[0]]
        not_light = 0
        for i in range(1, len(triple) - 1):
            if triple[i] not in self.stop_terms and pos_tags[i - 1] is not POS.PREP:
                not_light += 1
            if not_light == 2:
                return False
        return True

    def find_source_triples(self, term_id, target_triples):
        siblings_dict = dict()
        siblings_num = 0
        for target_triple in target_triples:
            query = Query(term_id, target_triple)
            siblings = query.find_triples(self.engine, strict=False)
            siblings = filter(lambda tr: not self.is_light_triple(tr), siblings)
            siblings_num += len(siblings)
            pattern_freq = sum([triple[-1] for triple in siblings])
            for sibling in siblings:
                source_id = sibling[query.source_term_pos]
                if source_id >= 0:
                    if source_id in siblings_dict:
                        siblings_dict[source_id].append((target_triple, sibling, pattern_freq))
                    else:
                        siblings_dict[source_id] = [(target_triple, sibling, pattern_freq)]
        return siblings_dict, siblings_num

    def map_stop_terms(self, stop_list_obj):
        stop_terms_ids = set()
        for term in stop_list_obj.stop_words:
            term_id = self.engine.term_id_map.get(term, -1)
            if term_id != -1:
                stop_terms_ids.add(term_id)
        logging.info("MAPPED %d/%d STOP TERMS" % (len(stop_terms_ids), len(stop_list_obj.stop_words)))
        for term in stop_list_obj.stop_words:
            term_id = self.engine.term_id_map.get(term, -1)
            if term_id == -1:
                logging.info("TERM NOT FOUND IN INDEX: %s" % term)
        stop_terms_ids.add(-1)
        return stop_terms_ids

    def map_concept_net(self, concept_net_obj):
        concept_net = dict()
        mapped = 0
        for rel_type, arg1, arg2, pos in concept_net_obj.relations:
            arg_1_id = self.engine.term_id_map.get(arg1)
            arg_2_id = self.engine.term_id_map.get(arg2)
            if arg_1_id is not None and arg_2_id is not None:
                mapped += 1
                if arg_1_id in concept_net:
                    concept_net[arg_1_id].add(arg_2_id)
                else:
                    concept_net[arg_1_id] = {arg_2_id}
        logging.info("USING %d RELATIONS FROM CONCEPT NET" % mapped)
        return concept_net

    def find_potential_sources(self, term, threshold=0):
        """
        Find all potential sources for given target term and calculate their frequencies.
        """

        target_term_id = self.engine.term_id_map.get(term)
        if target_term_id is None:
            return None
        target_triples = self.engine.search(arg_query=(target_term_id,))
        target_triples_num = len(target_triples)
        target_triples_freq = sum([target[-1] for target in target_triples])
        print "\tTARGET: triples %d, frequency %d" % (target_triples_num, target_triples_freq)
        print "\tFOUND TARGET TRIPLES FOR %s: %d" % (term, len(target_triples))
        target_triples = filter(lambda s: s[-1] >= threshold, target_triples)
        print "\tAFTER FILTERING (f>=%f): %d" % (threshold, len(target_triples))
        target_triples = filter(lambda tr: not self.is_light_triple(tr), target_triples)
        print "\tAFTER IGNORING LIGHT TRIPLES: %d" % len(target_triples)
        source_triples, source_triple_num = self.find_source_triples(target_term_id, target_triples)
        print "\tFOUND SOURCE TRIPLES FOR %s: %d" % (term, source_triple_num)
        potential_sources = []
        stops_ignored = 0
        cnect_ignored = 0

        for source_term_id, triples in source_triples.iteritems():
            if source_term_id in self.stop_terms:
                stops_ignored += 1
                continue
            if target_term_id in self.concept_net and source_term_id in self.concept_net[target_term_id]:
                cnect_ignored += 1
                continue
            if source_term_id in self.concept_net and target_term_id in self.concept_net[source_term_id]:
                cnect_ignored += 1
                continue

            new_source = PotentialSource(source_term_id, triples)
            new_source.calculate_freqs()
            potential_sources.append(new_source)
        print "\tSTOPS IGNORED: %d" % stops_ignored
        print "\tCONCEPT NET IGNORED: %d" % cnect_ignored
        potential_sources.sort(key=lambda source: -source.norm_freq)
        return potential_sources

    def format_source_output_line(self, potential_source):
        triples = potential_source.triples
        triples_str = ""
        for triple, norm_freq in triples:
            if triple[1] >= 0:
                triples_str += "{%s" % self.engine.id_term_map[triple[1]]
            else:
                triples_str += "{NONE"
            for term_id in triple[2:(len(triple) - 1)]:
                if term_id >= 0:
                    triples_str += ";" + self.engine.id_term_map[term_id]
                else:
                    triples_str += "NONE"
            triples_str += ";%.6f} " % norm_freq
        return "%s\t%.6f\t%d\t%d\t%d\t%s" % (
            self.engine.id_term_map[potential_source.source_id],
            potential_source.norm_freq,
            len(potential_source.triples),
            potential_source.total_pattern_source_triple_freq,
            potential_source.total_pattern_target_triple_freq,
            triples_str,
        )
