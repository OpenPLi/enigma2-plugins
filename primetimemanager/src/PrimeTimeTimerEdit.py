from . import _
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.config import config
from Components.MenuList import MenuList
from Components.TimerList import TimerList
from Components.TimerSanityCheck import TimerSanityCheck
from PrimeTimeTimerSanityCheck import PrimeTimeTimerSanityCheck
from Components.UsageConfig import preferredTimerPath
from RecordTimer import RecordTimerEntry, parseEvent, AFTEREVENT
from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.InputBox import PinInput
from ServiceReference import ServiceReference
from Screens.TimerEntry import TimerEntry, TimerLog
from Tools.BoundFunction import boundFunction
from time import time
from timer import TimerEntry as RealTimerEntry
from plugin import baseTimerEditList__init__

def PMTimerEditList__init__(self, session):
	baseTimerEditList__init__(self, session)
	if config.plugins.PrimeTimeManager.TimerEditKeyMenu.value:
		self["extactions"] = ActionMap(["MenuActions"],
			{
				"menu": self.openExtendedSetup
			}, -2)

def openExtendedSetup(self):
	cur = self["timerlist"].getCurrent()
	if cur:
		if not hasattr(cur, 'conflict_detection'):
			return 0
		menu = []
		currentSimulTimerList = []
		conflict_detection = None
		if not cur.conflict_detection:
			timersanitycheck = PrimeTimeTimerSanityCheck(self.session.nav.RecordTimer.timer_list, cur, True)
			if not timersanitycheck.check():
				currentSimulTimerList = timersanitycheck.getSimulTimerList()
				conflict_detection = cur
				menu.append((_("Current timer"), "current"))
		for timer in self.session.nav.RecordTimer.timer_list:
			if not timer.conflict_detection and (conflict_detection is None or conflict_detection != timer):
				timersanitycheck = PrimeTimeTimerSanityCheck(self.session.nav.RecordTimer.timer_list, timer, True)
				if not timersanitycheck.check():
					simulTimerList = timersanitycheck.getSimulTimerList()
					if simulTimerList != currentSimulTimerList:
						menu.append((_("Any timers"), "any"))
						break
		def conflictAction(choice):
			if choice is not None:
				if choice[1] == "current":
					self.session.openWithCallback(self.updateList, PrimeTimeTimerSanityConflict, currentSimulTimerList, True)
				if choice[1] == "any":
					self.session.openWithCallback(self.updateList, PrimeTimeTimerSanityConflict, simulTimerList, True)
		if menu:
			self.session.openWithCallback(conflictAction, ChoiceBox, title= _("Checking with conflict detection enabled for"), list=menu)

def updateList(self, answer=None):
	self.fillTimerList()
	self.updateState()

class PrimeTimeTimerSanityConflict(Screen):
	def __init__(self, session, timer, simulate=False):
		Screen.__init__(self, session)
		self.skinName = "TimerEditList"
		self.timer = timer
		self.simulate = simulate

		self.list = []
		count = 0
		for x in timer:
			self.list.append((timer[count], False))
			count += 1
		title_text = (": total conflicts %d") % count
		if simulate:
			title_text = _(": only notification")
		if count == 1:
			title_text = _("Channel not in services list") + title_text
		else:
			title_text = _("Timer sanity error") + title_text
		self.setTitle(title_text)

		self["timerlist"] = TimerList(self.list)

		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(" ")
		self["key_yellow"] = Button(" ")
		self["key_blue"] = Button(" ")

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ShortcutActions", "TimerEditActions", "MenuActions"],
			{
				"cancel": self.leave_cancel,
				"red": self.leave_cancel,
				"green": self.editTimer,
				"ok": self.editTimer,
				"yellow": self.toggleTimer,
				"blue": self.ignoreConflict,
				"up": self.up,
				"down": self.down,
				"log": self.showLog,
				"menu": self.openExtendedSetup
			}, -1)
		self.onShown.append(self.updateState)

	def getTimerList(self, timer):
		return [(timer, False)]

	def editTimer(self):
		self.session.openWithCallback(self.editTimerCallBack, TimerEntry, self["timerlist"].getCurrent())

	def showLog(self):
		selected_timer = self["timerlist"].getCurrent()
		if selected_timer:
			self.session.openWithCallback(self.editTimerCallBack, TimerLog, selected_timer)

	def editTimerCallBack(self, answer=None):
		if answer and len(answer) > 1 and answer[0] is True:
			self.session.nav.RecordTimer.timeChanged(answer[1])
			self.leave_ok()

	def toggleTimer(self):
		selected_timer = self["timerlist"].getCurrent()
		if selected_timer and self["key_yellow"].getText() != " ":
			selected_timer.disabled = not selected_timer.disabled
			self.session.nav.RecordTimer.timeChanged(selected_timer)
			self.leave_ok()

	def ignoreConflict(self):
		selected_timer = self["timerlist"].getCurrent()
		if selected_timer and selected_timer.conflict_detection:
			if config.usage.show_timer_conflict_warning.value:
				list = [(_("yes"), True), (_("no"), False), (_("yes") + " " + _("and never ask this again"), "never")]
				self.session.openWithCallback(self.ignoreConflictConfirm, MessageBox, _("Warning!\nThis is an option for advanced users.\nReally disable timer conflict detection?"), list=list)
			else:
				self.ignoreConflictConfirm(True)

	def ignoreConflictConfirm(self, answer):
		selected_timer = self["timerlist"].getCurrent()
		if answer and selected_timer and selected_timer.conflict_detection:
			if answer == "never":
				config.usage.show_timer_conflict_warning.value = False
				config.usage.show_timer_conflict_warning.save()
			selected_timer.conflict_detection = False
			selected_timer.disabled = False
			self.session.nav.RecordTimer.timeChanged(selected_timer)
			self.leave_ok()

	def leave_ok(self):
		if self.simulate or self.isResolvedConflict():
			self.close((True, self.timer[0]))
		else:
			self.timer[0].disabled = True
			self.session.nav.RecordTimer.timeChanged(self.timer[0])
			self.updateState()
			self.session.open(MessageBox, _("Conflict not resolved!"), MessageBox.TYPE_ERROR, timeout=3)

	def leave_cancel(self):
		isTimerSave = self.timer[0] in self.session.nav.RecordTimer.timer_list
		if self.simulate or self.isResolvedConflict() or not isTimerSave:
			self.close((False, self.timer[0]))
		else:
			timer_text = ""
			if not self.timer[0].isRunning():
				self.timer[0].disabled = True
				self.session.nav.RecordTimer.timeChanged(self.timer[0])
				timer_text = _("\nTimer '%s' disabled!") % self.timer[0].name
			self.session.openWithCallback(self.canceling, MessageBox, _("Conflict not resolved!") + timer_text, MessageBox.TYPE_INFO, timeout=3)

	def canceling(self, answer=None):
		self.close((False, self.timer[0]))

	def isResolvedConflict(self):
		timersanitycheck = TimerSanityCheck(self.session.nav.RecordTimer.timer_list, self.timer[0])
		success = False
		if not timersanitycheck.check():
			simulTimerList = timersanitycheck.getSimulTimerList()
			if simulTimerList is not None:
				for x in simulTimerList:
					if x.setAutoincreaseEnd(self.timer[0]):
						self.session.nav.RecordTimer.timeChanged(x)
				if timersanitycheck.check():
					success = True
		else:
			success = True
		return success

	def openExtendedSetup(self):
		menu = []
		if not config.usage.show_timer_conflict_warning.value:
			menu.append((_("Show warning before set 'Ignore conflict'"), "blue_key_warning"))
		def showAction(choice):
			if choice is not None:
				if choice[1] == "blue_key_warning":
					config.usage.show_timer_conflict_warning.value = True
					config.usage.show_timer_conflict_warning.save()
		if menu:
			self.session.openWithCallback(showAction, ChoiceBox, title= _("Select action"), list=menu)

	def up(self):
		self["timerlist"].instance.moveSelection(self["timerlist"].instance.moveUp)
		self.updateState()

	def down(self):
		self["timerlist"].instance.moveSelection(self["timerlist"].instance.moveDown)
		self.updateState()

	def updateState(self):
		selected_timer = self["timerlist"].getCurrent()
		if selected_timer:
			self["key_green"].setText(_("Edit"))
			if selected_timer.disabled:
				self["key_yellow"].setText(_("Enable"))
			elif selected_timer.isRunning() and not selected_timer.repeated:
				self["key_yellow"].setText(" ")
			elif not selected_timer.isRunning() or selected_timer.repeated:
				self["key_yellow"].setText(_("Disable"))
			if selected_timer.conflict_detection:
				self["key_blue"].setText(_("Ignore conflict"))
			else:
				self["key_blue"].setText(" ")
		else:
			self["key_green"].setText(" ")
			self["key_yellow"].setText(" ")
			self["key_blue"].setText(" ")
