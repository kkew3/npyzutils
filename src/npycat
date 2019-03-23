import sys
import argparse
import logging
logging.basicConfig(format='%(filename)s: %(levelname)s: %(message)s')

import numpy as np


def no_trailing_newline(s):
    if s.endswith('\n'):
        s = s[:-1]
    return s

class ArgumentParser(argparse.ArgumentParser):

    def error(self, message):
        self.print_help(sys.stderr)
        self.exit(2, '%s: error: %s\n' % (self.prog, message))


def make_parser():
    parser = ArgumentParser(
        description='Concatenate or stack several npy files to one npy file.',
        epilog='Return code: '
               '0) success; '
               '1) argument parsing error; '
               '2) failed to load one or more npy file(s); '
               '4) arrays have inconsistent dimension; '
               '8) failed to write result to file.')
    parser.add_argument('-s', '--stack', action='store_true',
                        help='stack arrays rather than concatenate them')
    parser.add_argument('-d', '--dim', type=int, default=0,
                        help='the dimension to concatenate/stack, default '
                             'to %(default)s')
    parser.add_argument('-o', '--tofile',
                        help='the npy file to write; if not specified, the '
                             'binary result will be written to stdout, which '
                             'is generally not recommended')
    parser.add_argument('-t', '--textwrite',
                        choices=('always', 'auto', 'never'),
                        default='auto',
                        help='when "auto", write in text mode only if the '
                             'output device is stdout, default to '
                             '%(default)s')
    parser.add_argument('-S', '--strict', action='store_true',
                        help='fail immediately if a numpy file cannot be '
                             'loaded')
    parser.add_argument('npyfiles', nargs='*',
                        help='npyfiles to concatenate; if not provided '
                             'anything, a list of npy filenames will be '
                             'expected at stdin, one per line')
    return parser


def main():
    args = make_parser().parse_args()
    if args.npyfiles:
        npyfiles = args.npyfiles
    else:
        npyfiles = list(map(no_trailing_newline, sys.stdin))
    all_data = []
    for filename in npyfiles:
        try:
            data = np.load(filename)
        except OSError:
            logging.warning('Failed to load "%s"', filename)
            if args.strict:
                sys.exit(2)
        else:
            all_data.append(data)

    merge = np.stack if args.stack else np.concatenate
    try:
        result = merge(all_data, axis=args.dim)
    except ValueError as e:
        logging.error(str(e))
        sys.exit(4)

    if args.textwrite == 'always':
        save = np.savetxt
    elif args.textwrite == 'never':
        save = np.save
    elif args.tofile:
        save = np.save
    else:
        save = np.savetxt

    if args.tofile:
        try:
            with open(args.tofile, 'wb') as outfile:
                save(outfile, result)
        except OSError:
            logging.error('Failed to write result to "%s"', args.tofile)
            sys.exit(8)
    else:
        save(sys.stdout, result)


if __name__ == '__main__':
    try:
        main()
    except (BrokenPipeError, KeyboardInterrupt):
        sys.exit(130)
