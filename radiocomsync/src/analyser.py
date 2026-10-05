import os
import struct
import subprocess
import time

TV_RAW = "/tmp/rcs_tv.raw"
RADIO_RAW = "/tmp/rcs_radio.raw"
SAMPLE_RATE = 8000
WINDOW_MS = 100
WINDOW_SAMPLES = SAMPLE_RATE * WINDOW_MS // 1000  # 800 samples per window
MAX_DELAY_SECONDS = 300  # Search up to 5 minutes
DEFAULT_CAPTURE_SECONDS = 60  # Default capture duration
# Capture must be at least 2x the expected delay for reliable correlation
# 60s default handles up to ~50s delay, user can increase for longer delays

LOG_FILE = "/var/log/radiocomsync.log"


def _log(msg):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"{msg}\n")
    except Exception:
        pass


def _build_gst_pipeline(source_url, output_file, is_tv=False):
    """Build a GStreamer command to capture raw PCM audio."""
    if is_tv:
        # TV (satellite/terrestrial): use tsdemux with audio/mpeg filter
        # to extract only audio, ignoring video (which may need unavailable decoders)
        return [
            "gst-launch-1.0", "-q",
            "souphttpsrc", f"location={source_url}",
            "!", "tsdemux", "name=demux", "demux.",
            "!", "audio/mpeg",
            "!", "mpegaudioparse",
            "!", "mpg123audiodec",
            "!", "audioconvert",
            "!", "audioresample",
            "!", f"audio/x-raw,rate={SAMPLE_RATE},channels=1,format=S16LE",
            "!", "filesink", f"location={output_file}",
        ]
    else:
        # Radio (internet stream): use decodebin for flexible format handling
        return [
            "gst-launch-1.0", "-q",
            "souphttpsrc", f"location={source_url}",
            "!", "decodebin",
            "!", "audioconvert",
            "!", "audioresample",
            "!", f"audio/x-raw,rate={SAMPLE_RATE},channels=1,format=S16LE",
            "!", "filesink", f"location={output_file}",
        ]


def get_tv_stream_url(session):
    """Get the current TV service as a streamable URL via Enigma2 web interface."""
    try:
        ref = session.nav.getCurrentlyPlayingServiceReference()
        if ref:
            return f"http://127.0.0.1:8001/{ref.toString()}"
    except Exception:
        pass
    return None


def start_capture(tv_url, radio_url, duration=30):
    """Start capturing audio from both sources.

    Returns (tv_process, radio_process) subprocess handles.
    """
    # Clean up any previous files
    for f in [TV_RAW, RADIO_RAW]:
        if os.path.exists(f):
            os.remove(f)

    tv_cmd = _build_gst_pipeline(tv_url, TV_RAW, is_tv=True)
    radio_cmd = _build_gst_pipeline(radio_url, RADIO_RAW, is_tv=False)

    _log(f"[Analyser] Starting TV capture: {tv_url[:60]}...")
    _log(f"[Analyser] Starting Radio capture: {radio_url[:60]}...")

    tv_proc = subprocess.Popen(
        tv_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    radio_proc = subprocess.Popen(
        radio_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    return tv_proc, radio_proc


def stop_capture(tv_proc, radio_proc):
    """Stop both capture processes."""
    for proc in [tv_proc, radio_proc]:
        if proc is None:
            continue
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def get_capture_progress():
    """Get the current capture file sizes (for live meters)."""
    tv_size = os.path.getsize(TV_RAW) if os.path.exists(TV_RAW) else 0
    radio_size = os.path.getsize(RADIO_RAW) if os.path.exists(RADIO_RAW) else 0
    return tv_size, radio_size


def get_live_levels():
    """Get approximate current audio levels from file growth.

    Returns (tv_level, radio_level) as 0-100 values.
    """
    tv_size = os.path.getsize(TV_RAW) if os.path.exists(TV_RAW) else 0
    radio_size = os.path.getsize(RADIO_RAW) if os.path.exists(RADIO_RAW) else 0

    # Read the last 800 samples (100ms) from each file for level metering
    tv_level = _read_tail_rms(TV_RAW, tv_size)
    radio_level = _read_tail_rms(RADIO_RAW, radio_size)

    return tv_level, radio_level


def _read_tail_rms(filepath, file_size):
    """Read the last window of samples and compute RMS level (0-100)."""
    bytes_needed = WINDOW_SAMPLES * 2  # S16LE = 2 bytes per sample
    if file_size < bytes_needed:
        return 0
    try:
        with open(filepath, "rb") as f:
            f.seek(file_size - bytes_needed)
            data = f.read(bytes_needed)
        samples = struct.unpack(f"<{WINDOW_SAMPLES}h", data)
        rms = _rms(samples)
        # Normalise to 0-100 (32768 is max for S16)
        level = min(100, int(rms * 100 / 8000))
        return level
    except Exception:
        return 0


def _rms(samples):
    """Compute RMS of a sequence of samples."""
    if not samples:
        return 0
    total = 0
    for s in samples:
        total += s * s
    return int((total / len(samples)) ** 0.5)


def _compute_energy_envelope(filepath):
    """Read raw PCM file and compute energy envelope (RMS per window)."""
    if not os.path.exists(filepath):
        return []

    file_size = os.path.getsize(filepath)
    num_samples = file_size // 2  # S16LE = 2 bytes per sample
    num_windows = num_samples // WINDOW_SAMPLES

    envelope = []
    with open(filepath, "rb") as f:
        for _ in range(num_windows):
            data = f.read(WINDOW_SAMPLES * 2)
            if len(data) < WINDOW_SAMPLES * 2:
                break
            samples = struct.unpack(f"<{WINDOW_SAMPLES}h", data)
            envelope.append(_rms(samples))

    return envelope


def analyse_delay():
    """Analyse captured audio and return delay in seconds.

    Returns (delay_seconds, confidence) or (None, 0) on failure.
    Confidence is 0-100 indicating how strong the correlation peak is.
    """
    _log("[Analyser] Computing energy envelopes...")

    tv_envelope = _compute_energy_envelope(TV_RAW)
    radio_envelope = _compute_energy_envelope(RADIO_RAW)

    _log(f"[Analyser] TV: {len(tv_envelope)} windows, Radio: {len(radio_envelope)} windows")

    if len(tv_envelope) < 50 or len(radio_envelope) < 50:
        _log("[Analyser] Not enough audio data captured")
        return None, 0

    # Cross-correlate: slide radio against TV to find the delay.
    # Radio online streams are typically BEHIND TV (delayed by buffering/encoding).
    # We test: "if radio is delayed by 'offset' windows, does TV[i] match Radio[offset+i]?"
    max_offset = min(
        MAX_DELAY_SECONDS * (1000 // WINDOW_MS),
        len(radio_envelope) - 50,
    )

    _log(f"[Analyser] Searching offsets 0 to {max_offset} ({max_offset * WINDOW_MS / 1000:.0f}s)...")

    best_corr = 0
    best_offset = 0
    correlations = []

    # Normalise envelopes to reduce volume difference effects
    tv_mean = sum(tv_envelope) / len(tv_envelope) if tv_envelope else 1
    radio_mean = sum(radio_envelope) / len(radio_envelope) if radio_envelope else 1

    tv_norm = [x / tv_mean if tv_mean > 0 else 0 for x in tv_envelope]
    radio_norm = [x / radio_mean if radio_mean > 0 else 0 for x in radio_envelope]

    for offset in range(0, max_offset):
        # Compute overlap fresh each iteration (don't shrink permanently)
        current_overlap = min(len(tv_norm), len(radio_norm) - offset)
        if current_overlap < 30:
            break

        corr = 0
        for i in range(current_overlap):
            corr += tv_norm[i] * radio_norm[offset + i]

        # Normalise by overlap length so different offsets are comparable
        corr = corr / current_overlap
        correlations.append(corr)
        if corr > best_corr:
            best_corr = corr
            best_offset = offset

    if not correlations:
        _log("[Analyser] Cross-correlation failed")
        return None, 0

    # Compute confidence: how much does the peak stand out?
    avg_corr = sum(correlations) / len(correlations)
    confidence = 0
    if avg_corr > 0:
        confidence = min(100, int((best_corr / avg_corr - 1) * 50))

    delay_seconds = best_offset * WINDOW_MS / 1000.0
    _log(f"[Analyser] Best offset: {best_offset} windows = {delay_seconds:.1f}s (confidence: {confidence}%)")

    return round(delay_seconds, 1), confidence


def cleanup():
    """Remove temporary audio files."""
    for f in [TV_RAW, RADIO_RAW]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass
