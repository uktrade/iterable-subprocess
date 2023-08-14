from collections import deque
from contextlib import contextmanager
from subprocess import PIPE, SubprocessError, Popen
from threading import Thread


@contextmanager
def iterable_subprocess(program, input_chunks, chunk_size=65536):
    # This context starts a thread that populates the subprocess's standard input. It
    # also starts a threads that reads the proceses standard error. Otherwise we risk
    # a deadlock - there is no output because the process is waiting for more input.
    #
    # This itself introduces its own complications and risks, but hopefully mitigated
    # by having a well defined start and stop mechanism that also avoid sending data
    # to the process if it's not running
    #
    # To start, i.e. on entry to the context from client code
    # - The process is started
    # - The thread to read from standard error is started
    # - The thread to populate input is started
    #
    # When running:
    # - The standard input thread iterates over the input, passing chunks to the process,
    #   When the iterable is exhausted it closes the process's standard input
    # - All while the standard error thread fetches the error output
    # - All while this thread iterates over the process's output from client code
    #   in the context
    #
    # To stop, i.e. on exit of the context from client code
    # - This thread instructs the process to terminate
    # - Wait for the standard input thread to exit
    # - Wait for the standard error thread to exit
    # - Wait for the process to exit
    #
    # By using context managers internally, this also gives quite strong guarentees that
    # the above order is enforced to make sure the thread doesn't send data to the process
    # whose standard input is closed and so we don't get BrokenPipe errors

    @contextmanager
    def thread(target, *args):
        exception = None
        def wrapper():
            nonlocal exception
            try:
                target(*args)
            except BaseException as e:
                exception = e

        t = Thread(target=wrapper)
        t.start()
        try:
            yield
        finally:
            t.join()

        if exception is not None:
            raise exception

    def input_to(stdin):
        try:
            for chunk in input_chunks:
                stdin.write(chunk)
        finally:
            stdin.close()

    def output_from(stdout):
        while True:
            chunk = stdout.read(chunk_size)
            if not chunk:
                break
            yield chunk

    def keep_only_most_recent(stderr, stderr_deque):
        total_length = 0
        while True:
            chunk = stderr.read(chunk_size)
            total_length += len(chunk)
            if not chunk:
                break
            stderr_deque.append(chunk)
            if total_length - len(stderr_deque[0]) >= chunk_size:
                total_length -= len(stderr_deque[0])
                stderr_deque.popleft()

    stderr_deque = deque()

    with \
            Popen(program, stdin=PIPE, stdout=PIPE, stderr=PIPE) as proc, \
            thread(keep_only_most_recent, proc.stderr, stderr_deque), \
            thread(input_to, proc.stdin):

        output = output_from(proc.stdout)

        try:
            yield output
        finally:
            # The happy path is that we would have written all input data to the process's
            # standard input, and have read all its output to completion. This terminate
            # is for the unhappy path where we exit the context before this has happened
            proc.terminate()

    if proc.returncode:
        raise IterableSubprocessError(proc.returncode, b''.join(stderr_deque)[-chunk_size:])


class IterableSubprocessError(SubprocessError):
    def __init__(self, returncode, stderr):
        self.returncode = returncode
        self.stderr = stderr
