import unittest
from unittest.mock import Mock, patch
from canoe_attach import attach_existing, hresult_text, matching_rot_entries

class AttachTests(unittest.TestCase):
    def test_direct_uses_only_existing_object(self):
        com, dynamic = Mock(), Mock()
        app, method = attach_existing(com, dynamic)
        self.assertEqual(method, 'GetActiveObject')
        dynamic.Dispatch.assert_called_once_with(com.GetActiveObject.return_value)
        com.GetRunningObjectTable.assert_not_called()

    def test_rot_fallback_uses_existing_object(self):
        com, dynamic = Mock(), Mock()
        com.GetActiveObject.side_effect = Exception(-2147221021, 'Operation unavailable')
        rot, moniker = Mock(), Mock()
        with patch('canoe_attach.matching_rot_entries', return_value=(rot, [('CANoe.Application:123', moniker)])):
            app, method = attach_existing(com, dynamic)
        self.assertEqual(method, 'Running Object Table')
        rot.GetObject.assert_called_once_with(moniker)
        dynamic.Dispatch.assert_called_once_with(rot.GetObject.return_value.QueryInterface.return_value)

    def test_no_object_returns_actionable_error(self):
        com, dynamic = Mock(), Mock()
        com.GetActiveObject.side_effect = Exception(-2147221021, 'Operation unavailable')
        with patch('canoe_attach.matching_rot_entries', return_value=(Mock(), [])):
            with self.assertRaisesRegex(RuntimeError, '0x800401E3.*same Windows user/elevation'):
                attach_existing(com, dynamic)
        dynamic.Dispatch.assert_not_called()

    def test_ambiguous_rot_objects_are_rejected(self):
        com, dynamic = Mock(), Mock()
        com.GetActiveObject.side_effect = Exception('No object')
        with patch('canoe_attach.matching_rot_entries', return_value=(Mock(), [('CANoe:1', Mock()), ('CANoe:2', Mock())])):
            with self.assertRaisesRegex(RuntimeError, 'Multiple CANoe'):
                attach_existing(com, dynamic)

    def test_rot_filters_other_apps_and_plain_config_paths(self):
        com = Mock()
        names = ['Excel.Application', r'C:\\test\\CANoeConfig.cfg', 'CANoe.Application:12', '!{TEST-CLSID}']
        monikers = [Mock() for _ in names]
        for moniker, name in zip(monikers, names):
            moniker.GetDisplayName.return_value = name
        com.GetRunningObjectTable.return_value.EnumRunning.return_value = monikers
        _, entries = matching_rot_entries(com, {'{test-clsid}'})
        self.assertEqual([name for name, _ in entries], names[2:])

    def test_hresult_format(self):
        self.assertEqual(hresult_text(Exception(-2147221021, 'Operation unavailable')), '0x800401E3')
