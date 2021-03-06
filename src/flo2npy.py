#!/usr/bin/env python3
import argparse
import os
import sys
import io
import shutil
import logging

import numpy as np

TAG_FLOAT = 202021.25

LOGGING_LEVEL = logging.WARNING

ERRNO_ARGS = 1
ERRNO_READ = 2
ERRNO_DATA = 4
ERRNO_WRITE = 8
ERRNO_INT = 130


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        args = {'prog': self.prog, 'message': message}
        self.exit(ERRNO_ARGS, '{prog}: error: {message}\n'.format(**args))


def make_parser():
    parser = ArgumentParser(
        prog='flo2npy',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Convert .flo optical flow file to numpy npy format.',
        epilog=('Adapted from https://github.com/Johswald/'
                'flow-code-python/blob/master/readFlowFile.py'))
    parser.add_argument(
        '-O',
        '--output',
        metavar='OUTFILE',
        type=os.path.normpath,
        help=('write to OUTFILE rather than FLOWFILE.npy; '
              'or `-\' to write raw bytes of the result npy '
              'to stdout'))
    parser.add_argument(
        'flofile', metavar='FLOFILE', help='the .flo file to convert')
    return parser


class IllegalFloFileError(Exception):
    pass


def convert(flofile):
    with open(flofile, 'rb') as infile:
        if np.fromfile(infile, np.float32, count=1)[0] != TAG_FLOAT:
            raise IllegalFloFileError
        w, h = np.fromfile(infile, np.int32, count=2)
        data = np.fromfile(infile, np.float32, 2 * w * h)
        flow = data.reshape((h, w, 2))
    return flow


def main():
    logging.basicConfig(
        format='%(filename)s: %(levelname)s: %(message)s', level=LOGGING_LEVEL)
    args = make_parser().parse_args()
    try:
        flow = convert(args.flofile)
    except IllegalFloFileError:
        logging.error('illegal flow file "%s" as flow number is incorrect',
                      args.flofile)
        return ERRNO_READ | ERRNO_DATA
    except FileNotFoundError:
        logging.error('cannot open "%s", no such file', args.flofile)
        return ERRNO_READ
    except IOError:
        logging.error('cannot open "%s"', args.flofile)
        return ERRNO_READ
    except KeyboardInterrupt:
        return ERRNO_INT

    output = args.output or (args.flofile + '.npy')
    if output != '-':
        try:
            with open(output, 'wb') as outfile:
                np.save(outfile, flow)
        except IOError:
            logging.error('cannot write to "%s"', output)
            return ERRNO_WRITE
    else:
        with io.BytesIO() as cbuf:
            np.save(cbuf, flow)
            cbuf.seek(0)
            shutil.copyfileobj(cbuf, sys.stdout.buffer)

    return 0


if __name__ == '__main__':
    sys.exit(main())
