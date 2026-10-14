from enigma import eDVBFrontendParameters, eDVBFrontendParametersSatellite as Sat, eDVBResourceManager

from Components.NimManager import nimmanager

from .conf import BEACONS
from .table import ORBIT


def satellite_sockets(orbpos=ORBIT):
    found = []
    for unit in nimmanager.nim_slots:
        try:
            if not unit.isCompatible("DVB-S") or (hasattr(unit, "isFBCLink") and unit.isFBCLink()):
                continue
            if orbpos in [entry[0] for entry in nimmanager.getSatListForNim(unit.slot)]:
                found.append(unit.slot)
        except Exception:
            continue
    return found


def letter(slot):
    return chr(65 + slot)


def describe_mode(mode):
    if isinstance(mode, tuple):
        return "kayitli (%s)" % ("DVB-S2" if mode[5] else "DVB-S")
    return "DVB-S2" if mode == "s2" else "DVB-S"


def _parameters(freq, pol, sr, system):
    p = Sat()
    p.inversion = Sat.Inversion_Unknown
    p.orbital_position = ORBIT
    if isinstance(system, tuple):
        _, khz, baud, plane, inner, gen, mode, roll, pilot = system
        p.frequency, p.symbol_rate, p.polarisation, p.fec = khz, baud, plane, inner
        p.system = Sat.System_DVB_S2 if gen else Sat.System_DVB_S
        p.modulation = mode if gen else Sat.Modulation_QPSK
        p.rolloff = roll if gen else Sat.RollOff_alpha_0_35
        p.pilot = pilot if gen else Sat.Pilot_Off
    else:
        p.frequency = int(freq) * 1000
        p.symbol_rate = int(sr) * 1000
        p.polarisation = Sat.Polarisation_Vertical if pol == "V" else Sat.Polarisation_Horizontal
        p.fec = Sat.FEC_3_4
        p.modulation = Sat.Modulation_QPSK
        p.rolloff = Sat.RollOff_alpha_0_35
        second = system == "s2"
        p.system = Sat.System_DVB_S2 if second else Sat.System_DVB_S
        p.pilot = Sat.Pilot_Unknown if second else Sat.Pilot_Off
    for name, value in (("is_id", -1), ("pls_mode", 0), ("pls_code", 0), ("t2mi_plp_id", -1), ("t2mi_pid", 4096)):
        if hasattr(p, name):
            try:
                setattr(p, name, value)
            except Exception:
                pass
    return p


def _last(value):
    return value[-1] if isinstance(value, tuple) else value


class Frontend(object):
    def __init__(self, socket):
        self.socket = socket
        self.channel = None
        self.handle = None

    @classmethod
    def grab(cls, candidates):
        for slot in candidates:
            fe = cls(slot)
            if fe.acquire():
                return fe
        return None

    def acquire(self):
        try:
            manager = eDVBResourceManager.getInstance()
            self.channel = _last(manager and manager.allocateRawChannel(self.socket))
            self.handle = _last(self.channel and self.channel.getFrontend())
        except Exception:
            self.channel = self.handle = None
        if not self.handle:
            self.release()
            return False
        return True

    def aim(self, freq, pol, sr, system):
        params = eDVBFrontendParameters()
        try:
            params.setDVBS(_parameters(freq, pol, sr, system), False)
        except TypeError:
            params.setDVBS(_parameters(freq, pol, sr, system))
        self.handle.tune(params)

    def readout(self):
        try:
            holder = {}
            answer = self.handle.getFrontendStatus(holder)
            return answer if isinstance(answer, dict) else holder
        except Exception:
            return {}

    def lock_state(self):
        return self.readout().get("tuner_state")

    def reserve(self):
        try:
            return _last(self.channel.reserveDemux())
        except Exception:
            return -1

    def release(self):
        self.handle = None
        self.channel = None


class Meter(object):
    __slots__ = ("locked", "quality", "power", "db")

    def __init__(self, locked, quality, power, db):
        self.locked, self.quality, self.power, self.db = locked, quality, power, db

    @staticmethod
    def _percent(raw):
        if raw is None:
            return None
        try:
            raw = int(raw)
        except (TypeError, ValueError):
            return None
        return max(0, min(100, raw * 100 // 65536 if raw > 100 else raw))

    @classmethod
    def read(cls, status):
        if not status:
            return None
        db = status.get("tuner_signal_quality_db")
        try:
            db = None if db is None else int(db) / 100.0
        except (TypeError, ValueError):
            db = None
        return cls(status.get("tuner_state") == "LOCKED" or bool(status.get("tuner_locked")),
                   cls._percent(status.get("tuner_signal_quality")),
                   cls._percent(status.get("tuner_signal_power")), db)
