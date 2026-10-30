"""Pure alarm policy, configuration and CANoe read helpers."""
from dataclasses import dataclass, field, asdict
import math

COLORS = {'error': '#FF0000', 'water': '#00FFFF', 'disk': '#FFFF00', 'running': '#00FF00', 'idle': '#000000', 'unknown': '#000000'}
LABELS = {'error': 'CANoe error / latched stop', 'water': 'Chamber DI water low', 'disk': 'Disk space warning', 'running': 'CANoe running', 'idle': 'CANoe stopped normally', 'unknown': 'Monitoring unavailable'}

@dataclass
class Config:
    disk_enabled: bool = True
    disk_path: str = 'C:\\'
    disk_free_gb: float = 10.0
    disk_free_percent: float = 5.0
    error_enabled: bool = False
    error_variable: str = 'LabBeacon::Error'
    error_value: float = 1.0
    water_enabled: bool = False
    water_variable: str = 'LabBeacon::DIWaterLow'
    water_value: float = 1.0
    any_stop_error: bool = False
    brightness: int = 98
    rules: dict = field(default_factory=lambda: {
        k: {'enabled': True, 'mode': 'Solid' if k == 'running' else 'Blink', 'interval_ms': 500}
        for k in ('error', 'water', 'disk', 'running')})

    def validate(self):
        for value in (self.disk_free_gb, self.disk_free_percent, self.error_value, self.water_value):
            if not math.isfinite(float(value)):
                raise ValueError('Numeric values must be finite')
        if not 0 <= self.disk_free_percent <= 100 or self.disk_free_gb < 0:
            raise ValueError('Disk thresholds: GB >= 0 and percent 0..100')
        if not 1 <= self.brightness <= 100:
            raise ValueError('Brightness must be 1..100')
        if self.disk_enabled and not self.disk_path.strip():
            raise ValueError('Choose a disk path')
        for enabled, path in ((self.error_enabled, self.error_variable), (self.water_enabled, self.water_variable)):
            if enabled and (len(path.split('::')) < 2 or any(not p.strip() for p in path.split('::'))):
                raise ValueError('System variable format: Namespace::Name (nested namespaces supported)')
        for k in ('error', 'water', 'disk', 'running'):
            r = self.rules[k]
            if r['mode'] not in ('Solid', 'Blink') or not 250 <= int(r['interval_ms']) <= 3000:
                raise ValueError('Blink ON/OFF duration must be 250..3000 ms')
        return self

    def to_dict(self):
        return asdict(self)


def select_status(config, *, error=False, water=False, disk=False, running=False, known=True):
    for key, active in (('error', error), ('water', water), ('disk', disk)):
        if active and config.rules[key]['enabled']:
            return key
    if not known:
        return 'unknown'
    return 'running' if running and config.rules['running']['enabled'] else 'idle'


def disk_warning(free, total, config):
    return free / 1024**3 <= config.disk_free_gb or (total > 0 and free / total * 100 <= config.disk_free_percent)


def read_sysvar(app, path):
    parts = path.split('::')
    ns = app.System
    for name in parts[:-1]:
        ns = ns.Namespaces.Item(name)
    return float(ns.Variables.Item(parts[-1]).Value)


class ErrorLatch:
    def __init__(self):
        self.active = False
        self.previous_running = None

    def update(self, running, error, any_stop=False):
        if error or (any_stop and self.previous_running is True and running is False):
            self.active = True
        # Do not infer a stop from a disconnected/unknown sample.
        self.previous_running = running
        return self.active

    def acknowledge(self, live_error):
        if not live_error:
            self.active = False
        return self.active
