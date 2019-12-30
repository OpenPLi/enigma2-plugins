from . import _
from Components.config import config, ConfigSubsection, getConfigListEntry, ConfigSelection, ConfigClock, ConfigYesNo
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.ActionMap import ActionMap
from Components.Label import Label
from Screens.Screen import Screen
from Tools.Directories import fileExists
from enigma import getDesktop

size_width = getDesktop(0).size().width()

plugin_version = "1.4"

config.plugins.PrimeTimeManager = ConfigSubsection()
config.plugins.PrimeTimeManager.Time1 = ConfigClock(default = 69300) # 20:15
config.plugins.PrimeTimeManager.Time2 = ConfigClock(default = 75600) # 22:00
config.plugins.PrimeTimeManager.DurationOrEndTime = ConfigSelection(default = "duration", choices = [
				("duration", _("Duration")),
				("endtime", _("End time"))
				])
config.plugins.PrimeTimeManager.RemoveFavorite = ConfigYesNo()
config.plugins.PrimeTimeManager.ViewLive = ConfigYesNo(default = False)
config.plugins.PrimeTimeManager.ViewLiveType = ConfigSelection(default = "zap", choices = [
				("zap", _("Zap")),
				("zaprec", _("Zap + Record"))
				])
config.plugins.PrimeTimeManager.CheckConflictOnExit = ConfigYesNo(default = False)
config.plugins.PrimeTimeManager.CheckConflictOnAccept = ConfigYesNo(default = True)
config.plugins.PrimeTimeManager.TimerEditKeyMenu = ConfigYesNo(default = True)
config.plugins.PrimeTimeManager.ExtMenu = ConfigYesNo(default = False)
config.plugins.PrimeTimeManager.UseAutotimer = ConfigYesNo(default = True)
config.plugins.PrimeTimeManager.RedButton = ConfigSelection(default = "epg", choices = [
				("epg", _("open Multi EPG")),
				("exit", _("exit plugin"))
				])
config.plugins.PrimeTimeManager.CloseMultiEPG = ConfigYesNo(default = False)

class PrimeTimeSettings(ConfigListScreen, Screen):
	if size_width >=1920:
		skin = """<screen title="Prime Time Settings" position="center,center" size="560,390">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<widget render="Label" source="key_red" position="0,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget render="Label" source="key_green" position="140,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget render="Label" source="key_yellow" position="280,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="yellow" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget render="Label" source="key_blue" position="420,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="blue" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="config" position="0,50" size="560,330" scrollbarMode="showOnDemand" />
		</screen>"""
	else:
		skin = """<screen title="Prime Time Settings" position="center,center" size="560,390">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<widget render="Label" source="key_red" position="0,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget render="Label" source="key_green" position="140,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget render="Label" source="key_yellow" position="280,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="yellow" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget render="Label" source="key_blue" position="420,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="blue" font="Regular;19" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="config" position="0,50" size="560,330" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)

		self["key_red"] = StaticText(_("Cansel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")

		list = []
		list.append(getConfigListEntry(_("Primary Prime Time:"), config.plugins.PrimeTimeManager.Time1))
		list.append(getConfigListEntry(_("Secondary Prime Time:"), config.plugins.PrimeTimeManager.Time2))
		list.append(getConfigListEntry(_("Show duration or end time:"), config.plugins.PrimeTimeManager.DurationOrEndTime))
		list.append(getConfigListEntry(_("Remove favorite on timer deletion:"), config.plugins.PrimeTimeManager.RemoveFavorite))
		list.append(getConfigListEntry(_("\"View live\" type:"), config.plugins.PrimeTimeManager.ViewLiveType))
		list.append(getConfigListEntry(_("\"View live\" event only in Prime Time:"), config.plugins.PrimeTimeManager.ViewLive))
		list.append(getConfigListEntry(_("Check conflicts timers after \"Accept\":"), config.plugins.PrimeTimeManager.CheckConflictOnAccept))
		list.append(getConfigListEntry(_("Check conflicts timers after exit:"), config.plugins.PrimeTimeManager.CheckConflictOnExit))
		list.append(getConfigListEntry(_("Prime Time Manager in E-menu:"), config.plugins.PrimeTimeManager.ExtMenu))
		list.append(getConfigListEntry(_("Red Button function:"), config.plugins.PrimeTimeManager.RedButton))
		list.append(getConfigListEntry(_("Exit from Multi EPG on selected service:"), config.plugins.PrimeTimeManager.CloseMultiEPG))
		list.append(getConfigListEntry(_("'Timer Edit' key menu - show conflict timer:"), config.plugins.PrimeTimeManager.TimerEditKeyMenu))
		if fileExists("/usr/lib/enigma2/python/Plugins/Extensions/AutoTimer/plugin.py"):
			list.append(getConfigListEntry(_("Use AutoTimer plugin instead remove favorites:"), config.plugins.PrimeTimeManager.UseAutotimer))

		ConfigListScreen.__init__(self, list)

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"red":		self.exit,
			"green":	self.save,
			"cancel":	self.exit
		}, -1)

		self.setTitle(_("Prime Time Settings") + ": " + plugin_version)

	def save(self):
		for x in self["config"].list:
			x[1].save()
		self.close()

	def exit(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()
