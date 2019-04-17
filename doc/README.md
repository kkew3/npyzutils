# npycat
```
usage: npycat [-h] [-s] [-d DIM] [-o TOFILE] [-t {always,auto,never}] [-S]
              [npyfiles [npyfiles ...]]

Concatenate or stack several npy files to one npy file.

Return code:

    0    success
    1    argument parsing error
    2    failed to load one or more npy files
    4    arrays have inconsistent dimension
    8    failed to write result to file

positional arguments:
  npyfiles              npyfiles to concatenate; if not provided anything, a
                        list of npy filenames will be expected at stdin, one
                        per line

optional arguments:
  -h, --help            show this help message and exit
  -s, --stack           stack arrays rather than concatenate them
  -d DIM, --dim DIM     the dimension to concatenate/stack, default to 0
  -o TOFILE, --tofile TOFILE
                        the npy file to write; if not specified, the binary
                        result will be written to stdout, which is generally
                        not recommended
  -t {always,auto,never}, --textwrite {always,auto,never}
                        when "auto", write in text mode only if the output
                        device is stdout, default to auto
  -S, --strict          fail immediately if a numpy file cannot be loaded
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

# npyzshape
```
usage: npyzshape [-h] [-d DELIM] [-H] [-c FIELD_SPEC]
                 [NPYZFILE [NPYZFILE ...]]

Display array metainfo like shape in numpy npy/npz files. Reading array from
stdin is not supported unless `--reading-header' option is used.

FIELDS_SPEC format

    A sequence of unique single-character field specifier.
    List of field specifiers:

        f      npy/npz filename
        k, K   npz key; if the underlying file is an npy file, empty string is
               displayed if using `k', otherwise "<na>"
        s, S   comma-separated list of shape; if the underlying data is a
               scalar, empty string is displayed if using `s', otherwie
               "<scalar>"
        t      the array dtype

positional arguments:
  NPYZFILE              the npy/npz file(s) to inspect shapes

optional arguments:
  -h, --help            show this help message and exit
  -d DELIM, --field-delimiter DELIM
                        DELIM with `\t', `\0' supported; `\n', `\r' are not
                        allowd. Default to colon
  -H, --reading-header  decide the metainfo by reading the header; despite
                        much faster and memory-saving, please note that this
                        function may break in the future as it uses potentiall
                        unstable API of numpy (accessing protected attributes)
  -c FIELD_SPEC, --fields-spec FIELD_SPEC
                        fields specification string; default to `kS'
```

# npyzz
```
usage: npyzz [-h] [-B] [-o TOFILE] [--overwrite {always,ask,skip,abort}] [-S]
             [FILE [FILE ...]]

Zip and compress npy or npz file(s). If the input is FILENAME.npy, the default
output will be FILENAME.npz with FILENAME.npy as a zip file entry within
FILENAME.npz. If the input is FILENAME.npz, the default output will be written
in-place such that the content is compressed if not already compressed. If the
input consists of multiple npy files, e.g. F1.npy, F2.npy, the output filename
must be specified, e.g. as OUT.npz, which will contain F1.npy and F2.npy as
zip file entries.

positional arguments:
  FILE                  npy/npz files to compress; if nothing is specified, a
                        list of npy/npz filenames will be expected at stdin,
                        one per line

optional arguments:
  -h, --help            show this help message and exit
  -B, --bundle-npy      bundle several npy files together into TOFILE; if not
                        in strict mode, all non-npy FILEs (e.g. npz files)
                        will be omitted, otherwise, error raised
  -o TOFILE, --tofile TOFILE
                        the npz file to write. TOFILE should ends with `.npz'.
                        If `--bundle-npy' is specified, this option is
                        mandatory. If more than one FILE is specified, this
                        option is omitted (so default TOFILE as mentioned in
                        Description will be adopted).
  --overwrite {always,ask,skip,abort}
                        overwriting policy when TOFILE is an existing file. If
                        `always', always overwrite. If `ask', interactively
                        prompt user what to do (skip/abort/rename current
                        TOFILE). If `skip', skip current TOFILE. If `abort',
                        abort the program
  -S, --strict          option to enable strict mode. When in strict mode, if
                        one of FILE cannot be loaded, or if one of TOFILE
                        cannot be written, or if there exists duplicate zip
                        file entry, the program will be aborted. See also
                        `--bundle-npy'
```

# npzcat
```
usage: npzcat [-h] [-s] [-d DIM] [-o TOFILE] [-S] [-k KEYS [KEYS ...]] [-n]
              [NPZFILE [NPZFILE ...]]

Concatenate or stack several npz files to one npz file. Use `--' to mark the
beginning of NPZFILEs if necessary.

positional arguments:
  NPZFILE               npzfiles to concatenate; if not provided anything, a
                        list of npz filenames will be expected at stdin, one
                        per line

optional arguments:
  -h, --help            show this help message and exit
  -s, --stack           stack arrays rather than concatenate them
  -d DIM, --dim DIM     the dimension to concatenate/stack, default to 0
  -o TOFILE, --tofile TOFILE
                        the npz file to write; if not specified, the binary
                        result will be written to stdout, which is generally
                        not recommended
  -S, --strict          fail immediately if a numpy file cannot be loaded
  -k KEYS [KEYS ...], --keys KEYS [KEYS ...]
                        npz field keys to use; if not specified, all field
                        keys of the first npz file provided will be used
  -n, --print-name      if specified, print the output filename in the end.
                        This option will only be considered if option `-o' has
                        been specified
```

