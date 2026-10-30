"""Regression tests for skip decisions and fail-closed public-registry reads."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

spec = importlib.util.spec_from_file_location('state', Path(__file__).with_name('rebuild-state.py'))
state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(state)


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.inputs = {'schema': 1, 'version': '3.4.0', 'architecture': 'amd64', 'base': 'sha256:base', 'packages': {'build': ['gcc-1', 'musl-1'], 'runtime': ['musl-1']}, 'packaging': 'recipe'}

    def test_unchanged_skips(self):
        a = state.fingerprint(self.inputs)
        self.assertFalse(state.decision(a, a))

    def test_any_input_change_rebuilds(self):
        previous = state.fingerprint(self.inputs)
        for key, value in [('version', '3.4.1'), ('architecture', 'arm64'), ('base', 'sha256:new'), ('packaging', 'changed'), ('packages', {'build': ['gcc-2', 'musl-1'], 'runtime': ['musl-1']})]:
            with self.subTest(key=key):
                current = dict(self.inputs, **{key: value})
                self.assertTrue(state.decision(state.fingerprint(current), previous))
        current = copy.deepcopy(self.inputs)
        current['packages']['runtime'] = ['musl-2']
        self.assertTrue(state.decision(state.fingerprint(current), previous))

    def test_force_and_first_baseline(self):
        digest = state.fingerprint(self.inputs)
        self.assertTrue(state.decision(digest, digest, force=True))
        self.assertTrue(state.decision(digest, ''))

    def test_serialization_order_does_not_trigger_rebuild(self):
        self.assertEqual(state.fingerprint(self.inputs), state.fingerprint(dict(reversed(list(self.inputs.items())))))

    def test_recipe_matches_both_actual_stages(self):
        base, groups = state.recipe()
        self.assertEqual(base, 'alpine:3.24')
        self.assertIn('build-base', groups['build'])
        self.assertIn('libssh', groups['runtime'])
        self.assertIn('libssh-dev', groups['build'])

    def test_unrecognized_recipe_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'Dockerfile'
            path.write_text('FROM alpine:edge AS build\n')
            with self.assertRaises(ValueError):
                state.recipe(path)


class RegistryTests(unittest.TestCase):
    def registry(self):
        return object.__new__(state.Registry)

    def test_only_missing_tag_is_baseline(self):
        for code in (401, 403, 429, 500):
            with self.subTest(code=code), patch.object(state.Registry, 'index', side_effect=urllib.error.HTTPError('https://ghcr.io/', code, 'error', {}, None)):
                with self.assertRaises(urllib.error.HTTPError):
                    self.registry().labels('3.4.0', 'amd64')
        with patch.object(state.Registry, 'index', side_effect=urllib.error.HTTPError('https://ghcr.io/', 404, 'missing', {}, None)):
            self.assertEqual(self.registry().labels('3.4.0', 'amd64'), {})

    def test_select_architecture_and_ignore_attestations(self):
        manifest = lambda arch, digest: {'platform': {'os': 'linux', 'architecture': arch}, 'digest': digest}
        index = {'manifests': [manifest('amd64', 'amd'), manifest('arm64', 'arm'), {'platform': {'os': 'unknown', 'architecture': 'unknown'}, 'digest': 'attestation'}]}
        with patch.object(state.Registry, 'index', return_value=(index, 'index')), patch.object(state.Registry, 'get', side_effect=[({'config': {'digest': 'config'}}, 'digest'), ({'config': {'Labels': {state.LABEL: 'expected'}}}, 'config')]) as get:
            self.assertEqual(self.registry().labels('3.4.0', 'arm64'), {state.LABEL: 'expected'})
            self.assertEqual(get.call_args_list[0].args, ('manifests', 'arm'))

    def test_missing_or_duplicate_platform_fails(self):
        for entries in ([], [{'platform': {'os': 'linux', 'architecture': 'amd64'}, 'digest': 'a'}] * 2):
            with patch.object(state.Registry, 'index', return_value=({'manifests': entries}, 'index')):
                with self.assertRaises(ValueError):
                    self.registry().labels('3.4.0', 'amd64')

    def test_missing_label_produces_one_baseline_rebuild(self):
        index = {'manifests': [{'platform': {'os': 'linux', 'architecture': 'amd64'}, 'digest': 'a'}]}
        with patch.object(state.Registry, 'index', return_value=(index, 'index')), patch.object(state.Registry, 'get', side_effect=[({'config': {'digest': 'config'}}, 'digest'), ({'config': {}}, 'config')]):
            self.assertEqual(self.registry().labels('3.4.0', 'amd64'), {})


if __name__ == '__main__':
    unittest.main()
