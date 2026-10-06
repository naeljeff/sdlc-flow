#!/usr/bin/env python3
"""Optional local team record keeper. Consistency checks are not semantic assurance.

Run --help. Canonical writes are orchestrator operations; --owner is an identity
check, not authentication. Workers write their result files and never state.json.
Requires Python 3.9+; uses POSIX fcntl or Windows msvcrt advisory locking.
"""
import argparse
import copy
try:
    import fcntl
except ImportError:  # Windows uses the standard-library byte-range lock.
    fcntl = None
    import msvcrt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import subprocess
import tempfile
import uuid
from contextlib import contextmanager

EXCLUDED = {'.git', '.sdlc-flow', '__pycache__', 'node_modules', '.venv', 'venv'}
CACHES = {'.pytest_cache', '.mypy_cache', '.ruff_cache', '.cache', '.next', 'dist', 'build', 'coverage'}
STATES = {'pending', 'ready', 'running', 'review', 'integrated', 'verified', 'blocked', 'obsolete'}
EDGES = {'pending': {'ready', 'blocked', 'obsolete'}, 'ready': {'running', 'blocked', 'obsolete'},
         'running': {'blocked', 'obsolete'}, 'review': {'integrated', 'ready', 'blocked', 'obsolete'},
         'integrated': {'ready', 'blocked', 'obsolete'}, 'verified': {'ready', 'obsolete'},
         'blocked': {'ready', 'obsolete'}, 'obsolete': set()}


class Invalid(ValueError):
    pass


def require(test, message):
    if not test:
        raise Invalid(message)


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', value),
            'IDs must contain only letters, numbers, dot, dash or underscore')
    return value


def relative(value):
    require(isinstance(value, str) and value and '\\' not in value, 'path must be relative POSIX text')
    p = PurePosixPath(value)
    require(not p.is_absolute() and '..' not in p.parts and str(p) != '.', 'unsafe relative path')
    require(str(p) == value.rstrip('/'), 'path must be normalized')
    return str(p)


def under(root, value):
    value = relative(value)
    p = root / value
    require(p.resolve().is_relative_to(root.resolve()), 'path escapes artifact/source root')
    # Internal symlinks are rejected for task artifacts; never overwrite a linked file.
    for part in [p, *p.parents]:
        if part == root.parent:
            break
        require(not part.is_symlink(), 'symlink in owned artifact path')
    return p


def read_json(path):
    with open(path, encoding='utf-8') as stream:
        return json.load(stream)


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def identity(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def sources(root, task=None):
    """Hash source bytes, including untracked files. Skip named dependency/cache roots."""
    root = root.resolve()
    require(root.is_dir(), 'source workspace does not exist')
    files = {}
    selected, tracked = None, set()
    if (root / '.git').exists():
        try:
            def git_files(*flags):
                result = subprocess.run(['git', '-C', str(root), 'ls-files', '-z', *flags],
                                        check=True, capture_output=True)
                return set(result.stdout.decode('utf-8').split('\0')) - {''}
            tracked = git_files('--cached')
            selected = tracked | git_files('--others', '--exclude-standard')
        except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
            raise Invalid('cannot read Git source inventory: ' + str(exc))
    for parent, dirs, names in os.walk(root, followlinks=False):
        base = Path(parent)
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED and
                         (d not in CACHES or any(p.startswith((base / d).relative_to(root).as_posix() + '/') for p in tracked)) and
                         (selected is None or any(p.startswith((base / d).relative_to(root).as_posix() + '/') for p in selected)) and
                         not (task and (base / d).resolve() == task.resolve()))
        for name in dirs:
            p = base / name
            require(not p.is_symlink(), 'symlink source directory requires explicit resolution')
        for name in sorted(names):
            if name.endswith(('.pyc', '.pyo')) or name in {'.DS_Store', '.git'}:
                continue
            p = base / name
            key = p.relative_to(root).as_posix()
            if (selected is not None and key not in selected) or (name.startswith('.coverage') and key not in tracked) or \
               (any(part in CACHES for part in p.relative_to(root).parts[:-1]) and key not in tracked):
                continue
            require(not p.is_symlink(), 'symlink source file requires explicit resolution')
            require(p.is_file(), 'source contains non-regular file')
            key = p.relative_to(root).as_posix()
            files[key] = {'sha256': digest(p), 'executable': bool(p.stat().st_mode & 0o111)}
    return files


def atomic(path, value):
    require(not path.is_symlink(), 'refusing to overwrite symlink')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            if isinstance(value, str):
                stream.write(value)
            else:
                json.dump(value, stream, indent=2, sort_keys=True)
                stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        if os.name != 'nt':
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def immutable(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Publish only a fully flushed file, without replacing an existing artifact.
    # A process interruption may leave a .pending file, never a partial final.
    fd, name = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(name, path)
        except FileExistsError:
            require(read_json(path) == value, 'existing artifact has different content')
        if os.name != 'nt':
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def brief(value):
    require(isinstance(value, dict) and isinstance(value.get('outcome'), str) and value['outcome'].strip(),
            'brief requires outcome')
    require(isinstance(value.get('acceptance'), list) and value['acceptance'], 'brief requires acceptance IDs')
    seen = set()
    for row in value['acceptance']:
        identifier(row['id'])
        require(row['id'] not in seen and isinstance(row.get('text'), str) and row['text'].strip(),
                'acceptance IDs must be unique and have text')
        seen.add(row['id'])
    for key in ('constraints', 'preserved', 'prohibited', 'interfaces'):
        value.setdefault(key, [])
        require(isinstance(value[key], list) and all(isinstance(x, str) for x in value[key]), key + ' must be text list')
    return value


@contextmanager
def locked(task, owner=None, revision=None):
    require(task.is_dir() and not task.is_symlink(), 'task root missing or linked')
    lock_path = under(task, '.lock')
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'r+') as stream:
        if fcntl is not None:
            fcntl.flock(stream, fcntl.LOCK_EX)
        else:
            if os.fstat(stream.fileno()).st_size == 0:
                stream.write('0')
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        state = read_json(under(task, 'state.json'))
        if owner is not None:
            require(owner == state['owner'], 'only the recorded orchestrator may mutate canonical state')
        if revision is not None:
            require(revision == state['revision'], 'revision conflict; reload current state')
        yield state


def view_text(value):
    """Render data as one literal Markdown line, preserving canonical content."""
    text = json.dumps(value, ensure_ascii=True)[1:-1]
    return ''.join('\\' + char if char in '\\`*_{}[]()#+-.!|<>~' else char for char in text)


def publish(task, state):
    for path in ('state.json', 'memory/facts.json', 'BRIEF.json', 'BRIEF.md', 'STATE.md', 'MEMORY.md'):
        under(task, path)
    state['revision'] += 1
    atomic(under(task, 'state.json'), state)
    # Views have no authority; a crash may leave them old. status regenerates from JSON.
    atomic(under(task, 'memory/facts.json'), {'revision': state['memory_revision'], 'facts': state['facts']})
    atomic(under(task, 'BRIEF.json'), state['brief'])
    lines = ['# Effective task brief', '', view_text(state['brief']['outcome']), '', '## Acceptance', '']
    lines += ['- ' + x['id'] + ': ' + view_text(x['text']) for x in state['brief']['acceptance']]
    for key in ('constraints', 'preserved', 'prohibited', 'interfaces'):
        lines += ['', '## ' + key.capitalize(), ''] + ['- ' + view_text(x) for x in state['brief'][key]]
    atomic(under(task, 'BRIEF.md'), '\n'.join(lines) + '\n')
    lines = ['# Generated task state', '', 'Authority: state.json. Revision: ' + str(state['revision']), '']
    lines += ['- ' + x['id'] + ': ' + x['state'] + '; owner ' + x['agent'] + '; live=' + str(x.get('live', False)) + '; next: ' + view_text(x['next_action'])
              for x in state['assignments'].values()]
    atomic(under(task, 'STATE.md'), '\n'.join(lines) + '\n')
    lines = ['# Generated memory index', '', 'Authority: state.json. Memory revision: ' + str(state['memory_revision']), '']
    lines += ['- ' + x['id'] + ' [' + x['kind'] + ', ' + x['status'] + ']: ' + view_text(x['text']) for x in state['facts']]
    atomic(under(task, 'MEMORY.md'), '\n'.join(lines) + '\n')


def fresh(state, task):
    changed = False
    for fact in state['facts']:
        if fact['status'] != 'current':
            continue
        for source in fact['sources']:
            p = under(Path(state['repo']), source['path'])
            if not p.is_file() or digest(p) != source['sha256']:
                fact['status'] = 'stale'
                changed = True
                break
    if changed:
        state['memory_revision'] += 1
    return changed


def assignment(state, key):
    require(key in state['assignments'], 'unknown assignment')
    return state['assignments'][key]


def shared_current(state, task, row, worker_files, checks=()):
    integrated = sources(Path(state['repo']), task)
    for scope in row.get('shared_reads', []):
        selected = lambda fs: {p: v for p, v in fs.items() if p == scope or p.startswith(scope + '/')}
        require(selected(worker_files) == selected(integrated), 'stale shared-read source; refresh assignment interface')
    for check in checks:
        for item in check.get('checked_files', []):
            path = item['path']
            if not any(path == owned or path.startswith(owned + '/') for owned in row['owned_paths']):
                require(worker_files.get(path) == integrated.get(path), 'check uses stale shared source')


def snapshot_matches(state, value, current):
    for key in ('task_id', 'generation', 'spec_revision', 'snapshot'):
        expected = state['task_id'] if key == 'task_id' else current[key]
        require(value.get(key) == expected, 'stale or mismatched ' + key)
    require(current['spec_revision'] == state['spec_revision'], 'assignment uses obsolete requirements')


def overlaps(a, b):
    return a == b or a.startswith(b + '/') or b.startswith(a + '/')


def deps_ready(state, row):
    return all(state['assignments'][d]['state'] in {'integrated', 'verified'} for d in row['dependencies'])


def graph_valid(rows):
    visiting, done = set(), set()
    def visit(key):
        require(key in rows, 'unknown dependency: ' + key)
        require(key not in visiting, 'dependency cycle')
        if key in done:
            return
        visiting.add(key)
        for dep in rows[key]['dependencies']:
            visit(dep)
        visiting.remove(key)
        done.add(key)
    for key in rows:
        visit(key)


def metadata(value):
    require(isinstance(value, dict), 'metadata must be an object')
    value = copy.deepcopy(value)
    for key in ('requested_model', 'reported_model', 'effort', 'backend', 'agent_id', 'usage'):
        value.setdefault(key, 'unknown')
        if key != 'usage':
            require(isinstance(value[key], str) and value[key], 'metadata identity/model fields must be text or unknown')
    if value['usage'] != 'unknown':
        require(isinstance(value['usage'], dict) and value['usage'].get('source') in {'host', 'provider'},
                'known usage requires observed host/provider source')
    # Self-reported prose is never promoted to provider-reported identity.
    if value['reported_model'] != 'unknown':
        require(value.get('reported_model_source') in {'host', 'provider'}, 'reported model requires host/provider source')
    return value


def evidence(task, rows, fingerprint, spec_revision):
    require(isinstance(rows, list) and rows, 'nonempty evidence list required')
    result = []
    for row in rows:
        require(isinstance(row, dict), 'evidence entries require path and sha256')
        require(row.get('result') == 'passed', 'evidence observation must have passed')
        require(row.get('source_fingerprint') == fingerprint and row.get('spec_revision') == spec_revision,
                'evidence observation uses obsolete source or requirements')
        path = relative(row['path'])
        require(path.startswith('evidence/'), 'evidence must be under task/evidence')
        p = under(task, path)
        require(p.is_file() and p.stat().st_size > 0, 'evidence file missing or empty')
        require(digest(p) == row.get('sha256'), 'evidence hash mismatch')
        result.append({'path': path, 'sha256': row['sha256'], 'result': 'passed',
                       'source_fingerprint': fingerprint, 'spec_revision': spec_revision})
    return result


def validate_gate(state, task, value, ids):
    require(value.get('task_id') == state['task_id'] and value.get('spec_revision') == state['spec_revision'],
            'gate has obsolete task or requirements')
    fingerprint = identity(sources(Path(state['repo']), task))
    require(value.get('source_fingerprint') == fingerprint, 'gate uses stale integrated source')
    claims = value.get('acceptance', {})
    require(set(claims) == set(ids), 'gate must cover exactly the required acceptance IDs')
    checks = {key: evidence(task, rows, fingerprint, state['spec_revision']) for key, rows in claims.items()}
    review = value.get('review', {})
    contributors = {state['owner']} | {a['agent'] for a in state['assignments'].values()}
    observed_ids = [state.get('owner_agent_id', 'unknown')] + [a['metadata'].get('agent_id', 'unknown') for a in state['assignments'].values()]
    contributors.update(x for x in observed_ids if isinstance(x, str) and x != 'unknown')
    require(review.get('independent') is True and isinstance(review.get('reviewer'), str) and review['reviewer'] and
            review['reviewer'] not in contributors and review.get('agent_id', review['reviewer']) not in contributors,
            'fresh independent reviewer required')
    require(isinstance(review.get('context_id'), str) and review['context_id'].strip(), 'fresh review context identity required')
    require(review.get('source_fingerprint') == fingerprint, 'review uses stale integrated source')
    require(review.get('spec_revision') == state['spec_revision'], 'review uses obsolete requirements')
    review = dict(review, evidence=evidence(task, review.get('evidence'), fingerprint, state['spec_revision']))
    return {'task_id': state['task_id'], 'spec_revision': state['spec_revision'],
            'source_fingerprint': fingerprint, 'acceptance': checks, 'review': review}


def gate_current(state, task):
    if not state.get('gate'):
        return False
    try:
        validate_gate(state, task, state['gate'], [x['id'] for x in state['brief']['acceptance']])
        return True
    except (Invalid, OSError):
        return False


def run(args):
    task = Path(args.task).absolute()
    if args.command == 'init':
        require(not task.exists(), 'task directory already exists; pre-existing artifacts protected')
        require(not task.is_symlink(), 'task root is linked')
        repo = Path(args.repo).resolve()
        value = brief(read_json(args.brief))
        initial = sources(repo, task)
        task.mkdir(parents=True, exist_ok=False)
        state = {'schema': 1, 'task_id': str(uuid.uuid4()), 'owner': args.owner, 'repo': str(repo),
                 'owner_agent_id': args.owner_agent_id, 'revision': 0, 'spec_revision': 1, 'memory_revision': 0, 'brief': value,
                 'initial_fingerprint': identity(initial), 'assignments': {}, 'facts': [], 'gate': None}
        atomic(under(task, 'state.json'), state)
        atomic(under(task, 'BRIEF.json'), value)
        return state
    with locked(task, getattr(args, 'owner', None), getattr(args, 'expect_revision', None)) as state:
        cmd = args.command
        if cmd == 'status':
            projected = copy.deepcopy(state)
            fresh(projected, task)
            return {'task_id': state['task_id'], 'revision': state['revision'], 'spec_revision': state['spec_revision'],
                    'memory_revision': state['memory_revision'], 'source_fingerprint': identity(sources(Path(state['repo']), task)),
                    'complete': gate_current(state, task),
                    'assignments': {key: {k: v for k, v in row.items() if k != 'baseline'}
                                    for key, row in state['assignments'].items()}, 'facts': projected['facts']}
        if cmd == 'context':
            row = assignment(state, args.assignment)
            require(row['spec_revision'] == state['spec_revision'] and row['state'] != 'obsolete', 'obsolete assignment')
            current = copy.deepcopy(state)
            fresh(current, task)
            packet = {'task_id': state['task_id'], 'state_revision': state['revision'],
                      'spec_revision': state['spec_revision'], 'memory_revision': current['memory_revision'],
                      'brief': state['brief'], 'assignment': {k: v for k, v in row.items() if k != 'baseline'},
                      'memory_location': None,
                      'memory_status_command': [sys.executable, str(Path(__file__).resolve()), 'status', '--task', str(task)],
                      'result_destination': str(task / 'inbox' / row['agent'] / (row['id'] + '-g' + str(row['generation']) + '.json')),
                      'facts': []}
            scopes = row['owned_paths'] + row.get('shared_reads', [])
            relevant = [fact for fact in current['facts'] if fact['status'] == 'current' and
                        (any(overlaps(scope, owned) for scope in fact['scope'] for owned in scopes) or
                         (row['role'] == 'reader' and not scopes))]
            packet['facts'] = [fact for fact in relevant if fact['kind'] == 'decision']
            mandatory = json.dumps(packet, indent=2, sort_keys=True) + '\n'
            require(len(mandatory) <= args.max_chars, 'mandatory requirements exceed context budget; split assignment or raise budget')
            for fact in relevant:
                if fact['kind'] != 'decision':
                    candidate = dict(packet, facts=packet['facts'] + [fact])
                    if len(json.dumps(candidate, indent=2, sort_keys=True)) + 1 <= args.max_chars:
                        packet = candidate
            return packet
        if cmd == 'add':
            row = read_json(args.input)
            key = identifier(row['id'])
            require(key not in state['assignments'], 'assignment already exists; resume it through transition')
            row['agent'] = identifier(row['agent'])
            require(row['role'] in {'writer', 'reader'}, 'role must be writer or reader')
            require(isinstance(row.get('outcome'), str) and row['outcome'].strip(), 'assignment outcome required')
            require(isinstance(row.get('next_action'), str) and row['next_action'].strip(), 'exact next action required')
            ids = {x['id'] for x in state['brief']['acceptance']}
            require(isinstance(row.get('acceptance_ids'), list) and row['acceptance_ids'] and set(row['acceptance_ids']) <= ids,
                    'assignment requires known acceptance IDs')
            row['owned_paths'] = [relative(x) for x in row.get('owned_paths', [])]
            row['shared_reads'] = [relative(x) for x in row.get('shared_reads', [])]
            require(row['role'] != 'writer' or row['owned_paths'], 'writer needs owned paths')
            require(isinstance(row.get('dependencies', []), list), 'dependencies must be IDs')
            row.setdefault('dependencies', [])
            workspace = Path(row['workspace']).resolve()
            row['workspace'] = str(workspace)
            baseline = sources(workspace, task)
            integrated = sources(Path(state['repo']), task)
            require(identity(baseline) == identity(integrated), 'workspace does not match current integration snapshot')
            if row['role'] == 'writer':
                repo = Path(state['repo']).resolve()
                require(not workspace.is_relative_to(repo) and not repo.is_relative_to(workspace), 'writer needs isolated workspace')
                require(not any(os.path.samefile(workspace / p, repo / p) for p in baseline),
                        'writer copy shares hardlinked source files with integration')
                for old in state['assignments'].values():
                    if old['role'] != 'writer' or (old['state'] in {'verified', 'obsolete'} and not old.get('live')):
                        continue
                    other = Path(old['workspace'])
                    require(not workspace.is_relative_to(other) and not other.is_relative_to(workspace), 'writers must use separate workspaces')
                    require(not any((other / p).is_file() and os.path.samefile(workspace / p, other / p) for p in baseline),
                            'writers share hardlinked source files')
                    require(not any(overlaps(a, b) for a in row['owned_paths'] for b in old['owned_paths']), 'owned path conflict')
            row.update(task_id=state['task_id'], generation=1, spec_revision=state['spec_revision'],
                       snapshot=identity(baseline), baseline=baseline, metadata=metadata(row.get('metadata', {})),
                       state='pending', live=False, results=[], result_hashes={}, verification=None)
            state['assignments'][key] = row
            graph_valid(state['assignments'])
            if deps_ready(state, row):
                row['state'] = 'ready'
            atomic(under(task, 'assignments/' + key + '.json'), row)
        elif cmd == 'ingest':
            value = read_json(args.input)
            row = assignment(state, value['assignment_id'])
            snapshot_matches(state, value, row)
            require(row['state'] == 'running', 'result only accepted from running assignment')
            require(value.get('agent') == row['agent'], 'result agent does not own assignment')
            require(value.get('status') in {'complete', 'partial', 'blocked', 'failed'}, 'invalid worker status')
            actual = sources(Path(row['workspace']), task)
            changed = sorted(key for key in set(actual) | set(row['baseline']) if actual.get(key) != row['baseline'].get(key))
            manifest = value.get('manifest')
            require(isinstance(manifest, list), 'result requires manifest')
            reported = {}
            for entry in manifest:
                path = relative(entry['path'])
                require(path not in reported, 'duplicate manifest path')
                require(any(path == owned or path.startswith(owned + '/') for owned in row['owned_paths']), 'manifest outside owned scope')
                reported[path] = entry.get('sha256')
                require(entry.get('sha256') == (actual[path]['sha256'] if path in actual else None), 'manifest content mismatch')
                require('executable' in entry and entry['executable'] == (actual[path]['executable'] if path in actual else None),
                        'manifest executable mode mismatch')
            require(sorted(reported) == changed, 'unaccounted workspace changes')
            require(row['role'] == 'writer' or not changed, 'reader changed source')
            require(isinstance(value.get('next_action'), str) and value['next_action'].strip(), 'result requires next action')
            require(isinstance(value.get('checks'), list) and isinstance(value.get('limitations'), list),
                    'result requires checks and explicit limitations')
            for check in value['checks']:
                require(isinstance(check, dict) and check.get('command') and check.get('result') in {'passed', 'failed', 'unknown'},
                        'invalid check observation')
                for file in check.get('checked_files', []):
                    p = relative(file['path'])
                    require(p in actual and file.get('sha256') == actual[p]['sha256'], 'check uses stale workspace source')
            shared_current(state, task, row, actual, value['checks'])
            value['metadata'] = metadata(value.get('metadata', {}))
            path = under(task, 'inbox/' + row['agent'] + '/' + row['id'] + '-g' + str(row['generation']) + '.json')
            if path.exists() or path.is_symlink():
                require(path.is_file() and not path.is_symlink(), 'result destination must be a regular file')
                existing = read_json(path)
                # Omitted worker metadata means unknown; keep the worker's immutable bytes.
                require(isinstance(existing, dict) and dict(existing, metadata=metadata(existing.get('metadata', {}))) == value,
                        'existing artifact has different content')
            else:
                immutable(path, value)
            artifact = path.relative_to(task).as_posix()
            row['results'].append(artifact)
            row['result_hashes'][artifact] = digest(path)
            row['state'] = 'review' if value['status'] in {'complete', 'partial'} else 'blocked'
            row['next_action'] = value['next_action']
            row['live'] = row.get('live', False) and not args.worker_ended
        elif cmd == 'memory':
            value = read_json(args.input)
            require(isinstance(value, list), 'memory input must be a fact list')
            fresh(state, task)
            for fact in value:
                identifier(fact['id'])
                require(not any(x['id'] == fact['id'] for x in state['facts']), 'fact ID already exists')
                require(fact.get('kind') in {'fact', 'decision', 'hypothesis'} and
                        isinstance(fact.get('text'), str) and fact['text'].strip(), 'fact needs kind and text')
                require(fact.get('confidence') in {'high', 'medium', 'low', 'unknown'}, 'fact confidence required')
                fact['scope'] = [relative(x) for x in fact['scope']]
                require(fact['scope'], 'fact requires source scope')
                require(isinstance(fact.get('sources'), list) and fact['sources'], 'source-backed fact requires sources')
                for source in fact['sources']:
                    p = under(Path(state['repo']), source['path'])
                    require(p.is_file() and digest(p) == source.get('sha256'), 'fact source is missing or stale')
                if fact.get('supersedes'):
                    old = next((x for x in state['facts'] if x['id'] == fact['supersedes']), None)
                    require(old is not None, 'unknown superseded fact')
                    old['status'] = 'superseded'
                fact.update(status='current', spec_revision=state['spec_revision'])
                state['facts'].append(fact)
            state['memory_revision'] += 1
        elif cmd == 'revise':
            state['brief'] = brief(read_json(args.brief))
            state['spec_revision'] += 1
            state['memory_revision'] += 1
            state['gate'] = None
            for fact in state['facts']:
                if fact['status'] == 'current':
                    fact['status'] = 'requirements_changed'
            for row in state['assignments'].values():
                row['state'] = 'obsolete'
                row['verification'] = None
            atomic(under(task, 'BRIEF.json'), state['brief'])
        elif cmd == 'transition':
            row = assignment(state, args.assignment)
            ending = False
            if row.get('live') and args.evidence:
                observation = read_json(args.evidence)
                ending = observation.get('worker_ended') is True
            if ending:
                ended = read_json(args.evidence)
                require(ended.get('worker_ended') is True and ended.get('agent') == row['agent'] and
                        ended.get('generation') == row['generation'], 'worker termination observation required')
                row['live'] = False
            same_state_terminal = ending and args.to == row['state']
            require(args.to in EDGES[row['state']] or (row['state'] == args.to and ending),
                    'invalid transition; worker completion is not verification')
            require(not row.get('live') or args.to in {'obsolete', 'blocked', 'integrated'}, 'live worker must end before reassignment')
            if args.to in {'ready', 'running', 'integrated'} and not same_state_terminal:
                require(row['spec_revision'] == state['spec_revision'], 'obsolete assignment')
                require(deps_ready(state, row), 'dependencies not integrated')
            if args.to == 'ready' and row['state'] in {'blocked', 'review', 'integrated', 'verified'}:
                for other in state['assignments'].values():
                    if other['id'] != row['id'] and other['role'] == 'writer' and (other['state'] not in {'verified', 'obsolete'} or other.get('live')):
                        require(not any(overlaps(a, b) for a in row['owned_paths'] for b in other['owned_paths']), 'owned path conflict on resume')
                row['generation'] += 1
                row['verification'] = None
                if row['state'] in {'integrated', 'verified'}:
                    baseline = sources(Path(row['workspace']), task)
                    require(identity(baseline) == identity(sources(Path(state['repo']), task)),
                            'resumed integrated workspace must match current integration source')
                    row['baseline'] = baseline
                    row['snapshot'] = identity(baseline)
            if args.to == 'running' and not same_state_terminal:
                workspace_files = sources(Path(row['workspace']), task)
                shared_current(state, task, row, workspace_files)
                for dep in row['dependencies']:
                    dependency = state['assignments'][dep]
                    if not dependency['results']:
                        continue
                    artifact = dependency['results'][-1]
                    result_path = under(task, artifact)
                    require(digest(result_path) == dependency['result_hashes'][artifact], 'accepted result artifact changed')
                    result = read_json(result_path)
                    for entry in result['manifest']:
                        path = entry['path']
                        require(entry['sha256'] == (workspace_files[path]['sha256'] if path in workspace_files else None),
                                'workspace lacks integrated dependency source')
                        if path in workspace_files:
                            row['baseline'][path] = workspace_files[path]
                        else:
                            row['baseline'].pop(path, None)
                row['snapshot'] = identity(row['baseline'])
            if args.to == 'integrated' and row['state'] != 'integrated':
                require(args.evidence, 'integration requires evidence JSON {manifest:[{path,sha256}]}')
                integrated = sources(Path(state['repo']), task)
                artifact = row['results'][-1]
                result_path = under(task, artifact)
                require(digest(result_path) == row['result_hashes'][artifact], 'accepted result artifact changed')
                result = read_json(result_path)
                shared_current(state, task, row, sources(Path(row['workspace']), task), result['checks'])
                proof = read_json(args.evidence)
                require(proof.get('manifest') == result['manifest'], 'integration manifest differs from accepted result')
                for entry in result['manifest']:
                    p = entry['path']
                    require(entry['sha256'] == (integrated[p]['sha256'] if p in integrated else None) and
                            entry['executable'] == (integrated[p]['executable'] if p in integrated else None),
                            'integrated source does not match result')
            row['state'] = args.to
            if args.to == 'running' and not same_state_terminal:
                row['live'] = True
            state['gate'] = None
            atomic(under(task, 'assignments/' + row['id'] + '.json'), row)
        elif cmd in {'verify', 'gate'}:
            if cmd == 'verify':
                row = assignment(state, args.assignment)
                require(row['state'] == 'integrated' and not row.get('live'), 'assignment must be integrated and worker ended before verification')
                row['verification'] = validate_gate(state, task, read_json(args.input), row['acceptance_ids'])
                row['state'] = 'verified'
            else:
                require(all(a['state'] in {'verified', 'integrated', 'obsolete'} and not a.get('live') for a in state['assignments'].values()),
                        'active assignments are not integrated')
                state['gate'] = validate_gate(state, task, read_json(args.input), [x['id'] for x in state['brief']['acceptance']])
        elif cmd == 'checkpoint':
            fresh(state, task)
            saved = copy.deepcopy(state)
            saved['source_fingerprint'] = identity(sources(Path(state['repo']), task))
            # Revision-specific immutable snapshots preserve running workers and their owners.
            immutable(under(task, 'checkpoints/' + str(state['revision']) + '.json'), saved)
        publish(task, state)
        return {'task_id': state['task_id'], 'revision': state['revision'], 'spec_revision': state['spec_revision'],
                'memory_revision': state['memory_revision'], 'complete': gate_current(state, task)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for cmd in ('init', 'add', 'ingest', 'memory', 'revise', 'context', 'checkpoint', 'status', 'transition', 'verify', 'gate'):
        p = sub.add_parser(cmd)
        p.add_argument('--task', required=True)
        if cmd not in {'status', 'context'}:
            p.add_argument('--owner', required=True)
            if cmd != 'init':
                p.add_argument('--expect-revision', type=int)
        if cmd == 'init':
            p.add_argument('--repo', required=True)
            p.add_argument('--owner-agent-id', default='unknown', help='host-observed orchestrator ID, if exposed')
        if cmd in {'init', 'revise'}:
            p.add_argument('--brief', required=True)
        if cmd in {'add', 'ingest', 'memory', 'verify', 'gate'}:
            p.add_argument('--input', required=True)
        if cmd == 'ingest':
            p.add_argument('--worker-ended', action='store_true', help='orchestrator observed worker termination')
        if cmd in {'context', 'transition', 'verify'}:
            p.add_argument('--assignment', required=True)
        if cmd == 'context':
            p.add_argument('--max-chars', required=True, type=int)
        if cmd == 'transition':
            p.add_argument('--to', required=True, choices=sorted(STATES))
            p.add_argument('--evidence')
    args = parser.parse_args()
    try:
        print(json.dumps(run(args), indent=2, sort_keys=True))
    except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
        print('team: ' + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
