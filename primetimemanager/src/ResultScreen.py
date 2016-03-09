from . import _
from time import localtime, strftime
from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.GUIComponent import GUIComponent
from Components.Sources.StaticText import StaticText
from enigma import eListboxPythonMultiContent, eListbox, gFont, getDesktop, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER, RT_HALIGN_CENTER, RT_VALIGN_TOP, RT_WRAP
from Screens.HelpMenu import HelpableScreen
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Tools.Directories import resolveFilename, SCOPE_CURRENT_PLUGIN, SCOPE_CURRENT_SKIN
from Tools.LoadPixmap import LoadPixmap
try:
	from Plugins.Extensions.AutoTimer.AutoTimerEditor import addAutotimerFromEvent
	AUTOTIMER = True
except ImportError:
	AUTOTIMER = False

size_width = getDesktop(0).size().width()

EVENTID		= 0
SERVICEREF	= 1
BEGIN		= 2
DURATION	= 3
TITLE		= 4
SHORTDESC	= 5
EXTDESC		= 6
SERVICENAME	= 7

skinPTMhdfull = """<screen title="%s" position="center,center" size="630,650">
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/PrimeTimeManager/images/red.png" position="35,20" size="140,2" transparent="1" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/PrimeTimeManager/images/green.png" position="175,20" size="140,2" transparent="1" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/PrimeTimeManager/images/yellow.png" position="315,20" size="140,2" transparent="1" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/PrimeTimeManager/images/blue.png" position="455,20" size="140,2" transparent="1" alphatest="on" />
		<widget render="Label" source="key_red" position="35,0" size="140,19" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;17" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
		<widget render="Label" source="key_green" position="175,0" size="140,19" zPosition="5" valign="center" halign="center" backgroundColor="green" font="Regular;17" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
		<widget render="Label" source="key_yellow" position="315,0" size="140,19" zPosition="5" valign="center" halign="center" backgroundColor="yellow" font="Regular;17" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
		<widget render="Label" source="key_blue" position="455,0" size="140,19" zPosition="5" valign="center" halign="center" backgroundColor="blue" font="Regular;17" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
		<widget render="Label" source="text_left" position="57,25" size="210,20" zPosition="5" valign="center" halign="center" font="Regular;18" transparent="1" foregroundColor="white" />
		<widget render="Label" source="text_right" position="332,25" size="210,20" zPosition="5" valign="center" halign="center" font="Regular;18" transparent="1" foregroundColor="white" />
		<widget name="list" position="57,50" scrollbarMode="showAlways" foregroundColorSelected="#00ffffff" backgroundColorSelected="#65535ff" size="516,600"/>
	</screen>""" % _("Prime Time Manager Conflict Results")
#############################################################################################
skinPTMsd = """<screen title="%s" position="center,center" size="630,520">
		<ePixmap pixmap="skin_default/buttons/red.png" position="35,0" size="140,40" transparent="1" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="175,0" size="140,40" transparent="1" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="315,0" size="140,40" transparent="1" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="455,0" size="140,40" transparent="1" alphatest="on" />
		<widget render="Label" source="key_red" position="35,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
		<widget render="Label" source="key_green" position="175,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="green" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
		<widget render="Label" source="key_yellow" position="315,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="yellow" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
		<widget render="Label" source="key_blue" position="455,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="blue" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
		<widget render="Label" source="text_left" position="57,40" size="210,25" zPosition="5" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" />
		<widget render="Label" source="text_right" position="332,40" size="210,25" zPosition="5" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" />
		<widget name="list" position="57,65" scrollbarMode="showAlways" foregroundColorSelected="#00ffffff" backgroundColorSelected="#65535ff" size="516,450"/>
	</screen>""" % _("Prime Time Manager Conflict Results")
#############################################################################################
class ResultScreen(Screen, HelpableScreen):
	def __init__(self, session, favoriteEvents):
		self.session = session
		self.favoriteEvents = favoriteEvents
		if size_width >= 1280 and len(self.favoriteEvents) > 3:
			self.skin = skinPTMhdfull
		else:
			self.skin = skinPTMsd
		Screen.__init__(self, session)
		self.list = [ ]
		self["list"] = ResultList(self.list)

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Accept"))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["text_left"] = StaticText(_("Favorite"))
		self["text_right"] = StaticText(_("Solution"))

		HelpableScreen.__init__(self)
		
		self["SetupActions"] = HelpableActionMap(self, "SetupActions",
		{
			"cancel":	(self.buttonCancel,	_("Close")),
			"ok":		(self.buttonOK,	_("Accept the events as shown")),
		}, -1)
		
		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
		{
			"red":		(self.buttonCancel,	_("Close")),
			"green":	(self.buttonAccept,	_("Accept the events as shown")),
		}, -1)
		
		self.visible = True
		self.onLayoutFinish.append(self.buildEventList)

	def buttonCancel(self):
		self.close(False)

	def buttonAccept(self):
		self.close(True)

	def buttonOK(self):
		self.session.openWithCallback(self.optionsConfirmed, MessageBox, _("Accept this solution?"), MessageBox.TYPE_YESNO)

	def optionsConfirmed(self, answer):
		if answer:
			self.close(True)

	def buildEventList(self, eventListIndex = 0):
		self["list"].setList([ (x,) for x in self.favoriteEvents])
		if len(self.favoriteEvents):
			self["list"].moveToIndex(eventListIndex)
		self["list"].show()

class ResultList(GUIComponent, object):
	def __init__(self, eventList):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setFont(0, gFont("Regular", 18))
		self.l.setBuildFunc(self.buildResultEntry)
		self.l.setItemHeight(150)
		self.onSelectionChanged = [ ]

		self.resultlist = LoadPixmap(cached = True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, 'Extensions/PrimeTimeManager/images/resultlist.png'), desktop = getDesktop(0))
		self.favoritePixmap = LoadPixmap(cached = True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, 'Extensions/PrimeTimeManager/images/favorite.png'), desktop = getDesktop(0))
		self.clockPixmap = LoadPixmap(cached = True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, 'Extensions/PrimeTimeManager/images/epgclock.png'), desktop = getDesktop(0))
		self.clockOverlap = LoadPixmap(cached = True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, 'Extensions/PrimeTimeManager/images/clockOverlap.png'), desktop = getDesktop(0))
		self.clockNotrecord = LoadPixmap(cached = True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, 'Extensions/PrimeTimeManager/images/clockNotrecord.png'), desktop = getDesktop(0))
		self.noConflictPixmap = LoadPixmap(cached = True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, 'Extensions/PrimeTimeManager/images/noConflict.png'), desktop = getDesktop(0))
		self.arrowRightPixmap = LoadPixmap(cached = True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, 'Extensions/PrimeTimeManager/images/right.png'), desktop = getDesktop(0))
		self.deletePixmap = LoadPixmap(cached = True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, 'Extensions/PrimeTimeManager/images/delete.png'), desktop = getDesktop(0))
		if AUTOTIMER and config.plugins.PrimeTimeManager.UseAutotimer.value:
			self.autotimerPixmap = LoadPixmap(cached = True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, 'Extensions/AutoTimer/plugin.png'), desktop = getDesktop(0))

		self.l.setList(eventList)

		self.digitList = []
		i = 0
		while i <= 10:
			name = 'Extensions/PrimeTimeManager/images/digit_' + str(i) + '.png'
			digitPixmap = LoadPixmap(cached = True, path=resolveFilename(SCOPE_CURRENT_PLUGIN, name), desktop = getDesktop(0))
			self.digitList.append(digitPixmap)
			i += 1

	def buildResultEntry(self, data):
		(favorite, bouquet, numConflicts, viewLive, isTimer, autoTimer, similarTimer, postsimilarTimer, conflictSat) = data

		# size left/right field 210x140
		# size middle field 50x140
		# borders 5
		width = self.l.getItemSize().width()

		if numConflicts > 9:
			numConflicts = 10
			
		if numConflicts > 0:
			conflictColor = 0x00FF0000
		else:
			conflictColor = 0x0000FF00

		res = [ None ]

		# left column
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 0, 0, width, 150, self.resultlist))

		begin = strftime("%H:%M", localtime(favorite[BEGIN]))

		res.append((eListboxPythonMultiContent.TYPE_TEXT, 5, 100, 105, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _("Begin time") + ":"))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, 105, 100, 105, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, "%s" % begin))

		if config.plugins.PrimeTimeManager.DurationOrEndTime.value == "duration":
			#duration = "%d:%02d" % (favorite[DURATION] / 60, favorite[DURATION] % 60)
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 5, 120, 105, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _("Duration") + ":"))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 105, 120, 105, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _("%d min") % (favorite[DURATION] / 60)))
		else:
			end = strftime("%H:%M", localtime(favorite[BEGIN] + favorite[DURATION]))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 5, 120, 105, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _("End time") + ":"))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 105, 120, 105, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, "%s" % end))

		res.append((eListboxPythonMultiContent.TYPE_TEXT, 5, 75, width, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _("Bouquet") + ":"))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, 105, 75, width / 2, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, bouquet))

		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 190, 103, 17, 30, self.digitList[numConflicts]))

		if isTimer == 1: # overlapping
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 215 - 21, 5, 21, 21, self.clockOverlap))
		elif isTimer == 3: # not record
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 215 - 21, 5, 21, 21, self.clockNotrecord))
		elif isTimer == 2: # normal timer
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 215 - 21, 5, 21, 21, self.clockPixmap))
		elif viewLive:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 215 - 21, 5, 21, 21, self.favoritePixmap))

		res.append((eListboxPythonMultiContent.TYPE_TEXT, 5, 0, 187, 23, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, favorite[SERVICENAME]))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, 5, 30, 210, 44, 0, RT_HALIGN_LEFT|RT_VALIGN_TOP|RT_WRAP, favorite[TITLE]))

		# middle column
		if similarTimer and similarTimer.begin > 0:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 229, 54, 32, 32, self.arrowRightPixmap))
		elif autoTimer:
			if AUTOTIMER and config.plugins.PrimeTimeManager.UseAutotimer.value:
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 229, 54, 32, 32, self.arrowRightPixmap))
			else:
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 229, 54, 32, 32, self.deletePixmap))
		else:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 229, 54, 32, 32, self.noConflictPixmap))

		# right column
		if similarTimer and similarTimer.begin > 0:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 485 - 21, 5, 21, 21, self.clockPixmap))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 275, 0, 187, 23, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, similarTimer.service_ref.getServiceName()))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 275, 30, 210, 44, 0, RT_HALIGN_LEFT|RT_VALIGN_TOP|RT_WRAP, similarTimer.name))

			t = localtime(similarTimer.begin)
			d = strftime("%02d.%02d.%04d" % (t[2], t[1], t[0]))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 275, 75, 105, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _("Date") + ":"))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 380, 75, 105, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, d))

			res.append((eListboxPythonMultiContent.TYPE_TEXT, 275, 100, 105, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _("Begin time") + ":"))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 380, 100, 105, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, "%s" % strftime("%H:%M", localtime(similarTimer.begin))))

			timerDuration = similarTimer.end - similarTimer.begin
			if config.plugins.PrimeTimeManager.DurationOrEndTime.value == "duration":
				#duration = "%d:%02d" % (timerDuration / 60, timerDuration % 60)
				res.append((eListboxPythonMultiContent.TYPE_TEXT, 275, 120, 105, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _("Duration") + ":"))
				res.append((eListboxPythonMultiContent.TYPE_TEXT, 380, 120, 105, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _("%d min") % (timerDuration / 60)))
			else:
				end = strftime("%H:%M", localtime(similarTimer.begin + favorite[DURATION]))
				res.append((eListboxPythonMultiContent.TYPE_TEXT, 275, 120, 105, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, _("End time") + ":"))
				res.append((eListboxPythonMultiContent.TYPE_TEXT, 380, 120, 105, 18, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, "%s" % end))
		elif autoTimer:
			if AUTOTIMER and config.plugins.PrimeTimeManager.UseAutotimer.value:
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 330, 50, 100, 40, self.autotimerPixmap))
			else:
				res.append((eListboxPythonMultiContent.TYPE_TEXT, 275, 0, 210, 140, 0, RT_HALIGN_CENTER|RT_VALIGN_CENTER, _("Favorite will be deleted!")))
		else:
			if numConflicts == 0:
				res.append((eListboxPythonMultiContent.TYPE_TEXT, 275, 0, 210, 140, 0, RT_HALIGN_CENTER|RT_VALIGN_CENTER, _("No conflicts found")))
			else:
				res.append((eListboxPythonMultiContent.TYPE_TEXT, 275, 0, 210, 140, 0, RT_HALIGN_CENTER|RT_VALIGN_CENTER, _("Conflicts were solved")))

		return res

	def selectionChanged(self):
		for x in self.onSelectionChanged:
			x()

	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)

	def preWidgetRemove(self, instance):
		instance.setContent(None)
		instance.selectionChanged.get().remove(self.selectionChanged)

	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def setList(self, list):
		self.l.setList(list)
