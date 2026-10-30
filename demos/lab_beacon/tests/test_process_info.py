import os
import sys
import unittest

@unittest.skipUnless(sys.platform == 'win32', 'Windows token API required')
class ProcessInfoTests(unittest.TestCase):
    def test_current_process_token_session_and_path(self):
        from process_info import query_process
        data = query_process(os.getpid())
        self.assertEqual(data['pid'], os.getpid())
        self.assertIsInstance(data['elevated'], bool)
        self.assertIsInstance(data['session_id'], int)
        self.assertTrue(data['path'].lower().endswith('.exe'))
        self.assertNotIn('token_query_error', data)
