"""Structured native receipt regressions; no model/provider calls."""
import importlib.util
from pathlib import Path
import unittest

PROBE = Path(__file__).with_name('probe.py')
spec = importlib.util.spec_from_file_location('native_probe', PROBE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class NativeReceiptTests(unittest.TestCase):
    def test_exact_route_requires_known_root_not_worker_identity(self):
        expected = 'requested-root'
        receipt = probe.metadata([
            {'type': 'system', 'subtype': 'init', 'session_id': 'fresh', 'model': 'fallback-root'},
            {'type': 'assistant', 'parent_tool_use_id': 'worker',
             'message': {'model': expected, 'content': []}},
            {'type': 'result', 'subtype': 'success', 'usage': {},
             'modelUsage': {expected: {}}},
        ], 'claude')
        self.assertTrue(receipt['host_completed'])
        self.assertFalse(probe.route_compliance(receipt, expected)['pass'])
        self.assertFalse(probe.route_compliance({}, expected)['pass'])

    def test_root_response_model_cannot_hide_behind_alias(self):
        receipt = probe.metadata([
            {'type': 'system', 'subtype': 'init', 'model': 'declared-alias'},
            {'type': 'assistant', 'message': {'model': 'unexpected-provider-route', 'content': []}},
        ], 'claude')
        self.assertFalse(probe.route_compliance(receipt, 'declared-alias')['pass'])
        self.assertTrue(probe.route_compliance(receipt, 'declared-alias',
                        ['declared-alias', 'unexpected-provider-route'])['pass'])

    def test_forwarded_worker_model_is_correlated_and_separate(self):
        receipt = probe.metadata([
            {'type': 'system', 'subtype': 'init', 'model': 'root'},
            {'type': 'assistant', 'parent_tool_use_id': 'agent-a',
             'message': {'model': 'worker-a', 'content': []}},
            {'type': 'assistant', 'parent_tool_use_id': 'agent-b',
             'message': {'model': 'worker-b', 'content': []}},
        ], 'claude')
        self.assertEqual(receipt['worker_reported_models'],
                         {'agent-a': ['worker-a'], 'agent-b': ['worker-b']})
        self.assertTrue(probe.route_compliance(receipt, 'root')['pass'])
        self.assertIsNone(receipt['full_workflow_usage'])
        self.assertIsNone(receipt['reported_usage']['input_tokens'])

    def test_model_claim_in_prose_cannot_establish_identity(self):
        receipt = probe.metadata([
            {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'I am requested-root'}},
            {'type': 'turn.completed', 'usage': {'input_tokens': 12, 'output_tokens': 4}},
        ], 'codex')
        self.assertTrue(receipt['host_completed'])
        self.assertFalse(probe.route_compliance(receipt, 'requested-root')['pass'])
        self.assertEqual(receipt['reported_usage']['input_tokens'], 12)
        self.assertIsNone(receipt['full_workflow_usage'])


if __name__ == '__main__':
    unittest.main()
