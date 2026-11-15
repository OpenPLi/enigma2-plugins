"""Audio playback — modelled on Budweiser's proven approach."""

import os
import shlex
import signal
import subprocess
import traceback
from fcntl import ioctl

LOG_FILE = "/var/log/radiocomsync.log"

AUDIO_FD = None
AUDIO_FILE = ''
AUDIO_PROCESS = None
SESSION = None

ALSA_DEVICE = "alsasink device=hw:0"


def _log(msg):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"{msg}\n")
    except Exception:
        pass


def audioFind():
    """Find Enigma2's DVB audio device file descriptor."""
    global AUDIO_FD, AUDIO_FILE
    try:
        if AUDIO_FD is not None:
            try:
                if ioctl(AUDIO_FD, 0x6f0c) == 0:
                    return AUDIO_FD
            except Exception:
                AUDIO_FD = None
                AUDIO_FILE = ''
        pid = os.getpid()
        ldir = os.listdir('/proc/%s/fd' % pid)
        for fd in ldir:
            try:
                ls = os.readlink('/proc/%s/fd/%s' % (pid, fd))
            except Exception:
                continue
            if '/dev/dvb/adapter' in ls and 'audio' in ls:
                AUDIO_FD = int(fd)
                AUDIO_FILE = ls
                return AUDIO_FD
    except Exception:
        AUDIO_FD = None
        AUDIO_FILE = ''
    return None


def audioStop():
    """Stop Enigma2's DVB audio decoder — releases ALSA device."""
    try:
        fd = audioFind()
        if fd is None:
            return
        _log('[Player] audioStop fd=%s' % str(fd))
        ioctl(fd, 0x6f01)
    except Exception:
        _log('[Player] audioStop exception')
        _log(traceback.format_exc())


def audioStart():
    """Restart Enigma2's DVB audio decoder."""
    try:
        fd = audioFind()
        if fd is None:
            return
        _log('[Player] audioStart fd=%s' % str(fd))
        ioctl(fd, 0x6f02)
    except Exception:
        _log('[Player] audioStart exception')
        _log(traceback.format_exc())


def audioKill():
    """Kill the GStreamer audio process."""
    global AUDIO_PROCESS
    _log('[Player] audioKill pid=%s' % str(AUDIO_PROCESS))
    if AUDIO_PROCESS:
        try:
            os.kill(AUDIO_PROCESS, signal.SIGKILL)
        except Exception:
            pass
        try:
            os.killpg(AUDIO_PROCESS, signal.SIGKILL)
        except Exception:
            pass
        try:
            os.waitpid(AUDIO_PROCESS, 0)
        except Exception:
            pass
        AUDIO_PROCESS = None
    # Kill any orphaned audio processes
    subprocess.run(
        ["killall", "-9", "gst-launch-1.0", "mpg123"],
        stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
    )


def audioProcess(argv):
    """Fork and exec the GStreamer pipeline."""
    global AUDIO_PROCESS
    _log('[Player] audioProcess argv=%s' % str(argv))
    try:
        audioKill()
        AUDIO_PROCESS = os.fork()
        if not AUDIO_PROCESS:
            try:
                os.closerange(3, os.sysconf('SC_OPEN_MAX'))
                os.setsid()
                os.execv(argv[0], argv)
            except Exception:
                pass
            os._exit(1)
        _log('[Player] audioProcess forked pid=%s' % str(AUDIO_PROCESS))
    except Exception:
        _log('[Player] audioProcess exception')
        _log(traceback.format_exc())


def _validate_url(url):
    """Basic URL validation to prevent injection and SSRF."""
    if not url or not isinstance(url, str):
        return False
    # Allow http/https schemes only
    if not url.startswith("http://") and not url.startswith("https://"):
        return False
    # Block file://, ftp://, data: etc.
    return True


def playStation(url, stream_type="MP3"):
    """Play a radio stream — audioStop, then fork/exec GStreamer.

    stream_type: 'MP3' for direct MP3 streams (wget | mpg123 pipeline)
                 'HLS' for BBC HLS streams (ffmpeg | gst-launch pipeline)
    """
    if not _validate_url(url):
        _log('[Player] Rejected invalid URL: %s' % str(url)[:80])
        return

    audioStop()

    safe_url = shlex.quote(url)
    buffers = 100

    if stream_type == "HLS":
        argv = [
            "/bin/sh", "-c",
            "(/usr/bin/ffmpeg -loglevel error"
            " -i %s"
            " -vn -c:a copy -f adts pipe:1"
            "|/usr/bin/gst-launch-1.0 fdsrc fd=0"
            " ! aacparse ! faad"
            " ! queue2 use-buffering=true max-size-buffers=%d"
            " max-size-bytes=0 max-size-time=0"
            " ! %s"
            ")>/dev/null 2>&1" % (safe_url, buffers, ALSA_DEVICE)
        ]
    else:
        argv = [
            "/bin/sh", "-c",
            "(/usr/bin/wget -qO- %s"
            "|/usr/bin/mpg123 -o wav -"
            "|/usr/bin/gst-launch-1.0 fdsrc fd=0"
            " ! decodebin"
            " ! queue2 use-buffering=true max-size-buffers=%d"
            " max-size-bytes=0 max-size-time=0"
            " ! %s"
            ")>/dev/null 2>&1" % (safe_url, buffers, ALSA_DEVICE)
        ]

    audioProcess(argv)


def stopStation():
    """Stop radio and restore TV audio."""
    audioKill()
    audioStart()
