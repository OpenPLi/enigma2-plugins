from __future__ import print_function

# Plugins Config
from xml.etree.cElementTree import parse as cet_parse
import os
from AutoTimerConfiguration import parseConfig, buildConfig
from Logger import doLog, startLog, getLog, doDebug

# Navigation (RecordTimer)
import NavigationInstance

# Timer
from ServiceReference import ServiceReference
from RecordTimer import RecordTimerEntry
from Components.TimerSanityCheck import TimerSanityCheck

# Notifications
from Tools.Notifications import AddPopup
from Screens import Standby
from Screens.MessageBox import MessageBox

# Timespan
from time import localtime, strftime, time, mktime
from datetime import timedelta, date

# EPGCache & Event
from enigma import eEPGCache, eServiceReference, eServiceCenter, iServiceInformation

from twisted.internet import reactor, defer
from twisted.python import failure
from threading import currentThread
import Queue

# AutoTimer Component
from AutoTimerComponent import preferredAutoTimerComponent

from itertools import chain
from collections import defaultdict
from difflib import SequenceMatcher
from operator import itemgetter

from SimpleThread import SimpleThread

try:
	from Plugins.Extensions.SeriesPlugin.plugin import getSeasonEpisode4 as sp_getSeasonEpisode
except ImportError as ie:
	sp_getSeasonEpisode = None

try:
	from Plugins.Extensions.SeriesPlugin.plugin import showResult as sp_showResult
except ImportError as ie:
	sp_showResult = None

from . import config, xrange, itervalues

CONFLICTINGDOUBLEID = 'AutoTimerConflictingDoubleTimersNotification'
addNewTimers = []

XML_CONFIG = "/etc/enigma2/autotimer.xml"

def getTimeDiff(timerbegin, timerend, begin, end):
	if begin <= timerbegin <= end:
		return end - timerbegin
	elif timerbegin <= begin <= timerend:
		return timerend - begin
	return 0

def timeSimilarityPercent(rtimer, evtBegin, evtEnd, timer=None):
	if (timer is not None) and (timer.offset is not None):
		# remove custom offset from rtimer using timer.offset as RecordTimerEntry doesn't store the offset
		rtimerBegin = rtimer.begin + timer.offset[0]
		rtimerEnd   = rtimer.end - timer.offset[1]
	else:
		# remove E2 offset
		rtimerBegin = rtimer.begin + config.recording.margin_before.value * 60
		rtimerEnd   = rtimer.end - config.recording.margin_after.value * 60
	if (rtimerBegin <= evtBegin) and (evtEnd <= rtimerEnd):
		commonTime = evtEnd - evtBegin
	elif (evtBegin <= rtimerBegin) and (rtimerEnd <= evtEnd):
		commonTime = rtimerEnd - rtimerBegin
	elif evtBegin <= rtimerBegin <= evtEnd:
		commonTime = evtEnd - rtimerBegin
	elif rtimerBegin <= evtBegin <= rtimerEnd:
		commonTime = rtimerEnd - evtBegin
	else:
		commonTime = 0
	if evtBegin != evtEnd:
		commonTime_percent = 100*commonTime/(evtEnd - evtBegin)
	else:
		return 0
	if rtimerEnd != rtimerBegin:
		durationMatch_percent = 100*(evtEnd - evtBegin)/(rtimerEnd - rtimerBegin)
	else:
		return 0
	if durationMatch_percent < commonTime_percent:
		#avoid false match for a short event completely inside a very long rtimer's time span 
		return durationMatch_percent
	else:
		return commonTime_percent

def blockingCallFromMainThread(f, *a, **kw):
	"""
	  Modified version of twisted.internet.threads.blockingCallFromThread
	  which waits 30s for results and otherwise assumes the system to be shut down.
	  This is an ugly workaround for a twisted-internal deadlock.
	  Please keep the look intact in case someone comes up with a way
	  to reliably detect from the outside if twisted is currently shutting
	  down.
	"""
	queue = Queue.Queue()
	def _callFromThread():
		result = defer.maybeDeferred(f, *a, **kw)
		result.addBoth(queue.put)
	reactor.callFromThread(_callFromThread)

	result = None
	while True:
		try:
			result = queue.get(True, config.plugins.autotimer.timeout.value*60)
		except Queue.Empty as qe:
			if True: #not reactor.running: # reactor.running is only False AFTER shutdown, we are during.
				doLog("[AutoTimer] Reactor no longer active, aborting.")
		else:
			break

	if isinstance(result, failure.Failure):
		result.raiseException()
	return result

typeMap = {
	"exact": eEPGCache.EXAKT_TITLE_SEARCH,
	"partial": eEPGCache.PARTIAL_TITLE_SEARCH,
	"start": eEPGCache.START_TITLE_SEARCH,
	"description": -99
}

caseMap = {
	"sensitive": eEPGCache.CASE_CHECK,
	"insensitive": eEPGCache.NO_CASE_CHECK
}

class AutoTimer:
	"""Read and save xml configuration, query EPGCache"""

	def __init__(self):
		# Initialize
		self.timers = []
		self.isParseRunning = False
		self.configMtime = -1
		self.uniqueTimerId = 0
		self.defaultTimer = preferredAutoTimerComponent(
			0,		# Id
			"",		# Name
			"",		# Match
			True 	# Enabled
		)

# Configuration

	def readXml(self):
		# Abort if no config found
		if not os.path.exists(XML_CONFIG):
			doLog("[AutoTimer] No configuration file present")
			return

		# Parse if mtime differs from whats saved
		mtime = os.path.getmtime(XML_CONFIG)
		if mtime == self.configMtime:
			doLog("[AutoTimer] No changes in configuration, won't parse")
			return

		# Save current mtime
		self.configMtime = mtime

		# Parse Config
		try:
			configuration = cet_parse(XML_CONFIG).getroot()
		except:
			try:
				if os_path.exists(XML_CONFIG + "_old"):
					os_rename(XML_CONFIG + "_old", XML_CONFIG + "_old(1)")
				os_rename(XML_CONFIG, XML_CONFIG + "_old")
				doLog("[AutoTimer] autotimer.xml is corrupt rename file to /etc/enigma2/autotimer.xml_old")
			except:
				pass
			if Standby.inStandby is None:
				AddPopup(_("The autotimer file (/etc/enigma2/autotimer.xml) is corrupt and could not be loaded.") + "\n" +_("A new and empty config was created. A backup of the config can be found here (/etc/enigma2/autotimer.xml_old)."), type = MessageBox.TYPE_ERROR, timeout = 0, id = "AutoTimerLoadFailed")

			self.timers = []
			self.defaultTimer = preferredAutoTimerComponent(
				0,		# Id
				"",		# Name
				"",		# Match
				True	# Enabled
			)

			try:
				self.writeXml()
				configuration = cet_parse(XML_CONFIG).getroot()
			except:
				doLog("[AutoTimer] fatal error, the autotimer.xml cannot create")
				return

		# Empty out timers and reset Ids
		del self.timers[:]
		self.defaultTimer.clear(-1, True)

		parseConfig(
			configuration,
			self.timers,
			configuration.get("version"),
			0,
			self.defaultTimer
		)
		self.uniqueTimerId = len(self.timers)

	def getXml(self):
		return buildConfig(self.defaultTimer, self.timers, webif = True)

	def writeXml(self):
		file = open(XML_CONFIG, 'w')
		file.writelines(buildConfig(self.defaultTimer, self.timers))
		file.close()

	def getStatusParseEPGrunning(self):
		#return self.isParseRunning
		return False

# Manage List
	def add(self, timer):
		self.timers.append(timer)

	def getEnabledTimerList(self):
		return (x for x in self.timers if x.enabled)

	def getTimerList(self):
		return self.timers

	def getTupleTimerList(self):
		lst = self.timers
		return [(x,) for x in lst]

	def getSortedTupleTimerList(self):
		lst = self.timers[:]
		lst.sort()
		return [(x,) for x in lst]

	def getUniqueId(self):
		self.uniqueTimerId += 1
		return self.uniqueTimerId

	def remove(self, uniqueId):
		idx = 0
		for timer in self.timers:
			if timer.id == uniqueId:
				self.timers.pop(idx)
				return
			idx += 1

	def set(self, timer):
		idx = 0
		for stimer in self.timers:
			if stimer == timer:
				self.timers[idx] = timer
				return
			idx += 1
		self.timers.append(timer)

	def parseEPGAsync(self, simulateOnly = False):
		t = SimpleThread(lambda: self.parseEPG(simulateOnly=simulateOnly))
		t.start()
		return t.deferred

# Main function

	def parseTimer(self, timer, epgcache, serviceHandler, recordHandler, checkEvtLimit, evtLimit, timers, conflicting, similars, skipped, timerdict, moviedict, simulateOnly=False):
		new = 0
		modified = 0

		# Workaround to allow search for umlauts if we know the encoding
		#match = timer.match
		match = timer.match.replace('\xc2\x86', '').replace('\xc2\x87', '')
		if timer.encoding != 'UTF-8':
			try:
				match = match.decode('UTF-8').encode(timer.encoding)
			except UnicodeDecodeError:
				pass

		if timer.searchType == "description":
			epgmatches = []
			mask = (eServiceReference.isMarker | eServiceReference.isDirectory)

			casesensitive = timer.searchCase == "sensitive"
			if not casesensitive:
				match = match.lower()

			# Service filter defined
			# Search only using the specified services
			test = [(service, 0, -1, -1) for service in timer.services]

			for bouquet in timer.bouquets:
				services = serviceHandler.list(eServiceReference(bouquet))
				if not services is None:
					while True:
						service = services.getNext()
						if not service.valid(): #check end of list
							break
						if not (service.flags & mask):
							test.append( (service.toString(), 0, -1, -1 ) )

			if not test:
				# No service filter defined
				# Search within all services - could be very slow

				# Get all bouquets
				bouquetlist = []
				if config.usage.multibouquet.value:
					refstr = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
					bouquetroot = eServiceReference(refstr)
					bouquets = serviceHandler.list(bouquetroot)
					if bouquets:
						while True:
							s = bouquets.getNext()
							if not s.valid():
								break
							if s.flags & eServiceReference.isDirectory and not s.flags & eServiceReference.isInvisible:
								info = serviceHandler.info(s)
								if info:
									bouquetlist.append((info.getName(s), s))
					mask = (eServiceReference.isMarker | eServiceReference.isDirectory)
					for name, bouquet in bouquetlist:
						if not bouquet.valid(): #check end of list
							break
						if bouquet.flags & eServiceReference.isDirectory:
							services = serviceHandler.list(bouquet)
							if not services is None:
								while True:
									service = services.getNext()
									if not service.valid(): #check end of list
										break
									if not (service.flags & mask):
										test.append( (service.toString(), 0, -1, -1 ) )
				else:
					service_types_tv = '1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 22) || (type == 25) || (type == 31) || (type == 134) || (type == 195)'
					refstr = '%s FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet'%(service_types_tv)
					bouquetroot = eServiceReference(refstr)
					info = serviceHandler.info(bouquetroot)
					if info:
						bouquetlist.append((info.getName(bouquetroot), bouquetroot))
					mask = (eServiceReference.isMarker | eServiceReference.isDirectory)
					for name, bouquet in bouquetlist:
						if bouquet.flags & eServiceReference.isDirectory:
							services = serviceHandler.list(bouquet)
							if not services is None:
								while True:
									service = services.getNext()
									if not service.valid(): #check end of list
										break
									if not (service.flags & mask):
										test.append( (service.toString(), 0, -1, -1 ) )

			if test:
				# Get all events
				#  eEPGCache.lookupEvent( [ format of the returned tuples, ( service, 0 = event intersects given start_time, start_time -1 for now_time), ] )
				test.insert(0, 'RITBDSE')
				allevents = epgcache.lookupEvent(test) or []

				# Filter events
				for serviceref, eit, name, begin, duration, shortdesc, extdesc in allevents:
					if match in (shortdesc if casesensitive else shortdesc.lower()) \
						or match in (extdesc if casesensitive else extdesc.lower()):
						epgmatches.append( (serviceref, eit, name, begin, duration, shortdesc, extdesc) )

		else:
			# Search EPG, default to empty list
			epgmatches = epgcache.search( ('RITBDSE', 2500, typeMap[timer.searchType], match, caseMap[timer.searchCase]) ) or []

		# Sort list of tuples by begin time 'B'
		epgmatches.sort(key=itemgetter(3))

		# Contains the the marked similar eits and the conflicting strings
		similardict = defaultdict(list)

		# Loop over all EPG matches
		for idx, ( serviceref, eit, name, begin, duration, shortdesc, extdesc ) in enumerate( epgmatches ):

			startLog()

			# timer destination dir
			dest = timer.destination

			evtBegin = begin
			evtEnd = end = begin + duration

			doLog("[AutoTimer] possible epgmatch %s" % (name))
			doLog("[AutoTimer] Serviceref %s" % (str(serviceref)))
			eserviceref = eServiceReference(serviceref)
			evt = epgcache.lookupEventId(eserviceref, eit)
			if not evt:
				doLog("[AutoTimer] Could not create Event!")
				skipped.append((name, begin, end, str(serviceref), timer.name, getLog()))
				continue
			# Try to determine real service (we always choose the last one)
			n = evt.getNumOfLinkageServices()
			if n > 0:
				i = evt.getLinkageService(eserviceref, n-1)
				serviceref = i.toString()
				doLog("[AutoTimer] Serviceref2 %s" % (str(serviceref)))


			# If event starts in less than 60 seconds skip it
			if begin < time() + 60:
				doLog("[AutoTimer] Skipping an event because it starts in less than 60 seconds")
				skipped.append((name, begin, end, serviceref, timer.name, getLog()))
				continue

			# Set short description to equal extended description if it is empty.
			if not shortdesc and timer.descShortEqualExt:
				shortdesc = extdesc

			# Convert begin time
			timestamp = localtime(begin)
			# Update timer
			timer.update(begin, timestamp)

			# Check if eit is in similar matches list
			# NOTE: ignore evtLimit for similar timers as I feel this makes the feature unintuitive
			similarTimer = False
			if eit in similardict:
				similarTimer = True
				dayofweek = None # NOTE: ignore day on similar timer
			else:
				# If maximum days in future is set then check time
				if checkEvtLimit:
					if begin > evtLimit:
						doLog("[AutoTimer] Skipping an event because of maximum days in future is reached")
						skipped.append((name, begin, end, serviceref, timer.name, getLog()))
						continue

				dayofweek = str(timestamp.tm_wday)

			# Check timer conditions
			# NOTE: similar matches do not care about the day/time they are on, so ignore them
			if timer.checkServices(serviceref):
				doLog("[AutoTimer] Skipping an event because of check services")
				skipped.append((name, begin, end, serviceref, timer.name, getLog()))
				continue
			if timer.checkDuration(duration):
				doLog("[AutoTimer] Skipping an event because of duration check")
				skipped.append((name, begin, end, serviceref, timer.name, getLog()))
				continue
			if not similarTimer:
				if timer.checkTimespan(timestamp):
					doLog("[AutoTimer] Skipping an event because of timestamp check")
					skipped.append((name, begin, end, serviceref, timer.name, getLog()))
					continue
				if timer.checkTimeframe(begin):
					doLog("[AutoTimer] Skipping an event because of timeframe check")
					skipped.append((name, begin, end, serviceref, timer.name, getLog()))
					continue

			# Initialize
			newEntry = None
			oldEntry = None
			oldExists = False
			allow_modify = True
			newAT = None

			# Eventually change service to alternative
			if timer.overrideAlternatives:
				serviceref = timer.getAlternative(serviceref)

			if timer.series_labeling and sp_getSeasonEpisode is not None:
				allow_modify = False
				doLog("[AutoTimer SeriesPlugin] Request name, desc, path %s %s %s" % (name, shortdesc, dest))
				sp = sp_getSeasonEpisode(serviceref, name, evtBegin, evtEnd, shortdesc, dest)
				if sp and type(sp) in (tuple, list) and len(sp) == 4:
					name = sp[0] or name
					shortdesc = sp[1] or shortdesc
					dest = sp[2] or dest
					doLog(str(sp[3]))
					allow_modify = True
					doLog("[AutoTimer SeriesPlugin] Returned name, desc, path %s %s %s" % (name, shortdesc, dest))
				else:
					# Nothing found
					doLog(str(sp))
					# If AutoTimer name not equal match, do a second lookup with the name
					if timer.name.lower() != timer.match.lower():
						doLog("[AutoTimer SeriesPlugin] Request name, desc, path %s %s %s" % (timer.name, shortdesc, dest))
						sp = sp_getSeasonEpisode(serviceref, timer.name, evtBegin, evtEnd, shortdesc, dest)
						if sp and type(sp) in (tuple, list) and len(sp) == 4:
							name = sp[0] or name
							shortdesc = sp[1] or shortdesc
							dest = sp[2] or dest
							doLog(str(sp[3]))
							allow_modify = True
							doLog("[AutoTimer SeriesPlugin] Returned name, desc, path %s %s %s" % (name, shortdesc, dest))
						else:
							doLog(str(sp))

			if timer.checkFilter(name, shortdesc, extdesc, dayofweek):
				doLog("[AutoTimer] Skipping an event because of filter check")
				skipped.append((name, begin, end, serviceref, timer.name, getLog()))
				continue

			if timer.hasOffset():
				# Apply custom Offset
				begin, end = timer.applyOffset(begin, end)
			else:
				# Apply E2 Offset
				begin -= config.recording.margin_before.value * 60
				end += config.recording.margin_after.value * 60

			# Overwrite endtime if requested
			if timer.justplay and not timer.setEndtime:
				end = begin

			# Check for existing recordings in directory
			if timer.avoidDuplicateDescription == 3:
				# Reset movie Exists
				movieExists = False

				if dest and dest not in moviedict:
					self.addDirectoryToMovieDict(moviedict, dest, serviceHandler)
				for movieinfo in moviedict.get(dest, ()):
					if self.checkDuplicates(timer, name, movieinfo.get("name"), shortdesc, movieinfo.get("shortdesc"), extdesc, movieinfo.get("extdesc") ):
						doLog("[AutoTimer] We found a matching recorded movie, skipping event:", name)
						movieExists = True
						break
				if movieExists:
					doLog("[AutoTimer] Skipping an event because movie already exists")
					skipped.append((name, begin, end, serviceref, timer.name, getLog()))
					continue

			# Check for double Timers
			# We first check eit and if user wants us to guess event based on time
			# we try this as backup. The allowed diff should be configurable though.
			for rtimer in timerdict.get(serviceref, ()):
				if rtimer.eit == eit:
					oldExists = True
					doLog("[AutoTimer] We found a timer based on eit")
					newEntry = rtimer
					oldEntry = rtimer
					break
				elif config.plugins.autotimer.try_guessing.value:
					if timer.hasOffset():
						# Remove custom Offset
						rbegin = rtimer.begin + timer.offset[0] * 60
						rend = rtimer.end - timer.offset[1] * 60
					else:
						# Remove E2 Offset
						rbegin = rtimer.begin + config.recording.margin_before.value * 60
						rend = rtimer.end - config.recording.margin_after.value * 60
					# As alternative we could also do a epg lookup
					#revent = epgcache.lookupEventId(rtimer.service_ref.ref, rtimer.eit)
					#rbegin = revent.getBeginTime() or 0
					#rduration = revent.getDuration() or 0
					#rend = rbegin + rduration or 0
					if getTimeDiff(rbegin, rend, evtBegin, evtEnd) > ((duration/10)*8) or timeSimilarityPercent(rtimer, evtBegin, evtEnd, timer) > 80:
						oldExists = True
						doLog("[AutoTimer] We found a timer based on time guessing")
						newEntry = rtimer
						oldEntry = rtimer
						break
				if timer.avoidDuplicateDescription >= 1 \
					and not rtimer.disabled:
						if self.checkDuplicates(timer, name, rtimer.name, shortdesc, rtimer.description, extdesc, rtimer.extdesc ):
						# if searchForDuplicateDescription > 1 then check short description
							oldExists = True
							doLog("[AutoTimer] We found a timer (similar service) with same description, skipping event")
							break

			# We found no timer we want to edit
			if newEntry is None:
				# But there is a match
				if oldExists:
					doLog("[AutoTimer] Skipping an event because a timer on same service exists")
					skipped.append((name, begin, end, serviceref, timer.name, getLog()))
					continue

				# We want to search for possible doubles
				if timer.avoidDuplicateDescription >= 2:
					for rtimer in chain.from_iterable( itervalues(timerdict) ):
						if not rtimer.disabled:
							if self.checkDuplicates(timer, name, rtimer.name, shortdesc, rtimer.description, extdesc, rtimer.extdesc ):
								oldExists = True
								doLog("[AutoTimer] We found a timer (any service) with same description, skipping event")
								break
					if oldExists:
						doLog("[AutoTimer] Skipping an event because a timer on any service exists")
						skipped.append((name, begin, end, serviceref, timer.name, getLog()))
						continue

				if timer.checkCounter(timestamp):
					doLog("[AutoTimer] Not adding new timer because counter is depleted.")
					skipped.append((name, begin, end, serviceref, timer.name, getLog()))
					continue
			# Append to timerlist and abort if simulating
			timers.append((name, begin, end, serviceref, timer.name, getLog()))
			if simulateOnly:
				continue

			if newEntry is not None:
				# Abort if we don't want to modify timers or timer is repeated
				if config.plugins.autotimer.refresh.value == "none" or newEntry.repeated:
					doLog("[AutoTimer] Won't modify existing timer because either no modification allowed or repeated timer")
					continue

				if "autotimer" in newEntry.flags:
					msg = "[AutoTimer] AutoTimer %s modified this automatically generated timer." % (timer.name)
					doLog(msg)
					newEntry.log(501, msg)
				else:
					if config.plugins.autotimer.refresh.value != "all":
						doLog("[AutoTimer] Won't modify existing timer because it's no timer set by us")
						continue

					msg = "[AutoTimer] Warning, AutoTimer %s messed with a timer which might not belong to it: %s ." % (timer.name, newEntry.name)
					doLog(msg)
					newEntry.log(501, msg)

				if allow_modify:
					if self.modifyTimer(newEntry, name, shortdesc, begin, end, serviceref, eit, base_timer=timer):
						msg = "[AutoTimer] AutoTimer modified timer: %s ." % (newEntry.name)
						doLog(msg)
						newEntry.log(501, msg)
						modified += 1
					else:
						msg = "[AutoTimer] AutoTimer modification not allowed for timer %s because conflicts or double timer." % (newEntry.name)
						doLog(msg)
						if oldEntry:
							self.setOldTimer(newEntry, oldEntry)
							doLog("[AutoTimer] conflict for modification timer %s detected return to old timer" % (newEntry.name))
						continue
				else:
					msg = "[AutoTimer] AutoTimer modification not allowed for timer: %s ." % (newEntry.name)
					doLog(msg)
					continue
			else:
				newEntry = RecordTimerEntry(ServiceReference(serviceref), begin, end, name, shortdesc, eit)
				newAT = True

				msg = "[AutoTimer] Try to add new timer based on AutoTimer %s." % (timer.name)
				doLog(msg)
				newEntry.log(500, msg)

				# Mark this entry as AutoTimer
				newEntry.flags.add("autotimer")

			# Apply afterEvent
			if timer.hasAfterEvent():
				afterEvent = timer.getAfterEventTimespan(localtime(end))
				if afterEvent is None:
					afterEvent = timer.getAfterEvent()
				if afterEvent is not None:
					newEntry.afterEvent = afterEvent

			newEntry.dirname = dest
			newEntry.calculateFilename()
			newEntry.justplay = timer.justplay
			newEntry.vpsplugin_enabled = timer.vps_enabled
			newEntry.vpsplugin_overwrite = timer.vps_overwrite
			newEntry.conflict_detection = timer.conflict_detection
			newEntry.always_zap = timer.always_zap
			newEntry.zap_wakeup = timer.zap_wakeup

			tags = timer.tags[:]
			if config.plugins.autotimer.add_autotimer_to_tags.value:
				if 'AutoTimer' not in tags:
					tags.append('AutoTimer')
			if config.plugins.autotimer.add_name_to_tags.value:
				tagname = timer.name.strip()
				if tagname:
					tagname = tagname[0].upper() + tagname[1:].replace(" ", "_")
					if tagname not in tags:
						tags.append(tagname)
			newEntry.tags = tags

			if oldExists and newAT is None:
				if self.isResolvedConflict(newEntry):
					recordHandler.timeChanged(newEntry)
				else:
					if oldEntry:
						self.setOldTimer(newEntry, oldEntry)
						doLog("[AutoTimer] rechecking - conflict for timer %s detected return to old timer" % (newEntry.name))
					continue
			elif newAT:
				newAT = newEntry
				conflictString = ""
				if similarTimer:
					conflictString = similardict[eit].conflictString
					msg = "[AutoTimer] Try to add similar Timer because of conflicts with %s." % (conflictString)
					doLog(msg)
					newEntry.log(504, msg)

				# add new timer in AT timer list
				atDoubleTimer = False
				refstr = ':'.join(newEntry.service_ref.ref.toString().split(':')[:11])
				for at in addNewTimers:
					needed_ref = ':'.join(at.service_ref.ref.toString().split(':')[:11]) == refstr
					if needed_ref and at.eit == newEntry.eit and (newEntry.begin < at.begin <= newEntry.end or at.begin <= newEntry.begin <= at.end):
						atDoubleTimer = True
						break
				if atDoubleTimer:
					doLog("[AutoTimer] ignore double new auto timer %s." % newEntry.name)
					continue
				else:
					addNewTimers.append(newEntry)

				# Try to add timer
				conflicts = recordHandler.record(newEntry)

				if conflicts:
					# Maybe use newEntry.log
					conflictString += ' / '.join(["%s (%s)" % (x.name, strftime("%Y%m%d %H%M", localtime(x.begin))) for x in conflicts])
					doLog("[AutoTimer] conflict with %s detected" % (conflictString))

					if config.plugins.autotimer.addsimilar_on_conflict.value:
						# We start our search right after our actual index
						# Attention we have to use a copy of the list, because we have to append the previous older matches
						lepgm = len(epgmatches)
						for i in xrange(lepgm):
							servicerefS, eitS, nameS, beginS, durationS, shortdescS, extdescS = epgmatches[ (i+idx+1)%lepgm ]
							if self.checkDuplicates(timer, name, nameS, shortdesc, shortdescS, extdesc, extdescS, force=True ):
								# Check if the similar is already known
								if eitS not in similardict:
									doLog("[AutoTimer] Found similar Timer: " + name)

									# Store the actual and similar eit and conflictString, so it can be handled later
									newEntry.conflictString = conflictString
									similardict[eit] = newEntry
									similardict[eitS] = newEntry
									similarTimer = True
									if beginS <= evtBegin:
										# Event is before our actual epgmatch so we have to append it to the epgmatches list
										epgmatches.append((servicerefS, eitS, nameS, beginS, durationS, shortdescS, extdescS))
									# If we need a second similar it will be found the next time
								else:
									similarTimer = False
									newEntry = similardict[eitS]
								break

				if conflicts is None:
					timer.decrementCounter()
					if newEntry in (recordHandler.timer_list[:] + recordHandler.processed_timers[:]):
						new += 1
						newEntry.extdesc = extdesc
						timerdict[serviceref].append(newEntry)

						# Similar timers are in new timers list and additionally in similar timers list
						if similarTimer:
							similars.append((name, begin, end, serviceref, timer.name))
							similardict.clear()
					else:
						doLog("[AutoTimer] ignore double timer %s." % newEntry.name)

				# Don't care about similar timers
				elif not similarTimer:
					conflicting.append((name, begin, end, serviceref, timer.name))

					if config.plugins.autotimer.disabled_on_conflict.value:
						msg = "[AutoTimer] Timer disabled because of conflicts with %s." % (conflictString)
						doLog(msg)
						newEntry.log(503, msg)
						newEntry.disabled = True
						if newEntry in (recordHandler.timer_list[:] + recordHandler.processed_timers[:]):
							recordHandler.timeChanged(newEntry)
						else:
							# We might want to do the sanity check locally so we don't run it twice - but I consider this workaround a hack anyway
							conflicts = recordHandler.record(newEntry)
					elif newAT != newEntry and newEntry in (recordHandler.timer_list[:] + recordHandler.processed_timers[:]):
						if not self.isResolvedConflict(newEntry):
							newEntry.disabled = True
							recordHandler.timeChanged(newEntry)
							doLog("[AutoTimer] Unknown conflict, disable this timer %s." % newEntry.name)

		return (new, modified)

	def parseEPG(self, simulateOnly=False, uniqueId=None, callback=None):
 
		from plugin import AUTOTIMER_VERSION
		doLog("AutoTimer Version: " + AUTOTIMER_VERSION)

		if NavigationInstance.instance is None:
			doLog("[AutoTimer] Navigation is not available, can't parse EPG")
			return (0, 0, 0, [], [], [])

		if self.isParseRunning:
			doLog("[AutoTimer] parse EPG it is already running, return zero, test only")
			#return (0, 0, 0, [], [], [])
		else:
			self.isParseRunning = True

		new = 0
		modified = 0
		timers = []
		conflicting = []
		similars = []
		skipped = []

		# Init new added timers list
		global addNewTimers
		addNewTimers = []

		if currentThread().getName() == 'MainThread':
			doBlockingCallFromMainThread = lambda f, *a, **kw: f(*a, **kw)
		else:
			doBlockingCallFromMainThread = blockingCallFromMainThread

		# NOTE: the config option specifies "the next X days" which means today (== 1) + X
		delta = timedelta(days = config.plugins.autotimer.maxdaysinfuture.value + 1)
		evtLimit = mktime((date.today() + delta).timetuple())
		checkEvtLimit = delta.days > 1
		del delta

		# Read AutoTimer configuration
		self.readXml()

		# Get E2 instances
		epgcache = eEPGCache.getInstance()
		serviceHandler = eServiceCenter.getInstance()
		recordHandler = NavigationInstance.instance.RecordTimer

		# Save Timer in a dict to speed things up a little
		# We include processed timers as we might search for duplicate descriptions
		# NOTE: It is also possible to use RecordTimer isInTimer(), but we won't get the timer itself on a match
		timerdict = defaultdict(list)
		doBlockingCallFromMainThread(self.populateTimerdict, epgcache, recordHandler, timerdict)

		# Create dict of all movies in all folders used by an autotimer to compare with recordings
		# The moviedict will be filled only if one AutoTimer is configured to avoid duplicate description for any recordings
		moviedict = defaultdict(list)

		# Iterate Timer
		for timer in self.getEnabledTimerList():
			if uniqueId is None or timer.id == uniqueId:
				tup = doBlockingCallFromMainThread(self.parseTimer, timer, epgcache, serviceHandler, recordHandler, checkEvtLimit, evtLimit, timers, conflicting, similars, skipped, timerdict, moviedict, simulateOnly=simulateOnly)
				if callback:
					callback(timers, conflicting, similars, skipped)
					del timers[:]
					del conflicting[:]
					del similars[:]
					del skipped[:]
				else:
					new += tup[0]
					modified += tup[1]

		if not simulateOnly:
 			if sp_showResult is not None:
				blockingCallFromMainThread(sp_showResult)

			if config.plugins.autotimer.remove_double_and_conflicts_timers.value != "no":
				self.reloadTimerList(recordHandler)

		# Set status finished
		self.isParseRunning = False

		return (len(timers), new, modified, timers, conflicting, similars)

# Supporting functions

	def reloadTimerList(self, recordHandler):
		doLog("[AutoTimer] Start reload timers list after search")
		# checking and deleting duplicate timers
		disabled_at = removed_at = 0
		check_timer_list = recordHandler.timer_list[:]
		for timer in check_timer_list:
			check_timer_list.remove(timer)
			timersanitycheck = TimerSanityCheck(check_timer_list, timer)
			if not timersanitycheck.check():
				simulTimerList = timersanitycheck.getSimulTimerList()
				if simulTimerList and timer in simulTimerList and "autotimer" in timer.flags and not timer.isRunning():
					timer.disabled = True
					recordHandler.timeChanged(timer)
					disabled_at += 1
					conflictString += ' / '.join(["%s (%s)" % (x.name, strftime("%Y%m%d %H%M", localtime(x.begin))) for x in simulTimerList])
					doLog("[AutoTimer-reload] Timer %s disabled because of conflicts with %s." % (timer.name, conflictString))
			elif timersanitycheck.doubleCheck() and "autotimer" in timer.flags and not timer.isRunning():
				try:
					recordHandler.removeEntry(timer)
					removed_at += 1
					doLog("[AutoTimer-reload] Remove double timer %s."% (timer.name))
				except:
					doLog("[AutoTimer-reload] Error for remove double timer %s."% (timer.name))
		if config.plugins.autotimer.remove_double_and_conflicts_timers.value == "yes_notify":
			if Standby.inStandby is None and (disabled_at or removed_at):
				AddPopup(_("Reload timers list.\n%d autotimer(s) disabled because conflict.\n%d double autotimer(s) removed.\n") % (disabled_at, removed_at), MessageBox.TYPE_INFO, config.plugins.autotimer.popup_timeout.value, CONFLICTINGDOUBLEID)

	def populateTimerdict(self, epgcache, recordHandler, timerdict):
		remove = []
		for timer in chain(recordHandler.timer_list, recordHandler.processed_timers):
			if timer and timer.service_ref:
				if timer.eit is not None:
					event = epgcache.lookupEventId(timer.service_ref.ref, timer.eit)
					if event:
						timer.extdesc = event.getExtendedDescription()
					else:
						remove.append(timer)
				else:
					remove.append(timer)
					continue

				if not hasattr(timer, 'extdesc'):
					timer.extdesc = ''

				timerdict[str(timer.service_ref)].append(timer)

		if config.plugins.autotimer.check_eit_and_remove.value:
			for timer in remove:
				if "autotimer" in timer.flags:
					try:
						# Because of the duplicate check, we only want to remove future timer
						if timer in recordHandler.timer_list:
							if not timer.isRunning():
								recordHandler.removeEntry(timer)
								doLog("[AutoTimer] Remove timer because of eit check %s." % (timer.name))
					except:
						pass
		del remove

	def isResolvedConflict(self, checktimer=None):
		if checktimer:
			check_timer_list = NavigationInstance.instance.RecordTimer.timer_list[:]
			if checktimer in check_timer_list:
				check_timer_list.remove(checktimer)
			timersanitycheck = TimerSanityCheck(check_timer_list, checktimer)
			if not timersanitycheck.check():
					return False
			elif timersanitycheck.doubleCheck():
				return False
			else:
				return True
		return False

	def modifyTimer(self, timer, name, shortdesc, begin, end, serviceref, eit=None, base_timer=None):
		if base_timer:
			timer.justplay = base_timer.justplay
			timer.conflict_detection = base_timer.conflict_detection
			timer.always_zap = base_timer.always_zap
		timer.name = name
		timer.description = shortdesc
		timer.begin = int(begin)
		timer.end = int(end)
		timer.service_ref = ServiceReference(serviceref)
		if eit: 
			timer.eit = eit
		if base_timer:
			check_timer_list = NavigationInstance.instance.RecordTimer.timer_list[:]
			if timer in check_timer_list:
				check_timer_list.remove(timer)
			timersanitycheck = TimerSanityCheck(check_timer_list, timer)
			if not timersanitycheck.check():
				return False
			elif timersanitycheck.doubleCheck():
				return False
			else:
				doLog("[AutoTimer] conflict not found for modify timer %s." % timer.name)
		return True

	def setOldTimer(self, new_timer=None, old_timer=None):
		if new_timer and old_timer:
			new_timer.justplay = old_timer.justplay
			new_timer.conflict_detection = old_timer.conflict_detection
			new_timer.always_zap = old_timer.always_zap
			new_timer.name = old_timer.name
			new_timer.description = old_timer.description
			new_timer.begin = old_timer.begin
			new_timer.end = old_timer.end
			new_timer.service_ref = old_timer.service_ref
			new_timer.eit = old_timer.eit
			new_timer.disabled = old_timer.disabled

	def addDirectoryToMovieDict(self, moviedict, dest, serviceHandler):
		movielist = serviceHandler.list(eServiceReference("2:0:1:0:0:0:0:0:0:0:" + dest))
		if movielist is None:
			doLog("[AutoTimer] listing of movies in " + dest + " failed")
		else:
			append = moviedict[dest].append
			while 1:
				movieref = movielist.getNext()
				if not movieref.valid():
					break
				if movieref.flags & eServiceReference.mustDescent:
					continue
				info = serviceHandler.info(movieref)
				if info is None:
					continue
				event = info.getEvent(movieref)
				if event is None:
					continue
				append({
					"name": info.getName(movieref),
					"shortdesc": info.getInfoString(movieref, iServiceInformation.sDescription),
					"extdesc": event.getExtendedDescription() or '' # XXX: does event.getExtendedDescription() actually return None on no description or an empty string?
				})

	def checkDuplicatesOE(self, timer, name1, name2, shortdesc1, shortdesc2, extdesc1, extdesc2, force=False):
		foundTitle = False
		foundShort = False
		retValue = False
		if name1 and name2:
			foundTitle = ( 0.8 < SequenceMatcher(lambda x: x == " ",name1, name2).ratio() )
		# NOTE: only check extended & short if tile is a partial match
		if foundTitle:
			if timer.searchForDuplicateDescription > 0 or force:
				if shortdesc1 and shortdesc2:
					# If the similarity percent is higher then 0.7 it is a very close match
					foundShort = ( 0.7 < SequenceMatcher(lambda x: x == " ",shortdesc1, shortdesc2).ratio() )
					if foundShort:
						if timer.searchForDuplicateDescription == 3:
							if extdesc1 and extdesc2:
								# Some channels indicate replays in the extended descriptions
								# If the similarity percent is higher then 0.7 it is a very close match
								retValue = ( 0.7 < SequenceMatcher(lambda x: x == " ",extdesc1, extdesc2).ratio() )
						else:
							retValue = True
			else:
				retValue = True
		return retValue

	def checkDuplicates(self, timer, name1, name2, shortdesc1, shortdesc2, extdesc1, extdesc2, force=False):
		if name1 and name2:
			sequenceMatcher = SequenceMatcher(" ".__eq__, name1, name2)
		else:
			return False

		ratio = sequenceMatcher.ratio()
		ratio_value = force and 0.8 or timer.ratioThresholdDuplicate
		doDebug("[AutoTimer] names ratio %f - %s - %d - %s - %d" % (ratio, name1, len(name1), name2, len(name2)))
		if name1 in name2 or (0.8 < ratio): # this is probably a match
			foundShort = True
			if (force or timer.searchForDuplicateDescription > 0) and shortdesc1 and shortdesc2:
				sequenceMatcher.set_seqs(shortdesc1, shortdesc2)
				ratio = sequenceMatcher.ratio()
				doDebug("[AutoTimer] shortdesc ratio %f - %s - %d - %s - %d" % (ratio, shortdesc1, len(shortdesc1), shortdesc2, len(shortdesc2)))
				foundShort = shortdesc1 in shortdesc2 or ((ratio_value < ratio) or (ratio_value == 1.0 and ratio_value == ratio))
				if foundShort:
					doLog("[AutoTimer] shortdesc ratio %f - %s - %d - %s - %d" % (ratio, shortdesc1, len(shortdesc1), shortdesc2, len(shortdesc2)))
			elif not force and timer.descShortExtEmpty and not shortdesc1 and not shortdesc2 and name1 != name2:
				foundShort = False

			foundExt = True
			# NOTE: only check extended if short description already is a match because otherwise
			# it won't evaluate to True anyway
			if foundShort and (force or timer.searchForDuplicateDescription > 1) and extdesc1 and extdesc2:
				sequenceMatcher.set_seqs(extdesc1, extdesc2)
				ratio = sequenceMatcher.ratio()
				doDebug("[AutoTimer] extdesc ratio %f - %s - %d - %s - %d" % (ratio, extdesc1, len(extdesc1), extdesc2, len(extdesc2)))
				foundExt = (ratio_value < ratio) or (ratio_value == 1.0 and ratio_value == ratio)
				if foundExt:
					doLog("[AutoTimer] extdesc ratio %f - %s - %d - %s - %d" % (ratio, extdesc1, len(extdesc1), extdesc2, len(extdesc2)))
			elif not force and timer.descShortExtEmpty and not extdesc1 and not extdesc2 and name1 != name2:
				foundExt = False
			return foundShort and foundExt
		return False
