"""Process-shared lab lease and durable recovery journal. Contains no model data."""
import fcntl
import functools
import json
import os
from pathlib import Path
from contextvars import ContextVar

ROOT = Path(__file__).resolve().parents[1]
HELD = ContextVar('held_environments', default=frozenset())


class Conflict(RuntimeError):
    pass


class Lease:
    def __init__(self, root=ROOT):
        self.directory = Path(root) / 'results' / 'control'
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'environment.lock'
        self.journal = self.directory / 'state.json'
        self.file = None

    def acquire(self):
        self.file = self.path.open('a+')
        try:
            fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.file.close()
            self.file = None
            raise Conflict('This experiment is busy in another operation or server')
        return self

    def release(self):
        if self.file:
            self.file.close()
            self.file = None

    def read(self):
        if not self.journal.exists():
            return {'pending': [], 'operation': None}
        # Corrupt state must fail closed; never silently forget an owned fault.
        state = json.loads(self.journal.read_text())
        if not isinstance(state, dict) or not isinstance(state.get('pending'), list) or not all(isinstance(f, str) for f in state['pending']) or not isinstance(state.get('operation'), (dict, type(None))):
            raise ValueError('Invalid recovery journal; inspect it before proceeding')
        return state

    def write(self, state):
        temp = self.directory / 'state.tmp'
        with temp.open('w') as output:
            json.dump(state, output, ensure_ascii=False)
            output.flush()
            os.fsync(output.fileno())
        temp.replace(self.journal)
        directory_fd = os.open(self.directory, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    def mark(self, fault):
        state = self.read()
        if fault not in state['pending']:
            state['pending'].append(fault)
            self.write(state)

    def clear(self, faults):
        state = self.read()
        state['pending'] = [f for f in state['pending'] if f not in faults]
        self.write(state)


def inherited(root=ROOT):
    try:
        fd = int(os.environ.get('SADE_ENV_LOCK_FD', '-1'))
        expected = Lease(root).path.stat()
        actual = os.fstat(fd)
        return (expected.st_dev, expected.st_ino) == (actual.st_dev, actual.st_ino)
    except (ValueError, OSError):
        return False


def evaluation_session(function):
    """Standalone evaluator calls and dashboard children use the same lab lease."""
    @functools.wraps(function)
    def guarded(*args, **kwargs):
        root = function.__globals__.get('ROOT', ROOT)
        if root in HELD.get():
            return function(*args, **kwargs)
        lease = Lease(root)
        owned = not inherited(root)
        if owned:
            lease.acquire()
        try:
            if lease.read()['pending']:
                raise Conflict('Recover pending faults in the dashboard before automatic evaluation')
            token = HELD.set(HELD.get() | {root})
            try:
                return function(*args, **kwargs)
            finally:
                HELD.reset(token)
        finally:
            if owned:
                lease.release()
    return guarded
