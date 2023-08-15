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
    # - The standard input thread iterates over the input, passing chunks to the process
    # - While the standard error thread fetches the error output
    # - And while this thread iterates over the processe's output from client code
    #   in the context
    #
    # To stop, i.e. on exit of the context from client code
    # - This thread closes the process's standard output
    # - Wait for the standard input thread to exit
    # - Wait for the standard error thread to exit
    # - Wait for the process to exit
    #
    # By using context managers internally, this also gives quite strong guarentees that
    # the above order is enforced to make sure the thread doesn't send data to the process
    # whose standard input is closed and so we don't get BrokenPipe errors

    # Writing to the process can result in a BrokenPipeError. If this then results in
    # a non-zero code from the process, the process's standard error probably has useful
    # information on the cause of this. However, the non-zero error code happens after
    # BrokenPipeError, so propagating "what happens first" isn't helpful in this case.
    # So, we re-raise BrokenPipeError as _BrokenPipeError so we can catch it after the
    # process ends to then allow us to branch on its error code:
    # - if it's non-zero raise an IterableSubprocessError containing its standard error
    # - if it's zero, re-raise the original BrokenPipeError
    class _BrokenPipeError(Exception):
        pass

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
                try:
                    stdin.write(chunk)
                except BrokenPipeError:
                    raise _BrokenPipeError()
        finally:
            try:
                stdin.close()
            except BrokenPipeError:
                raise _BrokenPipeError()

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

    proc = None
    stderr_deque = deque()

    try:

        with \
                Popen(program, stdin=PIPE, stdout=PIPE, stderr=PIPE) as proc, \
                thread(keep_only_most_recent, proc.stderr, stderr_deque), \
                thread(input_to, proc.stdin):

            output = output_from(proc.stdout)

            try:
                yield output
            finally:
                proc.stdout.close()

    except _BrokenPipeError as e:
        if proc.returncode == 0:
            raise e.__context__ from None

    if proc.returncode:
        raise IterableSubprocessError(proc.returncode, b''.join(stderr_deque)[-chunk_size:])


class IterableSubprocessError(SubprocessError):
    def __init__(self, returncode, stderr):
        self.returncode = returncode
        self.stderr = stderr
