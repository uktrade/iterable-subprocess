from collections import deque
from contextlib import contextmanager
from subprocess import PIPE, SubprocessError, Popen
from threading import Thread


@contextmanager
def iterable_subprocess(program, input_chunks, chunk_size=65536):
    # This context starts a thread that populates the subprocess's standard input.
    # Otherwise we risk a deadlock - there is no output because the process is waiting
    # for more input.
    #
    # This itself introduces its own complications and risks, but hopefully mitigated
    # by having a well defined entry and exit mechanism that avoids sending data
    # to the process if it's not running
    #
    # - The process is started
    # - The thread is started
    # - The thread iterates over the input, passing the input chunks to the process
    # - The thread is instructed to stop iterating and close the process's standard input
    # - Wait for the thread to exit
    # - Wait for the process to exit
    #
    # By using context manager internally, this also gives quite strong guarentees that
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

    def input_to(stdin, get_exiting):
        try:
            for chunk in input_chunks:
                if not get_exiting():
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
                stderr_deque.popleft()

    exiting = False
    stderr_deque = deque()

    with \
            Popen(program, stdin=PIPE, stdout=PIPE, stderr=PIPE) as proc, \
            thread(input_to, proc.stdin, lambda: exiting), \
            thread(keep_only_most_recent, proc.stderr, stderr_deque):

        output = output_from(proc.stdout)

        try:
            yield output
        finally:
            exiting = True
            for _ in output:  # Avoid a deadlock if the thread is still writing
                pass

    if proc.returncode:
        raise IterableSubprocessError(proc.returncode, b''.join(stderr_deque)[-chunk_size:])


class IterableSubprocessError(SubprocessError):
    def __init__(self, returncode, stderr):
        self.returncode = returncode
        self.stderr = stderr
