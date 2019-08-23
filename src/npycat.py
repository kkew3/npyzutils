#!/usr/bin/env python3
import sys
import io
import shutil
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
        prog='npycat',
        description='Concatenate or stack several npy files to one npy file.')
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
        '-O',
        '--output',
        metavar='OUTFILE',
        help=('the result will be written to OUTFILE. If '
              'not specified, the raw bytes of the result '
              'array (or text if `-H\' is given) will be '
              'written to stdout'))
    parser.add_argument(
        '-H',
        '--human-readable',
        dest='textwrite',
        action='store_true',
        help=('write to OUTFILE in text mode. Note that '
              'error occurs if the underlying array is more '
              'than 2D'))
    parser.add_argument(
        '-T',
        '--from-file',
        dest='from_file',
        metavar='FILE',
        help=('read filenames to concatenate/stack from FILE; use `-\' '
              'to denote stdin. In either case the filenames '
              'should be placed one per line'))
    parser.add_argument(
        'npyfiles',
        nargs='*',
        metavar='NPYFILE',
        help=('the npy files to concatenate/stack. '
              'If none is given here and if `-T\' is provided, then '
              'the NPYFILEs will be obtained from FILE. '
              'If neither NPYFILE nor `-T\' is provided, then '
              'raw bytes of an npy file will be expected from stdin. '
              'If both NPYFILE and `-T\' are provided, then '
              'the union of them will be used.'))
    return parser


def decide_input_files(args):
    global errno
    filenames = []
    if args.from_file == '-':
        filenames.extend(x.rstrip('\n') for x in sys.stdin)
        if not filenames and not args.npyfiles:
            logging.info('nothing to load; aborted')
            sys.exit(errno)
    elif args.from_file:
        try:
            with open(args.from_file) as infile:
                filenames.extend(x.rstrip('\n') for x in infile)
        except OSError as err:
            logging.warning('failed to load NPYFILEs from "%s" due to %s',
                            args.from_file, err)
            errno |= ERRNO_READ
        if not filenames and not args.npyfiles:
            logging.info('nothing to load; aborted')
            sys.exit(errno)
    if args.npyfiles:
        filenames.extend(args.npyfiles)
    return filenames or None


def read_data(filenames):
    all_data = []
    if filenames:
        for filename in filenames:
            try:
                data = np.load(filename)
            except OSError as err:
                logging.error('failed to load "%s" due to %s', filename, err)
                sys.exit(errno | ERRNO_READ)
            if hasattr(data, 'keys'):
                data.close()
                logging.error('failed to load "%s" as npy file', filename)
                sys.exit(errno | ERRNO_READ)
            logging.debug('loaded data of shape %s from "%s"', data.shape,
                          filename)
            all_data.append(data)
    else:
        with io.BytesIO() as cbuf:
            shutil.copyfileobj(sys.stdin.buffer, cbuf)
            cbuf.seek(0)
            try:
                data = np.load(cbuf)
            except OSError as err:
                logging.error('failed to load from "/dev/stdin" due to %s',
                              err)
                sys.exit(errno | ERRNO_READ)
            if hasattr(data, 'keys'):
                data.close()
                logging.error('failed to load "/dev/stdin" as npy file')
                sys.exit(errno | ERRNO_READ)
            logging.debug('loaded data of shape %s from "/dev/stdin"',
                          data.shape)
            all_data.append(data)
    return all_data


def merge_data(args, all_data):
    if len(all_data) > 1:
        merge = np.stack if args.stack else np.concatenate
        try:
            result = merge(all_data, axis=args.dim)
        except ValueError as err:
            logging.error('failed to %s arrays due to %s',
                          'stack' if args.stack else 'concatenate', err)
            sys.exit(errno | ERRNO_DATA)
    else:
        result = all_data[0]
    logging.debug('result shape = %s', result.shape)
    return result


def write_data(args, result):
    if args.output:
        if args.textwrite:
            try:
                with open(args.output, 'w') as outfile:
                    np.savetxt(outfile, result)
            except (OSError, ValueError) as err:
                logging.error('failed to write result to "%s" due to %s',
                              args.output, err)
                sys.exit(errno | ERRNO_WRITE)
            logging.info('written result to "%s"', args.output)
        else:
            try:
                with open(args.output, 'wb') as outfile:
                    np.save(outfile, result)
            except OSError as err:
                logging.error('failed to write result to "%s" due to %s',
                              args.output, err)
                sys.exit(errno | ERRNO_WRITE)
            logging.info('written result to "%s"', args.output)
    else:
        if args.textwrite:
            with io.StringIO() as cbuf:
                try:
                    np.savetxt(cbuf, result)
                except (OSError, ValueError) as err:
                    logging.error(
                        'failed to write result to "/dev/stdout" '
                        'due to %s', err)
                    sys.exit(errno | ERRNO_WRITE)
                cbuf.seek(0)
                shutil.copyfileobj(cbuf, sys.stdout)
                logging.info('written result to "/dev/stdout"')
        else:
            with io.BytesIO() as cbuf:
                np.save(cbuf, result)
                cbuf.seek(0)
                shutil.copyfileobj(cbuf, sys.stdout.buffer)
            logging.info('written result to "/dev/stdout"')


def main():
    logging.basicConfig(
        format='%(filename)s: %(levelname)s: %(message)s', level=LOGGING_LEVEL)
    args = make_parser().parse_args()
    filenames = decide_input_files(args)
    logging.debug('input filenames = %s', filenames or '/dev/stdin')
    all_data = read_data(filenames)
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
