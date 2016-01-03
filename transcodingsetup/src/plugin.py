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

config.plugins.transcodingsetup = ConfigSubsection()
config.plugins.transcodingsetup.port = ConfigInteger(default = None, limits = (1024, 65535))
config.plugins.transcodingsetup.bitrate = ConfigInteger(default = None, limits = (50000, 2000000))
config.plugins.transcodingsetup.resolution = ConfigSelection(default = "480p", choices = [ ("720x480", "480p"), ("720x576", "576p"), ("1280x720", "720p") ])

config.plugins.transcodingsetup.framerate = ConfigInteger(default = None)
config.plugins.transcodingsetup.aspectratio = ConfigInteger(default = None)
config.plugins.transcodingsetup.interlaced = ConfigInteger(default = None)

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
		bitrate_choices = [( 50, "50 kbps" ), ( 100, "100 kbps" ), ( 200, "200 kbps" ), ( 500, "500 kbps" ), ( 1000, "1 Mbps" ), ( 2000, "2 Mbps" )]
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

		vumodel = None
		boxtype = None
		transcoding = None
		port = None

		try:
			f = open("/proc/stb/info/vumodel", "r")
			vumodel = f.readlines()
			vumodel = [x.translate(None, ' \n\r') for x in vumodel]
			vumodel = vumodel[0]
			f.close()
		except:
			pass

		try:
			f = open("/proc/stb/info/boxtype", "r")
			boxtype = f.readlines()
			boxtype = [x.translate(None, ' \n\r') for x in boxtype]
			boxtype = boxtype[0]
			f.close()
		except:
			pass

		if vumodel == "solo2" or vumodel == "duo2" or vumodel == "solose" or vumodel == "solo4k":
			transcoding = "vuplus"
		else:
			if boxtype == "et10000" or boxtype == "hd2400":
				transcoding = "enigma"

		if transcoding == "vuplus":
			port = 8002
		elif transcoding == "enigma":
			port = 8001
		elif transcoding is None:
			self.statusTimer.callback.append(self.setErrorMessage)
			self.statusTimer.start(500, True)
			return

		config_list.append(getConfigListEntry(_("Bitrate"), self.bitrate))
		config_list.append(getConfigListEntry(_("Video size"), self.size))

		self["config"].list = config_list

		if config.plugins.transcodingsetup.framerate.value is None:
			config.plugins.transcodingsetup.framerate.value = 30000

		if config.plugins.transcodingsetup.aspectratio.value is None:
			config.plugins.transcodingsetup.aspectratio.value = 2

		if config.plugins.transcodingsetup.interlaced.value is None:
			config.plugins.transcodingsetup.interlaced.value = 0

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
		config.plugins.transcodingsetup.bitrate.value = self.bitrate.value * 1000
		config.plugins.transcodingsetup.bitrate.save()
		config.plugins.transcodingsetup.resolution.value = resolution
		config.plugins.transcodingsetup.resolution.save()
		config.plugins.transcodingsetup.framerate.save()
		config.plugins.transcodingsetup.aspectratio.save()
		config.plugins.transcodingsetup.interlaced.save()
		configfile.save()

		self.close()

	def KeyNone(self):
		None

	def callbackNone(self, *retval):
		None

def startSetup(menuid):
	if menuid != "system":
		return []
	return [(_("Transcoding Setup"), main, "transcoding_setup", 60)]

def main(session, **kwargs):
	session.open(TranscodingSetup)

def Plugins(**kwargs):
	return [PluginDescriptor(name = "Transcoding Setup", description = _("Set up default transcoding parameters"), where = PluginDescriptor.WHERE_MENU, fnc=startSetup)]
