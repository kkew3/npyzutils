#!/usr/bin/env python3
import argparse
import sys
import os
import re
import io
import shutil
import itertools
import typing
import logging

import numpy as np
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt

ERROR_ARGS = 1
ERROR_READ = 2
ERROR_DATA = 4

SliceExpr = typing.Tuple[typing.Union[
                             slice,
                             typing.Tuple[int, ...],
                             type(...)], ...]
NpyzData = typing.Union[np.ndarray, typing.Dict[str, np.ndarray]]


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        args = {'prog': self.prog, 'message': message}
        self.exit(ERROR_ARGS, '%(prog)s: error: %(message)s\n' % args)


def slice_expr(string: str) -> SliceExpr:
    string = re.sub(r'\s', '', string)
    tokens = string.split(',')
    sl = []
    for tok in tokens:
        if tok == '...':
            if Ellipsis in sl:
                raise argparse.ArgumentTypeError(
                    'Ellipsis may occur at most once')
            sl.append(Ellipsis)
        else:
            comps = tok.split(':')
            comps = [(int(x) if x else None) for x in comps]
            if len(comps) in (2, 3):
                sl.append(slice(*comps))
            elif len(comps) == 1:
                sl.append(comps[0])
            else:
                raise argparse.ArgumentTypeError
    return tuple(sl)


def channel_order(string: str) -> str:
    string = re.sub(r'\s', '', string)
    if 'H' not in string or 'W' not in string:
        raise argparse.ArgumentTypeError('H&W must occur once')
    if re.match(r'.*([CHW]).*\1', string):
        raise argparse.ArgumentTypeError('C&H&W must not occur more than once')
    return string


stdout = object()


def make_parser():
    parser = ArgumentParser(
        prog='npyz2img',
        description='Make image(s) from npy/npz file. Use `--\' to mark the '
                    'beginning of NPYZFILEs if necessary.')
    parser.add_argument('npyzfile', metavar='NPYZFILE', type=os.path.normpath,
                        help='the npy/npz file from which to render image(s)')
    dtypeopts = parser.add_argument_group('data type options')
    dtypeopts.add_argument('-T', '--dtype', default='uint8',
                           help='enforce an expected data type of the '
                                'image data. Default to %(default)s')
    dtypeopts.add_argument('-f', '--force', action='store_true',
                           help='render image even if the underlying data is '
                                'not normalized')
    clipopts = parser.add_argument_group('clipping options',
                                         'clip the image data before checking'
                                         ' normalization; default to no '
                                         'clipping. The lower/upper bound '
                                         'will be casted to the data type '
                                         'as specified by `--dtype\'')
    clipopts.add_argument('-l', '--vmin', type=float,
                          help='the lower bound of clipping')
    clipopts.add_argument('-u', '--vmax', type=float,
                          help='the upper bound of clipping')
    indopts = parser.add_argument_group('indexing options')
    indopts.add_argument('-C', '--channels', default='HWC', type=channel_order,
                         help='the channel order, should be a string '
                              'comprised of {`N\', `C\', `H\', `W\'}. The '
                              'length of the string must be identical to the '
                              'extracted sub-tensor from NPYZFILE. `N\' '
                              'denotes any number of images; `C\' denotes any '
                              'color channel; `H\' denotes the height and '
                              '`W\' the width. `H\' and `W\' must occur one '
                              'and only once; `C\' must not occur more '
                              'than once; `N\' may occur any times. '
                              'For example, `NHWC\' means the '
                              'extracted tensor is of shape `(N,H,W,C)\', and '
                              '`NNHW\' means the extracted tensor is of shape '
                              '`(N1,N2,H,W)\'. Default to `%(default)s\'')
    indopts.add_argument('-K', '--key',
                         help='the npz data key; for simplicity, only one key'
                              ' can be specified each time. This option will '
                              'be omitted if NPYZFILE is an npy file, and '
                              'will be mandatory if NPYZFILE is an npz file '
                              'containing more than one key')
    indopts.add_argument('-I', '--index', metavar='SLICE_EXPR',
                         type=slice_expr, default=':',
                         help='the indexing expression if it\'s not intended '
                              'to use the entire data file as source of '
                              'images. For example, `:,1:,... Default to '
                              '`:\'')
    rdropts = parser.add_argument_group('rendering options')
    rdropts.add_argument('-A', '--cmap', default='gray',
                         help='cmap to use if underlying images are '
                              'grayscale. Default to %(default)s')
    outopts = parser.add_argument_group('output options')
    outopts.add_argument('-o', '--tofile', type=os.path.normpath, nargs='?',
                         const=stdout,
                         help='write to TOFILE; if there are multiple images '
                              'to render, the behavior will be up to the '
                              'presence of option `--overwrite\'. If TOFILE '
                              'is left empty, TOFILE will be set to stdout, '
                              'and only the first image will be sent to '
                              'stdout')
    outopts.add_argument('-d', '--todir', type=os.path.normpath,
                         default=os.getcwd(),
                         help='write to files under existing TODIR; the files'
                              ' will be written as per OUT_TEMPLATE. Default '
                              'to current working directory')
    outopts.add_argument('-P', '--out-template',
                         help='the `str.format` template string used to form '
                              'the output file. This option will be omitted '
                              'if TOFILE has been specified. The template '
                              'string is expected to contain at most L '
                              'positional placeholders where L is the number '
                              'of `N\' in CHANNELS, where the ith placeholder '
                              'will be replaced by the integer index of the '
                              'ith axis specified by CHANNELS; it may also '
                              'contain one keyword placeholder named `key\', '
                              ' if NPYZFILE is an npz file, where the '
                              'placeholder will be replaced by KEY. Default '
                              'to `img-{}_..._{}.png\' where there are L '
                              'positional placeholders if NPYZFILE is an '
                              'npy file, and to `img-{key}_{}_..._{}.png\' '
                              'otherwise.')
    outopts.add_argument('-F', '--output-format',
                         help='the image format to write; if specified, this '
                              'option overwrites the output format implied by '
                              'OUT_TEMPLATE')
    outopts.add_argument('--overwrite', action='store_true',
                         help='if not specified, abort whenever an existing '
                              'file exists; otherwise overwrite existing '
                              'files')
    return parser


class NilKeyError(Exception):
    pass


class ShapeMismatchError(Exception):
    pass


class UnexpectedDTypeError(Exception):
    pass


class NotNormalizedError(Exception):
    pass


class InvalidOutputTemplate(Exception):
    pass


def loaddata(filename: str, key: typing.Optional[str]) \
        -> typing.Tuple[NpyzData, bool]:
    """
    Load data and determine its file type.
    :param filename: the npyzfile name
    :param key: the key to use if ``filename`` is an npz file
    :return: (data, ``True`` if ``filename`` is an npy file)
    :raise KeyError: if ``filename`` is an npz file and ``key`` is not found
    """
    zdata = np.load(filename)
    try:
        zkeys = list(zdata.keys())
    except AttributeError:
        data = zdata
        is_npy = True
    else:
        if key is None:
            n_keys = len(zkeys)
            if n_keys > 1:
                raise NilKeyError
            if n_keys == 0:
                raise KeyError
            data = zdata[zkeys[0]]
        else:
            data = zdata[key]
        is_npy = False
    return data, is_npy


def check_shape(subdata: np.ndarray, channels: str) \
        -> typing.Tuple[np.ndarray, bool]:
    """
    Check shape and return canonical shape.

    :param subdata: the sub-tensor
    :param channels: the channel expression
    :return: sub-tensor in canonical shape, and whether the last axis is 'C'
    """
    if len(subdata.shape) != len(channels):
        raise ShapeMismatchError
    # rearrange to (..., H, W[, C])
    hloc = channels.index('H')
    wloc = channels.index('W')
    nlocs = list(range(len(channels)))
    nlocs.remove(hloc)
    nlocs.remove(wloc)
    try:
        cloc = channels.index('C')
    except ValueError:
        perm_to = nlocs + [hloc, wloc]
    else:
        nlocs.remove(cloc)
        perm_to = nlocs + [hloc, wloc, cloc]
    subdata = subdata.transpose(*perm_to)
    ends_with_c = ('C' in channels)
    if ends_with_c and subdata.shape[-1] == 1:
        subdata = subdata[..., 0]
        ends_with_c = False
    return subdata, ends_with_c


def clip_data(data: np.ndarray,
              expected_dtype: typing.Optional[np.dtype],
              vmin: typing.Optional[float],
              vmax: typing.Optional[float]) -> np.ndarray:
    if expected_dtype is not None:
        expected_dtype = np.dtype(expected_dtype)
        if expected_dtype != data.dtype:
            raise UnexpectedDTypeError
        ty = expected_dtype
    else:
        ty = data.dtype

    if vmin is not None:
        vmin = np.array(vmin).astype(ty).item()
    if vmax is not None:
        vmax = np.array(vmax).astype(ty).item()
    if vmin is not None or vmax is not None:
        data = data.clip(vmin, vmax)
    return data


def ensure_normalized(data: np.ndarray) -> None:
    if issubclass(data.dtype.type, np.integer):
        if (data < 0).any() or (data > 255).any():
            raise NotNormalizedError(np.integer)
    if issubclass(data.dtype.type, np.floating):
        if (data < 0.0).any() or (data > 1.0).any():
            raise NotNormalizedError(np.floating)


def render_images(data: np.ndarray, ends_with_c: bool) \
        -> typing.Iterator[typing.Tuple[typing.Tuple[int, ...], np.ndarray]]:
    ns = data.shape[:-(3 if ends_with_c else 2)]
    indices = itertools.product(*map(range, ns))
    if ns:
        for imgid in indices:
            yield imgid, data[imgid]
    else:
        yield (), data


def write_images(image_source, todir: str, output_format: typing.Optional[str],
                 cmap: str, ends_with_c: bool,
                 is_npy: bool, key: typing.Optional[str],
                 template: typing.Optional[str], overwrite: bool) -> None:
    naming_kwargs = {}
    if not is_npy:
        naming_kwargs['key'] = key

    render_kwargs = {}
    if output_format:
        render_kwargs['format'] = output_format
    if not ends_with_c and cmap:
        render_kwargs['cmap'] = cmap

    for imgid, img in image_source:
        try:
            name = template.format(*imgid, **naming_kwargs)
        except AttributeError:
            n_placeholders = len(imgid)
            tokens = ['img-', '_'.join(['{}'] * n_placeholders), '.png']
            if not is_npy:
                tokens.insert(1, '{key}_')
            template = ''.join(tokens)
            name = template.format(*imgid, **naming_kwargs)
        except (IndexError, KeyError):
            raise InvalidOutputTemplate
        filename = os.path.join(todir, name)
        if not overwrite and os.path.isfile(filename):
            raise FileExistsError(filename)
        if issubclass(img.dtype.type, np.integer):
            vmin, vmax = 0, 255
        else:
            vmin, vmax = 0.0, 1.0
        plt.imsave(filename, img, vmin=vmin, vmax=vmax, **render_kwargs)


def write_image(image_source, tofile: str, output_format: typing.Optional[str],
                cmap: str, ends_with_c: bool,
                overwrite: bool) -> None:
    render_kwargs = {}
    if output_format:
        render_kwargs['format'] = output_format
    if not ends_with_c and cmap:
        render_kwargs['cmap'] = cmap

    for _, img in image_source:
        if os.path.isfile(tofile):
            if not overwrite:
                raise FileExistsError(tofile)
            logging.warning('overwriting existing file "%s"', tofile)
        plt.imsave(tofile, img, **render_kwargs)


def write_image_stdout(image_source, output_format: typing.Optional[str],
                       cmap: str, ends_with_c: bool) -> None:
    render_kwargs = {'format': output_format or 'png'}
    if not ends_with_c and cmap:
        render_kwargs['cmap'] = cmap

    image_source = iter(image_source)
    try:
        _, img = next(image_source)
        with io.BytesIO() as cbuf:
            plt.imsave(cbuf, img, **render_kwargs)
            cbuf.seek(0)
            shutil.copyfileobj(cbuf, sys.stdout.buffer)
    except StopIteration:
        return

    try:
        _, img = next(image_source)
    except StopIteration:
        pass
    else:
        logging.warning('more than one image to write but can only write the '
                        'first one to stdout')


def main():
    logging.basicConfig(format='%(filename)s: %(levelname)s: %(message)s')
    args = make_parser().parse_args()

    try:
        data, is_npy = loaddata(args.npyzfile, args.key)
    except NilKeyError:
        logging.error('KEY not specified')
        return ERROR_ARGS
    except KeyError as err:
        logging.warning('KEY not found -- %s', str(err))
        return 0
    except OSError:
        logging.error('failed to load "%s"', args.npyzfile)
        return ERROR_READ

    try:
        subdata = data[args.index]
    except IndexError:
        logging.error('index "%s" invalid for data of shape %s',
                      args.index, str(data.shape))
        return ERROR_DATA

    try:
        subdata, ends_with_c = check_shape(subdata, args.channels)
    except ShapeMismatchError:
        logging.error('data of shape %s doesn\'t match CHANNELS "%s"',
                      str(subdata.shape), args.channels)
        return ERROR_DATA

    try:
        subdata = clip_data(subdata, args.dtype, args.vmin, args.vmax)
    except UnexpectedDTypeError:
        logging.error('expecting dtype %s but got %s',
                      args.dtype, str(subdata.dtype))
        return ERROR_DATA

    if not args.force:
        try:
            ensure_normalized(subdata)
        except NotNormalizedError as err:
            if err.args[0] == np.integer:
                logging.error('int image not within range [0,256)')
            else:
                logging.error('float image not within range [0.0,1.0]')
            return ERROR_DATA

    image_source = render_images(subdata, ends_with_c)
    if args.tofile is stdout:
        write_image_stdout(image_source, args.output_format, args.cmap,
                           ends_with_c)
    elif args.tofile is not None:
        try:
            write_image(image_source, args.tofile, args.output_format,
                        args.cmap, ends_with_c, args.overwrite)
        except FileExistsError as err:
            logging.warning('file "%s" already exists; aborted', err.args[0])
            return 0
    else:
        if not os.path.isdir(args.todir):
            logging.error('todir "%s" not found', args.todir)
            return ERROR_ARGS
        try:
            write_images(image_source, args.todir, args.output_format,
                         args.cmap, ends_with_c, is_npy, args.key or '',
                         args.out_template, args.overwrite)
        except FileExistsError as err:
            logging.warning('file "%s" already exists; aborted', err.args[0])
            return 0
        except InvalidOutputTemplate:
            logging.error('output template "%s" is invalid or imcompatible '
                          'with CHANNELS "%s"',
                          args.out_template,
                          args.channels)
            return ERROR_ARGS
        except TypeError as err:
            logging.error('TypeError: %s', err)
            return ERROR_DATA

    return 0


if __name__ == '__main__':
    sys.exit(main())
