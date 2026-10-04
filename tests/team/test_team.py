"""Real-files CLI tests for ownership, recovery and the integrated evidence gate."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / 'skills/sdlc-flow/scripts/team.py'
spec = importlib.util.spec_from_file_location('team', SCRIPT)
team = importlib.util.module_from_spec(spec)
spec.loader.exec_module(team)


class TeamTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        (self.repo / 'src').mkdir()
        (self.repo / 'src/a.py').write_text('a = 1\n')
        (self.repo / 'src/b.py').write_text('b = 1\n')
        self.task = self.repo / '.sdlc-flow/tasks/demo'
        self.brief = self.write('brief.json', {'outcome': 'A and B work together',
                                'acceptance': [{'id': 'A1', 'text': 'A and B agree'}],
                                'constraints': ['Preserve private account scope.'],
                                'prohibited': ['Do not send messages.']})
        self.cli('init', '--repo', self.repo, '--brief', self.brief)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value))
        return path

    def command(self, *args):
        cmd = [sys.executable, str(SCRIPT), str(args[0]), '--task', str(self.task)]
        if args[0] not in {'context', 'status'}:
            cmd += ['--owner', 'main']
        if args[0] == 'ingest':
            cmd += ['--worker-ended']
        return cmd + [str(x) for x in args[1:]]

    def cli(self, *args, fail=None):
        proc = subprocess.run(self.command(*args), text=True, capture_output=True)
        if fail:
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            self.assertIn(fail, proc.stderr)
            return proc
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def state(self):
        return json.loads((self.task / 'state.json').read_text())

    def add(self, key='a', scope='src/a.py', dependencies=None, role='writer', shared_reads=None):
        workspace = self.root / ('workspace-' + key)
        shutil.copytree(self.repo, workspace, ignore=shutil.ignore_patterns('.sdlc-flow'))
        value = {'id': key, 'agent': 'worker-' + key, 'role': role, 'workspace': str(workspace),
                 'outcome': key + ' works', 'acceptance_ids': ['A1'], 'owned_paths': [scope],
                 'dependencies': dependencies or [], 'shared_reads': shared_reads or [], 'next_action': 'Implement and test.',
                 'metadata': {'agent_id': 'native-' + key}}
        path = self.write('assignment-' + key + '.json', value)
        self.cli('add', '--input', path)
        return workspace

    def result(self, key='a', status='complete'):
        row = self.state()['assignments'][key]
        actual = team.sources(Path(row['workspace']))
        paths = sorted(p for p in set(actual) | set(row['baseline']) if actual.get(p) != row['baseline'].get(p))
        value = {k: row[k] for k in ('task_id', 'generation', 'spec_revision', 'snapshot')}
        value.update(assignment_id=key, agent=row['agent'], status=status,
                     manifest=[{'path': p, 'sha256': actual[p]['sha256'] if p in actual else None,
                                'executable': actual[p]['executable'] if p in actual else None} for p in paths],
                     checks=[{'command': 'python -m check', 'result': 'passed',
                              'checked_files': [{'path': p, 'sha256': actual[p]['sha256']} for p in paths if p in actual]}],
                     limitations=[], next_action='Integrate and check combined outcome.')
        return value

    def running(self, key='a'):
        self.cli('transition', '--assignment', key, '--to', 'running')

    def integrate(self, key='a', value=None):
        row = self.state()['assignments'][key]
        value = value or json.loads((self.task / row['results'][-1]).read_text())
        for entry in value['manifest']:
            src = Path(row['workspace']) / entry['path']
            dst = self.repo / entry['path']
            if entry['sha256'] is None:
                dst.unlink()
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        proof = self.write('integration.json', {'manifest': value['manifest']})
        self.cli('transition', '--assignment', key, '--to', 'integrated', '--evidence', proof)

    def gate(self):
        fingerprint = self.cli('status')['source_fingerprint']
        ev = self.task / 'evidence/check.txt'
        ev.parent.mkdir(parents=True, exist_ok=True)
        ev.write_text('combined outcome passed\n')
        state = self.state()
        item = {'path': 'evidence/check.txt', 'sha256': team.digest(ev), 'result': 'passed',
                'source_fingerprint': fingerprint, 'spec_revision': state['spec_revision']}
        return {'task_id': state['task_id'], 'spec_revision': state['spec_revision'],
                'source_fingerprint': fingerprint, 'acceptance': {'A1': [item]},
                'review': {'independent': True, 'reviewer': 'fresh-reviewer', 'context_id': 'new-session',
                           'spec_revision': state['spec_revision'], 'source_fingerprint': fingerprint, 'evidence': [item]}}

    def test_status_omits_large_baselines_and_preserves_assignment_contract(self):
        inventory = self.repo / 'inventory'
        inventory.mkdir()
        for number in range(200):
            (inventory / ('source_%04d.py' % number)).write_text('value = %d\n' % number)
        self.add()
        self.running()
        proc = subprocess.run(self.command('status'), capture_output=True, text=True, check=True)
        status = json.loads(proc.stdout)
        canonical = self.state()['assignments']['a']
        self.assertEqual(status['assignments']['a'], {k: v for k, v in canonical.items() if k != 'baseline'})
        self.assertNotIn('baseline', status['assignments']['a'])
        self.assertEqual(len(canonical['baseline']), 202)
        with_baseline = dict(status, assignments={'a': canonical})
        previous_size = len(json.dumps(with_baseline, indent=2, sort_keys=True)) + 1
        self.assertLess(len(proc.stdout), previous_size // 10)
        # Persistence retains the full baseline required for manifest validation.
        self.assertEqual(self.state()['assignments']['a']['baseline'], canonical['baseline'])

    def test_initial_artifact_protection_and_owner(self):
        before = (self.task / 'state.json').read_bytes()
        self.cli('init', '--repo', self.repo, '--brief', self.brief, fail='already exists')
        self.cli('checkpoint', '--owner', 'impostor', fail='recorded orchestrator')
        self.assertEqual(before, (self.task / 'state.json').read_bytes())

    def test_ownership_prefix_isolation_unknown_dependency(self):
        self.add()
        ws = self.root / 'candidate'
        shutil.copytree(self.repo, ws, ignore=shutil.ignore_patterns('.sdlc-flow'))
        value = {'id': 'collision', 'agent': 'second', 'role': 'writer', 'workspace': str(ws),
                 'outcome': 'collision', 'acceptance_ids': ['A1'], 'owned_paths': ['src'],
                 'dependencies': [], 'next_action': 'work'}
        p = self.write('candidate.json', value)
        self.cli('add', '--input', p, fail='owned path conflict')
        value.update(owned_paths=['src/b.py'], dependencies=['missing'])
        self.cli('add', '--input', self.write('candidate.json', value), fail='unknown dependency')
        value.update(workspace=str(self.repo), dependencies=[])
        self.cli('add', '--input', self.write('candidate.json', value), fail='isolated workspace')
        with self.assertRaisesRegex(team.Invalid, 'cycle'):
            team.graph_valid({'a': {'dependencies': ['b']}, 'b': {'dependencies': ['a']}})
        self.assertEqual(set(self.state()['assignments']), {'a'})

    def test_scope_manifest_checked_sources_and_stale_generation(self):
        ws = self.add()
        self.running()
        (ws / 'src/a.py').write_text('a = 2\n')
        value = self.result()
        stale = dict(value, generation=0)
        self.cli('ingest', '--input', self.write('stale.json', stale), fail='generation')
        (ws / 'unexpected.txt').write_text('unaccounted')
        self.cli('ingest', '--input', self.write('result.json', value), fail='unaccounted')
        outside = self.result()
        self.cli('ingest', '--input', self.write('result.json', outside), fail='owned scope')
        (ws / 'unexpected.txt').unlink()
        value['checks'][0]['checked_files'][0]['sha256'] = 'old'
        self.cli('ingest', '--input', self.write('result.json', value), fail='stale workspace')
        self.cli('transition', '--assignment', 'a', '--to', 'verified', fail='not verification')

    def test_partial_resume_retains_unintegrated_changes_and_inbox(self):
        ws = self.add(scope='src')
        self.running()
        (ws / 'src/a.py').write_text('a = 2\n')
        first = self.result(status='partial')
        self.cli('ingest', '--input', self.write('first.json', first))
        inbox = self.task / 'inbox/worker-a/a-g1.json'
        original = inbox.read_bytes()
        self.cli('transition', '--assignment', 'a', '--to', 'ready')
        self.running()
        (ws / 'src/b.py').write_text('b = 2\n')
        final = self.result()
        self.assertEqual([x['path'] for x in final['manifest']], ['src/a.py', 'src/b.py'])
        self.cli('ingest', '--input', self.write('final.json', final))
        self.assertEqual(original, inbox.read_bytes())
        self.assertTrue((self.task / 'inbox/worker-a/a-g2.json').is_file())

    def test_dependencies_integration_and_complete_gate_freshness(self):
        ws = self.add()
        self.add('b', 'src/b.py', ['a'])
        self.cli('transition', '--assignment', 'b', '--to', 'running', fail='invalid transition')
        self.running()
        (ws / 'src/a.py').write_text('a = 2\n')
        self.cli('ingest', '--input', self.write('result.json', self.result()))
        proof = self.write('integration.json', {'manifest': self.result()['manifest']})
        self.cli('transition', '--assignment', 'a', '--to', 'integrated', '--evidence', proof, fail='does not match')
        self.integrate()
        self.cli('transition', '--assignment', 'b', '--to', 'ready')
        self.cli('transition', '--assignment', 'b', '--to', 'running', fail='lacks integrated dependency')
        wb = Path(self.state()['assignments']['b']['workspace'])
        shutil.copy2(self.repo / 'src/a.py', wb / 'src/a.py')
        self.running('b')
        # Individual slice tests passed, but combined integration has not been checked.
        self.cli('gate', '--input', self.write('gate.json', self.gate()), fail='not integrated')
        wb = Path(self.state()['assignments']['b']['workspace'])
        (wb / 'src/b.py').write_text('b = 2\n')
        self.cli('ingest', '--input', self.write('b-result.json', self.result('b')))
        self.integrate('b')
        gate = self.gate()
        bad = dict(gate, acceptance={})
        self.cli('gate', '--input', self.write('bad-gate.json', bad), fail='acceptance IDs')
        bad = dict(gate, acceptance={'A1': [dict(gate['acceptance']['A1'][0], result='failed')]})
        self.cli('gate', '--input', self.write('bad-gate.json', bad), fail='must have passed')
        bad = dict(gate, acceptance={'A1': [dict(gate['acceptance']['A1'][0], source_fingerprint='stale')]})
        self.cli('gate', '--input', self.write('bad-gate.json', bad), fail='obsolete source')
        bad = dict(gate, review=dict(gate['review'], reviewer='native-a'))
        self.cli('gate', '--input', self.write('bad-gate.json', bad), fail='independent')
        bad = dict(gate, review=dict(gate['review'], reviewer='worker-a'))
        self.cli('gate', '--input', self.write('bad-gate.json', bad), fail='independent')
        self.cli('gate', '--input', self.write('gate.json', gate))
        self.assertTrue(self.cli('status')['complete'])
        (self.task / 'evidence/check.txt').write_text('different evidence')
        self.assertFalse(self.cli('status')['complete'])
        gate = self.gate()
        self.cli('gate', '--input', self.write('gate.json', gate))
        (self.repo / 'untracked.txt').write_text('new relevant source')
        self.assertFalse(self.cli('status')['complete'])
        self.cli('gate', '--input', self.write('gate.json', gate), fail='stale integrated')

    def test_memory_freshness_requirements_context_and_live_recovery(self):
        self.add()
        self.running()
        fact = {'id': 'F1', 'kind': 'fact', 'text': 'A is one.', 'confidence': 'high', 'scope': ['src'],
                'sources': [{'path': 'src/a.py', 'sha256': team.digest(self.repo / 'src/a.py')}]}
        self.cli('memory', '--input', self.write('facts.json', [fact]))
        context = self.cli('context', '--assignment', 'a', '--max-chars', 10000)
        self.assertEqual(context['facts'][0]['id'], 'F1')
        self.assertIn('Do not send messages.', context['brief']['prohibited'])
        self.cli('context', '--assignment', 'a', '--max-chars', 30, fail='mandatory requirements')
        (self.repo / 'src/a.py').write_text('a = 99\n')
        self.assertEqual(self.cli('status')['facts'][0]['status'], 'stale')
        self.assertEqual(self.cli('context', '--assignment', 'a', '--max-chars', 10000)['facts'], [])
        self.cli('checkpoint')
        saved = list((self.task / 'checkpoints').glob('*.json'))[0]
        self.assertTrue(json.loads(saved.read_text())['assignments']['a']['live'])
        self.assertEqual(self.state()['facts'][0]['status'], 'stale')
        self.cli('revise', '--brief', self.brief)
        self.assertEqual(self.state()['assignments']['a']['state'], 'obsolete')
        self.assertTrue(self.state()['assignments']['a']['live'])
        ws = self.root / 'new-workspace'
        shutil.copytree(self.repo, ws, ignore=shutil.ignore_patterns('.sdlc-flow'))
        value = {'id': 'new', 'agent': 'new-worker', 'role': 'writer', 'workspace': str(ws),
                 'outcome': 'new', 'acceptance_ids': ['A1'], 'owned_paths': ['src/a.py'],
                 'next_action': 'work'}
        self.cli('add', '--input', self.write('new.json', value), fail='owned path conflict')
        ended = self.write('ended.json', {'worker_ended': True, 'agent': 'worker-a', 'generation': 1})
        self.cli('transition', '--assignment', 'a', '--to', 'obsolete', '--evidence', ended)
        self.cli('add', '--input', self.write('new.json', value))

    def test_concurrent_cas_preserves_winner_and_lock_releases_after_crash(self):
        rev = self.state()['revision']
        commands = [subprocess.Popen(self.command('checkpoint', '--expect-revision', rev),
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
        outputs = [p.communicate(timeout=10) for p in commands]
        self.assertEqual(sorted(p.returncode for p in commands), [0, 2])
        self.assertIn('revision conflict', ''.join(err for _, err in outputs))
        self.assertEqual(self.state()['revision'], rev + 1)
        # Abrupt death releases the OS lock; orphan atomic-write temporary files are not authority.
        script = 'import fcntl,time; f=open(%r,"r+"); fcntl.flock(f,fcntl.LOCK_EX); print("locked",flush=True); time.sleep(60)' % str(self.task / '.lock')
        if os.name != 'nt':
            holder = subprocess.Popen([sys.executable, '-c', script], stdout=subprocess.PIPE, text=True)
            self.assertEqual(holder.stdout.readline().strip(), 'locked')
            holder.kill()
            holder.wait(timeout=5)
            holder.stdout.close()
        (self.task / '.pending-crashed').write_text('{ incomplete')
        self.cli('checkpoint')
        self.assertEqual(self.state()['revision'], rev + 2)

    def test_fingerprint_excludes_artifacts_caches_and_checks_untracked(self):
        original = self.cli('status')['source_fingerprint']
        for directory in ('node_modules', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'dist', 'build'):
            p = self.repo / directory
            p.mkdir()
            (p / 'data').write_text('large generated dependency')
        (self.task / 'evidence').mkdir()
        (self.task / 'evidence/log').write_text('check output')
        self.assertEqual(self.cli('status')['source_fingerprint'], original)
        (self.repo / '.coverage').write_text('generated coverage')
        self.assertEqual(self.cli('status')['source_fingerprint'], original)
        (self.repo / 'untracked.py').write_text('relevant')
        self.assertNotEqual(self.cli('status')['source_fingerprint'], original)

    def test_shared_interface_staleness_and_exact_context_budget(self):
        ws = self.add(shared_reads=['src/b.py'])
        packet = self.cli('context', '--assignment', 'a', '--max-chars', 10000)
        required = len(json.dumps(packet, indent=2, sort_keys=True)) + 1
        response = subprocess.run(self.command('context', '--assignment', 'a', '--max-chars', required),
                                  capture_output=True, text=True)
        self.assertEqual(response.returncode, 0, response.stderr)
        self.assertEqual(len(response.stdout), required)
        self.cli('context', '--assignment', 'a', '--max-chars', required - 1, fail='mandatory requirements')
        self.running()
        (ws / 'src/a.py').write_text('a = 2\n')
        value = self.result()
        value['checks'][0]['checked_files'].append({'path': 'src/b.py', 'sha256': team.digest(ws / 'src/b.py')})
        (self.repo / 'src/b.py').write_text('b = 9\n')
        self.cli('ingest', '--input', self.write('stale-interface.json', value), fail='stale shared-read')
        (self.repo / 'src/b.py').write_text('b = 1\n')
        self.cli('ingest', '--input', self.write('result.json', value))
        shutil.copy2(ws / 'src/a.py', self.repo / 'src/a.py')
        (self.repo / 'src/b.py').write_text('b = 9\n')
        proof = self.write('integration.json', {'manifest': value['manifest']})
        self.cli('transition', '--assignment', 'a', '--to', 'integrated', '--evidence', proof, fail='stale shared-read')

    def test_live_partial_result_cannot_reclaim_and_shared_decision_is_mandatory(self):
        ws = self.add(shared_reads=['src/b.py'])
        decision = {'id': 'D1', 'kind': 'decision', 'text': 'B is the shared interface authority.',
                    'confidence': 'high', 'scope': ['src/b.py'],
                    'sources': [{'path': 'src/b.py', 'sha256': team.digest(self.repo / 'src/b.py')}] }
        self.cli('memory', '--input', self.write('decision.json', [decision]))
        packet = self.cli('context', '--assignment', 'a', '--max-chars', 10000)
        self.assertEqual(packet['facts'][0]['id'], 'D1')
        required = len(json.dumps(packet, indent=2, sort_keys=True)) + 1
        self.cli('context', '--assignment', 'a', '--max-chars', required - 1, fail='mandatory requirements')
        self.running()
        (ws / 'src/a.py').write_text('a = 2\n')
        value = self.result(status='partial')
        cmd = self.command('ingest', '--input', self.write('live-partial.json', value))
        cmd.remove('--worker-ended')
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(self.state()['assignments']['a']['live'])
        self.cli('transition', '--assignment', 'a', '--to', 'ready', fail='live worker')
        self.cli('checkpoint')
        self.assertTrue(self.state()['assignments']['a']['live'])
        ended = self.write('ended.json', {'worker_ended': True, 'agent': 'worker-a', 'generation': 1})
        self.cli('transition', '--assignment', 'a', '--to', 'review', '--evidence', ended)
        self.cli('transition', '--assignment', 'a', '--to', 'ready')
        self.assertEqual(self.state()['assignments']['a']['generation'], 2)

    def test_concurrent_results_preserve_both_workers_and_immutable_hash(self):
        wa = self.add()
        wb = self.add('b', 'src/b.py')
        self.running()
        self.running('b')
        (wa / 'src/a.py').write_text('a = 2\n')
        (wb / 'src/b.py').write_text('b = 2\n')
        inputs = [self.write(k + '-result.json', self.result(k)) for k in ('a', 'b')]
        procs = [subprocess.Popen(self.command('ingest', '--input', p), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for p in inputs]
        results = [p.communicate(timeout=10) for p in procs]
        self.assertEqual([p.returncode for p in procs], [0, 0], results)
        self.assertEqual([self.state()['assignments'][k]['state'] for k in ('a', 'b')], ['review', 'review'])
        row = self.state()['assignments']['a']
        inbox = self.task / row['results'][-1]
        value = json.loads(inbox.read_text())
        value['next_action'] = 'tampered'
        inbox.write_text(json.dumps(value))
        proof = self.write('integration.json', {'manifest': value['manifest']})
        self.cli('transition', '--assignment', 'a', '--to', 'integrated', '--evidence', proof, fail='artifact changed')

    def test_mode_change_and_hardlink_copy_are_accounted(self):
        ws = self.add()
        self.running()
        path = ws / 'src/a.py'
        path.chmod(path.stat().st_mode | 0o111)
        value = self.result()
        self.assertTrue(value['manifest'][0]['executable'])
        wrong = dict(value, manifest=[dict(value['manifest'][0], executable=False)])
        self.cli('ingest', '--input', self.write('wrong-mode.json', wrong), fail='executable mode')
        self.cli('ingest', '--input', self.write('result.json', value))
        self.integrate()
        self.assertTrue((self.repo / 'src/a.py').stat().st_mode & 0o111)
        linked = self.root / 'hardlink-copy'
        shutil.copytree(self.repo, linked, copy_function=os.link, ignore=shutil.ignore_patterns('.sdlc-flow'))
        assignment = {'id': 'linked', 'agent': 'linked-worker', 'role': 'writer', 'workspace': str(linked),
                      'outcome': 'isolated work', 'acceptance_ids': ['A1'], 'owned_paths': ['src/b.py'], 'next_action': 'implement'}
        self.cli('add', '--input', self.write('linked.json', assignment), fail='hardlinked')

    def test_git_inventory_preserves_tracked_dist_and_ignores_runtime(self):
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        (self.repo / '.gitignore').write_text('ignored-runtime/\n')
        dist = self.repo / 'dist'
        dist.mkdir()
        (dist / 'shipped.py').write_text('tracked generated source')
        subprocess.run(['git', '-C', str(self.repo), 'add', '.gitignore', 'src', 'dist'], check=True)
        before = self.cli('status')['source_fingerprint']
        runtime = self.repo / 'ignored-runtime'
        runtime.mkdir()
        (runtime / 'output').write_text('runtime output')
        self.assertEqual(self.cli('status')['source_fingerprint'], before)
        (dist / 'shipped.py').write_text('changed tracked source')
        self.assertNotEqual(self.cli('status')['source_fingerprint'], before)

    def test_artifact_traversal_symlinks_and_provider_identity(self):
        self.add()
        self.running()
        value = self.result()
        value['manifest'] = [{'path': '../outside', 'sha256': None}]
        self.cli('ingest', '--input', self.write('traversal.json', value), fail='unsafe')
        external = self.root / 'outside'
        external.mkdir()
        (self.task / 'inbox').mkdir()
        (self.task / 'inbox/worker-a').symlink_to(external, target_is_directory=True)
        self.cli('ingest', '--input', self.write('result.json', self.result()), fail='escapes')
        self.assertEqual(list(external.iterdir()), [])
        self.assertEqual(self.state()['assignments']['a']['state'], 'running')
        with self.assertRaisesRegex(team.Invalid, 'host/provider'):
            team.metadata({'reported_model': 'claimed-by-worker'})
        self.assertEqual(team.metadata({})['usage'], 'unknown')


if __name__ == '__main__':
    unittest.main()
