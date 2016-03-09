#  PrimeTimeManager E2
#  Coded by by Shaderman (c) 2010-2011 / Dimitrij openPLi 2013-2016
#
#################
### CHANGELOG ###
#################

# 0.9.0 - Preview release
# 0.9.1 - Show unhandled key icon for unhandled keys :)
#	- Show number of conflicts as digital-7 numbers
#	- Removed option "show conflict numbers"
#	- Added yet another message box. The user needs to confirm the "set day" function
#	- "view live" events are now set as zap timers
#	- Lowered the height of the prime time event entries and increased the height of the description
# 0.9.2 - Fixed crash when a view live event was set for an event without epg data
#	- Renamed plugin from PrimeTime to PrimeTimeManager
#	- Added a secondary prime time (default: 22:00). Can be toggled with the video key
#	- Existing record timers can now be turned into view live (zap) timers
# 0.9.3	- Added result screen
#	- Added settings button to main screen
# 0.9.4	- Added Autotimer support for unresolved collisions
# 0.9.5 - Made view live events (zap timer) work
# 0.9.6 - Added helper pixmaps to show possible scroll directions for prime time and favorite list
#	- Made conflict detection work with multiple tuners
#	- Simplified and improved add/remove timer
#	- Added new option: "Remove favorite on timer deletion" (default: No)
# 0.9.7 - Fixed crash when info key was pressed on a event without EPG data
#	- Fixed minor bug in the conflict detection code (spotted by Dr.Best)
#	- Improved conflict-solving
#	- Prefer HD services when solving conflicts with similar events
# 0.9.8 - Fixed overlapping timers
# 1.0	- Take timer margins into account when setting timers
#	- Changed from normal to helpable actions
# 1.1 - Completely redesigned plugin code(Dimitrij openPLi) 2013
# 1.2 - adapt to new parental control(Dimitrij openPLi) 2016
#	- add new icon
# 1.3 - add new func key menu TimerEdit - notify timer conflict
# 1.3-1 - fix event info <> if end list

from . import _
from copy import deepcopy
from datetime import datetime, timedelta
from time import mktime, localtime, strftime, time
from operator import itemgetter
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.Button import Button
from Components.config import config
from Components.GUIComponent import GUIComponent
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryPixmapAlphaTest
from Components.Pixmap import Pixmap
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Components.TimerSanityCheck import TimerSanityCheck
from Components.UsageConfig import preferredTimerPath
from enigma import eEPGCache, eServiceCenter, eServiceReference, getDesktop, RT_HALIGN_LEFT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_WRAP, eListboxPythonMultiContent, eListbox, gFont, eTimer
from enigma import ePoint, fontRenderClass, eSize, eLabel, eWidget
from Components.NimManager import nimmanager
from RecordTimer import RecordTimer, RecordTimerEntry, parseEvent, AFTEREVENT
from Screens.ChannelSelection import service_types_tv
from Screens.EventView import EventViewBase
from Screens.EpgSelection import EPGSelection
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.TimerEntry import TimerEntry
from Screens.TimerEdit import TimerEditList, TimerSanityConflict
from Screens.UnhandledKey import UnhandledKey
from ServiceReference import ServiceReference
import skin
from Tools.BoundFunction import boundFunction
from Tools.Notifications import AddPopup
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN, SCOPE_CURRENT_PLUGIN, fileExists
from Tools.HardwareInfo import HardwareInfo
from Tools.LoadPixmap import LoadPixmap
import NavigationInstance
from ResultScreen import ResultScreen
from PrimeTimeSettings import PrimeTimeSettings
try:
	from Plugins.Extensions.AutoTimer.AutoTimerEditor import addAutotimerFromEvent
	AUTOTIMER = True
except ImportError:
	AUTOTIMER = False

# HD services stuff
service_types_tv = '1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 22) || (type == 25) || (type == 31) || (type == 134) || (type == 195)'
service_types_tv_hd = '1:7:1:0:0:0:0:0:0:0:(type == 17) || (type == 25) || (type == 31) || (type == 134) || (type == 195)'

#############################################################################################

PRIMETIME	= 0
FAVORITE	= 1
PT_AND_FAV	= 2

EVENTID		= 0
SERVICEREF	= 1
BEGIN		= 2
DURATION	= 3
TITLE		= 4
SHORTDESC	= 5
EXTDESC		= 6
SERVICENAME	= 7

#############################################################################################

class PrimeTimeManager(Screen, HelpableScreen):
	skin = """<screen name="PrimeTimeManager" title="Prime Time Manager" position="center,center" size="650,545">
		<ePixmap pixmap="skin_default/buttons/red.png" position="45,0" size="140,40" transparent="1" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="185,0" size="140,40" transparent="1" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="325,0" size="140,40" transparent="1" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="465,0" size="140,40" transparent="1" alphatest="on" />
		<ePixmap position="10,10" size="35,25" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/PrimeTimeManager/images/key_menu.png" alphatest="on" />
		<ePixmap position="610,10" size="35,25" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/PrimeTimeManager/images/key_help.png" alphatest="on" />
		<widget render="Label" source="key_red" position="45,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
		<widget render="Label" source="key_green" position="185,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="green" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
		<widget render="Label" source="key_yellow" position="325,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="yellow" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
		<widget render="Label" source="key_blue" position="465,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="blue" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
		<ePixmap position="0,40" zPosition="0" size="650,480" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/PrimeTimeManager/images/border.png" transparent="0" alphatest="on" />
		<widget render="Label" source="primetime" position="0,40" size="650,21" zPosition="1" font="Regular;17" transparent="1" halign="left" foregroundColor="yellow" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="description" position="5,190" size="640,165" font="Regular;18" />
		<widget name="infoPixmap" position="610,185" size="35,25" zPosition="1" transparent="1" alphatest="on" />
		<widget render="Label" source="favorites" position="0,350" size="650,25" zPosition="1" font="Regular;18" transparent="1" halign="center" valign="center" foregroundColor="yellow" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="ptList1" position="5,65" size="210,115" zPosition="1" transparent="0" foregroundColorSelected="#ffd700" backgroundColor="#255" backgroundColorSelected="#65535ff" />
		<widget name="ptList2" position="220,65" size="210,115" zPosition="1" transparent="0" foregroundColorSelected="#ffd700" backgroundColor="#255" backgroundColorSelected="#65535ff" />
		<widget name="ptList3" position="435,65" size="210,115" zPosition="1" transparent="0" foregroundColorSelected="#ffd700" backgroundColor="#255" backgroundColorSelected="#65535ff" />
		<widget name="favList1" position="5,375" size="210,140" zPosition="1" transparent="0" foregroundColorSelected="#ffd700" backgroundColorSelected="#08004c00" />
		<widget name="favList2" position="220,375" size="210,140" zPosition="1" transparent="0" foregroundColorSelected="#ffd700" backgroundColorSelected="#08004c00" />
		<widget name="favList3" position="435,375" size="210,140" zPosition="1" transparent="0" foregroundColorSelected="#ffd700" backgroundColorSelected="#08004c00" />
		<widget name="ptListScrollLeft" position="0,65" size="5,115" zPosition="1" transparent="0" alphatest="on" />
		<widget name="ptListScrollRight" position="645,65" size="5,115" zPosition="1" transparent="0" alphatest="on" />
		<widget name="favListScrollLeft" position="0,387" size="5,115" zPosition="1" transparent="0" alphatest="on" />
		<widget name="favListScrollRight" position="645,387" size="5,115" zPosition="1" transparent="0" alphatest="on" />
		<widget source="global.CurrentTime" render="Label" position="10,523" size="430, 21" font="Regular; 18" halign="left" foregroundColor="white" backgroundColor="background" transparent="1">
			<convert type="ClockToText">Date</convert>
		</widget>
		<ePixmap alphatest="on" pixmap="skin_default/icons/clock.png" position="540,520" size="14,14" zPosition="1" />
		<widget font="Regular;18" halign="left" position="560,523" render="Label" size="55,20" source="global.CurrentTime" transparent="1" valign="center" zPosition="1">
			<convert type="ClockToText">Default</convert>
		</widget>
		<widget font="Regular;15" halign="left" position="612,520" render="Label" size="27,17" source="global.CurrentTime" transparent="1" valign="center" zPosition="1">
			<convert type="ClockToText">Format::%S</convert>
		</widget>
		</screen>"""

	def __init__(self, session, servicelist = None):
		self.servicelist = servicelist
		Screen.__init__(self, session)
		self.session = session
		self.setTitle(_("Prime Time Manager"))

		# color button labels
		if config.plugins.PrimeTimeManager.RedButton.value == "exit":
			self["key_red"] = StaticText(_("Exit"))
		else:
			self["key_red"] = StaticText(_("Multi EPG"))
		self["key_green"] = StaticText(_("Set Timer"))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText(_("Timers list"))

		# misc labels
		self["primetime"] = StaticText("")
		self["favorites"] = StaticText(_("Selected favorites"))
		self["description"] = NoScrollBarLabel("")
		self["infoPixmap"] = Pixmap()
		self["ptListScrollLeft"] = Pixmap()
		self["ptListScrollRight"] = Pixmap()
		self["favListScrollLeft"] = Pixmap()
		self["favListScrollRight"] = Pixmap()

		# actions
		HelpableScreen.__init__(self)
		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
		{
			"cancel":	(self.buttonCancel,	_("Exit plugin")),
			"ok":		(self.buttonOk,		_("Add/remove event to or from favourites")),
		}, -1)

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
		{
			"red":		(self.buttonRed,	_("Exit plugin or open Multi EPG")),
			"green":	(self.showTimerEntry,	_("Set or remove a timer")),
			"yellow":	(self.showResultScreen,	_("Try to solve conflicts and show result")),
			"blue":		(self.openTimerlist,	_("Open timers list")),
		}, -1)

		self["DirectionActions"] = HelpableActionMap(self, "DirectionActions",
		{
			"up":		(self.changeActiveList, _("Switch betw. favourite/prime time list")),
			"down":		(self.changeActiveList, _("Switch betw. favourite/prime time list")),
			"left":		(self.buttonLeft,	_("Scroll selected list to the left")),
			"leftRepeated":	(self.buttonLeft,	_("Scroll selected list to the left")),
			"right":	(self.buttonRight,	_("Scroll selected list to the right")),
			"rightRepeated":(self.buttonRight,	_("Scroll selected list to the right")),
		}, -1)

		self["ChannelSelectBaseActions"] = HelpableActionMap(self, "ChannelSelectBaseActions",
		{
			"nextMarker":	(boundFunction(self.changeDay, True),	_("Switch to the next day")),
			"prevMarker":	(boundFunction(self.changeDay, False),	_("Switch to the previous day")),
			"nextBouquet":	(self.nextBouquet,			_("Switch to the next bouquet")),
			"prevBouquet":	(self.prevBouquet,			_("Switch to the previous bouquet")),
		}, -1)

		self["ChannelSelectEPGActions"] = HelpableActionMap(self, "ChannelSelectEPGActions",
		{
			"showEPGList":	(self.showEventView,	_("Show event information")),
		}, -1)

		self["ChannelSelectEditActions"] = HelpableActionMap(self, "ChannelSelectEditActions",
		{
			"contextMenu":	(self.showSettings,	_("Open the settings screen")),
		}, -1)

		self["NumberActions"] = HelpableActionMap(self, "NumberActions",
		{
			"0":		(self.toggleViewLive,	_('Toggle marker for a "view live" event')),
			"1":		(self.toggleViewLiveType,	_('Toggle "view live" type')),
		}, -1)

		self["InfobarActions"] = HelpableActionMap(self, "InfobarActions",
		{
			"showMovies":	(self.togglePrimeTime,	_("Toggle primary/secondary prime time")),
		}, -1)

		# initialize the skin sub lists
		i = 1
		while i < 4:
			self["ptList" + str(i)] = PreviewList([], PRIMETIME)
			self["favList" + str(i)] = PreviewList([], FAVORITE)
			i += 1

		self.alternatePrimeTime = False

		self.unhandledKey = KeyNotHandled(self.session, init=True)

		# get some enigma instances to work with
		self.serviceHandler = eServiceCenter.getInstance()
		self.epgcache = eEPGCache.getInstance()
		self.recordTimer = self.session.nav.RecordTimer

		self.onShown.append(self.initialize)

	# initialize the lists for the first time
	def initialize(self):
		self["infoPixmap"].hide()
		self["infoPixmap"].instance.setPixmapFromFile(resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/buttons/key_info.png'))

		scrollLeftPixmap = resolveFilename(SCOPE_CURRENT_PLUGIN, 'Extensions/PrimeTimeManager/images/scrollLeft.png')
		scrollRightPixmap = resolveFilename(SCOPE_CURRENT_PLUGIN, 'Extensions/PrimeTimeManager/images/scrollRight.png')

		self["ptListScrollLeft"].instance.setPixmapFromFile(scrollLeftPixmap)
		self["ptListScrollLeft"].hide()
		self["ptListScrollRight"].instance.setPixmapFromFile(scrollRightPixmap)
		self["ptListScrollRight"].hide()
		self["favListScrollLeft"].instance.setPixmapFromFile(scrollLeftPixmap)
		self["favListScrollLeft"].hide()
		self["favListScrollRight"].instance.setPixmapFromFile(scrollRightPixmap)
		self["favListScrollRight"].hide()

		self.setDayEnabled = False

		# remove the callback, it's no longer needed
		if self.initialize in self.onShown:
			self.onShown.remove(self.initialize)

		# 0 = today, 1 = tomorrow...
		self.dayOffset = 0

		# a list of ListObjects for every bouquet
		self.primeTimeEvents = []

		# a list of ListObjects for every selectable day
		self.favoriteEvents = []

		# a list of lists of tuples (serviceref, eventid) for every real timer
		self.timerServices = []

		# a list of lists of tuples (serviceref, eventid) for every overlapping timer
		self.overlappingTimers = []

		self.notrecordingTimers = []
		
		# a list of service references for view live events (there can be only one event for each day)
		self.viewLiveServices = []

		# a list to store ConflictObjects
		self.conflictList = []

		# a list of dicts storing service refs and their number of conflicts
		self.conflictCounts = []

		# a list of dicts storing service refs and their number of conflicts
		self.conflictSat = []

		# get the number of available tuners
		self.numTuners = self.getNumTuners()

		# fill some lists for use with self.dayOffset (7 days)
		i = 0
		while i < 7:
			self.favoriteEvents.append(ListObject("favList", None, [], 0))
			self.timerServices.append([])
			self.overlappingTimers.append([])
			self.viewLiveServices.append("")
			self.conflictList.append([])
			self.conflictCounts.append({})
			self.conflictSat.append([])
			self.notrecordingTimers.append([])
			i += 1

		# bouquet initialisation
		if config.usage.multibouquet.value:
			self.bouquet_rootstr = service_types_tv + ' FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
		else:
			self.bouquet_rootstr = '%s FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet' % (service_types_tv)
		self.bouquet_root = eServiceReference(self.bouquet_rootstr)

		# a dict of serviceRefs as key and the bouquet name as value
		self.serviceBouquet = { }

		# get a list of all bouquets
		self.bouquets = self.getBouquetList()
		self.bouquetCount = len(self.bouquets)
		self.currentBouquet = 0

		# set the prime time
		self.setPrimeTime()

		# get the prime time events for day self.offset
		self.getPrimeTimeEvents()

		# find timers where begin < primeTime and end + margin > primeTime
		self.getOverlappingTimers()
		
		# add existing timers to the favorites
		self.getTimerEvents()

		# set the selected list to the first prime time object
		self.activeList = self.primeTimeEvents[0]

		if self.primeTimeIsOver:
			text = _("Prime Time Manager:\n\nPrime time has already begun or is over. Starting with tomorrow's events.")
			self.session.open(MessageBox, text, MessageBox.TYPE_INFO)

		self.setPrimeTimeTitleString()

		self.updateLists()

		self.setScrollPixmaps(self.primeTimeEvents[self.currentBouquet])
		
		# HD service refs will be stored here
		self.serviceRefsHD = None

		self.pre_list = []

	################
	### BOUQUETS ###
	################

	# get a list of available bouquets (without empty bouquets)
	def getBouquetList(self):
		bouquets = []
		if config.usage.multibouquet.value:
			list = self.serviceHandler.list(self.bouquet_root)
			if list:
				while True:
					s = list.getNext()
					if not s.valid():
						break
					if s.flags & eServiceReference.isDirectory and not s.flags & eServiceReference.isInvisible:
						item = self.serviceHandler.list(s).getNext()
						info = self.serviceHandler.info(s)
						if not item.valid():
							print '[PrimeTimeManager] Skipping empty bouquet', info.getName(s)
							break
						if info:
							bouquets.append((info.getName(s).rstrip(' (TV)'), s))
				return bouquets
		else:
			info = serviceHandler.info(self.bouquet_root)
			if info:
				bouquets.append((info.getName(self.bouquet_root).rstrip(' (TV)'), self.bouquet_root))
			return bouquets
		return None

	def openTimerlist(self, onlyConflict=False):
		check_on = False
		simulTimerList = None
		self.pre_list = []
		for timer in self.recordTimer.timer_list:
			self.pre_list.append(timer)
			timersanitycheck = TimerSanityCheck(self.recordTimer.timer_list, timer)
			if not timersanitycheck.check():
				check_on = True
				simulTimerList = timersanitycheck.getSimulTimerList()
				break
		if check_on and simulTimerList is not None:
			self.session.openWithCallback(boundFunction(self.postEdit), PTMtimerSanityConflict, simulTimerList)
		else:
			if not onlyConflict:
				self.session.openWithCallback(boundFunction(self.postEdit), TimerEditList)

	def postEdit(self, answer=None):
		for timer in self.pre_list:
			if not timer in self.recordTimer.timer_list:
				if (timer.service_ref.ref.toString(), timer.eit) in self.timerServices[self.dayOffset]:
					self.timerServices[self.dayOffset].remove((timer.service_ref.ref.toString(), timer.eit))
					print "[PrimeTimeManager] Del in timerServices"
				if (timer.service_ref.ref.toString(), timer.eit) in self.overlappingTimers[self.dayOffset]:
					self.overlappingTimers[self.dayOffset].remove((timer.service_ref.ref.toString(), timer.eit))
					print "[PrimeTimeManager] Del in overlappingTimers"
				if (timer.service_ref.ref.toString(), timer.eit) in self.notrecordingTimers[self.dayOffset]:
					self.notrecordingTimers[self.dayOffset].remove((timer.service_ref.ref.toString(), timer.eit))
					print "[PrimeTimeManager] Del in notrecordingTimers"
				timer_str = GetWithAlternative(timer.service_ref.ref.toString())
				if (timer_str, timer.eit) in self.timerServices[self.dayOffset]:
					self.timerServices[self.dayOffset].remove((timer_str, timer.eit))
					print "[PrimeTimeManager] Del in timerServices"
				if (timer_str, timer.eit) in self.overlappingTimers[self.dayOffset]:
					self.overlappingTimers[self.dayOffset].remove((timer_str, timer.eit))
					print "[PrimeTimeManager] Del in overlappingTimers"
				if (timer_str, timer.eit) in self.notrecordingTimers[self.dayOffset]:
					self.notrecordingTimers[self.dayOffset].remove((timer_str, timer.eit))
					print "[PrimeTimeManager] Del in notrecordingTimers"
				if funcRefStr(self.viewLiveServices[self.dayOffset]) == funcRefStr(timer.service_ref.ref.toString()):
					self.viewLiveServices[self.dayOffset] = ""
				if config.plugins.PrimeTimeManager.RemoveFavorite.value or timer.disabled:
					for favorite in self.favoriteEvents[self.dayOffset].services:
						if funcRefStr(timer.service_ref.ref.toString()) == funcRefStr(favorite[SERVICEREF]):
							self.removeEntryFromFavorites(favorite, False)
							print "[PrimeTimeManager] Del favorite"
				self.updateLists()
				self.setSetDayButton()

	def setPositionService(self, num=0):
		try:
			if self.activeList.name != "ptList":
				self.changeActiveList()
			selected = self["ptList" + str(self.primeTimeEvents[self.currentBouquet].position)].getCurrent()[0]
			count = 0
			for event in self.primeTimeEvents[self.currentBouquet].services:
				count += 1
				if funcRefStr(event[SERVICEREF]) == funcRefStr(selected[SERVICEREF]):
					break
			if num != count:
				if num > count:
					sum = num - count
					i = 0
					while i < sum:
						self.buttonRight()
						i += 1
				else:
					sum = count - num
					i = 0
					while i < sum:
						self.buttonLeft()
						i += 1
		except:
			print "[PrimeTimeManager] Error setPositionService for close multi EPG"

	def buttonRed(self):
		if config.plugins.PrimeTimeManager.RedButton.value == "exit":
			self.buttonCancel()
		else:
			sRef = None
			if self.activeList.name == "ptList":
				selected = self["ptList" + str(self.primeTimeEvents[self.currentBouquet].position)].getCurrent()[0]
				sRef = eServiceReference(selected[SERVICEREF])
			services = self.getBouquetServices(self.bouquets[self.currentBouquet][1])
			bouquetName = self.bouquets[self.currentBouquet][0]
			if services:
				self.session.open(PrimeTimeSelection, services, service_ref=sRef, day_time=self.primeTime, setPositionService=self.setPositionService, bouquetname=bouquetName)

	def getBouquetServices(self, bouquet):
		services = []
		Servicelist = self.serviceHandler.list(bouquet)
		if not Servicelist is None:
			while True:
				service = Servicelist.getNext()
				if not service.valid():
					break
				if service.flags & (eServiceReference.isDirectory | eServiceReference.isMarker): #ignore non playable services
					continue
				services.append(ServiceReference(service))
		return services

	####################################
	### TRANSPONDER / CONFLICT STUFF ###
	####################################

	# check for a conflict between two timers
	def getConflictWithTimer(self, timer1, timer2):
		timerEntryList = [timer1]
		timersanitycheck = TimerSanityCheck(timerEntryList, timer2)
		check = not timersanitycheck.check()
		return check

	# get number of tuners
	def getNumTuners(self):
		nimCount = 0
		for slot in nimmanager.nim_slots:
			if slot.type is not None:
				nimCount += 1
		return nimCount

	# update the conflicts with a service ref
	def addToConflicts(self, sRef, add=None):
		conflict = False
		transponderFound = False
		# try to find a matching transponder tuple
		for conflictObject in self.conflictList[self.dayOffset]:
			if sRef in conflictObject.transponderServices:
				transponderFound = True
				break

		if transponderFound:
			# add the service ref to the transponder object
			conflictObject.knownServices.append(sRef)
			conflictObject.knownServicesSize += 1
		else:
			# add new transponder object to the conflict list
			serviceList = self.getTransponderServices(sRef)
			conflictObject = ConflictObject(transponderServices = serviceList, knownServices = [sRef])
			self.conflictList[self.dayOffset].append(conflictObject)
			#if self.numTuners > 1 and self.getAvailableTunerCount(sRef) == 1:
			if self.getAvailableTunerCount(sRef) == 1:
				if not sRef in self.conflictSat[self.dayOffset]:
					self.conflictSat[self.dayOffset].append(sRef)
					print "[PrimeTimeManager] Add only 1 sat %s" % ServiceReference(sRef).getServiceName()
			if add:
				conflict = True
		if conflict:
			self.updateConflicts(event=add)
		else:
			self.updateConflicts()

	# remove a service ref from the conflicts
	def removeFromConflicts(self, sRef):
		for conflictObject in self.conflictList[self.dayOffset]:
			if sRef in conflictObject.knownServices:
				del self.conflictCounts[self.dayOffset][sRef]
				conflictObject.knownServices.remove(sRef)
				conflictObject.knownServicesSize -= 1
				if conflictObject.knownServicesSize == 0:
					self.conflictList[self.dayOffset].remove(conflictObject)
			if sRef in self.conflictSat[self.dayOffset]:
				self.conflictSat[self.dayOffset].remove(sRef)
				print "[PrimeTimeManager] Del only 1 sat %s" % ServiceReference(sRef).getServiceName()

		self.updateConflicts(event=None)

	# update the conflict counts of all ConflictObjects but conflictObject
	def updateConflicts(self, event=None):
		check_on = False
		conflict_list = []
		if len(self.conflictList[self.dayOffset]) <= self.numTuners:
			for favorite in self.favoriteEvents[self.dayOffset].services:
				timer = self.getRecordTimerEntry(favorite)
				conflict_list.append(timer)
				for x in conflict_list:
					timersanitycheck = TimerSanityCheck(conflict_list, x)
					if not timersanitycheck.check():
						check_on = True
						break
		for conflictObject in self.conflictList[self.dayOffset]:
			for sRef in conflictObject.knownServices:
				# number of conflicts = number of favorites - known services on sRefs transponder
				if check_on:
					numConflicts = self.favoriteEvents[self.dayOffset].size - conflictObject.knownServicesSize
					print "[PrimeTimeManager] conflict count = %d " % numConflicts
				elif len(self.conflictList[self.dayOffset]) > self.numTuners:
					numConflicts = self.favoriteEvents[self.dayOffset].size - conflictObject.knownServicesSize
					print "[PrimeTimeManager] conflict count = %d " % numConflicts
				else:
					numConflicts = 0
					print "[PrimeTimeManager] conflict count = %d " % numConflicts
				self.conflictCounts[self.dayOffset][sRef] = numConflicts

	# get all services sharing a transponder with sRef
	def getTransponderServices(self, sRef):
		self.service_types = service_types_tv
		sRef = GetWithAlternative(sRef)
		cur_ref = eServiceReference(sRef)
		if cur_ref:
			self.service_types = service_types_tv
			pos = self.service_types.rfind(':')
			refstr = '%s (channelID == %08x%04x%04x) && %s ORDER BY name' % (self.service_types[:pos+1],
				cur_ref.getUnsignedData(4), # NAMESPACE
				cur_ref.getUnsignedData(2), # TSID
				cur_ref.getUnsignedData(3), # ONID
				self.service_types[pos+1:])
			ref = eServiceReference(refstr)

			returnList = []
			serviceList = self.serviceHandler.list(ref)
			if not serviceList is None:
				while True:
					service = serviceList.getNext()
					if not service.valid(): #check if end of list
						break
					returnList.append(service.toString())

			return returnList

	def showResultScreen(self):
		if not self.setDayEnabled:
			self.unhandledKey.show()
		else:
			self.resultList = self.resolveConflicts()
			self.session.openWithCallback(self.setDayConfirmed, ResultScreen, self.resultList)

	# the user confirmed solving conflicts
	def setDayConfirmed(self, result):
		if not result:
			return

		print "[PrimeTimeManager] setting the day"
		for result in self.resultList:
			sRef = result[0][SERVICEREF] # service reference
			if config.plugins.PrimeTimeManager.ViewLive.value:
				view_live = not result[3]
			else:
				view_live = result[3]
			# find the matching favorite event entry
			for favorite in self.favoriteEvents[self.dayOffset].services:
				if funcRefStr(sRef) == funcRefStr(favorite[SERVICEREF]):
					if result[5]: # auto timer?
						if AUTOTIMER and config.plugins.PrimeTimeManager.UseAutotimer.value:
							try:
								event = self.epgcache.lookupEventId(ServiceReference(favorite[SERVICEREF]).ref, favorite[EVENTID])
								addAutotimerFromEvent(self.session, evt = event, service = sRef)
								print "[PrimeTimeManager] Add auto timer %s" % ServiceReference(sRef).getServiceName()
							except:
								pass
						timerEntry = self.getIsInTimer(favorite)
						if timerEntry is not None:
							try:
								if not timerEntry.isRunning():
									self.recordTimer.timer_list.remove(timerEntry)
								else:
									timerEntry.afterEvent = AFTEREVENT.NONE
									NavigationInstance.instance.RecordTimer.removeEntry(timerEntry)
							except:
								pass
						try:
							if (favorite[SERVICEREF], favorite[EVENTID]) in self.timerServices[self.dayOffset]:
								self.timerServices[self.dayOffset].remove((favorite[SERVICEREF], favorite[EVENTID]))
							favorite_str = GetWithAlternative(favorite[SERVICEREF])
							if (favorite_str, favorite[EVENTID]) in self.timerServices[self.dayOffset]:
								self.timerServices[self.dayOffset].remove((favorite_str, favorite[EVENTID]))
						except:
							pass
						try:
							if (favorite[SERVICEREF], favorite[EVENTID]) in self.overlappingTimers[self.dayOffset]:
								self.overlappingTimers[self.dayOffset].remove((favorite[SERVICEREF], favorite[EVENTID]))
							if (favorite[SERVICEREF], favorite[EVENTID]) in self.notrecordingTimers[self.dayOffset]:
								self.notrecordingTimers[self.dayOffset].remove((favorite[SERVICEREF], favorite[EVENTID]))
							favorite_str = GetWithAlternative(favorite[SERVICEREF])
							if (favorite_str, favorite[EVENTID]) in self.overlappingTimers[self.dayOffset]:
								self.overlappingTimers[self.dayOffset].remove((favorite_str, favorite[EVENTID]))
							if (favorite_str, favorite[EVENTID]) in self.notrecordingTimers[self.dayOffset]:
								self.notrecordingTimers[self.dayOffset].remove((favorite_str, favorite[EVENTID]))
						except:
							pass
						try:
							print "[PrimeTimeManager] Del favorite %s" % ServiceReference(sRef).getServiceName()
							self.removeEntryFromFavorites(favorite, False)
						except:
							pass
					elif result[3] and result[6] is None: # view live event?
						try:
							timerEntry = self.getIsInTimer(favorite)
							if timerEntry is not None:
								if config.plugins.PrimeTimeManager.ViewLiveType.value == "zaprec":
									timerEntry.justplay = False
									timerEntry.always_zap = True
								else:
									timerEntry.justplay = True
									timerEntry.always_zap = False
								timerEntry.dontSave = False
								timerEntry.primeTime = False
								if not (timerEntry.service_ref.ref.toString(), timerEntry.eit) in self.timerServices[self.dayOffset]:
									self.timerServices[self.dayOffset].append((timerEntry.service_ref.ref.toString(), timerEntry.eit))
								timer_ref = GetWithAlternative(timerEntry.service_ref.ref.toString())
								if not (timer_ref, timerEntry.eit) in self.timerServices[self.dayOffset]:
									self.timerServices[self.dayOffset].append((timer_ref, timerEntry.eit))
							else:
								timerEntry = self.getRecordTimerEntry(favorite)
								self.recordTimer.addTimerEntry(timerEntry)
								if config.plugins.PrimeTimeManager.ViewLiveType.value == "zaprec":
									timerEntry.justplay = False
									timerEntry.always_zap = True
								else:
									timerEntry.justplay = True
									timerEntry.always_zap = False
								timerEntry.dontSave = False
								timerEntry.primeTime = False
								if not (timerEntry.service_ref.ref.toString(), timerEntry.eit) in self.timerServices[self.dayOffset]:
									self.timerServices[self.dayOffset].append((timerEntry.service_ref.ref.toString(), timerEntry.eit))
								timer_ref = GetWithAlternative(timerEntry.service_ref.ref.toString())
								if not (timer_ref, timerEntry.eit) in self.timerServices[self.dayOffset]:
									self.timerServices[self.dayOffset].append((timer_ref, timerEntry.eit))
							print "[PrimeTimeManager] Add view timer %s" % ServiceReference(sRef).getServiceName()
						except:
							pass
					elif result[6] and view_live: # similar timer event?
						# we don't want duplicate timer entries
						try:
							timerEntry = self.getIsInTimer(favorite)
							if timerEntry is not None:
								try:
									if not timerEntry.isRunning():
										self.recordTimer.timer_list.remove(timerEntry)
									else:
										timerEntry.afterEvent = AFTEREVENT.NONE
										NavigationInstance.instance.RecordTimer.removeEntry(timerEntry)
								except:
									pass
							else:
								try:
									timerEntry = self.getRecordTimerEntry(favorite)
									if not timerEntry.isRunning():
										self.recordTimer.timer_list.remove(timerEntry)
									else:
										timerEntry.afterEvent = AFTEREVENT.NONE
										NavigationInstance.instance.RecordTimer.removeEntry(timerEntry)
								except:
									pass
							duplicate = self.recordTimer.isInTimer(result[6].eit, result[6].begin, result[6].end - result[6].begin, result[6].service_ref.ref.toString())
							if duplicate is None or not duplicate:
								self.recordTimer.addTimerEntry(result[6])
								try:
									if result[6].isRunning():
										if not result[6].justplay:
											if not (result[6].service_ref.ref.toString(), result[6].eit) in self.overlappingTimers[self.dayOffset]:
												self.overlappingTimers[self.dayOffset].append((result[6].service_ref.ref.toString(), result[6].eit))
											if not (result[6].service_ref.ref.toString(), result[6].eit) in self.timerServices[self.dayOffset]:
												self.timerServices[self.dayOffset].append((result[6].service_ref.ref.toString(), result[6].eit))
											timer_ref = GetWithAlternative(result[6].service_ref.ref.toString())
											if not (timer_ref, result[6].eit) in self.overlappingTimers[self.dayOffset]:
												self.overlappingTimers[self.dayOffset].append((timer_ref, result[6].eit))
											if not (timer_ref, result[6].eit) in self.timerServices[self.dayOffset]:
												self.timerServices[self.dayOffset].append((timer_ref, result[6].eit))
											self.addTimerToFavorites(result[6])
									else:
										curtime = localtime(time())
										print "[PrimeTimeManager] Current day %s" % curtime.tm_wday
										timertime = localtime(result[6].begin)
										print "[PrimeTimeManager] Timer day %s" % timertime.tm_wday
										if curtime.tm_wday == timertime.tm_wday:
											if (result[6].begin - config.recording.margin_before.value * 60 <= self.primeTime) and (result[6].end - config.recording.margin_after.value * 60 > self.primeTime):
												if not (result[6].service_ref.ref.toString(), result[6].eit) in self.timerServices[self.dayOffset]:
													self.timerServices[self.dayOffset].append((result[6].service_ref.ref.toString(), result[6].eit))
												timer_ref = GetWithAlternative(result[6].service_ref.ref.toString())
												if not (timer_ref, result[6].eit) in self.timerServices[self.dayOffset]:
													self.timerServices[self.dayOffset].append((timer_ref, result[6].eit))
												self.addTimerToFavorites(result[6])
								except:
									pass
								print "[PrimeTimeManager] Add similar timer %s" % ServiceReference(sRef).getServiceName()
							if (favorite[SERVICEREF], favorite[EVENTID]) in self.timerServices[self.dayOffset]:
								self.timerServices[self.dayOffset].remove((favorite[SERVICEREF], favorite[EVENTID]))
							if (favorite[SERVICEREF], favorite[EVENTID]) in self.overlappingTimers[self.dayOffset]:
								self.overlappingTimers[self.dayOffset].remove((favorite[SERVICEREF], favorite[EVENTID]))
							if (favorite[SERVICEREF], favorite[EVENTID]) in self.notrecordingTimers[self.dayOffset]:
								self.notrecordingTimers[self.dayOffset].remove((favorite[SERVICEREF], favorite[EVENTID]))
							ref_str = GetWithAlternative(favorite[SERVICEREF])
							if (ref_str, favorite[EVENTID]) in self.timerServices[self.dayOffset]:
								self.timerServices[self.dayOffset].remove((ref_str, favorite[EVENTID]))
							if (ref_str, favorite[EVENTID]) in self.overlappingTimers[self.dayOffset]:
								self.overlappingTimers[self.dayOffset].remove((ref_str, favorite[EVENTID]))
							if (ref_str, favorite[EVENTID]) in self.notrecordingTimers[self.dayOffset]:
								self.notrecordingTimers[self.dayOffset].remove((ref_str, favorite[EVENTID]))
							self.removeEntryFromFavorites(favorite, False)
						except:
							pass
					else: # must be a simple favorite. turn it into a timer
						try:
							timerEntry = self.getIsInTimer(favorite)
							if timerEntry is not None:
								if result[3]:
									if config.plugins.PrimeTimeManager.ViewLiveType.value == "zaprec":
										timerEntry.justplay = False
										timerEntry.always_zap = True
									else:
										timerEntry.justplay = True
										timerEntry.always_zap = False
								timerEntry.dontSave = False
								timerEntry.primeTime = False
								timer_ref = GetWithAlternative(timerEntry.service_ref.ref.toString())
								if timerEntry.isRunning():
									if not timerEntry.justplay:
										if not (timer_ref, timerEntry.eit) in self.overlappingTimers[self.dayOffset]:
											self.overlappingTimers[self.dayOffset].append((timer_ref, timerEntry.eit))
										if not (timer_ref, timerEntry.eit) in self.timerServices[self.dayOffset]:
											self.timerServices[self.dayOffset].append((timer_ref, timerEntry.eit))
										if not (timerEntry.service_ref.ref.toString(), timerEntry.eit) in self.overlappingTimers[self.dayOffset]:
											self.overlappingTimers[self.dayOffset].append((timerEntry.service_ref.ref.toString(), timerEntry.eit))
										if not (timerEntry.service_ref.ref.toString(), timerEntry.eit) in self.timerServices[self.dayOffset]:
											self.timerServices[self.dayOffset].append((timerEntry.service_ref.ref.toString(), timerEntry.eit))
								else:
									if not (timer_ref, timerEntry.eit) in self.timerServices[self.dayOffset]:
										self.timerServices[self.dayOffset].append((timer_ref, timerEntry.eit))
									if not (timerEntry.service_ref.ref.toString(), timerEntry.eit) in self.timerServices[self.dayOffset]:
										self.timerServices[self.dayOffset].append((timerEntry.service_ref.ref.toString(), timerEntry.eit))
							else:
								timerEntry = self.getRecordTimerEntry(favorite)
								if result[3]:
									if config.plugins.PrimeTimeManager.ViewLiveType.value == "zaprec":
										timerEntry.justplay = False
										timerEntry.always_zap = True
									else:
										timerEntry.justplay = True
										timerEntry.always_zap = False
								self.recordTimer.addTimerEntry(timerEntry)
								try:
									timer_ref = GetWithAlternative(timerEntry.service_ref.ref.toString())
									if timerEntry.isRunning():
										if not timerEntry.justplay:
											if not (timerEntry.service_ref.ref.toString(), timerEntry.eit) in self.overlappingTimers[self.dayOffset]:
												self.overlappingTimers[self.dayOffset].append((timerEntry.service_ref.ref.toString(), timerEntry.eit))
											if not (timerEntry.service_ref.ref.toString(), timerEntry.eit) in self.timerServices[self.dayOffset]:
												self.timerServices[self.dayOffset].append((timerEntry.service_ref.ref.toString(), timerEntry.eit))
											if not (timer_ref, timerEntry.eit) in self.overlappingTimers[self.dayOffset]:
												self.overlappingTimers[self.dayOffset].append((timer_ref, timerEntry.eit))
											if not (timer_ref, timerEntry.eit) in self.timerServices[self.dayOffset]:
												self.timerServices[self.dayOffset].append((timer_ref, timerEntry.eit))
										else:
											ref_str = GetWithAlternative(favorite[SERVICEREF])
											if (favorite[SERVICEREF], favorite[EVENTID]) in self.timerServices[self.dayOffset]:
												self.timerServices[self.dayOffset].remove((favorite[SERVICEREF], favorite[EVENTID]))
											if (favorite[SERVICEREF], favorite[EVENTID]) in self.overlappingTimers[self.dayOffset]:
												self.overlappingTimers[self.dayOffset].remove((favorite[SERVICEREF], favorite[EVENTID]))
											if (favorite[SERVICEREF], favorite[EVENTID]) in self.notrecordingTimers[self.dayOffset]:
												self.notrecordingTimers[self.dayOffset].remove((favorite[SERVICEREF], favorite[EVENTID]))
											if (ref_str, favorite[EVENTID]) in self.timerServices[self.dayOffset]:
												self.timerServices[self.dayOffset].remove((ref_str, favorite[EVENTID]))
											if (ref_str, favorite[EVENTID]) in self.overlappingTimers[self.dayOffset]:
												self.overlappingTimers[self.dayOffset].remove((ref_str, favorite[EVENTID]))
											if (ref_str, favorite[EVENTID]) in self.notrecordingTimers[self.dayOffset]:
												self.notrecordingTimers[self.dayOffset].remove((ref_str, favorite[EVENTID]))
											self.removeEntryFromFavorites(favorite, False)
									else:
										if not (timerEntry.service_ref.ref.toString(), timerEntry.eit) in self.timerServices[self.dayOffset]:
											self.timerServices[self.dayOffset].append((timerEntry.service_ref.ref.toString(), timerEntry.eit))
										if not (timer_ref, timerEntry.eit) in self.timerServices[self.dayOffset]:
											self.timerServices[self.dayOffset].append((timer_ref, timerEntry.eit))
								except:
									pass
							print "[PrimeTimeManager] Add simple timer %s" % ServiceReference(sRef).getServiceName()
						except:
							pass

		# update the lists
		self.updateLists()

		self.setSetDayButton()

		# save the timers
		self.recordTimer.saveTimer()

		if config.plugins.PrimeTimeManager.CheckConflictOnAccept.value:
			self.openTimerlist(onlyConflict=True)

	def getConflictListTimer(self, resultList):
		conflict = False
		conflict_list = []
		for result in resultList:
			if result[6] is None and not result[5]:
				timer = self.getRecordTimerEntry(result[0])
				orig_timer = self.getIsInTimer(result[0])
				if orig_timer:
					if hasattr(orig_timer, "conflict_detection"):
						timer.conflict_detection = orig_timer.conflict_detection
				conflict_list.append(timer)
				for cur in conflict_list:
					timersanitycheck = TimerSanityCheck(conflict_list, cur)
					if not timersanitycheck.check():
						conflict = True
						continue
		return conflict

	def getAvailableTunerCount(self, sRef):
		count = 0
		cur_ref = eServiceReference(sRef)
		if cur_ref:
			str_service = cur_ref.toString()
			if '%3a//' not in str_service and not str_service.rsplit(":", 1)[1].startswith("/"):
				type_service = cur_ref.getUnsignedData(4) >> 16
				if type_service == 0xEEEE:
					for n in nimmanager.nim_slots:
						if n.isCompatible("DVB-T"):
							count += 1
				elif type_service == 0xFFFF:
					for n in nimmanager.nim_slots:
						if n.isCompatible("DVB-C"):
							count += 1
				else:
					orbpos = cur_ref.getData(4) >> 16
					if orbpos < 0:
						orbpos += 3600
					for n in nimmanager.nim_slots:
						if n.isCompatible("DVB-S"):
							for sat in nimmanager.getSatListForNim(n.slot):
								if sat[0] == orbpos:
									count += 1
									continue
		print "[PrimeTimeManager] tuners count %s" % count
		return count

	def similarFunc(self, x):
		if x[7] is None:
			return -1
		else:
			return 0

	def conflictSatFunc(self, x):
		if x[8]:
			return -1
		else:
			return 0

	def TimeSortFunc(self, x):
		t = time()
		if int(x[BEGIN]) > int(t):
			#print "[PrimeTimeManager] begin event %s" % x[2]
			return -1
		else:
			return 0

	def getSimilarForViewLive(self, view_live, ref):
		transponderFound = False
		for conflictObject in self.conflictList[self.dayOffset]:
			for knownService in conflictObject.knownServices:
				if view_live == knownService and conflictObject.knownServicesSize > 0:
					if ref in conflictObject.transponderServices:
						transponderFound = True
						break
		return transponderFound

	# resolve conflicts for all favorite events of the selected day
	def resolveConflicts(self):
		resultList = []

		# build a basic list of results
		for favorite in self.favoriteEvents[self.dayOffset].services:
			numConflicts = self.conflictCounts[self.dayOffset][favorite[SERVICEREF]]
			
			if (favorite[SERVICEREF], favorite[EVENTID]) in self.overlappingTimers[self.dayOffset]:
				isTimer = 1
			elif (favorite[SERVICEREF], favorite[EVENTID]) in self.notrecordingTimers[self.dayOffset]:
				isTimer = 3
			elif (favorite[SERVICEREF], favorite[EVENTID]) in self.timerServices[self.dayOffset]:
				isTimer = 2
			else:
				isTimer = 0

			if favorite[SERVICEREF] in self.viewLiveServices[self.dayOffset]:
				viewLive = True
			else:
				viewLive = False

			if favorite[SERVICEREF] in self.conflictSat[self.dayOffset]:
				conflictSat = True
			else:
				conflictSat = False

			result = [	favorite,								# the favorite event
					self.serviceBouquet[favorite[SERVICEREF]],	# bouquet
					numConflicts,								# number of conflicts
					viewLive,									# is it a view live event?
					isTimer,									# is it a timer?
					False,										# auto timer?
					None,										# similar timer?
					None,										# deferred similar timer?
					conflictSat									# only 1 sat
					]

			resultList.append(result)

		# get the number of tuners missing to handle everything without conflicts
		if not self.getConflictListTimer(resultList):
			print '[PrimeTimeManager] Nothing to do, there are no conflicts'
			return resultList
		else:
			# this is how conflicts are solved:
			# 1. get similar services for all transponders
			# 2. build two lists containing transponders where every known service has (or doesn't have) similar events
			# 3.1 try solving conflicts for transponders where every known service has similar events
			# 3.2 if conflicts for a known service can't be solved with similar events, add this transponder to the list where
			#     not all known services have similar events
			# 3.3 return if there are enough tuners now
			# 4.1 try solving conflicts for transponders where not all known services have similar events
			# 4.2 if conflicts for a known service can't be solved with similar events, set the autotimer flag
			# 4.3 repeat from 4.1 until all conflicts are solved

			print "[PrimeTimeManager] Starting to resolve conflicts" # because the favorite selection requires %s more tuner(s) and  %s conflict sat." % (missingTuners, satTuners)
			self.getHDServices()
			view_live = None
			for result in resultList:
				if result[3]:
					view_live = result[0][SERVICEREF]
			# STEP 1
			similarServicesList = []
			# make a copy of the conflictList for this day because we don't want to overwrite transponder information
			conflictList = deepcopy(self.conflictList[self.dayOffset])
			transponders = len(conflictList)
			resultList.sort(key=self.conflictSatFunc)
			# get similar events for all favorites
			for transponder in conflictList:
				for sRef in transponder.knownServices:
					for favorite in self.favoriteEvents[self.dayOffset].services:
						if sRef == favorite[SERVICEREF]:
							simObject = SimilarObject(sRef)
							simObject.similarEvents = self.epgcache.search(('IRBDTSEN', 20, eEPGCache.SIMILAR_BROADCASTINGS_SEARCH, favorite[SERVICEREF], favorite[EVENTID]))
							if simObject.similarEvents is not None:
								# sort by time
								simObject.similarEvents.sort(key=self.TimeSortFunc)
								# sort the similar events, HD services first
								simObject.similarEvents.sort(key=self.sRefHDSortFunc, reverse=True)
								simObject.similarEventsSize = len(simObject.similarEvents)
								transponder.numSimilarEvents += 1
							similarServicesList.append(simObject)

			# STEP 2
			# get a list of transponders where every service has similar events
			transponderEqualList = []
			transponderNotEqualList = []
			for transponder in conflictList:
				if transponder.numSimilarEvents == transponder.knownServicesSize:
					transponderEqualList.append(transponder)
				else:
					transponderNotEqualList.append(transponder)

			# sort the list ascending by the number of known services
			if len(transponderEqualList) > 1:
				transponderEqualList.sort(key=lambda x: x.knownServicesSize)

			# STEP 3.1
			for transponder in transponderEqualList:
				for knownService in transponder.knownServices:
					similarConflicts = False
					for simObject in similarServicesList:
						if simObject.sRef == knownService:
							similarTimer = None

							# a simple sanity check would return the first conflict found in the
							# timer list. we already know there are conflicts so we need to compare
							# every similar event with every timer one by one to get a reliable result
							# for similar events.
							if simObject.similarEvents is not None:
								for similarEvent in simObject.similarEvents:
									noConflict = False
									for timer in self.recordTimer.timer_list:
										# don't compare with the timer we're trying to solve
										# the conflicts for
										if funcRefStr(timer.service_ref.ref.toString()) == funcRefStr(similarEvent[SERVICEREF]):
											continue

										similarTimer = self.getRecordTimerEntry(similarEvent)
										noConflict = self.getConflictWithTimer(similarTimer, timer)

										if noConflict:
											similarTimer = None
											break
									if similarTimer:
										break

								if similarTimer:
									print "[PrimeTimeManager] Conflict step 3.1 for %s can be solved with a similar event" % ServiceReference(simObject.sRef).getServiceName()
									for result in resultList:
										# does the service ref match?
										if config.plugins.PrimeTimeManager.ViewLive.value:
											if simObject.sRef == result[0][SERVICEREF] and not result[3]:
												add_to_live = False
												if view_live is not None:
													ref = result[0][SERVICEREF]
													if not self.getSimilarForViewLive(view_live, ref):
														result[6] = similarTimer
													else:
														add_to_live = True
												else:
													result[6] = similarTimer
												if not self.getConflictListTimer(resultList):
													print "[PrimeTimeManager] Step 3.1 similar timer and not view live %s" % ServiceReference(simObject.sRef).getServiceName()
													return resultList
												else:
													if not result[8] and not add_to_live:
														result[6] = None
														result[7] = similarTimer
														print "[PrimeTimeManager] Step 3.1 revert changes %s" % ServiceReference(simObject.sRef).getServiceName()
										else:
											if simObject.sRef == result[0][SERVICEREF]:
												result[6] = similarTimer
												if not self.getConflictListTimer(resultList):
													print "[PrimeTimeManager]  Step 3.1 similar timer %s" % ServiceReference(simObject.sRef).getServiceName()
													return resultList
												else:
													if not result[8]:
														result[6] = None
														result[7] = similarTimer
														print "[PrimeTimeManager] Step 3.1 revert changes %s" % ServiceReference(simObject.sRef).getServiceName()
								else: # unable to solve conflicts with a similar event
									print "[PrimeTimeManager] Unable to set timer for similar event %s" % ServiceReference(simObject.sRef).getServiceName()
									similarConflicts = True
									break
				# STEP 3.2
				if similarConflicts:
					transponderNotEqualList.append(transponder)
					# revert changes made to the result list
					for knownService in transponder.knownServices:
						for result in resultList:
							if knownService == result[0][SERVICEREF]:
								result[6] = None
								print "[PrimeTimeManager]  Step 3.2 revert changes %s" % ServiceReference(result[0][SERVICEREF]).getServiceName()

				# STEP 3.3
			# sort by not similar timer
			print "[PrimeTimeManager] STEP 4.0 sort by not similar timer"
			resultList.sort(key=self.similarFunc)
			if not self.getConflictListTimer(resultList):
				print "[PrimeTimeManager] Step 3.3 done resolving conflicts"
				return resultList

			# STEP 4.0
			# sort the list ascending by the number of known services
			if len(transponderNotEqualList) > 1:
				transponderNotEqualList.sort(key=lambda x: x.knownServicesSize)

				for transponder in transponderNotEqualList:
					for knownService in transponder.knownServices:
						for simObject in similarServicesList:
							if simObject.sRef == knownService:
								similarTimer = None

								# a simple sanity check would return the first conflict found in the
								# timer list. we already know there are conflicts so we need to compare
								# every similar event with every timer one by one to get a reliable result
								# for similar events.
								if simObject.similarEventsSize > 0:
									for similarEvent in simObject.similarEvents:
										noConflict = False
										for timer in self.recordTimer.timer_list:
											# don't compare with the timer we're trying to solve
											# the conflicts for
											if funcRefStr(timer.service_ref.ref.toString()) == funcRefStr(similarEvent[SERVICEREF]):
												continue

											similarTimer = self.getRecordTimerEntry(similarEvent)
											noConflict = self.getConflictWithTimer(similarTimer, timer)

											if noConflict:
												similarTimer = None
												break
										if noConflict:
											break

									# STEP 4.1
									if similarTimer:
										print "[PrimeTimeManager] Conflict for %s can be solved with a similar event" % ServiceReference(simObject.sRef).getServiceName()
										for result in resultList:
											# does the service ref match?
											if config.plugins.PrimeTimeManager.ViewLive.value:
												if simObject.sRef == result[0][SERVICEREF] and not result[3]:
													if view_live is not None:
														ref = result[0][SERVICEREF]
														if not self.getSimilarForViewLive(view_live, ref):
															result[6] = similarTimer
															print "[PrimeTimeManager] Step 4.1 similar timer and not view live %s" % ServiceReference(simObject.sRef).getServiceName()
													else:
														result[6] = similarTimer
														print "[PrimeTimeManager] Step 4.1 similar timer and not view live %s" % ServiceReference(simObject.sRef).getServiceName()
													if not self.getConflictListTimer(resultList):
														print "[PrimeTimeManager] STEP 4.1 done resolving conflicts"
														return resultList
											else:
												if simObject.sRef == result[0][SERVICEREF]:
													result[6] = similarTimer
													print "[PrimeTimeManager] Step 4.1 similar timer %s" % ServiceReference(simObject.sRef).getServiceName()
													if not self.getConflictListTimer(resultList):
														print "[PrimeTimeManager] STEP 4.1 done resolving conflicts"
														return resultList

									# STEP 4.2
									else: # unable to solve conflict with a similar event
										print "[PrimeTimeManager] There are no similar events for %s" % ServiceReference(simObject.sRef).getServiceName()
										for result in resultList:
											# does the service ref match?
											if config.plugins.PrimeTimeManager.ViewLive.value:
												if simObject.sRef == result[0][SERVICEREF] and result[7] is None and not result[3]:
													result[5] = True # set auto timer flag
													print "[PrimeTimeManager] Step 4.2 auto timer and not view live %s" % ServiceReference(simObject.sRef).getServiceName()
													if not self.getConflictListTimer(resultList):
														print "[PrimeTimeManager] STEP 4.2 done resolving conflicts"
														return resultList
											else:
												if simObject.sRef == result[0][SERVICEREF] and result[7] is None:
													result[5] = True # set auto timer flag
													print "[PrimeTimeManager] Step 4.2 auto timer %s" % ServiceReference(simObject.sRef).getServiceName()
													if not self.getConflictListTimer(resultList):
														print "[PrimeTimeManager] STEP 4.2 done resolving conflicts"
														return resultList
								# STEP 4.3
								else: # unable to solve conflict with a similar event
									print "[PrimeTimeManager] There are no similar events for %s" % ServiceReference(simObject.sRef).getServiceName()
									for result in resultList:
										# does the service ref match?
										if config.plugins.PrimeTimeManager.ViewLive.value:
											if simObject.sRef == result[0][SERVICEREF] and result[7] is None and not result[3]:
												result[5] = True # set auto timer flag
												print "[PrimeTimeManager] Step 4.3 auto timer and not view live %s" % ServiceReference(simObject.sRef).getServiceName()
												if not self.getConflictListTimer(resultList):
													print "[PrimeTimeManager] STEP 4.2 done resolving conflicts"
													return resultList
										else:
											if simObject.sRef == result[0][SERVICEREF] and result[7] is None:
												result[5] = True # set auto timer flag
												print "[PrimeTimeManager] Step 4.3 auto timer %s" % ServiceReference(simObject.sRef).getServiceName()
												if not self.getConflictListTimer(resultList):
													print "[PrimeTimeManager] STEP 4.3 done resolving conflicts"
													return resultList
					# STEP 4.4
					if not self.getConflictListTimer(resultList):
						print "[PrimeTimeManager] STEP 4.4 done resolving conflicts"
						return resultList

		# STEP 4.5
		if self.getConflictListTimer(resultList):
			for result in resultList:
				if result[6] is None and not result[5] and not result[3]:
					if result[8] and result[7] is None:
						if config.plugins.PrimeTimeManager.ViewLive.value and view_live is not None:
							ref = result[0][SERVICEREF]
							if not self.getSimilarForViewLive(view_live, ref):
								result[5] = True
								print "[PrimeTimeManager] Step 4.5 auto timer %s" % ServiceReference(result[0][SERVICEREF]).getServiceName()
						else:
							result[5] = True
							print "[PrimeTimeManager] Step 4.5 auto timer %s" % ServiceReference(result[0][SERVICEREF]).getServiceName()
					elif result[7] is not None:
						result[6] = result[7]
						print "[PrimeTimeManager] Step 4.5 similar timer %s" % ServiceReference(result[0][SERVICEREF]).getServiceName()
					if not self.getConflictListTimer(resultList):
						print "[PrimeTimeManager] Step 4.5 maybe done resolving conflicts"
						return resultList
			# STEP 4.6
			if self.getConflictListTimer(resultList):
				for result in resultList:
					if result[6] is None and not result[5] and not result[3]:
						if config.plugins.PrimeTimeManager.ViewLive.value and view_live is not None:
							ref = result[0][SERVICEREF]
							if not self.getSimilarForViewLive(view_live, ref):
								result[5] = True
								print "[PrimeTimeManager] Step 4.6 auto timer %s" % ServiceReference(result[0][SERVICEREF]).getServiceName()
						else:
							result[5] = True
							print "[PrimeTimeManager] Step 4.6 auto timer %s" % ServiceReference(result[0][SERVICEREF]).getServiceName()
						if not self.getConflictListTimer(resultList):
							print "[PrimeTimeManager] Step 4.6 maybe done resolving conflicts"
							return resultList

		# STEP 4.7
		print "[PrimeTimeManager] STEP 4.7 maybe done resolving conflicts"
		return resultList

	###################
	### EVENT LISTS ###
	###################

	def updateNavigation(self):
		self.setScrollPixmaps(self.activeList)
		self.setSetTimerButton()
		self.showDescription()

	# update both, prime time and favorite lists
	def updateLists(self):
		self.updateSubLists(PT_AND_FAV)
		self.setSublistOffsets(PT_AND_FAV)
		self.setListMarker()
		self.setSetTimerButton()
		self.showDescription()

	# update the visible favorite list
	def postFavoriteAdd(self):
		# set the marker position on the strip.
		# If the strip is full already, show the new entry on the last strip position
		if self.favoriteEvents[self.dayOffset].size <= 3:
			self.favoriteEvents[self.dayOffset].position = self.favoriteEvents[self.dayOffset].size
		else:
			self.favoriteEvents[self.dayOffset].position = 3
			self.favoriteEvents[self.dayOffset].offset = self.favoriteEvents[self.dayOffset].size - 3

		# list updates
		self.updateSubLists(PT_AND_FAV)
		self.setSublistOffsets(PT_AND_FAV)
		self.setSetDayButton()
		self.setScrollPixmaps(self.favoriteEvents[self.dayOffset])

	# add an event to the favorite list
	def addTimerToFavorites(self, timer):
		event = (timer.eit, timer.service_ref.ref.toString(), timer.begin, timer.end - timer.begin, timer.name, timer.description, "", timer.service_ref.getServiceName())

		self.favoriteEvents[self.dayOffset].services.append(event)
		self.favoriteEvents[self.dayOffset].size += 1
		self.addToConflicts(event[SERVICEREF])
		self.postFavoriteAdd()

	# add an event to the favorite list
	def addToFavorites(self, event):
		# add this event to the favorites if not there already
		if not event in self.favoriteEvents[self.dayOffset].services:
			for x in self.favoriteEvents[self.dayOffset].services:
				if event[SERVICEREF] == x[SERVICEREF] and event[EVENTID] == x[EVENTID]:
					self.unhandledKey.show()
					return
			print "[PrimeTimeManager] Add to favorites %s" % ServiceReference(event[SERVICEREF]).getServiceName()
			timerEntry = self.getIsInTimer(event)

			if timerEntry is None:
				timerEntry = self.getRecordTimerEntry(event)
				timerEntry.dontSave = True
				timerEntry.primeTime = True
				self.recordTimer.addTimerEntry(timerEntry)
			else:
				timerEntry.dontSave = False
				timerEntry.primeTime = False

			self.favoriteEvents[self.dayOffset].services.append(event)
			self.favoriteEvents[self.dayOffset].size += 1
			
			self.addToConflicts(event[SERVICEREF], add=timerEntry)
			self.postFavoriteAdd()
		else:
			self.unhandledKey.show()

	# update the sub lists
	def updateSubLists(self, listType):
		i = 1
		while i < 4:
			if (listType is PRIMETIME) or (listType is PT_AND_FAV):
				self["ptList" + str(i)].setList([ (x,) for x in self.primeTimeEvents[self.currentBouquet].services], self.conflictCounts[self.dayOffset], self.serviceBouquet, self.timerServices[self.dayOffset], self.overlappingTimers[self.dayOffset], self.viewLiveServices[self.dayOffset], self.conflictSat[self.dayOffset], self.notrecordingTimers[self.dayOffset])
			if (listType is FAVORITE) or (listType is PT_AND_FAV):
				self["favList" + str(i)].setList([ (x,) for x in self.favoriteEvents[self.dayOffset].services], self.conflictCounts[self.dayOffset], self.serviceBouquet, self.timerServices[self.dayOffset], self.overlappingTimers[self.dayOffset], self.viewLiveServices[self.dayOffset], self.conflictSat[self.dayOffset], self.notrecordingTimers[self.dayOffset])
			i += 1

	# update the list indices
	def setSublistOffsets(self, listType):
		i = 1
		while i < 4:
			if (listType is PRIMETIME) or (listType is PT_AND_FAV):
				self["ptList" + str(i)].moveToIndex(self.primeTimeEvents[self.currentBouquet].offset +i -1)
			if (listType is FAVORITE) or (listType is PT_AND_FAV):
				self["favList" + str(i)].moveToIndex(self.favoriteEvents[self.dayOffset].offset +i -1)
			i += 1

	# update the channel marker (list and position)
	def setListMarker(self):
		# clear all list markers
		i = 1
		while i < 4:
			self["favList" + str(i)].selectionEnabled(0)
			self["ptList" + str(i)].selectionEnabled(0)
			i += 1

		# set the new marker
		if self.activeList.name == "ptList":
			self["ptList" + str(self.activeList.position)].selectionEnabled(1)
		else:
			self["favList" + str(self.activeList.position)].selectionEnabled(1)

	# change the active list (prime time / favorites)
	def changeActiveList(self):
		if self.activeList.name == "ptList":
			# only activate the favorite list if it has entries already
			if self.favoriteEvents[self.dayOffset].size > 0:
				self.activeList = self.favoriteEvents[self.dayOffset]
				self.setListMarker()
			else:
				self.unhandledKey.show()
		else:
			self.activeList = self.primeTimeEvents[self.currentBouquet]
			self.setListMarker()

		self.setSetTimerButton()
		self.showDescription()

	# remove a favorit list entry
	def removeEntryFromFavorites(self, event, repeated):
		sRef = event[SERVICEREF]

		# remove a view live flag
		if sRef in self.viewLiveServices[self.dayOffset]:
			self.viewLiveServices[self.dayOffset] = ""
			self.updateSubLists(PRIMETIME)

		# delete the selected entry from the favorite list
		self.removeRepeatedFavorites(event, repeated)

		# remove from conflict list
		self.removeFromConflicts(sRef)

		# the last item was deleted, change to the prime time list
		if self.favoriteEvents[self.dayOffset].size == 0:
			self.updateSubLists(FAVORITE)
			self.changeActiveList()
			return

		# if there's a list offset, decrease the offset (but keep the position of the current selection)
		if self.favoriteEvents[self.dayOffset].offset > 0:
			self.favoriteEvents[self.dayOffset].offset -= 1
		# if the last (3rd) entry was deleted, move the selection one step to the left
		elif self.favoriteEvents[self.dayOffset].position == self.favoriteEvents[self.dayOffset].size + 1:
			self.favoriteEvents[self.dayOffset].position -= 1

		# list updates
		self.updateSubLists(FAVORITE)
		self.setSublistOffsets(FAVORITE)
		self.setListMarker()
		self.showDescription()
		self.setScrollPixmaps(self.favoriteEvents[self.dayOffset])

	# get the event from a service ref
	def getEventFromId(self, service, eventid):
		event = None
		if self.epgcache is not None and eventid is not None:
			event = self.epgcache.lookupEventId(service.ref, eventid)
		return event

	# get the event and service ref
	def getCurrent(self, eventid, selServiceRef):
		service = ServiceReference(selServiceRef)
		event = self.getEventFromId(service, eventid)
		return (event, service)

	#######################
	### BUTTON HANDLING ###
	#######################

	# toggle the prime time
	def togglePrimeTime(self):
		text = _("Do you want to switch the prime time? Currently selected favorites will be lost!")
		self.session.openWithCallback(self.togglePrimeTimeConfirmed, MessageBox, text)

	# called when the users confirmed the deletion of a timer
	def togglePrimeTimeConfirmed(self, result):
		if result:
			self.alternatePrimeTime = not self.alternatePrimeTime
			self.initialize()

	# toggle a view live type
	def toggleViewLiveType(self):
		if config.plugins.PrimeTimeManager.ViewLiveType.value == "zap":
			type = _("Zap + Record")
		else:
			type = _("Zap") 
		text = _("Set 'view live' type '%s'?") % type
		self.session.openWithCallback(self.toggleViewLiveTypeAnswer, MessageBox, text)

	def toggleViewLiveTypeAnswer(self, answer):
		if answer:
			if config.plugins.PrimeTimeManager.ViewLiveType.value == "zap":
				config.plugins.PrimeTimeManager.ViewLiveType.value = "zaprec"
			else:
				config.plugins.PrimeTimeManager.ViewLiveType.value = "zap"
			config.plugins.PrimeTimeManager.ViewLiveType.save()

	# toggle a view live event
	def toggleViewLive(self):
		selected = self[self.activeList.name + str(self.activeList.position)].getCurrent()[0]
		begin = selected[BEGIN]

		# don't add the selected item to the favorites because it has no begin time (epg data)
		if begin == None:
			self.unhandledKey.show()
			return

		serviceRef = selected[SERVICEREF]
		eventId = selected[EVENTID]
		ref_str = GetWithAlternative(serviceRef)
		if (serviceRef, eventId) in self.overlappingTimers[self.dayOffset] or (serviceRef, eventId) in self.notrecordingTimers[self.dayOffset]:
			self.unhandledKey.show()
			return
		if (ref_str, eventId) in self.overlappingTimers[self.dayOffset] or (ref_str, eventId) in self.notrecordingTimers[self.dayOffset]:
			self.unhandledKey.show()
			return
		if begin <= int(time()) or (begin - int(time())) <= 60 and config.plugins.PrimeTimeManager.ViewLiveType.value == "zaprec":
			self.unhandledKey.show()
			return
		timerEntry = self.getIsInTimer(selected)
		# try turning a record timer event into a view live event
		timerServicesList = (serviceRef, eventId) in self.timerServices[self.dayOffset]
		if timerServicesList:
			if timerEntry is not None and not timerEntry.isRunning():
				if timerEntry.repeated:
					text = _("Prime Time Manager:\n\nSorry, but turning a repeated timer into a view live event isn't supported.")
					self.session.open(MessageBox, text, MessageBox.TYPE_INFO)
				else:
					if config.plugins.PrimeTimeManager.ViewLiveType.value == "zaprec":
						timerEntry.justplay = False
						timerEntry.always_zap = True
					else:
						timerEntry.justplay = True
						timerEntry.always_zap = False
					# remove from record timer list
					self.timerServices[self.dayOffset].remove((serviceRef, eventId))
					# insert into the view live list
					self.viewLiveServices[self.dayOffset] = serviceRef
					# refresh prime time and favorite list
					self.updateSubLists(PT_AND_FAV)
					self.setSublistOffsets(PT_AND_FAV)
		elif not timerServicesList and timerEntry is not None and not timerEntry.isRunning() and self.viewLiveServices[self.dayOffset] == serviceRef:
			if timerEntry.repeated:
				text = _("Prime Time Manager:\n\nSorry, but turning a repeated timer into a view live event isn't supported.")
				self.session.open(MessageBox, text, MessageBox.TYPE_INFO)
			else:
				self.viewLiveServices[self.dayOffset] = ""
				timerEntry.justplay = False
				timerEntry.always_zap = False
				self.timerServices[self.dayOffset].append((serviceRef, eventId))
				# refresh prime time and favorite list
				self.updateSubLists(PT_AND_FAV)
				self.setSublistOffsets(PT_AND_FAV)
		else:
			# this event has a view live marker, remove it
			if self.viewLiveServices[self.dayOffset] == serviceRef:
				self.viewLiveServices[self.dayOffset] = ""
				self.updateSubLists(PT_AND_FAV)
				self.setSublistOffsets(PT_AND_FAV)
			# set view live marker for the selected entry
			else:
				self.viewLiveServices[self.dayOffset] = serviceRef

				if not selected in self.favoriteEvents[self.dayOffset].services:
					# add to the favorites if not there already
					self.addToFavorites(selected)
				else:
					self.updateSubLists(PT_AND_FAV)
					self.setSublistOffsets(PT_AND_FAV)

	# change the day +/- 1
	def changeDay(self, nextDay):
		if nextDay:
			if self.dayOffset + self.primeTimeIsOver >= 6:
				return
			self.dayOffset += 1
		else:
			if self.dayOffset < 1:
				return
			self.dayOffset -= 1

		self.activeList = self.primeTimeEvents[self.currentBouquet]

		# set the prime time
		self.setPrimeTime()

		# get the prime time events for day self.offset
		self.getPrimeTimeEvents()

		self.getOverlappingTimers()

		# add existing timers to the favorites
		self.getTimerEvents()

		self.updateLists()

		self.setPrimeTimeTitleString()

	# scroll the active list to the left
	def buttonLeft(self):
		if self.activeList.position > 1:
			self.activeList.position -= 1
			self.setListMarker()
			self.updateNavigation()
		elif self.activeList.offset > 0:
			self.activeList.offset -= 1
			if self.activeList.name == "ptList":
				self.setSublistOffsets(PRIMETIME)
			else:
				self.setSublistOffsets(FAVORITE)
			self.updateNavigation()
		elif self.activeList.name == "ptList" and self.activeList.size > 3 and self.activeList.offset == 0 and self.activeList.position == 1:
			index = self.activeList.size - 3
			self["ptList1"].moveToIndex(index - 2)
			self["ptList2"].moveToIndex(index - 1)
			self["ptList3"].moveToIndex(index)
			self.activeList.position = 3
			self.activeList.offset = index
			self.updateLists()
			self.updateNavigation()
		else:
			self.unhandledKey.show()

	# scroll the active list to the right
	def buttonRight(self):
		if self.activeList.position < 3:
			if self.activeList.size > self.activeList.position:
				self.activeList.position += 1
				self.setListMarker()
				self.updateNavigation()
		elif self.activeList.offset < self.activeList.size - 3:
			self.activeList.offset += 1
			if self.activeList.name == "ptList":
				self.setSublistOffsets(PRIMETIME)
			else:
				self.setSublistOffsets(FAVORITE)
			self.updateNavigation()
		elif self.activeList.name == "ptList" and self.activeList.size > 3 and (self.activeList.offset == self.activeList.size - 3):
			self["ptList1"].moveToIndex(0)
			self["ptList2"].moveToIndex(1)
			self["ptList3"].moveToIndex(2)
			self.activeList.offset = 0
			self.activeList.position = 1
			self.updateLists()
			self.updateNavigation()
		else:
			self.unhandledKey.show()

	# close the plugin
	def buttonCancel(self):
		self.cleanupTimers()
		if config.plugins.PrimeTimeManager.CheckConflictOnExit.value:
			check_on = False
			simulTimerList = None
			for timer in self.recordTimer.timer_list:
				timersanitycheck = TimerSanityCheck(self.recordTimer.timer_list, timer)
				if not timersanitycheck.check():
					check_on = True
					simulTimerList = timersanitycheck.getSimulTimerList()
					break
			if check_on:
				total = ""
				if simulTimerList is not None:
					try:
						total = _("\nTotal number of conflicts: %s") % (len(simulTimerList) - 1)
					except:
						pass
				AddPopup(_("Sorri!\nConflict timers in timers.xml detected!\nPlease recheck it!") + total, type = MessageBox.TYPE_ERROR, timeout = 0, id = "TimerLoadFailed")
		self.close()

	# previous bouquet selected
	def prevBouquet(self):
		# return if there's only one bouquet
		if self.bouquetCount == 1:
			return

		if self.currentBouquet > 0:
			self.currentBouquet -= 1
		else:
			self.currentBouquet = self.bouquetCount -1

		self.setPrimeTimeTitleString()
		print '[PrimeTimeManager] Selected next bouquet'

		self.activeList = self.primeTimeEvents[self.currentBouquet]
		self.updateLists()
		self.updateNavigation()

	# next bouquet selected
	def nextBouquet(self):
		# return if there's only one bouquet
		if self.bouquetCount == 1:
			return

		if self.currentBouquet < self.bouquetCount -1:
			self.currentBouquet += 1
		else:
			self.currentBouquet = 0

		self.setPrimeTimeTitleString()
		print '[PrimeTimeManager] Selected previous bouquet'

		self.activeList = self.primeTimeEvents[self.currentBouquet]
		self.updateLists()
		self.updateNavigation()

	# add or remove events
	def buttonOk(self):
		# prime time list is active, add item to favorite list if it's not there already
		if self.activeList.name == "ptList":
			# get the currently selected prime time list entry
			selected = self["ptList" + str(self.primeTimeEvents[self.currentBouquet].position)].getCurrent()[0]
			begin = selected[BEGIN]
			sRef = selected[SERVICEREF]
			eventId = selected[EVENTID]

			# don't add the selected item to the favorites because it has no begin time (epg data)
			if begin == None:
				self.unhandledKey.show()
				return

			# can't add a timer entry to the favorites
			ref_str = GetWithAlternative(sRef)
			if (sRef, eventId) in self.timerServices[self.dayOffset] or (ref_str, eventId) in self.timerServices[self.dayOffset]:
				self.unhandledKey.show()
				return
			if begin <= int(time()) or (begin - int(time())) <= 60:
				text = _('This event "%s" has already begun or will begin in the next few minutes.\nWe can not add it to your list of favorites, as will instantly record.\nJust want to switch to this service?') % selected[TITLE]
				self.session.openWithCallback(boundFunction(self.zapToConfirmed, sRef), MessageBox, text, MessageBox.TYPE_YESNO, default=False)
				return
			# add the entry if it's not in the favorite list already
			self.addToFavorites(selected)

		# favorite list is active
		else:
			# delete the selected favorite list entry
			selectedIndex = self["favList" + str(self.favoriteEvents[self.dayOffset].position)].getSelectedIndex()
			selected = self.favoriteEvents[self.dayOffset].services[selectedIndex]
			sRef = selected[SERVICEREF]
			eventId = selected[EVENTID]

			ref_str = GetWithAlternative(sRef)
			if (sRef, eventId) in self.timerServices[self.dayOffset] or (ref_str, eventId) in self.timerServices[self.dayOffset]:
				# check if it's a repeated timer
				timerEntry = self.getIsInTimer(selected)
				if timerEntry is not None:
					if timerEntry.repeated:
						# the user is trying to remove a repeated timer entry from the favorites
						text = _('This is a repeated timer! Do you really want to delete the repeated timer for "%s"?') % selected[TITLE]
					else:
						text = ""
						if timerEntry.isRunning() and not timerEntry.justplay:
							text = _('Recording is in progress.\n')
						# the user is trying to remove a timer entry from the favorites
						text += _('Do you really want to delete the timer for "%s"?') % selected[TITLE]
					self.session.openWithCallback(boundFunction(self.deleteTimerConfirmed, selected), MessageBox, text, default=False)
			else:
				self.removeEntryFromFavorites(selected, False)
				timerEntry = self.getIsInTimer(selected)
				if timerEntry is not None and eventId == timerEntry.eit:
					try:
						self.recordTimer.removeEntry(timerEntry)
					except:
						pass
				self.setSetDayButton()

	def zapToConfirmed(self, sRef, answer):
		if answer and sRef is not None:
			try:
				if self.servicelist is not None:
					self.root = self.servicelist.getRoot()
					if self.root and self.bouquets is not None:
						if self.root != self.bouquets[self.currentBouquet][1]:
							self.servicelist.clearPath()
							if self.servicelist.bouquet_root != self.bouquets[self.currentBouquet][1]:
								self.servicelist.enterPath(self.servicelist.bouquet_root)
							self.servicelist.enterPath(self.bouquets[self.currentBouquet][1])
						self.servicelist.setCurrentSelection(ServiceReference(sRef).ref)
						self.servicelist.zap()
			except:
				pass
			try:
				self.session.nav.playService(ServiceReference(sRef).ref)
			except:
				pass

	# show more information for the event and maybe similar events
	def showEventView(self):
		print "[PrimeTimeManager] Opening base event view."
		# get the selected entry from the active list
		selected = self[self.activeList.name + str(self.activeList.position)].getCurrent()

		if selected and selected[0][EVENTID]:
			event = self.epgcache.lookupEventId(eServiceReference(selected[0][SERVICEREF]), selected[0][EVENTID])
			self.session.open(EventViewSuperSimple, event, ServiceReference(selected[0][SERVICEREF]), None, self.openSimilarList, self.showTimerEntry, self.getIsTimer)
		else:
			self.unhandledKey.show()

	def openSimilarList(self, eventid, refstr):
		self.session.open(EPGSelection, refstr, None, eventid)

	def getIsTimer(self):
		selected = self[self.activeList.name + str(self.activeList.position)].getCurrent()[0]
		sRef = selected[SERVICEREF]
		eventId = selected[EVENTID]
		ref_str = GetWithAlternative(sRef)
		if eventId is None:
			return False
		elif (sRef, eventId) in self.timerServices[self.dayOffset] or (ref_str, eventId) in self.timerServices[self.dayOffset]:
			return True
		else:
			return False

	# user wants to add a new timer
	def showTimerEntry(self):
		# get the selected entry from the active list
		selected = self[self.activeList.name + str(self.activeList.position)].getCurrent()[0]
		sRef = selected[SERVICEREF]
		eventId = selected[EVENTID]
		begin = selected[BEGIN]
		title = selected[TITLE]
		ref_str = GetWithAlternative(sRef)
		# it's impossible to set a timer without epg data
		if eventId is None:
			self.unhandledKey.show()
			return
		elif (sRef, eventId) in self.timerServices[self.dayOffset] or (ref_str, eventId) in self.timerServices[self.dayOffset]:
			text = ""
			timerEntry = self.getIsInTimer(selected)
			if timerEntry is not None and timerEntry.isRunning() and not timerEntry.justplay:
				text = _('Recording is in progress.\n')
			text += _('Do you really want to delete the timer for "%s"?') % selected[TITLE]
			self.session.openWithCallback(boundFunction(self.deleteTimerConfirmed, selected), MessageBox, text, default=False)
		else:
			print "[PrimeTimeManager] Opening Timer Entry Screen"
			if begin <= int(time()) or (begin - int(time())) <= 60:
				text = _('This event will be an instant record.\n')
				text += _('Add timer for "%s"?') % title
				self.session.openWithCallback(boundFunction(self.addInstantRecord, selected), MessageBox, text, default=False)
			else:
				timerEntry = self.getRecordTimerEntry(selected)
				self.session.openWithCallback(boundFunction(self.timerEntryScreenClosed, selected), TimerEntry, timerEntry)

	def addInstantRecord(self, selected, result):
		if result:
			timerEntry = self.getRecordTimerEntry(selected)
			self.session.openWithCallback(boundFunction(self.timerEntryScreenClosed, selected), TimerEntry, timerEntry)

	# enable / disable the "set day" button
	def setSetDayButton(self):
		numFavorites = len(self.favoriteEvents[self.dayOffset].services)

		if numFavorites == 0:
			self["key_yellow"].text = ""
			self.setDayEnabled = False
		else:
			self["key_yellow"].text = _("Set day")
			self.setDayEnabled = True

	# enable / disable the "set timer" button
	def setSetTimerButton(self):
		selected = self[self.activeList.name + str(self.activeList.position)].getCurrent()[0]
		sRef = selected[SERVICEREF]
		eventId = selected[EVENTID]
		ref_str = GetWithAlternative(sRef)
		if eventId is None:
			self["key_green"].text = ""
		elif (sRef, eventId) in self.timerServices[self.dayOffset] or (ref_str, eventId) in self.timerServices[self.dayOffset]:
			self["key_green"].text = _("Remove timer")
		else:
			self["key_green"].text = _("Add Timer")

	def showSettings(self):
		self.session.open(PrimeTimeSettings)

	######################
	### MISC FUNCTIONS ###
	######################

	def sRefHDSortFunc(self, x):
		if x[1] in self.serviceRefsHD:
			return x

	# get a list of service refs for all HD services
	def getHDServices(self):
		if self.serviceRefsHD != None:
			return
		print "[PrimeTimeManager] Searching HD Services"
		self.serviceRefsHD = []
		refstr = '%s FROM SATELLITES' % (service_types_tv)
		ref = eServiceReference(refstr)
		counter = i = 0
		if config.servicelist.lastmode.value == "tv" and HardwareInfo().get_device_name() != "dm7025":
			counter = 1

		while i <= counter:
			if i:
				refstr ='%s FROM SATELLITES' % (service_types_tv_hd)
				ref = eServiceReference(refstr)

			servicelist = self.serviceHandler.list(ref)
			if not servicelist is None:
				while True:
					service = servicelist.getNext()
					if not service.valid(): #check if end of list
						break

					if i and (service.getPath().find("FROM PROVIDER") == -1):
						list = self.serviceHandler.list(service)
						if list:
							while True:
								s = list.getNext()
								if not s.valid():
									break
									
								self.serviceRefsHD.append(s.toString())
			i += 1

		print "[PrimeTimeManager] Found %s HD services" % len(self.serviceRefsHD)

	# show pixmaps for possible scroll directions of prime time and favorite list
	def setScrollPixmaps(self, listObject):
		if listObject.size - listObject.offset > 3:
			self[listObject.name + "ScrollRight"].show()
		else:
			self[listObject.name + "ScrollRight"].hide()

		if listObject.offset > 0:
			self[listObject.name + "ScrollLeft"].show()
		else:
			self[listObject.name + "ScrollLeft"].hide()

	# user finished timer change
	def timerEntryScreenClosed(self, selected, result):
		if result[0]:
			timerEntry = result[1]
			add_favorite = True

			# a new timer was set or reset
			print "[PrimeTimeManager] timer was set from Timer Entry Screen."

			timersanitycheck = TimerSanityCheck(self.recordTimer.timer_list, timerEntry)
			if timersanitycheck.check():
				if selected in self.favoriteEvents[self.dayOffset].services:
					self.removeEntryFromFavorites(selected, False)
					timer = self.getIsInTimer(selected)
					if timer is not None and selected[EVENTID] == timer.eit:
						try:
							self.recordTimer.removeEntry(timer)
						except:
							pass
				self.recordTimer.addTimerEntry(timerEntry)
				if timerEntry is not None:
					timer_ref = GetWithAlternative(timerEntry.service_ref.ref.toString())
					if timerEntry.isRunning():
						if not timerEntry.justplay:
							if not (timerEntry.service_ref.ref.toString(), timerEntry.eit) in self.overlappingTimers[self.dayOffset]:
								self.overlappingTimers[self.dayOffset].append((timerEntry.service_ref.ref.toString(), timerEntry.eit))
							if not (timerEntry.service_ref.ref.toString(), timerEntry.eit) in self.timerServices[self.dayOffset]:
								self.timerServices[self.dayOffset].append((timerEntry.service_ref.ref.toString(), timerEntry.eit))
							if not (timer_ref, timerEntry.eit) in self.overlappingTimers[self.dayOffset]:
								self.overlappingTimers[self.dayOffset].append((timer_ref, timerEntry.eit))
							if not (timer_ref, timerEntry.eit) in self.timerServices[self.dayOffset]:
								self.timerServices[self.dayOffset].append((timer_ref, timerEntry.eit))
						else:
							if not timerEntry.repeated:
								try:
									self.recordTimer.removeEntry(timerEntry)
								except:
									pass
								add_favorite = False
							else:
								if not (timerEntry.service_ref.ref.toString(), timerEntry.eit) in self.notrecordingTimers[self.dayOffset]:
									self.notrecordingTimers[self.dayOffset].append((timerEntry.service_ref.ref.toString(), timerEntry.eit))
								if not (timerEntry.service_ref.ref.toString(), timerEntry.eit) in self.timerServices[self.dayOffset]:
									self.timerServices[self.dayOffset].append((timerEntry.service_ref.ref.toString(), timerEntry.eit))
								if not (timer_ref, timerEntry.eit) in self.notrecordingTimers[self.dayOffset]:
									self.notrecordingTimers[self.dayOffset].append((timer_ref, timerEntry.eit))
								if not (timer_ref, timerEntry.eit) in self.timerServices[self.dayOffset]:
									self.timerServices[self.dayOffset].append((timer_ref, timerEntry.eit))
					else:
						if not (timerEntry.service_ref.ref.toString(), timerEntry.eit) in self.notrecordingTimers[self.dayOffset]:
							self.notrecordingTimers[self.dayOffset].append((timerEntry.service_ref.ref.toString(), timerEntry.eit))
						if not (timerEntry.service_ref.ref.toString(), timerEntry.eit) in self.timerServices[self.dayOffset]:
							self.timerServices[self.dayOffset].append((timerEntry.service_ref.ref.toString(), timerEntry.eit))
						if not (timer_ref, timerEntry.eit) in self.notrecordingTimers[self.dayOffset]:
							self.notrecordingTimers[self.dayOffset].append((timer_ref, timerEntry.eit))
						if not (timer_ref, timerEntry.eit) in self.timerServices[self.dayOffset]:
							self.timerServices[self.dayOffset].append((timer_ref, timerEntry.eit))
				self.setSetTimerButton()
				if add_favorite:
					self.addToFavorites(selected)

			else:
				text = _("Prime Time Manager:\n\nSorry, but a timer for %s can't be set because there are conflicts with other timers.") % selected[TITLE]
				self.session.open(MessageBox, text, MessageBox.TYPE_INFO)
		else:
			# user deleted an existing timer or aborted the creation of a new timer
			print "[PrimeTimeManager] user aborted timer creation from Timer Entry."
			
		self.setSetDayButton()

	# remove timer repetitions from the favorites
	def removeRepeatedFavorites(self, event, repeated):
		i = 0
		while i <= 6:
			if event in self.favoriteEvents[i].services:
				sRef = event[SERVICEREF]
				self.favoriteEvents[i].services.remove(event)
				self.favoriteEvents[i].size -= 1

				# delete remaining favorite entries
				if repeated:
					while i <= 6:
						for item in self.favoriteEvents[i].services:
							if funcRefStr(item[SERVICEREF]) == funcRefStr(sRef):
								self.favoriteEvents[i].services.remove(item)
								self.favoriteEvents[i].size -= 1
								continue
						i += 1
			i += 1

	# show the extended service description
	def showDescription(self):
		selected = self[self.activeList.name + str(self.activeList.position)].getCurrent()[0]
		text = ""
		if not selected:
			self["description"].setText(text)
			return
		getEventName = selected[TITLE]
		shortDescription = selected[SHORTDESC]
		extDescription = selected[EXTDESC]
		if getEventName is not None and shortDescription is not None and getEventName != shortDescription:
			text = getEventName + "\n"
		if shortDescription is not None:
			text += shortDescription + "\n\n"
		if extDescription is not None:
			text += extDescription

		self["description"].setText(text)

		if self["description"].pages > 1:
			self["infoPixmap"].show()
		else:
			self["infoPixmap"].hide()

	# set the prime time title description
	def setPrimeTimeTitleString(self):
		bouquetName = self.bouquets[self.currentBouquet][0]
		if self.alternatePrimeTime:
			alternatePrimeTime = _("Secondary")
		else:
			alternatePrimeTime = _("Primary")

		if self.dayOffset == 0 and not self.primeTimeIsOver:
			text = _("%s prime time | events today (%s) | Bouquet: %s") % (alternatePrimeTime, self.primeTimeDay, bouquetName)
		else:
			text = _("%s prime time | events today +%s (%s) | Bouquet: %s") % (alternatePrimeTime, self.dayOffset + self.primeTimeIsOver, self.primeTimeDay, bouquetName)

		self["primetime"].text = text

	#######################
	### TIMER FUNCTIONS ###
	#######################

	# find and return a RecordTimerEntry for an event
	def getRecordTimerEntry(self, event):
		serviceRef = ServiceReference(event[SERVICEREF])
		beginTime = event[BEGIN] - config.recording.margin_before.value * 60
		endTime = event[BEGIN] + event[DURATION] + config.recording.margin_after.value * 60
		title = event[TITLE]
		shortDesc = event[SHORTDESC]
		eventId = event[EVENTID]
		timerEntry = RecordTimerEntry(serviceRef, beginTime, endTime, title, shortDesc, eventId)
		return timerEntry

	# add existing and overlapping timer events to the favorite list
	def getOverlappingTimers(self):
		for timer in self.recordTimer.timer_list:
			# is it an overlapping timer?
			if (timer.begin - config.recording.margin_before.value * 60 <= self.primeTime) and (timer.end - config.recording.margin_after.value * 60 > self.primeTime):
				timer_ref = GetWithAlternative(str(timer.service_ref))
				if timer.isRunning():
					if not timer.justplay:
						if not (timer_ref, timer.eit) in self.overlappingTimers[self.dayOffset]:
							self.overlappingTimers[self.dayOffset].append((timer_ref, timer.eit))
						if not (timer.service_ref.ref.toString(), timer.eit) in self.overlappingTimers[self.dayOffset]:
							self.overlappingTimers[self.dayOffset].append((timer.service_ref.ref.toString(), timer.eit))
							self.addTimerToFavorites(timer)
							print "[PrimeTimeManager] Add recording timer event %s" % timer.service_ref.getServiceName()
				else:
					if not (timer_ref, timer.eit) in self.notrecordingTimers[self.dayOffset]:
						self.notrecordingTimers[self.dayOffset].append((timer_ref, timer.eit))
					if not (timer.service_ref.ref.toString(), timer.eit) in self.notrecordingTimers[self.dayOffset]:
						self.notrecordingTimers[self.dayOffset].append((timer.service_ref.ref.toString(), timer.eit))
						self.addTimerToFavorites(timer)
						print "[PrimeTimeManager] Add overlapping timer event %s" % timer.service_ref.getServiceName()

	# add timer events to the favorite list
	def getTimerEvents(self):
		i = 0
		while i < self.bouquetCount:
			for event in self.primeTimeEvents[i].services:
				if (event[EVENTID] and event[BEGIN] and event[DURATION] and event[SERVICEREF]) is not None:
					timerEntry = self.getIsInTimer(event)
					if timerEntry is not None and (timerEntry.begin - config.recording.margin_before.value * 60 <= self.primeTime) and (timerEntry.end - config.recording.margin_after.value * 60 > self.primeTime): #and not timerEntry.isRunning():
						try:
							if timerEntry.primeTime:
								continue
						except AttributeError:
							pass
						self.addToFavorites(event)
						ref_str = GetWithAlternative(event[SERVICEREF])
						if not (ref_str, event[EVENTID]) in self.timerServices[self.dayOffset]:
							self.timerServices[self.dayOffset].append((ref_str, event[EVENTID]))
						if not (timerEntry.service_ref.ref.toString(), timerEntry.eit) in self.timerServices[self.dayOffset]:
							self.timerServices[self.dayOffset].append((timerEntry.service_ref.ref.toString(), timerEntry.eit))
			i += 1
			# need to set an offset?
			if self.favoriteEvents[self.dayOffset].size > 3:
				self.favoriteEvents[self.dayOffset].offset = self.favoriteEvents[self.dayOffset].size - 3

	# taken from RecordTimer.py and modified to return a RecordTimerEntry (or None) for an event
	def getIsInTimer(self, event):
		x = ServiceReference(event[SERVICEREF]).ref.toString()
		eventref = funcRefStr(x)
		for timer in self.recordTimer.timer_list:
			if eventref == funcRefStr(timer.service_ref.ref.toString()) and event[EVENTID] == timer.eit:
				return timer
		return None

	# called when the user confirmed or aborted the deletion of a timer
	def deleteTimerConfirmed(self, selected, result):
		if result:
			timerEntry = self.getIsInTimer(selected)
			if timerEntry is not None:
				try:
					if timerEntry.isRunning():
						timerEntry.afterEvent = AFTEREVENT.NONE
						NavigationInstance.instance.RecordTimer.removeEntry(timerEntry)
					else:
						self.recordTimer.timer_list.remove(timerEntry)
				except:
					pass
			if (selected[SERVICEREF], selected[EVENTID]) in self.timerServices[self.dayOffset]:
				self.timerServices[self.dayOffset].remove((selected[SERVICEREF], selected[EVENTID]))
			if (selected[SERVICEREF], selected[EVENTID]) in self.overlappingTimers[self.dayOffset]:
				self.overlappingTimers[self.dayOffset].remove((selected[SERVICEREF], selected[EVENTID]))
			if (selected[SERVICEREF], selected[EVENTID]) in self.notrecordingTimers[self.dayOffset]:
				self.notrecordingTimers[self.dayOffset].remove((selected[SERVICEREF], selected[EVENTID]))
			ref_str = GetWithAlternative(selected[SERVICEREF])
			if (ref_str, selected[EVENTID]) in self.timerServices[self.dayOffset]:
				self.timerServices[self.dayOffset].remove((ref_str, selected[EVENTID]))
			if (ref_str, selected[EVENTID]) in self.overlappingTimers[self.dayOffset]:
				self.overlappingTimers[self.dayOffset].remove((ref_str, selected[EVENTID]))
			if (ref_str, selected[EVENTID]) in self.notrecordingTimers[self.dayOffset]:
				self.notrecordingTimers[self.dayOffset].remove((ref_str, selected[EVENTID]))

			if config.plugins.PrimeTimeManager.RemoveFavorite.value:
				self.removeEntryFromFavorites(selected, False)

			self.setSetTimerButton()
			self.setSetDayButton()

	# remove temporary timers on exit
	def cleanupTimers(self):
		print '[PrimeTimeManager] removing temporary timer entries'
		# delete timers set by this plugin but no real timers
		for timerEntry in self.recordTimer.timer_list[:]:
			try:
				if timerEntry.primeTime:
					if timerEntry.isRunning():
						timerEntry.afterEvent = AFTEREVENT.NONE
						NavigationInstance.instance.RecordTimer.removeEntry(timerEntry)
					else:
						self.recordTimer.timer_list.remove(timerEntry)
			except AttributeError:
				pass

	##################
	### PRIME TIME ###
	##################

	# build or update the list of prime time events
	def getPrimeTimeEvents(self):
		i = 0
		while i < self.bouquetCount:
			bouquet = self.bouquets[i]
			services = self.getPrimeTimeList(bouquet[1])
			listObj = ListObject("ptList", bouquet[1], services, len(services))

			# TODO wird das auch nicht mehrmals ausgefuehrt?
			for service in services:
				self.serviceBouquet.update({service[SERVICEREF] : bouquet[0]})

			# TODO was war noch gleich der sinn hiervon?
			if len(self.primeTimeEvents) != len(self.bouquets):
				self.primeTimeEvents.append(listObj)
			else:
				self.primeTimeEvents[i].services = services

			i += 1

	# set the prime time (day offset optional)
	def setPrimeTime(self):
		now = localtime(time())
		if self.alternatePrimeTime:
			dt = datetime(now.tm_year, now.tm_mon, now.tm_mday, config.plugins.PrimeTimeManager.Time2.value[0], config.plugins.PrimeTimeManager.Time2.value[1])
		else:
			dt = datetime(now.tm_year, now.tm_mon, now.tm_mday, config.plugins.PrimeTimeManager.Time1.value[0], config.plugins.PrimeTimeManager.Time1.value[1])

		if datetime.now() > dt:
			self.primeTimeIsOver = 1
		else:
			self.primeTimeIsOver = 0

		if self.dayOffset != 0:
			dt += timedelta(self.dayOffset)
		if self.primeTimeIsOver:
			dt += timedelta(self.primeTimeIsOver)

		self.primeTime = int(mktime(dt.timetuple()))
		self.primeTimeDay = dt.strftime("%A")

	# get epg info for the prime time
	def getPrimeTimeList(self, bouquet):
		if not bouquet.valid():
			return

		epgSearchList = []

		if bouquet.flags & eServiceReference.isDirectory:
			serviceList = self.serviceHandler.list(bouquet)
			while True:
				service = serviceList.getNext()
				if not service.valid():
					break
				if service.flags & (eServiceReference.isDirectory | eServiceReference.isMarker):
					continue
				epgSearchList.append((service.toString(), 0, self.primeTime))

		# I = Event Id
		# R = Service Reference
		# B = Event Begin Time
		# D = Event Duration
		# T = Event Title
		# S = Event Short Description
		# E = Event Extended Description
		# N = Service Name
		# X = Return a minimum of one tuple per service in the result list...
		epgSearchList.insert(0, 'IRBDTSENX')

		return self.epgcache.lookupEvent(epgSearchList)

#############################################################################################

class PreviewList(MenuList):
	def __init__(self, list, listType):
		MenuList.__init__(self, list)
		self.listType = listType
		self.l = eListboxPythonMultiContent()
		self.l.setFont(0, gFont("Regular", 18))
		self.l.setBuildFunc(self.buildEventEntry)
		if self.listType is FAVORITE:
			self.l.setItemHeight(140)
		else:
			self.l.setItemHeight(115)

		self.favoritePixmap = LoadPixmap(cached = True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, 'Extensions/PrimeTimeManager/images/favorite.png'), desktop = getDesktop(0))
		self.clockPixmap = LoadPixmap(cached = True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, 'Extensions/PrimeTimeManager/images/epgclock.png'), desktop = getDesktop(0))
		self.clockOverlap = LoadPixmap(cached = True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, 'Extensions/PrimeTimeManager/images/clockOverlap.png'), desktop = getDesktop(0))
		self.clockNotrecord = LoadPixmap(cached = True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, 'Extensions/PrimeTimeManager/images/clockNotrecord.png'), desktop = getDesktop(0))
		
		self.digitList = []
		i = 0
		while i <= 10:
			name = 'Extensions/PrimeTimeManager/images/digit_' + str(i) + '.png'
			digitPixmap = LoadPixmap(cached = True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, name), desktop = getDesktop(0))
			self.digitList.append(digitPixmap)
			i += 1

	# build the list entry
	def buildEventEntry(self, data = None):
		(eventId, serviceRef, beginTime, durationTime, title, shortDescription, extendedDescription, shortServiceName) = data

		width = self.l.getItemSize().width()

		if self.listType is FAVORITE:
			offsetY = 25
			if self.conflictCounts:
				numConflicts = self.conflictCounts[serviceRef]
			else:
				numConflicts = 0

			if numConflicts > 0:
				conflictColor = 0x00FF0000
			else:
				conflictColor = 0x0000FF00
		else:
			offsetY = 0
			conflictColor = None

		res = [ None ]

		if eventId is None:
			title = _("No EPG data")
		else:
			begin = strftime("%H:%M", localtime(beginTime))

			res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 75 + offsetY, width / 2, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _("Begin time") + ":"))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, width / 2, 75 + offsetY, width / 2, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, "%s" % begin))

			if config.plugins.PrimeTimeManager.DurationOrEndTime.value == "duration":
				#duration = _("%dh:%02dmin") % (durationTime / 3600, (durationTime / 60) - ((durationTime / 3600) * 60))
				res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 95 + offsetY, width / 2, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _("Duration") + ":"))
				res.append((eListboxPythonMultiContent.TYPE_TEXT, width / 2, 95 + offsetY, width / 2, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _("%d min") % (durationTime / 60)))
			else:
				end = strftime("%H:%M", localtime(beginTime + durationTime))
				res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 95 + offsetY, width / 2, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _("End time") + ":"))
				res.append((eListboxPythonMultiContent.TYPE_TEXT, width / 2, 95 + offsetY, width / 2, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, "%s" % end))

			if self.listType is FAVORITE:
				bouquet = self.serviceBouquet[serviceRef]
				res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 75, width, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _("Bouquet:")))
				res.append((eListboxPythonMultiContent.TYPE_TEXT, width / 2, 75, width / 2, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, bouquet))

				if numConflicts > 9:
					numConflicts = 10
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, width - 20, 103, 17, 30, self.digitList[numConflicts]))

			if (serviceRef, eventId) in self.timerServices:
				if (serviceRef, eventId) in self.overlappingTimers:
					res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, width - 21, 0, 21, 21, self.clockOverlap))
				elif (serviceRef, eventId) in self.notrecordingTimers:
					res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, width - 21, 0, 21, 21, self.clockNotrecord))
				else:
					res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, width - 21, 0, 21, 21, self.clockPixmap))
			elif serviceRef in self.viewLiveServices:
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, width - 21, 0, 21, 21, self.favoritePixmap))

		res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 0, width - 23, 23, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, shortServiceName))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 30, width, 44, 0, RT_HALIGN_LEFT|RT_VALIGN_TOP|RT_WRAP, title))

		return res

	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		#self.instance.setWrapAround(True)

	def preWidgetRemove(self, instance):
		instance.setContent(None)

	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def setList(self, list, conflictCounts, serviceBouquet, timerServices, overlappingTimers, viewLiveServices, conflictSat, notrecordingTimers):
		self.list = list
		self.conflictCounts = conflictCounts
		self.serviceBouquet = serviceBouquet
		self.timerServices = timerServices
		self.overlappingTimers = overlappingTimers
		self.viewLiveServices = viewLiveServices
		self.conflictSat = conflictSat
		self.notrecordingTimers = notrecordingTimers
		self.l.setList(list)

	def deleteItem(self, index):
		del self.list[index]
		self.l.entryRemoved(index)

#############################################################################################

# used to store the prime time and favorite lists with additional information
class ListObject:
	def __init__(self, name, bouquetName, services, size):
		self.name = name		# the name of the gui list
		self.bouquetName = bouquetName	# the name of the bouquet
		self.services = services	# this list is holding service tuples
		self.size = size		# the size of the list
		self.offset = 0			# the offset in the list when the strip is scrolled
		self.position = 1		# SD res: 1 = left, 2 = middle, 3 = right

#############################################################################################

# used to store a transponders list of service refs and favorite services using it
class ConflictObject:
	def __init__(self, transponderServices = [], knownServices = []):
		self.transponderServices = transponderServices	# a list holding servicesrefs of a transponder
		self.knownServices = knownServices		# a list holding known services
		self.knownServicesSize = len(knownServices)	# the list size of known services list
		self.numSimilarEvents = 0			# the number of known services having similar events

#############################################################################################

# used to store similar event information
class SimilarObject:
	def __init__(self, sRef):
		self.sRef = sRef		# the service ref we're storing similar events for
		self.similarEvents = []		# a list of similar events
		self.similarEventsSize = 0	# the number of similar events

#############################################################################################

# used to show the event description and to check if the whole description can be displayed or the info icons should be shown
# TODO write own class because this one is ugly!
class NoScrollBarLabel(ScrollLabel):
	def __init__(self, text=""):
		GUIComponent.__init__(self)
		self.message = text
		self.instance = None
		self.long_text = None
		self.pages = None
		self.total = None

	def applySkin(self, desktop, parent):
		ret = False
		if self.skinAttributes is not None:
			skin.applyAllAttributes(self.long_text, desktop, self.skinAttributes, parent.scale)
			widget_attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib.find("transparent") != -1 or attrib.find("backgroundColor") != -1:
					widget_attribs.append((attrib,value))
			skin.applyAllAttributes(self.instance, desktop, widget_attribs, parent.scale)
			ret = True
		s = self.long_text.size()
		self.instance.move(self.long_text.position())
		lineheight=fontRenderClass.getInstance().getLineHeight( self.long_text.getFont() )
		if not lineheight:
			lineheight = 30 # assume a random lineheight if nothing is visible
		lines = (int)(s.height() / lineheight)
		self.pageHeight = (int)(lines * lineheight)
		self.instance.resize(eSize(s.width(), self.pageHeight+(int)(lineheight/6)))
		self.long_text.move(ePoint(0,0))
		self.long_text.resize(eSize(s.width()-30, self.pageHeight*16))
		self.setText(self.message)
		return ret
		
	def setText(self, text):
		self.message = text
		if self.long_text is not None and self.pageHeight:
			self.long_text.move(ePoint(0,0))
			self.long_text.setText(self.message)
			text_height=self.long_text.calculateSize().height()
			total=self.pageHeight
			pages=1
			while total < text_height:
				total=total+self.pageHeight
				pages=pages+1
			if pages > 1:
				self.total = total
				self.pages = pages
			else:
				self.total = None
				self.pages = None

	def GUIcreate(self, parent):
		self.instance = eWidget(parent)
		self.long_text = eLabel(self.instance)

	def GUIdelete(self):
		self.long_text = None
		self.instance = None

#############################################################################################

# show the "unhandled key" pixmap
class KeyNotHandled:
	def __init__(self, session, init=False):
		self.session = session
		self.unhandledKeyScreen = self.session.instantiateDialog(UnhandledKey)
		if init:
			self.unhandledKeyScreen.hide()
		self.hideTimer = eTimer()
		self.hideTimer.callback.append(self.unhandledKeyScreen.hide)

	def show(self):
		self.unhandledKeyScreen.show()
		self.hideTimer.start(1500, True)

#############################################################################################

# this is shown when the info key was pressed
class EventViewSuperSimple(Screen, EventViewBase):
	def __init__(self, session, Event, Ref, callback=None, similarEPGCB=None, showTimerEntry=None, getIsTimer=None):
		Screen.__init__(self, session)
		self.skinName = "EventView"
		self.event = Event
		self.currentService = Ref
		self.getIsTimer = getIsTimer
		self.showTimerEntry = showTimerEntry
		EventViewBase.__init__(self, Event, Ref, callback, similarEPGCB)
		self["key_green"] = Button("")
		self["key_yellow"] = Button("")
		self["key_blue"] = Button("")
		self.TMBD = False
		self.IMDb = False
		if fileExists("/usr/lib/enigma2/python/Plugins/Extensions/TMBD/plugin.pyo"):
			self.TMBD = True
			self["key_blue"].setText(_("Lookup in TMBD"))
		if fileExists("/usr/lib/enigma2/python/Plugins/Extensions/IMDb/plugin.pyo"):
			self.IMDb = True
			self["key_yellow"].setText(_("Search in IMDb"))
		if not self.IMDb and self.TMBD:
			self["key_yellow"].setText(_("Single EPG"))
		if (not self.TMBD and self.IMDb) or (not self.TMBD and not self.IMDb):
			self["key_blue"].setText(_("Single EPG"))
		self["epgactions"] = ActionMap(["EventViewEPGActions"],
			{
				"openSingleServiceEPG": self.runIMDb,
				"openMultiServiceEPG": self.runTMBD,
			})
		try:
			from Screens.EventView import EventViewContextMenu
			self["actions"] = ActionMap(["OkCancelActions", "EventViewActions"],
				{
					"cancel": self.close,
					"ok": self.close,
					"pageUp": self.pageUp,
					"pageDown": self.pageDown,
					"openSimilarList": self.openSimilarList,
					"timerAdd": self.timerAdd,
					"contextMenu": self.doContext
				})
		except:
			self["actions"] = ActionMap(["OkCancelActions", "EventViewActions"],
				{
					"cancel": self.close,
					"ok": self.close,
					"pageUp": self.pageUp,
					"pageDown": self.pageDown,
					"openSimilarList": self.openSimilarList,
					"timerAdd": self.timerAdd
				})

	def onCreate(self):
		try:
			self.setService(self.currentService)
			self.setEvent(self.event)
			if self.getIsTimer():
				self["key_green"].setText(_("Remove timer"))
			else:
				self["key_green"].setText(_("Add timer"))
		except:
			pass

	def timerAdd(self):
		try:
			self.showTimerEntry()
		except:
			pass

	def runTMBD(self):
		if fileExists("/usr/lib/enigma2/python/Plugins/Extensions/TMBD/plugin.pyo"):
			try:
				from Plugins.Extensions.TMBD.plugin import TMBD
			except:
				return
			cur = self.event
			if cur is not None:
				name2 = cur.getEventName()
				name3 = name2.split("(")[0].strip()
				eventname = name3.replace('"', '').replace('Х/Ф', '').replace('М/Ф', '').replace('Х/ф', '').replace('.', '')
				eventname = eventname.replace('0+', '').replace('(0+)', '').replace('6+', '').replace('(6+)', '').replace('7+', '').replace('(7+)', '').replace('12+', '').replace('(12+)', '').replace('16+', '').replace('(16+)', '').replace('18+', '').replace('(18+)', '')				
				try:
					tmbdsearch = config.plugins.tmbd.profile.value
				except:
					tmbdsearch = None
				if tmbdsearch != None:
					if config.plugins.tmbd.profile.value == "0":
						try:
							self.session.open(TMBD, eventname, False)
						except:
							pass
					else:
						try:
							from Plugins.Extensions.TMBD.plugin import KinoRu
							self.session.open(KinoRu, eventname, False)
						except:
							pass
				else:
					try:
						self.session.open(TMBD, eventname, False)
					except:
						pass
		else:
			if (not self.TMBD and self.IMDb) or (not self.TMBD and not self.IMDb):
				try:
					if self.currentService is not None and self.event is not None:
						ref = self.currentService.ref.toString()
						id = self.event.getEventId()
						self.session.open(PrimeTimeSingleSelection, ref, event_id=id)
				except:
					pass

	def runIMDb(self):
		if fileExists("/usr/lib/enigma2/python/Plugins/Extensions/IMDb/plugin.pyo"):
			cur = self.event
			if cur is not None:
				try:
					from Plugins.Extensions.IMDb.plugin import IMDB
					self.session.open(IMDB, cur.getEventName())
				except:
					pass
		else:
			if not self.IMDb and self.TMBD:
				try:
					if self.currentService is not None and self.event is not None:
						ref = self.currentService.ref.toString()
						id = self.event.getEventId()
						self.session.open(PrimeTimeSingleSelection, ref, event_id=id)
				except:
					pass

from enigma import getDesktop
HD = False
if getDesktop(0).size().width() >= 1280:
	HD = True
class PrimeTimeSelection(EPGSelection):
	if HD:
		skin = """<screen name="PrimeTimeSelection" position="90,100" size="1100, 576" title="Prime Time EPG Selection Multi">
			<widget name="date" position="880,0" size="200,28" font="Regular;24" valign="center" halign="right" foregroundColor="#ffd700" backgroundColor="transpBlack" transparent="1" />
			<widget source="Event" render="Label" position="420,5" size="150,24" backgroundColor="background" transparent="1" foregroundColor="red" font="Regular;22" valign="top">
				<convert type="EventTime">StartTime</convert>
				<convert type="ClockToText">ShortDate</convert>
			</widget>
			<widget source="Event" render="Label" position="490,5" size="80,24" backgroundColor="background" transparent="1" foregroundColor="red" font="Regular;22" halign="right" valign="top">
				<convert type="EventTime">StartTime</convert>
				<convert type="ClockToText" />
			</widget>
			<widget source="Event" render="Label" position="570,5" size="80,24" backgroundColor="background" transparent="1" foregroundColor="red" font="Regular;22" halign="left" valign="top">
				<convert type="EventTime">EndTime</convert>
				<convert type="ClockToText">Format: - %H:%M</convert>
			</widget>
			<widget source="Event" render="Label" position="680,5" size="250,24" halign="left" foregroundColor="white" backgroundColor="background" transparent="1"  font="Regular;22" valign="top" >
				<convert type="EventTime">Remaining</convert>
				<convert type="RemainingToText">InMinutes</convert>
			</widget>
			<widget source="Event" render="Label" position="20,30" size="1060,90" backgroundColor="background" foregroundColor="#00999999" halign="center" transparent="1" font="Regular;20">
				<convert type="EventName">ExtendedDescription</convert>
			</widget>
			<widget name="list" position="10,135" size="1080,380" itemHeight="24"  transparent="1" scrollbarMode="showOnDemand" foregroundColorSelected="#ffd700" selectionPixmap="/usr/lib/enigma2/python/Plugins/Extensions/PrimeTimeManager/images/sel.png" />
			<widget position="65, 540" size="95, 20" halign="left" source="global.CurrentTime" render="Label" font="Regular;20" backgroundColor="background" transparent="1" zPosition="3">
				<convert type="ClockToText">Default</convert>
			</widget>
			<ePixmap pixmap="skin_default/icons/clock.png" position="40, 542" zPosition="3" size="14,14" alphatest="on" />
			<widget position="190, 535" size="200,36" name="key_red" font="Regular;20" foregroundColor="red" halign="center" valign="center" backgroundColor="black" transparent="1" zPosition="3" />
			<widget position="390, 535" size="200,36" name="key_green" font="Regular;20" foregroundColor="green" halign="center" valign="center" backgroundColor="black" transparent="1" zPosition="3" />
			<widget position="590, 535" size="200,36" name="key_yellow" font="Regular;20" foregroundColor="yellow" halign="center" valign="center" backgroundColor="black" transparent="1" zPosition="3" />
			<widget position="790, 535" size="200,36" name="key_blue" font="Regular;20" foregroundColor="blue" halign="center" valign="center" backgroundColor="black" transparent="1" zPosition="3" />
			<eLabel name="new eLabel" position="0, 525" size="1100, 2" backgroundColor="grey" />
		</screen>"""
	else:
		skin = """<screen name="PrimeTimeSelection" position="center,center" size="560,430" title="Prime Time EPG Selection Multi">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
			<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="key_yellow" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget name="key_blue" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
			<ePixmap pixmap="skin_default/border_epg.png" position="5,70" size="551,361" alphatest="on" />
			<widget name="date" position="410,35" size="140,45" font="Regular;18" valign="center" halign="right" />
			<widget name="list" position="11,75" size="540,350" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, service, service_ref=None, day_time=-1, setPositionService=None, bouquetname=""):
		self.service_ref = service_ref
		self.day_time = day_time
		self.setPositionService = setPositionService
		self.bouquetname = bouquetname
		EPGSelection.__init__(self, session, service)
		self.skinName = "PrimeTimeSelection"
		self.setup_title = _("Bouquet: %s - EPG Selection Multi") % self.bouquetname
		self["actions"] = ActionMap(["EPGSelectActions", "OkCancelActions"],
			{
				"cancel": self.closeScreen,
				"ok": self.eventSelected,
				"timerAdd": self.timerAdd,
				"yellow": self.yellowButtonPressed,
				"blue": self.blueButtonPressed,
			})
		self["actions"].csel = self
		self.green = eTimer()
		self.green.callback.append(self.text_green)
		self.text_green()
		self.onClose.append(self.__closed)

	def __closed(self):
		if config.plugins.PrimeTimeManager.CloseMultiEPG.value:
			sref = self["list"].getCurrent() and self["list"].getCurrent()[1]
			if sref is not None:
				count = 0
				for x in self.services:
					count += 1
					if funcRefStr(x.ref.toString()) == funcRefStr(sref.ref.toString()):
						break
				self.setPositionService(num=count)

	def text_green(self):
		self["key_green"].setText("OK")
		if not self.green.isActive(): 
			self.green.start(300)

	def onCreate(self):
		try:
			self.setTitle(self.setup_title)
			l = self["list"]
			l.recalcEntrySize()
			self.ask_time = self.day_time
			l.fillMultiEPG(self.services, self.ask_time)
			l.moveToService(self.service_ref)
		except:
			pass

	def eventSelected(self):
		sref = self["list"].getCurrent()[1]
		if sref is not None:
			count = 0
			for x in self.services:
				count += 1
				if funcRefStr(x.ref.toString()) == funcRefStr(sref.ref.toString()):
					break
			self.setPositionService(num=count)
			self.closeScreen()

	def timerAdd(self):
		self.eventSelected()

class PrimeTimeSingleSelection(EPGSelection):
	def __init__(self, session, ref, event_id=None):
		self.event_id = event_id
		EPGSelection.__init__(self, session, ref)
		self.skinName = ["PrimeTimeSingleSelection", "EPGSelection"]
		self.green_key = eTimer()
		self.green_key.callback.append(self.text_green)
		self.text_green()

	def text_green(self):
		if self.key_green_choice != self.EMPTY:
			self["key_green"].setText("")
		if not self.green_key.isActive(): 
			self.green_key.start(300)

	def timerAdd(self):
		pass

	def onCreate(self):
		try:
			EPGSelection.onCreate(self)
			if self.event_id is not None:
				self["list"].moveToEventId(self.event_id)
		except:
			pass

	def eventSelected(self):
		pass

class PTMtimerSanityConflict(TimerSanityConflict):
	def __init__(self, session, timer):
		TimerSanityConflict.__init__(self, session, timer)

	def leave_cancel(self):
		conflict_text = self.isResolvedConflict()
		if conflict_text == "":
			self.close()
		else:
			self.session.openWithCallback(self.close, MessageBox, _("Conflict detected!") + conflict_text, MessageBox.TYPE_INFO, timeout=3)

	def isResolvedConflict(self):
		total = ""
		check_on = False
		simulTimerList = None
		for timer in self.session.nav.RecordTimer.timer_list:
			timersanitycheck = TimerSanityCheck(self.session.nav.RecordTimer.timer_list, timer)
			if not timersanitycheck.check():
				check_on = True
				simulTimerList = timersanitycheck.getSimulTimerList()
				break
		if check_on:
			if simulTimerList is not None:
				total = _("\nTotal number of conflicts: %s") % (len(simulTimerList) - 1)
		return total


def funcRefStr(service=None):
	if service:
		service = GetWithAlternative(service)
		return ':'.join(service.split(':')[:11])
	return ""

def getAlternativeChannels(service):
	alternativeServices = eServiceCenter.getInstance().list(eServiceReference(service))
	return alternativeServices and alternativeServices.getContent("S", True)

def GetWithAlternative(service):
	if service.startswith('1:134:'):
		channels = getAlternativeChannels(service)
		if channels:
			return channels[0]
	return service
