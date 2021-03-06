#!/usr/bin/env python3
import pdb
import argparse
import shutil
import sys
import io
import logging

import numpy as np
from sliceparser import parse_slice

ERRNO_ARGS = 1
ERRNO_READ = 2
ERRNO_DATA = 4
ERRNO_WRITE = 8
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
        prog='npyzindex',
        description='Index subarray from npy/npz files.')
    parser.add_argument(
        '-e',
        '--index-expr',
        dest='indexexprs',
        metavar='INDEX/KEYEDINDEX',
        type=_slice_expr,
        action='append',
        help=('numpy style ndarray index to sample from underlying array. '
              'The index may either be INDEX, or KEY<slash>INDEX, where the '
              'latter form is to sample from KEY in npz. For example, '
              '`-e2\' picks the third element from data, and '
              '`-etrain/2\' picks the third element from the array named '
              '`train\'. If the underlying file is an npy file, using the '
              'keyed form leads to KeyError; if the underlying is an npz '
              'file, using the key-free form applies the indexing to all '
              'keys simultaneously. '
              'Multiple `-e\' options can be appended to form a '
              'sequence of sampling. For example, `-e2 -e:,3\' picks the '
              'third row and then the fourth column of the array, which is '
              'equivalent to `-e2,3\''))
    parser.add_argument(
        '-T',
        '--from-file',
        dest='from_file',
        metavar='FILE',
        help=('read filenames to index from FILE; use `-\' '
              'to denote stdin. In either case the filenames '
              'should be placed one per line'))
    parser.add_argument(
        '-O',
        '--output',
        metavar='.SUFFIX/-',
        nargs='?',
        const='',
        default='.out',
        type=_output_suffix,
        help=('controls how the output is saved. If using the form .SUFFIX, '
              'the indexed array will be saved as `NPYZFILE.SUFFIX\'. If '
              'specified as `-O-\', the output bytes will be written to '
              'stdout, or raise error if there\'s more than one NPYZFILE. '
              'If specified as `-O\', the change will be made in-place. '
              'If not specified as `-O-\' but input is from stdin, it will '
              'be treated as if `-O-\' were specified. Default to '
              '`%(default)s\''))
    parser.add_argument(
        'npyzfiles',
        metavar='NPYZFILE',
        nargs='*',
        help=('the npy/npz files to index using the set of '
              '[KEY/]INDEX expression. A series of both npy '
              'and npz files may lead to KeyError (see help '
              'for `-e\' option. '
              'If none is given, and if `-T\' is provided, then '
              'the NPYZFILEs will be obtained from FILE. '
              'If neither NPYZFILE nor `-T\' is provided, then '
              'raw bytes of an npy/npz file will be expected '
              'from stdin. '
              'If both NPYZFILE and `-T\' are provided, then '
              'the union of them will be used'))
    return parser


def _output_suffix(string):
    if string == '-' or string.startswith('.'):
        return string
    raise argparse.ArgumentTypeError


def _slice_expr(string):
    try:
        key, expr = string.split('/', maxsplit=1)
    except ValueError:
        expr = string
        try:
            compiled_expr = parse_slice(expr)
        except ValueError as err:
            raise argparse.ArgumentTypeError(
                'illegal INDEX `{}\''.format(string)) from err
        return compiled_expr
    else:
        try:
            compiled_expr = parse_slice(expr)
        except ValueError as err:
            raise argparse.ArgumentTypeError(
                'illegal KEYEDINDEX `{}\''.format(string)) from err
        return key, compiled_expr


def decide_input_files(args):
    global errno
    filenames = []
    if args.from_file == '-':
        filenames.extend(x.rstrip('\n') for x in sys.stdin)
    elif args.from_file:
        try:
            with open(args.from_file) as infile:
                filenames.extend(x.rstrip('\n') for x in infile)
        except OSError as err:
            logging.warning('failed to load NPYZFILEs from "%s" due to %s',
                            args.from_file, err)
            errno |= ERRNO_READ
            if not args.npyzfiles:
                logging.error('nothing to load; aborted')
                sys.exit(errno)
    if args.npyzfiles:
        filenames.extend(args.npyzfiles)
    return filenames or None


def decide_output_files(args, filenames):
    if filenames and len(filenames) > 1 and args.output == '-':
        logging.error('more than on input NPYZFILEs occur but outputing via '
                      'stdout')
        sys.exit(errno | ERRNO_ARGS)
    if args.output == '-':
        return None
    if not filenames:
        logging.warning('writing to stdout as input is stdin')
        return None
    return [x + args.output for x in filenames]


def read_data(filename=None):
    global errno

    data = None
    if filename is None:
        with io.BytesIO() as cbuf:
            shutil.copyfileobj(sys.stdin.buffer, cbuf)
            cbuf.seek(0)
            try:
                with np.load(cbuf) as infile:
                    data = {k: infile[k] for k in infile.keys()}
            except AttributeError:
                logging.info(
                    'failed to read "/dev/stdin" as npz file, trying reading '
                    'as npy file')
                cbuf.seek(0)
                try:
                    data = np.load(cbuf)
                except OSError as err:
                    logging.error(
                        'failed to read "/dev/stdin" as npy/npz file due to '
                        '%s; skipped', err)
                    errno |= ERRNO_READ
            except OSError as err:
                logging.error(
                    'failed to read "/dev/stdin" as npy/npz file due to %s; '
                    'skipped', err)
                errno |= ERRNO_READ
    else:
        try:
            with np.load(filename) as infile:
                data = {k: infile[k] for k in infile.keys()}
        except AttributeError:
            logging.info(
                'failed to read "%s" as npz file, trying reading '
                'as npy file', filename)
            try:
                data = np.load(filename)
            except OSError as err:
                logging.error(
                    'failed to read "%s" as npy/npz file due to %s; '
                    'skipped', filename, err)
                errno |= ERRNO_READ
        except OSError as err:
            logging.error(
                'failed to read "%s" as npy/npz file due to %s; '
                'skipped', filename, err)
            errno |= ERRNO_READ
    return data


def index_data(exprs, data):
    for expr in exprs:
        if isinstance(expr[0], str):
            key, expr = expr
            try:
                data = data[key]
            except (KeyError, IndexError):
                logging.error('KeyError occurs for key "%s"', key)
                sys.exit(errno | ERRNO_DATA)
        if isinstance(data, dict):
            try:
                data = {k: data[k][expr] for k in data}
            except IndexError:
                logging.error(
                    'IndexError occurs when indexing data of '
                    'shape %s using compiled INDEX `%s',
                    {k: data.shape
                     for k in data}, expr)
                sys.exit(errno | ERRNO_DATA)
        else:
            try:
                data = data[expr]
            except IndexError:
                logging.error(
                    'IndexError occurs when indexing data of '
                    'shape %s using compiled INDEX `%s', data.shape, expr)
                sys.exit(errno | ERRNO_DATA)
    return data


def write_data(data, outfilename=None):
    global errno
    if outfilename:
        if isinstance(data, dict):
            try:
                with open(outfilename, 'wb') as outfile:
                    np.savez(outfile, **data)
            except OSError as err:
                logging.error(
                    'failed to save data to "%s" in npz format due to '
                    '%s; skipped', outfilename, err)
                errno |= ERRNO_WRITE
            else:
                logging.info('saved data to "%s" in npz format', outfilename)
        else:
            try:
                with open(outfilename, 'wb') as outfile:
                    np.save(outfile, data)
            except OSError as err:
                logging.error(
                    'failed to save data to "%s" in npy format due to '
                    '%s; skipped', outfilename, err)
                errno |= ERRNO_WRITE
            logging.info('saved data to "%s" in npy format', outfilename)
    else:
        with io.BytesIO() as cbuf:
            if isinstance(data, dict):
                try:
                    np.savez(cbuf, **data)
                except OSError as err:
                    logging.error(
                        'failed to save data to "/dev/stdout" in '
                        'npz format due to %s; skipped', err)
                    errno |= ERRNO_WRITE
                    return
                else:
                    logging.info('saved data to "/dev/stdout" in npz format')
            else:
                try:
                    np.save(cbuf, data)
                except OSError as err:
                    logging.error(
                        'failed to save data to "/dev/stdout" in '
                        'npy format due to %s; skipped', err)
                    errno |= ERRNO_WRITE
                    return
                else:
                    logging.info('saved data to "/dev/stdout" in npy format')
            cbuf.seek(0)
            shutil.copyfileobj(cbuf, sys.stdout.buffer)


def main():
    logging.basicConfig(
        format='%(filename)s: %(levelname)s: %(message)s', level=LOGGING_LEVEL)
    args = make_parser().parse_args()
    filenames = decide_input_files(args)
    logging.debug('input filenames = %s', filenames or '/dev/stdin')
    outfilenames = decide_output_files(args, filenames)
    logging.debug('output filenames = %s', outfilenames)
    if filenames and outfilenames:
        for filename, outfilename in zip(filenames, outfilenames):
            data = read_data(filename)
            if data is not None:
                data = index_data(args.indexexprs, data)
                write_data(data, outfilename)
    elif filenames:
        assert len(filenames) == 1, filenames
        for filename in filenames:  # pylint: disable=not-an-iterable
            data = read_data(filename)
            if data is not None:
                data = index_data(args.indexexprs, data)
                write_data(data)
    else:
        data = read_data()
        if data is not None:
            data = index_data(args.indexexprs, data)
            write_data(data)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logging.warning('written data may have corrupted due to interrupt')
        errno |= ERRNO_WRITE | ERRNO_INT
    except BrokenPipeError:
        logging.warning('written data may have corrupted due to broken pipe')
        sys.stderr.close()
        errno |= ERRNO_WRITE
    finally:
        sys.exit(errno)
