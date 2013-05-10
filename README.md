# MOKUJIN

A a language-agnostic tolset for semantic triples extractions.

## Relation Extractor

Usage:

```
python mokujin.py [<input file in logical form>] [<output file>]
```

### Features

* Input format are sentences in first-order logic form produced by [Metaphor](https://github.com/metaphor-adp/Metaphor-ADP) semantic pipelines.
* Extracts the following relationships:

  **Verbs**

  1. `subj_verb_dirobj([noun*],verb,[noun+]) ("John reads a book")`
  2. `subj_verb_indirobj([noun*],verb,[noun+]) ("John gives to Mary")`
  3. `subj_verb_instr([noun*],verb,[noun+]) ("Джон работает топором")`
  4. `subj_verb([noun+], verb) ("John runs") // only if there is no dirobj and indirobj`
  5. `subj_verb_prep_compl([noun*],verb,prep,[noun+]) ("John comes from London")`
  6. `subj_verb_verb_prep_noun([noun*],verb,verb,prep,[noun+]) ("John tries to go into the house")`
  7. `subj_verb_verb([noun+],verb,verb) ("John tries to go") // only if there is no prep attached to the second verb`

  **Nouns**

  1. `noun_be_prep_noun(noun,verb,prep,noun) ("intention to leave for money")`
  2. `noun_be(noun,verb) ("intention to leave") // only if there is no prep attached to verb`
  3. `noun_adj_prep_noun(noun,adjective,prep,noun) ("The book is good for me") -> only if "for" has "good" (and not "is") as its arg`
  5. `noun_adj([noun+],adjective) ("The book is good") // only if there is no prep attached to adj as its arg`
  6. `noun_verb_adv_prep_noun(adverb,verb) ("John runs fast for me") -> only if "for" has "fast" (and not "runs") as its arg`
  7. `noun_verb_adv([noun*],verb,adverb) ("John runs fast") // only if there is no prep attached to adv`
  8. `nn_prep([noun+],prep,noun) ("[city]&bike for John") // only if "for" has "bike" (and not some verb) as its arg`
  9. `nn(noun,noun) ("city bike") // only if there is no prep attached to the second noun`
  10. `nnn(noun,noun,noun) ("Tzar Ivan Grozny")`
  11. `noun_equal_prep_noun(noun,noun,prep,noun) ("John is a man of heart") // only if "of" has "man" (and not "is") as its arg.`
  12. `noun_equal_noun(noun,noun) ("John is a biker") // only if there is no prep attached to the second noun`
  13. `noun_prep_noun(noun,prep,noun) ("house in London")`
  14. `noun_prep_prep_noun(noun,prep,prep,noun) ("book out of the store")`
  
  **Verbs**

  1. `compl(anything,anything) ("близкий мне")`
  
## Mapping Instances to Classes
