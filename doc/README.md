# flo2npy
```
usage: flo2npy [-h] [-O OUTFILE] FLOFILE

Convert .flo optical flow file to numpy npy format.

positional arguments:
  FLOFILE               the .flo file to convert

optional arguments:
  -h, --help            show this help message and exit
  -O OUTFILE, --output OUTFILE
                        write to OUTFILE rather than FLOWFILE.npy; or `-' to
                        write raw bytes of the result npy to stdout

Adapted from https://github.com/Johswald/flow-code-python/blob/master/readFlowFile.py
```

# npycat
```
usage: npycat [-h] [-s] [-d DIM] [-O OUTFILE] [-H] [-T FILE]
              [NPYFILE [NPYFILE ...]]

Concatenate or stack several npy files to one npy file.

positional arguments:
  NPYFILE               the npy files to concatenate/stack. If none is given
                        here and if `-T' is provided, then the NPYFILEs will
                        be obtained from FILE. If neither NPYFILE nor `-T' is
                        provided, then raw bytes of an npy file will be
                        expected from stdin. If both NPYFILE and `-T' are
                        provided, then the union of them will be used.

optional arguments:
  -h, --help            show this help message and exit
  -s, --stack           stack arrays rather than concatenate them
  -d DIM, --dim DIM     the dimension to concatenate/stack, default to 0
  -O OUTFILE, --output OUTFILE
                        the result will be written to OUTFILE. If not
                        specified, the raw bytes of the result array (or text
                        if `-H' is given) will be written to stdout
  -H, --human-readable  write to OUTFILE in text mode. Note that error occurs
                        if the underlying array is more than 2D
  -T FILE, --from-file FILE
                        read filenames to concatenate/stack from FILE; use `-'
                        to denote stdin. In either case the filenames should
                        be placed one per line
```

# npyz2img
```
usage: npyz2img [-h] [-T DTYPE] [-f] [-l VMIN] [-u VMAX] [-C CHANNELS]
                [-K KEY] [-I SLICE_EXPR] [-A CMAP] [-o [TOFILE]] [-d TODIR]
                [-P OUT_TEMPLATE] [-F OUTPUT_FORMAT] [--overwrite]
                NPYZFILE

Make image(s) from npy/npz file. Use `--' to mark the beginning of NPYZFILEs
if necessary.

positional arguments:
  NPYZFILE              the npy/npz file from which to render image(s)

optional arguments:
  -h, --help            show this help message and exit

data type options:
  -T DTYPE, --dtype DTYPE
                        enforce an expected data type of the image data.
                        Default to uint8
  -f, --force           render image even if the underlying data is not
                        normalized

clipping options:
  clip the image data before checking normalization; default to no clipping.
  The lower/upper bound will be casted to the data type as specified by
  `--dtype'

  -l VMIN, --vmin VMIN  the lower bound of clipping
  -u VMAX, --vmax VMAX  the upper bound of clipping

indexing options:
  -C CHANNELS, --channels CHANNELS
                        the channel order, should be a string comprised of
                        {`N', `C', `H', `W'}. The length of the string must be
                        identical to the extracted sub-tensor from NPYZFILE.
                        `N' denotes any number of images; `C' denotes any
                        color channel; `H' denotes the height and `W' the
                        width. `H' and `W' must occur one and only once; `C'
                        must not occur more than once; `N' may occur any
                        times. For example, `NHWC' means the extracted tensor
                        is of shape `(N,H,W,C)', and `NNHW' means the
                        extracted tensor is of shape `(N1,N2,H,W)'. Default to
                        `HWC'
  -K KEY, --key KEY     the npz data key; for simplicity, only one key can be
                        specified each time. This option will be omitted if
                        NPYZFILE is an npy file, and will be mandatory if
                        NPYZFILE is an npz file containing more than one key
  -I SLICE_EXPR, --index SLICE_EXPR
                        the indexing expression if it's not intended to use
                        the entire data file as source of images. For example,
                        `:,1:,... Default to `:'

rendering options:
  -A CMAP, --cmap CMAP  cmap to use if underlying images are grayscale.
                        Default to gray

output options:
  -o [TOFILE], --tofile [TOFILE]
                        write to TOFILE; if there are multiple images to
                        render, the behavior will be up to the presence of
                        option `--overwrite'. If TOFILE is left empty, TOFILE
                        will be set to stdout, and only the first image will
                        be sent to stdout
  -d TODIR, --todir TODIR
                        write to files under existing TODIR; the files will be
                        written as per OUT_TEMPLATE. Default to current
                        working directory
  -P OUT_TEMPLATE, --out-template OUT_TEMPLATE
                        the `str.format` template string used to form the
                        output file. This option will be omitted if TOFILE has
                        been specified. The template string is expected to
                        contain at most L positional placeholders where L is
                        the number of `N' in CHANNELS, where the ith
                        placeholder will be replaced by the integer index of
                        the ith axis specified by CHANNELS; it may also
                        contain one keyword placeholder named `key', if
                        NPYZFILE is an npz file, where the placeholder will be
                        replaced by KEY. Default to `img-{}_..._{}.png' where
                        there are L positional placeholders if NPYZFILE is an
                        npy file, and to `img-{key}_{}_..._{}.png' otherwise.
  -F OUTPUT_FORMAT, --output-format OUTPUT_FORMAT
                        the image format to write; if specified, this option
                        overwrites the output format implied by OUT_TEMPLATE
  --overwrite           if not specified, abort whenever an existing file
                        exists; otherwise overwrite existing files
```

# npyzindex
```
usage: npyzindex [-h] [-e INDEX/KEYEDINDEX] [-T FILE] [-O [.SUFFIX/-]]
                 [NPYZFILE [NPYZFILE ...]]

Index subarray from npy/npz files.

positional arguments:
  NPYZFILE              the npy/npz files to index using the set of
                        [KEY/]INDEX expression. A series of both npy and npz
                        files may lead to KeyError (see help for `-e' option.
                        If none is given, and if `-T' is provided, then the
                        NPYZFILEs will be obtained from FILE. If neither
                        NPYZFILE nor `-T' is provided, then raw bytes of an
                        npy/npz file will be expected from stdin. If both
                        NPYZFILE and `-T' are provided, then the union of them
                        will be used

optional arguments:
  -h, --help            show this help message and exit
  -e INDEX/KEYEDINDEX, --index-expr INDEX/KEYEDINDEX
                        numpy style ndarray index to sample from underlying
                        array. The index may either be INDEX, or
                        KEY<slash>INDEX, where the latter form is to sample
                        from KEY in npz. For example, `-e2' picks the third
                        element from data, and `-etrain/2' picks the third
                        element from the array named `train'. If the
                        underlying file is an npy file, using the keyed form
                        leads to KeyError; if the underlying is an npz file,
                        using the key-free form applies the indexing to all
                        keys simultaneously. Multiple `-e' options can be
                        appended to form a sequence of sampling. For example,
                        `-e2 -e:,3' picks the third row and then the fourth
                        column of the array, which is equivalent to `-e2,3'
  -T FILE, --from-file FILE
                        read filenames to index from FILE; use `-' to denote
                        stdin. In either case the filenames should be placed
                        one per line
  -O [.SUFFIX/-], --output [.SUFFIX/-]
                        controls how the output is saved. If using the form
                        .SUFFIX, the indexed array will be saved as
                        `NPYZFILE.SUFFIX'. If specified as `-O-', the output
                        bytes will be written to stdout, or raise error if
                        there's more than one NPYZFILE. If specified as `-O',
                        the change will be made in-place. If not specified as
                        `-O-' but input is from stdin, it will be treated as
                        if `-O-' were specified. Default to `.out'
```

# npyzshape
```
usage: npyzshape [-h] [NPYZFILE [NPYZFILE ...]]

Inspect array shapes of npy or npz files. The output will be of format
`<filename>\t<key/empty-if-npy>\t<shape>/"<scalar>"\n' for each line. If the
input is from stdin, `<filename>\t' will be omitted in output lines.

positional arguments:
  NPYZFILE    the npy/npz files to inspect shapes, or leave empty to read from
              stdin raw bytes of an npy or npz file. Note that reading from
              stdin requires loading the entire file into memory, since stdin
              is not seekable, whereas reading from regular files need not

optional arguments:
  -h, --help  show this help message and exit
```

# npzcat
```
usage: npzcat [-h] [-s] [-d DIM] [-K KEYS [KEYS ...]] [-O OUTFILE] [-H]
              [--csv] [-T FILE]
              [NPZFILE [NPZFILE ...]]

Concatenate or stack several npz files to one npz file.

positional arguments:
  NPZFILE               the npz files to concatenate/stack. If none is given
                        here and if `-T' is provided, then the NPZFILEs will
                        be obtained from FILE. If neither NPZFILE nor `-T' is
                        provided, then raw bytes of an npz file will be
                        expected from stdin. If both NPZFILE and `-T' are
                        provided, then the union of them will be used.

optional arguments:
  -h, --help            show this help message and exit
  -s, --stack           stack arrays rather than concatenate them
  -d DIM, --dim DIM     the dimension to concatenate/stack, default to 0
  -K KEYS [KEYS ...], --keys KEYS [KEYS ...]
                        npz field keys to use; if not specified, all field
                        keys of the first npz file provided will be used
  -O OUTFILE, --output OUTFILE
                        the result will be written to OUTFILE. If not
                        specified, the raw bytes (or text if `-H' is given)
                        will be written to stdout
  -H, --human-readable  write to OUTFILE in text mode. Note that error occurs
                        if any underlying array is more then 2D
  --csv                 arrange the output in CSV with field names equal to
                        the key names; effective only if `-H' is specified
  -T FILE, --from-file FILE
                        read filenames to concatenate/stack from FILE; use `-'
                        to denote stdin. In either case the filenames should
                        be placed one per line
```

