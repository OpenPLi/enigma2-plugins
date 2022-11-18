from __future__ import print_function

# Plugins Config
from xml.etree.cElementTree import parse as cet_parse, fromstring as cet_fromstring
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
from Tools.XMLTools import stringToXML
from Screens import Standby
from Screens.MessageBox import MessageBox

# Timespan
from time import localtime, strftime, time, mktime, ctime
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
except:
	sp_getSeasonEpisode = None

try:
	from Plugins.Extensions.SeriesPlugin.plugin import showResult as sp_showResult
except:
	sp_showResult = None

try:
	from Plugins.SystemPlugins.vps import Vps
	hasVps = True
except:
	hasVps = False

from . import config, xrange, itervalues

CONFLICTINGDOUBLEID = 'AutoTimerConflictingDoubleTimersNotification'
addNewTimers = []

XML_CONFIG = "/etc/enigma2/autotimer.xml"


def timeSimilarityPercent(rtimer, evtBegin, evtEnd, timer=None):
	if (timer is not None) and (timer.offset is not None):
		# remove custom offset from rtimer using timer.offset as RecordTimerEntry doesn't store the offset
		rtimerBegin = rtimer.begin + timer.offset[0]
		rtimerEnd = rtimer.end - timer.offset[1]
	else:
		# remove E2 offset
		rtimerBegin = rtimer.begin + config.recording.margin_before.value * 60
		rtimerEnd = rtimer.end - config.recording.margin_after.value * 60
	#commonTime = max(min(evtEnd, rtimerEnd) - max(evtBegin, rtimerBegin), 0)
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
		commonTime_percent = 100 * commonTime / (evtEnd - evtBegin)
	else:
		return 0
	if rtimerEnd != rtimerBegin:
		durationMatch_percent = 100 * (evtEnd - evtBegin) / (rtimerEnd - rtimerBegin)
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
			result = queue.get(True, config.plugins.autotimer.timeout.value * 60)
		except Queue.Empty as qe:
			if True: #not reactor.running: # reactor.running is only False AFTER shutdown, we are during.
				doLog("[AutoTimer] Reactor no longer active, aborting.")
		else:
			break

	if isinstance(result, failure.Failure):
		print("[AutoTimer]", result.getTraceback())
		doLog(result.getTraceback())
		result.raiseException()
	return result


typeMap = {
	"exact": eEPGCache.EXAKT_TITLE_SEARCH,
	"partial": eEPGCache.PARTIAL_TITLE_SEARCH,
	"start": eEPGCache.START_TITLE_SEARCH,
	"end": eEPGCache.END_TITLE_SEARCH,
	"description": eEPGCache.PARTIAL_DESCRIPTION_SEARCH,
	"favoritedesc": -99
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
		self.configMtime = -1
		self.uniqueTimerId = 0
		self.defaultTimer = preferredAutoTimerComponent(
			0,		# Id
			"",		# Name
			"",		# Match
			True 	# Enabled
		)

# Configuration

	def readXml(self, **kwargs):
		if "xml_string" in kwargs:
			# reset time
			self.configMtime = -1
			# Parse Config
			try:
				configuration = cet_fromstring(kwargs["xml_string"])
			except:
				doLog("[AutoTimer] fatal error, the xml_string not read")
				return
		else:
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
					if os.path.exists(XML_CONFIG + "_old"):
						os.rename(XML_CONFIG + "_old", XML_CONFIG + "_old(1)")
					os.rename(XML_CONFIG, XML_CONFIG + "_old")
					doLog("[AutoTimer] autotimer.xml is corrupt rename file to /etc/enigma2/autotimer.xml_old")
				except:
					pass
				if Standby.inStandby is None:
					AddPopup(_("The autotimer file (/etc/enigma2/autotimer.xml) is corrupt and could not be loaded.") + "\n" + _("A new and empty config was created. A backup of the config can be found here (/etc/enigma2/autotimer.xml_old)."), type=MessageBox.TYPE_ERROR, timeout=0, id="AutoTimerLoadFailed")

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

	def getXml(self, webif=True):
		return buildConfig(self.defaultTimer, self.timers, webif)

	def writeXml(self):
		file = open(XML_CONFIG, 'w')
		file.writelines(buildConfig(self.defaultTimer, self.timers))
		file.close()

	def writeXmlTimer(self, timers):
		return ''.join(buildConfig(self.defaultTimer, timers))

	def readXmlTimer(self, xml_string):
		# Parse xml string
		try:
			configuration = cet_fromstring(xml_string)
		except:
			doLog("[AutoTimer] fatal error, the xml_string not read")
			return
		parseConfig(
			configuration,
			self.timers,
			configuration.get("version"),
			self.uniqueTimerId,
			self.defaultTimer
		)
		self.uniqueTimerId += 1

		# reset time
		self.configMtime = -1

# Manage List
	def add(self, timer):
		self.timers.append(timer)

	def getEnabledTimerList(self):
		return sorted([x for x in self.timers if x.enabled], key=lambda x: x.name)

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

	def parseEPGAsync(self, simulateOnly=False):
		t = SimpleThread(lambda: self.parseEPG(simulateOnly=simulateOnly))
		t.start()
		return t.deferred

# Main function

	def parseTimer(self, timer, epgcache, serviceHandler, recordHandler, checkEvtLimit, evtLimit, timers, conflicting, similars, skipped, timerdict, moviedict, simulateOnly=False):
		new = 0
		modified = 0

		# enable multiple timer if services or bouquets specified (eg. recording the same event on sd service and hd service)
		enable_multiple_timer = ((timer.services and 's' in config.plugins.autotimer.enable_multiple_timer.value or False) or (timer.bouquets and 'b' in config.plugins.autotimer.enable_multiple_timer.value or False))

		# Workaround to allow search for umlauts if we know the encoding
		match = timer.match.replace('\xc2\x86', '').replace('\xc2\x87', '')
		if timer.encoding != 'UTF-8':
			try:
				match = match.decode('UTF-8').encode(timer.encoding)
			except UnicodeDecodeError:
				pass

		self.isIPTV = bool([service for service in timer.services if ":http" in service])

		if timer.searchType == "favoritedesc" or self.isIPTV:
			epgmatches = []

			casesensitive = timer.searchCase == "sensitive"
			if not casesensitive:
				match = match.lower()

			test = []
			if timer.services or timer.bouquets:
				if timer.services:
					test = [(service, 0, -1, -1) for service in timer.services]
				if timer.bouquets:
					for bouquet in timer.bouquets:
						services = serviceHandler.list(eServiceReference(bouquet))
						if services:
							while True:
								service = services.getNext()
								if not service.valid():
									break
								playable = not (service.flags & (eServiceReference.isMarker | eServiceReference.isDirectory | eServiceReference.isNumberedMarker))
								if playable:
									test.append((service.toString(), 0, -1, -1))
			else: # Get all bouquets
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
									bouquetlist.append(s)
				else:
					service_types_tv = '1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 22) || (type == 25) || (type == 31) || (type == 134) || (type == 195)'
					refstr = '%s FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet' % (service_types_tv)
					bouquetroot = eServiceReference(refstr)
					info = serviceHandler.info(bouquetroot)
					if info and bouquetroot.valid() and not bouquetroot.flags & eServiceReference.isInvisible:
						bouquetlist.append(bouquetroot)
				if bouquetlist:
					for bouquet in bouquetlist:
						if not bouquet.valid():
							continue
						if bouquet.flags & eServiceReference.isDirectory:
							services = serviceHandler.list(bouquet)
							if services:
								while True:
									service = services.getNext()
									if not service.valid():
										break
									playable = not (service.flags & (eServiceReference.isMarker | eServiceReference.isDirectory | eServiceReference.isNumberedMarker))
									if playable:
										test.append((service.toString(), 0, -1, -1))

			if test:
				# Get all events
				#  eEPGCache.lookupEvent( [ format of the returned tuples, ( service, 0 = event intersects given start_time, start_time -1 for now_time), ] )
				test.insert(0, 'RITBDSE')
				allevents = epgcache.lookupEvent(test) or []

				# Filter events
				for serviceref, eit, name, begin, duration, shortdesc, extdesc in allevents:
					if timer.searchType == "favoritedesc":
						if match in (shortdesc if casesensitive else shortdesc.lower()) or match in (extdesc if casesensitive else extdesc.lower()) or match in (name if casesensitive else name.lower()):
							epgmatches.append((serviceref, eit, name, begin, duration, shortdesc, extdesc))
					else: # IPTV streams
						if timer.searchType == "exact" and match == (name if casesensitive else name.lower()) or \
							timer.searchType == "partial" and match in (name if casesensitive else name.lower()) or \
							timer.searchType == "start" and (name if casesensitive else name.lower()).startswith(match) or \
							timer.searchType == "end" and (name if casesensitive else name.lower()).endswith(match) or \
							timer.searchType == "description" and (match in (shortdesc if casesensitive else shortdesc.lower()) or match in (extdesc if casesensitive else extdesc.lower())):
							epgmatches.append((serviceref, eit, name, begin, duration, shortdesc, extdesc))

		else:
			# Search EPG, default to empty list
			epgmatches = epgcache.search(('RITBDSE', int(config.plugins.autotimer.max_search_events_match.value), typeMap[timer.searchType], match, caseMap[timer.searchCase])) or []

		# Sort list of tuples by begin time 'B'
		epgmatches.sort(key=itemgetter(3))

		# Contains the the marked similar eits and the conflicting strings
		similardict = defaultdict(list)

		dayofweek_exclude = timer.exclude[3]
		if dayofweek_exclude:
			dayofweek_exclude_values = dayofweek_exclude[:]
			if "weekend" in dayofweek_exclude_values:
				dayofweek_exclude_values.extend(("5", "6"))
			if "weekday" in dayofweek_exclude_values:
				dayofweek_exclude_values.extend(("0", "1", "2", "3", "4"))
		dayofweek_include = timer.include[3]
		if dayofweek_include:
			dayofweek_include_values = dayofweek_include[:]
			if "weekend" in dayofweek_include_values:
				dayofweek_include_values.extend(("5", "6"))
			if "weekday" in dayofweek_include_values:
				dayofweek_include_values.extend(("0", "1", "2", "3", "4"))

		# Loop over all EPG matches
		for idx, (serviceref, eit, name, begin, duration, shortdesc, extdesc) in enumerate(epgmatches):
			startLog()

			# timer destination dir
			dest = timer.destination or config.usage.default_path.value

			evtBegin = begin
			evtEnd = end = begin + duration

			doLog("[AutoTimer] possible epgmatch %s" % (name))
			doLog("[AutoTimer] Serviceref %s" % serviceref)
			eserviceref = eServiceReference(serviceref)
			evt = epgcache.lookupEventId(eserviceref, eit)
			if not evt:
				doLog("[AutoTimer] Could not create Event!")
				skipped.append((name, begin, end, serviceref, timer.name, getLog()))
				continue
			# Try to determine real service (we always choose the last one)
			#n = evt.getNumOfLinkageServices()
			#if n > 0:
			#	i = evt.getLinkageService(eserviceref, n-1)
			#	serviceref = i.toString()
			#	doLog("[AutoTimer] Serviceref2 %s" % serviceref)

			# If event starts in less than 60 seconds skip it
			if begin < time() + 60:
				doLog("[AutoTimer] Skipping an event because it starts in less than 60 seconds")
				skipped.append((name, begin, end, serviceref, timer.name, getLog()))
				continue

			# Set short description to equal extended description if it is empty.
			if not shortdesc and timer.descShortEqualExt and extdesc:
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

				current_dayofweek = tdow = timestamp.tm_wday
				if (timer.timespan[0] != None) and timer.timespan[2]:
					begin_offset = 60 * timestamp.tm_hour + timestamp.tm_min
					timer_offset = 60 * timer.timespan[0][0] + timer.timespan[0][1]
					if begin_offset < timer_offset:
						tdow = (tdow - 1) % 7
				dayofweek = str(tdow)

				# Update dayofweek when programmes that cross midnight and have a dayofweek filter
				if str(current_dayofweek) == dayofweek and (dayofweek_exclude or dayofweek_include):
					end_timestamp = localtime(end)
					end_dayofweek = str(end_timestamp.tm_wday)
					#if timestamp.tm_hour == 0 and timestamp.tm_min == 0:
					#	current_dayofweek = (current_dayofweek - 1) % 7
					#	if str(current_dayofweek) != end_dayofweek:
					#		dayofweek = str(current_dayofweek)
					if dayofweek != end_dayofweek:
						if dayofweek_exclude:
							if dayofweek in dayofweek_exclude_values:
								if not end_dayofweek in dayofweek_exclude_values:
									doLog("[AutoTimer] [AutoTimer] Update dayofweek by reason of exclude dayofweek filter")
									dayofweek = end_dayofweek
						if dayofweek_include and dayofweek != end_dayofweek:
							if not dayofweek in dayofweek_include_values:
								if end_dayofweek in dayofweek_include_values:
									doLog("[AutoTimer] [AutoTimer] Update dayofweek by reason of include dayofweek filter")
									dayofweek = end_dayofweek

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
				sp = sp_getSeasonEpisode(serviceref, name, evtBegin, evtEnd, shortdesc, dest, True)
				if sp and type(sp) in (tuple, list) and len(sp) > 3:
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
						sp = sp_getSeasonEpisode(serviceref, timer.name, evtBegin, evtEnd, shortdesc, dest, True)
						if sp and type(sp) in (tuple, list) and len(sp) > 3:
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
				offsetBegin = timer.offset[0]
				offsetEnd = timer.offset[1]
			else:
				# Apply E2 Offset
				begin -= config.recording.margin_before.value * 60
				end += config.recording.margin_after.value * 60
				offsetBegin = config.recording.margin_before.value * 60
				offsetEnd = config.recording.margin_after.value * 60

			# Overwrite endtime if requested
			if timer.justplay and not timer.setEndtime:
				end = begin
				evtEnd = evtBegin

			# Check for existing recordings in directory
			if timer.avoidDuplicateDescription == 3:
				# Reset movie Exists
				movieExists = False

				if dest and dest not in moviedict:
					self.addDirectoryToMovieDict(moviedict, dest, serviceHandler)
				for movieinfo in moviedict.get(dest, ()):
					if self.checkSimilarity(timer, name, movieinfo.get("name"), shortdesc, movieinfo.get("shortdesc"), extdesc, movieinfo.get("extdesc"), isMovie=True):
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
				try: # protect against vps plugin not being present
					vps_changed = hasVps and (rtimer.vpsplugin_enabled != timer.vps_enabled or rtimer.vpsplugin_overwrite != timer.vps_overwrite)
				except:
					vps_changed = False
				time_changed = (evtBegin - offsetBegin != rtimer.begin) or (evtEnd + offsetEnd != rtimer.end)
				desc_changed = (timer.avoidDuplicateDescription >= 1 and shortdesc and rtimer.description and shortdesc != rtimer.description) or (timer.avoidDuplicateDescription >= 2 and extdesc and rtimer.extdesc and extdesc != rtimer.extdesc)
				if rtimer.eit == eit:
					oldExists = True
					doLog("[AutoTimer] We found a timer based on eit")
					if time_changed or desc_changed or vps_changed:
						newEntry = rtimer
						oldEntry = [rtimer.name, rtimer.description, rtimer.extdesc, rtimer.begin, rtimer.end, rtimer.service_ref, rtimer.eit, rtimer.disabled]
					break
				elif config.plugins.autotimer.try_guessing.value:
					if timeSimilarityPercent(rtimer, evtBegin, evtEnd, timer) > 80:
						oldExists = True
						doLog("[AutoTimer] We found a timer based on time guessing")
						if time_changed or desc_changed or vps_changed:
							newEntry = rtimer
							oldEntry = [rtimer.name, rtimer.description, rtimer.extdesc, rtimer.begin, rtimer.end, rtimer.service_ref, rtimer.eit, rtimer.disabled]
						break
				if oldExists is None and timer.avoidDuplicateDescription >= 1 and not rtimer.disabled:
					# searchForDuplicateDescription is 1 - check short description / searchForDuplicateDescription is 2 - check extended description
					if self.checkSimilarity(timer, name, rtimer.name, shortdesc, rtimer.description, extdesc, rtimer.extdesc):
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
				for rtimer in chain.from_iterable(itervalues(timerdict)):
					if not rtimer.disabled:
						if self.checkDoubleTimers(timer, name, rtimer.name, begin, rtimer.begin, end, rtimer.end, serviceref, rtimer.service_ref.ref.toString(), enable_multiple_timer):
							oldExists = True
							print("[AutoTimer] We found a timer with same start time, skipping event")
							break
						if timer.avoidDuplicateDescription >= 2:
							if self.checkSimilarity(timer, name, rtimer.name, shortdesc, rtimer.description, extdesc, rtimer.extdesc):
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

			# if set option for check/save timer in filterlist and only if not found an existing timer
			isnewFilterEntry = False
			if (config.plugins.autotimer.series_save_filter.value or timer.series_save_filter) and not oldExists:
				if timer.series_labeling and sp_getSeasonEpisode is not None:
					if sp and type(sp) in (tuple, list) and len(sp) == 4:
						ret = self.addToFilterfile(str(sp[0]), begin, simulateOnly)
					if sp and type(sp) in (tuple, list) and len(sp) > 3:
						filter_title = str(sp[0])
						if len(sp) > 4:
							filter_title = "{series:s} - S{season:02d}E{rawepisode:s} - {title:s}".format(**sp[4])
						ret = self.addToFilterfile(filter_title, begin, simulateOnly, str(sp[0]))
						if ret:
							if simulateOnly:
								doLog("[AutoTimer SeriesPlugin] only simulate - new Timer would be saved in autotimer_filter")
							else:
								doLog("[AutoTimer SeriesPlugin] new Timer saved in autotimer_filter")
								isnewFilterEntry = True
						else:
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

				changed = newEntry.begin != begin or newEntry.end != end or newEntry.name != name
				if allow_modify:
					if oldExists and newEntry.service_ref.ref.toString() == serviceref and newEntry.eit == eit and newEntry.name == name and newEntry.begin < begin and newEntry.end < end and (0 < begin - newEntry.end <= 600):
						begin = newEntry.begin
						doLog("[AutoTimer] This same eit and different times end - update only end")
					if self.modifyTimer(newEntry, name, shortdesc, begin, end, serviceref, eit, base_timer=timer):
						msg = "[AutoTimer] AutoTimer modified timer: %s ." % (newEntry.name)
						doLog(msg)
						newEntry.log(501, msg)
						if changed:
							self.addToSearchLogfile(newEntry, "#", simulateOnly)
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
				msg = "[AutoTimer] Timer start on: %s" % ctime(begin)
				doLog(msg)
				newEntry.log(509, msg)

				# Mark this entry as AutoTimer
				newEntry.flags.add("autotimer")
				# Mark this entry as timer name
				newEntry.flags.add(stringToXML(timer.name))

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

				if conflicts and not timer.hasOffset() and not config.recording.margin_before.value and not config.recording.margin_after.value and len(conflicts) > 1:
					change_end = change_begin = False
					conflict_begin = conflicts[1].begin
					conflict_end = conflicts[1].end
					if conflict_begin == newEntry.end:
						newEntry.end -= 30
						change_end = True
					elif newEntry.begin == conflict_end:
						newEntry.begin += 30
						change_begin = True
					if change_end or change_begin:
						conflicts = recordHandler.record(newEntry)
						if conflicts:
							if change_end:
								newEntry.end += 30
							elif change_begin:
								newEntry.begin -= 30
						else:
							doLog("[AutoTimer] The conflict is resolved by offset time begin/end (30 sec) for %s." % newEntry.name)

				if conflicts:
					# Maybe use newEntry.log
					conflictString += ' / '.join(["%s (%s)" % (x.name, strftime("%Y%m%d %H%M", localtime(x.begin))) for x in conflicts])
					doLog("[AutoTimer] conflict with %s detected" % (conflictString))

					if config.plugins.autotimer.addsimilar_on_conflict.value:
						# We start our search right after our actual index
						# Attention we have to use a copy of the list, because we have to append the previous older matches
						lepgm = len(epgmatches)
						for i in xrange(lepgm):
							servicerefS, eitS, nameS, beginS, durationS, shortdescS, extdescS = epgmatches[(i + idx + 1) % lepgm]
							if self.checkSimilarity(timer, name, nameS, shortdesc, shortdescS, extdesc, extdescS, force=True):
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
						if isnewFilterEntry:
							self.addToSearchLogfile(newEntry, "++", simulateOnly)
						else:
							self.addToSearchLogfile(newEntry, "+", simulateOnly)
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

		new = 0
		modified = 0
		timers = []
		conflicting = []
		similars = []
		skipped = []

		# Init new added timers list
		global addNewTimers
		addNewTimers = []

		if config.plugins.autotimer.searchlog_write.value and not simulateOnly:
			self.prepareSearchLogfile()

		if currentThread().getName() == 'MainThread':
			doBlockingCallFromMainThread = lambda f, *a, **kw: f(*a, **kw)
		else:
			doBlockingCallFromMainThread = blockingCallFromMainThread

		# NOTE: the config option specifies "the next X days" which means today (== 1) + X
		delta = timedelta(days=config.plugins.autotimer.maxdaysinfuture.value + 1)
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
		doBlockingCallFromMainThread(self.populateTimerdict, epgcache, recordHandler, timerdict, simulateOnly=simulateOnly)

		# Create dict of all movies in all folders used by an autotimer to compare with recordings
		# The moviedict will be filled only if one AutoTimer is configured to avoid duplicate description for any recordings
		moviedict = defaultdict(list)

		# Iterate Timer
		for timer in self.getEnabledTimerList():
			if uniqueId is None or timer.id == uniqueId:
				doLog("[AutoTimer] Start search for %s" % (timer.match.replace('\xc2\x86', '').replace('\xc2\x87', '')))
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

		return (len(timers), new, modified, timers, conflicting, similars)

# Supporting functions

	def addToSearchLogfile(self, timerEntry, entryType, simulateOnlyValue=False):
		if config.plugins.autotimer.searchlog_write.value and not simulateOnlyValue:
			#write eventname totextfile
			logpath = config.plugins.autotimer.searchlog_path.value
			if logpath == "?likeATlog?":
				logpath = os.path.dirname(config.plugins.autotimer.log_file.value)
			path_search_log = os.path.join(logpath, "autotimer_search.log")
			file_search_log = open(path_search_log, "a")
			log_txt = "(" + str(entryType) + ") "
			log_txt += str(strftime('%d.%m., %H:%M', localtime(timerEntry.begin)))
			log_txt += ' - ' + timerEntry.service_ref.getServiceName()
			log_txt += ' - "' + str(timerEntry.name) + '"\n'
			file_search_log.write(log_txt)
			file_search_log.close()

	def prepareSearchLogfile(self):
		# prepare searchlog at begin of real search (max. last 5 searches)
		logpath = config.plugins.autotimer.searchlog_path.value
		if logpath == "?likeATlog?":
			logpath = os.path.dirname(config.plugins.autotimer.log_file.value)
		path_search_log = os.path.join(logpath, "autotimer_search.log")
		searchlog_txt = ""
		if os.path.exists(path_search_log):
			searchlog_txt = open(path_search_log).read()
			#read last logs from logfile (do not change then "\n########## " in the code !!!!)
			if "\n########## " in searchlog_txt:
				searchlog_txt = searchlog_txt.split("\n########## ")
				count_logs = len(searchlog_txt)
				max_count_logs = int(config.plugins.autotimer.searchlog_max.value)
				if count_logs > max_count_logs:
					searchlog_txt = searchlog_txt[count_logs - max_count_logs + 1:]
					searchlog_txt = "\n########## " + "\n########## ".join(searchlog_txt)
				else:
					searchlog_txt = "\n########## ".join(searchlog_txt)
		searchlog_txt += "\n########## " + _("begin searchLog from") + " " + str(strftime('%d.%m.%Y, %H:%M', localtime())) + " ########\n\n"
		file_search_log = open(path_search_log, "w")
		file_search_log.write(searchlog_txt)
		file_search_log.close()

	def addToFilterfile(self, name, begin, simulateOnlyValue=False, sp_title="xxxxxxxxxxxxxxxx"):
		path_filter_txt = "/etc/enigma2/autotimer_filter.txt"
		if os.path.exists(path_filter_txt):
			search_txt = '"' + name + '"'
			search_txt_sp = '"' + sp_title + '"'
			if (search_txt or search_txt_sp) in open(path_filter_txt).read():
				print("[AutoTimer] Skipping an event because found event in autotimer_filter")
				doLog("[AutoTimer] Skipping an event because found event in autotimer_filter")
				return False
		if simulateOnlyValue:
			return True
		#write eventname totextfile
		filter_txt = str(strftime('%d.%m.%Y, %H:%M', localtime(begin))) + ' - "' + name + '"\n'
		file_filter_txt = open(path_filter_txt, "a")
		file_filter_txt.write(filter_txt)
		file_filter_txt.close()
		doLog("[AutoTimer] added a new event to autotimer_filter")
		return True

	def addToFilterList(self, session, services, *args, **kwargs):
		if services:
			serviceHandler = eServiceCenter.getInstance()
			add_counter = 0
			try:
				for service in services:
					info = serviceHandler.info(service)
					name = info and info.getName(service) or ""
					if info:
						begin = info.getInfo(service, iServiceInformation.sTimeCreate)
					else:
						doLog("[AutoTimer] No recordinfo available")
						continue
					ret = self.addToFilterfile(name, begin)
					if ret:
						add_counter += 1
				session.open(MessageBox, _("Finished add to filterList with %s event(s):\n\n %s event(s) added \n %s event(s) skipped") % (len(services), add_counter, len(services) - add_counter), type=MessageBox.TYPE_INFO, timeout=config.plugins.autotimer.popup_timeout.value)
			except Exception as e:
				doLog("[AutoTimer] Error in addToFilterList", e)
				print("[AutoTimer] ======== Error in addToFilterList ", e)

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
					doLog("[AutoTimer-reload] Remove double timer %s." % (timer.name))
				except:
					doLog("[AutoTimer-reload] Error for remove double timer %s." % (timer.name))
		if config.plugins.autotimer.remove_double_and_conflicts_timers.value == "yes_notify":
			if Standby.inStandby is None and (disabled_at or removed_at):
				AddPopup(_("Reload timers list.\n%d autotimer(s) disabled because conflict.\n%d double autotimer(s) removed.\n") % (disabled_at, removed_at), MessageBox.TYPE_INFO, config.plugins.autotimer.popup_timeout.value, CONFLICTINGDOUBLEID)

	def populateTimerdict(self, epgcache, recordHandler, timerdict, simulateOnly=False):
		remove = []
		check_eit_and_remove = config.plugins.autotimer.check_eit_and_remove.value
		for timer in chain(recordHandler.timer_list, recordHandler.processed_timers):
			if timer and timer.service_ref:
				if timer.eit is not None:
					event = epgcache.lookupEventId(timer.service_ref.ref, timer.eit)
					if event:
						timer.extdesc = event.getExtendedDescription()
					elif check_eit_and_remove and "autotimer" in timer.flags and not timer.isRunning():
						remove.append(timer)
						continue
				else:
					remove.append(timer)
					continue

				if not hasattr(timer, 'extdesc'):
					timer.extdesc = ''

				timerdict[str(timer.service_ref)].append(timer)

		if check_eit_and_remove:
			for timer in remove:
				if "autotimer" in timer.flags:
					try:
						# Because of the duplicate check, we only want to remove future timer
						if timer in recordHandler.timer_list:
							if not timer.isRunning():
								recordHandler.removeEntry(timer)
								doLog("[AutoTimer] Remove timer because of eit check %s." % (timer.name))
								self.addToSearchLogfile(timer, "-", simulateOnly)
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
			new_timer.name = old_timer[0]
			new_timer.description = old_timer[1]
			new_timer.extdesc = old_timer[2]
			new_timer.begin = old_timer[3]
			new_timer.end = old_timer[4]
			new_timer.service_ref = old_timer[5]
			new_timer.eit = old_timer[6]
			new_timer.disabled = old_timer[7]

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

	def checkSimilarityOE(self, timer, name1, name2, shortdesc1, shortdesc2, extdesc1, extdesc2, force=False):
		foundTitle = False
		foundShort = False
		retValue = False
		if name1 and name2:
			foundTitle = (0.8 < SequenceMatcher(lambda x: x == " ", name1, name2).ratio())
		# NOTE: only check extended & short if tile is a partial match
		if foundTitle:
			if timer.searchForDuplicateDescription > 0 or force:
				if shortdesc1 and shortdesc2:
					# If the similarity percent is higher then 0.7 it is a very close match
					foundShort = (0.7 < SequenceMatcher(lambda x: x == " ", shortdesc1, shortdesc2).ratio())
					if foundShort:
						if timer.searchForDuplicateDescription == 2:
							if extdesc1 and extdesc2:
								# Some channels indicate replays in the extended descriptions
								# If the similarity percent is higher then 0.7 it is a very close match
								retValue = (0.7 < SequenceMatcher(lambda x: x == " ", extdesc1, extdesc2).ratio())
						else:
							retValue = True
			else:
				retValue = True
		return retValue

	def checkSimilarity(self, timer, name1, name2, shortdesc1, shortdesc2, extdesc1, extdesc2, force=False, isMovie=False):
		if name1 and name2:
			sequenceMatcher = SequenceMatcher(" ".__eq__, name1, name2)
		else:
			return False
		retValue = False
		ratio = sequenceMatcher.ratio()
		ratio_value = force and 0.8 or timer.ratioThresholdDuplicate
		doDebug("[AutoTimer] names ratio %f - %s - %d - %s - %d" % (ratio, name1, len(name1), name2, len(name2)))
		if name1 in name2 or (0.8 < ratio): # this is probably a match
			if not force and timer.descShortExtEmpty and (((isMovie and shortdesc1 and not shortdesc2) or (not isMovie and not shortdesc1 and not shortdesc2 and name1 != name2))
				or ((isMovie and extdesc1 and not extdesc2) or (not isMovie and not extdesc1 and not extdesc2 and name1 != name2))):
				doDebug("[AutoTimer] Configuration caused this sortdesc/extdesc match to be ignored!")
				return False
			if force or timer.searchForDuplicateDescription > 0:
				if shortdesc1 and shortdesc2:
					sequenceMatcher.set_seqs(shortdesc1, shortdesc2)
					ratio = sequenceMatcher.ratio()
					doDebug("[AutoTimer] shortdesc ratio %f - %s - %d - %s - %d" % (ratio, shortdesc1, len(shortdesc1), shortdesc2, len(shortdesc2)))
					foundShort = shortdesc1 in shortdesc2 or ((ratio_value < ratio) or (ratio_value == 1.0 and ratio_value == ratio))
					doDebug("[AutoTimer] Final result for found shortdesc: %s" % foundShort)
					if foundShort:
						doLog("[AutoTimer] shortdesc match: ratio %f - %s - %d - %s - %d" % (ratio, shortdesc1, len(shortdesc1), shortdesc2, len(shortdesc2)))
						if force or timer.searchForDuplicateDescription > 1:
							if extdesc1 and extdesc2:
								sequenceMatcher.set_seqs(extdesc1, extdesc2)
								ratio = sequenceMatcher.ratio()
								doDebug("[AutoTimer] extdesc ratio %f - %s - %d - %s - %d" % (ratio, extdesc1, len(extdesc1), extdesc2, len(extdesc2)))
								retValue = (ratio_value < ratio) or (ratio_value == 1.0 and ratio_value == ratio)
								doDebug("[AutoTimer] Final result for found extdesc: %s" % retValue)
								if retValue:
									doLog("[AutoTimer] extdesc match: ratio %f - %s - %d - %s - %d" % (ratio, extdesc1, len(extdesc1), extdesc2, len(extdesc2)))
						else:
							retValue = True
			else:
				retValue = True
		return retValue

	def checkDoubleTimers(self, timer, name1, name2, starttime1, starttime2, endtime1, endtime2, serviceref1, serviceref2, multiple):
		foundTitle = name1 == name2
		foundstart = starttime1 == starttime2
		foundend = endtime1 == endtime2
		foundref = serviceref1 == serviceref2
		return foundTitle and foundstart and foundend and (foundref or not multiple)
