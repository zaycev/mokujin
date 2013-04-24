#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

from django.conf.urls import url
from django.conf.urls import patterns
from django.shortcuts import redirect


urlpatterns = patterns(
    "",
    url("^$", lambda _: redirect("/triples/")),
    url(r"^triples/$", "mokujin.web.search.views.triples", name="triples"),
    url(r"^novels/$", "mokujin.web.search.views.novels", name="novels"),
)

