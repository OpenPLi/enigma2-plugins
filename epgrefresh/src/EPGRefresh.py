# -*- coding: UTF-8 -*-
from __future__ import print_function
import Screens.Standby
from enigma import eServiceReference, eServiceCenter, eTimer
from ServiceReference import ServiceReference
from EPGRefreshTimer import epgrefreshtimer, EPGRefreshTimerEntry, checkTimespan
from time import time
from xml.etree.cElementTree import parse as cet_parse
from Tools.XMLTools import stringToXML
from os import path as path
from EPGRefreshService import EPGRefreshService
from OrderedSet import OrderedSet
from Components.config import config
from Screens.MessageBox import MessageBox
from Tools import Notifications
from Tools.BoundFunction import boundFunction
from Components.ParentalControl import parentalControl
from . import _, NOTIFICATIONID
from MainPictureAdapter import MainPictureAdapter
from PipAdapter import PipAdapter
from RecordAdapter import RecordAdapter

CONFIG = "/etc/enigma2/epgrefresh.xml"
XML_VERSION = "1"

class EPGRefresh:
	"""Simple Class to refresh EPGData"""

	def __init__(self):
		self.services = (OrderedSet(), OrderedSet())
		self.forcedScan = False
		self.isrunning = False
		self.DontShutdown = False
		self.session = None
		self.checkTimer = eTimer()
		self.check_finish = False
		self.wait = eTimer()
		self.wait.timeout.get().append(self.refresh)
		self.autotimer_pause = eTimer()
		self.autotimer_pause.timeout.get().append(self.finish)
		self.beginOfTimespan = 0
		self.refreshAdapter = None
		self.configMtime = -1
		self.readConfiguration()

	def isRunning(self):
		return self.isrunning

	def isServiceProtected(self, service):
		if not service:
			return True
		if not config.ParentalControl.configured.value or not config.ParentalControl.servicepinactive.value:
			return False
		refstr = ':'.join(str(service).split(':')[:11])
		return parentalControl.getProtectionLevel(refstr) != -1

	def readConfiguration(self):
		if not path.exists(CONFIG):
			return
		mtime = path.getmtime(CONFIG)
		if mtime == self.configMtime:
			return
		self.configMtime = mtime
		self.services[0].clear()
		self.services[1].clear()
		configuration = cet_parse(CONFIG).getroot()
		version = configuration.get("version", None)
		if version is None:
			factor = 60
		else:
			factor = 1
		for service in configuration.findall("service"):
			value = service.text
			if value:
				pos = value.rfind(':')
				if pos != -1:
					value = value[:pos+1]
				duration = service.get('duration', None)
				duration = duration and int(duration)*factor
				self.services[0].add(EPGRefreshService(value, duration))
		for bouquet in configuration.findall("bouquet"):
			value = bouquet.text
			if value:
				duration = bouquet.get('duration', None)
				duration = duration and int(duration)
				self.services[1].add(EPGRefreshService(value, duration))

	def buildConfiguration(self, webif = False):
		list = ['<?xml version="1.0" ?>\n<epgrefresh version="', XML_VERSION, '">\n\n']
		if webif:
			for serviceref in self.services[0].union(self.services[1]):
				ref = ServiceReference(str(serviceref))
				list.extend((
					' <e2service>\n',
					'  <e2servicereference>', str(serviceref), '</e2servicereference>\n',
					'  <e2servicename>', stringToXML(ref.getServiceName().replace('\xc2\x86', '').replace('\xc2\x87', '')), '</e2servicename>\n',
					' </e2service>\n',
				))
		else:
			for service in self.services[0]:
				ref = ServiceReference(service.sref)
				list.extend((' <!--', stringToXML(ref.getServiceName().replace('\xc2\x86', '').replace('\xc2\x87', '')), '-->\n', ' <service'))
				if service.duration is not None:
					list.extend((' duration="', str(service.duration), '"'))
				list.extend(('>', stringToXML(service.sref), '</service>\n'))
			for bouquet in self.services[1]:
				ref = ServiceReference(bouquet.sref)
				list.extend((' <!--', stringToXML(ref.getServiceName().replace('\xc2\x86', '').replace('\xc2\x87', '')), '-->\n', ' <bouquet'))
				if bouquet.duration is not None:
					list.extend((' duration="', str(bouquet.duration), '"'))
				list.extend(('>', stringToXML(bouquet.sref), '</bouquet>\n'))
		list.append('\n</epgrefresh>')
		return list

	def saveConfiguration(self):
		file = open(CONFIG, 'w')
		file.writelines(self.buildConfiguration())
		file.close()

	def maybeStopAdapter(self):
		if self.refreshAdapter:
			self.refreshAdapter.stop()
			self.refreshAdapter = None

	def forceRefresh(self, session = None, dontshutdown = False):
		print("[EPGRefresh] Forcing start of EPGRefresh")
		if self.session is None:
			if session is not None:
				self.session = session
			else:
				return False
		if dontshutdown:
			self.DontShutdown = True
		self.forcedScan = True
		self.prepareRefresh()
		return True

	def start(self, session = None):
		if session is not None:
			self.session = session
		if not self.forcedScan:
			self.stop()
		epgrefreshtimer.setRefreshTimer(self.createWaitTimer)

	def stop(self):
		self.maybeStopAdapter()
		epgrefreshtimer.clear()
		if self.wait.isActive():
			self.wait.stop()
		self.forcedScan = False
		self.isrunning = False
		self.DontShutdown = False

	def addServices(self, fromList, toList, channelIds):
		for scanservice in fromList:
			service = eServiceReference(scanservice.sref)
			if not service.valid() \
				or (service.flags & (eServiceReference.isMarker|eServiceReference.isDirectory)):
				continue
			channelID = '%08x%04x%04x' % (
				service.getUnsignedData(4), # NAMESPACE
				service.getUnsignedData(2), # TSID
				service.getUnsignedData(3), # ONID
			)
			if channelID not in channelIds:
				toList.append(scanservice)
				channelIds.append(channelID)

	def generateServicelist(self, services, bouquets):
		additionalServices = []
		additionalBouquets = []
		if config.plugins.epgrefresh.inherit_autotimer.value:
			try:
				from Plugins.Extensions.AutoTimer.plugin import autotimer
				if autotimer is None:
					from Plugins.Extensions.AutoTimer.AutoTimer import AutoTimer
					autotimer = AutoTimer()
				autotimer.readXml()
			except Exception as e:
				print("[EPGRefresh] Could not inherit AutoTimer Services:", e)
			else:
				for timer in autotimer.getEnabledTimerList():
					additionalServices.extend([EPGRefreshService(x, None) for x in timer.services])
					additionalBouquets.extend([EPGRefreshService(x, None) for x in timer.bouquets])
		scanServices = []
		channelIdList = []
		self.addServices(services, scanServices, channelIdList)
		serviceHandler = eServiceCenter.getInstance()
		for bouquet in bouquets.union(additionalBouquets):
			myref = eServiceReference(bouquet.sref)
			list = serviceHandler.list(myref)
			if list is not None:
				while 1:
					s = list.getNext()
					if s.valid():
						additionalServices.append(EPGRefreshService(s.toString(), None))
					else:
						break
		del additionalBouquets[:]
		def sortServices(services): # sort by positions - better for motor
			unsortedServices = []
			for service in services:
				ref = service.sref
				position = ref.split(":")[6][:-4]
				if not position:
					position = "0"
				auxiliarySortParameter = int(position, 16)
				if auxiliarySortParameter > 1800:
					auxiliarySortParameter = 3600 - auxiliarySortParameter
				unsortedServices.append((auxiliarySortParameter, service))
			unsortedServices.sort()
			sortedServices = []
			for service in unsortedServices:
				sortedServices.append(service[1])
			return sortedServices
		scanServices = sortServices(scanServices)
		self.addServices(additionalServices, scanServices, channelIdList)
		del additionalServices[:]
		return scanServices

	def prepareRefresh(self):
		print("[EPGRefresh] About to start refreshing EPG")
		try:
			self.readConfiguration()
		except Exception as e:
			print("[EPGRefresh] Error occured while reading in configuration:", e)
		self.scanServices = self.generateServicelist(self.services[0], self.services[1])
		print("[EPGRefresh] Services we're going to scan:", ', '.join([repr(x) for x in self.scanServices]))
		self.maybeStopAdapter()
		if config.plugins.epgrefresh.adapter.value == "main":
			refreshAdapter = MainPictureAdapter(self.session)
		elif config.plugins.epgrefresh.adapter.value == "record":
			refreshAdapter = RecordAdapter(self.session)
		else:
			if config.plugins.epgrefresh.adapter.value == "pip":
				hidden = False
			elif config.plugins.epgrefresh.adapter.value == "pip_hidden":
				hidden = True
			refreshAdapter = PipAdapter(self.session, hide=hidden)
		if (not refreshAdapter.backgroundCapable and Screens.Standby.inStandby) or not refreshAdapter.prepare():
			print("[EPGRefresh] Adapter is not able to run in background or not available, falling back to MainPictureAdapter")
			refreshAdapter = MainPictureAdapter(self.session)
			refreshAdapter.prepare()
		self.refreshAdapter = refreshAdapter
		self.isrunning = True
		self.refresh()
		print("[EPGRefresh] pre start...")

	def cleanUp(self):
		config.plugins.epgrefresh.lastscan.value = int(time())
		config.plugins.epgrefresh.lastscan.save()
		if config.plugins.epgrefresh.save_epg.value:
			try:
				from enigma import eEPGCache
				epgcache = eEPGCache.getInstance()
				epgcache.save()
				print("[EPGRefresh] save epgcache...")
			except:
				pass
			if config.plugins.epgrefresh_extra.save_backup.value and config.plugins.epgrefresh_extra.epgcachepath.value != "/etc/enigma2/":
				from os import system as my_system
				from os import chmod as my_chmod
				from os import path as my_path
				restore_backup = config.misc.epgcache_filename.value + ".backup"
				if my_path.exists(config.misc.epgcache_filename.value):
					try:
						my_system("cp -f %s %s" % (config.misc.epgcache_filename.value, restore_backup))
						my_chmod("%s" % (restore_backup), 0644)
						print("[EPGRefresh] save epgcache backup...")
					except:
						pass
		if config.plugins.epgrefresh.parse_autotimer.value:
			try:
				from Plugins.Extensions.AutoTimer.plugin import autotimer

				if autotimer is None:
					from Plugins.Extensions.AutoTimer.AutoTimer import AutoTimer
					autotimer = AutoTimer()
				autotimer.readXml()
				autotimer.parseEPGAsync(simulateOnly=False)
				if not self.autotimer_pause.isActive():
					if config.plugins.epgrefresh.afterevent.value and not self.DontShutdown:
						try:
							from Plugins.Extensions.SeriesPlugin.plugin import renameTimer
						except:
							self.autotimer_pause.startLongTimer(120)
						else:
							self.autotimer_pause.startLongTimer(int(config.plugins.epgrefresh.timeout_shutdown.value)*60)
					else:
						self.finish()
			except Exception as e:
				print("[EPGRefresh] Could not start AutoTimer:", e)
				self.finish()
		else:
			self.finish()

	def checkFinish(self):
		try:
			if self.checkTimer.callback:
				self.checkTimer.callback.remove(self.checkFinish)
			self.checkTimer.stop()
			print("[EPGRefresh] stop timer...")
		except:
			pass
		self.check_finish = False
		print("[EPGRefresh] stop check...")

	def finish(self, *args, **kwargs):
		if Screens.Standby.inStandby is None and config.plugins.epgrefresh.enablemessage.value:
			try:
				Notifications.AddPopup(_("EPG refresh finished."), MessageBox.TYPE_INFO, 4, NOTIFICATIONID)
			except:
				pass
		epgrefreshtimer.cleanup()
		self.maybeStopAdapter()
		if not self.check_finish:
			self.check_finish = True
			try:
				self.checkTimer.callback.append(self.checkFinish)
				self.checkTimer.start(30000, True)
				self.forcedScan = False
				print("[EPGRefresh] pause 30 sec...")
			except:
				pass
		else:
			return
		self.isrunning = False
		if config.plugins.epgrefresh.afterevent.value and self.DontShutdown:
			self.DontShutdown = False
			self.forcedScan = False
			print("[EPGRefresh] Return to TV viewing...")
			return
		if not self.forcedScan and config.plugins.epgrefresh.afterevent.value and not Screens.Standby.inTryQuitMainloop:
			self.forcedScan = False
			print("[EPGRefresh] Shutdown after EPG refresh...")
			self.session.open(
				Screens.Standby.TryQuitMainloop,
				1
			)
		self.forcedScan = False
		self.DontShutdown = False

	def refresh(self):
		if self.wait.isActive():
			self.wait.stop()
		if self.forcedScan:
			self.nextService()
		else:
			if self.beginOfTimespan < config.plugins.epgrefresh.lastscan.value:
				if not self.wait.isActive():
					self.isrunning = False
				return
			check_standby = False
			stop_service = False
			if Screens.Standby.inStandby:
				check_standby = True
			if not config.plugins.epgrefresh.force.value and check_standby:
				rec_time = self.session.nav.RecordTimer.getNextRecordingTime()
				interval = config.plugins.epgrefresh.interval_seconds.value
				if interval <= 20:
					interval = 25
				if rec_time > 0 and (rec_time - time()) <= interval:
					stop_service = True
			if config.plugins.epgrefresh.force.value or (check_standby and not self.session.nav.RecordTimer.isRecording() and not stop_service):
				self.nextService()
			else:
				if not checkTimespan(
					config.plugins.epgrefresh.begin.value,
					config.plugins.epgrefresh.end.value):

					print("[EPGRefresh] Gone out of timespan while refreshing, sorry!")
					self.cleanUp()
				else:
					print("[EPGRefresh] Box no longer in Standby or Recording started, rescheduling")
					if check_standby and config.plugins.epgrefresh.adapter.value == "main":
						self.session.nav.stopService()
					epgrefreshtimer.add(EPGRefreshTimerEntry(
							time() + config.plugins.epgrefresh.delay_standby.value*60,
							self.refresh,
							nocheck = True)
					)

	def createWaitTimer(self):
		self.beginOfTimespan = time()
		epgrefreshtimer.add(EPGRefreshTimerEntry(time() + 30, self.prepareRefresh))

	def nextService(self):
		print("[EPGRefresh] Maybe zap to next service")
		try:
			service = self.scanServices.pop(0)
		except IndexError:
			print("[EPGRefresh] Done refreshing EPG")
			self.cleanUp()
		else:
			Notifications.RemovePopup("Parental control")
			if self.isServiceProtected(service):
				skipProtectedServices = config.plugins.epgrefresh.skipProtectedServices.value
				adapter = config.plugins.epgrefresh.adapter.value
				if (not self.forcedScan) or skipProtectedServices == "always" or (self.forcedScan and Screens.Standby.inStandby is None and skipProtectedServices == "bg_only" and (adapter == "pip" or adapter == "main")):
					print("[EPGRefresh] Service is protected, skipping!")
					self.refresh()
					return
			if (not self.refreshAdapter.backgroundCapable and Screens.Standby.inStandby):
				print("[EPGRefresh] Adapter is not able to run in background or not available, falling back to MainPictureAdapter")
				self.maybeStopAdapter()
				self.refreshAdapter = MainPictureAdapter(self.session)
				self.refreshAdapter.prepare()
			self.refreshAdapter.play(eServiceReference(service.sref))
			delay = service.duration or config.plugins.epgrefresh.interval_seconds.value
			if not delay:
				delay = 20
			if not self.wait.isActive():
				self.wait.start(int(delay*1000), True)

	def showPendingServices(self, session):
		if session is None:
			session = self.session
		else:
			if self.session is None:
				self.session = session
		if session is None:
			return False
		if not self.isRunning():
			return False
		LISTMAX = 10
		servcounter = 0
		try:
			servtxt = ""
			for service in self.scanServices:
				if self.isServiceProtected(service):
					skipProtectedServices = config.plugins.epgrefresh.skipProtectedServices.value
					adapter = config.plugins.epgrefresh.adapter.value
					if (not self.forcedScan) or skipProtectedServices == "always" or (self.forcedScan and Screens.Standby.inStandby is None and skipProtectedServices == "bg_only" and (adapter == "pip" or adapter == "main")):
						continue
				if servcounter <= LISTMAX:
					ref = ServiceReference(service.sref)
					txt = ref.getServiceName().replace('\xc2\x86', '').replace('\xc2\x87', '')
					servtxt = servtxt + str(txt) + "\n"
				servcounter = servcounter + 1
			first_text = _("Stop Running EPG-refresh?\n")
			if servcounter > LISTMAX:
				servtxt = servtxt + _("\n%d more services.") % (servcounter)
			session.openWithCallback(self.msgClosed, MessageBox, first_text + _("Following Services have to be scanned:") + "\n" + servtxt, MessageBox.TYPE_YESNO)
		except:
			print("[EPGRefresh] showPendingServices Error!")

	def msgClosed(self, ret=False):
		if ret:
			self.stop()
			if config.plugins.epgrefresh.enabled.value:
				self.start()

epgrefresh = EPGRefresh()
