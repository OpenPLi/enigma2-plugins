import json
import re
import time
import urllib.request

LOG_FILE = "/var/log/radiocomsync.log"
MAX_RESPONSE = 512 * 1024  # 512KB max API response
MAX_ICY_METAINT = 65536  # Max ICY metadata interval (typical: 8192-32768)

# Module-level cache: {station_name: (title, source_type, timestamp)}
_cache = {}
CACHE_TTL = 120  # 2 minutes

# Map station names to BBC service IDs
STATION_TO_BBC = {
    "BBC 5 Live": "bbc_radio_five_live",
    "BBC 5 Sports Extra": "bbc_radio_five_live_sports_extra",
    "BBC Radio Ulster": "bbc_radio_ulster",
    "BBC Sportsound Scotland": "bbc_radio_scotland_fm",
    "BBC Radio 4 (TMS)": "bbc_radio_fourfm",
    "BBC World Service": "bbc_world_service",
}

# Stations with custom REST APIs
STATION_WLR_API = "https://wlrfm.com/wp-json/wlr/v1/schedule"

# Map station names to talkSPORT API IDs
STATION_TO_TALKSPORT = {
    "talkSPORT": "talksport",
    "talkSPORT 2": "talksport2",
}

# Map station names to RTE page slugs
STATION_TO_RTE = {
    "RTE Radio 1": "radio1",
    "RTE 2FM": "2fm",
}


def _log(msg):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"{msg}\n")
    except Exception:
        pass


def _bbc_now_playing(service_id):
    """Fetch now-playing from BBC Nitro schedule API."""
    try:
        url = f"https://rms.api.bbc.co.uk/v2/experience/inline/schedules/{service_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=5).read(MAX_RESPONSE).decode()
        j = json.loads(data)
        for block in j.get("data", []):
            for item in block.get("data", []):
                titles = item.get("titles", {})
                primary = titles.get("primary", "")
                secondary = titles.get("secondary", "")
                if primary:
                    if secondary:
                        return f"{primary} - {secondary}"
                    return primary
    except Exception as e:
        _log(f"[Metadata] BBC API failed for {service_id}: {e}")
    return None


def _talksport_now_playing(station_id):
    """Fetch now-playing from talkSPORT API."""
    try:
        url = f"https://talksport.com/play/api/onAirNow/{station_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=5).read(MAX_RESPONSE).decode()
        j = json.loads(data)
        show = j.get("show", {}).get("title", "") or j.get("title", "")
        if show:
            return show
    except Exception as e:
        _log(f"[Metadata] talkSPORT API failed for {station_id}: {e}")
    return None


def _wlr_now_playing():
    """Fetch now-playing from WLR FM REST API."""
    try:
        req = urllib.request.Request(STATION_WLR_API, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=5).read(MAX_RESPONSE).decode()
        j = json.loads(data)
        current = j.get("currentShow", {})
        name = current.get("name", "")
        if name:
            start = current.get("startTime", "")
            end = current.get("endTime", "")
            if start and end:
                return f"{name} ({start}-{end})"
            return name
    except Exception as e:
        _log(f"[Metadata] WLR API failed: {e}")
    return None


def _rte_now_playing(station_slug):
    """Fetch now-playing from RTE Radio schedule JSON API.

    GET /radio/{slug}/schedule/{YYYYMMDD}/ with Accept: application/json
    returns schedule blocks with is_now/is_next/is_last flags.
    """
    try:
        today = time.strftime("%Y%m%d")
        url = "https://www.rte.ie/radio/%s/schedule/%s/" % (station_slug, today)
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        })
        data = urllib.request.urlopen(req, timeout=5).read(MAX_RESPONSE).decode()
        blocks = json.loads(data)
        for block in blocks:
            for show in block.get("data", []):
                if show.get("is_now") and show.get("showName"):
                    name = show["showName"]
                    t = show.get("showTime", "")
                    if t:
                        return "%s (%s)" % (name, t)
                    return name
    except Exception as e:
        _log("[Metadata] RTE API failed for %s: %s" % (station_slug, e))
    return None


def get_icy_metadata(url, timeout=5):
    """Fetch ICY metadata (now playing) from an internet radio stream."""
    try:
        req = urllib.request.Request(url)
        req.add_header("Icy-MetaData", "1")
        req.add_header("User-Agent", "RadioComSync/1.0")

        response = urllib.request.urlopen(req, timeout=timeout)
        try:
            headers = response.headers
            icy_name = headers.get("icy-name", "").strip()

            meta_int = headers.get("icy-metaint")
            if not meta_int:
                if icy_name and icy_name not in ("_", "Unspecified", ""):
                    return icy_name
                return None

            meta_int = int(meta_int)
            if meta_int > MAX_ICY_METAINT:
                return None

            for attempt in range(5):
                response.read(meta_int)
                meta_length_byte = response.read(1)
                if not meta_length_byte:
                    break
                meta_length = meta_length_byte[0] * 16
                if meta_length == 0:
                    continue
                meta_data = response.read(meta_length).decode("utf-8", errors="ignore")
                match = re.search(r"StreamTitle='([^']*)'", meta_data)
                if match:
                    title = match.group(1).strip()
                    if title and title not in ("_", "", "Unspecified"):
                        return title

            if icy_name and icy_name not in ("_", "Unspecified", ""):
                return icy_name
        finally:
            response.close()

    except Exception as e:
        _log(f"[Metadata] ICY fetch failed for {url[:40]}: {e}")

    return None


def get_sat_now_playing(session, service_ref_url):
    """Get EPG now-playing info for a satellite radio service."""
    try:
        from enigma import eEPGCache, eServiceReference

        sref_str = service_ref_url.split("/", 3)[-1] if "/" in service_ref_url else None
        if not sref_str:
            return None

        epgcache = eEPGCache.getInstance()
        ref = eServiceReference(sref_str)
        event = epgcache.lookupEventTime(ref, -1)
        if event:
            return event.getEventName()

    except Exception as e:
        _log(f"[Metadata] EPG lookup failed: {e}")

    return None


def get_now_playing(station, session=None):
    """Get now-playing info for a station.

    Results are cached for 2 minutes to avoid hammering APIs.

    Returns (title_string, source_type) or (None, None).
    """
    station_name = station.get("name", "")

    # Check cache first
    cached = _cache.get(station_name)
    if cached:
        title, source, ts = cached
        if time.time() - ts < CACHE_TTL:
            return title, source

    title, source = _fetch_now_playing(station, session)
    if title:
        _cache[station_name] = (title, source, time.time())
    return title, source


def _fetch_now_playing(station, session):
    """Internal: fetch now-playing without caching."""
    station_name = station.get("name", "")

    # 1. BBC API
    bbc_id = STATION_TO_BBC.get(station_name)
    if bbc_id:
        title = _bbc_now_playing(bbc_id)
        if title:
            return title, "api"

    # 2. talkSPORT API
    ts_id = STATION_TO_TALKSPORT.get(station_name)
    if ts_id:
        title = _talksport_now_playing(ts_id)
        if title:
            return title, "api"

    # 3. WLR FM API
    if station_name == "WLR FM":
        title = _wlr_now_playing()
        if title:
            return title, "api"

    # 4. RTE schedule API
    rte_slug = STATION_TO_RTE.get(station_name)
    if rte_slug:
        title = _rte_now_playing(rte_slug)
        if title:
            return title, "api"

    # 5. Satellite EPG
    if station.get("url_sat") and session:
        title = get_sat_now_playing(session, station["url_sat"])
        if title:
            return title, "sat"

    # 6. ICY metadata from online stream
    if station.get("url_online"):
        title = get_icy_metadata(station["url_online"])
        if title:
            return title, "online"

    return None, None
