from . import _
from Components.config import config, getConfigListEntry, ConfigClock, ConfigDateTime, ConfigText, NoSave
# GUI (Screens)
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox

# for showSearchLog
from Tools.Directories import fileExists

# GUI (Components)
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.ConfigList import ConfigListScreen

from Components.MenuList import MenuList
from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT

from skin import parseColor, parseFont

import time
import datetime


class AutoTimerFilterList(MenuList):
	"""Defines a simple Component to show Timer name"""

	def __init__(self, entries):
		MenuList.__init__(self, entries, False, content=eListboxPythonMultiContent)

		self.l.setFont(0, gFont("Regular", 22))
		self.l.setBuildFunc(self.buildListboxEntry)
		self.l.setItemHeight(25)
		self.colorDisabled = 12368828

	def applySkin(self, desktop, parent):
		attribs = []
		if self.skinAttributes is not None:
			for (attrib, value) in self.skinAttributes:
				if attrib == "font":
					self.l.setFont(0, parseFont(value, ((1, 1), (1, 1))))
				elif attrib == "itemHeight":
					self.l.setItemHeight(int(value))
				elif attrib == "colorDisabled":
					self.colorDisabled = parseColor(value).argb()
				else:
					attribs.append((attrib, value))
		self.skinAttributes = attribs
		return MenuList.applySkin(self, desktop, parent)

	def buildListboxEntry(self, filter_txt):
		size = self.l.getItemSize()
		color = None
		return [
			None,
			(eListboxPythonMultiContent.TYPE_TEXT, 5, 0, size.width() - 5, size.height(), 0, RT_HALIGN_LEFT, filter_txt[1], color, color)
		]

	def getCurrent(self):
		cur = self.l.getCurrentSelection()
		return cur and cur[0]

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	def moveToEntry(self, entry):
		if entry is None:
			return
		idx = 0
		for x in self.list:
			if x[0] == entry:
				self.instance.moveSelectionTo(idx)
				break
			idx += 1


class AutoTimerFilterListOverview(Screen):

	skin = """<screen name="AutoTimerEditor" title="Edit AutoTimer" position="center,120" size="820,520">
		<ePixmap pixmap="skin_default/buttons/red.png" position="10,5" size="140,40" alphatest="on"/>
		<ePixmap pixmap="skin_default/buttons/green.png" position="210,5" size="140,40" alphatest="on"/>
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="410,5" size="140,40" alphatest="on"/>
		<ePixmap pixmap="skin_default/buttons/blue.png" position="610,5" size="140,40" alphatest="on"/>
		<widget source="key_red" render="Label" position="10,5" size="140,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" shadowColor="black" shadowOffset="-2,-2"/>
		<widget source="key_green" render="Label" position="210,5" size="140,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" shadowColor="black" shadowOffset="-2,-2"/>
		<widget source="key_yellow" render="Label" position="410,5" size="140,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" shadowColor="black" shadowOffset="-2,-2"/>
		<widget source="key_blue" render="Label" position="610,5" size="140,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" shadowColor="black" shadowOffset="-2,-2"/>
		<eLabel	position="10,50" size="800,1" backgroundColor="grey"/>
		<widget name="config" position="10,60" size="800,360" enableWrapAround="1" scrollbarMode="showOnDemand"/>
		<eLabel	position="10,430" size="800,1" backgroundColor="grey"/>
		<widget source="help" render="Label" position="10,440" size="800,70" font="Regular;20" halign="center" valign="center" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		try:
			self.skinName = "AutoTimerEditor"
			self.changed = False
			self["key_green"] = StaticText(_("Save"))
			self["key_yellow"] = StaticText(_("Delete"))
			self["key_blue"] = StaticText(_("Add"))
			self["key_red"] = StaticText(_("Close"))
			self["help"] = StaticText()
			filter_txt = ""
			path_filter_txt = "/etc/enigma2/autotimer_filter.txt"
			if fileExists(path_filter_txt):
				filter_txt = open(path_filter_txt).read()
				filter_txt = filter_txt.split("\n")
			self.FilterList = []
			for count, filter in enumerate(filter_txt):
				filter1 = filter.split(' - "')
				if len(filter1) > 1:
					time1 = time.mktime(datetime.datetime.strptime(filter1[0], "%d.%m.%Y, %H:%M").timetuple())
					Filter = ([count, filter1[1][:-1], time1],)
					self.FilterList.append(Filter)
			self.FilterList.sort(key=lambda x: x[0][1].lower())
			self.sorted = 1
			self["config"] = AutoTimerFilterList(self.FilterList)
			self.updateFilterDate()
			self["config"].onSelectionChanged.append(self.updateFilterDate)
			self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "InfobarActions", "MenuActions"],
				{
					"ok": self.ok,
					"cancel": self.cancel,
					"red": self.cancel,
					"green": self.save,
					"yellow": self.remove,
					"blue": self.add,
					"showTv": self.sortList,
					"menu": self.add_copy,
				}
			)
			self.onLayoutFinish.append(self.setCustomTitle)

		except Exception:
			import traceback
			traceback.print_exc()

	def setCustomTitle(self):
		self.setTitle(_("AutoTimer ") + _("Filterlist"))

	def updateFilterDate(self):
		cur = self["config"].getCurrent()
		if cur is not None:
			timertime = datetime.datetime.fromtimestamp(cur[2]).strftime("%d.%m.%Y, %H:%M")
			self["help"].text = _("Timer from:\n") + timertime
		else:
			self["help"].text = " "

	def sortList(self):
		if self.sorted == 1:
			self.sorted = 0
			self.FilterList.sort(key=lambda x: x[0][0])
		elif self.sorted == 0:
			self.sorted = 2
			self.FilterList.sort(key=lambda x: x[0][2])
		else:
			self.FilterList.sort(key=lambda x: x[0][1].lower())
			self.sorted = 1
		self["config"].setList(self.FilterList)

	def selectionChanged(self):
		pass

	def add(self):
		self.session.openWithCallback(self.add_edit_Callback, AutoTimerFilterListEditor, None, 'add')

	def add_copy(self):
		current = self["config"].getCurrent()
		if current is not None:
			self.session.openWithCallback(self.add_edit_Callback, AutoTimerFilterListEditor, current, 'add')

	def addCallback(self, ret):
		pass

	def ok(self):
		current = self["config"].getCurrent()
		if current is not None:
			self.session.openWithCallback(self.add_edit_Callback, AutoTimerFilterListEditor, current, 'edit')

	def add_edit_Callback(self, ret, add_edit):
		if ret:
			date1 = ret[0][1].value
			time1 = ret[1][1].value
			filtertext = ret[2][1].value.strip().replace('"', "")
			for filter in self.FilterList:
				if filter[0][1] == filtertext:
					self.session.open(MessageBox, _("The filterEntry '%s' already exist!\nThe change was canceled.") % filtertext, MessageBox.TYPE_INFO)
					return
			date1 = datetime.datetime.fromtimestamp(date1)
			datetime1 = datetime.datetime(date1.year, date1.month, date1.day, time1[0], time1[1])
			filtertime = time.mktime(datetime1.timetuple())
			Filter = ([len(self.FilterList), filtertext, filtertime],)
			if add_edit == "add":
				self.FilterList.append(Filter)
			elif add_edit == "edit":
				cur_index = self["config"].getCurrentIndex()
				self.FilterList[cur_index] = Filter
			self.FilterList.sort(key=lambda x: x[0][self.sorted])
			self["config"].setList(self.FilterList)
			self.changed = True

	def remove(self):
		current = self["config"].getCurrent()
		if current is not None:
			self.session.openWithCallback(self.removeCallback, MessageBox, _("Do you really want to delete %s?") % (_("FilterEntry") + " '" + str(current[1]) + "'"), )

	def removeCallback(self, ret):
		cur = self["config"].getCurrentIndex()
		if ret and cur is not None:
			del self.FilterList[cur]
			self["config"].setList(self.FilterList)
			self.changed = True

	def cancel(self):
		self.close()

	def save(self):
		if self.changed:
			self.FilterList.sort(key=lambda x: x[0][0])
			path_filter_txt = "/etc/enigma2/autotimer_filter.txt"
			filter_txt = ""
			file_search_log = open(path_filter_txt, "w")
			for filter in self.FilterList:
				timertime = datetime.datetime.fromtimestamp(filter[0][2]).strftime("%d.%m.%Y, %H:%M")
				filter_txt += timertime + ' - "' + filter[0][1] + '"\n'
			file_search_log.write(filter_txt)
			file_search_log.close()
		self.close()


class AutoTimerFilterListEditor(Screen, ConfigListScreen):
	"""Edit AutoTimer Filter"""

	skin = """<screen name="AutoTimerFilterEditor" title="Edit AutoTimer Filters" position="center,120" size="820,520">
		<ePixmap pixmap="skin_default/buttons/red.png" position="10,5" size="140,40" alphatest="on"/>
		<ePixmap pixmap="skin_default/buttons/green.png" position="210,5" size="140,40" alphatest="on"/>
		<widget source="key_red" render="Label" position="10,5" size="140,40" zPosition="1" font="Regular;20" backgroundColor="#9f1313" transparent="1" shadowColor="black" shadowOffset="-2,-2"/>
		<widget source="key_green" render="Label" position="210,5" size="140,40" zPosition="1" font="Regular;20" backgroundColor="#1f771f" transparent="1" shadowColor="black" shadowOffset="-2,-2"/>
		<eLabel	position="10,50" size="800,1" backgroundColor="grey"/>
		<widget name="config" position="10,60" size="800,450" enableWrapAround="1" scrollbarMode="showOnDemand"/>
	</screen>"""

	def __init__(self, session, filterEntry, add_edit):
		Screen.__init__(self, session)

		try:
			self.skinName = "AutoTimerFilterEditor"
			self.onChangedEntry = []
			self.add_edit = add_edit
			if filterEntry is not None:
				self.EntryDate = NoSave(ConfigDateTime(filterEntry[2], _("%d.%B %Y"), increment=86400))
				self.EntryTime = NoSave(ConfigClock(default=filterEntry[2]))
				self.EntryTitle = NoSave(ConfigText(default=filterEntry[1], fixed_size=False))
			else:
				self.EntryDate = NoSave(ConfigDateTime(time.time(), _("%d.%B %Y"), increment=86400))
				self.EntryTime = NoSave(ConfigClock(default=time.time()))
				self.EntryTitle = NoSave(ConfigText(default="", fixed_size=False))
			self.list = [
				getConfigListEntry(_("Date"), self.EntryDate),
				getConfigListEntry(_("Time"), self.EntryTime),
				getConfigListEntry(_("Title"), self.EntryTitle),
			]
			ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changed)
			self["key_red"] = StaticText(_("Cancel"))
			self["key_green"] = StaticText(_("Save"))
			self["actions"] = ActionMap(["SetupActions", "ColorActions"],
				{
					"cancel": self.cancel,
					"save": self.save,
				}
			)
			# Trigger change
			self.changed()
			self.onLayoutFinish.append(self.setCustomTitle)
		except Exception:
			import traceback
			traceback.print_exc()

	def setCustomTitle(self):
		self.setTitle(_("AutoTimer %s FilterListEntry") % self.add_edit)

	def changed(self):
		pass
		for x in self.onChangedEntry:
			try:
				x()
			except Exception:
				pass

	def cancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close(None, self.add_edit)

	def cancelConfirm(self, ret):
		if ret:
			self.close(None, self.add_edit)

	def save(self):
		if not self.list[2][1].value.strip():
			self.session.open(MessageBox, _("The title attribute is mandatory."), type=MessageBox.TYPE_ERROR, timeout=5)
		else:
			if self["config"].isChanged():
				self.close(self.list, self.add_edit)
			else:
				self.close(None, self.add_edit)
