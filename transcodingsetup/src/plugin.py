# for localized messages
from . import _
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.Label import Label
from Components.ActionMap import ActionMap
from Screens.MessageBox import MessageBox
from enigma import eTimer
from Components.config import config, ConfigSubsection, getConfigListEntry, ConfigInteger, ConfigSelection, configfile 
from Tools.Directories import fileExists, pathExists

import os

config.plugins.transcodingsetup = ConfigSubsection()
config.plugins.transcodingsetup.port = ConfigInteger(default = None, limits = (1024, 65535))
if fileExists("/proc/stb/encoder/0/vcodec"):
	config.plugins.transcodingsetup.bitrate = ConfigSelection([("100000", _("100 kbps")), ("300000", _("300 kbps")), ("500000", _("500 kbps")), ("800000", _("800 kbps")), ("1000000", _("1.0 Mbps")),  ("1200000", _("1.2 Mbps")), ("1500000", _("1.5 Mbps")), ("2000000", _("2.0 Mbps")), ("2500000", _("2.5 Mbps")), ("3000000", _("3.0 Mbps")), ("3500000", _("3.5 Mbps")), ("4000000", _("4.0 Mbps")), ("5000000", _("5.0 Mbps"))], default="1500000")
	config.plugins.transcodingsetup.resolution = ConfigSelection([("720x480", _("480p")), ("720x576", _("576p")), ("1280x720", _("720p"))], default="720x576")
	config.plugins.transcodingsetup.vcodec = ConfigSelection([("h264", _("H.264")), ("h265", _("H.265"))], default="h265")
	config.plugins.transcodingsetup.framerate = ConfigSelection([("23976", _("23.976 fps")), ("24000", _("24 fps")), ("25000", _("25 fps")), ("30000", _("30 fps"))], default="25000")
	config.plugins.transcodingsetup.aspectratio = ConfigInteger(default = 2)
	config.plugins.transcodingsetup.interlaced = ConfigInteger(default = 0)
else:
	config.plugins.transcodingsetup.bitrate = ConfigInteger(default = None, limits = (50000, 4000000))
	config.plugins.transcodingsetup.resolution = ConfigSelection(default = "480p", choices = [ ("720x480", "480p"), ("720x576", "576p"), ("1280x720", "720p") ])
	config.plugins.transcodingsetup.framerate = ConfigSelection(default = 30000)
	config.plugins.transcodingsetup.aspectratio = ConfigInteger(default = 2)
	config.plugins.transcodingsetup.interlaced = ConfigInteger(default = 0)

TRANSCODING_CONFIG = "/etc/enigma2/streamproxy.conf"

class TranscodingSetup(ConfigListScreen, Screen):
	skin = 	"""
		<screen position="center,center" size="500,114" title="Transcoding Setup">
			<widget name="content" position="0,0" size="500,22" font="Regular;20" />

			<widget name="config" position="4,26" font="Regular;20" size="492,60" />

			<ePixmap pixmap="skin_default/buttons/red.png" position="0,76" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="150,76" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="0,76" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1"/>
			<widget source="key_green" render="Label" position="150,76" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1"/>
		</screen>
		"""

	def __init__(self, session):
		bitrate_choices = [( 50000, "50 kbps" ), ( 100000, "100 kbps" ), ( 200000, "200 kbps" ), ( 500000, "500 kbps" ), ( 1000000, "1 Mbps" ), ( 1500000, "1.5 Mbps" ), ( 2000000, "2 Mbps" ), ( 2500000, "2.5 Mbps" ), ( 3000000, "3 Mbps" ), ( 3500000, "3.5 Mbps" ), ( 4000000, "4 Mbps" )]
		size_choices = [ "480p", "576p", "720p" ]

		current_bitrate_value = ""
		current_size = ""

		Screen.__init__(self, session)
		self.setTitle(_("Transcoding Setup"))

		config_list = []
		ConfigListScreen.__init__(self, config_list)

		self.bitrate = ConfigSelection(choices = bitrate_choices)
		self.size = ConfigSelection(choices = size_choices)

		self.statusTimer = eTimer()
		self.warningTimer = eTimer()

		port = None

		if os.path.exists("/dev/bcm_enc0"):
			port = 8002
		else:
			if os.path.exists("/proc/stb/encoder/0"):
				port = 8001
			else:
				self.statusTimer.callback.append(self.setErrorMessage)
				self.statusTimer.start(500, True)
				return

		if fileExists("/proc/stb/encoder/0/vcodec"):
			config_list.append(getConfigListEntry(_("Bitrate"), config.plugins.transcodingsetup.bitrate))
			config_list.append(getConfigListEntry(_("Video size"), config.plugins.transcodingsetup.resolution))
			config_list.append(getConfigListEntry(_("Video codec"), config.plugins.transcodingsetup.vcodec))
			config_list.append(getConfigListEntry(_("Frame rate"), config.plugins.transcodingsetup.framerate))
		else:
			config_list.append(getConfigListEntry(_("Bitrate"), self.bitrate))
			config_list.append(getConfigListEntry(_("Video size"), self.size))

		self["config"].list = config_list

		if config.plugins.transcodingsetup.port.value is None:
			config.plugins.transcodingsetup.port.value = port

		rawcontent = []

		try:
			f = open(TRANSCODING_CONFIG, "r")
			rawcontent = f.readlines()
			rawcontent = [x.translate(None, ' \n\r') for x in rawcontent]
			f.close()
		except:
			self.warningTimer.callback.append(self.setWarningMessage)
			self.warningTimer.start(500, True)

		self.content = []

		for line in rawcontent:
			if not line.startswith('#') and not line.startswith(';'):
				tokens = line.split('=')

				if(tokens[0] == "bitrate"):
					for tuple in bitrate_choices:
						if int(tokens[1]) <= int(tuple[0]):
							self.bitrate.setValue(tuple[0])
							break

				if(tokens[0] == "size"):
					self.size.setValue(tokens[1])

				self.content += [ tokens ]

		self["actions"] = ActionMap(["OkCancelActions", "ShortcutActions", "ColorActions"],
		{
			"red": self.keyCancel,
			"green": self.keyGo,
			"ok": self.keyGo,
			"cancel": self.keyCancel,
		}, -2)

		self["key_red"] = StaticText(_("Quit"))
		self["key_green"] = StaticText(_("Set"))

		self["content"] = Label(_("Default values for trancoding"))

	def setWarningMessage(self):
		self.session.open(MessageBox, _("Not found file '/etc/enigma2/streamproxy.conf' !"), MessageBox.TYPE_WARNING)

	def setErrorMessage(self):
		self.session.openWithCallback(self.closeCallback, MessageBox, _("It seems your receiver is not supported!"), MessageBox.TYPE_ERROR)

	def closeCallback(self, answer):
		self.close()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)

	def keyRight(self):
		ConfigListScreen.keyRight(self)

	def keyCancel(self):
		self.close()

	def keyGo(self):
		for token in self.content:
			if(token[0] == "bitrate"):
				token[1] = self.bitrate.value

			if(token[0] == "size"):
				token[1] = self.size.value

		try:
			f = open(TRANSCODING_CONFIG, "w")
			for token in self.content:
				f.write("%s = %s\n" % (token[0], token[1]))
			f.close()
		except:
			pass

		if self.size.value == "480p":
			resx = 720
			resy = 480
		else:
			if self.size.value == "576p":
				resx = 720
				resy = 576
			else:
				if self.size.value == "720p":
					resx = 1280
					resy = 720

		resolution = "%dx%d" % (resx, resy)

		config.plugins.transcodingsetup.port.save()
		config.plugins.transcodingsetup.bitrate.save()
		config.plugins.transcodingsetup.resolution.value = resolution
		config.plugins.transcodingsetup.resolution.save()
		config.plugins.transcodingsetup.framerate.save()
		config.plugins.transcodingsetup.aspectratio.save()
		config.plugins.transcodingsetup.interlaced.save()
		if fileExists("/proc/stb/encoder/0/vcodec"):
			config.plugins.transcodingsetup.vcodec.save()

		configfile.save()

		self.close()

	def KeyNone(self):
		None

	def callbackNone(self, *retval):
		None

def startSetup(menuid):
	if menuid != "expert":
		return []
	return [(_("Transcoding Setup"), main, "transcoding_setup", 60)]

def main(session, **kwargs):
	session.open(TranscodingSetup)

def Plugins(**kwargs):
	return [PluginDescriptor(name = "Transcoding Setup", description = _("Set up default transcoding parameters"), where = PluginDescriptor.WHERE_MENU, fnc=startSetup)]
