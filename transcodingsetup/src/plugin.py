# for localized messages
from . import _
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.SystemInfo import SystemInfo
from Screens.MessageBox import MessageBox
from enigma import eTimer
from Components.config import config, ConfigSubsection, getConfigListEntry, ConfigInteger, ConfigSelection, configfile 

import os

config.plugins.transcodingsetup = ConfigSubsection()

if os.path.exists("/dev/bcm_enc0"):
	config.plugins.transcodingsetup.port = ConfigSelection(default = "8002", choices=[("8002", "8002")])
else:
	config.plugins.transcodingsetup.port = ConfigSelection(default = "8001", choices=[("8001", "8001")])

config.plugins.transcodingsetup.bitrate = ConfigSelection(default = "1000000", choices = [( "50000", "50 kbps" ), ( "100000", "100 kbps" ), ( "200000", "200 kbps" ), ( "500000", "500 kbps" ), ( "1000000", "1 Mbps" ), ( "1500000", "1.5 Mbps" ), ( "2000000", "2 Mbps" ), ( "2500000", "2.5 Mbps" ), ( "3000000", "3 Mbps" ), ( "3500000", "3.5 Mbps" ), ( "4000000", "4 Mbps" )])

if SystemInfo["HasH265Encoder"]:
	config.plugins.transcodingsetup.resolution = ConfigSelection(default = "640x360", choices = [ ("426x240", "240p"), ("640x360", "360p"), ("854x480", "480p"), ("768x576", "576p"), ("1280x720", "720p"), ("1920x1080", "1080p"), ("480x360", "360p (4:3)"), ("640x480", "480p (4:3)"), ("720x576", "576p (4:3)"), ("720x480", "480pSD"), ("960x540", "540qHD"), ("1366x768", "WXGA"), ("1600x900", "1600x900 (HD+)")])
	config.plugins.transcodingsetup.framerate = ConfigSelection(default = "25000", choices = [("23976", "23.976 fps"), ("24000", "24 fps"), ("25000", "25 fps"), ("30000", "30 fps")])
	config.plugins.transcodingsetup.vcodec = ConfigSelection(default = "h265", choices = [("h264", "H.264"), ("h265", "H.265")])
	config.plugins.transcodingsetup.aspectratio = ConfigSelection(default = "0", choices = [("0", "auto")])
	config.plugins.transcodingsetup.interlaced = ConfigSelection(default = "0", choices = [("0", "auto")])
else:
	config.plugins.transcodingsetup.resolution = ConfigSelection(default = "720x576", choices = [ ("720x480", "480p"), ("720x576", "576p"), ("1280x720", "720p")])
	config.plugins.transcodingsetup.framerate = ConfigSelection(default = "25000", choices = [("23976", "23.976 fps"), ("24000", "24 fps"), ("25000", "25 fps"), ("30000", "30 fps")])
	config.plugins.transcodingsetup.aspectratio = ConfigSelection(default = "2", choices = [("0", "auto"), ("1", "4x3"), ("2", "16x9")])
	config.plugins.transcodingsetup.interlaced = ConfigSelection(default = "0", choices = [("0", "progressive"), ("1", "interlaced")])

TRANSCODING_CONFIG = "/etc/enigma2/streamproxy.conf"

class TranscodingSetup(ConfigListScreen, Screen):
	skin = 	"""
		<screen position="center,center" size="500,190" title="Transcoding Setup">
			<widget name="content" position="0,0" size="500,22" font="Regular;19" />

			<widget name="config" position="4,36" font="Regular;20" size="492,100" />

			<ePixmap pixmap="skin_default/buttons/red.png" position="0,150" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="150,150" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="0,150" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1"/>
			<widget source="key_green" render="Label" position="150,150" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1"/>
		</screen>
		"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Transcoding Setup"))

		config_list = []
		ConfigListScreen.__init__(self, config_list)

		self.statusTimer = eTimer()
		self.warningTimer = eTimer()

		needstreamproxy = False

		if os.path.exists("/dev/bcm_enc0"):
			needstreamproxy = True

		config_list.append(getConfigListEntry(_("Port"), config.plugins.transcodingsetup.port))
		config_list.append(getConfigListEntry(_("Bitrate"), config.plugins.transcodingsetup.bitrate))
		config_list.append(getConfigListEntry(_("Video size"), config.plugins.transcodingsetup.resolution))
		config_list.append(getConfigListEntry(_("Frame rate"), config.plugins.transcodingsetup.framerate))
		if SystemInfo["HasH265Encoder"]:
			config_list.append(getConfigListEntry(_("Video codec"), config.plugins.transcodingsetup.vcodec))

		self["config"].list = config_list

		rawcontent = []

		try:
			f = open(TRANSCODING_CONFIG, "r")
			rawcontent = f.readlines()
			rawcontent = [x.translate(None, ' \n\r') for x in rawcontent]
			f.close()
		except:
			if needstreamproxy:
				self.warningTimer.callback.append(self.setWarningMessage)
				self.warningTimer.start(500, True)

		self.content = []

		for line in rawcontent:
			if not line.startswith('#') and not line.startswith(';'):
				tokens = line.split('=')

				if(tokens[0] == "bitrate"):
					for choice in config.plugins.transcodingsetup.bitrate.choices:
						if int(tokens[1]) * 1000 <= int(choice):
							config.plugins.transcodingsetup.bitrate.value = choice
							break

				if(tokens[0] == "size"):
					if tokens[1] == "240p":
						config.plugins.transcodingsetup.resolution.value = "426x240"
					elif tokens[1] == "360p":
						config.plugins.transcodingsetup.resolution.value = "640x360"
					elif tokens[1] == "480p":
						config.plugins.transcodingsetup.resolution.value = "854x480"
					elif tokens[1] == "576p":
						config.plugins.transcodingsetup.resolution.value = "768x576"
					elif tokens[1] == "720p":
						config.plugins.transcodingsetup.resolution.value = "1280x720"
					elif tokens[1] == "1080p":
						config.plugins.transcodingsetup.resolution.value = "1920x1080"
					elif tokens[1] == "240p (4:3)":
						config.plugins.transcodingsetup.resolution.value = "320x240"
					elif tokens[1] == "360p (4:3)":
						config.plugins.transcodingsetup.resolution.value = "480x360"
					elif tokens[1] == "480p (4:3)":
						config.plugins.transcodingsetup.resolution.value = "640x480"
					elif tokens[1] == "576p (4:3)":
						config.plugins.transcodingsetup.resolution.value = "720x576"
					elif tokens[1] == "480pSD":
						config.plugins.transcodingsetup.resolution.value = "720x480"
					elif tokens[1] == "540qHD":
						config.plugins.transcodingsetup.resolution.value = "960x540"
					elif tokens[1] == "WXGA":
						config.plugins.transcodingsetup.resolution.value = "1366x768"
					elif tokens[1] == "1600x900 (HD+)":
						config.plugins.transcodingsetup.resolution.value = "1600x900"


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
		if self.content:
			for token in self.content:
				if(token[0] == "bitrate"):
					token[1] = str(int(config.plugins.transcodingsetup.bitrate.value) / 1000)

				if(token[0] == "size"):
					if tokens[1] == "240p":
						config.plugins.transcodingsetup.resolution.value = "426x240"
					elif tokens[1] == "360p":
						config.plugins.transcodingsetup.resolution.value = "640x360"
					elif tokens[1] == "480p":
						config.plugins.transcodingsetup.resolution.value = "854x480"
					elif tokens[1] == "576p":
						config.plugins.transcodingsetup.resolution.value = "768x576"
					elif tokens[1] == "720p":
						config.plugins.transcodingsetup.resolution.value = "1280x720"
					elif tokens[1] == "1080p":
						config.plugins.transcodingsetup.resolution.value = "1920x1080"
					elif tokens[1] == "240p (4:3)":
						config.plugins.transcodingsetup.resolution.value = "320x240"
					elif tokens[1] == "360p (4:3)":
						config.plugins.transcodingsetup.resolution.value = "480x360"
					elif tokens[1] == "480p (4:3)":
						config.plugins.transcodingsetup.resolution.value = "640x480"
					elif tokens[1] == "576p (4:3)":
						config.plugins.transcodingsetup.resolution.value = "720x576"
					elif tokens[1] == "480pSD":
						config.plugins.transcodingsetup.resolution.value = "720x480"
					elif tokens[1] == "540qHD":
						config.plugins.transcodingsetup.resolution.value = "960x540"
					elif tokens[1] == "WXGA":
						config.plugins.transcodingsetup.resolution.value = "1366x768"
					elif tokens[1] == "1600x900 (HD+)":
						config.plugins.transcodingsetup.resolution.value = "1600x900"

			try:
				f = open(TRANSCODING_CONFIG, "w")
				for token in self.content:
					f.write("%s = %s\n" % (token[0], token[1]))
				f.close()
			except:
				pass

		config.plugins.transcodingsetup.port.save()
		config.plugins.transcodingsetup.bitrate.save()
		config.plugins.transcodingsetup.resolution.save()
		config.plugins.transcodingsetup.framerate.save()
		config.plugins.transcodingsetup.aspectratio.save()
		config.plugins.transcodingsetup.interlaced.save()
		if SystemInfo["HasH265Encoder"]:
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
