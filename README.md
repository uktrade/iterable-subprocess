# iterable-subprocess

[![PyPI package](https://img.shields.io/pypi/v/iterable-subprocess?label=PyPI%20package&color=%234c1)](https://pypi.org/project/iterable-subprocess/) [![Test suite](https://img.shields.io/github/actions/workflow/status/uktrade/iterable-subprocess/test.yml?label=Test%20suite)](https://github.com/uktrade/iterable-subprocess/actions/workflows/test.yml) [![Code coverage](https://img.shields.io/codecov/c/github/uktrade/iterable-subprocess?label=Code%20coverage)](https://app.codecov.io/gh/uktrade/iterable-subprocess)

Python context manager to communicate with a subprocess using iterables: for when data is too big to fit in memory and has to be streamed.

Data is sent to a subprocess's standard input via an iterable, and extracted from its standard output via another iterable. This allows an external subprocess to be naturally placed in a chain of iterables for streaming processing.


## Installation

```bash
pip install iterable-subprocess
```


## Usage

A single context manager `iterable_subprocess` is exposed. The first parameter is the `args` argument passed to the [Popen Constructor](https://docs.python.org/3/library/subprocess.html#popen-constructor), and the second is an iterable whose items must be `bytes` instances and are sent to the subprocess's standard input.

Returned from the function is an iterable whose items are `bytes` instances of the process's standard output.

```python
from iterable_subprocess import iterable_subprocess

# In a real case could be a generator function that reads from the filesystem or the network
iterable_of_bytes = (
    b'first\n',
    b'second\n'
    b'third\n'
)

with iterable_subprocess(['cat'], iterable_of_bytes) as output:
    for chunk in output:
        print(chunk)
```

If the process exits with a non-zero error code, a `SubprocessError` exception will be raised, with the contents of the processes's standard error as the message. Only the most recent 65536 bytes of the process's standard error are returned by default.


## Usage: unzip the first file of a ZIP archive while downloading

It's possible to download the bytes of a ZIP file in Python, and unzip by passing the bytes to `funzip`, as in the following example.

```python
import httpx
from iterable_subprocess import iterable_subprocess

with \
        httpx.stream('GET', 'https://www.example.com/my.zip') as r, \
        iterable_subprocess(['funzip'], r.iter_bytes()) as unzipped_chunks:

    for chunk in unzipped_chunks:
        print(chunk)
```

Note that it's also possible to stream unzip files without resorting to another process using [stream-unzip](https://github.com/uktrade/stream-unzip).
