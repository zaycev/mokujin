#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

import re
import os
import sys
import pickle
import leveldb
import logging
import sqlite3
import argparse
import itertools
import collections


ARG_NONE = 0x0
ARG_EMPTY = 0x1


class NodeType(object):
    WORDNET = 0x1
    OWL = 0x2
    WIKI_INSTANCE = 0x3
    WIKI_CATEGORY = 0x4
    YAGO = 0x5


class ConceptRelation(object):
    ConceptuallyRelatedTo = 0x1
    DerivedFrom = 0x2
    Synonym = 0x3


class Output(object):

    def __init__(self, debug, out_file):
        self.out_file = out_file
        self.debug = debug
        self.out_files = dict()
        if debug:
            if not os.path.exists("debug"):
                os.makedirs("debug")

    def get_file(self, rel_class=None, compound=False):
        if self.debug:
            if compound:
                fl = self.out_files.get("compound", None)
                if fl is None:
                    fl = open("debug/compound.txt", "w")
                    self.out_files["compound"] = fl
                    return fl
                return fl
            fl = self.out_files.get(rel_class, None)
            if fl is None:
                fl = open("debug/%s.txt" % rel_class, "w")
                self.out_files[rel_class] = fl
                return fl
            return fl
        return self.out_file

    def close(self):
        for fl in self.out_files.itervalues():
            fl.close()


class StatCollector(object):

    def __init__(self):
        self.conceptnet_total_found = 0
        self.conceptnet_total_missed = 0
        self.conceptner_arg_found = collections.Counter()
        self.conceptner_arg_missed = collections.Counter()
        self.total_reltype = 0
        self.total_reltype_handled = 0
        self.total_reltype_missed = 0
        self.total_args = 0
        self.total_args_missed = 0
        self.total_args_handled = 0
        self.reltype_stat = collections.Counter()
        self.reltype_handled_stat = collections.Counter()
        self.reltype_missed_stat = collections.Counter()
        self.arg_stat = collections.Counter()
        self.arg_handled_stat = collections.Counter()
        self.arg_missed_stat = collections.Counter()

    def update_conceptnet(self, concept_lemma, found):
        if found:
            self.conceptner_arg_found[concept_lemma] += 1
            self.conceptnet_total_found += 1
        else:
            self.conceptner_arg_missed[concept_lemma] += 1
            self.conceptnet_total_missed += 1

    def update_arg(self, arg, found):
        self.total_args += 1
        self.arg_stat[arg] += 1
        if found:
            self.total_args_handled += 1
            self.arg_handled_stat[arg] += 1
        else:
            self.total_args_missed += 1
            self.arg_missed_stat[arg] += 1

    def update_rel(self, reltype, found):
        self.total_reltype += 1
        self.reltype_stat[reltype] += 1
        if found:
            self.total_reltype_handled += 1
            self.reltype_handled_stat[reltype] += 1
        else:
            self.total_reltype_missed += 1
            self.reltype_missed_stat[reltype] += 1

    def save(self, to_filename):
        main_stat_fl = open("%s.stat.main.txt" % to_filename, "w")
        arg_stat_fl = open("%s.stat.arg.all.txt" % to_filename, "w")
        arg_missed_stat_fl = open("%s.stat.arg.missed.txt" % to_filename, "w")
        arg_handled_stat_fl = open("%s.stat.arg.handled.txt" % to_filename, "w")
        conceptnet_found_stat_fl = open("%s.stat.concept.found.txt" % to_filename, "w")
        conceptnet_missed_stat_fl = open("%s.stat.concept.missed.txt" % to_filename, "w")

        main_stat_fl.write("Total triples: %d\n" % self.total_reltype)
        main_stat_fl.write("Total triples handled: %d\n" % self.total_reltype_handled)
        main_stat_fl.write("Total triples missed: %d\n" % self.total_reltype_missed)
        main_stat_fl.write("Conceptnet improved args: %d\n" % self.conceptnet_total_found)
        main_stat_fl.write("Conceptnet not improved args: %d\n" % self.conceptnet_total_missed)

        main_stat_fl.write("\nTotal args: %d\n" % self.total_args)
        main_stat_fl.write("Total args handled: %d\n" % self.total_args_handled)
        main_stat_fl.write("Total args missed: %d\n" % self.total_args_missed)

        main_stat_fl.write("\nBy reltype (total):\n")
        for rel_type, freq in self.reltype_stat.most_common():
            main_stat_fl.write("%s:\t%d\n" % (rel_type, freq))

        main_stat_fl.write("\nBy reltype (handled):\n")
        for rel_type, freq in self.reltype_handled_stat.most_common():
            main_stat_fl.write("%s:\t%d\n" % (rel_type, freq))

        main_stat_fl.write("\nBy reltype (missed):\n")
        for rel_type, freq in self.reltype_missed_stat.most_common():
            main_stat_fl.write("%s:\t%d\n" % (rel_type, freq))

        main_stat_fl.write("\n")

        for arg, freq in self.arg_stat.most_common():
            arg_stat_fl.write(("%s\t%d\n" % (arg, freq)).encode("utf-8"))

        for arg, freq in self.arg_handled_stat.most_common():
            arg_handled_stat_fl.write(("%s\t%d\n" % (arg, freq)).encode("utf-8"))

        for arg, freq in self.arg_missed_stat.most_common():
            arg_missed_stat_fl.write(("%s\t%d\n" % (arg, freq)).encode("utf-8"))

        for arg, freq in self.conceptner_arg_found.most_common():
            conceptnet_found_stat_fl.write(("%s\t%d\n" % (arg, freq)).encode("utf-8"))

        for arg, freq in self.conceptner_arg_missed.most_common():
            conceptnet_missed_stat_fl.write(("%s\t%d\n" % (arg, freq)).encode("utf-8"))

        main_stat_fl.close()
        arg_stat_fl.close()
        arg_missed_stat_fl.close()
        arg_handled_stat_fl.close()
        conceptnet_found_stat_fl.close()
        conceptnet_missed_stat_fl.close()


class YagoEntry(object):
    word_re = re.compile(ur"\b[^\W\d_]+\b", re.UNICODE)

    def __init__(self, wn_node, rdf_label, lang=None):
        self.node = wn_node
        self.label = rdf_label.lower()
        self.lang = lang

    @staticmethod
    def instance_size(inst_node):
        return len(YagoEntry.word_re.findall(inst_node))

    @staticmethod
    def from_tsv_line(tsv_line, simplify=True):
        tsv_line = tsv_line.decode("utf-8")
        row = tsv_line.split("\t")
        if simplify:
            wn_node = row[1]
            rdf_label = row[3].lower()
            label_parts = rdf_label.split("@")
            lang = label_parts[-1]
            rdf_label = "".join(label_parts[0:(len(label_parts) - 1)])
            rdf_label = rdf_label[1:(len(rdf_label) - 1)]
            return YagoEntry(wn_node, rdf_label, lang)
        else:
            wn_node = row[1]
            rdf_label = row[3].lower()
            label_parts = rdf_label.split("@")
            lang = label_parts[-1]
            return YagoEntry(wn_node, rdf_label, lang)

    @staticmethod
    def is_class(node):
        if node.startswith("<wordnet"):
            return True
        return False

    @staticmethod
    def extract_transition(tsv_line):
        line = tsv_line.decode("utf-8")
        row = line.split("\t")
        return row[1], row[3]

    def __repr__(self):
        repr_str = u"<YagoEntry(%s, %s, \"%s\")>" % (self.lang, self.node, self.label)
        return repr_str.encode("utf-8")


class YagoDict(object):
    SQL_CREATE_TABLE_STATEMENTS = (
        """
        CREATE TABLE IF NOT EXISTS yago_node (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label VARCHAR(128) NOT NULL,
            node VARCHAR(128) NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS yago_cpnd (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part VARCHAR(128) NOT NULL,
            node INTEGER NOT NULL,
            UNIQUE (part, node)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS yago_taxn (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ins VARCHAR(64) NOT NULL,
            cls VARCHAR(64) NOT NULL,
            UNIQUE (ins, cls)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS yago_hrch (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child VARCHAR(64) NOT NULL,
            parent VARCHAR(64) NOT NULL,
            UNIQUE (parent, child)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS conceptnet (
            rel INT2 NOT NULL,
            concept VARCHAR(64) NOT NULL,
            form VARCHAR(64) NOT NULL,
            pos VARCHAR(1) NOT NULL DEFAULT '?',
            PRIMARY KEY (rel, concept, form, pos)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS names (
            name VARCHAR(128),
            PRIMARY KEY (name)
        );
        """,

        "CREATE UNIQUE INDEX IF NOT EXISTS `yago_node_id_idx` ON `yago_node` (`id` ASC);",
        "CREATE INDEX IF NOT EXISTS `yago_node_label_idx` ON `yago_node` (`label` ASC);",
        "CREATE INDEX IF NOT EXISTS `yago_node_node_idx` ON `yago_node` (`node` ASC);",

        "CREATE UNIQUE INDEX IF NOT EXISTS `yago_cpnd_id_idx` ON `yago_cpnd` (`id` ASC);",
        "CREATE INDEX IF NOT EXISTS `yago_cpnd_part_idx` ON `yago_cpnd` (`part` ASC);",
        "CREATE INDEX IF NOT EXISTS `yago_cpnd_node_idx` ON `yago_cpnd` (`node` ASC);",

        "CREATE UNIQUE INDEX IF NOT EXISTS `yago_taxn_id_idx` ON `yago_taxn` (`id` ASC);",
        "CREATE INDEX IF NOT EXISTS `yago_taxn_ins_idx` ON `yago_taxn` (`ins` ASC);",
        "CREATE INDEX IF NOT EXISTS `yago_taxn_cls_idx` ON `yago_taxn` (`cls` ASC);",

        "CREATE INDEX IF NOT EXISTS `yago_hrch_child_idx` ON `yago_hrch` (`child` ASC);",
        "CREATE INDEX IF NOT EXISTS `yago_hrch_parent_idx` ON `yago_hrch` (`parent` ASC);",

        "CREATE INDEX IF NOT EXISTS `conceptnet_concept_idx` ON `conceptnet` (`concept` ASC);",
        "CREATE INDEX IF NOT EXISTS `conceptnet_form_idx` ON `conceptnet` (`form` ASC);",

        "CREATE INDEX IF NOT EXISTS `names_name_idx` ON `names` (`name` ASC);",
    )

    SQL_MAP_LEMMA = "SELECT node FROM yago_node WHERE label=?;"
    SQL_IS_NAME = "SELECT name FROM names WHERE name=?;"
    SQL_FIND_ALL_CLASSES = "SELECT parent FROM yago_hrch WHERE child=?;"
    SQL_FIND_CLASS = "SELECT cls FROM yago_taxn WHERE ins=?;"
    SQL_FIND_CONCEPT = "SELECT concept FROM conceptnet WHERE form=?;"
    SQL_FIND_CONCEPT_REL = "SELECT concept FROM conceptnet WHERE form=? AND rel=?;"
    SQL_FIND_PARENT = "SELECT parent FROM yago_hrch WHERE child=?;"
    SQL_INSERT_ENTRYSET = "INSERT INTO yago_cpnd (part, node) VALUES (?,?);"
    SQL_INSERT_NAME = "INSERT INTO names (name) VALUES (?);"
    SQL_INSERT_TXN_RELATION = "INSERT INTO yago_hrch (child, parent) VALUES (?,?);"
    SQL_INSERT_TXN_TRANSITION = "INSERT INTO yago_taxn (ins, cls) VALUES (?,?);"
    SQL_INSERT_ENTRY = "INSERT INTO yago_node (label, node) VALUES (?,?);"
    SQL_INSERT_CONCEPT = "INSERT INTO conceptnet (rel,concept,form,pos) VALUES (?,?,?,?);"
    SQL_SELECT_DISTINCT_NODES = "SELECT DISTINCT(node) FROM yago_node ORDER BY node ASC;"
    NODE_PERSON = {"<wordnet_person_100007846>", "<wordnet_person_105217688>"}

    def __init__(self, yago_dir, db_dir):
        self.kvs_place = "%s/kvs.db" % db_dir
        self.idx_place = "%s/idx.db" % db_dir
        self.sql_place = "%s/sql.db" % db_dir
        self.txn_place = "%s/txn.db" % db_dir
        self.par_place = "%s/par.db" % db_dir

        self.sql = sqlite3.connect(self.sql_place)
        self.kvs = leveldb.LevelDB(self.kvs_place)
        self.idx = leveldb.LevelDB(self.idx_place)
        self.par = leveldb.LevelDB(self.par_place)

        self.sql_r_cursor = self.sql.cursor()
        self.sql_w_cursor = self.sql.cursor()

        self.kvs_batch = leveldb.WriteBatch()
        self.idx_batch = leveldb.WriteBatch()
        self.par_batch = leveldb.WriteBatch()

        self.yago_dir = yago_dir
        self.db_dir = db_dir
        self.__kvs_counter = 0
        self.conceptnet = dict()

        for statement in YagoDict.SQL_CREATE_TABLE_STATEMENTS:
            self.sql_w_cursor.execute(statement)
        self.sql.commit()

    @staticmethod
    def create(yago_dir, db_dir, lang=None):
        yago_classes_fl = "%s/yagoMultilingualClassLabels.tsv" % yago_dir
        yago_instances_fl = "%s/yagoMultilingualInstanceLabels.tsv" % yago_dir

        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        yago = YagoDict(yago_dir, db_dir)

        with open(yago_classes_fl, "rb") as classes, open(yago_instances_fl, "rb") as instances:
            for line in itertools.chain(classes, instances):
                entry = YagoEntry.from_tsv_line(line)
                if lang is not None and entry.lang == lang:
                    yago.sql_insert_entry(entry)
                elif lang is None:
                    yago.sql_insert_entry(entry)

        yago.sql.commit()
        return yago

    def create_txn(self):
        yago_transitions_fl = "%s/yagoTransitiveType.tsv" % self.yago_dir
        with open(yago_transitions_fl, "rb") as transitions:
            for line in transitions:
                node_a, node_b = YagoEntry.extract_transition(line)
                self.sql_insert_txn_transition(node_a, node_b)
        self.sql.commit()

    def create_hrc(self):
        yago_taxonomy_fl = "%s/yagoTaxonomy.tsv" % self.yago_dir
        with open(yago_taxonomy_fl, "rb") as relations:
            for line in relations:
                row = line.decode("utf-8").split("\t")
                child, parent = row[1], row[3]
                self.sql_insert_txn_relation(child, parent)
        self.sql.commit()

    def create_names(self, lang="ru"):
        names_list_fl = "%s/names_%s.txt" % (self.yago_dir, lang.upper())
        with open(names_list_fl, "rb") as names:
            for line in names:
                name = line.decode("utf-8").split("\n")[0]
                self.sql_insert_name(name)
        self.sql.commit()

    def create_conceptnet(self, lang="ru"):
        conceptnet_fl = "%s/conceptnet5_filtered_%s.csv" % (self.yago_dir, lang.upper())
        with open(conceptnet_fl, "rb") as conceptnet_rels:
            for line in conceptnet_rels:
                rel_name, form, concept = line.decode("utf-8").split("\t")
                self.sql_insert_concept(rel_name, form, concept)
        self.sql.commit()

    def create_kvs_from_sql(self):
        prev = None
        node_set = None
        for label, node in self.sql_r_cursor.execute("SELECT label,node FROM yago_node ORDER BY label;"):
            if label != prev:
                if node_set is not None and len(node_set) > 0:
                    self.kvs_insert_entryset(prev.encode("utf-8"), node_set)
                prev = label
                node_set = set()
            node_set.add(node)
        if node_set is not None and len(node_set) > 0:
            self.kvs_insert_entryset(prev.encode("utf-8"), node_set)
        self.kvs.Write(self.kvs_batch, sync=True)

    def create_idx_from_sql(self):
        word_re = YagoEntry.word_re
        for label, node in self.sql_r_cursor.execute("SELECT label,node FROM yago_node ORDER BY label;"):
            label_parts = word_re.findall(label)
            for part in label_parts:
                self.sql_insert_part(part, node)
        self.sql.commit()
        prev = None
        node_set = None
        for part, node in self.sql_r_cursor.execute("SELECT part,node FROM yago_cpnd ORDER BY part;"):
            if part != prev:
                if node_set is not None and len(node_set) > 0:
                    self.index_part(prev.encode("utf-8"), node_set)
                prev = part
                node_set = set()
            node_set.add(node)
        if node_set is not None and len(node_set) > 0:
            self.index_part(prev.encode("utf-8"), node_set)
        self.idx.Write(self.idx_batch, sync=True)

    def create_txn_from_sql(self):
        print "CREATE TAXONOMY"

    def create_par_from_sql(self):
        for row in list(self.sql_r_cursor.execute(self.SQL_SELECT_DISTINCT_NODES)):
            node = row[0]
            parents = self.find_direct_parent(node)
            if parents is not None:
                self.par_index_parents(node.encode("utf-8"), parents)
        self.par.Write(self.par_batch, sync=True)

    def sql_insert_concept(self, rel_name, form, concept):
        concept_spl = concept.split("/")
        concept = concept_spl[0].lower()
        concept = concept[0:(len(concept) - 1)]
        pos = concept_spl[-1] if len(concept_spl) > 1 else "?"
        form = form.lower()
        if rel_name == "DerivedFrom":
            values = (ConceptRelation.DerivedFrom, concept, form, pos)
        elif rel_name == "ConceptuallyRelatedTo":
            values = (ConceptRelation.ConceptuallyRelatedTo, concept, form, pos)
        elif rel_name == "Synonym":
            values = (ConceptRelation.Synonym, concept, form, pos)
        else:
            values = None
            logging.msg("ERROR: unknown conceptnet relation type")
        try:
            self.sql_w_cursor.execute(self.SQL_INSERT_CONCEPT, values)
        except sqlite3.Error:
            pass

    def sql_insert_entry(self, entry):
        values = (entry.label, entry.node)
        try:
            self.sql_w_cursor.execute(self.SQL_INSERT_ENTRY, values)
        except sqlite3.Error:
            pass

    def sql_insert_txn_transition(self, inst_node, class_node):
        values = (inst_node, class_node)
        try:
            self.sql_w_cursor.execute(self.SQL_INSERT_TXN_TRANSITION, values)
        except sqlite3.Error:
            pass

    def sql_insert_txn_relation(self, child, parent):
        values = (child, parent)
        try:
            self.sql_w_cursor.execute(self.SQL_INSERT_TXN_RELATION, values)
        except sqlite3.Error:
            pass

    def sql_insert_name(self, name):
        try:
            self.sql_w_cursor.execute(self.SQL_INSERT_NAME, (name, ))
        except sqlite3.Error:
            pass

    def sql_insert_part(self, part, node):
        try:
            self.sql_w_cursor.execute(self.SQL_INSERT_ENTRYSET, (part, node))
        except sqlite3.Error:
            pass

    def kvs_insert_entryset(self, label, node_set):
        self.kvs_batch.Put(label, pickle.dumps(node_set, protocol=pickle.HIGHEST_PROTOCOL))
        self.__kvs_counter += 1
        if self.__kvs_counter % 100000 == 0:
            self.kvs.Write(self.kvs_batch, sync=True)

    def index_part(self, part, node_set):
        self.idx_batch.Put(part, pickle.dumps(node_set, protocol=pickle.HIGHEST_PROTOCOL))
        self.__kvs_counter += 1
        if self.__kvs_counter % 100000 == 0:
            self.idx.Write(self.kvs_batch, sync=True)

    def par_index_parents(self, node, parents):
        self.par_batch.Put(node, pickle.dumps(parents, protocol=pickle.HIGHEST_PROTOCOL))
        self.__kvs_counter += 1
        if self.__kvs_counter % 100000 == 0:
            self.par.Write(self.par_batch, sync=True)

    def par_find_direct_parent(self, ins_or_cls):
        try:
            db_value = self.par.Get(ins_or_cls)
            return pickle.loads(db_value)
        except KeyError:
            return None

    def find_concept(self, form, rel=None):
        if rel is None:
            values = (form, )
            concepts = [row[0] for row in self.sql_r_cursor.execute(self.SQL_FIND_CONCEPT, values)]
        else:
            values = (form, rel, )
            concepts = [row[0] for row in self.sql_r_cursor.execute(self.SQL_FIND_CONCEPT_REL, values)]
        if len(concepts) > 0:
            return concepts
        return None

    def find_class(self, instance):
        classes = [row[0] for row in self.sql_r_cursor.execute(self.SQL_FIND_CLASS, (instance, ))]
        if len(classes) > 0:
            return set(classes)
        return None

    def find_all_classes(self, child):
        classes = [child]
        new_classes = [row[0] for row in self.sql_r_cursor.execute(self.SQL_FIND_ALL_CLASSES, (child, ))]
        while len(new_classes) > 0:
            classes.extend(new_classes)
            children = new_classes
            new_classes = []
            for ch in children:
                new_classes.extend([row[0] for row in self.sql_r_cursor.execute(self.SQL_FIND_ALL_CLASSES, (ch, ))])
        return set(classes)

    def is_subclass(self, inst_nodes, class_node):
        if YagoEntry.is_class(class_node) and class_node in inst_nodes:
            return True
        return False

    def is_name(self, name):
        names = self.sql_r_cursor.execute(self.SQL_IS_NAME, (name, ))
        return len(list(names)) > 0

    def sql_map_lemma(self, lemma):
        nodes = [row[0] for row in self.sql_r_cursor.execute(self.SQL_MAP_LEMMA, (lemma, ))]
        if len(nodes) > 0:
            return set(nodes)
        return None

    def kvs_map_lemma(self, lemma):
        try:
            db_value = self.kvs.Get(lemma)
            return pickle.loads(db_value)
        except KeyError:
            return None

    def kvs_map_concept(self, lemma):
        clemma = self.conceptnet.get(lemma, -1)
        if clemma != -1:
            return clemma
        else:
            conc = self.find_concept(lemma.decode("utf-8"), ConceptRelation.DerivedFrom)
            if conc is not None and len(conc) > 0:
                nodes = self.kvs_map_lemma(conc[0].encode("utf-8"))
                self.conceptnet[lemma] = nodes
                return nodes
            self.conceptnet[lemma] = None
            return None

    def idx_map_part(self, part):
        try:
            db_value = self.idx.Get(part)
            return pickle.loads(db_value)
        except KeyError:
            return None

    def idx_map_compound(self, compound):
        node_sets = [self.idx_map_part(part.encode("utf-8")) for part in compound]
        intersection = node_sets[0]
        for ns in node_sets:
            if ns is not None:
                intersection &= ns
            else:
                return set()
        return intersection

    def expand_instances(self, node_set):
        if node_set is not None and len(node_set) > 0:
            new_nodes = set()
            for node in node_set:
                if not YagoEntry.is_class(node):
                    found_nodes = self.par_find_direct_parent(node.encode("utf-8"))
                    if found_nodes is not None:
                        for foud_node in found_nodes:
                            new_nodes.add(foud_node)
                else:
                    new_nodes.add(node)
            return new_nodes
        return node_set

    def find_class_parent(self, cls):
        rows = [r[0] for r in self.sql_r_cursor.execute(self.SQL_FIND_PARENT, (cls, ))]
        if len(rows) == 1:
            return rows[0]
        return None

    def find_direct_parent(self, cls_or_inst):
        parent = self.find_class_parent(cls_or_inst)
        if parent is not None:
            return parent
        else:
            all_parents = self.find_class(cls_or_inst)
            if all_parents is None:
                return None
            chain = dict()
            for cls in all_parents:
                chain[cls] = [None, None]
            for cls in all_parents:
                parent = self.find_class_parent(cls)
                if parent is not None and parent in chain:
                    chain[cls][1] = parent
                    chain[parent][0] = cls
            direct_parents = set()
            for node, [child, parent] in chain.iteritems():
                if child is None:
                    direct_parents.add(node)
                    if parent is not None:
                        direct_parents.add(parent)
            return direct_parents

    def count_classes(self, node_set):
        count = 0
        for node in node_set:
            if YagoEntry.is_class(node):
                count += 1
        return count

    def find_compound(self, lemmas, min_threshold=1, init_len=1, max_len=3, prefer_classes=True):
        if len(lemmas) == 0:
            return None
        best_comb = None
        best_nodes = None
        best_len = 0xFFFFFF
        for comb_len in xrange(init_len, min(len(lemmas) + 1, max_len + 1)):
            combs = list(itertools.combinations(lemmas, comb_len))
            for comb in combs:
                if len(comb) == 1:
                    nodes = self.kvs_map_lemma(comb[0].encode("utf-8"))
                    if nodes is None or len(nodes) == 0:
                        nodes = self.idx_map_compound(comb)
                    else:
                        nodes = set()
                        for comb2 in combs:
                            new_nodes = self.kvs_map_lemma(comb2[0].encode("utf-8"))
                            if new_nodes is not None and len(new_nodes) > 0:
                                for new_node in new_nodes:
                                    if YagoEntry.is_class(new_node):
                                        nodes.add(new_node)
                                    else:
                                        ins_parents = self.par_find_direct_parent(new_node.encode("utf-8"))
                                        if ins_parents is not None and len(ins_parents) > 0:
                                            nodes |= ins_parents
                        return nodes
                else:
                    nodes = self.idx_map_compound(comb)
                classes_n = self.count_classes(nodes)
                new_len = classes_n if classes_n > 0 else len(nodes)
                if min_threshold <= new_len <= best_len:
                    best_nodes = nodes
                    best_len = new_len
                    best_comb = comb
        if prefer_classes and best_nodes is not None:
            classes_found = False
            for node in best_nodes:
                if YagoEntry.is_class(node):
                    classes_found = True
                    break
            if classes_found:
                best_nodes = filter(lambda node: YagoEntry.is_class(node), best_nodes)
            else:
                best_nodes = [min(best_nodes, key=lambda node: len(node.split("_")))]
        if best_nodes is not None and len(best_comb) == 1 and self.is_name(best_comb[0]):
            return self.NODE_PERSON
        return self.expand_instances(best_nodes)


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


def process_triple(yago, out_file, rel_name, freq, test, stat_collector, *args):
    if test:
        for arg in args:
            if arg is ARG_NONE:
                continue
            elif arg is ARG_EMPTY:
                continue
            else:
                lemmas, pos = arg
                lemmas_set = lemmas.split("&&")
                if pos == "NN" and len(lemmas_set) > 1:
                    nodes = yago.find_compound(lemmas_set)
                    if nodes is not None and len(nodes) > 0:
                        out_file.write(lemmas.encode("utf-8"))
                        # out_file.write("\t")
                        # out_file.write(("{%s}" % ";".join(nodes)).encode("utf-8"))
                        if len(nodes) == 1 and not YagoEntry.is_class(list(nodes)[0]):
                            out_file.write(" => ")
                            out_file.write("\n")
                            classes = yago.find_class(list(nodes)[0])
                            for cl in classes:
                                out_file.write("\t\t")
                                out_file.write(cl.encode("utf-8"))
                                out_file.write("\n")
                        else:
                            out_file.write(" => ")
                            out_file.write("\n")
                            for node in nodes:
                                out_file.write("\t\t")
                                out_file.write(node.encode("utf-8"))
                                out_file.write("\n")
                        out_file.write("\n")
    else:
        triple_completely_mapped = True
        out_file.write(rel_name)
        out_file.write(",")
        for arg in args:
            if arg is ARG_NONE:
                out_file.write("<NONE>,")
            elif arg is ARG_EMPTY:
                out_file.write("<->,")
            else:
                lemmas, pos = arg
                out_file.write(lemmas.encode("utf-8"))
                out_file.write("-")
                out_file.write(pos)
                out_file.write(",")
                if pos == "NN":
                    lemmas_set = lemmas.split("&&")
                    if len(lemmas_set) == 1:
                        nodes = yago.kvs_map_lemma(lemmas_set[0].encode("utf-8"))
                        if nodes is None or len(nodes) == 0:
                            nodes = yago.kvs_map_concept(lemmas_set[0].encode("utf-8"))
                            if nodes is not None and len(nodes) > 0:
                                stat_collector.update_conceptnet("%s-%s" % (lemmas_set[0], list(nodes)[0]), True)
                            else:
                                stat_collector.update_conceptnet(lemmas_set[0], False)
                    else:
                        nodes = yago.find_compound(lemmas_set)
                    if nodes is None or len(nodes) == 0:
                        lemma_node_sets = "{}"
                        triple_completely_mapped = False
                        stat_collector.update_arg(lemmas, False)
                    else:
                        lemma_node_sets = "{%s}" % ";".join(nodes)
                        stat_collector.update_arg(lemmas, True)
                    out_file.write(lemma_node_sets.encode("utf-8"))
                    out_file.write(",")
                else:
                    out_file.write(lemmas.encode("utf-8"))
                    out_file.write("-")
                    out_file.write(pos)
                    out_file.write(",")
        out_file.write(freq)
        if triple_completely_mapped:
            stat_collector.update_rel(rel_name, True)
        else:
            stat_collector.update_rel(rel_name, False)


def map_triples(yago, triples_file, out, stat_collector):
    for line in triples_file:
        line = line.decode("utf-8")
        row = line.split(", ")
        rel_name, args, freq = parse_triple_row(row)
        out_file = out.get_file(rel_name, any([arg != ARG_NONE and
                                               arg != ARG_EMPTY and
                                               len(arg[0].split("&&")) > 1
                                               for arg in args]))
        process_triple(yago, out_file, rel_name, freq, False, stat_collector, *args)


if __name__ == "__main__":

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
    parser.add_argument("-t", "--debug", default=0, type=int, choices=(0, 1), help="Enables debug mode")

    args = parser.parse_args()

    in_file = file(args.ifile, "r") if args.ifile is not None else sys.stdin
    out_file = file(args.ofile, "w") if args.ofile is not None else sys.stdout
    yago_dir = args.yago
    db_dir = args.dbdir
    lang = args.lang
    create_db = args.createdb
    debug = args.debug

    if debug:
        logging.basicConfig(level=logging.DEBUG)

    if create_db == 1:
        logging.info("CREATING A TEMP DB FOR YAGO(%s): %s" % (yago_dir, db_dir))
        logging.info("CREATING MAIN SQL STORAGE")
        yago = YagoDict.create(yago_dir, db_dir, lang)
        logging.info("CREATING KV STORAGE")
        yago.create_kvs_from_sql()
        logging.info("CREATING INVERTED INDEX")
        yago.create_idx_from_sql()
        logging.info("CREATING CONCEPTNET DB")
        yago.create_conceptnet()
        logging.info("CREATING HIERARCHY DB")
        yago.create_hrc()
        logging.info("CREATING TAXONOMY INDEX")
        yago.create_txn_from_sql()
        logging.info("CREATING NAMES DB")
        yago.create_names()
        logging.info("CREATE DIRECT PARENT MAP")
        yago.create_par_from_sql()
        logging.info("DB COMPLETE")
    else:
        logging.info("LOADING TEMP DB: %s" % db_dir)
        yago = YagoDict(yago_dir, db_dir)

    out = Output(debug, out_file)
    stat_collector = StatCollector()
    logging.info("MAPPING TRIPLES FROM %s TO %s" % (in_file, out_file))
    map_triples(yago, in_file, out, stat_collector)
    out.close()

    if args.ofile:
        stat_collector.save(args.ofile)
    else:
        stat_collector.save("last_run")

    logging.info("DONE")
