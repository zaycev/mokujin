#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

import os
import sys
import pickle
import leveldb
import logging
import sqlite3
import argparse
import itertools


ARG_NONE = 0x0
ARG_EMPTY = 0x1
NODE_CLASS = 0x2
NODE_INSTANCE = 0x3


class YagoEntry(object):
    
    def __init__(self, wn_node, rdf_label, node_type, lang=None):
        self.node = wn_node
        self.label = rdf_label.lower()
        self.type = node_type
        self.lang = lang
    
    @staticmethod
    def from_tsv_line(line, node_type, simplify=True):
        line = line.decode("utf-8")
        row = line.split("\t")
        if simplify:
            wn_node = row[1]
            rdf_label = row[3].lower()
            label_parts = rdf_label.split("@")
            lang = label_parts[-1]
            rdf_label = "".join(label_parts[0:(len(label_parts) - 1)])
            rdf_label = rdf_label[1:(len(rdf_label) - 1)]
            return YagoEntry(wn_node, rdf_label, node_type, lang)
        else:
            wn_node = row[1]
            rdf_label = row[3].lower()
            label_parts = rdf_label.split("@")
            lang = label_parts[-1]
            return YagoEntry(wn_node, rdf_label, node_type, lang)
        
    def __repr__(self):
        if self.type is NODE_CLASS:
            repr_str = u"<YagoEntry(class, %s, %s, \"%s\")>" % (self.lang, self.node, self.label)
        else:
            repr_str = u"<YagoEntry(instance, %s, %s, \"%s\")>" % (self.lang, self.node, self.label)
        return repr_str.encode("utf-8")


class YagoDict(object):
    
    SQL_CREATE_TABLE_STATEMENTS = (
        """
        CREATE TABLE IF NOT EXISTS yago (
            id INTEGER NOT NULL,
            label VARCHAR(128) NOT NULL,
            node VARCHAR(128) NOT NULL,
            type INTEGER NOT NULL,
            lang VARCHAR(3),
            PRIMARY KEY (id)
        );
        """,
        "CREATE UNIQUE INDEX IF NOT EXISTS `yago_id_idx` ON `yago` (`id` ASC);",
        "CREATE INDEX IF NOT EXISTS `yago_label_idx` ON `yago` (`label` ASC);",
        "CREATE INDEX IF NOT EXISTS `yago_node_idx` ON `yago` (`node` ASC);",
    )
    
    def __init__(self, yago_dir, db_dir):
        self.kvs_place = "%s/kvs.db" % db_dir
        self.sql_place = "%s/sql.db" % db_dir
        self.sql = sqlite3.connect(self.sql_place)
        self.kvs = leveldb.LevelDB(self.kvs_place)
        self.sql_cursor = self.sql.cursor()
        self.kvs_batch = leveldb.WriteBatch()
        self.yago_dir = yago_dir
        self.db_dir = db_dir
        self.__sql_counter = 0
        self.__kvs_counter = 0
        for statement in YagoDict.SQL_CREATE_TABLE_STATEMENTS:
            self.sql_cursor.execute(statement)
        self.sql.commit()
        
    @staticmethod
    def create(yago_dir, db_dir, lang=None):
        yago_classes_fl = "%s/yagoMultilingualClassLabels.tsv" % yago_dir
        yago_instances_fl = "%s/yagoMultilingualInstanceLabels.tsv" % yago_dir
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            print db_dir
        yago = YagoDict(yago_dir, db_dir)
        with open(yago_classes_fl, "rb") as tsvin:
            for line in tsvin:
                entry = YagoEntry.from_tsv_line(line, NODE_CLASS)
                if lang is not None and entry.lang == lang:
                    yago.sql_insert_entry(entry)
                elif lang is None:
                    yago.sql_insert_entry(entry)
        with open(yago_instances_fl, "rb") as tsvin:
            for line in tsvin:
                entry = YagoEntry.from_tsv_line(line, NODE_INSTANCE)
                if lang is not None and entry.lang == lang:
                    yago.sql_insert_entry(entry)
                elif lang is None:
                    yago.sql_insert_entry(entry)
        yago.sql.commit()
        yago.create_kvs_from_sql()
        return yago
            
    def create_kvs_from_sql(self):
        prev = None
        node_set = None
        for label, node in self.sql_cursor.execute("SELECT label,node FROM yago ORDER BY label;"):
            if label != prev:
                if node_set is not None and len(node_set) > 0:
                    self.kvs_insert_entryset(prev.encode("utf-8"), node_set)
                prev = label
                node_set = set()
            node_set.add(node)
        if node_set is not None and len(node_set) > 0:
            self.kvs_insert_entryset(prev.encode("utf-8"), node_set)
        self.kvs.Write(self.kvs_batch, sync=True)
    
    def sql_insert_entry(self, entry):
        if entry.lang is not None:
            sql_insert = u"INSERT INTO yago VALUES (?,?,?,?,?);"
            values = (self.__sql_counter, entry.label, entry.node, entry.type, entry.lang,)
            self.sql_cursor.execute(sql_insert, values)
        else:
            sql_insert = u"INSERT INTO yago VALUES (?,?,?,?);"
            values = (self.__sql_counter, entry.label, entry.node, entry.type,)
            self.sql_cursor.execute(sql_insert, values)
        self.__sql_counter += 1
        
    def kvs_insert_entryset(self, label, node_set):
        self.kvs_batch.Put(label, pickle.dumps(node_set, protocol=pickle.HIGHEST_PROTOCOL))
        self.__kvs_counter += 1
        if self.__kvs_counter % 100000 == 0:
            self.kvs.Write(self.kvs_batch, sync=True)

    def sql_map_lemma(self, lemma):
        sql_statement = "SELECT node FROM yago WHERE label=?;"
        nodes = [row[0] for row in self.sql_cursor.execute(sql_statement, (lemma, ))]
        if len(nodes) > 0:
            return set(nodes)
        return None

    def kvs_map_lemma(self, lemma):
        try:
            db_value = self.kvs.Get(lemma)
            return pickle.loads(db_value)
        except KeyError:
            return None

    def sql_map_like(self, lemmas):
        sql_statement = u"SELECT node FROM yago WHERE "
        where = []
        for lemma in lemmas:
            where.append(u"label LIKE '%" + lemma + "%'")
        sql_statement += " AND ".join(where) + ";"
        nodes = [row[0] for row in self.sql_cursor.execute(sql_statement)]
        # print "TRY: %s, FOUND %d" % (sql_statement.encode("utf-8"), len(nodes))
        return set(nodes)

    def sql_map_compound(self, lemmas, min_threshold=1, init_len=1, max_len=3):
        if len(lemmas) == 0:
            return None
        # if len(lemmas) == 1:
        #     return self.kvs_map_lemma(lemmas[0].encode("utf-8"))
        
        # best_comb = None
        best_nodes = None
        best_len = 0xFFFFFF
        # best_match_len = 0
        
        for comb_len in xrange(init_len, min(len(lemmas) + 1, max_len + 1)):
            combs = list(itertools.combinations(lemmas, comb_len))
            for comb in combs:
                nodes = self.sql_map_like(comb)
                if min_threshold <= len(nodes) <= best_len:
                    best_nodes = nodes
                    # best_comb = comb
                    best_len = len(best_nodes)
                    # best_match_len = len(best_comb)
    
        return best_nodes


def parse_triple_row(csv_row):
    rel_name = csv_row[0]
    freq = csv_row[-1]
    args = []
    for arg in csv_row[1:(len(csv_row)-1)]:
        if arg == "<NONE>":
            args.append(ARG_NONE)
        elif arg == "<->":
            args.append(ARG_EMPTY)
        else:
            arg = arg.split("-")
            pos = arg[-1]
            lemmas = "".join(arg[0:(len(arg) - 1)])
            args.append((lemmas, pos))
    return rel_name, args, freq


def map_triples(yago, triples_file, out_file):
    for line in triples_file:
        line = line.decode("utf-8")
        row = line.split(", ")
        rel_name, args, freq = parse_triple_row(row)
        out_file.write(rel_name)
        out_file.write(", ")
        for arg in args:
            if arg is ARG_NONE:
                out_file.write("<NONE>,")
            elif arg is ARG_EMPTY:
                out_file.write("<->,")
            else:
                lemmas, pos = arg
                if pos == "NN":
                    lemmas_set = lemmas.split("&&")
                    if len(lemmas_set) == 1:
                        nodes = yago.kvs_map_lemma(lemmas_set[0].encode("utf-8"))
                    else:
                        nodes = yago.sql_map_compound(lemmas_set)
                    if nodes is None or len(nodes) == 0:
                        lemma_node_sets = "{}"
                    else:
                        lemma_node_sets = "{%s}" % ";".join(nodes)
                    out_file.write(lemma_node_sets.encode("utf-8"))
                    out_file.write("/")
                    out_file.write(lemmas.encode("utf-8"))
                    out_file.write("-")
                    out_file.write(pos)
                    out_file.write(", ")
                else:
                    out_file.write(lemmas.encode("utf-8"))
                    out_file.write("-")
                    out_file.write(pos)
                    out_file.write(", ")
        out_file.write(freq)


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument("-y", "--yago", default=None, type=str, help="A path to the directory containing "
                                                                     "yagoMultilingualClassLabels.tsv and "
                                                                     "yagoMultilingualInstanceLabels.tsv files")
    parser.add_argument("-d", "--dbdir", default="yago.ldb", type=str, help="A path to the temp database directory"
                                                                            " which will be created")
    parser.add_argument("-c", "--createdb", default=1, type=int, choices=(0, 1), help="Create a temp db for YAGO if it "
                                                                                      "does not exist")
    parser.add_argument("-l", "--lang", default=None, type=str, help="A lang of the input data")
    parser.add_argument("-i", "--ifile", default=None, type=str, help="A path to the input csv file with the triples")
    parser.add_argument("-o", "--ofile", default=None, type=str, help="A path to the result file")

    args = parser.parse_args()

    in_file = file(args.ifile, "r") if args.ifile is not None else sys.stdin
    out_file = file(args.ofile, "w") if args.ofile is not None else sys.stdout
    yago_dir = args.yago
    db_dir = args.dbdir
    lang = args.lang
    create_db = args.createdb

    if create_db == 1:
        logging.info("CREATING A TEMP DB FOR YAGO(%s): %s" % (yago_dir, db_dir))
        yago = YagoDict.create(yago_dir, db_dir, lang)
    else:
        logging.info("LOADING TEMP DB: %s" % db_dir)
        yago = YagoDict(yago_dir, db_dir)

    logging.info("MAPPING TRIPLES FROM %s TO %s" % (in_file, out_file))
    
    map_triples(yago, in_file, out_file)
    
    logging.info("DONE")
