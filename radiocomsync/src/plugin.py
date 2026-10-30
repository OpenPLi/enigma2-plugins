"""RadioComSync — sync radio commentary with TV video."""

from enigma import eTimer
from Plugins.Plugin import PluginDescriptor

PLUGIN_NAME = "RadioComSync"
PLUGIN_DESC = "Sync radio commentary with TV video"


class RadioMonitor:
    """Background monitor — stops radio audio on real channel changes.

    Polls the current service ref once per second. When radio is playing
    and the service ref changes (= user zapped), kills radio and restores
    TV audio. Polling is more reliable than ServiceEventTracker which
    doesn't always fire on zap.
    """
    instance = None

    def __init__(self, session):
        self.session = session
        self._last_sref = self._get_current_sref()
        self._timer = eTimer()
        self._timer.callback.append(self._check_channel)
        self._timer.start(1000)

    def _get_current_sref(self):
        try:
            ref = self.session.nav.getCurrentlyPlayingServiceReference()
            return ref.toString() if ref else None
        except Exception:
            return None

    def _check_channel(self):
        from . import player
        current = self._get_current_sref()
        if current and current != self._last_sref:
            if player.AUDIO_PROCESS:
                player.stopStation()
            self._last_sref = current


def sessionStart(reason, session, **kwargs):
    if reason == 0:
        # Kill any orphaned audio processes from previous session/reboot
        import subprocess
        subprocess.run(["killall", "-9", "gst-launch-1.0", "mpg123", "ffmpeg"],
                       stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        # Stop old timer if GUI restarted
        if RadioMonitor.instance:
            RadioMonitor.instance._timer.stop()
        RadioMonitor.instance = RadioMonitor(session)


def main(session, **kwargs):
    from .ui.station_list import StationListScreen
    session.open(StationListScreen)


def Plugins(**kwargs):
    return [
        PluginDescriptor(
            where=PluginDescriptor.WHERE_SESSIONSTART,
            fnc=sessionStart,
        ),
        PluginDescriptor(
            name=PLUGIN_NAME,
            description=PLUGIN_DESC,
            where=[PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU],
            icon=None,
            fnc=main,
        ),
    ]
