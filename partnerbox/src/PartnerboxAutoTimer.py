#
#  Partnerbox E2
#
#  $Id$
#
#  Coded by Dr.Best (c) 2009
#  Support: board.dreambox.tools
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

from . import _
from Tools.BoundFunction import boundFunction
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.Sources.StaticText import StaticText
from Components.config import config
from PartnerboxFunctions import sendPartnerBoxWebCommand
from PartnerboxSetup import PartnerboxEntriesListConfigScreen
from Plugins.Extensions.AutoTimer.AutoTimerEditor import AutoTimerEditor, AutoTimerEPGSelection, addAutotimerFromEvent
from Plugins.Extensions.AutoTimer.AutoTimerOverview import AutoTimerOverview
from Plugins.Extensions.AutoTimer.AutoTimerWizard import AutoTimerWizard
from xml.etree.cElementTree import fromstring as cet_fromstring
from ServiceReference import ServiceReference
from enigma import eServiceReference


class PartnerboxAutoTimer(object):
	instance = None

	def __init__(self, session):
		self.session = session
		assert not PartnerboxAutoTimer.instance, "only one PartnerboxAutoTimer instance is allowed!"
		PartnerboxAutoTimer.instance = self # set instance

	def setPartnerboxAutoTimer(self, ret):
		if ret:
			from Plugins.Extensions.AutoTimer.plugin import autotimer
			parameter = {'xml': autotimer.writeXmlTimer([ret])}
			count = config.plugins.Partnerbox.entriescount.value
			if count == 1:
				self.partnerboxplugin(None, parameter, config.plugins.Partnerbox.Entries[0])
			else:
				self.session.openWithCallback(self.partnerboxplugin, PartnerboxEntriesListConfigScreen, parameter)

	def partnerboxplugin(self, unUsed, parameter, partnerboxentry=None):
		if partnerboxentry is None:
			return
		ip = "%d.%d.%d.%d" % tuple(partnerboxentry.ip.value)
		port = partnerboxentry.port.value
		username = "root"
		password = partnerboxentry.password.value
		sCommand = "http://%s:%d/autotimer/add_xmltimer" % (ip, port)
		sendPartnerBoxWebCommand(sCommand, None, 10, username, password, parameter=parameter).addCallback(self.downloadCallback).addErrback(self.downloadError)

	def downloadCallback(self, result=None):
		if result:
			root = cet_fromstring(result)
			statetext = root.findtext("e2statetext")
			if statetext:
				text = statetext.encode("utf-8", 'ignore')
				self.session.open(MessageBox, text, MessageBox.TYPE_INFO, timeout=10)

	def downloadError(self, error=None):
		if error is not None:
			self.session.open(MessageBox, str(error.getErrorMessage()), MessageBox.TYPE_INFO)

	def autotimerImporterCallback(self, ret):
		if ret:
			ret, session = ret
			session.openWithCallback(self.setPartnerboxAutoTimer, AutoTimerEditor, ret, False, partnerbox=True)

	def openPartnerboxAutoTimerOverview(self):
		count = config.plugins.Partnerbox.entriescount.value
		if count == 1:
			self.getPartnerboxAutoTimerList(None, None, config.plugins.Partnerbox.Entries[0])
		else:
			self.session.openWithCallback(self.getPartnerboxAutoTimerList, PartnerboxEntriesListConfigScreen, 1)

	def getPartnerboxAutoTimerList(self, unUsed1, unUsed2, partnerboxentry=None):
		if partnerboxentry is None:
			return
		ip = "%d.%d.%d.%d" % tuple(partnerboxentry.ip.value)
		port = partnerboxentry.port.value
		username = "root"
		password = partnerboxentry.password.value
		sCommand = "http://%s:%d/autotimer?webif=false" % (ip, port)
		print(sCommand)
		sendPartnerBoxWebCommand(sCommand, None, 10, username, password).addCallback(self.getPartnerboxAutoTimerListCallback, partnerboxentry).addErrback(self.downloadError)

	def getPartnerboxAutoTimerListCallback(self, result, partnerboxentry):
		if result is not None:
			from Plugins.Extensions.AutoTimer.AutoTimer import AutoTimer
			autotimer = AutoTimer()
			autotimer.readXml(xml_string=result)
			self.session.openWithCallback(boundFunction(self.callbackAutoTimerOverview, partnerboxentry, autotimer), PartnerboxAutoTimerOverview, autotimer, partnerboxentry.name.value)

	def callbackAutoTimerOverview(self, partnerboxentry, autotimer, result):
		if result is not None:
			parameter = {'xml': autotimer.writeXmlTimer(autotimer.timers)}
			ip = "%d.%d.%d.%d" % tuple(partnerboxentry.ip.value)
			port = partnerboxentry.port.value
			username = "root"
			password = partnerboxentry.password.value
			sCommand = "http://%s:%d/autotimer/upload_xmlconfiguration" % (ip, port)
			sendPartnerBoxWebCommand(sCommand, None, 10, username, password, parameter=parameter).addCallback(self.downloadCallback).addErrback(self.downloadError)


class PartnerboxAutoTimerEPGSelection(AutoTimerEPGSelection):
	def __init__(self, *args):
		AutoTimerEPGSelection.__init__(self, *args)
		self.skinName = "EPGSelection"
		self["key_red"].setText(_("add AutoTimer"))

	def zapTo(self):
		cur = self["list"].getCurrent()
		evt = cur[0]
		sref = cur[1]
		if not evt:
			return

		if sref.getPath():
			sref.ref.setPath("")
			ref_split = str(sref).split(":")
			ref_split[1] = "0"
			sref = ServiceReference(":".join(ref_split))

		addAutotimerFromEvent(self.session, evt=evt, service=sref, importer_Callback=PartnerboxAutoTimer.instance.autotimerImporterCallback)


class PartnerboxAutoTimerOverview(AutoTimerOverview):
	def __init__(self, session, autotimer, partnerbox):
		AutoTimerOverview.__init__(self, session, autotimer)
		self.partnerbox = partnerbox
		self["key_red"] = StaticText("")
		self["key_green"] = StaticText(_("Save"))

	def setCustomTitle(self):
		from Plugins.Extensions.AutoTimer.plugin import AUTOTIMER_VERSION
		self.setTitle(_("AutoTimer overview") + _(" (Partnerbox %s - Version: %s)") % (self.partnerbox, AUTOTIMER_VERSION))

	def add(self):
		newTimer = self.autotimer.defaultTimer.clone()
		newTimer.id = self.autotimer.getUniqueId()
		self.session.openWithCallback(self.addCallback, AutoTimerEditor, newTimer, False, partnerbox=True)

	def firstExec(self):
		pass

	def cancel(self):
		if self.changed:
			self.session.openWithCallback(self.cancelConfirm, ChoiceBox, title=_('Really close without saving settings?\nWhat do you want to do?'), list=[(_('Close without saving'), 'close'), (_('Close and save'), 'close_save')])
		else:
			self.close(None)

	def cancelConfirm(self, ret):
		ret = ret and ret[1]
		if ret:
			if ret == 'close':
				self.close(None)
			elif ret == 'close_save':
				self.save()

	def menu(self):
		pass

	def timer_menu(self):
		pass

	def save(self):
		self.close(self.changed and True or None)

	def ok(self):
		current = self["entries"].getCurrent()
		if current is not None:
			self.session.openWithCallback(self.editCallback, AutoTimerEditor, current, False, partnerbox=True)

	def remove(self):
		cur = self["entries"].getCurrent()
		if cur is not None:
			self.session.openWithCallback(self.removeCallback, MessageBox, _("Do you really want to delete %s?") % (cur.name))

	def removeCallback(self, ret):
		cur = self["entries"].getCurrent()
		if ret and cur:
			self.autotimer.remove(cur.id)
			self.refresh()
			self.changed = True
