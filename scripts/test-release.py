"""Security regression tests for stable release selection and URL validation."""
import importlib.util
from pathlib import Path
import unittest
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

if __name__ == '__main__': unittest.main()
