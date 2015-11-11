from Plugins.Plugin import PluginDescriptor

import Screens.Screen
import Components.ConfigList
import Components.Sources.StaticText
import Components.ActionMap
import Components.config

Components.config.config.plugins.transcodingsetup = Components.config.ConfigSubsection()
Components.config.config.plugins.transcodingsetup.port = Components.config.ConfigInteger(default = None, limits = (1024, 65535))
Components.config.config.plugins.transcodingsetup.bitrate = Components.config.ConfigInteger(default = None, limits = (50000, 2000000))
Components.config.config.plugins.transcodingsetup.resolution = Components.config.ConfigSelection(default = "480p", choices = [ ("720x480", "480p"), ("720x576", "576p"), ("1280x720", "720p") ])

Components.config.config.plugins.transcodingsetup.framerate = Components.config.ConfigInteger(default = None)
Components.config.config.plugins.transcodingsetup.aspectratio = Components.config.ConfigInteger(default = None)
Components.config.config.plugins.transcodingsetup.interlaced = Components.config.ConfigInteger(default = None)

class TranscodingSetup(Components.ConfigList.ConfigListScreen, Screens.Screen.Screen):
	skin = 	"""
		<screen position="center,center" size="500,114" title="TranscodingSetup">
			<eLabel position="0,0" size="500,22" font="Regular;20" text="Default values for trancoding" />

			<widget name="config" position="4,26" font="Regular;20" size="492,60" />

			<ePixmap pixmap="skin_default/buttons/red.png" position="0,76" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="150,76" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="0,76" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1"/>
			<widget source="key_green" render="Label" position="150,76" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1"/>

		</screen>
		"""

	def KeyNone(self):
		None

	def callbackNone(self, *retval):
		None

	def __init__(self, session):
		bitrate_choices = [( 50, "50 kbps" ), ( 100, "100 kbps" ), ( 200, "200 kbps" ), ( 500, "500 kbps" ), ( 1000, "1 Mbps" ), ( 2000, "2 Mbps" )]
		size_choices = [ "480p", "576p", "720p" ]

		current_bitrate_value = ""
		current_size = ""

		Screens.Screen.Screen.__init__(self, session)

		config_list = []
		Components.ConfigList.ConfigListScreen.__init__(self, config_list)

		self.bitrate = Components.config.ConfigSelection(choices = bitrate_choices)
		self.size = Components.config.ConfigSelection(choices = size_choices)

		config_list.append(Components.config.getConfigListEntry(_("Bitrate"), self.bitrate));
		config_list.append(Components.config.getConfigListEntry(_("Video size"), self.size));

		self["config"].list = config_list

		vumodel = None;
		boxtype = None;
		transcoding = None;
		port = None;

		try:
			with open("/proc/stb/info/vumodel", "r") as f:
				vumodel = f.readlines();
				vumodel = [x.translate(None, ' \n\r') for x in vumodel]
				vumodel = vumodel[0]
				f.close
		except:
			pass

		try:
			with open("/proc/stb/info/boxtype", "r") as f:
				boxtype = f.readlines();
				boxtype = [x.translate(None, ' \n\r') for x in boxtype]
				boxtype = boxtype[0]
				f.close
		except:
			pass

		if vumodel == "solo2" or vumodel == "duo2" or vumodel == "solose":
			transcoding = "vuplus"
		else:
			if boxtype == "et10000" or boxtype == "hd2400":
				transcoding = "enigma"

		if transcoding == "vuplus":
			port = 8002
		else:
			if transcoding == "enigma":
				port = 8001

		if Components.config.config.plugins.transcodingsetup.framerate.value is None:
			Components.config.config.plugins.transcodingsetup.framerate.value = 30000

		if Components.config.config.plugins.transcodingsetup.aspectratio.value is None:
			Components.config.config.plugins.transcodingsetup.aspectratio.value = 2

		if Components.config.config.plugins.transcodingsetup.interlaced.value is None:
			Components.config.config.plugins.transcodingsetup.interlaced.value = 0

		if Components.config.config.plugins.transcodingsetup.port.value is None:
			Components.config.config.plugins.transcodingsetup.port.value = port

		rawcontent = []

		with open("/etc/enigma2/streamproxy.conf", "r") as f:
			rawcontent = f.readlines()
			rawcontent = [x.translate(None, ' \n\r') for x in rawcontent]
			f.close()

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

		self["actions"] = Components.ActionMap.ActionMap(["OkCancelActions", "ShortcutActions", "ColorActions" ],
		{
			"red": self.keyCancel,
			"green": self.keyGo,
			"ok": self.keyGo,
			"cancel": self.keyCancel,
		}, -2)

		self["key_red"] = Components.Sources.StaticText.StaticText(_("Quit"))
		self["key_green"] = Components.Sources.StaticText.StaticText(_("Set"))

	def keyLeft(self):
		Components.ConfigList.ConfigListScreen.keyLeft(self)

	def keyRight(self):
		Components.ConfigList.ConfigListScreen.keyRight(self)

	def keyCancel(self):
		self.close()

	def keyGo(self):
		for token in self.content:
			if(token[0] == "bitrate"):
				token[1] = self.bitrate.value

			if(token[0] == "size"):
				token[1] = self.size.value

		with open("/etc/enigma2/streamproxy.conf", "w") as f:
			for token in self.content:
				f.write("%s = %s\n" % (token[0], token[1]))
			f.close()

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

		Components.config.config.plugins.transcodingsetup.port.save()
		Components.config.config.plugins.transcodingsetup.bitrate.value = self.bitrate.value * 1000
		Components.config.config.plugins.transcodingsetup.bitrate.save()
		Components.config.config.plugins.transcodingsetup.resolution.value = resolution
		Components.config.config.plugins.transcodingsetup.resolution.save()
		Components.config.config.plugins.transcodingsetup.framerate.save()
		Components.config.config.plugins.transcodingsetup.aspectratio.save()
		Components.config.config.plugins.transcodingsetup.interlaced.save()
		Components.config.configfile.save()

		self.close()

def main(session, **kwargs):
	session.open(TranscodingSetup)

def Plugins(**kwargs):
	return [PluginDescriptor(name = _("TranscodingSetup"), description = _("Set up default transcoding parameters"), where = PluginDescriptor.WHERE_PLUGINMENU, fnc = main)]
