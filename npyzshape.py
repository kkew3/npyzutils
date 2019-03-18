#!/usr/bin/env python3
import sys
import argparse

import numpy as np


def make_parser():
    parser = argparse.ArgumentParser(
        description='Print array shape. If the input file is an npy file, '
                    'the output will be a comma-separated list of integers, '
                    'signifying the dimension along each axis; if the input '
                    'file is an npz file, each line of the output will be '
                    '"${filename}:${comma-separated-list-of-dimensions}".')
    # Reading from stdin is too complicated ... See:
    # - https://stackoverflow.com/q/11305790/7881370
    # - https://stackoverflow.com/q/14283025/7881370
    parser.add_argument('npyzfile')
    return parser


if __name__ == '__main__':
    args = make_parser().parse_args()
    npyzfile = args.npyzfile if args.npyzfile else sys.stdin.buffer
    data = np.load(npyzfile)
    try:
        for k, v in data.items():
            if len(v.shape):
                print(''.join((k, ':', ','.join(map(str, v.shape)))))
            else:
                print(''.join((k, ':', '<scalar>')))
    except AttributeError:
        print(','.join(map(str, data.shape)))
