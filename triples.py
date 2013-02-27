# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE


class AbsTriplePattern(object):

    def find_matches(self, sentence):
        raise NotImplementedError()


class SubjectTriplePattern(AbsTriplePattern):

    def find_matches(self, sentence):
        matches = []
        for pred in sentence:
            if pred.pos == "vb" and pred.args.second:
                subjects = sentence.index.get(pred.args.second, [])
                for subj in subjects:
                    if subj.pos == "nn":

                        if len(subj.lemma) == 2:
                            pass
                            # print "%r %r" % (pred, subj)
                            # print "%r" % subj
                            # print sentence.line.encode("utf-8")
                            # print
                        # else:
                        #     print subj.lemma.encode("utf-8")
                        else:
                            matches.append((pred.lemma, subj.lemma))
        return matches