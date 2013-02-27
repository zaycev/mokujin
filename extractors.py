    # coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

from collections import Counter


class Predicate(object):

    def __init__(self, pid, lemma, pos, args):
        self.pid = pid
        self.lemma = lemma
        self.pos = pos
        self.args = self.Args(args)

    @staticmethod
    def fromstr(line, line_index):
        pid, other = line.split(":")
        result = other.split("-")
        # handling cases such as "торгово-развлекательный-adj"
        if len(result) > 2:
            other = result[-1]
            lemma = "-".join(result[0:(len(result) - 1)])
        else:
            lemma, other = result
        pos, arg_line = other.split("(")
        arg_line = arg_line[0:(len(arg_line) - 1)]
        args = arg_line.split(",")
        return Predicate(line_index, lemma, pos, args)

    def __repr__(self):
        predicate_str = u"[%d]-%s-%s(%s)" % (
            self.pid,
            self.lemma,
            self.pos,
            ", ".join(self.args)
        )
        return predicate_str.encode("utf-8")

    class Args(object):

        def __init__(self, arg_list):
            self.arg_list = arg_list

        @property
        def first(self):
            if len(self.arg_list) > 0:
                return self.arg_list[0]
            return False

        @property
        def second(self):
            if len(self.arg_list) > 1:
                return self.arg_list[1]
            return False

        @property
        def third(self):
            if len(self.arg_list) > 2:
                return self.arg_list[2]
            return False

        @property
        def fourth(self):
            if len(self.arg_list) > 3:
                return self.arg_list[3]
            return False

        def __iter__(self):
            for arg in self.arg_list:
                yield arg


class Sentence(object):

    def __init__(self, sid, predicates, line=None):
        self.line = line
        self.predicates = predicates
        self.sid = sid
        self.index = Sentence.index_predicates(predicates)

    @staticmethod
    def index_predicates(predicates):
        inv_index = dict()

        for pred in predicates:

            # index nouns, adjectives and pronouns
            if pred.pos in ("nn", "adj", "pr") and pred.args.second:

                if pred.args.second not in inv_index:
                    inv_index[pred.args.second] = [pred]
                else:
                    inv_index[pred.args.second].append(pred)

            if pred.pos in ("vb", "rb", ) and pred.args.first:

                if pred.args.first not in inv_index:
                    inv_index[pred.args.first] = [pred]
                else:
                    inv_index[pred.args.first].append(pred)

        return inv_index

    @staticmethod
    def from_lf_line(lf_line_index, lf_line):
        predicates = []
        predicate_str = filter(lambda t: t != "&", lf_line.split(" "))
        for i, p_str in enumerate(predicate_str):
            if p_str[0] == "[":
                predicate = Predicate.fromstr(p_str, i)
                if len(predicate.lemma) > 1:
                    predicates.append(predicate)

        return Sentence(lf_line_index, predicates, lf_line)

    def __iter__(self):
        for pred in self.predicates:
            yield pred


class MetaphorLF_Reader(object):

    def __init__(self, lf_file):
        self.lf_file = lf_file

    def i_sentences(self):
        with open(self.lf_file, "r") as lf:
            i = 0
            for line in lf:
                line = line.decode("utf-8")
                if line[0] == "%":
                    continue
                elif line[0:3] == "id(":
                    continue
                elif len(line) > 1:
                    sentence = Sentence.from_lf_line(i, line)
                    i += 1
                    yield sentence
                else:
                    continue


class TripleExtractor():

    def __init__(self, triple_patterns=()):
        if len(triple_patterns) == 0:
            raise Exception("Extractor should have least 1 triple pattern.")
        self.triple_patterns = triple_patterns

    def i_extract_triples(self, i_sentences):
        for sent in i_sentences:
            matches = []
            for pattern in self.triple_patterns:
                matches.extend(pattern.find_matches(sent))
            yield matches


class TripleFold(object):

    def __init__(self):
        self.counter = Counter()

    def pack_triple(self, triple):
        return "_AND_".join(triple)

    def unpack_triple(self, p_triple):
        return p_triple.split("_AND_")

    def add_triples(self, triples):
        self.counter.update(map(self.pack_triple, triples))

    def i_triples(self):
        for p_triple, count in self.counter.most_common():
            yield self.unpack_triple(p_triple) + [count]
