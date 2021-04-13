# -*- coding: utf-8 -*-
#===============================================================================
# Remote Timer Setup by Homey
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2, or (at your option) any later
# version.
#
# Copyright (C) 2009 by nixkoenner@newnigma2.to
# http://newnigma2.to
#
# License: GPL
#
# $Id$
#===============================================================================

# for localized messages
from . import _
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Button import Button
from Components.TimerList import TimerList
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.config import getConfigListEntry, config, \
	ConfigSubsection, ConfigText, ConfigIP, ConfigYesNo, \
	ConfigPassword, ConfigNumber, KEY_LEFT, KEY_RIGHT, KEY_0
from Screens.TimerEntry import TimerEntry
from Screens.MessageBox import MessageBox
from RecordTimer import AFTEREVENT
from enigma import eEPGCache
from Tools.BoundFunction import boundFunction
from Tools.Alternatives import GetWithAlternative
from twisted.web.client import getPage
from xml.etree.cElementTree import fromstring as cElementTree_fromstring
from base64 import encodestring
import urllib

config.plugins.remoteTimer = ConfigSubsection()
config.plugins.remoteTimer.httphost = ConfigText(default="", fixed_size=False)
config.plugins.remoteTimer.httpip = ConfigIP(default=[0, 0, 0, 0])
config.plugins.remoteTimer.httpport = ConfigNumber(default=80)
config.plugins.remoteTimer.username = ConfigText(default="root", fixed_size=False)
config.plugins.remoteTimer.password = ConfigPassword(default="", fixed_size=False)
config.plugins.remoteTimer.default = ConfigYesNo(default=False)
config.plugins.remoteTimer.remotedir = ConfigYesNo(default=False)
config.plugins.remoteTimer.extmenu = ConfigYesNo(default=True)


def localGetPage(url):
	username = config.plugins.remoteTimer.username.value
	password = config.plugins.remoteTimer.password.value
	if username and password:
		basicAuth = encodestring(username + ':' + password)
		authHeader = "Basic " + basicAuth.strip()
		headers = {"Authorization": authHeader}
	else:
		headers = {}

	return getPage(url, headers=headers)


class RemoteService:
	def __init__(self, sref, sname):
		self.sref = sref
		self.sname = sname

	getServiceName = lambda self: self.sname


class RemoteTimerScreen(Screen):
	skin = """
		<screen position="center,center" size="700,500" title="Remote-Timer digest" >
			<widget name="text" position="0,10" zPosition="1" size="700,22" font="Regular;19" halign="center" valign="center" />
			<widget name="timerlist" position="5,40" size="690,400" scrollbarMode="showOnDemand" />
			<ePixmap name="red" position="0,460" zPosition="4" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
			<widget name="key_red" position="0,460" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<ePixmap name="green" position="200,460" zPosition="4" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
			<widget name="key_green" position="200,460" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<ePixmap name="yellow" position="370,460" zPosition="4" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
			<widget name="key_yellow" position="370,460" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<ePixmap name="blue" position="560,460" zPosition="4" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
			<widget name="key_blue" position="560,460" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Remote-Timer digest"))

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"green": self.settings,
			"blue": self.clean,
			"yellow": self.delete,
			"cancel": self.close,
		}, -1)

		self["timerlist"] = TimerList([])
		self["key_green"] = Label(_("Settings"))
		self["key_blue"] = Label("")
		self["key_yellow"] = Label("")
		self["key_red"] = Label(_("Cancel"))
		self["text"] = Label("")

		remoteip = "%d.%d.%d.%d" % tuple(config.plugins.remoteTimer.httpip.value)
		self.remoteurl = "%s:%s" % (remoteip, str(config.plugins.remoteTimer.httpport.value))

		self.onLayoutFinish.append(self.getInfo)

	def getInfo(self, *args):
		try:
			info = _("fetching remote data...")
			url = "http://%s/web/timerlist" % (self.remoteurl)
			localGetPage(url).addCallback(self._gotPageLoad).addErrback(self.errorLoad)
		except:
			info = _("not configured yet. please do so in the settings.")
		self["text"].setText(info)

	def _gotPageLoad(self, data):
		# XXX: this call is not optimized away so it is easier to extend this functionality to support other kinds of receiver
		self["timerlist"].l.setList(self.generateTimerE2(data))
		info = _("finish fetching remote data...")
		self["text"].setText(info)
		sel = self["timerlist"].getCurrent()
		if sel:
			self["key_blue"].setText(_("Cleanup"))
			self["key_yellow"].setText(_("Delete"))
		else:
			self["key_blue"].setText("")
			self["key_yellow"].setText("")

	def errorLoad(self, error):
		print "[RemoteTimer] errorLoad ERROR:", error.getErrorMessage()
		info = _(error.getErrorMessage())
		self["text"].setText(info)

	def clean(self):
		sel = self["timerlist"].getCurrent()
		if sel:
			try:
				url = "http://%s/web/timercleanup?cleanup=true" % (self.remoteurl)
				localGetPage(url).addCallback(self.getInfo).addErrback(self.errorLoad)
			except:
				print "[RemoteTimer] ERROR Cleanup"

	def delete(self):
		sel = self["timerlist"].getCurrent()
		if sel:
			self.session.openWithCallback(
				self.deleteTimerConfirmed,
				MessageBox,
				_("Do you really want to delete the timer \n%s ?") % sel.name
			)

	def deleteTimerConfirmed(self, val):
		if val:
			sel = self["timerlist"].getCurrent()
			if sel:
				url = "http://%s/web/timerdelete?sRef=%s&begin=%s&end=%s" % (self.remoteurl, sel.service_ref.sref, sel.begin, sel.end)
				localGetPage(url).addCallback(self.getInfo).addErrback(self.errorLoad)

	def settings(self):
		self.session.open(RemoteTimerSetup)

	def generateTimerE2(self, data):
		try:
			root = cElementTree_fromstring(data)
		except Exception, e:
			print "[RemoteTimer] error: %s", e
			self["text"].setText(_("error parsing incoming data..."))
		else:
			return [
				(
					E2Timer(
						sref=str(timer.findtext("e2servicereference", '').encode("utf-8", 'ignore')),
						sname=str(timer.findtext("e2servicename", 'n/a').encode("utf-8", 'ignore')),
						name=str(timer.findtext("e2name", '').encode("utf-8", 'ignore')),
						disabled=int(timer.findtext("e2disabled", 0)),
						timebegin=int(timer.findtext("e2timebegin", 0)),
						timeend=int(timer.findtext("e2timeend", 0)),
						duration=int(timer.findtext("e2duration", 0)),
						startprepare=int(timer.findtext("e2startprepare", 0)),
						state=int(timer.findtext("e2state", 0)),
						repeated=int(timer.findtext("e2repeated", 0)),
						justplay=int(timer.findtext("e2justplay", 0)),
						eit=int(timer.findtext("e2eit", -1)),
						afterevent=int(timer.findtext("e2afterevent", 0)),
						dirname=str(timer.findtext("e2dirname", '').encode("utf-8", 'ignore')),
						description=str(timer.findtext("e2description", '').encode("utf-8", 'ignore')),
						flags="",
						conflict_detection=0
					),
					False
				)
				for timer in root.findall("e2timer")
			]


class E2Timer:
	def __init__(self, sref="", sname="", name="", disabled=0,
			timebegin=0, timeend=0, duration=0, startprepare=0,
			state=0, repeated=0, justplay=0, eit=0, afterevent=0,
			dirname="", description="", flags="", conflict_detection=0):
		self.service_ref = RemoteService(sref, sname)
		self.name = name
		self.disabled = disabled
		self.begin = timebegin
		self.end = timeend
		self.duration = duration
		self.startprepare = startprepare
		self.state = state
		self.repeated = repeated
		self.justplay = justplay
		self.eit = eit
		self.afterevent = afterevent
		self.dirname = dirname
		self.description = description
		self.flags = flags
		self.conflict_detection = conflict_detection

	def isRunning(self):
		return self.state == 2


class RemoteTimerSetup(Screen, ConfigListScreen):
	skin = """
		<screen position="center,center" size="560,300" title="Remote-Timer settings" >
			<widget name="config" position="5,10" size="550,240" scrollbarMode="showOnDemand" />
			<ePixmap name="red" position="120,260" zPosition="4" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
			<ePixmap name="green" position="320,260" zPosition="4" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
			<widget name="key_red" position="120,260" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="key_green" position="320,260" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Remote-Timer settings"))

		self["SetupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"ok": self.keySave,
			"cancel": self.Exit,
			"green": self.keySave,
		}, -1)

		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))

		ConfigListScreen.__init__(self, [
			getConfigListEntry(_("Hostname"), config.plugins.remoteTimer.httphost),
			getConfigListEntry(_("Network IP"), config.plugins.remoteTimer.httpip),
			getConfigListEntry(_("WebIf port"), config.plugins.remoteTimer.httpport),
			getConfigListEntry(_("Username"), config.plugins.remoteTimer.username),
			getConfigListEntry(_("Password"), config.plugins.remoteTimer.password),
			getConfigListEntry(_("Use remote directory"), config.plugins.remoteTimer.remotedir),
			getConfigListEntry(_("Timer Edit - remote as default"), config.plugins.remoteTimer.default),
			getConfigListEntry(_("Show in extensions menu"), config.plugins.remoteTimer.extmenu),
		], session)

	def keySave(self):
		if self["config"].isChanged():
			for x in self["config"].list:
				x[1].save()
			timerInit()
		self.close()

	def Exit(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()


baseTimerEntrySetup = None
baseTimerEntryGo = None
timerinit = None


def timerInit():
	global baseTimerEntrySetup, baseTimerEntryGo
	if baseTimerEntrySetup is None:
		baseTimerEntrySetup = TimerEntry.createSetup
	if baseTimerEntryGo is None:
		baseTimerEntryGo = TimerEntry.keyGo
	TimerEntry.createSetup = createNewnigma2Setup
	TimerEntry.keyGo = newnigma2KeyGo


def createNewnigma2Setup(self, widget):
	baseTimerEntrySetup(self, widget)
	self.timerentry_remote = ConfigYesNo(default=config.plugins.remoteTimer.default.value)
	self.list.insert(0, getConfigListEntry(_("Remote Timer"), self.timerentry_remote))

	# force re-reading the list
	self[widget].list = self.list


def newnigma2SubserviceSelected(self, service):
	if service is not None:
		# ouch, this hurts a little
		service_ref = timerentry_service_ref
		self.timerentry_service_ref = ServiceReference(service[1])
		eit = self.timer.eit
		self.timer.eit = None

		newnigma2KeyGo(self)

		self.timerentry_service_ref = service_ref
		self.timer.eit = eit


def newnigma2KeyGo(self):
	if not self.timerentry_remote.value:
		baseTimerEntryGo(self)
	else:
		service_ref = self.timerentry_service_ref
		if self.timer.eit is not None:
			event = eEPGCache.getInstance().lookupEventId(service_ref.ref, self.timer.eit)
			if event:
				n = event.getNumOfLinkageServices()
				if n > 1:
					tlist = []
					ref = self.session.nav.getCurrentlyPlayingServiceReference()
					parent = service_ref.ref
					selection = 0
					for x in range(n):
						i = event.getLinkageService(parent, x)
						if i.toString() == ref.toString():
							selection = x
						tlist.append((i.getName(), i))
					self.session.openWithCallback(boundFunction(newnigma2SubserviceSelected, self), ChoiceBox, title=_("Please select a subservice to record..."), list=tlist, selection=selection)
					return
				elif n > 0:
					parent = service_ref.ref
					service_ref = ServiceReference(event.getLinkageService(parent, 0))

		#resolve alternative
		alternative_ref = GetWithAlternative(str(service_ref))
		service_ref = ':'.join(alternative_ref.split(':')[:11])

		# XXX: this will - without any hassle - ignore the value of repeated
		begin, end = self.getBeginEnd()

		# when a timer end is set before the start, add 1 day
		if end < begin:
			end += 86400

		rt_name = urllib.quote(self.timerentry_name.value.decode('utf8').encode('utf8', 'ignore'))
		rt_description = urllib.quote(self.timerentry_description.value.decode('utf8').encode('utf8', 'ignore'))
		rt_disabled = 0 # XXX: do we really want to hardcode this? why do we offer this option then?
		rt_repeated = 0 # XXX: same here

		if config.plugins.remoteTimer.remotedir.value:
			rt_dirname = urllib.quote(self.timerentry_dirname.value.decode('utf8').encode('utf8', 'ignore'))
		else:
			rt_dirname = "None"

		if self.timerentry_justplay.value == "zap":
			rt_justplay = 1
		else:
			rt_justplay = 0

		rt_eit = 0
		if self.timer.eit is not None:
			rt_eit = self.timer.eit

		rt_afterEvent = {
			"deepstandby": AFTEREVENT.DEEPSTANDBY,
			"standby": AFTEREVENT.STANDBY,
			"nothing": AFTEREVENT.NONE,
			"auto": AFTEREVENT.AUTO
			}.get(self.timerentry_afterevent.value, AFTEREVENT.AUTO)

		remoteip = "%d.%d.%d.%d" % tuple(config.plugins.remoteTimer.httpip.value)
		remoteurl = "http://%s:%s/web/timeradd?sRef=%s&begin=%s&end=%s&name=%s&description=%s&disabled=%s&justplay=%s&afterevent=%s&repeated=%s&dirname=%s&eit=%s" % (
			remoteip,
			config.plugins.remoteTimer.httpport.value,
			service_ref,
			begin,
			end,
			rt_name,
			rt_description,
			rt_disabled,
			rt_justplay,
			rt_afterEvent,
			rt_repeated,
			rt_dirname,
			rt_eit
		)
		print "[RemoteTimer] debug remote", remoteurl

		defer = localGetPage(remoteurl)
		defer.addCallback(boundFunction(_gotPageLoad, self.session, self))
		defer.addErrback(boundFunction(errorLoad, self.session))


def _gotPageLoadCb(timerEntry, doClose, *args):
	if doClose:
		timerEntry.keyCancel()


def _gotPageLoad(session, timerEntry, html):
	remoteresponse = parseXml(html)
	doClose = _("added") in remoteresponse
	session.openWithCallback(boundFunction(_gotPageLoadCb, timerEntry, doClose), MessageBox, _("Set timer on remote reciever via WebIf:\n%s") % _(remoteresponse), MessageBox.TYPE_INFO)


def errorLoad(session, error):
	session.open(MessageBox, _("ERROR - Set timer on remote reciever via WebIf:\n%s") % _(error), MessageBox.TYPE_INFO, timeout=10)


def parseXml(string):
	try:
		dom = cElementTree_fromstring(string)
		entry = dom.findtext('e2statetext')
		if entry:
			return entry.encode("utf-8", 'ignore')
		return _("No entry in XML from the web server")
	except:
		return _("ERROR XML parse")


def autostart(reason, **kwargs):
	global timerinit
	if timerinit is None and reason == 0 and "session" in kwargs:
		try:
			timerinit = True
			if config.plugins.remoteTimer.httpip.value:
				timerInit()
		except:
			print "[RemoteTimer] NO remoteTimer.httpip.value"


def main(session, **kwargs):
	session.open(RemoteTimerScreen)


def Plugins(**kwargs):
 	p = [
		PluginDescriptor(name=_("Remote Timer"), description=_("Create timers on remote reciever enigma2"), where=PluginDescriptor.WHERE_PLUGINMENU, icon="remotetimer.png", fnc=main),
		PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=autostart)
	]
	if config.plugins.remoteTimer.extmenu.value:
		p.append(PluginDescriptor(name=_("Remote Timer"), where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main))
	return p
