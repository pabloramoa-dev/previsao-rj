"""Timing, framing and fail-before-delivery checks for HyperFrames."""
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hf', ROOT/'video/compositor.py')
hf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hf)

class HyperFramesTests(unittest.TestCase):
    def test_invalid_times_rejected(self):
        for duration, cuts in [(0, []), (math.nan, []), (2, [-1]), (2, [2]), (2, [math.inf])]:
            with self.assertRaises(ValueError):
                hf.timeline(duration, cuts)

    def test_cuts_sorted_and_deduplicated(self):
        self.assertEqual(hf.timeline(3, [2, 1, 1, 0]), (3., [1., 2.]))

    def test_weather_data_not_cropped_or_scaled(self):
        with tempfile.TemporaryDirectory() as d:
            for style in ['rj', 'vr']:
                page = hf.composition(d, 10, 1080, 1920, [3, 6], style)
                self.assertIn('object-fit:contain', page)
                self.assertNotIn('scale:.992', page)
                self.assertIn('data-duration="10.0"', page)
                self.assertNotIn('caption', page)
                self.assertIn('assets/mix.wav', page)

    def test_missing_runtime_does_not_modify_source(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)/'source.mp4'
            source.write_bytes(b'original')
            with self.assertRaises(FileNotFoundError):
                hf.apply(source, root=Path(d))
            self.assertEqual(source.read_bytes(), b'original')

    def test_wrong_duration_rejected(self):
        info = {'streams': [
            {'codec_type':'video','width':1080,'height':1920,'codec_name':'h264','avg_frame_rate':'30/1'},
            {'codec_type':'audio','codec_name':'aac'}],
            'format':{'duration':'6'}}
        with patch.object(hf, 'probe', return_value=info):
            with self.assertRaises(ValueError):
                hf.validate('test.mp4', 2, 1080, 1920)

if __name__ == '__main__':
    unittest.main()
