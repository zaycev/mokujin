#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

import unidecode

# RU_EN_MAP = {
#     u"а": "a",
#     u"б": "b",
#     u"в": "v",
#     u"г": "g",
#     u"д": "d",
#     u"е": "e",
#     u"ё": "yo",
#     u"ж": "j",
#     u"з": "z",
#     u"и": "i",
#     u"й": "y",
#     u"к": "k",
#     u"л": "l",
#     u"м": "m",
#     u"н": "n",
#     u"о": "o",
#     u"п": "p",
#     u"р": "r",
#     u"с": "s",
#     u"т": "t",
#     u"у": "u",
#     u"ф": "f",
#     u"х": "h",
#     u"ц": "ts",
#     u"ч": "ch",
#     u"ш": "sh",
#     u"щ": "sch",
#     u"ъ": "",
#     u"ы": "y",
#     u"ь": "",
#     u"э": "e",
#     u"ю": "yu",
#     u"я": "ya",
# }
# 
# 
# def transliterate_ru(string):
#     transliterated = ""
#     string = string.lower()
#     if not isinstance(string, unicode):
#         string = string.decode("utf-8")
#     for c in string:
#         if c in RU_EN_MAP:
#             transliterated += RU_EN_MAP[c]
#         else:
#             transliterated += c
#     return transliterated

def transliterate_ru(string):
    if isinstance(string, unicode):
        return unidecode.unidecode(string)
    return unidecode.unidecode(string.decode("utf-8"))
