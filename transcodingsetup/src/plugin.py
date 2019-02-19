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

TRANSCODING_CONFIG = "/etc/enigma2/streamproxy.conf"

PORT_LIMITS = (1024, 65535)
BITRATE_CHOICES = [( "100000", "100 kbps" ), ( "200000", "200 kbps" ), ( "500000", "500 kbps" ), ( "1000000", "1 Mbps" ),
	( "1500000", "1.5 Mbps" ), ( "2000000", "2 Mbps" ), ( "2500000", "2.5 Mbps" ), ( "3000000", "3 Mbps" ), ( "3500000", "3.5 Mbps" ), ( "4000000", "4 Mbps" ), ( "450000", "4.5 Mbps" ),
	( "5000000", "5 Mbps" ), ( "5500000", "5.5 Mpbs" ), ( "6000000", "6 Mbps" ), ( "6500000", "6.5 Mbps" ), ( "7000000", "7 Mbps" ), ( "7500000", "7.5 Mbps" ), ( "8000000", "8 Mbps" )]
RESOLUTION_CHOICES = [ ("720x480", "480p"), ("720x576", "576p"), ("1280x720", "720p") ]
VCODEC_CHOICES = [("h264", "H.264"), ("h265", "H.265")]

config.plugins.transcodingsetup = ConfigSubsection()
config.plugins.transcodingsetup.port = ConfigInteger(default = None, limits = PORT_LIMITS )
config.plugins.transcodingsetup.port2 = ConfigInteger(default = None, limits = PORT_LIMITS )
config.plugins.transcodingsetup.bitrate = ConfigSelection(default = "1000000", choices = BITRATE_CHOICES )
config.plugins.transcodingsetup.resolution = ConfigSelection(default = "720x576", choices = RESOLUTION_CHOICES )

#config.plugins.transcodingsetup.framerate = ConfigSelection(default = "25000", choices = [("23976", "23.976 fps"), ("24000", "24 fps"), ("25000", "25 fps"), ("30000", "30 fps")])
config.plugins.transcodingsetup.aspectratio = ConfigSelection(default = 2, choices = [ ("0", "auto"), ("1", "4x3"), ("2", "16x9") ])
config.plugins.transcodingsetup.interlaced = ConfigInteger(default = 0)
if SystemInfo["HasH265Encoder"]:
	config.plugins.transcodingsetup.vcodec = ConfigSelection(default = "h265", choices = VCODEC_CHOICES )


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

		self.warningTimer = eTimer()
		self.statusTimer = eTimer()

		if os.path.exists("/dev/bcm_enc0"):
			if not os.path.exists(TRANSCODING_CONFIG):
				self.warningTimer.callback.append(self.setWarningMessage)
				self.warningTimer.start(500, True)
		else:
			if not os.path.exists("/proc/stb/encoder/0"):
				self.statusTimer.callback.append(self.setErrorMessage)
				self.statusTimer.start(500, True)
				return

		self.port = ConfigInteger(default = config.plugins.transcodingsetup.port.value, limits = PORT_LIMITS )
		self.port2 = ConfigInteger(default = config.plugins.transcodingsetup.port2.value, limits = PORT_LIMITS )
		self.bitrate = ConfigSelection(default = config.plugins.transcodingsetup.bitrate.value, choices = BITRATE_CHOICES ) 
		self.resolution = ConfigSelection(default = config.plugins.transcodingsetup.resolution.value, choices = RESOLUTION_CHOICES ) 

		config_list.append(getConfigListEntry(_("Port"), self.port))
		config_list.append(getConfigListEntry(_("Port2"), self.port2))
		config_list.append(getConfigListEntry(_("Bitrate"), self.bitrate))
		config_list.append(getConfigListEntry(_("Video size"), self.resolution))
#		config_list.append(getConfigListEntry(_("Frame rate"), config.plugins.transcodingsetup.framerate))

		if SystemInfo["HasH265Encoder"]:
			self.vcodec = ConfigSelection(default = config.plugins.transcodingsetup.vcodec.value, choices = VCODEC_CHOICES )
			config_list.append(getConfigListEntry(_("Video codec"), self.vcodec))

		self["config"].list = config_list

		self["actions"] = ActionMap(["OkCancelActions", "ShortcutActions", "ColorActions"],
		{
			"red": self.keyCancel,
			"green": self.keyGo,
			"ok": self.keyGo,
			"cancel": self.keyCancel,
		}, -2)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Ok"))

		self["content"] = Label(_("Default values for trancoding"))

	def setWarningMessage(self):
		self.session.open(MessageBox, _("Not found file '/etc/enigma2/streamproxy.conf' !"), MessageBox.TYPE_WARNING)

	def setErrorMessage(self):
		self.session.openWithCallback(self.closeCallback, MessageBox, _("It seems your receiver is not supported!"), MessageBox.TYPE_ERROR)

	def closeCallback(self, answer):
		self.close();

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)

	def keyRight(self):
		ConfigListScreen.keyRight(self)

	def keyCancel(self):
		self.close()

	def keyGo(self):
		spc_removeNotifier()										# prevent 4 times write via callbacks
		config.plugins.transcodingsetup.port.value = self.port.value
		config.plugins.transcodingsetup.port2.value = self.port2.value
		config.plugins.transcodingsetup.bitrate.value = self.bitrate.value
		config.plugins.transcodingsetup.resolution.value = self.resolution.value
		set_spc_content(True)										# now write changes
		spc_addNotifier()										# enable callback on save for plugin parameter
		self.close()

	def KeyNone(self):
		None

	def callbackNone(self, *retval):
		None
		


def setup_config():
	rawcontent = read_spc_content()
	port= None
	port2 = None
	for line in rawcontent:
		if not line.startswith('#') and not line.startswith(';'):
			tokens = line.split('=')
			if (tokens[0] == "bitrate"):
				for choice in config.plugins.transcodingsetup.bitrate.choices:
					if int(tokens[1]) * 1000 <= int(choice):
						config.plugins.transcodingsetup.bitrate.value = choice
						break

			if (tokens[0] == "size"):
				if tokens[1] == "480p":
					config.plugins.transcodingsetup.resolution.value = "720x480"
				elif tokens[1] == "576p":
					config.plugins.transcodingsetup.resolution.value = "720x576"
				elif tokens[1] == "720p":
					config.plugins.transcodingsetup.resolution.value = "1280x720"

			if (tokens[0] == "listen"):
				listen = tokens[1].split(':')
				if (listen[1] == "transcode"):
					newport = int(listen[0])
					if port == None:
						port = newport
					elif port2 == None:
						port2 = newport
	config.plugins.transcodingsetup.port.value = port
	config.plugins.transcodingsetup.port2.value = port2

	if config.plugins.transcodingsetup.port.value is None:
		port = None
		if os.path.exists("/dev/bcm_enc0"):
			port = 8002
		else:
			if os.path.exists("/proc/stb/encoder/0"):
				port = 8001
		config.plugins.transcodingsetup.port.value = port
	spc_addNotifier()

def set_spc_content(dummy):
	rawcontent = read_spc_content()
	changed = False
	port = str(config.plugins.transcodingsetup.port.value)+":transcode"
	port2 = str(config.plugins.transcodingsetup.port2.value)+":transcode"

	lines = []
	for line in rawcontent:
		if not line.startswith('#') and not line.startswith(';'):
			tokens = line.split('=')
			if (tokens[0] == "bitrate"):
				value = str(int(config.plugins.transcodingsetup.bitrate.value) / 1000)
				if value != tokens[1]:
					tokens[1] = value
					changed = True
			if (tokens[0] == "size"):
				value = tokens[1]
				if config.plugins.transcodingsetup.resolution.value == "720x480":
					value = "480p"
				elif config.plugins.transcodingsetup.resolution.value == "720x576":
					value = "576p"
				elif config.plugins.transcodingsetup.resolution.value == "1280x720":
					value = "720p"
				if value != tokens[1]:
					tokens[1] = value
					changed = True

			if (tokens[0] == "listen"):
				value = tokens[1]
				if (value.split(':')[1] == "transcode"):
					if port != None:
						value = port
						port = None
					elif port2 != None:
						value = port2
						port2 = None
					if value != tokens[1]:
						tokens[1] = value
						changed = True
			lines += [tokens[0] + " = " + tokens[1]+ "\n"]
		else:
			lines += [line]

	if changed:
		try:
			f = open(TRANSCODING_CONFIG, "w")
			f.writelines(lines)
			f.close()
		except:
			pass

	config.plugins.transcodingsetup.port.save()
	config.plugins.transcodingsetup.port2.save()
	config.plugins.transcodingsetup.bitrate.save()
	config.plugins.transcodingsetup.resolution.save()
#	config.plugins.transcodingsetup.framerate.save()
#	config.plugins.transcodingsetup.aspectratio.save()
#	config.plugins.transcodingsetup.interlaced.save()
	if SystemInfo["HasH265Encoder"]:
		config.plugins.transcodingsetup.vcodec.save()

def read_spc_content():
	rawcontent = []
	try:
		f = open(TRANSCODING_CONFIG, "r")
		rawcontent = f.readlines()
		lines = []
		for line in rawcontent:
			if not line.startswith('#') and not line.startswith(';'):
				lines += [x.translate(None, ' \n\r') for x in [line]]
			else:
				lines += [line]
		f.close()
	except:
		pass
	return lines


def spc_addNotifier():
	config.plugins.transcodingsetup.bitrate.addNotifier(set_spc_content, False)
	config.plugins.transcodingsetup.resolution.addNotifier(set_spc_content, False)
	config.plugins.transcodingsetup.port.addNotifier(set_spc_content, False)
	config.plugins.transcodingsetup.port2.addNotifier(set_spc_content, False)
	if SystemInfo["HasH265Encoder"]:
		config.plugins.transcodingsetup.vcodec.addNotifier(set_spc_content, False)

def spc_removeNotifier():
	config.plugins.transcodingsetup.bitrate.removeNotifier(set_spc_content)
	config.plugins.transcodingsetup.resolution.removeNotifier(set_spc_content)
	config.plugins.transcodingsetup.port.removeNotifier(set_spc_content)
	config.plugins.transcodingsetup.port2.removeNotifier(set_spc_content)
	if SystemInfo["HasH265Encoder"]:
		config.plugins.transcodingsetup.vcodec.removeNotifier(set_spc_content)


def startSetup(menuid):
	if menuid != "expert":
		return []
	return [(_("Transcoding Setup"), main, "transcoding_setup", 60)]

def main(session, **kwargs):
	session.open(TranscodingSetup)

def Plugins(**kwargs):
	setup_config()
	return [PluginDescriptor(name = "Transcoding Setup", description = _("Set up default transcoding parameters"), where = PluginDescriptor.WHERE_MENU, fnc=startSetup)]
