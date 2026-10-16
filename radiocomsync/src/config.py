import json
import os

CONFIG_FILE = "/etc/enigma2/radiocomsync_stations.json"

DEFAULT_STATIONS = [
    {
        "name": "talkSPORT",
        "url_online": "http://radio.talksport.com/stream",
        "url_sat": "http://127.0.0.1:8001/1:0:2:D79E:82F:2:11A0000:0:0:0:",
        "preferred": "sat",
        "type": "MP3",
        "last_delay_online": None,
        "last_delay_sat": None,
        "fine_tune": 0,
        "last_measured": None,
    },
    {
        "name": "talkSPORT 2",
        "url_online": "http://radio.talksport.com/stream2",
        "url_sat": None,
        "preferred": "online",
        "type": "MP3",
        "last_delay_online": None,
        "last_delay_sat": None,
        "fine_tune": 0,
        "last_measured": None,
    },
    {
        "name": "BBC 5 Live",
        "url_online": "http://as-hls-ww-live.akamaized.net/pool_89021708/live/ww/bbc_radio_five_live/bbc_radio_five_live.isml/bbc_radio_five_live-audio%3d96000.norewind.m3u8",
        "url_sat": "http://127.0.0.1:8001/1:0:2:2305:80D:2:11A0000:0:0:0:",
        "preferred": "sat",
        "type": "HLS",
        "last_delay_online": None,
        "last_delay_sat": None,
        "fine_tune": 0,
        "last_measured": None,
    },
    {
        "name": "BBC 5 Sports Extra",
        "url_online": "http://as-hls-ww-live.akamaized.net/pool_47700285/live/ww/bbc_radio_five_live_sports_extra/bbc_radio_five_live_sports_extra.isml/bbc_radio_five_live_sports_extra-audio%3d96000.norewind.m3u8",
        "url_sat": "http://127.0.0.1:8001/1:0:2:18C3:7FD:2:11A0000:0:0:0:",
        "preferred": "sat",
        "type": "HLS",
        "last_delay_online": None,
        "last_delay_sat": None,
        "fine_tune": 0,
        "last_measured": None,
    },
    {
        "name": "BBC Radio Ulster",
        "url_online": "http://as-hls-ww-live.akamaized.net/pool_31244774/live/ww/bbc_radio_ulster/bbc_radio_ulster.isml/bbc_radio_ulster-audio%3d96000.norewind.m3u8",
        "url_sat": None,
        "preferred": "online",
        "type": "HLS",
        "last_delay_online": None,
        "last_delay_sat": None,
        "fine_tune": 0,
        "last_measured": None,
    },
    {
        "name": "BBC Radio 4 (TMS)",
        "url_online": "http://as-hls-ww-live.akamaized.net/pool_55057080/live/ww/bbc_radio_fourfm/bbc_radio_fourfm.isml/bbc_radio_fourfm-audio%3d96000.norewind.m3u8",
        "url_sat": None,
        "preferred": "online",
        "type": "HLS",
        "last_delay_online": None,
        "last_delay_sat": None,
        "fine_tune": 0,
        "last_measured": None,
    },
    {
        "name": "BBC Sportsound Scotland",
        "url_online": "http://as-hls-ww-live.akamaized.net/pool_43322914/live/ww/bbc_radio_scotland_fm/bbc_radio_scotland_fm.isml/bbc_radio_scotland_fm-audio%3d96000.norewind.m3u8",
        "url_sat": None,
        "preferred": "online",
        "type": "HLS",
        "last_delay_online": None,
        "last_delay_sat": None,
        "fine_tune": 0,
        "last_measured": None,
    },
    {
        "name": "BBC World Service",
        "url_online": "http://as-hls-ww-live.akamaized.net/pool_87948813/live/ww/bbc_world_service/bbc_world_service.isml/bbc_world_service-audio%3d96000.norewind.m3u8",
        "url_sat": None,
        "preferred": "online",
        "type": "HLS",
        "last_delay_online": None,
        "last_delay_sat": None,
        "fine_tune": 0,
        "last_measured": None,
    },
    {
        "name": "WLR FM",
        "url_online": "https://playerservices.streamtheworld.com/api/livestream-redirect/WLR_FM.mp3",
        "url_sat": None,
        "preferred": "online",
        "type": "MP3",
        "last_delay_online": None,
        "last_delay_sat": None,
        "fine_tune": 0,
        "last_measured": None,
    },
    {
        "name": "RTE Radio 1",
        "url_online": "https://icecast.rte.ie/radio1",
        "url_sat": "http://127.0.0.1:8001/1:0:2:148D:7E7:2:11A0000:0:0:0:",
        "preferred": "sat",
        "type": "MP3",
        "last_delay_online": None,
        "last_delay_sat": None,
        "fine_tune": 0,
        "last_measured": None,
    },
    {
        "name": "RTE 2FM",
        "url_online": "https://icecast.rte.ie/2fm",
        "url_sat": "http://127.0.0.1:8001/1:0:2:148E:7E7:2:11A0000:0:0:0:",
        "preferred": "sat",
        "type": "MP3",
        "last_delay_online": None,
        "last_delay_sat": None,
        "fine_tune": 0,
        "last_measured": None,
    },
]


def load_stations():
    """Load stations from config file, or create with defaults."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return data.get("stations", DEFAULT_STATIONS)
        except Exception:
            pass
    save_stations(DEFAULT_STATIONS)
    return DEFAULT_STATIONS[:]


def save_stations(stations):
    """Save stations to config file (atomic write)."""
    tmp = CONFIG_FILE + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump({"stations": stations}, f, indent=2)
        os.rename(tmp, CONFIG_FILE)
    except Exception:
        try:
            os.remove(tmp)
        except Exception:
            pass


def get_station_url(station):
    """Get the active URL for a station based on preferred source."""
    preferred = station.get("preferred", "online")
    if preferred == "sat" and station.get("url_sat"):
        return station["url_sat"], "sat"
    if station.get("url_online"):
        return station["url_online"], "online"
    if station.get("url_sat"):
        return station["url_sat"], "sat"
    return None, None


def get_saved_delay(station):
    """Get the saved delay for the station's preferred source."""
    preferred = station.get("preferred", "online")
    if preferred == "sat":
        return station.get("last_delay_sat")
    return station.get("last_delay_online")


def save_delay(station, delay_seconds, source_type):
    """Save a measured delay for a station."""
    if source_type == "sat":
        station["last_delay_sat"] = delay_seconds
    else:
        station["last_delay_online"] = delay_seconds
    station["last_measured"] = _today()


def get_capture_duration(station):
    """Get appropriate capture duration based on saved delay.

    If we know the delay is ~3 minutes, we need at least 3.5+ minutes of capture.
    Default is 60 seconds for unknown delays.
    """
    saved = get_saved_delay(station)
    if saved and saved > 30:
        # Need capture time > delay + some overlap for correlation
        return int(saved + max(30, saved * 0.3))
    return 60  # Default 60 seconds


def _today():
    import time
    return time.strftime("%Y-%m-%d")
