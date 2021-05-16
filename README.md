# iterable-subprocess [![CircleCI](https://circleci.com/gh/uktrade/iterable-subprocess.svg?style=shield)](https://circleci.com/gh/uktrade/iterable-subprocess) [![Test Coverage](https://api.codeclimate.com/v1/badges/048c4f322de3361468af/test_coverage)](https://codeclimate.com/github/uktrade/iterable-subprocess/test_coverage)

Python utility function to communicate with a subprocess using iterables: for when data is too big to fit in memory and has to be streamed.

Data is sent to a subprocess's standard input via an iterable, and extracted from its standard output via another iterable. This allows an external subprocess to be naturally placed in a chain of iterables for streaming processing.


## Installation

```bash
pip install iterable-subprocess
```


## Usage

A single function `iterable_subprocess` is exposed. The first parameter is the `args` argument passed to the [Popen Constructor](https://docs.python.org/3/library/subprocess.html#popen-constructor), and the second is an iterable whose items must be `bytes` instances and are sent to the subprocess's standard input.

Returned from the function is an iterable whose items are `bytes` instances of the process's standard output.

```python
from iterable_subprocess import iterable_subprocess

def yield_input():
    # In a real case could read from the filesystem or the network
    yield b'first\n'
    yield b'second\n'
    yield b'third\n'

output = iterable_subprocess(['cat'], yield_input())

for chunk in output:
    print(chunk)
```
