from enigma import eTimer

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Slider import Slider

from ..analyser import (
    get_tv_stream_url, start_capture, stop_capture,
    get_live_levels, analyse_delay, cleanup,
)
from ..player import playStation, stopStation, audioStop, audioStart
from ..config import (
    get_station_url, get_saved_delay, save_delay, save_stations, load_stations,
    get_capture_duration,
)


class AnalyserScreen(Screen):
    skin = """
        <screen name="RadioComSyncAnalyser" position="center,center" size="800,500"
                title="RadioComSync" backgroundColor="#20000000">

            <widget name="title_label" position="20,10" size="760,45"
                    font="Regular;32" foregroundColor="#00ffffff"
                    backgroundColor="#20000000" halign="center" />

            <widget name="tv_label" position="20,70" size="120,30"
                    font="Regular;24" foregroundColor="#0000ff00"
                    backgroundColor="#20000000" />
            <widget name="tv_meter" position="150,70" size="620,25"
                    borderWidth="1" />

            <widget name="radio_label" position="20,110" size="120,30"
                    font="Regular;24" foregroundColor="#000088ff"
                    backgroundColor="#20000000" />
            <widget name="radio_meter" position="150,110" size="620,25"
                    borderWidth="1" />

            <widget name="countdown_label" position="20,160" size="760,120"
                    font="Regular;72" foregroundColor="#00ffffff"
                    backgroundColor="#20000000" halign="center" valign="center" />

            <widget name="info_label" position="20,300" size="760,40"
                    font="Regular;28" foregroundColor="#00ffcc00"
                    backgroundColor="#20000000" halign="center" />

            <widget name="status_label" position="20,350" size="760,35"
                    font="Regular;24" foregroundColor="#00aaaaaa"
                    backgroundColor="#20000000" halign="center" />

            <widget name="buttons_label" position="20,450" size="760,35"
                    font="Regular;22" foregroundColor="#00ffcc00"
                    backgroundColor="#20000000" halign="center" />
        </screen>
    """

    MODE_IDLE = 0
    MODE_ANALYSING = 1
    MODE_RESULT = 2
    MODE_WAIT_PAUSE = 3
    MODE_COUNTDOWN = 4
    MODE_PLAYING = 5

    def __init__(self, session, station, skip_analysis=False):
        Screen.__init__(self, session)
        self.session = session
        self.station = station
        self.skip_analysis = skip_analysis
        self.mode = self.MODE_IDLE

        self._is_playing = False
        self._tv_proc = None
        self._radio_proc = None
        self._capture_seconds = get_capture_duration(station)
        self._elapsed = 0
        self._delay_seconds = 0
        self._countdown_remaining = 0

        # UI elements
        self["title_label"] = Label(station["name"])
        self["tv_label"] = Label("TV Audio")
        self["radio_label"] = Label("Radio")
        self["tv_meter"] = Slider(0, 100)
        self["radio_meter"] = Slider(0, 100)
        self["countdown_label"] = Label("")
        self["info_label"] = Label("")
        self["status_label"] = Label("")
        self["buttons_label"] = Label("")

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions"],
            {
                "ok": self._on_ok,
                "cancel": self._on_cancel,
                "left": self._on_left,
                "right": self._on_right,
            },
            -1,
        )

        # Timers
        self._tick_timer = eTimer()
        self._tick_timer.callback.append(self._on_tick)

        self._meter_timer = eTimer()
        self._meter_timer.callback.append(self._update_meters)

        # Start
        if skip_analysis:
            saved = get_saved_delay(station)
            if saved:
                self._delay_seconds = saved + station.get("fine_tune", 0)
                self._enter_wait_pause()
            else:
                self._start_analysis()
        else:
            self._start_analysis()

    def _start_analysis(self):
        """Begin audio capture and analysis."""
        self.mode = self.MODE_ANALYSING
        self._elapsed = 0

        tv_url = get_tv_stream_url(self.session)
        radio_url, source_type = get_station_url(self.station)

        if not tv_url or not radio_url:
            self["info_label"].setText("Error: Could not get audio sources")
            return

        self["info_label"].setText("Analysing audio...")
        self["buttons_label"].setText("")
        self._update_countdown_display()

        self._tv_proc, self._radio_proc = start_capture(tv_url, radio_url, self._capture_seconds)

        # Update meters every 200ms
        self._meter_timer.start(200, False)
        # Tick every second for countdown
        self._tick_timer.start(1000, False)

    def _on_tick(self):
        """Called every second during various modes."""
        if self.mode == self.MODE_ANALYSING:
            self._elapsed += 1
            self._update_countdown_display()

            if self._elapsed >= self._capture_seconds:
                self._finish_analysis()

        elif self.mode == self.MODE_COUNTDOWN:
            self._countdown_remaining -= 1
            self._update_countdown_display()

            if self._countdown_remaining <= 0:
                self._start_playback()

    def _update_countdown_display(self):
        """Update the large countdown display."""
        if self.mode == self.MODE_ANALYSING:
            remaining = self._capture_seconds - self._elapsed
            self["countdown_label"].setText(f"{remaining}s")
            self["status_label"].setText("Capturing audio from both sources...")

        elif self.mode == self.MODE_COUNTDOWN:
            mins = self._countdown_remaining // 60
            secs = self._countdown_remaining % 60
            if mins > 0:
                self["countdown_label"].setText(f"{mins}:{secs:02d}")
            else:
                self["countdown_label"].setText(f"{secs}s")

        elif self.mode == self.MODE_RESULT:
            delay = self._delay_seconds
            mins = int(delay) // 60
            secs = int(delay) % 60
            if mins > 0:
                self["countdown_label"].setText(f"{mins}m {secs:02d}s")
            else:
                self["countdown_label"].setText(f"{delay:.1f}s")

    def _update_meters(self):
        """Update audio level meters."""
        if self.mode == self.MODE_ANALYSING:
            tv_level, radio_level = get_live_levels()
            self["tv_meter"].setValue(tv_level)
            self["radio_meter"].setValue(radio_level)

    def _finish_analysis(self):
        """Stop capture and compute delay."""
        self._tick_timer.stop()
        self._meter_timer.stop()

        if self._tv_proc and self._radio_proc:
            stop_capture(self._tv_proc, self._radio_proc)
            self._tv_proc = None
            self._radio_proc = None

        self["status_label"].setText("Computing delay...")

        delay, confidence = analyse_delay()

        if delay is not None and confidence > 10:
            self._delay_seconds = delay
            self.mode = self.MODE_RESULT

            # Save the measured delay
            url, source_type = get_station_url(self.station)
            save_delay(self.station, delay, source_type)
            stations = load_stations()
            for i, s in enumerate(stations):
                if s["name"] == self.station["name"]:
                    stations[i] = self.station
                    break
            save_stations(stations)

            self._update_countdown_display()
            self["info_label"].setText(f"Radio delay detected (confidence: {confidence}%)")
            self["status_label"].setText("")
            self["buttons_label"].setText("OK: Proceed to sync  |  Cancel: Abort")
        else:
            self["countdown_label"].setText("?")
            self["info_label"].setText("Could not detect delay reliably")
            self["status_label"].setText("Try again during a louder moment (crowd, commentary)")
            self["buttons_label"].setText("OK: Try again  |  Cancel: Abort")
            self.mode = self.MODE_IDLE

        cleanup()

    def _enter_wait_pause(self):
        """Show instruction to pause timeshift."""
        self.mode = self.MODE_WAIT_PAUSE

        delay = self._delay_seconds
        mins = int(delay) // 60
        secs = int(delay) % 60
        if mins > 0:
            delay_str = f"{mins}m {secs:02d}s"
        else:
            delay_str = f"{delay:.1f}s"

        self["countdown_label"].setText(delay_str)
        self["info_label"].setText("Pause timeshift now, then press OK")
        self["status_label"].setText("")
        self["buttons_label"].setText("OK: Start countdown  |  Cancel: Abort")
        self["tv_meter"].setValue(0)
        self["radio_meter"].setValue(0)

    def _start_countdown(self):
        """Start the sync countdown timer."""
        self.mode = self.MODE_COUNTDOWN
        self._countdown_remaining = int(self._delay_seconds)

        self["info_label"].setText("Unpause timeshift when countdown reaches zero")
        self["buttons_label"].setText("")
        self._update_countdown_display()
        self._tick_timer.start(1000, False)

    def _start_playback(self):
        """Start radio playback."""
        self._tick_timer.stop()
        self.mode = self.MODE_PLAYING

        url, source_type = get_station_url(self.station)
        if url:
            stream_type = self.station.get("type", "MP3")
            playStation(url, stream_type=stream_type)
            self._is_playing = True

        adj = self.station.get("fine_tune", 0)
        adj_str = f" {adj:+d}s" if adj != 0 else ""

        self["countdown_label"].setText("Synced!")
        self["info_label"].setText(f"{self.station['name']}{adj_str}")
        self["status_label"].setText("Radio commentary synced")

        self["tv_label"].setText("")
        self["radio_label"].setText("")
        self["tv_meter"].setValue(0)
        self["radio_meter"].setValue(0)
        self["title_label"].setText(self.station["name"])
        self["buttons_label"].setText("Left/Right: Fine-tune +/-1s  |  Exit: Stop")

    def _on_ok(self):
        """Handle OK press based on current mode."""
        if self.mode == self.MODE_IDLE:
            # Retry analysis
            self._start_analysis()
        elif self.mode == self.MODE_RESULT:
            self._enter_wait_pause()
        elif self.mode == self.MODE_WAIT_PAUSE:
            self._start_countdown()
        elif self.mode == self.MODE_PLAYING:
            pass  # OK does nothing during playback

    def _on_cancel(self):
        """Handle Cancel/Exit."""
        self._cleanup_and_close()

    def _on_left(self):
        """Fine-tune: reduce delay by 1 second."""
        if self.mode == self.MODE_PLAYING:
            adj = self.station.get("fine_tune", 0) - 1
            self.station["fine_tune"] = adj
            stations = load_stations()
            for i, s in enumerate(stations):
                if s["name"] == self.station["name"]:
                    stations[i]["fine_tune"] = adj
                    break
            save_stations(stations)
            self["info_label"].setText(f"{self.station['name']} {adj:+d}s")

    def _on_right(self):
        """Fine-tune: increase delay by 1 second."""
        if self.mode == self.MODE_PLAYING:
            adj = self.station.get("fine_tune", 0) + 1
            self.station["fine_tune"] = adj
            stations = load_stations()
            for i, s in enumerate(stations):
                if s["name"] == self.station["name"]:
                    stations[i]["fine_tune"] = adj
                    break
            save_stations(stations)
            self["info_label"].setText(f"{self.station['name']} {adj:+d}s")

    def _cleanup_and_close(self):
        """Clean up everything and close."""
        self._tick_timer.stop()
        self._meter_timer.stop()

        if self._tv_proc or self._radio_proc:
            stop_capture(self._tv_proc, self._radio_proc)

        if self._is_playing:
            stopStation()
            self._is_playing = False

        cleanup()
        self.close()


