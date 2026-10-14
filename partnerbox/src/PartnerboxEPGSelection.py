
#  Partnerbox E2
#
#  $Id$
#
#  Coded by Dr.Best (c) 2009
#  Support: www.dreambox-tools.info
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.config import config
from .PartnerboxSetup import PartnerboxEntriesListConfigScreen, PartnerboxSetup
from Screens.EpgSelection import EPGSelection
from Components.EpgList import EPG_TYPE_SINGLE, EPG_TYPE_SIMILAR, EPG_TYPE_MULTI
from Screens.ChoiceBox import ChoiceBox
from Tools.BoundFunction import boundFunction
from Tools.Directories import fileExists
from .PartnerboxFunctions import isInTimerList, isInRepeatTimer, sendPartnerBoxWebCommand, FillE1TimerList, FillE2TimerList
from . import PartnerboxFunctions as partnerboxfunctions
from enigma import eServiceReference, eServiceCenter

# for localized messages
from . import _

baseEPGSelection__init__ = None
baseEPGSelection_zapTo = None
baseonSelectionChanged = None
basetimerAdd = None
basefinishedAdd = None
baseonCreate = None


def Partnerbox_EPGSelectionInit():
	global baseEPGSelection__init__, baseEPGSelection_zapTo, baseonSelectionChanged, basetimerAdd, basefinishedAdd, baseonCreate
	if baseEPGSelection__init__ is None:
		baseEPGSelection__init__ = EPGSelection.__init__
	if baseEPGSelection_zapTo is None:
		baseEPGSelection_zapTo = EPGSelection.zapTo
	if baseonSelectionChanged is None:
		baseonSelectionChanged = EPGSelection.onSelectionChanged
	if basetimerAdd is None:
		basetimerAdd = EPGSelection.timerAdd
	if basefinishedAdd is None:
		basefinishedAdd = EPGSelection.finishedAdd
	if baseonCreate is None:
		baseonCreate = EPGSelection.onCreate

	EPGSelection.__init__ = Partnerbox_EPGSelection__init__
	EPGSelection.zapTo = Partnerbox_EPGSelection_zapTo
	EPGSelection.onSelectionChanged = Partnerbox_onSelectionChanged
	EPGSelection.timerAdd = Partnerbox_timerAdd
	EPGSelection.finishedAdd = Partnerbox_finishedAdd
	EPGSelection.onCreate = Partnerbox_onCreate
	# new methods
	EPGSelection.NewPartnerBoxSelected = NewPartnerBoxSelected
	EPGSelection.GetPartnerboxTimerlistCallback = GetPartnerboxTimerlistCallback
	EPGSelection.GetPartnerboxTimerlistCallbackError = GetPartnerboxTimerlistCallbackError
	EPGSelection.CheckRemoteTimer = CheckRemoteTimer
	EPGSelection.GetMatchingPartnerboxTimers = GetMatchingPartnerboxTimers
	EPGSelection.ChooseRemoteTimer = ChooseRemoteTimer
	EPGSelection.RemoteTimerSelected = RemoteTimerSelected
	EPGSelection.OpenRemoteTimer = OpenRemoteTimer
	EPGSelection.DeleteTimerConfirmed = DeleteTimerConfirmed
	EPGSelection.DeleteTimerCallback = DeleteTimerCallback
	EPGSelection.DeleteTimerCallbackError = DeleteTimerCallbackError
	EPGSelection.GetPartnerboxTimerlist = GetPartnerboxTimerlist
	EPGSelection.RedCallback = RedCallback
	EPGSelection.setRedbutton = setRedbutton
	EPGSelection.remoteTimerMenu = remoteTimerMenu
	EPGSelection.PartnerboxInit = PartnerboxInit


def Partnerbox_EPGSelection__init__(self, session, service, zapFunc=None, eventid=None, bouquetChangeCB=None, serviceChangeCB=None, parent=None):
	#check if alternatives are defined
	#if isinstance(service, eServiceReference):
	#	if service.flags & (eServiceReference.isGroup):
	#		service = eServiceCenter.getInstance().list(eServiceReference("%s" %(service.toString()))).getContent("S")[0]
	baseEPGSelection__init__(self, session, service, zapFunc, eventid, bouquetChangeCB, serviceChangeCB, parent)
	self.PartnerboxInit(True)


def PartnerboxInit(self, filterRef):
	self.filterRef = filterRef
	self.isTMBD = fileExists("/usr/lib/enigma2/python/Plugins/Extensions/TMBD/plugin.pyc")
	self.AutoTimer = fileExists("/usr/lib/enigma2/python/Plugins/Extensions/AutoTimer/SimpleThread.pyc")
	self.partnerboxentry = None
	partnerboxfunctions.remote_timer_list = []
	if int(config.plugins.Partnerbox.entriescount.value) >= 1:
		try:
			self.partnerboxentry = config.plugins.Partnerbox.Entries[0]
			partnerboxfunctions.CurrentIP = self.partnerboxentry.ip.value
		except:
			self.partnerboxentry = None
		self.setRedbutton()


def setRedbutton(self):
	if not hasattr(self, 'partnerboxentry'):
		self.PartnerboxInit(True)
	if not hasattr(self, 'zapFunc'):
		self.zapFunc = None
	if hasattr(self, 'partnerboxentry') and self.partnerboxentry is None:
		return
	if self.zapFunc:
		if config.plugins.Partnerbox.enablepartnerboxzapbuton.value:
			try:
				if int(config.plugins.Partnerbox.entriescount.value) > 1:
					self["key_red"].setText("PartnerBox")
				else:
					name_red = _("Zap/") + config.plugins.Partnerbox.Entries[0].name.value
					self["key_red"].setText(name_red)
			except:
				pass
	elif self.type == EPG_TYPE_SINGLE and not self.zapFunc and not self.isTMBD and not self.AutoTimer:
		try:
			if int(config.plugins.Partnerbox.entriescount.value) > 1:
				self["key_red"].setText("PartnerBox")
			else:
				self["key_red"].setText(config.plugins.Partnerbox.Entries[0].name.value)
		except:
			pass


def Partnerbox_EPGSelection_zapTo(self):
	if hasattr(self, 'partnerboxentry') and self.partnerboxentry is None:
		baseEPGSelection_zapTo(self)
		return
	try:
		if int(config.plugins.Partnerbox.entriescount.value) >= 1:
			if self.key_red_choice == self.ZAP and self.zapFunc:
				if config.plugins.Partnerbox.enablepartnerboxzapbuton.value:
					list = [
					(_("Standard Zap"), "zap"),
					(_("Partnerbox Entries"), "partnerboxentry"),
					(_("Partnerbox RemoteTimer"), "partnerboxremotetimer"),
					(_("Partnerbox Setup"), "partnerboxsetup"),
					]
					dlg = self.session.openWithCallback(self.RedCallback, ChoiceBox, title=_("Select action:"), list=list)
					dlg.setTitle(_("Choice list Partnerbox"))
				else:
					baseEPGSelection_zapTo(self)
			elif not (self.zapFunc and self.key_red_choice == self.ZAP):
				self.session.openWithCallback(self.NewPartnerBoxSelected, PartnerboxEntriesListConfigScreen, 0)
			else:
				baseEPGSelection_zapTo(self)
	except:
		pass


def RedCallback(self, ret):
	ret = ret and ret[1]
	if ret:
		if ret == "zap":
			try:
				baseEPGSelection_zapTo(self)
			except:
				pass
		elif ret == "partnerboxentry":
			try:
				self.session.openWithCallback(self.NewPartnerBoxSelected, PartnerboxEntriesListConfigScreen, 0)
			except:
				pass
		elif ret == "partnerboxremotetimer":
			try:
				if hasattr(self, 'partnerboxentry') and self.partnerboxentry is not None:
					from .plugin import RemoteTimer
					self.session.openWithCallback(self.DeleteTimerCallback, RemoteTimer, self.partnerboxentry, not_epg=True)
			except:
				pass
		elif ret == "partnerboxsetup":
			try:
				self.session.open(PartnerboxSetup)
			except:
				pass
		else:
			pass


def NewPartnerBoxSelected(self, session, what, partnerboxentry=None):
	try:
		if partnerboxentry is not None:
			self.partnerboxentry = partnerboxentry
			self.GetPartnerboxTimerlist()
			name_red = ''
			if int(config.plugins.Partnerbox.entriescount.value) > 1:
				name_red = _("Zap/") + partnerboxentry.name.value
			else:
				if self.zapFunc:
					if config.plugins.Partnerbox.enablepartnerboxzapbuton.value:
						name_red = _("Zap/") + partnerboxentry.name.value
					else:
						name_red = _("Zap")
				else:
					name_red = partnerboxentry.name.value
			self["key_red"].setText(name_red)
			self["list"].l.invalidate()
	except:
		pass


def Partnerbox_onSelectionChanged(self):
	try:
		baseonSelectionChanged(self)
		self.CheckRemoteTimer()
		self.setRedbutton()
	except:
		pass


def GetPartnerboxEntries(self):
	if config.plugins.Partnerbox.allboxes.value:
		return config.plugins.Partnerbox.Entries
	return [self.partnerboxentry]


def HasInternalTimer(self, event, serviceref):
	eventId = event.getEventId()
	begin = event.getBeginTime()
	end = begin + event.getDuration()
	service = ':'.join(serviceref.ref.toString().split(':')[:11])
	recordTimer = self.session.nav.RecordTimer

	for timer in recordTimer.timer_list:
		if ':'.join(timer.service_ref.ref.toString().split(':')[:11]) != service:
			continue
		if timer.eit == eventId and (begin < timer.begin <= end or timer.begin <= begin <= timer.end):
			return True
		if timer.repeated and recordTimer.isInRepeatTimer(timer, event):
			return True
	return False


def GetMatchingPartnerboxTimers(self, event, serviceref, firstOnly=False):
	boxes = [box for box in GetPartnerboxEntries(self) if box is not None]
	best = {id(box): None for box in boxes}
	begin = event.getBeginTime()
	duration = event.getDuration()
	end = begin + duration
	eventId = event.getEventId()
	service = serviceref.ref.toString()

	for timer in partnerboxfunctions.remote_timer_list:
		box = getattr(timer, "partnerboxentry", None)
		key = id(box)
		if key not in best:
			continue
		# Check each timer separately so overlapping timers cannot hide a better match.
		if isInTimerList(begin, duration, service, eventId, [timer]) is None:
			continue
		if firstOnly:
			return [(box, timer)]
		overlap = max(0, min(end, timer.timeend) - max(begin, timer.timebegin))
		exact = eventId is not None and eventId >= 0 and timer.eventId == eventId
		score = (exact, overlap)  # Prefer matching EIT, then the longest overlap.
		if best[key] is None or score > best[key][0]:
			best[key] = (score, timer)
	return [(box, best[id(box)][1]) for box in boxes if best[id(box)] is not None]


def Partnerbox_timerAdd(self):
	def pbColorText(text):
		return "\\c0008f0f0%s\\C" % text

	try:
		if self.key_green_choice != self.REMOVE_TIMER:
			basetimerAdd(self)
			return
		current = self["list"].getCurrent()
		if current is None or current[0] is None:
			return
		event, serviceref = current[:2]
		matches = self.GetMatchingPartnerboxTimers(event, serviceref)
		if not matches:
			basetimerAdd(self)
			return

		box, timer = matches[0]
		if int(box.enigma.value) != 0:
			self.ChooseRemoteTimer(matches)
			return

		internalAction = _("Edit internal timer") if HasInternalTimer(self, event, serviceref) else _("Add internal timer")
		remoteAction = _("Edit remote timer")
		remoteAction += " - " + ", ".join(pbColorText(box.name.value) for box, _ in matches)
		menu = [(remoteAction, "remote"), (internalAction, "internal")]

		def timerAction(choice):
			if choice is None:
				return
			if choice[1] == "remote":
				self.ChooseRemoteTimer(matches)
			elif choice[1] == "internal":
				basetimerAdd(self)

		self.session.openWithCallback(timerAction, ChoiceBox,
			title=_("Select action for timer '%s':") % timer.name, list=menu, keys=["blue", "green"])
	except:
		pass


def ChooseRemoteTimer(self, matches):
	if not matches:
		return
	if len(matches) == 1:
		self.OpenRemoteTimer(matches[0][1])
	else:
		menu = [(box.name.value, timer) for box, timer in matches]
		self.session.openWithCallback(self.RemoteTimerSelected, ChoiceBox,
			title=_("Select Partnerbox:"), list=menu)


def RemoteTimerSelected(self, choice):
	if choice is not None:
		self.OpenRemoteTimer(choice[1])


def OpenRemoteTimer(self, timerentry):
	if int(timerentry.partnerboxentry.enigma.value) == 0:
		self.remoteTimerMenu(timerentry)
	else:
		message = _("Do you really want to delete the remote timer \n%s ?") % timerentry.description
		self.session.openWithCallback(boundFunction(self.DeleteTimerConfirmed, timerentry), MessageBox, message)


def remoteTimerMenu(self, timerentry):
	try:
		menu = [(_("Delete timer"), "delete"), (_("Timer Overview"), "timerlist")]
		buttons = ["red", "green"]
		title_text = timerentry.repeated and _("Attention, this is repeated timer!\n") or ""

		def remoteTimerAction(choice):
			if choice is not None:
				if choice[1] == "delete":
					self.session.openWithCallback(boundFunction(self.DeleteTimerConfirmed, timerentry), MessageBox, _("Do you really want to delete the timer \n%s ?") % timerentry.name)
				elif choice[1] == "timerlist":
					from .plugin import RemoteTimer
					self.session.openWithCallback(self.DeleteTimerCallback, RemoteTimer, timerentry.partnerboxentry, not_epg=True)
		self.session.openWithCallback(remoteTimerAction, ChoiceBox, title=title_text + _("Select action for remote timer '%s':") % timerentry.name, list=menu, keys=buttons)
	except:
		pass


def Partnerbox_finishedAdd(self, answer):
	try:
		basefinishedAdd(self, answer)
		self.GetPartnerboxTimerlist()
	except:
		pass


def Partnerbox_onCreate(self):
	try:
		if not hasattr(self, 'partnerboxentry'):
			self.PartnerboxInit(True)
		baseonCreate(self)
		self.GetPartnerboxTimerlist()
	except:
		pass


def RefreshPartnerboxEPG(self):
	Partnerbox_onSelectionChanged(self)
	self["list"].l.invalidate()


def GetPartnerboxTimerlist(self, keepTimers=False):
	if self.partnerboxentry is None:
		return
	self.partnerboxRequestId = getattr(self, "partnerboxRequestId", 0) + 1
	requestId = self.partnerboxRequestId
	if not keepTimers:
		partnerboxfunctions.remote_timer_list = []
		RefreshPartnerboxEPG(self)

	for box in GetPartnerboxEntries(self):
		if box is None:
			continue
		ip = "%d.%d.%d.%d" % tuple(box.ip.value)
		path = "/web/timerlist" if int(box.enigma.value) == 0 else "/xml/timers"
		command = "http://%s:%d%s" % (ip, box.port.value, path)
		request = sendPartnerBoxWebCommand(command, None, 3, "root", box.password.value)
		request.addCallback(boundFunction(self.GetPartnerboxTimerlistCallback, box, requestId))
		request.addErrback(boundFunction(self.GetPartnerboxTimerlistCallbackError, box, requestId))


def GetPartnerboxTimerlistCallback(self, box, requestId, sxml=None):
	if requestId != self.partnerboxRequestId or sxml is None:
		return
	try:
		curService = None
		if self.type == EPG_TYPE_SINGLE and self.filterRef:
			curService = self.currentService.ref.toString()
		parseTimers = FillE2TimerList if int(box.enigma.value) == 0 else FillE1TimerList
		timers = parseTimers(sxml, curService)
		for timer in timers:
			timer.partnerboxentry = box
		partnerboxfunctions.remote_timer_list = [
			timer for timer in partnerboxfunctions.remote_timer_list
			if getattr(timer, "partnerboxentry", None) is not box
		]
		partnerboxfunctions.remote_timer_list.extend(timers)
		RefreshPartnerboxEPG(self)
	except Exception as error:
		print("[Partnerbox] Timerlist from %s: %s" % (box.name.value, error))


def GetPartnerboxTimerlistCallbackError(self, box, requestId, error=None):
	if requestId == self.partnerboxRequestId and error is not None:
		print("[Partnerbox] Timerlist from %s: %s" % (box.name.value, error.getErrorMessage()))


def CheckRemoteTimer(self):
	try:
		if self.key_green_choice != self.REMOVE_TIMER:
			cur = self["list"].getCurrent()
			if cur is None:
				return
			event = cur[0]
			serviceref = cur[1]
			if event is not None:
				if self.GetMatchingPartnerboxTimers(event, serviceref, firstOnly=True):
					self["key_green"].setText(_("Timer menu"))
					self.key_green_choice = self.REMOVE_TIMER
	except:
		pass


def DeleteTimerConfirmed(self, timerentry, answer):
	if not answer:
		return
	try:
		box = timerentry.partnerboxentry
		ip = "%d.%d.%d.%d" % tuple(box.ip.value)
		http = "http://%s:%d" % (ip, box.port.value)
		if int(box.enigma.value) == 0:
			serviceRef = ':'.join(str(timerentry.servicereference).split(':')[:11])
			command = "%s/web/timerdelete?sRef=%s&begin=%s&end=%s" % (
				http, serviceRef, timerentry.timebegin, timerentry.timeend)
		else:
			command = "%s/deleteTimerEvent?ref=%s&start=%s&type=%s&force=yes" % (
				http, timerentry.servicereference, timerentry.timebegin, timerentry.type)
		request = sendPartnerBoxWebCommand(command, None, 3, "root", box.password.value)
		request.addCallback(self.DeleteTimerCallback)
		request.addErrback(self.DeleteTimerCallbackError)
	except:
		pass


def DeleteTimerCallback(self, callback=None):
	try:
		self.GetPartnerboxTimerlist(keepTimers=True)
		fallbackTimer = getattr(self, "fallbackTimer", None)
		if fallbackTimer and fallbackTimer.url:
			from Tools.FallbackTimer import FallbackTimerList
			# Refresh the separate fallback cache without changing its screen callbacks.
			FallbackTimerList(self, boundFunction(RefreshPartnerboxEPG, self))
	except:
		pass


def DeleteTimerCallbackError(self, error=None):
	try:
		if error is not None:
			self.session.open(MessageBox, str(_(error.getErrorMessage())), MessageBox.TYPE_INFO)
	except:
		pass
