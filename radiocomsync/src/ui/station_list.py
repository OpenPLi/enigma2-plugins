"""Station list screen — modelled on Budweiser's SourceSelectionScreen."""

import threading
import time

from enigma import eTimer

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList

from ..config import load_stations, save_stations, get_station_url, get_saved_delay
from ..metadata import get_now_playing, _cache as metadata_cache, CACHE_TTL
from .. import player


class StationListScreen(Screen):
    skin = """
        <screen name="RadioComSyncStations" position="center,center" size="750,560"
                title="RadioComSync" backgroundColor="#20000000">
            <widget name="title_label" position="20,10" size="710,40"
                    font="Regular;30" foregroundColor="#00ffffff"
                    backgroundColor="#20000000" halign="center" />
            <widget name="mode_label" position="20,55" size="710,30"
                    font="Regular;24" foregroundColor="#0000ccff"
                    backgroundColor="#20000000" halign="center" />
            <widget name="stationlist" position="20,90" size="710,280"
                    font="Regular;26" itemHeight="40"
                    foregroundColor="#00ffffff" backgroundColor="#20000000"
                    scrollbarMode="showOnDemand" />
            <widget name="now_playing" position="20,375" size="710,60"
                    font="Regular;22" foregroundColor="#0000ff88"
                    backgroundColor="#20000000" halign="center" />
            <widget name="status" position="20,440" size="710,25"
                    font="Regular;20" foregroundColor="#00aaaaaa"
                    backgroundColor="#20000000" halign="center" />
            <ePixmap pixmap="buttons/red.png" position="20,470" size="35,25" alphatest="on" />
            <ePixmap pixmap="buttons/green.png" position="195,470" size="35,25" alphatest="on" />
            <ePixmap pixmap="buttons/yellow.png" position="370,470" size="35,25" alphatest="on" />
            <ePixmap pixmap="buttons/blue.png" position="570,470" size="35,25" alphatest="on" />
            <widget name="key_red" position="60,470" size="125,25"
                    font="Regular;20" foregroundColor="#00ffffff" backgroundColor="#20000000" />
            <widget name="key_green" position="235,470" size="125,25"
                    font="Regular;20" foregroundColor="#00ffffff" backgroundColor="#20000000" />
            <widget name="key_yellow" position="410,470" size="150,25"
                    font="Regular;20" foregroundColor="#00ffffff" backgroundColor="#20000000" />
            <widget name="key_blue" position="610,470" size="120,25"
                    font="Regular;20" foregroundColor="#00ffffff" backgroundColor="#20000000" />
            <widget name="help_label" position="20,505" size="710,40"
                    font="Regular;20" foregroundColor="#00888888"
                    backgroundColor="#20000000" halign="center" />
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.stations = load_stations()
        self._view_mode = "online"

        self["title_label"] = Label("RadioComSync")
        self["mode_label"] = Label("")
        self["stationlist"] = MenuList([])
        self["now_playing"] = Label("")
        self["status"] = Label("")
        self["key_red"] = Label("Stop Radio")
        self["key_green"] = Label("Satellite")
        self["key_yellow"] = Label("Analyse & Sync")
        self["key_blue"] = Label("Close")
        self["help_label"] = Label("OK: Play  |  Red: Stop  |  Blue: Close  |  Exit: Stop & Close")

        # Pre-populate from module-level metadata cache (only fresh entries)
        now = time.time()
        self._now_playing_cache = {}
        for name, (title, source, ts) in metadata_cache.items():
            if now - ts < CACHE_TTL:
                self._now_playing_cache[name] = title
        self._np_fetch_idx = 0
        self._filtered_stations = []
        self._fetch_thread = None

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "MenuActions"],
            {
                "ok": self._on_ok,
                "cancel": self._on_exit,
                "red": self._on_stop,
                "yellow": self._on_analyse,
                "green": self._on_toggle_view,
                "blue": self._on_close,
                "menu": self._on_settings,
            },
            -1,
        )

        self["stationlist"].onSelectionChanged.append(self._on_selection_changed)

        # Timer polls for results from the background thread
        self._np_timer = eTimer()
        self._np_timer.callback.append(self._check_fetch_result)

        self._build_list()
        self._start_next_fetch()

    @property
    def _playing(self):
        return player.AUDIO_PROCESS is not None

    def _get_filtered_stations(self):
        filtered = []
        for station in self.stations:
            if self._view_mode == "sat":
                if station.get("url_sat"):
                    filtered.append(station)
            else:
                if station.get("url_online"):
                    filtered.append(station)
        return filtered

    def _build_list(self):
        self._filtered_stations = self._get_filtered_stations()
        entries = []
        for station in self._filtered_stations:
            np = self._now_playing_cache.get(station["name"])
            if self._view_mode == "sat":
                delay = station.get("last_delay_sat")
            else:
                delay = station.get("last_delay_online")
            if np:
                entry = f"{station['name']} - {np[:40]}"
            elif delay is not None:
                mins = int(delay) // 60
                secs = int(delay) % 60
                delay_str = f"{mins}m {secs:02d}s" if mins > 0 else f"{secs}s"
                entry = f"{station['name']} -- delay: {delay_str}"
            else:
                entry = f"{station['name']}"
            entries.append(entry)
        self["stationlist"].setList(entries)
        if self._view_mode == "sat":
            self["mode_label"].setText("Satellite Radio Feeds")
            self["key_green"].setText("Online")
        else:
            self["mode_label"].setText("Online Radio Streams")
            self["key_green"].setText("Satellite")
        self._update_status()

    def _update_status(self):
        idx = self["stationlist"].getSelectedIndex()
        if idx is not None and idx < len(self._filtered_stations):
            station = self._filtered_stations[idx]
            np = self._now_playing_cache.get(station["name"])
            if np:
                self["now_playing"].setText(f"Now: {np}")
            else:
                self["now_playing"].setText("")
            if self._playing:
                self["status"].setText("Radio playing — press OK for different station, Exit to stop")
            else:
                self["status"].setText("")

    def _on_selection_changed(self):
        self._update_status()

    def _start_next_fetch(self):
        """Find the next uncached station and fetch in a background thread."""
        while self._np_fetch_idx < len(self.stations):
            station = self.stations[self._np_fetch_idx]
            if station["name"] not in self._now_playing_cache:
                break
            self._np_fetch_idx += 1

        if self._np_fetch_idx >= len(self.stations):
            self._build_list()
            self["now_playing"].setText("")
            self._update_status()
            return

        station = self.stations[self._np_fetch_idx]
        self._np_fetch_idx += 1
        self["now_playing"].setText(f"Checking: {station['name']}...")

        # Fetch in background thread to avoid blocking the UI
        self._fetch_result = None
        self._fetch_station_name = station["name"]
        self._fetch_thread = threading.Thread(
            target=self._fetch_worker, args=(station,), daemon=True
        )
        self._fetch_thread.start()
        # Poll every 200ms for the result
        self._np_timer.start(200, False)

    def _fetch_worker(self, station):
        """Runs in background thread — fetches now-playing metadata."""
        try:
            title, source = get_now_playing(station, self.session)
            self._fetch_result = (title, source)
        except Exception:
            self._fetch_result = (None, None)

    def _check_fetch_result(self):
        """Timer callback — checks if the background fetch is done."""
        if self._fetch_result is None:
            return  # Still running, timer will fire again

        self._np_timer.stop()
        title, source = self._fetch_result
        self._fetch_result = None
        self._fetch_thread = None

        if title:
            self._now_playing_cache[self._fetch_station_name] = title
            self._build_list()

        # Move to next station
        if self._np_fetch_idx < len(self.stations):
            self._start_next_fetch()
        else:
            self["now_playing"].setText("")
            self._update_status()

    def _get_selected_station(self):
        idx = self["stationlist"].getSelectedIndex()
        if idx is not None and idx < len(self._filtered_stations):
            return self._filtered_stations[idx], idx
        return None, None

    def _on_ok(self):
        """Play selected radio station."""
        station, idx = self._get_selected_station()
        if not station:
            return

        station["preferred"] = self._view_mode
        save_stations(self.stations)

        if self._view_mode == "sat":
            url = station.get("url_sat")
        else:
            url = station.get("url_online")

        if not url:
            return

        stream_type = station.get("type", "MP3")
        player.playStation(url, stream_type=stream_type)
        self["status"].setText(f"Playing: {station['name']}")
        self._update_status()

    def _on_stop(self):
        """Stop radio and restore TV audio."""
        player.stopStation()
        self["status"].setText("Radio stopped — TV audio restored")

    def _on_close(self):
        """Blue button — close screen, radio keeps playing."""
        self._np_timer.stop()
        self.close()

    def _on_exit(self):
        """Exit button — stop radio and close screen."""
        self._np_timer.stop()
        player.stopStation()
        self.close()

    def _on_analyse(self):
        """Open analyser screen for delay measurement."""
        station, idx = self._get_selected_station()
        if not station:
            return

        station["preferred"] = self._view_mode
        save_stations(self.stations)

        if self._playing:
            player.stopStation()

        if self._view_mode == "sat":
            delay = station.get("last_delay_sat")
        else:
            delay = station.get("last_delay_online")

        from .analyser_screen import AnalyserScreen
        self.session.openWithCallback(
            self._on_screen_closed, AnalyserScreen,
            station=station, skip_analysis=(delay is not None)
        )

    def _on_toggle_view(self):
        self._view_mode = "sat" if self._view_mode == "online" else "online"
        self._build_list()

    def _on_settings(self):
        from .settings import SettingsScreen
        self.session.openWithCallback(self._on_settings_closed, SettingsScreen)

    def _on_settings_closed(self, *args):
        self.stations = load_stations()
        self._build_list()

    def _on_screen_closed(self, *args):
        self.stations = load_stations()
        self._build_list()
