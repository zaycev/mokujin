# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE


import collections
from logicalform import POS


class AbsDependencyRelation(object):
    triple_class = "abstract"

    def together(self, lemma1, lemma2):
        if lemma1 is None:
            lemma1 = "N"
        if lemma2 is None:
            lemma2 = "N"
        if lemma1 > lemma2:
            return lemma2 + lemma1
        return lemma1 + lemma2

    def find_matches(self, sentence):
        raise NotImplementedError()


class Triple(object):

    def __init__(self, relation, arg1=None, arg2=None, arg3=None, extra=None):
        self.relation = relation
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3
        self.extra = extra

    @staticmethod
    def to_row(triple_tuple):
        relation, arg1, arg2, arg3, extra, freq = triple_tuple
        return "%s, %s, %s, %s, %s, %d" % (relation, arg1, arg2, arg3, extra, freq,)

    def pack(self):
        return "@AND@".join((
            self.relation,
            self.arg1.lemma_pos() if self.arg1 is not None else "<NONE>",
            self.arg2.lemma_pos() if self.arg2 is not None else "<NONE>",
            self.arg3.lemma_pos() if self.arg3 is not None else "<NONE>",
            self.extra.lemma_pos() if self.extra is not None else "<NONE>",
        ))

    @staticmethod
    def unpack(string):
        return string.split("@AND@")

    def __repr__(self):
        return u"Triple(%s, %s, %s, %s, %s)" % (
            self.relation,
            self.arg1,
            self.arg2,
            self.arg3 if self.arg3 is not None else "<NONE>",
            self.extra if self.extra is not None else "<NONE>",
        )


##################################
#                                #
#       VERB RELATIONS           #
#                                #
##################################


class DepVerb_SubjVerbDirobj(AbsDependencyRelation):
    """
    Example:
    subj_verb_dirobj(noun,verb,noun) ("John reads a book")
    """
    rel_name = "subj_verb_dirobj"

    def find_matches(self, sentence):
        matches = []
        for verb in sentence.index.find(pos=POS.VB):
            if verb.args.second and verb.args.third:
                subjs = sentence.index.find(second=verb.args.second, pos=POS.NN)
                dirobjs = sentence.index.find(second=verb.args.third, pos=POS.NN)
                for subj in subjs:
                    for dirobj in dirobjs:
                        if subj != dirobj:
                            matches.append(Triple(self.rel_name, subj, verb, dirobj))
        return matches


class DepVerb_SubjVerbIndirobj(AbsDependencyRelation):
    """
    Example:
    subj_verb_indirobj(noun,verb,noun) ("John gives to Mary")
    """
    rel_name = "subj_verb_indirobj"

    def find_matches(self, sentence):
        matches = []
        for verb in sentence.index.find(pos=POS.VB):
            if verb.args.second and verb.args.fourth:
                subjs = sentence.index.find(second=verb.args.second, pos=POS.NN)
                indirobjs = sentence.index.find(second=verb.args.fourth, pos=POS.NN)
                for subj in subjs:
                    for indirobj in indirobjs:
                        if subj != indirobj:
                            matches.append(Triple(self.rel_name, subj, verb, indirobj))
        return matches


class DepVerb_SubjVerbInstr(AbsDependencyRelation):
    """
    Example:
    subj_verb_instr(noun,verb,noun) ("Джон работает топором")
    """
    rel_name = "subj_verb_instr"

    def find_matches(self, sentence):
        matches = []
        for verb in sentence.index.find(pos=POS.VB):
            if verb.args.second and verb.args.fourth:
                subjs = sentence.index.find(second=verb.args.second, pos=POS.NN)
                instrs = sentence.index.find(second=verb.args.first, extra="instr")
                for instr in instrs:
                    instr_preds = sentence.index.find(second=instr.args.third, pos=POS.NN)
                    for instr_pred in instr_preds:
                        for subj in subjs:
                            if subj != instr_pred:
                                matches.append(Triple(self.rel_name, subj, verb, instr_pred))
        return matches


class DepVerb_SubjVerb(AbsDependencyRelation):
    """
    Example:
    subj_verb(noun, verb) ("John runs") // only if there is no obj
    """
    rel_name = "subj_verb"

    def find_matches(self, sentence):
        matches = []
        for verb in sentence.index.find(pos=POS.VB):
            if verb.args.second and not verb.args.third and not verb.args.fourth:
                subjs = sentence.index.find(second=verb.args.second, pos=POS.NN)
                for subj in subjs:
                    matches.append(Triple(self.rel_name, subj, verb))
        return matches


class DepVerb_PrepCompl(AbsDependencyRelation):
    """
    Example:
    subj_verb_prep_compl(noun,verb,prep,noun) ("John comes from London")
    """
    rel_name = "subj_verb_prep_compl"

    def find_matches(self, sentence):
        matches = []
        for verb in sentence.index.find(pos=POS.VB):
            if verb.args.second:
                subjs = sentence.index.find(second=verb.args.second, pos=POS.NN)
                preps = sentence.index.find(second=verb.args.first, pos=POS.PREP)
                for prep in preps:
                    prep_nouns = sentence.index.find(second=prep.args.third, pos=POS.NN)
                    for subj in subjs:
                        for noun in prep_nouns:
                            matches.append(Triple(self.rel_name, subj, verb, prep, noun))
        return matches


class DepVerb_PrepPrepCompl(AbsDependencyRelation):
    # TODO(zaytsev@usc.edu): implement this
    """
    Example:
    subj_verb_prep_prep_compl(noun,verb,prep,prep,noun) ("John goes out of the store")
    """
    rel_name = "subj_verb_prep_compl"


class DepVerb_VerbPrepNoun(AbsDependencyRelation):
    """
    Example:
    verb_verb_prep_noun(verb,verb,prep,noun) ("try to go into the house")
    """
    rel_name = "verb_verb_prep_noun"

    def find_matches(self, sentence):
        matches = []
        vb_pairs = []
        for verb1 in sentence.index.find(pos=POS.VB):
            if verb1.args.second:
                verbs2 = sentence.index.find(first=verb1.args.third, pos=POS.VB)
                verbs2 = filter(lambda p: p != verb1, verbs2)
                for verb2 in verbs2:
                    together = self.together(verb1.lemma, verb2.lemma)
                    if together not in vb_pairs:
                        preps = sentence.index.find(second=verb1.args.first, pos=POS.PREP)
                        for prep in preps:
                            nouns = sentence.index.find(second=prep.args.third, pos=POS.NN)
                            for noun in nouns:
                                matches.append(Triple(self.rel_name, verb2, verb1, prep, noun))
                                vb_pairs.append(together)
        return matches


class DepVerb_Verb(AbsDependencyRelation):
    # TODO(zaytsev@usc.edu): add constraint
    """
    Example:
    verb_verb(verb,verb,prep,noun) ("try to go") -> only if there is no prep attached to the second verb
    """
    rel_name = "verb_verb"

    def find_matches(self, sentence):
        matches = []
        for verb in sentence.index.find(pos=POS.VB):
            if verb.args.third:
                second_verbs = sentence.index.find(first=verb.args.third, pos=POS.VB)
                subjs = sentence.index.find(second=verb.args.second, pos=POS.NN)
                for verb2 in second_verbs:
                    if verb != verb2:
                        for subj in subjs:
                            matches.append(Triple(self.rel_name, verb, verb2, None, subj))
        return matches


class DepVerb_NounBePrepNoun(AbsDependencyRelation):
    # TODO(zaytsev@usc.edu): implement this
    """
    Example:
    noun_be_prep_noun(noun,verb,prep,noun) ("intention to leave for money")
    """
    rel_name = "noun_be_prep_noun"


class DepVerb_NounBe(AbsDependencyRelation):
    # TODO(zaytsev@usc.edu): implement this
    """
    Example:
    noun_be(noun,verb) ("intention to leave") -> only if there is no prep attached to verb
    """
    rel_name = "noun_be"


##################################
#                                #
#        ADJ RELATIONS           #
#                                #
##################################


class DepAdj_NounBePrepNoun(AbsDependencyRelation):
    """
    Example:
    noun_adj_prep_noun(noun,adjective,prep,noun) ("The book is good for me") -> only if "for" has "good" (and not "is")
    as its arg.
    """
    rel_name = "noun_adj_prep_noun"

    def find_matches(self, sentence):
        matches = []
        for adj in sentence.index.find(pos=POS.ADJ):
            if adj.args.second:
                nouns1 = sentence.index.find(second=adj.args.second, pos=POS.NN)
                for noun1 in nouns1:
                    preps = sentence.index.find(pos=POS.PREP)
                    for prep in preps:
                        nouns2 = sentence.index.find(second=prep.args.third, pos=POS.NN)
                        for noun2 in nouns2:
                            if noun1 != noun2:
                                matches.append(Triple(self.rel_name, noun1, adj, prep, noun2))
        return matches


class DepAdj_NounAdj(AbsDependencyRelation):
    """
    Example:
    noun_adj(noun,adjective) ("The book is good") -> only if there is no prep attached to adj as its arg.
    """
    rel_name = "noun_adj"

    def find_matches(self, sentence):
        matches = []
        for adj in sentence.index.find(pos=POS.ADJ):
            if adj.args.second:
                nouns1 = sentence.index.find(second=adj.args.second, pos=POS.NN)
                for noun1 in nouns1:
                    preps = sentence.index.find(pos=POS.PREP)
                    if len(preps) == 0:
                        matches.append(Triple(self.rel_name, noun1, adj))
        return matches


##################################
#                                #
#        ADV RELATIONS           #
#                                #
##################################


class DepAdv_NounVerbAdvPrepNoun(AbsDependencyRelation):
    # TODO(zaytsev@usc.edu): seems to be very very rare, double check this
    """
    Example:
    noun_verb_adv_prep_noun(adverb,verb) ("John runs fast for me") -> only if "for" has "fast" (and not "runs")
    as its arg.
    """
    rel_name = "noun_verb_adv_prep_noun"

    def find_matches(self, sentence):
        matches = []
        # for adv in sentence.index.find(pos=POS.RB):
        #     if adv.args.second:
        #         preps = sentence.index.find(third=adv.args.first, pos=POS.PREP)
                # print adv.lemma.encode("utf-8"), len(preps)
                # print(len(preps))
                # for prep in preps:
                #     print adv.lemma.encode("utf-8"), prep.lemma.encode("utf-8")

                # verbs = sentence.index.find(second=adv.args.second, pos=POS.VB)
                #     for verb in verbs:
                #         print verb.lemma.encode("utf-8"), adv.lemma.encode("utf-8"), prep.lemma.encode("utf-8")

                # verbs = sentence.index.find(first=adv.args.second, pos=POS.VB)
                # for verb in verbs:
                #     preps = sentence.index.find(pos=POS.PREP)
                #     for prep in preps:
                #         nouns1 = sentence.index.find(second=verb.args.second, pos=POS.NN)
                #         for noun2 in nouns2:
                #             if noun1 != noun2:
                #                 matches.append(Triple(self.rel_name, noun1, adv, prep, noun2.lemma))
        return matches


class DepAdv_VerbNounAdv(AbsDependencyRelation):
    """
    Example:
    noun_verb_adv(adverb,verb) ("John runs fast") -> only if there is no prep attached to adv
    """
    rel_name = "noun_verb_adv"

    def find_matches(self, sentence):
        matches = []
        for adv in sentence.index.find(pos=POS.RB):
            preps1 = sentence.index.find(second=adv.args.first, pos=POS.PREP)
            preps2 = sentence.index.find(third=adv.args.first, pos=POS.PREP)
            if len(preps1) == 0 and len(preps2) == 0:
                verbs = sentence.index.find(first=adv.args.second, pos=POS.VB)
                for verb in verbs:
                    nouns = sentence.index.find(second=verb.args.second, pos=POS.NN)
                    for noun in nouns:
                        matches.append(Triple(self.rel_name, adv, verb, noun))
        return matches


##################################
#                                #
#        NOUN RELATIONS          #
#                                #
##################################


class DepNoun_NounPrep(AbsDependencyRelation):
    """
    Example:
    nn_prep(noun,noun,prep,noun) ("city bike for John") -> only if "for" has "bike" (and not some verb) as its arg.
    """
    rel_name = "nn_prep"

    def find_matches(self, sentence):
        matches = []
        nn_pairs = []
        for prep in sentence.index.find(pos=POS.PREP):
            if prep.args.second:
                nouns1 = sentence.index.find(second=prep.args.second, pos=POS.NN)
                for noun1 in nouns1:
                    nouns2 = sentence.index.find(second=prep.args.second, pos=POS.NN)
                    nouns2 = filter(lambda p: p != noun1, nouns2)
                    for noun2 in nouns2:
                        together = self.together(noun1.lemma, noun2.lemma)
                        if together not in nn_pairs:
                            nouns3 = sentence.index.find(second=prep.args.third, pos=POS.NN)
                            for noun3 in nouns3:
                                if noun3 != noun1 and noun3 != noun2:
                                    matches.append(Triple(self.rel_name, noun2, noun1, prep, noun3))
                                    nn_pairs.append(together)
        return matches


class DepNoun_NounNoun(AbsDependencyRelation):
    """
    Example:
    nn(noun,noun) ("city bike") -> only if there is no prep attached to the second noun
    """
    rel_name = "nn"

    def find_matches(self, sentence):
        matches = []
        nn_pairs = []
        for noun1 in sentence.index.find(pos=POS.NN):
            preps = sentence.index.find(second=noun1.args.second, pos=POS.PREP)
            if len(preps) == 0:
                nouns2 = sentence.index.find(second=noun1.args.second, pos=POS.NN)
                nouns2 = filter(lambda p: p != noun1, nouns2)
                for noun2 in nouns2:
                    together = self.together(noun1.lemma, noun2.lemma)
                    if together not in nn_pairs:
                        matches.append(Triple(self.rel_name, noun1, noun2))
                        nn_pairs.append(together)
        return matches


class DepNoun_NounEqualPrepNoun(AbsDependencyRelation):
    """
    Example:
    noun_equal_prep_noun(noun,noun,prep,noun) ("John is a man of heart") -> only if "of" has "man" (and not "is")
    as its arg.
    """
    rel_name = "noun_equal_prep_noun"

    def find_matches(self, sentence):
        matches = []
        nn_pairs1 = []
        nn_pairs2 = []
        nn_pairs3 = []
        for equal in sentence.index.find(extra="equal"):
            nouns1 = sentence.index.find(second=equal.args.second, pos=POS.NN)
            for noun1 in nouns1:
                nouns2 = sentence.index.find(second=equal.args.third, pos=POS.NN)
                nouns2 = filter(lambda p: p != noun1, nouns2)
                for noun2 in nouns2:
                    together1 = self.together(noun1.lemma, noun2.lemma)
                    if together1 not in nn_pairs1:
                        preps = sentence.index.find(second=noun2.args.second, pos=POS.PREP)
                        for prep in preps:
                            nouns3 = sentence.index.find(second=prep.args.third, pos=POS.NN)
                            nouns3 = filter(lambda p: p != noun1, nouns3)
                            nouns3 = filter(lambda p: p != noun2, nouns3)
                            for noun3 in nouns3:
                                together2 = self.together(noun1.lemma, noun3.lemma)
                                together3 = self.together(noun2.lemma, noun3.lemma)
                                if together2 not in nn_pairs2 and together3 not in nn_pairs3:
                                    matches.append(Triple(self.rel_name, noun1, noun2, prep, noun3))
                                    nn_pairs1.append(together1)
                                    nn_pairs2.append(together2)
                                    nn_pairs3.append(together3)
        return matches


class DepNoun_NounEqualNoun(AbsDependencyRelation):
    """
    Example:
    noun_equal_noun(noun,noun) ("John is a biker") -> only if there is no prep attached to the second noun.
    """
    rel_name = "noun_equal_noun"

    def find_matches(self, sentence):
        matches = []
        nn_pairs = []
        for equal in sentence.index.find(extra="equal"):
            nouns1 = sentence.index.find(second=equal.args.second, pos=POS.NN)
            for noun1 in nouns1:
                nouns2 = sentence.index.find(second=equal.args.third, pos=POS.NN)
                nouns2 = filter(lambda p: p != noun1, nouns2)
                for noun2 in nouns2:
                    together = self.together(noun1.lemma, noun2.lemma)
                    if together not in nn_pairs:
                        preps = sentence.index.find(second=noun2.args.second, pos=POS.PREP)
                        if len(preps) == 0:
                            matches.append(Triple(self.rel_name, noun1, noun2))
                            nn_pairs.append(together)
        return matches


class DepNoun_NounPrepNoun(AbsDependencyRelation):
    """
    Example:
    noun_prep_noun(noun,prep,noun) ("house in London")
    """
    rel_name = "noun_prep_noun"

    def find_matches(self, sentence):
        matches = []
        nn_pairs = []
        for prep in sentence.index.find(pos=POS.PREP):
            nouns1 = sentence.index.find(second=prep.args.second, pos=POS.NN)
            for noun1 in nouns1:
                nouns2 = sentence.index.find(second=prep.args.third, pos=POS.NN)
                nouns2 = filter(lambda p: p != noun1, nouns2)
                for noun2 in nouns2:
                    together = self.together(noun1.lemma, noun2.lemma)
                    if together not in nn_pairs:
                        matches.append(Triple(self.rel_name, noun1, prep, noun2))
                        nn_pairs.append(together)
        return matches


class DepNoun_NounPrepPrepNoun(AbsDependencyRelation):
    # TODO(zaytsev@usc.edu): implement this
    """
    Example:
    noun_prep_prep_noun(noun,prep,prep,noun) ("book out of the store")
    """
    rel_name = "noun_prep_prep_noun"


##################################
#                                #
#       OTHER RELATIONS          #
#                                #
##################################

class DepAny_Compl(AbsDependencyRelation):
    """
    Example:
    compl(anything,anything) ("близкий мне")
    """
    rel_name = "compl"

    def find_matches(self, sentence):
        matches = []
        any_pairs = []
        for compl in sentence.index.find(extra="compl"):
            any_1s = sentence.index.find(first=compl.args.second)
            any_1s = filter(lambda p: p != compl, any_1s)
            for any_1 in any_1s:
                any_2s = sentence.index.find(first=compl.args.third)
                any_2s = filter(lambda p: p != any_1 and p != compl, any_2s)
                for any_2 in any_2s:
                    together = self.together(any_1.lemma, any_2.lemma)
                    if together not in any_pairs and any_1.lemma is not None and any_2.lemma is not None:
                        matches.append(Triple(self.rel_name, any_1, any_2))
        return matches


##################################
#                                #
#            MISC                #
#                                #
##################################


class TripleFold(object):

    def __init__(self):
        self.counter = collections.Counter()

    def add_triples(self, triples):
        for triple in triples:
            self.counter[triple.pack()] += 1

    def i_triples(self):
        for p_triple, freq in self.counter.most_common():
            triple = Triple.unpack(p_triple)
            yield triple + [freq]


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

