# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

# Triples Difinitions


class AbsTriplePattern(object):
    triple_class = "abstract"

    def find_matches(self, sentence):
        raise NotImplementedError()


class SubjectTriplePattern(AbsTriplePattern):
    triple_class = "subj"

    def find_matches(self, sentence):
        matches = []
        for pred in sentence:
            if pred.pos == "vb" and pred.args.second:
                subjects = sentence.index.get(pred.args.second, [])
                for subj in subjects:
                    if subj.pos == "nn":

                        if len(subj.lemma) < 3:
                            pass
                            # TODO(zaytsev@usc.edu): fix issue with zero-length lemmas
                            # print "%r %r" % (pred, subj)
                            # print "%r" % subj
                            # print sentence.line.encode("utf-8")
                            # print
                        # else:
                        #     print subj.lemma.encode("utf-8")
                        else:
                            matches.append((pred.lemma, subj.lemma))
        return matches


class DirObjTriplePattern(AbsTriplePattern):
    triple_class = "dir_obj"
    
    def find_matches(self, sentence):
        matches = []
        for pred in sentence:
            if pred.pos == "vb" and pred.args.third:
                d_objects = sentence.index.get(pred.args.third, [])
                for d_obj in d_objects:
                    if d_obj.pos == "nn":
                        if len(d_obj.lemma) > 2:
                            matches.append((pred.lemma, d_obj.lemma))
        return matches


class IndirObjTriplePatern(AbsTriplePattern):
    triple_class = "indir_obj"
    
    def find_matches(self, sentence):
        matches = []
        for pred in sentence:
            if pred.pos == "vb" and pred.args.fourth:
                i_objects = sentence.index.get(pred.args.fourth, [])
                for i_obj in i_objects:
                    if i_obj.pos == "nn":
                        if len(i_obj.lemma) > 2:
                            matches.append((pred.lemma, i_obj.lemma))
        return matches


class AdjTriplePattern(AbsTriplePattern):
    triple_class = "adj"
    
    def find_matches(self, sentence):
        matches = []
        for pred in sentence:
            if pred.pos == "adj" and pred.args.second:
                nouns = sentence.index.get(pred.args.second, [])
                for nn in nouns:
                    if nn.pos == "nn":
                        if len(nn.lemma) > 2:
                            matches.append((pred.lemma, nn.lemma))
        return matches


class AdvTriplePattern(AbsTriplePattern):
    triple_class = "adv"
    
    def find_matches(self, sentence):
        matches = []
        for pred in sentence:
            if pred.pos == "rb" and pred.args.second:
                verbs = sentence.index.get(pred.args.second, [])
                for vb in verbs:
                    if vb.pos == "vb":
                        if len(vb.lemma) > 2:
                            matches.append((pred.lemma, vb.lemma))
        return matches


# class ComplTriplePattern(AbsTriplePattern):
#     triple_class = "compl"
# 
#     def find_matches(self, sentence):
#         matches = []
#         for pred in sentence:
#             if pred.extra == "compl" and pred.args.second and pred.args.third:
#                 nouns = sentence.index.get(pred.args.second, [])
#                 
#                 
#                 for vb in verbs:
#                     if vb.pos == "vb":
#                         if len(vb.lemma) > 2:
#                             matches.append((pred.lemma, vb.lemma))
#         return matches


class VerbGovTriplePattern(AbsTriplePattern):
    triple_class = "verb_gov"

    def find_matches(self, sentence):
        matches = []
        for pred in sentence:
            if pred.extra == "compl" and pred.args.second and pred.args.third:
                print "%r" % pred
                verbs1 = sentence.index.get(pred.args.second, [])
                verbs2 = sentence.index.get(pred.args.third, [])
                for vb1 in verbs1:
                        print vb1.pos, vb2.pos
                        if vb1.pos == "vb" and vb2.pos == "vb":
                            matches.append((vb1.lemma, vb2.lemma))
        return matches
