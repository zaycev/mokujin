    # coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

from collections import Counter


class Predicate(object):

    def __init__(self, pid, lemma, pos, args, extra=None):
        self.pid = pid
        self.lemma = lemma
        self.pos = pos
        self.args = self.Args(args)
        self.extra = extra

    @staticmethod
    def fromstr(line, line_index):
        import sys
        # TODO(zaytsev@usc.edu): use line_index
        result = line.split(":")
        if len(result) != 2:
            pid = result[0]
            other = result[1:len(result)]
            other = "".join(other)
            # aaa = other
            # ooo = result
            # xxx = len(result) - 1
            # if other == "http://www.example.com/my-picture.gif.-in(e3,x2,x3)":
            #     sys.stderr.write("YES")
        else:
            pid, other = line.split(":")
        result = other.split("-")
        if len(result) != 2:
            other = result[-1]
            lemma = "-".join(result[0:len(result)])
        else:
            lemma, other = result        

        try:
            pos, arg_line = other.split("(")
        except:
            import sys
            sys.stderr.write(str(ooo))
            exit(0)

        arg_line = arg_line[0:(len(arg_line) - 1)]
        args = arg_line.split(",")
        return Predicate(pid, lemma, pos, args)

    @staticmethod
    def efromstr(line, line_index):
        # TODO(zaytsev@usc.edu): use line_index
        result = line.split("(")
        if result == 2:
            extra, arg_line = result
        else:
            extra = result[0:(len(result) - 1)]
            arg_line = result[-1]
        arg_line = arg_line[0:(len(arg_line) - 1)]
        args = arg_line.split(",")
        return Predicate(-1, "-NONE-", "-NONE-", args, extra[0])

    def __repr__(self):
        if self.extra is None:
            predicate_str = u"%s-%s(%s)" % (
                # self.pid,
                self.lemma,
                self.pos,
                ", ".join(self.args)
            )
        else:
            predicate_str = u"%s(%s)" % (
                self.extra,
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
        self.index2 = Sentence.index_all(predicates)

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
    def index_all(predicates):
        inv_index = dict()
        for pred in predicates:
            if pred.pos in ("nn", "vb", "pr", "adj"):
                for arg in pred.args:
                    if arg[0] != "u":
                        if arg not in inv_index:
                            inv_index[arg] = [pred]
                        else:
                            inv_index[arg].append(pred)
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
            else:
                predicate = Predicate.efromstr(p_str, i)
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
                matches.append((
                    pattern.triple_class,
                    pattern.find_matches(sent)
                ))
            yield matches


class TripleFold(object):

    def __init__(self):
        self.counter = Counter()

    def pack_triple(self, triples_class, triple):
        return  triples_class + "_AND_" + "_AND_".join(triple)

    def unpack_triple(self, p_triple):
        return p_triple.split("_AND_")

    def add_triples(self, triples_class, triples):
        for t in triples:
            packed_triple = self.pack_triple(triples_class, t)
            self.counter[packed_triple] += 1

    def i_triples(self):
        for p_triple, count in self.counter.most_common():
            yield self.unpack_triple(p_triple) + [count]
