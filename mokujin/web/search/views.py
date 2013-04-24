#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

# Create your views here.

import itertools

from mokujin.index import TripleIndex
from mokujin.index import SearchEngine
from mokujin.web.settings import INDEX_DIR
from django.shortcuts import render_to_response


indexer = TripleIndex(INDEX_DIR)
engine = SearchEngine(indexer)


class SearchResultWrapper(object):

    def __init__(self, search_result, max_results=100, show_all=False):
        search_result = list(search_result)
        search_result.sort(key=lambda stamp: -stamp[-1])
        self.total_found = len(search_result)
        self.max_results = max_results
        if len(search_result) > max_results:
            if not show_all:
                search_result = search_result[0:max_results]
        self.search_result = search_result
        if len(search_result) == 0:
            self.max_length = 0
        else:
            self.max_length = max(itertools.imap(lambda triple: len(triple), search_result))
        self.size = len(search_result)

    def __iter__(self):
        for triple_stamp in self.search_result:
            triple_row = TripleIndex.stamp2triple(triple_stamp, engine.id_term_map, map_none=True)
            triple_ext = []
            for i in range(0, len(triple_row) - 1):
                triple_ext.append(triple_row[i])
            for _ in xrange(self.max_length - len(triple_row)):
                triple_ext.append("<EMPTY>")
            triple_ext.append(triple_row[-1])
            yield triple_ext


def triples(request):
    raw_query = request.GET.get("q", "")
    show_all = request.GET.get("all", False)
    if raw_query:
        query = raw_query.split("#")
        if len(query) > 0:
            term = query[0]
            if len(query) > 1:
                try:
                    term_pos = int(query[1])
                except Exception:
                    term_pos = -1
            else:
                term_pos = -1
        else:
            term = None
            term_pos = -1

        if term is not None and term.encode("utf-8") in engine.term_id_map:
            found_triples = engine.search(arg_query=((term, term_pos),))
            results = SearchResultWrapper(found_triples, max_results=20, show_all=show_all)
            return render_to_response("triples.html", {
                "query": raw_query,
                "result": results,
                "all": show_all,
                "url": request.build_absolute_uri,
            })
        else:
            return render_to_response("triples.html", {
                "query": raw_query,
                "message": "Term not found",
                "all": show_all,
                "url": request.build_absolute_uri,
            })
    else:
        return render_to_response("triples.html", {
            "query": raw_query,
            "all": show_all,
            "url": request.build_absolute_uri,
        })


def novels(request):
    raw_query = request.GET.get("q", "")
    show_all = request.GET.get("all", False)
    if raw_query:
        query = raw_query.split("#")
        if len(query) > 0:
            term = query[0]
            if len(query) > 1:
                try:
                    term_pos = int(query[1])
                except Exception:
                    term_pos = -1
            else:
                term_pos = -1
        else:
            term = None
            term_pos = -1

        if term is not None and term.encode("utf-8") in engine.term_id_map:
            found_triples = engine.search(arg_query=((term, term_pos),))
            results = SearchResultWrapper(found_triples, max_results=20, show_all=show_all)
            return render_to_response("novels.html", {
                "query": raw_query,
                "result": results,
                "all": show_all,
                "url": request.build_absolute_uri,
            })
        else:
            return render_to_response("novels.html", {
                "query": raw_query,
                "message": "Term not found",
                "all": show_all,
                "url": request.build_absolute_uri,
            })
    else:
        return render_to_response("novels.html", {
            "query": raw_query,
            "all": show_all,
            "url": request.build_absolute_uri,
        })
