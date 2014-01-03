#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

import numpy as np


def lda_similarity(w1, w2, dictionary, lda):
    try:
        lda_1 = lda.state.get_lambda()[:, dictionary.token2id[w1]]
        lda_1 /= np.sum(lda_1)
        lda_2 = lda.state.get_lambda()[:, dictionary.token2id[w2]]
        lda_2 /= np.sum(lda_2)
        return np.sum(lda_1*lda_2)
    except:
        return -1.0