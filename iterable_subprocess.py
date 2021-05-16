from subprocess import Popen, PIPE
from threading import Thread

def iterable_subprocess(program, input_chunks, chunk_size=65536):
    write_exception = None

    with Popen(program, stdin=PIPE, stdout=PIPE) as proc:

        # Send to process from another thread...
        def pipe_to():
            nonlocal write_exception

            try:
                for chunk in input_chunks:
                    proc.stdin.write(chunk)
            except Exception as e:
                write_exception = e
                proc.kill()

        t = Thread(target=pipe_to)
        t.start()

        # ... but read from the process in this threadå
        while True:
            chunk = proc.stdout.read(chunk_size)
            if not chunk:
                break
            yield chunk

        t.join()
        if write_exception is not None:
            raise write_exception
