#!/usr/bin/env python3
import sys
import io
import shutil
import collections
import argparse
import logging

import numpy as np

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
        prog='npzcat',
        description=('Concatenate or stack several npz files to one npz '
                     'file.'))
    parser.add_argument(
        '-s',
        '--stack',
        action='store_true',
        help='stack arrays rather than concatenate them')
    parser.add_argument(
        '-d',
        '--dim',
        type=int,
        default=0,
        help=('the dimension to concatenate/stack, default '
              'to %(default)s'))
    parser.add_argument(
        '-K',
        '--keys',
        nargs='+',
        help=('npz field keys to use; if not specified, all '
              'field keys of the first npz file provided '
              'will be used'))
    parser.add_argument(
        '-O',
        '--output',
        metavar='OUTFILE',
        help=('the result will be written to OUTFILE. If '
              'not specified, the raw bytes (or text if `-H\''
              ' is given) will be written to stdout'))
    parser.add_argument(
        '-H',
        '--human-readable',
        dest='textwrite',
        action='store_true',
        help=('write to OUTFILE in text mode. Note that '
              'error occurs if any underlying array is more '
              'then 2D'))
    parser.add_argument(
        '--csv',
        action='store_true',
        help=('arrange the output in CSV with field names '
              'equal to the key names; effective only if '
              '`-H\' is specified'))
    parser.add_argument(
        '-T',
        '--from-file',
        dest='from_file',
        metavar='FILE',
        help=('read filenames to concatenate/stack from FILE;'
              ' use `-\' to denote stdin. In either case '
              'the filenames should be placed one per line'))
    parser.add_argument(
        'npzfiles',
        nargs='*',
        metavar='NPZFILE',
        help=('the npz files to concatenate/stack. '
              'If none is given here and if `-T\' is '
              'provided, then the NPZFILEs will be obtained '
              'from FILE. '
              'If neither NPZFILE nor `-T\' is provided, '
              'then raw bytes of an npz file will be '
              'expected from stdin. '
              'If both NPZFILE and `-T\' are provided, then '
              'the union of them will be used.'))
    return parser


def decide_input_files(args):
    global errno
    filenames = []
    if args.from_file == '-':
        filenames.extend(x.rstrip('\n') for x in sys.stdin)
        if not filenames and not args.npzfiles:
            logging.info('nothing to load; aborted')
            sys.exit(errno)
    elif args.from_file:
        try:
            with open(args.from_file) as infile:
                filenames.extend(x.rstrip('\n') for x in infile)
        except OSError as err:
            logging.warning('failed to load NPZFILEs from "%s" due to %s',
                            args.from_file, err)
            errno |= ERRNO_READ
        if not filenames and not args.npzfiles:
            logging.info('nothing to load; aborted')
            sys.exit(errno)

    if args.npzfiles:
        filenames.extend(args.npzfiles)
    return filenames or None


def read_data(filenames, keys=None):
    all_data = collections.OrderedDict()
    if filenames:
        for filename in filenames:
            try:
                data = np.load(filename)
            except OSError as err:
                logging.error('failed to load "%s" due to %s', filename, err)
                sys.exit(errno | ERRNO_READ)
            if not hasattr(data, 'keys'):
                logging.error('failed to load "%s" as npz file', filename)
                sys.exit(errno | ERRNO_READ)
            if keys is None:
                keys = list(data.keys())
            for k in keys:
                try:
                    arr = data[k]
                except KeyError as err:
                    logging.error('failed to load "%s" due to %s', filename,
                                  err)
                    sys.exit(errno | ERRNO_DATA)
                try:
                    all_data[k].append(arr)
                except KeyError:
                    all_data[k] = []
                    all_data[k].append(data[k])
                    logging.debug(
                        'loaded data of key "%s" of shape %s '
                        'from "%s"', k, data[k].shape, filename)
            data.close()
    else:
        with io.BytesIO() as cbuf:
            shutil.copyfileobj(sys.stdin.buffer, cbuf)
            cbuf.seek(0)
            try:
                data = np.load(cbuf)
            except OSError as err:
                logging.error('failed to load "/dev/stdin" due to %s', err)
                sys.exit(errno | ERRNO_READ)
            if not hasattr(data, 'keys'):
                logging.error('failed to load "/dev/stdin" as npz file')
                sys.exit(errno | ERRNO_READ)
            if keys is None:
                keys = list(data.keys())
            for k in keys:
                try:
                    arr = data[k]
                except KeyError as err:
                    logging.error('failed to load "/dev/stdin" due to %s', err)
                    sys.exit(errno | ERRNO_DATA)
                try:
                    all_data[k].append(arr)
                except KeyError:
                    all_data[k] = []
                    all_data[k].append(data[k])
                    logging.debug(
                        'loaded data of key "%s" of shape %s '
                        'from "/dev/stdin"', k, data[k].shape)
            data.close()
    return all_data


def merge_data(args, all_data):
    assert len(set(map(len, all_data.values()))) == 1, all_data
    result = collections.OrderedDict()
    if len(all_data[next(iter(all_data))]) > 1:
        merge = np.stack if args.stack else np.concatenate
        try:
            for k in all_data:
                result[k] = merge(all_data[k], axis=args.dim)
        except ValueError as err:
            logging.error('failed to %s arrays due to %s',
                          'stack' if args.stack else 'concatenate', err)
            sys.exit(errno | ERRNO_DATA)
    else:
        for k in all_data:
            result[k] = all_data[k][0]
    logging.debug('result shape = %s', {k: result[k].shape for k in result})
    return result


def write_data(args, result):
    if args.output:
        if args.textwrite:
            if args.csv:
                csv_rows = None
                for k in result:
                    if not result[k].shape:
                        result[k] = np.array([result[k]])
                    elif len(result[k].shape) > 1:
                        logging.warning(
                            'array of key "%s" is more '
                            'than 1D, trying squeezing '
                            'it to 1D', k)
                        result[k] = np.squeeze(result[k])
                        if len(result[k].shape) > 1:
                            logging.error(
                                'array of key "%s" is more '
                                'than 1D and thus cannot '
                                'fit into a CSV column; '
                                'aborted', k)
                            sys.exit(errno | ERRNO_WRITE)
                    if not csv_rows:
                        csv_rows = len(result[k])
                    elif csv_rows != len(result[k]):
                        logging.error(
                            'array of key "%s" is '
                            'greater in length than '
                            'previous key, and thus '
                            'cannot fit into a CSV '
                            'table; aborted', k)
                        sys.exit(errno | ERRNO_WRITE)
                if csv_rows == 0:
                    try:
                        with open(args.output, 'w') as outfile:
                            print(*result.keys(), sep=',', file=outfile)
                    except OSError as err:
                        logging.error(
                            'failed to write result to "%s" due '
                            'to %s', args.output, err)
                        sys.exit(errno | ERRNO_WRITE)
                    logging.info('written result to "%s"', args.output)
                else:
                    try:
                        with open(args.output, 'w') as outfile:
                            print(*result.keys(), sep=',', file=outfile)
                            np.savetxt(
                                outfile,
                                np.stack(list(result.values()), axis=1),
                                delimiter=',')
                    except OSError as err:
                        logging.error(
                            'failed to write result to "%s" due '
                            'to %s', args.output, err)
                        sys.exit(errno | ERRNO_WRITE)
                    logging.info('written result to "%s"', args.output)
            else:
                try:
                    with open(args.output, 'w') as outfile:
                        for i, k in enumerate(result):
                            if i:
                                print(file=outfile)
                            print('==>', k, '<==', file=outfile)
                            try:
                                np.savetxt(outfile, result[k])
                            except ValueError as err:
                                logging.error(
                                    'failed to write result of key '
                                    '"%s" to "%s" due to %s', k, args.output,
                                    err)
                                sys.exit(errno | ERRNO_WRITE)
                except OSError as err:
                    logging.error(
                        'failed to write result of key "%s" to "%s"'
                        'due to %s', k, args.output, err)
                    sys.exit(errno | ERRNO_WRITE)
                logging.info('written result to "%s"', args.output)
        else:
            try:
                with open(args.output, 'wb') as outfile:
                    np.savez(outfile, **result)
            except OSError as err:
                logging.error('failed to write result to "%s" due to %s',
                              args.output, err)
                sys.exit(errno | ERRNO_WRITE)
            logging.info('written result to "%s"', args.output)
    else:
        if args.textwrite:
            if args.csv:
                csv_rows = None
                for k in result:
                    if not result[k].shape:
                        result[k] = np.array([result[k]])
                    elif len(result[k].shape) > 1:
                        logging.warning(
                            'array of key "%s" is more '
                            'than 1D, trying squeezing '
                            'it to 1D', k)
                        result[k] = np.squeeze(result[k])
                        if len(result[k].shape) > 1:
                            logging.error(
                                'array of key "%s" is more '
                                'than 1D and thus cannot '
                                'fit into a CSV column; '
                                'aborted', k)
                            sys.exit(errno | ERRNO_WRITE)
                    if not csv_rows:
                        csv_rows = len(result[k])
                    elif csv_rows != len(result[k]):
                        logging.error(
                            'array of key "%s" is '
                            'greater in length than '
                            'previous key, and thus '
                            'cannot fit into a CSV '
                            'table; aborted', k)
                        sys.exit(errno | ERRNO_WRITE)
                if csv_rows == 0:
                    print(*result.keys(), sep=',')
                    logging.info('written result to "/dev/stdout"')
                else:
                    with io.StringIO() as cbuf:
                        print(*result.keys(), sep=',', file=cbuf)
                        np.savetxt(
                            cbuf,
                            np.stack(list(result.values()), axis=1),
                            delimiter=',')
                        cbuf.seek(0)
                        shutil.copyfileobj(cbuf, sys.stdout)
                    logging.info('written result to "/dev/stdout"')
            else:
                with io.StringIO() as cbuf:
                    for i, k in enumerate(result):
                        if i:
                            print(file=cbuf)
                        print('==>', k, '<==', file=cbuf)
                        try:
                            np.savetxt(cbuf, result[k])
                        except ValueError as err:
                            logging.error(
                                'failed to write result of key "%s" to '
                                '"/dev/stdout" due to %s', k, err)
                            sys.exit(errno | ERRNO_WRITE)
                    cbuf.seek(0)
                    shutil.copyfileobj(cbuf, sys.stdout)
                    logging.info('written result to "/dev/stdout"')
        else:
            with io.BytesIO() as cbuf:
                np.savez(cbuf, **result)
                cbuf.seek(0)
                shutil.copyfileobj(cbuf, sys.stdout.buffer)
            logging.info('written result to "/dev/stdout"')


def main():
    logging.basicConfig(
        format='%(filename)s: %(levelname)s: %(message)s', level=LOGGING_LEVEL)
    args = make_parser().parse_args()
    filenames = decide_input_files(args)
    all_data = read_data(filenames, args.keys)
    if not all_data:
        logging.debug('loaded nothing; aborted')
        return
    result = merge_data(args, all_data)
    write_data(args, result)


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
