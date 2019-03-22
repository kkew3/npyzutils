#!/usr/bin/env python
import sys
import argparse
from collections import defaultdict
import logging
logging.basicConfig(format='%(filename)s: %(levelname)s: %(message)s')

import numpy as np


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_help(sys.stderr)
        self.exit(1, '%s: error: %s\n' % (self.prog, message))


def make_parser():
    parser = ArgumentParser(
        description='Concatenate or stack several npz files to one npz '
                    'file.',
        epilog='`--\' is supported to separate optional and positional '
               'arguments.')
    parser.add_argument('-s', '--stack', action='store_true',
                            help='stack arrays rather than concatenate them')
    parser.add_argument('-d', '--dim', type=int, default=0,
                        help='the dimension to concatenate/stack, default '
                             'to %(default)s')
    parser.add_argument('-o', '--tofile',
                        help='the npz file to write; if not specified, the '
                             'binary result will be written to stdout, which '
                             'is generally not recommended')
    parser.add_argument('-S', '--strict', action='store_true',
                        help='fail immediately if a numpy file cannot be '
                             'loaded')
    parser.add_argument('npzfiles', nargs='*',
                        help='npzfiles to concatenate; if not provided '
                             'anything, a list of npz filenames will be '
                             'expected at stdin, one per line')
    parser.add_argument('-k', '--keys', nargs='+',
                        help='npz field keys to use; if not specified, all '
                             'field keys of the first npz file provided will '
                             'be used')
    return parser


def no_trailing_newline(s):
    if s.endswith('\n'):
        s = s[:-1]
    return s


def main():
    args = make_parser().parse_args()
    if args.npzfiles:
        npzfiles = args.npzfiles
    else:
        npzfiles = list(map(no_trailing_newline, sys.stdin))
    all_data = defaultdict(list)
    keys = None
    for filename in npzfiles:
        try:
            data = np.load(filename)
        except OSError:
            if args.strict:
                logging.error('Failed to load "%s"', filename)
                sys.exit(2)
            else:
                logging.warning('Failed to load "%s"', filename)
        else:
            if keys is None:
                if args.keys is not None:
                    keys = args.keys
                else:
                    keys = list(data.keys())
            for k in keys:
                all_data[k].append(data[k])

    merge = np.stack if args.stack else np.concatenate
    all_results = {}
    if keys is not None:
        try:
            for k in keys:
                all_results[k] = merge(all_data[k], axis=args.dim)
        except ValueError as err:
            logging.error(str(err))
            sys.exit(4)

    if args.tofile:
        try:
            with open(args.tofile, 'wb') as outfile:
                np.savez(outfile, **all_results)
        except OSError:
            logging.error('Failed to write result to "%s"', args.tofile)
    else:
        np.savez(sys.stdout, **all_results)


if __name__ == '__main__':
    try:
        main()
    except (BrokenPipeError, KeyboardInterrupt):
        sys.exit(130)
