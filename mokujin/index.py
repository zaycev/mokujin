#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

import gc
import leveldb
import logging
import marshal as pickle

from mokujin import numencode
from mokujin.triples import ACTUAL_RELS


REL_ID_MAP = dict()
ID_REL_MAP = dict()

for rel in ACTUAL_RELS:
    REL_ID_MAP[rel.rel_name] = len(REL_ID_MAP)
    ID_REL_MAP[REL_ID_MAP[rel.rel_name]] = rel.rel_name


class ArgType(object):
    NONE = -1
    EMPTY = -2
    STR_NONE = "<NONE>"
    STR_EMPTY = "<->"
    POS_DELIMITER = "-"
    POS_NONE = "POS>"


class TripleReader(object):
    
    def parse_triple_row(self, ts_row):
        arguments = []
        for i in range(1, (len(ts_row) - 1)):
            argument = ts_row[i]
            if argument == ArgType.STR_NONE:
                arguments.append(ArgType.NONE)
            elif argument == ArgType.STR_EMPTY:
                arguments.append(ArgType.EMPTY)
            else:
                lemma_pos = argument.split(ArgType.POS_DELIMITER)
                if lemma_pos[-1] == ArgType.POS_NONE:
                    arguments.append(ArgType.NONE)
                else:
                    arguments.append("-".join(lemma_pos[0:(len(lemma_pos) - 1)]))
        return ts_row[0], arguments, int(ts_row[-1])

    def iter_triples(self, i_file):
        for line in i_file:
            row = line.split(", ")
            triple = self.parse_triple_row(row)
            yield triple


class TripleIndex(object):

    def __init__(self, data_dir):
        # term = str()
        # triple = str()
        # stamp(triple) = (int)
        self.data_dir = data_dir
        # table: id(term) -> term
        self.term_id_map = None
        # table: id(triple) -> stamp(triple)
        self.triple_id_map = None
        # table: id(term) -> stamp(triple)
        self.arg_cache = None
        self.rel_id_map = REL_ID_MAP
        self.id_rel_map = ID_REL_MAP
        try:
            import lz4 as compressor
            self.compress = compressor.compress
            self.compressHC = compressor.compressHC
            self.decompress = compressor.decompress
        except ImportError:
            import zlib as compressor
            self.compress = lambda data: compressor.compress(data, 3)
            self.compressHC = lambda data: compressor.compress(data, 9)
            self.decompress = lambda data: compressor.decompress(data)

    @staticmethod
    def triple2stamp(triple, term_id_map):
        rel_name = triple[0]
        rel_id = REL_ID_MAP[rel_name]
        args = triple[1]
        stamp = [rel_id]
        for arg in args:
            if arg == ArgType.NONE:
                stamp.append(arg)
            elif arg != ArgType.EMPTY:
                stamp.append(term_id_map[arg])
        stamp.append(triple[-1])
        return tuple(stamp)

    @staticmethod
    def stamp2triple(stamp, id_term_map, map_none=False):
        triple = [ID_REL_MAP[stamp[0]]]
        for i in range(1, len(stamp) - 1):
            if stamp[i] >= 0:
                triple.append(id_term_map[stamp[i]])
            else:
                if map_none:
                    triple.append("<NONE>")
                else:
                    triple.append(stamp[i])
        triple.append(stamp[-1])
        return triple

    @staticmethod
    def stamp_arg(stamp):
        return stamp[1: len(stamp) - 1]

    def __commit_triples(self, batch_size=64):
        triple_store = leveldb.LevelDB("%s/triple.db" % self.data_dir)
        batch = []
        tr_id = 0
        batch_key = 0
        while tr_id < len(self.triple_id_map):
            batch.append(self.triple_id_map[tr_id])
            if tr_id % batch_size == batch_size - 1:
                batch_data = self.compressHC(pickle.dumps(batch))
                triple_store.Put(numencode.encode_uint(batch_key), batch_data)
                batch = []
                batch_key += 1
            tr_id += 1
        if len(batch) > 0:
            batch_data = self.compressHC(pickle.dumps(batch))
            triple_store.Put(numencode.encode_uint(batch_key), batch_data)

    def load_triples(self, batch_size=64):
        id_triple_map = dict()
        triple_store = leveldb.LevelDB("%s/triple.db" % self.data_dir)
        for batch_key, batch_data in triple_store.RangeIter():
            batch = pickle.loads(self.decompress(batch_data))
            batch_key = numencode.decode_uint(batch_key)
            for i in xrange(len(batch)):
                tr_id = batch_key * batch_size + i
                id_triple_map[tr_id] = batch[i]
        return id_triple_map

    def __commit_terms(self, batch_size=64):
        term_store = leveldb.LevelDB("%s/term.db" % self.data_dir)
        batch = []
        term_id = 0
        batch_key = 0
        while term_id < len(self.term_id_map):
            batch.append(self.id_term_map[term_id])
            if term_id % batch_size == batch_size - 1:
                batch_data = self.compressHC(pickle.dumps(batch))
                term_store.Put(numencode.encode_uint(batch_key), batch_data)
                batch = []
                batch_key += 1
            term_id += 1
        if len(batch) > 0:
            batch_data = self.compressHC(pickle.dumps(batch))
            term_store.Put(numencode.encode_uint(batch_key), batch_data)

    def load_terms(self, batch_size=64):
        id_term_map = dict()
        term_store = leveldb.LevelDB("%s/term.db" % self.data_dir)
        for batch_key, batch_data in term_store.RangeIter():
            batch = pickle.loads(self.decompress(batch_data))
            batch_key = numencode.decode_uint(batch_key)
            for i in xrange(len(batch)):
                term_id = batch_key * batch_size + i
                id_term_map[term_id] = batch[i]
        return id_term_map

    def decode_posting_list(self, plist_data):
        plist = numencode.decode_plist(self.decompress(plist_data))
        return plist

    def encode_posting_list(self, plist):
        return self.compressHC(numencode.encode_plist(plist))

    def update_posting_list(self, old_plist_data, new_plist):
        plist_data = self.decompress(old_plist_data)
        updated_plist = numencode.update_plist(plist_data, new_plist)
        return self.compressHC(updated_plist)

    def __update_arg_index(self):
        w_batch = leveldb.WriteBatch()
        arg_index = leveldb.LevelDB("%s/arg.index" % self.data_dir)
        for term_id, plist in self.arg_cache.iteritems():
            term_key = numencode.encode_uint(term_id)
            try:
                old_plist_data = arg_index.Get(term_key)
            except KeyError:
                old_plist_data = None
            if old_plist_data is None:
                plist_data = self.encode_posting_list(plist)
            else:
                plist_data = self.update_posting_list(old_plist_data, plist)
            w_batch.Put(term_key, plist_data)
        arg_index.Write(w_batch, sync=True)

    def __cache_triple(self, triple_stamp):
        tr_id = len(self.triple_id_map)
        self.triple_id_map.append(triple_stamp)
        return tr_id

    def __cache_term(self, term):
        if term not in self.term_id_map:
            term_id = len(self.term_id_map)
            self.id_term_map.append(term)
            self.term_id_map[term] = term_id

    def __cache_arg_posting_list(self, triple_id, stamp):
        for i in range(1, len(stamp) - 1):
            if stamp[i] >= 0:
                if stamp[i] in self.arg_cache:
                    self.arg_cache[stamp[i]].append((triple_id, i))
                else:
                    self.arg_cache[stamp[i]] = [(triple_id, i)]

    def create_index(self, triples, threshold=10, cache_size=1000 ** 2):
        i = 0
        self.id_term_map = []
        self.term_id_map = dict()
        self.triple_id_map = []
        self.arg_cache = dict()
        cached = 0
        logging.info("starting creating index")
        for triple in triples:
            args = triple[1]
            freq = triple[-1]
            for term in args:
                if isinstance(term, basestring):
                    self.__cache_term(term)
            stamp = self.triple2stamp(triple, self.term_id_map)
            if freq > threshold:
                i += 1
                tr_id = self.__cache_triple(stamp)
                self.__cache_arg_posting_list(tr_id, stamp)
                cached += 1
                if cached > cache_size:
                    logging.info("%dM triples done, flushing cache" % i)
                    self.__update_arg_index()
                    cached = 0
                    self.arg_cache = dict()
                    gc.collect()
        self.__commit_terms()
        self.__commit_triples()
        self.__update_arg_index()
        self.arg_cache = dict()
        self.term_id_map = dict()
        self.triple_id_map = []

    def arg_index(self):
        return leveldb.LevelDB("%s/arg.index" % self.data_dir)


class SearchEngine(object):

    def __init__(self, triple_index):
        self.index = triple_index
        self.id_term_map = triple_index.load_terms()
        self.term_id_map = dict()
        self.id_triple_map = triple_index.load_triples()
        for term_id, term in self.id_term_map.iteritems():
            self.term_id_map[term] = term_id
        self.arg_index = triple_index.arg_index()

    def search(self, rel_type=None, arg_query=()):
        norm_query = []
        for arg in arg_query:
            if isinstance(arg, list) or isinstance(arg, tuple):
                term, pos = arg
                if isinstance(term, basestring):
                    if isinstance(term, unicode):
                        term = term.encode("utf-8")
                    term_id = self.term_id_map.get(term)
                else:
                    term_id = term
            elif isinstance(arg, basestring):
                term, pos = arg, -1
                if isinstance(term, unicode):
                    term = term.encode("utf-8")
                term_id = self.term_id_map.get(term)
            elif isinstance(arg, int):
                term_id, pos = arg, -1
            else:
                term_id, pos = None, -1
            if term_id is not None and term_id in self.id_term_map:
                norm_query.append((term_id, pos))
        results = []
        for term_id, pos in norm_query:
            try:
                plist_data = self.arg_index.Get(numencode.encode_uint(term_id))
                plist = self.index.decode_posting_list(plist_data)
            except KeyError:
                plist = []
            if pos != -1:
                plist = filter(lambda plist_el: plist_el[1] == pos, plist)
            plist = [plist_el[0] for plist_el in plist]
            plist = set(plist)
            results.append(plist)
        if len(results) > 0:
            final_result = results[0]
            for i in range(1, len(results)):
                final_result ^= results[i]
            results = [self.id_triple_map[triple_id] for triple_id in final_result]
            if rel_type is not None:
                results = filter(lambda triple: triple[0] == rel_type, results)
            return results
        return []

    def print_result(self, search_result, max_results=10):
        for triple in search_result[:max_results]:
            triple_str = "<Triple(%s, " % self.index.id_rel_map[triple[0]]
            for i in range(1, len(triple) - 1):
                if triple[i] >= 0:
                    triple_str += "%s, " % self.id_term_map[triple[i]]
                else:
                    triple_str += "NONE, "
            triple_str += " %d>" % triple[-1]
            print triple_str
