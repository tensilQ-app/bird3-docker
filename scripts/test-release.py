"""Security regression tests for stable release selection and URL validation."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
import urllib.error
import subprocess
spec = importlib.util.spec_from_file_location('release', Path(__file__).with_name('check-release.py'))
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)

class ReleaseTests(unittest.TestCase):
    def test_prereleases_excluded(self):
        page = '<b>BIRD 3.4.0</b> (tgz) BIRD 3.5.0-rc1 (tgz) BIRD 3.5.0beta (tgz) BIRD 3.5.0-beta (tgz) BIRD 2.20.0 (tgz) BIRD 3.04.0 (tgz)'
        self.assertEqual(release.stable_versions(page), {'3.4.0'})
    def test_redirect_boundaries(self):
        for url in ['http://bird.nic.cz/a', 'https://bird.nic.cz.evil.test/a', 'https://evil.test/a', 'https://user@bird.nic.cz/a']:
            with self.assertRaises(ValueError): release.check_url(url)
        release.check_url('https://pkg.labs.nic.cz/archive/bird/a')

class TransportTests(unittest.TestCase):
    @patch.object(release.time, 'sleep')
    @patch.object(release.urllib.request, 'build_opener')
    def test_page_retries_403_without_changing_endpoint(self, opener, sleep):
        client = opener.return_value
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.url = release.PAGE
        response.read.return_value = b'BIRD 3.4.0 (tgz)'
        client.open.side_effect = [urllib.error.HTTPError(release.PAGE, 403, 'Forbidden', {}, None), response]
        self.assertEqual(release.fetch_page(), 'BIRD 3.4.0 (tgz)')
        self.assertEqual(client.open.call_count, 2)
        for call in client.open.call_args_list:
            self.assertEqual(call.args, (release.PAGE,))
        sleep.assert_called_once_with(5)

    @patch.object(release.time, 'sleep')
    @patch.object(release.urllib.request, 'build_opener')
    def test_page_missing_is_not_retried(self, opener, sleep):
        opener.return_value.open.side_effect = urllib.error.HTTPError(release.PAGE, 404, 'Not found', {}, None)
        with self.assertRaises(urllib.error.HTTPError):
            release.fetch_page()
        sleep.assert_not_called()

    @patch.object(release.time, 'sleep')
    @patch.object(release.subprocess, 'run')
    def test_git_retries_are_bounded_and_fail_closed(self, run, sleep):
        run.return_value = subprocess.CompletedProcess(['git'], 128)
        with self.assertRaises(subprocess.CalledProcessError):
            release.fetch_tag('/tmp/source', 'v3.4.0')
        self.assertEqual(run.call_count, 8)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [5, 10, 15, 5, 10, 15])
        for index, call in enumerate(run.call_args_list):
            self.assertIn(release.GIT if index < 4 else release.MIRROR, call.args[0])
            self.assertIn('http.followRedirects=false', call.args[0])

    @patch.object(release.time, 'sleep')
    @patch.object(release.subprocess, 'run')
    def test_official_mirror_after_transport_failure(self, run, sleep):
        failure = subprocess.CompletedProcess(['git'], 128)
        success = subprocess.CompletedProcess(['git'], 0)
        run.side_effect = [failure] * 4 + [success]
        self.assertEqual(release.fetch_tag('/tmp/source', 'v3.4.0'), release.MIRROR)
        self.assertEqual(run.call_count, 5)
        self.assertIn(release.MIRROR, run.call_args.args[0])

    @patch.object(release.subprocess, 'run')
    def test_primary_success_does_not_use_mirror(self, run):
        run.return_value = subprocess.CompletedProcess(['git'], 0)
        self.assertEqual(release.fetch_tag('/tmp/source', 'v3.4.0'), release.GIT)
        run.assert_called_once()

if __name__ == '__main__': unittest.main()
