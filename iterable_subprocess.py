from contextlib import contextmanager
from subprocess import Popen, PIPE
from threading import Thread


@contextmanager
def iterable_subprocess(program, input_chunks, chunk_size=65536):
    write_exception = None
    t = None

    try:
        with Popen(program, stdin=PIPE, stdout=PIPE) as proc:
            # Send to process from another thread...
            def input_to_process():
                nonlocal write_exception

                try:
                    for chunk in input_chunks:
                        proc.stdin.write(chunk)
                except BaseException as e:
                    write_exception = e
                finally:
                    proc.stdin.close()

            t = Thread(target=input_to_process)
            t.start()

            # ... but read from the process in this thread
            def output_from_process():
                while True:
                    chunk = proc.stdout.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

            yield output_from_process()
    finally:
        if t is not None and t.ident:
            t.join()

    if write_exception is not None:
        raise write_exception
