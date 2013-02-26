#!/usr/bin/env python
# coding: utf-8

# Copyright (C) USC Information Sciences Institute
# Author: Vladimir M. Zaytsev <zaytsev@usc.edu>
# URL: <http://nlg.isi.edu/>
# For more information, see README.md
# For license information, see LICENSE

# combine.py – a simple tool for combining many text file into bigger one.
# Usage example:
# ./combine.py --dir datasets/russian/untagged/ \
#              --ofile combined.txt \
#              -p "*.rus" \
#              -ie "utf-16" \
#              -oe "utf-8"


import os
import sys
import argparse

from fnmatch import fnmatch


def visit(pattern, dir_name, files, rd_file, wr_file):
    for filename in files:
        if fnmatch(filename, pattern):
            fl_path = os.path.join(dir_name, filename)
            fl = open(fl_path, "r")
            wr_file(rd_file(fl))


def read(i_file):
    for line in i_file:
        yield line


def read_enc(i_file, enc):
    for line in i_file:
        yield line.decode(enc)


def write(o_file, lines):
    for line in lines:
        o_file.write(line)


def write_enc(o_file, enc, lines):
    for line in lines:
        o_file.write(line.encode(enc))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--dir", default=None, type=str,
                        help="A path to the directory which contains the files "
                             "which should be combined.")
    parser.add_argument("-o", "--ofile", default=None, type=str,
                        help="A path to the combined file which will be "
                             "produced.")
    parser.add_argument("-p", "--pattern", default="*", type=str,
                        help="File name pattern which should be applied to "
                             "filter the files which should be combined.")
    parser.add_argument("-r", "--recursive", default=0, choices=(0, 1),
                        help="Recursively traverse subdirs of the input "
                             "directory.")
    parser.add_argument("-ie", "--iencoding", default=None, type=str,
                        help="Encoding of the input files. Specify in case, "
                             "when the conversation should be performed.")
    parser.add_argument("-oe", "--oencoding", default=None, type=str,
                        help="Encoding of the output files.")
    args = parser.parse_args()

    out_file = file(args.ofile, "w") if args.ofile is not None else sys.stdout

    if args.iencoding is not None and args.oencoding is not None:
        rd_file = lambda i_file: read_enc(i_file, args.iencoding)
        wr_file = lambda lines: write_enc(out_file, args.oencoding, lines)
    else:
        rd_file = read
        wr_file = lambda lines: write(out_file, lines)

    vst = lambda pattern, dir_name, files: \
        visit(pattern, dir_name, files, rd_file, wr_file)

    os.path.walk(args.dir, vst, args.pattern)

    out_file.close()