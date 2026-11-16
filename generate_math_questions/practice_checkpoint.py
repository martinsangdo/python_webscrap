"""Local, atomic checkpoints for one practice set; no credentials are stored."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile


class CheckpointError(RuntimeError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class PracticeCheckpoint:
    VERSION = 1

    def __init__(self, directory, identity):
        self.identity = identity
        self.path = Path(directory) / (digest(identity) + '.json')
        self.data = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = self.path.with_suffix('.lock').open('a')
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            self.lock.close()
            raise CheckpointError(f'Another generator is using checkpoint {self.path}') from error
        return self

    def __exit__(self, *exc):
        self.lock.close()  # OS releases this lock even if the process is killed.

    def load(self, context):
        self.context_hash = digest(context)
        if not self.path.exists():
            return None
        try:
            data = json.loads(self.path.read_text())
            if (data['version'] != self.VERSION or data['identity'] != self.identity
                    or data['context_hash'] != self.context_hash
                    or not isinstance(data['questions'], dict)):
                raise ValueError('Checkpoint version or exam settings have changed')
        except (ValueError, KeyError, TypeError, OSError) as error:
            raise CheckpointError(
                f'Cannot resume checkpoint {self.path}: {error}. '
                'Keep a backup and remove this file to intentionally start again.'
            ) from error
        self.data = data
        print(f'Resuming checkpoint: {self.path}', flush=True)
        return data

    def initialize(self, plan):
        self.data = {
            'version': self.VERSION, 'identity': self.identity,
            'context_hash': self.context_hash, 'plan': plan.model_dump(),
            'questions': {str(q.position): {'status': 'draft', 'question': None}
                          for q in plan.questions},
        }
        self.save()
        print(f'Saving progress to: {self.path}', flush=True)

    def complete(self, question, duplicate_source):
        self.data['questions'][str(question.position)] = {
            'status': 'completed', 'question': question.model_dump(),
            'duplicate_source': duplicate_source,
        }
        self.save()

    def save(self):
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', dir=self.path.parent,
                                             prefix=self.path.name + '.', delete=False) as output:
                temporary = output.name
                json.dump(self.data, output, ensure_ascii=False)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.path)
            temporary = None
            directory_fd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError as error:
            raise CheckpointError(f'Unable to save checkpoint {self.path}: {error}') from error
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)

    def finish(self):
        try:
            self.path.unlink(missing_ok=True)
        except OSError as error:
            print(f'Set saved, but checkpoint cleanup failed: {error}', flush=True)
