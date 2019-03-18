npyzutils
=========

A collection of command line utilities to manipulate `npy` or `npz` files.

- `npyzshape`: tell the shape of array(s) stored in `npy` file or `npz` file
- `npycat`: concatenate or stack multiple `npy` files to one `npy` file

Will add more as needed

Build and installation
----------------------

```bash
python3 -m virtualenv rt
. rt/bin/activate
pip install -r requirements-dev.txt

make
# install to /usr/local/bin
make install
# or install to a custom directory instead, say "$HOME/bin"
#make install PREFIX="$HOME/bin"
```
