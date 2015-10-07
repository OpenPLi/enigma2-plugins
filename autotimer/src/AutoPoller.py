# for localized messages
from __future__ import print_function

from . import _
# Core functionality
from enigma import eTimer, ePythonMessagePump

# Config
from Components.config import config
from time import time, localtime, asctime

# Notifications
from Tools.FuzzyDate import FuzzyTime
from Tools.Notifications import AddPopup
from Screens.MessageBox import MessageBox
from Screens import Standby

NOTIFICATIONID = 'AutoTimerConflictEncounteredNotification'
SIMILARNOTIFICATIONID = 'AutoTimerSimilarUsedNotification'
TIMERNOTIFICATIONID = 'AutoTimerAddedAfterPollNotification'

from threading import Thread, Semaphore
from collections import deque

from twisted.internet import reactor

class AutoPollerThread(Thread):
	"""Background thread where the EPG is parsed (unless initiated by the user)."""
	def __init__(self):
		Thread.__init__(self)
		self.__semaphore = Semaphore(0)
		self.__queue = deque(maxlen=1)
		self.__pump = ePythonMessagePump()
		self.__pump.recv_msg.get().append(self.gotThreadMsg)
		self.__timer = eTimer()
		self.__timer.callback.append(self.timeout)
		self.running = False

	def timeout(self):
		self.__semaphore.release()

	def gotThreadMsg(self, msg):
		"""Create Notifications if there is anything to display."""
		ret = self.__queue.pop()
		conflicts = ret[4]
		if conflicts and config.plugins.autotimer.notifconflict.value:
			AddPopup(
				#_("%d conflict(s) encountered when trying to add new timers:\n%s") % (len(conflicts), '\n'.join([_("%s: %s at %s") % (x[4], x[0], asctime(localtime(x[2]))) for x in conflicts])),
				_("%d conflict(s) encountered when trying to add new timers:\n%s") % (len(conflicts), '\n'.join([_("%s: %s at %s") % (x[4], x[0], "('%s', '%s')" % FuzzyTime(x[2])) for x in conflicts])),
				MessageBox.TYPE_INFO,
				config.plugins.autotimer.popup_timeout.value,
				NOTIFICATIONID
			)
		similars = ret[5]
		if similars and config.plugins.autotimer.notifsimilar.value:
			AddPopup(
				#_("%d conflict(s) solved with similar timer(s):\n%s") % (len(similars), '\n'.join([_("%s: %s at %s") % (x[4], x[0], asctime(localtime(x[2]))) for x in similars])),
				_("%d conflict(s) solved with similar timer(s):\n%s") % (len(similars), '\n'.join([_("%s: %s at %s") % (x[4], x[0], "('%s', '%s')" % FuzzyTime(x[2])) for x in similars])),
				MessageBox.TYPE_INFO,
				config.plugins.autotimer.popup_timeout.value,
				SIMILARNOTIFICATIONID
			)
		added_timer = ret[1]
		if added_timer and config.plugins.autotimer.notiftimers.value and Standby.inStandby is None:
			AddPopup(
				_("AutoTimer\n%d timer(s) were added.") % (ret[1]),
				MessageBox.TYPE_INFO,
				config.plugins.autotimer.popup_timeout.value,
				TIMERNOTIFICATIONID 
			)

	def start(self, initial=True):
		if initial:
			delay = config.plugins.autotimer.delay.value*60
			if delay == 0:
				delay = 30
		else: delay = config.plugins.autotimer.interval.value*3600

		self.__timer.startLongTimer(delay)
		if not self.isAlive():
			Thread.start(self)

	def pause(self):
		self.__timer.stop()

	def stop(self):
		self.__timer.stop()
		self.running = False
		self.__semaphore.release()
		self.__pump.recv_msg.get().remove(self.gotThreadMsg)
		self.__timer.callback.remove(self.timeout)

	def run(self):
		sem = self.__semaphore
		queue = self.__queue
		pump = self.__pump
		timer = self.__timer

		self.running = True
		while 1:
			sem.acquire()
			# NOTE: we have to check this here and not using the while to prevent the parser to be started on shutdown
			if not self.running: break

			if config.plugins.autotimer.skip_during_records.value:
				try:
					import NavigationInstance
					if NavigationInstance.instance.RecordTimer.isRecording():
						print("[AutoTimer]: Skip check during running records")
						reactor.callFromThread(timer.startLongTimer, config.plugins.autotimer.interval.value*3600)
						continue
				except:
					pass
			try:
				if config.plugins.autotimer.onlyinstandby.value and Standby.inStandby is None:
					print("[AutoTimer]: Skip check during live tv")
					reactor.callFromThread(timer.startLongTimer, config.plugins.autotimer.interval.value*3600)
					continue
			except:
				pass
			if config.plugins.autotimer.skip_during_epgrefresh.value:
				try:
					from Plugins.Extensions.EPGRefresh.EPGRefresh import epgrefresh
					if epgrefresh.isrunning:
						print("[AutoTimer]: Skip check during EPGRefresh")
						reactor.callFromThread(timer.startLongTimer, config.plugins.autotimer.interval.value*3600)
						continue
				except:
					pass

			from plugin import autotimer
			# Ignore any program errors
			try:
				queue.append(autotimer.parseEPG())
				pump.send(0)
			except Exception:
				# Dump error to stdout
				import traceback, sys
				traceback.print_exc(file=sys.stdout)
			#Keep that eTimer in the mainThread
			reactor.callFromThread(timer.startLongTimer, config.plugins.autotimer.interval.value*3600)

class AutoPoller:
	"""Manages actual thread which does the polling. Used for convenience."""

	def __init__(self):
		self.thread = AutoPollerThread()

	def start(self, initial=True):
		self.thread.start(initial=initial)

	def pause(self):
		self.thread.pause()

	def stop(self):
		self.thread.stop()
		# NOTE: while we don't need to join the thread, we should do so in case it's currently parsing
		self.thread.join()
		self.thread = None
