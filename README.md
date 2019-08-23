npyzutils
=========

A collection of command line utilities to manipulate `npy` or `npz` files.

- `npyzshape`: tell the shape of array(s) stored in `npy` file or `npz` file
- `npycat`: concatenate or stack multiple `npy` files to one `npy` file
- `npzcat`: concatenate or stack multiple `npz` files to one `npz` file
- `npyz2img`: display data of `npy` file or `npz` file as image(s), supporting
              advanced indexing
- `npyzindex`: index sub-arrays from `npy` or `npz` file using advanced
               indexing notation
- `flo2npy`: convert `.flo` optical flow data file to `npy` file

Will add more as needed.

Installation
------------

```bash
python3 -m virtualenv rt
. rt/bin/activate
pip install -r requirements.txt
find src/ -type f | xargs ./make-launch-scripts
```

The launch scripts will be generated under `dist/`.

Currently there's no plan to distribute via `PyPI`, because I don't want to
spoil the global `pip` by `numpy` and friends.


Documentation
-------------

See `COMMAND --help`. May also refer to [HTML help page](doc/index.html),
which is merely a copy of the `--help` output.


Similar projects
----------------

- [nplook](https://github.com/gustavla/nplook.git): better handling of various
  data types, like `str`, `dict`, whereas its counterpart in this collection,
  the `npyzshape`, only support numpy arrays in `npy` files or numpy arrays as
  values in `npz` files.
