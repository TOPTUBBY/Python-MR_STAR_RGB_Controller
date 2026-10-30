import asyncio
import itertools
import multiprocessing as mp
import queue
import unittest
from unittest.mock import Mock
from core import Config, ErrorLatch, select_status, disk_warning, read_sysvar
from monitor import canoe_worker
from protocol import brightness_frame, rgb_frame, power_frame
from ble_manager import BLEManager


class PolicyTests(unittest.TestCase):
    def test_all_alarm_combinations_priority(self):
        cfg = Config()
        for error, water, disk in itertools.product((False, True), repeat=3):
            expected = 'error' if error else 'water' if water else 'disk' if disk else 'running'
            self.assertEqual(select_status(cfg, error=error, water=water, disk=disk, running=True), expected)

    def test_disabled_rule_falls_through(self):
        cfg = Config()
        cfg.rules['error']['enabled'] = False
        self.assertEqual(select_status(cfg, error=True, water=True), 'water')

    def test_unknown_never_green(self):
        self.assertEqual(select_status(Config(), known=False, running=True), 'unknown')
        self.assertEqual(select_status(Config(), known=False, disk=True), 'disk')

    def test_normal_stop_is_off(self):
        latch = ErrorLatch()
        latch.update(True, False)
        self.assertFalse(latch.update(False, False))
        self.assertEqual(select_status(Config()), 'idle')

    def test_error_survives_stop_and_disconnect_until_ack(self):
        latch = ErrorLatch()
        latch.update(True, True)
        self.assertTrue(latch.update(False, False))
        self.assertTrue(latch.update(None, False))
        self.assertTrue(latch.acknowledge(True))
        self.assertFalse(latch.acknowledge(False))

    def test_optional_every_stop_and_disconnect(self):
        latch = ErrorLatch()
        latch.update(True, False, True)
        self.assertTrue(latch.update(False, False, True))
        latch = ErrorLatch()
        latch.update(True, False, True)
        latch.update(None, False, True)
        self.assertFalse(latch.update(False, False, True))

    def test_disk_gb_or_percent_threshold_and_recovery(self):
        cfg = Config(disk_free_gb=10, disk_free_percent=5)
        gb = 1024**3
        self.assertTrue(disk_warning(10*gb, 100*gb, cfg))
        self.assertTrue(disk_warning(20*gb, 1000*gb, cfg))
        self.assertFalse(disk_warning(20*gb, 100*gb, cfg))

    def test_settings_roundtrip_and_validation(self):
        cfg = Config()
        self.assertEqual(Config(**cfg.to_dict()).validate(), cfg)
        for cfg in (Config(brightness=0), Config(disk_free_percent=101), Config(error_enabled=True, error_variable='Bad'), Config(error_value=float('nan'))):
            with self.assertRaises(ValueError):
                cfg.validate()
        cfg = Config()
        cfg.rules['disk']['interval_ms'] = 100
        with self.assertRaises(ValueError):
            cfg.validate()

    def test_nested_namespace_read(self):
        app = Mock()
        app.System.Namespaces.Item.return_value.Namespaces.Item.return_value.Variables.Item.return_value.Value = 1
        self.assertEqual(read_sysvar(app, 'Chamber::Water::Low'), 1)
        app.System.Namespaces.Item.assert_called_once_with('Chamber')
        app.System.Namespaces.Item.return_value.Namespaces.Item.assert_called_once_with('Water')

    def test_attach_worker_with_fake_com(self):
        import sys
        from unittest.mock import patch
        pythoncom = Mock()
        app = Mock()
        app.Measurement.Running = True
        app.System.Namespaces.Item.return_value.Variables.Item.return_value.Value = 1
        dynamic = Mock()
        dynamic.Dispatch.return_value = app
        stop = Mock()
        stop.is_set.side_effect = [False, True]
        out = queue.Queue()
        cfg = Config(error_enabled=True)
        with patch.dict(sys.modules, {'pythoncom': pythoncom, 'win32com': Mock(), 'win32com.client': Mock(dynamic=dynamic)}):
            canoe_worker(out, stop, cfg.to_dict())
        result = out.get_nowait()
        self.assertTrue(result['running'])
        self.assertTrue(result['error'])
        pythoncom.GetActiveObject.assert_called_once_with('CANoe.Application')
        self.assertEqual(dynamic.Dispatch.call_args.args, (pythoncom.GetActiveObject.return_value,))
        app.Open.assert_not_called()
        app.Measurement.Start.assert_not_called()
        app.Quit.assert_not_called()


class BLETests(unittest.TestCase):
    def setUp(self):
        self.events = queue.Queue()
        self.ble = BLEManager(self.events, demo=True)
        self.ble.submit(self.ble._connect('DEMO:01')).result(3)
        self.packets = []
        async def record(char, packet, response=False):
            self.packets.append(packet)
        self.ble._client.write_gatt_char = record

    def tearDown(self):
        self.ble.shutdown()
        self.assertFalse(self.ble.thread.is_alive())

    def test_primary_98_percent_compatibility(self):
        self.ble.submit(self.ble._send_color((255, 0, 0), 100, 0)).result(3)
        self.assertEqual(self.packets, [power_frame(True), rgb_frame((255, 0, 0)), brightness_frame(98)])

    def test_blink_then_solid_cancels_old_pattern(self):
        self.ble.submit(self.ble._start_software_blink((255, 255, 0), 98, 0, 250)).result(3)
        self.ble.submit(asyncio.sleep(0.3)).result(2)
        self.assertIn(power_frame(False), self.packets)
        self.ble.submit(self.ble._send_color((0, 255, 255), 98, 0)).result(3)
        count = len(self.packets)
        self.ble.submit(asyncio.sleep(0.55)).result(2)
        self.assertEqual(len(self.packets), count)
        self.assertEqual(self.packets[-2], rgb_frame((0, 255, 255)))

    def test_overlapping_blink_and_solid_keeps_latest_command(self):
        async def slow_record(char, packet, response=False):
            await asyncio.sleep(0.07)
            self.packets.append(packet)
        self.ble._client.write_gatt_char = slow_record
        first = self.ble.submit(self.ble._start_software_blink((255, 0, 0), 98, 0, 250))
        last = self.ble.submit(self.ble._send_color((0, 255, 0), 98, 0))
        first.result(3)
        last.result(3)
        count = len(self.packets)
        self.ble.submit(asyncio.sleep(0.6)).result(2)
        self.assertEqual(len(self.packets), count)
        self.assertIsNone(self.ble._blink_task)

    def test_off_cancels_blink(self):
        self.ble.submit(self.ble._start_software_blink((0, 255, 0), 98, 0, 250)).result(3)
        self.ble.submit(self.ble._send_power(False)).result(3)
        count = len(self.packets)
        self.ble.submit(asyncio.sleep(0.55)).result(2)
        self.assertEqual(len(self.packets), count)
        self.assertEqual(self.packets[-1], power_frame(False))

if __name__ == '__main__':
    unittest.main()
