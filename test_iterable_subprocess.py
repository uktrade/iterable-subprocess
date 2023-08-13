import functools
import io
import threading
import unittest
import zipfile

import pytest

from iterable_subprocess import iterable_subprocess


def test_cat_not_necessarily_streamed():
    output = b''.join(iterable_subprocess(['cat'], yield_small_input()))
    assert output == b'firstsecondthird'


def test_cat_streamed():
    latest_input = None

    def yield_input():
        nonlocal latest_input

        for i in range(0, 10000000):
            yield b'*' * 10
            latest_input = i

    output_chunks = iter(iterable_subprocess(['cat'], yield_input()))
    latest_input_during_output = [latest_input for _ in output_chunks]

    # Make sure the input is progressing during the output. In test, there
    # are about 915 steps, so checking that it's greater than 50 shouldm't
    # make this test too flakey
    num_steps = 0
    prev_i = 0
    for i in latest_input_during_output:
        if i != prev_i:
            num_steps += 1
        prev_i = i

    assert num_steps > 50


def test_exception_from_input_before_yield_propagated():
    def yield_input():
        raise Exception('Something went wrong')

    with pytest.raises(Exception, match='Something went wrong'):
        b''.join(iterable_subprocess(['cat'], yield_input()))


def test_exception_from_input_after_yield_propagated():
    def yield_input():
        yield b'*'
        raise Exception('Something went wrong')

    with pytest.raises(Exception, match='Something went wrong'):
        b''.join(iterable_subprocess(['cat'], yield_input()))


def test_exception_from_input_incorrect_type_propagated():
    def yield_input():
        yield 'this-should-be-bytes'

    with pytest.raises(TypeError):
        b''.join(iterable_subprocess(['cat'], yield_input()))


def test_exception_from_not_found_process_propagated():
    with pytest.raises(FileNotFoundError):
        b''.join(iterable_subprocess(['does-not-exist'], yield_small_input()))


def test_funzip_no_compression():
    contents = b'*' * 100000

    def yield_input():
        file = io.BytesIO()
        with zipfile.ZipFile(file, 'w', zipfile.ZIP_STORED) as zf:
            zf.writestr('any.txt', contents)

        yield file.getvalue()

    output = b''.join(iterable_subprocess(['funzip'], yield_input()))
    assert output == contents


def test_funzip_deflate():
    contents = b'*' * 100000

    def yield_input():
        file = io.BytesIO()
        with zipfile.ZipFile(file, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('any.txt', contents)

        yield file.getvalue()

    output = b''.join(iterable_subprocess(['funzip'], yield_input()))
    assert output == contents


def yield_small_input():
    yield b'first'
    yield b'second'
    yield b'third'
