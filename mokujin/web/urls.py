#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

from django.conf.urls import url
from django.conf.urls import patterns


urlpatterns = patterns("", url(r"^$", "mokujin.web.search.views.search_index", name="search_index"),)

