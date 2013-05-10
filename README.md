# MOKUJIN

A a language-agnostic tolset for semantic triples extractions.

* Input format are sentences in first-order logic form produced by [Metaphor](https://github.com/metaphor-adp/Metaphor-ADP) semantic pipelines.
* Extracts the following relationships:
  1. `subj_verb_dirobj([noun*],verb,[noun+]) ("John reads a book")`
  1. `subj_verb_indirobj([noun*],verb,[noun+]) ("John gives to Mary")`
  1. `subj_verb_instr([noun*],verb,[noun+]) ("Джон работает топором")`
  1. ` subj_verb([noun+], verb) ("John runs") // only if there is no dirobj and indirobj`
  1. `subj_verb_prep_compl([noun*],verb,prep,[noun+]) ("John comes from London")`
  1. `subj_verb_verb_prep_noun([noun*],verb,verb,prep,[noun+]) ("John tries to go into the house")`
  1. `subj_verb_verb([noun+],verb,verb) ("John tries to go") -> only if there is no prep attached to the second verb`
  1. `noun_be_prep_noun(noun,verb,prep,noun) ("intention to leave for money")`
  1. `noun_be(noun,verb) ("intention to leave") -> only if there is no prep attached to verb`
 
