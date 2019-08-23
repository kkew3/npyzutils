#!/usr/bin/env python3
import sys
import io
import ast
import shutil
import zipfile
import argparse
import logging

import numpy as np

ERRNO_ARGS = 1
ERRNO_READ = 2
ERRNO_INT = 130

errno = 0

LOGGING_LEVEL = logging.WARNING


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        args = {'prog': self.prog, 'message': message}
        self.exit(ERRNO_ARGS, '{prog}: error: {message}\n'.format(**args))


def make_parser():
    parser = ArgumentParser(
        prog='npyzshape',
        description=('Inspect array shapes of npy or npz files. The output '
                     'will be of format `<filename>\\t<key/empty-if-npy>\\t'
                     '<shape>/\"<scalar>"\\n\' for each line. If the input '
                     'is from stdin, `<filename>\\t\' will be omitted in '
                     'output lines.'))
    parser.add_argument(
        'npyzfiles',
        nargs='*',
        metavar='NPYZFILE',
        help=('the npy/npz files to inspect shapes, or leave '
              'empty to read from stdin raw bytes of an npy '
              'or npz file. Note that reading from stdin '
              'requires loading the entire file into memory, '
              'since stdin is not seekable, whereas reading '
              'from regular files need not'))
    return parser


class NotNpyFileError(Exception):
    pass


def get_shape_npy(infile):
    global errno
    magic = infile.read(6)
    if magic != b'\x93NUMPY':
        raise NotNpyFileError
    try:
        major = infile.read(1)[0]
    except IndexError:
        errno |= ERRNO_READ
        return
    try:
        _ = infile.read(1)[0]
    except IndexError:
        errno |= ERRNO_READ
        return
    if major == 1:
        headerlen = infile.read(2)
        if len(headerlen) < 2:
            errno |= ERRNO_READ
            return
        headerlen = int.from_bytes(headerlen, byteorder='little', signed=False)
    else:
        headerlen = infile.read(4)
        if len(headerlen) < 4:
            errno |= ERRNO_READ
            return
        headerlen = int.from_bytes(headerlen, byteorder='little', signed=False)
    header = infile.read(headerlen)
    if len(header) < headerlen:
        errno |= ERRNO_READ
        return
    if major in (1, 2):
        header = header.decode('latin1')
    else:
        header = header.decode('utf-8')
    header = ast.literal_eval(header)
    try:
        shape = header['shape']
    except KeyError:
        errno |= ERRNO_READ
        return
    return shape


def inspect_file(infile):
    global errno
    try:
        shape = get_shape_npy(infile)
    except NotNpyFileError:
        infile.seek(0)
        shape = {}
        try:
            with zipfile.ZipFile(infile, 'r') as zf:
                for filename in zf.namelist():
                    with zf.open(filename, 'r') as infile:
                        if filename.endswith('.npy'):
                            key = filename[:-4]
                        else:
                            key = filename
                        try:
                            shape[key] = get_shape_npy(infile)
                        except NotNpyFileError:
                            pass
        except zipfile.BadZipFile:
            errno |= ERRNO_READ
            shape = None
    else:
        if shape == ():
            shape = '<scalar>'
    return shape


def main():
    logging.basicConfig(
        format='%(filename)s: %(levelname)s: %(message)s', level=LOGGING_LEVEL)
    args = make_parser().parse_args()
    if args.npyzfiles:
        for filename in args.npyzfiles:
            try:
                with open(filename, 'rb') as infile:
                    shape = inspect_file(infile)
            except OSError as err:
                logging.error('failed to load "%s" due to %s; skipped',
                              filename, err)
                errno |= ERRNO_READ
            else:
                if shape is None:
                    logging.error('failed to load "%s" as either npy or npz '
                                  'file; skipped', filename)
                    errno |= ERRNO_READ
                elif shape == {}:
                    logging.warning('failed to find any npy file in "%s" '
                                    'loaded as npz file; skipped', filename)
                else:
                    try:
                        for k, v in shape.items():
                            print(filename, k, v, sep='\t')
                    except AttributeError:
                        print(filename, '', shape, sep='\t')
    else:
        with io.BytesIO() as cbuf:
            shutil.copyfileobj(sys.stdin.buffer, cbuf)
            cbuf.seek(0)
            shape = inspect_file(cbuf)
        if shape is None:
            logging.error('failed to load "/dev/stdin" as either npy or '
                          'npz file')
            errno |= ERRNO_READ
        elif shape == {}:
            logging.warning('failed to find any npy file in "/dev/stdin" '
                            'loaded as npz file')
        else:
            try:
                for k, v in shape.items():
                    print(k, v, sep='\t')
            except AttributeError:
                print('', shape, sep='\t')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        errno |= ERRNO_INT
    except BrokenPipeError:
        sys.stderr.close()
    finally:
        sys.exit(errno)
