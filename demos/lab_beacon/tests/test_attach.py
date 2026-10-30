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

class ConnectionModeTests(unittest.TestCase):
    def test_normal_mode_never_activates(self):
        from canoe_attach import connect_once
        com, dynamic = Mock(), Mock()
        with patch('canoe_attach.attach_existing', side_effect=RuntimeError('missing')):
            with self.assertRaises(RuntimeError):
                connect_once(com, dynamic)
        com.CoCreateInstance.assert_not_called()

    def test_manual_activation_only_after_attach_fails(self):
        from canoe_attach import connect_once
        com, dynamic = Mock(), Mock()
        with patch('canoe_attach.attach_existing', side_effect=RuntimeError('missing')):
            app, method = connect_once(com, dynamic, activate=True)
        self.assertEqual(method, 'Manual COM activation')
        com.CoCreateInstance.assert_called_once_with(com.CLSIDFromProgID.return_value, None, com.CLSCTX_LOCAL_SERVER, com.IID_IDispatch)

    def test_manual_request_prefers_existing(self):
        from canoe_attach import connect_once
        com, dynamic, app = Mock(), Mock(), Mock()
        with patch('canoe_attach.attach_existing', return_value=(app, 'GetActiveObject')):
            self.assertEqual(connect_once(com, dynamic, activate=True), (app, 'GetActiveObject'))
        com.CoCreateInstance.assert_not_called()

    def test_ambiguity_does_not_activate(self):
        from canoe_attach import connect_once
        com, dynamic = Mock(), Mock()
        with patch('canoe_attach.attach_existing', side_effect=RuntimeError('Multiple CANoe objects found')):
            with self.assertRaises(RuntimeError):
                connect_once(com, dynamic, activate=True)
        com.CoCreateInstance.assert_not_called()

    def test_worker_reuses_proxy_and_consumes_activation_once(self):
        import sys, queue
        from unittest.mock import PropertyMock, call
        from monitor import canoe_worker
        from core import Config
        com = Mock()
        app1, app2 = Mock(), Mock()
        type(app1.Measurement).Running = PropertyMock(side_effect=[True, True, RuntimeError('RPC disconnected')])
        app2.Measurement.Running = False
        stop = Mock()
        stop.is_set.side_effect = [False, False, False, False, True]
        out = queue.Queue()
        cfg = Config().to_dict(); cfg['_activate_once'] = True
        with patch.dict(sys.modules, {'pythoncom': com, 'win32com': Mock(), 'win32com.client': Mock(dynamic=Mock())}):
            with patch('monitor.connect_once', side_effect=[(app1, 'Manual COM activation'), (app2, 'GetActiveObject')]) as connect:
                canoe_worker(out, stop, cfg)
        self.assertEqual(connect.call_count, 2)
        self.assertTrue(connect.call_args_list[0].kwargs['activate'])
        self.assertFalse(connect.call_args_list[1].kwargs['activate'])
        results = [out.get_nowait() for _ in range(4)]
        self.assertEqual([r['connected'] for r in results], [True, True, False, True])
        app1.Open.assert_not_called(); app1.Quit.assert_not_called()

    def test_failed_activation_not_repeated(self):
        import sys, queue
        from monitor import canoe_worker
        from core import Config
        cfg = Config().to_dict(); cfg['_activate_once'] = True
        stop = Mock(); stop.is_set.side_effect = [False, False, True]
        with patch.dict(sys.modules, {'pythoncom': Mock(), 'win32com': Mock(), 'win32com.client': Mock(dynamic=Mock())}):
            with patch('monitor.connect_once', side_effect=RuntimeError('Unavailable')) as connect:
                canoe_worker(queue.Queue(), stop, cfg)
        self.assertEqual([c.kwargs['activate'] for c in connect.call_args_list], [True, False])
