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

### Input/Output Examples:

**Input (Logical Form):**

```
% В четверг , 7 февраля 2013 года , стартовала официальная продажа билетов на Олимпийские игры в Сочи —
% ровно за год до начала соревнований .
id(1).
[1001]:в-in(e1,e5,x1) & [1002]:четверг-nn(e2,x1) & [1005]:февраль-nn(e3,x2) & [1007]:год-nn(e4,x3) & 
[1009]:стартовать-vb(e5,x4,u1,u2) & [1010]:официальный-adj(e6,x4) & [1011]:продажа-nn(e7,x4) &
[1012]:билет-nn(e8,x5) & [1013]:на-in(e9,x5,x6) & [1014]:олимпийский-adj(e10,x6) & [1015]:игра-nn(e11,x6) &
[1016]:в-in(e12,x6,x7) & [1017]:сочи-nn(e13,x7) & [1019]:ровно-rb(e14,e15) & [1020]:за-in(e15,e5,x8) &
[1021]:год-nn(e16,x8) & [1022]:до-in(e17,x9,x10) & [1023]:начало-nn(e18,x10) & [1024]:соревнование-nn(e19,x11) &
card(e20,u3,7) & card(e21,x3,2013) & of-in(e22,x2,x3) & of-in(e23,x4,x5) & typelt(e24,x5,s1) & typelt(e25,x6,s2) &
of-in(e26,x10,x11) & typelt(e27,x11,s3) & past(e28,e5)

% В первые же часы билеты на самые интересные широкому кругу болельщиков виды программы — хоккей , биатлон ,
% сноуборд — были раскуплены чуть менее чем полностью .
id(2).
[2001]:в-in(e1,x1,x2) & [2004]:часы-nn(e2,x2) & [2005]:билет-nn(e3,x1) & [2006]:на-in(e4,x1,x3) &
[2008]:интересный-adj(e5,x3) & [2009]:широкий-adj(e6,x3) & [2010]:круг-nn(e7,x3) & [2011]:болельщик-nn(e8,x4) &
[2012]:вид-nn(e9,x1) & [2013]:программа-nn(e10,x5) & [2015]:хоккей-nn(e11,x6) & [2017]:биатлон-nn(e12,x7) &
[2019]:сноуборд-nn(e13,x8) & [2022]:раскупить-vb(e14,u1,x8,u2) & [2023]:чуть-rb(e15,e16) & [2024]:менее-rb(e16,e14) &
[2025]:чем-cnj(e17,x9) & [2026]:полностью-rb(e18,e17) & card(e19,x2,1) & typelt(e20,x2,s1) & typelt(e21,x1,s2) &
of-in(e22,x3,x4) & typelt(e23,x4,s3) & typelt(e24,x1,s4) & of-in(e25,x1,x5) & past(e26,x8) & past(e27,e14)

% Что касается мужского хоккея , например , то недоступными оказались пропуска на все игры плей-офф — и это при том ,
% что даже сетка турнира составлена пока не целиком .
id(3).
[3002]:касаться-vb(e1,u1,x1,u2) & [3003]:мужской-adj(e2,x1) & [3004]:хоккей-nn(e3,x1) & [3006]:например-rb(e4,e5) &
[3008]:то-cnj(e5,x2) & [3009]:недоступный-adj(e6,x3) & [3010]:оказаться-vb(e7,x4,u3,u4) & [3011]:пропуск-nn(e8,x4) &
[3012]:на-in(e9,x4,x5) & [3014]:игра-nn(e10,x5) & [3015]:плей-офф-nn(e11,x6) & thing(e12,x7) 
[3019]:при-in(e13,x8,x7) & [3024]:сетка-nn(e14,x9) & [3025]:турнир-nn(e15,x10) & [3026]:составить-vb(e16,x9,u5,u6) &
[3027]:пока-cnj(e17,x11) & [3029]:целиком-rb(e18,e17) & of-in(e19,x5,x6) & of-in(e20,x9,x10) & not(e21,e18) &
past(e22,e7) & past(e23,e16)
```

Output():

```
rel_type,arg1,arg2,arg3,arg4,arg5,arg6,freq
noun_adj,федерация-NN, российский-ADJ,<->,<->,<->,162267
subj_verb,речь-NN,идти-VB,<->,<->,<->,85846
subj_verb_dirobj,<NONE>,обратить-VB,внимание-NN,<->,<->,64583
noun_adj,житель-NN,местный-ADJ,<->,<->,<->,17450
```

## Mapping Instances to Classes
