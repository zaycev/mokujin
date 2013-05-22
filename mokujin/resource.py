#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

import csv
import logging


class ConceptNetRelations(object):
    CRT = 0x00
    DRF = 0x01
    SYN = 0x02


class ConceptNetList(object):
    rel_id_map = {
        "ConceptuallyRelatedTo": ConceptNetRelations.CRT,
        "DerivedFrom": ConceptNetRelations.DRF,
        "Synonym": ConceptNetRelations.SYN
    }

    def __init__(self, relations):
        self.relations = relations

    @staticmethod
    def load(file_path, rels=None):
        relations = []
        with open(file_path, "rb") as fl:
            reader = csv.reader(fl, delimiter=";")
            for rel, arg1, arg2 in reader:
                arg_and_pos = arg2.split("/")
                if len(arg_and_pos) == 2:
                    arg2, pos = arg_and_pos
                else:
                    arg2, pos = arg_and_pos[0], None
                if rel == "ConceptuallyRelatedTo":
                    rel_short = "c"
                elif rel == "DerivedFrom":
                    rel_short = "d"
                elif rel == "Synonym":
                    rel_short = "s"
                else:
                    rel_short = None
                    print rel
                if rel_short in rels:
                    relations.append((ConceptNetList.rel_id_map[rel], arg1, arg2, pos))
        logging.info("LOADED %d %s CONCEPTS" % (len(relations), rels))
        return ConceptNetList(relations)


class StopList(object):

    def __init__(self, stop_words):
        self.stop_words = stop_words

    @staticmethod
    def load(file_path, threshold=500.0):
        stop_terms_set = set()
        try:
            with open(file_path, "rb") as csvfile:
                stop_terms = csv.reader(csvfile, delimiter=",")
                for rank, freq, lemma, pos in stop_terms:
                    freq = float(freq)
                    if freq >= threshold:
                        stop_terms_set.add(lemma)
                    else:
                        break
        except IOError:
            pass
        logging.info("LOADED %d (f<=%f) STOP WORDS" % (len(stop_terms_set), threshold))
        return StopList(stop_terms_set)
