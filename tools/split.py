#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

import os
import sys
import argparse


SENT_END = 0xDC


class PlainSplitter(object):
    
    def __init__(self):
        self.prev_eol = False
        
    def map_line(self, line):
        if line == "\n":
            if self.prev_eol:
                return SENT_END, "\n"
            self.prev_eol = True
            return ""
        self.prev_eol = False
        return line,


class RuwacSplitter(object):
    
    def map_tokens(self, t):
        t[-1] = t[-1][0:(len(t[-1]) - 1)]
        mapping = u"%s	%s	%s	%s	%s	%s	%s	%s	_	_" % \
            (t[4], t[0], t[2], t[3], t[3], t[1], t[5], t[6])
        return mapping.encode("utf-8")
    
    def map_line(self, line):
        if (len(line) >= 5 and line[0:5] == "<text") or \
           (len(line) >= 6 and line[0:6] == "</text"):
            return (SENT_END, )
        line = line.decode("utf-8")
        tokens = line.split("\t")
        mapping = self.map_tokens(tokens)
        if tokens[1] == "SENT":
            return mapping, SENT_END
        if tokens[4] == "1":
            return SENT_END, mapping
        return (mapping, )


FORMAT_SPLITTER_MAP = {
    "plain": PlainSplitter,
    "ruwac": RuwacSplitter,
}


def split_file(ifile, ofilef, iformat, chunk_numb):
    splitter = FORMAT_SPLITTER_MAP[iformat]()
    source_size = os.path.getsize(ifile)
    ifile = file(ifile, "r")
    if chunk_numb is None:
        chunk_size = source_size
    else:
        chunk_size = source_size / chunk_numb
    read_bytes = 0
    curren_chunk = 1
    chunk = open(ofilef % curren_chunk, "w")
    prev_is_end = True
    for line in ifile:
        read_bytes += len(line)
        mappings = splitter.map_line(line)
        for mapping in mappings:
            if mapping is SENT_END:
                if not prev_is_end:
                    chunk.write("\n")
                    prev_is_end = True
                if read_bytes > chunk_size:
                    read_bytes = 0
                    chunk.close()
                    curren_chunk += 1
                    chunk = open(ofilef % curren_chunk, "w")
            else:
                prev_is_end = False
                chunk.write(mapping)
                # chunk.write("\n")
    
    if not chunk.closed:
        chunk.close()
    ifile.close()


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()

    iformats = FORMAT_SPLITTER_MAP.keys()

    parser.add_argument("-i", "--ifile", default=None, type=str)
    parser.add_argument("-o", "--ofilef", default=None, type=str)
    parser.add_argument("-n", "--chunknumb", default=1, type=int)
    parser.add_argument("-f", "--iformat", default="plain", type=str, choices=iformats)

    args = parser.parse_args()

    ifile = args.ifile
    ofilef = args.ofilef
    chunk_numb = args.chunknumb
    iformat = args.iformat

    if not ofilef or not ifile:
        sys.stderr.write("Error: you have to specify both – the input file path "
                         "and the output files format (-i/--ifile and -o/--ofilef)\n")
        exit(1)
        
    split_file(ifile, ofilef, iformat, chunk_numb)
