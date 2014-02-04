#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

import gc
import os
import lz4
import plyvel
import logging
import StringIO
import marshal as pickle
import mokujin.triples as mtr

from mokujin import numencode
from mokujin.logicalform import POS
from mokujin.triples import ACTUAL_RELS


REL_ID_MAP = dict()
ID_REL_MAP = dict()

for rel in ACTUAL_RELS:
    REL_ID_MAP[rel.rel_name] = len(REL_ID_MAP)
    ID_REL_MAP[REL_ID_MAP[rel.rel_name]] = rel.rel_name


REL_POS_MAP = {
    REL_ID_MAP[mtr.DepVerb_SubjVerbDirobj.rel_name]: (POS.NN, POS.VB, POS.NN, ),
    REL_ID_MAP[mtr.DepVerb_SubjVerbIndirobj.rel_name]: (POS.NN, POS.VB, POS.NN, ),
    REL_ID_MAP[mtr.DepVerb_SubjVerbInstr.rel_name]: (POS.NN, POS.VB, POS.NN, ),
    REL_ID_MAP[mtr.DepVerb_SubjVerb.rel_name]: (POS.NN, POS.VB, ),
    REL_ID_MAP[mtr.DepVerb_PrepCompl.rel_name]: (POS.NN, POS.VB, POS.PREP, POS.NN, ),
    REL_ID_MAP[mtr.DepVerb_SubjVerbVerbPrepNoun.rel_name]: (POS.NN, POS.VB, POS.VB, POS.PREP, POS.NN, ),
    REL_ID_MAP[mtr.DepVerb_SubjVerbVerb.rel_name]: (POS.NN, POS.VB, POS.VB, ),
    REL_ID_MAP[mtr.DepAdj_NounAdj.rel_name]: (POS.NN, POS.ADJ, ),
    REL_ID_MAP[mtr.DepAdv_VerbNounAdv.rel_name]: (POS.NN, POS.VB, POS.RB, ),
    REL_ID_MAP[mtr.DepNoun_NounEqualPrepNoun.rel_name]: (POS.NN, POS.NN, POS.PREP, POS.NN, ),
    REL_ID_MAP[mtr.DepNoun_NounNoun.rel_name]: (POS.NN, POS.NN, ),
    REL_ID_MAP[mtr.DepNoun_NounNounNoun.rel_name]: (POS.NN, POS.NN, POS.NN, ),
    REL_ID_MAP[mtr.DepNoun_NounEqualNoun.rel_name]: (POS.NN, POS.NN, ),
    REL_ID_MAP[mtr.DepNoun_NounPrepNoun.rel_name]: (POS.NN, POS.PREP, POS.NN, ),
    REL_ID_MAP[mtr.DepAny_Compl.rel_name]: (POS.ANY, POS.ANY, ),
    REL_ID_MAP[mtr.DepNoun_NounEqualNoun.rel_name]: (POS.NN, POS.NN),
}

if len(REL_POS_MAP) != len(REL_ID_MAP):
    logging.error("NOT ALL RELATIONS HAS POS MAP")


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


class DepTupleIndex(object):
    """
    Dependency relation tuple indexer.

    This class stores

    """

    TUPLE_INDEX_DB_BLOCK_SIZE = 64
    TERM_INDEX_DB_BLOCK_SIZE  = 256
    PLIST_CACHE_SIZE          = 256000
    STRING_ARRAY_SEP          = chr(244)

    def __init__(self, index_root):
        self.index_root = index_root

        self.term_ldb   = DepTupleIndex.get_term_ldb(index_root, create=False)
        self.plist_ldb  = DepTupleIndex.get_plist_ldb(index_root, create=False)
        self.tuple_ldb  = DepTupleIndex.get_tuple_ldb(index_root, create=False)

        self.term2id    = {}
        self.id2term    = {}
        self.id2tuple   = {}
        self.reltype2id = REL_ID_MAP
        self.id2reltype = ID_REL_MAP

        DepTupleIndex.load_terms(self.term_ldb, self.id2term, self.term2id)
        DepTupleIndex.load_tuples(self.tuple_ldb, self.id2tuple)

    @staticmethod
    def tuple2stamp(d_tuple, term2id):
        args = d_tuple[1]
        stamp = [REL_ID_MAP[d_tuple[0]]]
        for arg in args:
            if arg == ArgType.NONE:
                stamp.append(arg)
            elif arg != ArgType.EMPTY:
                stamp.append(term2id[arg])
        stamp.append(d_tuple[-1])
        return tuple(stamp)

    @staticmethod
    def stamp2tuple(stamp, id2term, map_none=False):
        d_tuple = [ID_REL_MAP[stamp[0]]]
        for i in range(1, len(stamp) - 1):
            if stamp[i] >= 0:
                d_tuple.append(id2term[stamp[i]])
            else:
                if map_none:
                    d_tuple.append("<NONE>")
                else:
                    d_tuple.append(stamp[i])
        d_tuple.append(stamp[-1])
        return d_tuple

    @staticmethod
    def stamp_arg(stamp):
        return stamp[1: len(stamp) - 1]

    @staticmethod
    def get_tuple_ldb(index_root, create=False):
        db_path = os.path.join(index_root, "tuple.ldb")
        return plyvel.DB(db_path,
                         compression="snappy",
                         write_buffer_size=1024 * (1024 ** 2),  # 1 GB
                         block_size=512 * (1024 ** 2),          # 512 MB
                         bloom_filter_bits=8,
                         create_if_missing=create,
                         error_if_exists=create)

    @staticmethod
    def get_term_ldb(index_root, create=False):
        db_path = os.path.join(index_root, "term.ldb")
        return plyvel.DB(db_path,
                         compression="snappy",
                         write_buffer_size=1024 * (1024 ** 2),  # 1 GB
                         block_size=512 * (1024 ** 2),          # 512 MB
                         bloom_filter_bits=8,
                         create_if_missing=create,
                         error_if_exists=create)

    @staticmethod
    def get_plist_ldb(index_root, create=False):
        db_path = os.path.join(index_root, "plist.ldb")
        return plyvel.DB(db_path,
                         compression="snappy",
                         write_buffer_size=1024 * (1024 ** 2),  # 1 GB
                         block_size=512 * (1024 ** 2),          # 512 MB
                         bloom_filter_bits=8,
                         create_if_missing=create,
                         error_if_exists=create)

    @staticmethod
    def write_tuples(id2tuple, tuple_ldb):
        with tuple_ldb.write_batch() as wb:
            for tuple_id, stamp in id2tuple.iteritems():
                wb.put(str(tuple_id), pickle.dumps(stamp))
        logging.info("Wrote %d tuples on disk." % len(id2tuple))

    @staticmethod
    def load_tuples(tuple_ldb, id2tuple):
        for tuple_id_str, stamp_blob in tuple_ldb:
            tuple_id = int(tuple_id_str)
            id2tuple[tuple_id] = pickle.loads(stamp_blob)
        logging.info("Loaded %d tuples into the memory." % len(id2tuple))

    @staticmethod
    def write_terms(term2id, term_ldb):
        with term_ldb.write_batch() as wb:
            for term, term_id in term2id.iteritems():
                wb.put(str(term_id), term)
        logging.info("Wrote %d terms on disk." % len(term2id))

    @staticmethod
    def load_terms(term_ldb, id2term, term2id):
        for term_id_str, term in term_ldb:
            term_id = int(term_id_str)
            id2term[term_id] = term
            term2id[term] = term_id
        logging.info("Loaded %d terms into the memory." % len(id2term))

    @staticmethod
    def decode_posting_list(plist_blob):
        plist = numencode.decode_plist(lz4.decompress(plist_blob))
        return plist

    @staticmethod
    def encode_posting_list(plist):
        return lz4.compressHC(numencode.encode_plist(plist))

    @staticmethod
    def update_posting_list(old_plist_blob, new_plist):
        plist_blob = lz4.decompress(old_plist_blob)
        updated_plist = numencode.update_plist(plist_blob, new_plist)
        return lz4.compressHC(updated_plist)

    @staticmethod
    def write_plists(plist_dict, plist_ldb, final_iteration=True):
        plist_dict_dict = {}
        with plist_ldb.write_batch() as wb:
            for term_id, plist in plist_dict.iteritems():
                if 50 <= len(plist) <= 100000 and not final_iteration:
                    plist_dict_dict[term_id] = plist
                    continue
                term_key = numencode.encode_uint(term_id)
                try:
                    old_plist_blob = plist_ldb.get(term_key)
                except KeyError:
                    old_plist_blob = None
                if old_plist_blob is None:
                    plist_blob = DepTupleIndex.encode_posting_list(plist)
                else:
                    plist_blob = DepTupleIndex.update_posting_list(old_plist_blob, plist)
                wb.put(term_key, plist_blob)
        logging.info("Wrote %d posting lists on disk." % len(plist_dict))
        return plist_dict_dict

    @staticmethod
    def create(index_root, tuples, freq_threshold=5):

        id2term    = {}
        term2id    = {}
        id2tuple   = {}
        plist_dict = {}

        term_ldb   = DepTupleIndex.get_term_ldb(index_root, create=True)
        plist_ldb  = DepTupleIndex.get_plist_ldb(index_root, create=True)
        tuple_ldb  = DepTupleIndex.get_tuple_ldb(index_root, create=True)

        cached = 0
        logging.info("Beginning creating index.")

        for line_no, d_tuple in enumerate(tuples):

            dep_arguments = d_tuple[1]
            dep_frequency = d_tuple[-1]

            if line_no % 25000 == 0:
                logging.info("Indexing tuple #%d. Freq=%d." % (line_no, dep_frequency))

            for term in dep_arguments:

                # Skip special terms.
                if term == -1 or term == -2:
                    continue

                # Add term to dictionary.
                term_id = term2id.get(term, -1)
                if term_id == -1:
                    term_id = len(term2id)
                    term2id[term] = term_id
                    id2term[term_id] = term

            # Get compact representation of dependency tuple.
            stamp = DepTupleIndex.tuple2stamp(d_tuple, term2id)

            if dep_frequency > freq_threshold:

                # Generate ID for new tuple.
                tuple_id = len(id2tuple)
                id2tuple[tuple_id] = stamp

                for arg_idx, arg in enumerate(stamp[1:-1]):
                    if arg >= 0:
                        arg_plist = plist_dict.get(arg)
                        if arg_plist is None:
                            plist_dict[arg] = [(tuple_id, arg_idx)]
                        else:
                            plist_dict[arg].append((tuple_id, arg_idx))

                cached += 1
                if cached == DepTupleIndex.PLIST_CACHE_SIZE:
                    logging.info("Writing %d posting lists to disc." % len(plist_dict))
                    plist_dict = DepTupleIndex.write_plists(plist_dict, plist_ldb, final_iteration=False)
                    cached = 0

                    gc.collect()

        DepTupleIndex.write_terms(term2id, term_ldb)
        DepTupleIndex.write_tuples(id2tuple, tuple_ldb)
        DepTupleIndex.write_plists(plist_dict, plist_ldb, final_iteration=True)


class TripleSearchEngine(object):

    def __init__(self, triple_index):
        self.index = triple_index
        self.id_term_map = triple_index.id2term
        self.term_id_map = triple_index.term2id
        self.id_triple_map = triple_index.id2tuple
        self.arg_index = triple_index.plist_ldb

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
        results = None
        for term_id, pos in norm_query:
            try:
                plist_blob = self.arg_index.get(numencode.encode_uint(term_id))
                plist = self.index.decode_posting_list(plist_blob)
            except KeyError:
                plist = []
            if pos != -1:
                plist = filter(lambda plist_el: plist_el[1] == pos, plist)
            plist = [plist_el[0] for plist_el in plist]
            plist = set(plist)
            if results is None:
                results = plist
            else:
                results &= plist
        if results is None:
            return ()
        results = [self.id_triple_map[triple_id] for triple_id in results]
        if rel_type is not None:
            results = filter(lambda triple: triple[0] == rel_type, results)
        return results

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

    def pprint(self, triple):
        pstr = StringIO.StringIO()
        pstr.write("{")
        pstr.write(ID_REL_MAP[triple[0]])
        pstr.write(";")
        terms = ";".join([self.id_term_map[term_id] if term_id >= 0 else "NONE" for term_id in triple[1:-1]])
        pstr.write(terms)
        pstr.write("}")
        return pstr.getvalue()


class SimpleObjectIndex(object):

    def __init__(self, data_dir, obj_to_terms, obj_to_str, str_to_obj):
        self.data_dir = data_dir
        self.obj_to_terms = obj_to_terms
        self.obj_to_str = obj_to_str
        self.str_to_obj = str_to_obj
        self.id_term_map = None
        self.term_id_map = None
        self.objnum = 0
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

    def load_all(self):
        id_term_map = self.load_terms()
        self.id_term_map = [None] * len(id_term_map)
        self.term_id_map = dict()
        for term_id, term in id_term_map.iteritems():
            self.id_term_map[term_id] = term
            self.term_id_map[term] = term_id
        self.objnum = self.load_objnum()

    def load_objnum(self):
        objnum_fl_path = "%s/OBJNUM" % self.data_dir
        try:
           with open(objnum_fl_path, "r") as objnum_fl:
               objnum = int(objnum_fl.read())
        except IOError:
            objnum = 0
        logging.info("LOADED DOCNUM %d" % objnum)
        return objnum

    def update_objnum(self, new_objnum):
        objnum_fl_path = "%s/OBJNUM" % self.data_dir
        prev_objnum = self.load_objnum()
        with open(objnum_fl_path, "w") as objnum_fl:
            objnum_fl.write(str(new_objnum))
        logging.info("OBJNUM updated %d => %d [+%d]" % (prev_objnum, new_objnum, new_objnum - prev_objnum))
        return new_objnum - prev_objnum

    def decode_posting_list(self, plist_blob):
        plist = numencode.decode_1d_plist(self.decompress(plist_blob))
        return plist

    def encode_posting_list(self, plist):
        return self.compressHC(numencode.encode_1d_plist(plist))

    def update_posting_list(self, old_plist_blob, new_plist):
        plist_blob = self.decompress(old_plist_blob)
        updated_plist = numencode.update_1d_plist(plist_blob, new_plist)
        return self.compressHC(updated_plist)

    def update_posting_lists(self, post_lists):
        plist_store = leveldb.LevelDB("%s/plist.index" % self.data_dir)
        w_batch = leveldb.WriteBatch()
        upd_num = 0
        new_num = 0
        for term_id, plist in post_lists.iteritems():
            term_key = numencode.encode_uint(term_id)
            try:
                old_plist_blob = plist_store.Get(term_key)
                upd_num += 1
            except KeyError:
                new_num += 1
                old_plist_blob = None
            if old_plist_blob is None:
                plist_blob = self.encode_posting_list(plist)
            else:
                plist_blob = self.update_posting_list(old_plist_blob, plist)
            w_batch.Put(term_key, plist_blob)
        plist_store.Write(w_batch, sync=True)
        logging.info("updated %d plists, %d new" % (upd_num, new_num))

    def load_posting_list(self, term_id, plist_store):
        term_key = numencode.encode_uint(term_id)
        plist_blob = plist_store.Get(term_key)
        plist = self.decode_posting_list(plist_blob)
        return plist

    def write_objects(self, id_object_map):
        object_store = leveldb.LevelDB("%s/object.db" % self.data_dir)
        w_batch = leveldb.WriteBatch()
        for obj_id, obj in id_object_map:
            obj_str = self.obj_to_str(obj)
            obj_blob = self.compressHC(obj_str)
            obj_key = numencode.encode_uint(obj_id)
            w_batch.Put(obj_key, obj_blob)
        object_store.Write(w_batch, sync=True)
        logging.info("wrote %d objects" % len(id_object_map))
        self.update_objnum(self.objnum)

    def load_object(self, obj_id, obj_store):
        obj_key = numencode.encode_uint(obj_id)
        obj_blob = obj_store.Get(obj_key)
        obj_str = self.decompress(obj_blob)
        obj = self.str_to_obj(obj_str)
        return obj

    def write_terms(self, id_term_map, batch_size=64):
        term_store = leveldb.LevelDB("%s/term.db" % self.data_dir)
        batch = []
        term_id = 0
        batch_key = 0
        while term_id < len(id_term_map):
            batch.append(id_term_map[term_id])
            if term_id % batch_size == batch_size - 1:
                batch_data = self.compressHC(pickle.dumps(batch))
                term_store.Put(numencode.encode_uint(batch_key), batch_data)
                batch = []
                batch_key += 1
            term_id += 1
        if len(batch) > 0:
            batch_data = self.compressHC(pickle.dumps(batch))
            term_store.Put(numencode.encode_uint(batch_key), batch_data)
        logging.info("wrote %d terms" % len(id_term_map))

    def load_terms(self, batch_size=64):
        id_term_map = dict()
        term_store = leveldb.LevelDB("%s/term.db" % self.data_dir)
        for batch_key, batch_data in term_store.RangeIter():
            batch = pickle.loads(self.decompress(batch_data))
            batch_key = numencode.decode_uint(batch_key)
            for i in xrange(len(batch)):
                term_id = batch_key * batch_size + i
                id_term_map[term_id] = batch[i]
        logging.info("INDEX: LOADED %d TERMS" % len(id_term_map))
        return id_term_map

    def index_term(self, term, object_id, post_lists):
        term_id = self.term_id_map.get(term, -1)
        if term_id == -1:
            term_id = len(self.term_id_map)
            self.term_id_map[term] = term_id
            self.id_term_map.append(term)
        plist = post_lists.get(term_id, -1)
        if plist == -1:
            post_lists[term_id] = [object_id]
        else:
            plist.append(object_id)

    def update_index(self, objects, cache_size=(200000, 80000000)):
        post_lists = dict()
        id_obj_map = []
        cached = 0
        logging.info("starting creating index")
        for obj in objects:
            terms = self.obj_to_terms(obj)
            for term in terms:
                self.index_term(term, self.objnum, post_lists)
                cached += 1
                if cached > cache_size[1]:
                    self.update_posting_lists(post_lists)
                    post_lists = dict()
                    cached = 0
            id_obj_map.append((self.objnum, obj))
            if len(id_obj_map) > cache_size[0]:
                self.write_objects(id_obj_map)
                id_obj_map = []
            self.objnum += 1
        self.write_objects(id_obj_map)
        self.update_posting_lists(post_lists)
        self.write_terms(self.id_term_map)
        logging.info("index done")

    def find(self, query_terms_cnf=None):
        for query_terms in query_terms_cnf:
            plist_store = leveldb.LevelDB("%s/plist.index" % self.data_dir)
            object_store = leveldb.LevelDB("%s/object.db" % self.data_dir)
            if query_terms is None:
                continue
            result_ids = set()
            for query_term in query_terms:
                term_id = self.term_id_map.get(query_term, -1)
                logging.info("TERM ID: %d" % term_id)
                if term_id == -1:
                    logging.info("TERM NOT FOUND IN DICTIONARY")
                    continue
                plist = self.load_posting_list(term_id, plist_store)
                result_ids.update(plist)
            logging.info("RETRIEVING %d OBJECTS FROM DISK" % len(result_ids))
            for obj_id in result_ids:
                obj = self.load_object(obj_id, object_store)
                yield obj