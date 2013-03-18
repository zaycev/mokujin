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
import collections

from fnmatch import fnmatch


def accumulate_table(pattern, dir_name, files, result_table):
    for filename in files:
        if fnmatch(filename, pattern):
            fl_path = os.path.join(dir_name, filename)
            with open(fl_path, "r") as fl:
                for row in fl:
                    fields = row.split(", ")
                    freq = int(fields[-1])
                    r_key = ", ".join(fields[0:(len(fields) - 1)])
                    result_table[r_key] += freq


def write_table(result_table, ofile):
    for r_key, freq in result_table.most_common():
        ofile.write(r_key)
        ofile.write(", ")
        ofile.write(str(freq))
        ofile.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--dir", default=None, type=str, help="A path to the directory containing the csv "
                                                                    "files which should be reduced.")
    parser.add_argument("-o", "--ofile", default=None, type=str, help="A path to the result file")
    parser.add_argument("-p", "--pattern", default="*", type=str, help="File name pattern which should be applied to "
                                                                       "filter the files which should be reduced.")
    parser.add_argument("-r", "--recursive", default=0, choices=(0, 1), help="Recursively traverse sub-dirs of the "
                                                                             "input directory.")
    args = parser.parse_args()
    out_file = file(args.ofile, "w") if args.ofile is not None else sys.stdout
    result_table = collections.Counter()
    os.path.walk(args.dir,
                 lambda pattern, dir_name, files: accumulate_table(pattern, dir_name, files, result_table),
                 args.pattern)

    write_table(result_table, out_file)

    out_file.close()