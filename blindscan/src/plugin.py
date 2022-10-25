from __future__ import print_function
# for localized messages
from . import _
from enigma import getBoxType, eComponentScan, eConsoleAppContainer, eDVBFrontendParametersSatellite, eDVBResourceManager, eDVBSatelliteEquipmentControl, eTimer
from Components.About import about
from Components.ActionMap import ActionMap
from Components.config import config, ConfigBoolean, ConfigInteger, getConfigListEntry, ConfigNothing, ConfigSelection, ConfigSubsection, ConfigYesNo
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.NimManager import getConfigSatlist, nimmanager
from Components.Sources.FrontendStatus import FrontendStatus
from Components.Sources.StaticText import StaticText
from Components.TuneTest import Tuner
from Plugins.Plugin import PluginDescriptor
from Screens.ChoiceBox import ChoiceBox
from Screens.Console import Console
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.ServiceScan import ServiceScan
from Tools.BoundFunction import boundFunction
from Tools.Directories import fileExists
from .filters import TransponderFiltering # imported from Blindscan folder
#used for the XML file
from time import strftime, time
import os

BOX_MODEL = "all"
BOX_NAME = "none"
if fileExists("/proc/stb/info/vumodel") and not fileExists("/proc/stb/info/hwmodel") and not fileExists("/proc/stb/info/boxtype"):
	try:
		l = open("/proc/stb/info/vumodel")
		model = l.read().strip()
		l.close()
		BOX_NAME = str(model.lower())
		BOX_MODEL = "vuplus"
	except:
		pass
elif fileExists("/proc/stb/info/boxtype") and not fileExists("/proc/stb/info/hwmodel") and not fileExists("/proc/stb/info/gbmodel"):
	try:
		l = open("/proc/stb/info/boxtype")
		model = l.read().strip()
		l.close()
		BOX_NAME = str(model.lower())
		if BOX_NAME.startswith("et"):
			BOX_MODEL = "xtrend"
		elif BOX_NAME.startswith("os"):
			BOX_MODEL = "edision"
	except:
		pass
elif fileExists("/proc/stb/info/model") and not fileExists("/proc/stb/info/hwmodel") and not fileExists("/proc/stb/info/gbmodel"):
	try:
		l = open("/proc/stb/info/model")
		model = l.read().strip()
		l.close()
		BOX_NAME = str(model.lower())
		if BOX_NAME.startswith('dm'):
			BOX_MODEL = "dreambox"
	except:
		pass
elif fileExists("/proc/stb/info/gbmodel"):
	try:
		l = open("/proc/stb/info/gbmodel")
		model = l.read().strip()
		l.close()
		BOX_NAME = str(model.lower())
		if BOX_NAME in ("gbquad4k", "gbue4k", "gbtrio4k"):
			BOX_MODEL = "gigablue"
	except:
		pass
elif fileExists("/proc/stb/info/hwmodel"):
	try:
		l = open("/proc/stb/info/hwmodel")
		model = l.read().strip()
		l.close()
		BOX_NAME = str(model.lower())
		if BOX_NAME in ("lunix4k", "dual"):
			BOX_MODEL = "qviart"
	except:
		pass
elif fileExists("/proc/stb/info/boxtype"):
	try:
		l = open("/proc/stb/info/boxtype")
		model = l.read().strip()
		l.close()
		BOX_NAME = str(model.lower())
		if BOX_NAME == "ustym4kpro":
			BOX_MODEL = "uclan"

	except:
		pass

# root2gold based on https://github.com/DigitalDevices/dddvb/blob/master/apps/pls.c


def root2gold(root):
	if root < 0 or root > 0x3ffff:
		return 0
	g = 0
	x = 1
	while g < 0x3ffff:
		if root == x:
			return g
		x = (((x ^ (x >> 7)) & 1) << 17) | (x >> 1)
		g += 1
	return 0

# helper function for initializing mis/pls properties


def getMisPlsValue(d, idx, defaultValue):
	try:
		return int(d[idx])
	except:
		return defaultValue

#used for blindscan-s2


def getAdapterFrontend(frontend, description):
	for adapter in range(1, 5):
		try:
			product = open("/sys/class/dvb/dvb%d.frontend0/device/product" % adapter).read()
			if description in product:
				return " -a %d" % adapter
		except:
			break
	return " -f %d" % frontend

try:
	Lastrotorposition = config.misc.lastrotorposition
except:
	Lastrotorposition = None

XML_BLINDSCAN_DIR = "/tmp"
XML_FILE = None

# _supportNimType is only used by vuplus hardware
_supportNimType = {'AVL1208': '', 'AVL6222': '6222_', 'AVL6211': '6211_', 'BCM7356': 'bcm7346_', 'SI2166': 'si2166_'}

# For STBs that support PnP DVB-S/S2 tuner models, e.g. VU+Solo 4K,VU+Ultimo 4K,Gigablue UE/Quad 4K
_unsupportedNims = ("Vuplus DVB-S NIM(7376 FBC)", "Vuplus DVB-S NIM(45308X FBC)", "DVB-S2 NIM(45308 FBC)", "DVB-S2 NIM(45208 FBC)", "DVB-S2X NIM(45308X FBC)", "DVB-S2 NIM(45308 FBC)") # format = nim.description from nimmanager

# blindscan-s2 supported tuners
_blindscans2Nims = ('TBS-5925', 'DVBS2BOX', 'M88DS3103')

defaults = {"search_type": "transponders",
	"user_defined_lnb_inversion": False,
	"step_mhz_tbs5925": 10,
	"polarization": str(eDVBFrontendParametersSatellite.Polarisation_CircularRight + 1), # "vertical and horizontal"
	"start_symbol": 2,
	"stop_symbol": 45,
	"clearallservices": "no",
	"onlyFTA": False,
	"dont_scan_known_tps": False,
	"disable_sync_with_known_tps": False,
	"disable_remove_duplicate_tps": False,
	"filter_off_adjacent_satellites": "3"}

config.blindscan = ConfigSubsection()
config.blindscan.search_type = ConfigSelection(default=defaults["search_type"], choices=[
	("services", _("scan for channels")),
	("transponders", _("scan for transponders"))])
config.blindscan.user_defined_lnb_inversion = ConfigBoolean(default=defaults["user_defined_lnb_inversion"], descriptions={False: _("normal"), True: _("inverted")})
config.blindscan.step_mhz_tbs5925 = ConfigInteger(default=defaults["step_mhz_tbs5925"], limits=(1, 20))
config.blindscan.polarization = ConfigSelection(default=defaults["polarization"], choices=[
	(str(eDVBFrontendParametersSatellite.Polarisation_CircularRight + 1), _("vertical and horizontal")),
	(str(eDVBFrontendParametersSatellite.Polarisation_Vertical), _("vertical")),
	(str(eDVBFrontendParametersSatellite.Polarisation_Horizontal), _("horizontal")),
	(str(eDVBFrontendParametersSatellite.Polarisation_CircularRight + 2), _("circular right and circular left")),
	(str(eDVBFrontendParametersSatellite.Polarisation_CircularRight), _("circular right")),
	(str(eDVBFrontendParametersSatellite.Polarisation_CircularLeft), _("circular left"))])
config.blindscan.start_symbol = ConfigInteger(default=defaults["start_symbol"], limits=(1, 59))
config.blindscan.stop_symbol = ConfigInteger(default=defaults["stop_symbol"], limits=(2, 60))
config.blindscan.clearallservices = ConfigSelection(default=defaults["clearallservices"], choices=[("no", _("no")), ("yes", _("yes")), ("yes_hold_feeds", _("yes (keep feeds)"))])
config.blindscan.onlyFTA = ConfigYesNo(default=defaults["onlyFTA"])
config.blindscan.dont_scan_known_tps = ConfigYesNo(default=defaults["dont_scan_known_tps"])
config.blindscan.disable_sync_with_known_tps = ConfigYesNo(default=defaults["disable_sync_with_known_tps"])
config.blindscan.disable_remove_duplicate_tps = ConfigYesNo(default=defaults["disable_remove_duplicate_tps"])
config.blindscan.filter_off_adjacent_satellites = ConfigSelection(default=defaults["filter_off_adjacent_satellites"], choices=[
	("0", _("no")),
	("1", _("up to 1 degree")),
	("2", _("up to 2 degrees")),
	("3", _("up to 3 degrees"))])


class BlindscanState(Screen, ConfigListScreen):
	skin = """
	<screen position="center,center" size="820,578" title="Satellite Blindscan">
		<widget name="progress" position="10,5" size="800,85" font="Regular;19" />
		<eLabel	position="10,95" size="800,1" backgroundColor="grey"/>
		<widget name="config" position="10,102" size="524,425" font="Regular;18" />
		<eLabel	position="544,95" size="1,440" backgroundColor="grey"/>
		<widget name="post_action" position="554,102" size="256,480" font="Regular;18" halign="center"/>
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/Blindscan/images/red.png" position="10,573" size="100,2" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/Blindscan/images/green.png" position="120,573" size="100,2" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/Blindscan/images/yellow.png" position="240,573" size="100,2" alphatest="on" />
		<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/Blindscan/images/blue.png" position="360,573" size="100,2" alphatest="on" />
		<widget source="key_red" render="Label" position="10,530" size="100,40" font="Regular;17" halign="center"/>
		<widget source="key_green" render="Label" position="120,530" size="100,40" font="Regular;17" halign="center"/>
		<widget source="key_yellow" render="Label" position="230,530" size="100,40" font="Regular;17" halign="center"/>
		<widget source="key_blue" render="Label" position="340,530" size="100,40" font="Regular;17" halign="center"/>
	</screen>
	"""
	def __init__(self, session, progress, post_action, tp_list, finished=False):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Blind scan state"))
		self.finished = finished
		self["progress"] = Label()
		self["progress"].setText(progress)
		self["post_action"] = Label()
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")

		self.configBooleanTpList = []
		self.tp_list = []
		ConfigListScreen.__init__(self, self.tp_list, session=self.session)

		self["actions"] = ActionMap(["SetupActions"],
		{
			"cancel": self.keyCancel,
		}, -2)

		self["actions2"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"ok": self.scan,
			"save": self.scan,
			"yellow": self.selectAll,
			"blue": self.deselectAll,
		}, -2)

		if finished:
			self["post_action"].setText(_("Select transponders and press green to scan.\nPress yellow to select all transponders and blue to deselect all."))
			self["key_green"].setText(_("Scan"))
			self["key_yellow"].setText(_("Select all"))
			self["key_blue"].setText(_("Deselect all"))
			self["actions2"].setEnabled(True)
		else:
			self["post_action"].setText(post_action)
			self["actions2"].setEnabled(False)

		for t in tp_list:
			cb = ConfigBoolean(default=False, descriptions={False: _("don't scan"), True: _("scan")})
			self.configBooleanTpList.append((cb, t[1]))
			self.tp_list.append(getConfigListEntry(t[0], cb))
		self["config"].list = self.tp_list
		self["config"].l.setList(self.tp_list)

	def selectAll(self):
		if self.finished:
			for i in self.configBooleanTpList:
				i[0].setValue(True)
			self["config"].setList(self["config"].getList())

	def deselectAll(self):
		if self.finished:
			for i in self.configBooleanTpList:
				i[0].setValue(False)
			self["config"].setList(self["config"].getList())

	def scan(self):
		if self.finished:
			scan_list = []
			for i in self.configBooleanTpList:
				if i[0].getValue():
					scan_list.append(i[1])
			if len(scan_list) > 0:
				self.close(True, scan_list)
			else:
				self.close(False)

	def keyCancel(self):
		self.close(False)


class Blindscan(ConfigListScreen, Screen, TransponderFiltering):
	skin = """
		<screen position="center,center" size="640,565" title="Blind scan">
			<widget name="rotorstatus" position="5,5" size="350,25" font="Regular;20" foregroundColor="#00ffc000"/>
			<widget name="config" position="5,30" size="630,330" scrollbarMode="showOnDemand"/>
			<ePixmap pixmap="skin_default/div-h.png" position="0,365" zPosition="1" size="640,2"/>
			<widget name="description" position="5,370" size="630,125" font="Regular;19" foregroundColor="#00ffc000"/>
			<ePixmap pixmap="skin_default/div-h.png" position="0,495" zPosition="1" size="640,2"/>
			<widget name="introduction" position="0,500" size="640,20" font="Regular;18" foregroundColor="green" halign="center"/>
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/Blindscan/images/red.png" position="0,560" size="160,2" alphatest="on"/>
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/Blindscan/images/green.png" position="160,560" size="160,2" alphatest="on"/>
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/Blindscan/images/yellow.png" position="320,560" size="160,2" alphatest="on" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/Blindscan/images/blue.png" position="480,560" size="160,2" alphatest="on" />
			<widget name="key_red" position="0,530" zPosition="2" size="160,20" font="Regular;18" halign="center" valign="center" backgroundColor="background" foregroundColor="white" transparent="1"/>
			<widget name="key_green" position="160,530" zPosition="2" size="160,20" font="Regular;18" halign="center" valign="center" backgroundColor="background" foregroundColor="white" transparent="1"/>
			<widget name="key_yellow" position="320,530" zPosition="2" size="160,20" font="Regular;18" halign="center" valign="center" backgroundColor="background" foregroundColor="white" transparent="1" />
			<widget name="key_blue" position="480,530" zPosition="2" size="160,20" font="Regular;18" halign="center" valign="center" backgroundColor="background" foregroundColor="white" transparent="1" />
			<widget text="LOCK" source="Frontend" render="FixedLabel" zPosition="0" position="500,5" size="160,30" font="Regular;25" foregroundColor="green" transparent="1">
				<convert type="FrontendInfo">LOCK</convert>
				<convert type="ConditionalShowHide"/>
			</widget>
		</screen>
		"""
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setup_title = _("Blind scan for DVB-S2 tuners") + ":" + BOX_NAME + "/" + BOX_MODEL
		Screen.setTitle(self, self.setup_title)
		self.skinName = "Blindscan"
		self.session.postScanService = self.session.nav.getCurrentlyPlayingServiceOrGroup()

		self["description"] = Label("")
		self["rotorstatus"] = Label("")

		# update sat list
		self.satList = []
		for slot in nimmanager.nim_slots:
			if slot.canBeCompatible("DVB-S"):
				self.satList.append(nimmanager.getSatListForNim(slot.slot))
			else:
				self.satList.append(None)

		# make config
		self.getCurrentTuner = None
		self.createConfig()

		self.frontend = None
		self["Frontend"] = FrontendStatus(frontend_source=lambda: self.frontend, update_interval=500)

		self.list = []
		self.status = ""
		self.onChangedEntry = []
		self.blindscan_session = None
		self.tmpstr = ""
		self.Sundtek_pol = ""
		self.Sundtek_band = ""
		self.SundtekScan = False
		self.offset = 0
		self.start_time = time()
		self.orb_pos = 0
		self.is_c_band_scan = False
		self.is_Ku_band_scan = False
		self.user_defined_lnb_scan = False
		self.user_defined_lnb_lo_freq = 0
		self.suggestedPolarisation = _("vertical and horizontal")
		self.tunerEntry = None
		self.clockTimer = eTimer()
		self.statusTimer = eTimer()
		self.statusTimer.callback.append(self.setDishOrbosValue)

		# run command
		self.cmd = ""
		self.bsTimer = eTimer()
		self.bsTimer.callback.append(self.asyncBlindScan)

		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changedEntry)
		self["introduction"] = Label("")

		self["actions"] = ActionMap(["SetupActions"],
		{
			"cancel": self.keyCancel,
		}, -2)

		self["actions2"] = ActionMap(["ColorActions", "SetupActions"],
		{
			"ok": self.keyGo,
			"save": self.keyGo,
			"blue": self.resetDefaults,
		}, -2)
		self["actions2"].setEnabled(False)

		self["actions3"] = ActionMap(["ColorActions"],
		{
			"yellow": self.keyYellow,
		}, -2)
		self["actions3"].setEnabled(False)

		self["key_red"] = Label(_("Exit"))
		self["key_yellow"] = Label("")
		self["key_green"] = Label("")
		self["key_blue"] = Label(_(""))

		if self.scan_nims.value is not None and self.scan_nims.value != "": # self.scan_nims set in createConfig()
			self["key_green"].setText(_("Start scan"))
			self.createSetup(True)
		else:
			self["introduction"].setText(_("Please setup your tuner configuration."))

		self.i2c_mapping_table = {}
		self.nimSockets = self.ScanNimsocket()
		self.makeNimSocket()

		if XML_FILE is not None and os.path.exists(XML_FILE):
			self["key_yellow"].setText(_("Open xml file"))
			self["actions3"].setEnabled(True)
		else:
			self["actions3"].setEnabled(False)

		if not self.textHelp in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.textHelp)
		self.textHelp()
		self.changedEntry()

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent() and self["config"].getCurrent()[0] or ""

	def getCurrentValue(self):
		return self["config"].getCurrent() and str(self["config"].getCurrent()[1].getText()) or ""

	def textHelp(self):
		self["description"].setText(self.getCurrentDescription())
		self.setBlueText()

	def getCurrentDescription(self):
		return self["config"].getCurrent() and len(self["config"].getCurrent()) > 2 and self["config"].getCurrent()[2] or ""

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary

	def ScanNimsocket(self, filepath='/proc/bus/nim_sockets'):
		_nimSocket = {}
		try:
			fp = open(filepath)
		except:
			return _nimSocket
		sNo, sName, sI2C = -1, "", -1
		for line in fp:
			line = line.strip()
			if line.startswith('NIM Socket'):
				sNo, sName, sI2C = -1, '', -1
				try:
					sNo = line.split()[2][:-1]
				except:
					sNo = -1
			elif line.startswith('I2C_Device:'):
				try:
					sI2C = line.split()[1]
				except:
					sI2C = -1
			elif line.startswith('Name:'):
				splitLines = line.split()
				try:
					if splitLines[1].startswith('BCM'):
						sName = splitLines[1]
					else:
						sName = splitLines[3][4:-1]
				except:
					sName = ""
			if sNo >= 0 and sName != "":
				if sName.startswith('BCM'):
					sI2C = sNo
				if sI2C != -1:
					_nimSocket[sNo] = [sName, sI2C]
				else:
					_nimSocket[sNo] = [sName]
		fp.close()
		print("[Blindscan][ScanNimsocket] parsed nimsocket:", _nimSocket)
		return _nimSocket

	def makeNimSocket(self, nimname=""):
		is_exist_i2c = False
		self.i2c_mapping_table = {0: 2, 1: 3, 2: 1, 3: 0}
		if self.nimSockets is not None:
			for XX in self.nimSockets.keys():
				nimsocket = self.nimSockets[XX]
				if len(nimsocket) > 1:
					try:
						self.i2c_mapping_table[int(XX)] = int(nimsocket[1])
					except:
						continue
					is_exist_i2c = True
		print("[Blindscan][makeNimSocket] i2c_mapping_table:", self.i2c_mapping_table, ", is_exist_i2c:", is_exist_i2c)
		if is_exist_i2c:
			return

		if nimname == "AVL6222":
			if BOX_NAME == "uno":
				self.i2c_mapping_table = {0: 3, 1: 3, 2: 1, 3: 0}
			elif BOX_NAME == "duo2":
				nimdata = self.nimSockets['0']
				try:
					if nimdata[0] == "AVL6222":
						self.i2c_mapping_table = {0: 2, 1: 2, 2: 4, 3: 4}
					else:
						self.i2c_mapping_table = {0: 2, 1: 4, 2: 4, 3: 0}
				except:
					self.i2c_mapping_table = {0: 2, 1: 4, 2: 4, 3: 0}
			else:
				self.i2c_mapping_table = {0: 2, 1: 4, 2: 0, 3: 0}
		else:
			self.i2c_mapping_table = {0: 2, 1: 3, 2: 1, 3: 0}

	def getNimSocket(self, slot_number):
		bus = self.i2c_mapping_table.get(slot_number, -1)
		if bus == -1:
			I2CDevice = nimmanager.getI2CDevice(self.feid)
			if I2CDevice != None:
				bus = I2CDevice
		return bus

	def callbackNone(self, *retval):
		None

	def openFrontend(self):
		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			self.raw_channel = res_mgr.allocateRawChannel(self.feid)
			if self.raw_channel:
				self.frontend = self.raw_channel.getFrontend()
				if self.frontend:
					return True
				else:
					print("[Blindscan][openFrontend] getFrontend failed")
			else:
				print("[Blindscan][openFrontend] getRawChannel failed")
		else:
			print("[Blindscan][openFrontend] getResourceManager instance failed")
		return False

	def prepareFrontend(self):
		self.releaseFrontend()
		if not self.openFrontend():
			oldref = self.session.nav.getCurrentlyPlayingServiceReference()
			stop_current_service = True
			if oldref and self.getCurrentTuner != None:
				if self.feid != self.getCurrentTuner:
					stop_current_service = False
			if stop_current_service:
				self.session.nav.stopService()
				self.getCurrentTuner = None
			if not self.openFrontend():
				if self.session.pipshown:
					if hasattr(self.session, 'infobar'):
						try:
							slist = self.session.infobar.servicelist
							if slist and slist.dopipzap:
								slist.togglePipzap()
						except:
							pass
					self.session.pipshown = False
					if hasattr(self.session, 'pip'):
						del self.session.pip
					self.openFrontend()
		print('[Blindscan] self.frontend:', self.frontend)
		if self.frontend is None:
			text = _("Sorry, this tuner is in use.")
			if self.session.nav.getRecordings():
				text += "\n"
				text += _("Maybe the reason that recording is currently running.")
			self.session.open(MessageBox, text, MessageBox.TYPE_ERROR)
			return False
		self.tuner = Tuner(self.frontend)
		return True

	def createConfig(self):
		self.feinfo = None
		frontendData = None
		defaultSat = {
			"orbpos": 192,
			"system": eDVBFrontendParametersSatellite.System_DVB_S,
			"frequency": 11836,
			"inversion": eDVBFrontendParametersSatellite.Inversion_Unknown,
			"symbolrate": 27500,
			"polarization": eDVBFrontendParametersSatellite.Polarisation_Horizontal,
			"fec": eDVBFrontendParametersSatellite.FEC_Auto,
			"fec_s2": eDVBFrontendParametersSatellite.FEC_9_10,
			"modulation": eDVBFrontendParametersSatellite.Modulation_QPSK
		}

		self.service = self.session.nav.getCurrentService()
		if self.service is not None:
			self.feinfo = self.service.frontendInfo()
			frontendData = self.feinfo and self.feinfo.getAll(True)
		if frontendData is not None:
			ttype = frontendData.get("tuner_type", "UNKNOWN")
			if ttype == "DVB-S":
				defaultSat["system"] = frontendData.get("system", eDVBFrontendParametersSatellite.System_DVB_S)
				defaultSat["frequency"] = frontendData.get("frequency", 0) / 1000
				defaultSat["inversion"] = frontendData.get("inversion", eDVBFrontendParametersSatellite.Inversion_Unknown)
				defaultSat["symbolrate"] = frontendData.get("symbol_rate", 0) / 1000
				defaultSat["polarization"] = frontendData.get("polarization", eDVBFrontendParametersSatellite.Polarisation_Horizontal)
				if defaultSat["system"] == eDVBFrontendParametersSatellite.System_DVB_S2:
					defaultSat["fec_s2"] = frontendData.get("fec_inner", eDVBFrontendParametersSatellite.FEC_Auto)
					defaultSat["rolloff"] = frontendData.get("rolloff", eDVBFrontendParametersSatellite.RollOff_alpha_0_35)
					defaultSat["pilot"] = frontendData.get("pilot", eDVBFrontendParametersSatellite.Pilot_Unknown)
				else:
					defaultSat["fec"] = frontendData.get("fec_inner", eDVBFrontendParametersSatellite.FEC_Auto)
				defaultSat["modulation"] = frontendData.get("modulation", eDVBFrontendParametersSatellite.Modulation_QPSK)
				defaultSat["orbpos"] = frontendData.get("orbital_position", 0)
			if ttype != "UNKNOWN":
				self.getCurrentTuner = frontendData.get("tuner_number", None)
		del self.feinfo
		del self.service
		del frontendData

		self.Ku_band_freq_limits = {"low": 10700, "high": 12750}
		self.universal_lo_freq = {"low": 9750, "high": 10600}
		self.c_band_freq_limits = {"low": 3000, "high": 4200, "default_low": 3400, "default_high": 4200}
		self.c_band_lo_freq = 5150
		self.tunerIfLimits = {"low": 950, "high": 2150}
		self.uni_lnb_cutoff = 11700
		self.last_user_defined_lo_freq = 0 # # Makes values sticky when changing satellite
		self.circular_lnb_lo_freq = 10750
		self.linear_polarisations = (
			eDVBFrontendParametersSatellite.Polarisation_Horizontal,
			eDVBFrontendParametersSatellite.Polarisation_Vertical,
			eDVBFrontendParametersSatellite.Polarisation_CircularRight + 1)

		self.blindscan_Ku_band_start_frequency = ConfigInteger(default=self.Ku_band_freq_limits["low"], limits=(self.Ku_band_freq_limits["low"], self.Ku_band_freq_limits["high"] - 1))
		self.blindscan_Ku_band_stop_frequency = ConfigInteger(default=self.Ku_band_freq_limits["high"], limits=(self.Ku_band_freq_limits["low"] + 1, self.Ku_band_freq_limits["high"]))
		self.blindscan_C_band_start_frequency = ConfigInteger(default=self.c_band_freq_limits["default_low"], limits=(self.c_band_freq_limits["low"], self.c_band_freq_limits["high"] - 1))
		self.blindscan_C_band_stop_frequency = ConfigInteger(default=self.c_band_freq_limits["default_high"], limits=(self.c_band_freq_limits["low"] + 1, self.c_band_freq_limits["high"]))

		# collect all nims which are *not* set to "nothing"
		nim_list = []
		for n in nimmanager.nim_slots:
			if not n.isCompatible("DVB-S"):
				continue
			if hasattr(n, 'isFBCLink') and n.isFBCLink():
				continue
			if n.description in _unsupportedNims: # DVB-S NIMs without blindscan hardware or software
				continue
			if n.config_mode == "nothing":
				continue
			try:
				if n.config_mode == "advanced" and int(n.config.advanced.sat[3607].lnb.value) != 0:
					continue
			except:
				pass
			if len(nimmanager.getSatListForNim(n.slot)) < 1:
				if n.config_mode in ("advanced", "simple"):
					config.Nims[n.slot].configMode.value = "nothing"
					config.Nims[n.slot].configMode.save()
				continue
			if n.config_mode in ("loopthrough", "satposdepends"):
				root_id = nimmanager.sec.getRoot(n.slot_id, int(n.config.connectedTo.value))
				if n.type == nimmanager.nim_slots[root_id].type: # check if connected from a DVB-S to DVB-S2 Nim or vice versa
					continue
			nim_list.append((str(n.slot), n.friendly_full_description))
		self.scan_nims = ConfigSelection(choices=nim_list)

		self.scan_satselection = []
		for slot in nimmanager.nim_slots:
			if slot.canBeCompatible("DVB-S"):
				default_sat_pos = defaultSat["orbpos"]
				if self.getCurrentTuner != None and slot.slot != self.getCurrentTuner:
					if len(nimmanager.getRotorSatListForNim(slot.slot)) and Lastrotorposition is not None and config.misc.lastrotorposition.value != 9999:
						default_sat_pos = config.misc.lastrotorposition.value
				self.scan_satselection.append(getConfigSatlist(default_sat_pos, self.satList[slot.slot]))

	def getSelectedSatIndex(self, v):
		index = 0
		none_cnt = 0
		for n in self.satList:
			if self.satList[index] is None:
				none_cnt = none_cnt + 1
			if index == int(v):
				return (index - none_cnt)
			index = index + 1
		return -1

	def createSetup(self, first_start=False):
		self.list = []
		if self.scan_nims == []:
			return
		index_to_scan = int(self.scan_nims.value)
		print("[Blindscan][createSetup] ID: ", index_to_scan)

		warning_text = ""
		nim = nimmanager.nim_slots[index_to_scan]
		nimname = nim.friendly_full_description
		self.SundtekScan = "Sundtek DVB-S/S2" in nimname
		if not self.SundtekScan and (BOX_MODEL.startswith('xtrend') or BOX_MODEL.startswith('vu')):
			warning_text = _("\nWARNING! Blind scan may make the tuner malfunction on a VU+ and ET receiver. A reboot afterwards may be required to return to proper tuner function.")
			if BOX_MODEL.startswith('vu') and "AVL6222" in nimname:
				warning_text = _("\nSecond slot dual tuner may not be supported blind scan.")
		elif self.SundtekScan:
			warning_text = _("\nYou must use the power adapter.")

		self.tunerEntry = getConfigListEntry(_("Tuner"), self.scan_nims, (_('Select a tuner that is configured for the satellite you wish to search') + warning_text))
		self.list.append(self.tunerEntry)

		self.satelliteEntry = None
		self.onlyUnknownTpsEntry = None
		self.userDefinedLnbInversionEntry = None

		if nim.canBeCompatible("DVB-S"):
			self.satelliteEntry = getConfigListEntry(_('Satellite'), self.scan_satselection[self.getSelectedSatIndex(index_to_scan)], _('Select the satellite you wish to search'))
			self.list.append(self.satelliteEntry)

			if not self.SatBandCheck():
				self["config"].list = self.list
				self["config"].l.setList(self.list)
				#self["description"].setText(_("LNB of current satellite not compatible with plugin"))
				self["key_green"].setText("")
				self["key_blue"].setText("")
				self["actions2"].setEnabled(False)
				self["introduction"].setText(_("LNB of current satellite not compatible with plugin"))
				return
			else:
				self["introduction"].setText(_("Press Green/OK to start the scan"))

			self.searchtypeEntry = getConfigListEntry(_("Search type"), config.blindscan.search_type, _('"channel scan" searches for channels and saves them to your receiver; "transponder scan" does a transponder search and displays the results allowing user to select some or all transponder. Both options save the results in satellites.xml format under /tmp'))
			self.list.append(self.searchtypeEntry)

			if self.is_c_band_scan:
				self.list.append(getConfigListEntry(_("Scan start frequency"), self.blindscan_C_band_start_frequency, _('Frequency values must be between %d MHz and %d MHz (C-band)') % (self.c_band_freq_limits["low"], self.c_band_freq_limits["high"] - 1)))
				self.list.append(getConfigListEntry(_("Scan stop frequency"), self.blindscan_C_band_stop_frequency, _('Frequency values must be between %d MHz and %d MHz (C-band)') % (self.c_band_freq_limits["low"] + 1, self.c_band_freq_limits["high"])))
			elif self.is_Ku_band_scan:
				self.list.append(getConfigListEntry(_("Scan start frequency"), self.blindscan_Ku_band_start_frequency, _('Frequency values must be between %d MHz and %d MHz') % (self.Ku_band_freq_limits["low"], self.Ku_band_freq_limits["high"] - 1)))
				self.list.append(getConfigListEntry(_("Scan stop frequency"), self.blindscan_Ku_band_stop_frequency, _('Frequency values must be between %d MHz and %d MHz') % (self.Ku_band_freq_limits["low"] + 1, self.Ku_band_freq_limits["high"])))
			elif self.user_defined_lnb_scan:
				self.userDefinedLnbInversionEntry = getConfigListEntry(_("LNB inversion"), config.blindscan.user_defined_lnb_inversion, _('CAUTION: Only select "inverted" if you are using an inverted LNB (i.e. an LNB where the local oscillator frequency is greater than the scan frequency). Default is "normal". Only change this if you understand why you are doing it.'))
				self.list.append(self.userDefinedLnbInversionEntry)
				if self.last_user_defined_lo_freq != self.user_defined_lnb_lo_freq: # only recreate user defined config if user defined local oscillator changed frequency when moving to another user defined LNB
					self.last_user_defined_lo_freq = self.user_defined_lnb_lo_freq
					self.blindscan_user_defined_lnb_inverted_start_frequency = ConfigInteger(default=self.user_defined_lnb_lo_freq - self.tunerIfLimits["high"], limits=(self.user_defined_lnb_lo_freq - self.tunerIfLimits["high"], self.user_defined_lnb_lo_freq - self.tunerIfLimits["low"] - 1))
					self.blindscan_user_defined_lnb_inverted_stop_frequency = ConfigInteger(default=self.user_defined_lnb_lo_freq - self.tunerIfLimits["low"], limits=(self.user_defined_lnb_lo_freq - self.tunerIfLimits["high"] + 1, self.user_defined_lnb_lo_freq - self.tunerIfLimits["low"]))
					self.blindscan_user_defined_lnb_start_frequency = ConfigInteger(default=self.user_defined_lnb_lo_freq + self.tunerIfLimits["low"], limits=(self.user_defined_lnb_lo_freq + self.tunerIfLimits["low"], self.user_defined_lnb_lo_freq + self.tunerIfLimits["high"] - 1))
					self.blindscan_user_defined_lnb_stop_frequency = ConfigInteger(default=self.user_defined_lnb_lo_freq + self.tunerIfLimits["high"], limits=(self.user_defined_lnb_lo_freq + self.tunerIfLimits["low"] + 1, self.user_defined_lnb_lo_freq + self.tunerIfLimits["high"]))
				if config.blindscan.user_defined_lnb_inversion.value:
					self.list.append(getConfigListEntry(_("Scan start frequency"), self.blindscan_user_defined_lnb_inverted_start_frequency, _('Frequency values must be between %d MHz and %d MHz') % (self.user_defined_lnb_lo_freq - self.tunerIfLimits["high"], self.user_defined_lnb_lo_freq - self.tunerIfLimits["low"] - 1)))
					self.list.append(getConfigListEntry(_("Scan stop frequency"), self.blindscan_user_defined_lnb_inverted_stop_frequency, _('Frequency values must be between %d MHz and %d MHz') % (self.user_defined_lnb_lo_freq - self.tunerIfLimits["high"] + 1, self.user_defined_lnb_lo_freq - self.tunerIfLimits["low"])))
				else: # Normal LNB, not inverted
					self.list.append(getConfigListEntry(_('Scan start frequency'), self.blindscan_user_defined_lnb_start_frequency, _('Frequency values must be between %d MHz and %d MHz') % (self.user_defined_lnb_lo_freq + self.tunerIfLimits["low"], self.user_defined_lnb_lo_freq + self.tunerIfLimits["high"] - 1)))
					self.list.append(getConfigListEntry(_('Scan stop frequency'), self.blindscan_user_defined_lnb_stop_frequency, _('Frequency values must be between %d MHz and %d MHz') % (self.user_defined_lnb_lo_freq + self.tunerIfLimits["low"] + 1, self.user_defined_lnb_lo_freq + self.tunerIfLimits["high"])))

			if nim.description == 'TBS-5925':
				self.list.append(getConfigListEntry(_("Scan Step in MHz(TBS5925)"), config.blindscan.step_mhz_tbs5925, _('Smaller steps takes longer but scan is more thorough')))
			self.list.append(getConfigListEntry(_("Polarisation"), config.blindscan.polarization, _('The suggested polarisation for this satellite is "%s"') % (self.suggestedPolarisation)))
			self.list.append(getConfigListEntry(_("Scan start symbolrate"), config.blindscan.start_symbol, _('Symbol rate values are in megasymbols; enter a value between 1 and 44')))
			self.list.append(getConfigListEntry(_("Scan stop symbolrate"), config.blindscan.stop_symbol, _('Symbol rate values are in megasymbols; enter a value between 2 and 45')))
			self.list.append(getConfigListEntry(_("Clear before scan"), config.blindscan.clearallservices, _('If you select "yes" all channels on the satellite being search will be deleted before starting the current search, yes (keep feeds) means the same but hold all feed services/transponders.')))
			self.list.append(getConfigListEntry(_("Only free scan"), config.blindscan.onlyFTA, _('If you select "yes" the scan will only save channels that are not encrypted; "no" will find encrypted and non-encrypted channels.')))
			self.onlyUnknownTpsEntry = getConfigListEntry(_("Only scan unknown transponders"), config.blindscan.dont_scan_known_tps, _('If you select "yes" the scan will only search transponders not listed in satellites.xml'))
			self.list.append(self.onlyUnknownTpsEntry)
			if not config.blindscan.dont_scan_known_tps.value:
				self.list.append(getConfigListEntry(_("Disable sync with known transponders"), config.blindscan.disable_sync_with_known_tps, _('CAUTION: If you select "yes" the scan will not sync with transponders listed in satellites.xml. Default is "no". Only change this if you understand why you are doing it.')))
			self.list.append(getConfigListEntry(_("Disable remove duplicates"), config.blindscan.disable_remove_duplicate_tps, _('CAUTION: If you select "yes" the scan will not remove "duplicated" transponders from the list. Default is "no". Only change this if you understand why you are doing it.')))
			self.list.append(getConfigListEntry(_("Filter out adjacent satellites"), config.blindscan.filter_off_adjacent_satellites, _('When a neighbouring satellite is very strong this avoids searching transponders known to be coming from the neighbouring satellite.')))
			self["config"].list = self.list
			self["config"].l.setList(self.list)
			self["key_green"].setText(_("Scan"))
			self["actions2"].setEnabled(True)
			if first_start:
				self.firstTimer = eTimer()
				self.firstTimer.callback.append(self.startDishMovingIfRotorSat)
				self.firstTimer.start(1000, True)
			else:
				self.startDishMovingIfRotorSat()

	def newConfig(self):
		cur = self["config"].getCurrent()
		print("[Blindscan][newConfig] cur is", cur)
		if cur and (cur == self.tunerEntry or cur == self.satelliteEntry or cur == self.onlyUnknownTpsEntry or cur == self.userDefinedLnbInversionEntry):
			self.createSetup()
		self.setBlueText()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

	def saveConfig(self):
		for x in self["config"].list:
			x[1].save()

	def keyCancel(self):
		self.saveConfig()
		if self.clockTimer:
			self.clockTimer.stop()
		self.statusTimer.stop()
		self.releaseFrontend()
		self.session.nav.playService(self.session.postScanService)
		self.close(False)

	def keyGo(self):
		self.saveConfig()
		print("[Blindscan][keyGo] started")
		self.start_time = time()
		self.tp_found = []

		tab_pol = {
			eDVBFrontendParametersSatellite.Polarisation_Horizontal: "horizontal",
			eDVBFrontendParametersSatellite.Polarisation_Vertical: "vertical",
			eDVBFrontendParametersSatellite.Polarisation_CircularLeft: "circular left",
			eDVBFrontendParametersSatellite.Polarisation_CircularRight: "circular right",
			eDVBFrontendParametersSatellite.Polarisation_CircularRight + 1: "horizontal and vertical",
			eDVBFrontendParametersSatellite.Polarisation_CircularRight + 2: "circular left and circular right"
		}

		self.tmp_tplist = []
		tmp_pol = []
		tmp_band = []
		idx_selected_sat = int(self.getSelectedSatIndex(self.scan_nims.value))
		tmp_list = [self.satList[int(self.scan_nims.value)][self.scan_satselection[idx_selected_sat].index]]

		if self.is_Ku_band_scan:
			self.checkStartStopValues(self.blindscan_Ku_band_start_frequency, self.blindscan_Ku_band_stop_frequency)
			self.blindscan_start_frequency = self.blindscan_Ku_band_start_frequency.value
			self.blindscan_stop_frequency = self.blindscan_Ku_band_stop_frequency.value
		elif self.is_c_band_scan:
			self.checkStartStopValues(self.blindscan_C_band_start_frequency, self.blindscan_C_band_stop_frequency)
			self.blindscan_start_frequency = self.blindscan_C_band_start_frequency.value
			self.blindscan_stop_frequency = self.blindscan_C_band_stop_frequency.value
		elif self.user_defined_lnb_scan:
			if config.blindscan.user_defined_lnb_inversion.value:
				self.checkStartStopValues(self.blindscan_user_defined_lnb_inverted_start_frequency, self.blindscan_user_defined_lnb_inverted_stop_frequency)
				self.blindscan_start_frequency = abs((self.blindscan_user_defined_lnb_inverted_stop_frequency.value - self.user_defined_lnb_lo_freq) * 2) + self.blindscan_user_defined_lnb_inverted_stop_frequency.value - (self.user_defined_lnb_lo_freq - self.universal_lo_freq["low"])
				self.blindscan_stop_frequency = abs((self.blindscan_user_defined_lnb_inverted_start_frequency.value - self.user_defined_lnb_lo_freq) * 2) + self.blindscan_user_defined_lnb_inverted_start_frequency.value - (self.user_defined_lnb_lo_freq - self.universal_lo_freq["low"])
			else:
				self.checkStartStopValues(self.blindscan_user_defined_lnb_start_frequency, self.blindscan_user_defined_lnb_stop_frequency)
				self.blindscan_start_frequency = self.blindscan_user_defined_lnb_start_frequency.value - (self.user_defined_lnb_lo_freq - self.universal_lo_freq["low"])
				self.blindscan_stop_frequency = self.blindscan_user_defined_lnb_stop_frequency.value - (self.user_defined_lnb_lo_freq - self.universal_lo_freq["low"])
		else:
			return

		self.checkStartStopValues(config.blindscan.start_symbol, config.blindscan.stop_symbol)

		if self.user_defined_lnb_scan:
			uni_lnb_cutoff = self.blindscan_stop_frequency
		else:
			uni_lnb_cutoff = self.uni_lnb_cutoff

		if self.blindscan_start_frequency < uni_lnb_cutoff and self.blindscan_stop_frequency > uni_lnb_cutoff:
			tmp_band = ["low", "high"]
		elif self.blindscan_start_frequency < uni_lnb_cutoff:
			tmp_band = ["low"]
		else:
			tmp_band = ["high"]

		if int(config.blindscan.polarization.value) > eDVBFrontendParametersSatellite.Polarisation_CircularRight: # must be searching both polarisations, either V and H, or R and L
			tmp_pol = ["vertical", "horizontal"]
		elif int(config.blindscan.polarization.value) == eDVBFrontendParametersSatellite.Polarisation_CircularRight:
			tmp_pol = ["vertical"]
		elif int(config.blindscan.polarization.value) == eDVBFrontendParametersSatellite.Polarisation_CircularLeft:
			tmp_pol = ["horizontal"]
		else:
			tmp_pol = [tab_pol[int(config.blindscan.polarization.value)]]

		self.doRun(tmp_list, tmp_pol, tmp_band)

	def checkStartStopValues(self, start, stop):
		# swap start and stop values if entered the wrong way round
		if start.value > stop.value:
			start.value, stop.value = (stop.value, start.value)

	def doRun(self, tmp_list, tmp_pol, tmp_band):
		print("[Blindscan][doRun] started")

		def GetCommand(nimIdx):
			_nimSocket = self.nimSockets
			try:
				sName = _nimSocket[str(nimIdx)][0]
				sType = _supportNimType[sName]
				return "vuplus_%(TYPE)sblindscan" % {'TYPE': sType}, sName
			except:
				pass
			return "vuplus_blindscan", ""
		if BOX_MODEL == "vuplus" and not self.SundtekScan:
			self.binName, nimName = GetCommand(self.scan_nims.value)

			self.makeNimSocket(nimName)
			if self.binName is None:
				self.session.open(MessageBox, _("Blindscan is not supported in ") + nimName + _(" tuner."), MessageBox.TYPE_ERROR)
				print("[Blindscan][doRun] " + nimName + " does not support blindscan.")
				return

		self.full_data = ""
		self.total_list = []
		for x in tmp_list:
			for y in tmp_pol:
				for z in tmp_band:
					self.total_list.append([x, y, z])
					print("[Blindscan][doRun] add scan item: ", x, ", ", y, ", ", z)

		self.max_count = len(self.total_list)
		self.is_runable = True
		self.running_count = 0
		self.clockTimer = eTimer()
		self.clockTimer.callback.append(self.doClock)
		self.start_time = time()
		if self.SundtekScan:
			if self.clockTimer:
				self.clockTimer.stop()
				del self.clockTimer
				self.clockTimer = None
			orb = self.total_list[self.running_count][0]
			pol = self.total_list[self.running_count][1]
			band = self.total_list[self.running_count][2]
			self.prepareScanData(orb, pol, band, True)
		else:
			self.clockTimer.start(1000)

	def doClock(self):
#		print "[Blindscan][doClock] started"
		is_scan = False
#		print "[Blindscan][doClock] self.is_runable", self.is_runable
		if self.is_runable:
			if self.running_count >= self.max_count:
				self.clockTimer.stop()
				del self.clockTimer
				self.clockTimer = None
				print("[Blindscan][doClock] Done")
				return
			orb = self.total_list[self.running_count][0]
			pol = self.total_list[self.running_count][1]
			band = self.total_list[self.running_count][2]
			self.running_count = self.running_count + 1
			print("[Blindscan][doClock] running status-[%d]: [%d][%s][%s]" % (self.running_count, orb[0], pol, band))
			if self.running_count == self.max_count:
				is_scan = True
			self.prepareScanData(orb, pol, band, is_scan)

	def prepareScanData(self, orb, pol, band, is_scan):
		print("[Blindscan][prepareScanData] started")
		self.is_runable = False
		self.adjust_freq = True
		self.orb_position = orb[0]
		self.sat_name = orb[1]
		self.feid = int(self.scan_nims.value)
		tab_hilow = {"high": 1, "low": 0}
		tab_pol = {
			"horizontal": eDVBFrontendParametersSatellite.Polarisation_Horizontal,
			"vertical": eDVBFrontendParametersSatellite.Polarisation_Vertical,
			"circular left": eDVBFrontendParametersSatellite.Polarisation_CircularLeft,
			"circular right": eDVBFrontendParametersSatellite.Polarisation_CircularRight
		}
		uni_lnb_cutoff = self.uni_lnb_cutoff

		if not self.prepareFrontend():
			print("[Blindscan][prepareScanData] self.prepareFrontend() failed (in prepareScanData)")
			return False

		random_ku_band_low_tunable_freq = 11015 # used to activate the tuner
		random_c_band_tunable_freq = 3400 # used to activate the tuner

		if self.is_c_band_scan:
			tuning_frequency = random_c_band_tunable_freq
		elif self.user_defined_lnb_scan:
			tuning_frequency = random_ku_band_low_tunable_freq + (self.user_defined_lnb_lo_freq - self.universal_lo_freq["low"])
		else:
			if tab_hilow[band]: # high band
				tuning_frequency = random_ku_band_low_tunable_freq + (self.universal_lo_freq["high"] - self.universal_lo_freq["low"]) #used to be 12515
			else: # low band
				tuning_frequency = random_ku_band_low_tunable_freq

		self.tuner.tune(
			(tuning_frequency,
			0, # symbolrate
			tab_pol[pol],
			eDVBFrontendParametersSatellite.FEC_Auto,
			eDVBFrontendParametersSatellite.Inversion_Off,
			orb[0],
			eDVBFrontendParametersSatellite.System_DVB_S,
			eDVBFrontendParametersSatellite.Modulation_Auto,
			eDVBFrontendParametersSatellite.RollOff_alpha_0_35,
			eDVBFrontendParametersSatellite.Pilot_Off,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid)
		)

		nim = nimmanager.nim_slots[self.feid]
		tunername = nim.description
		if not self.SundtekScan and tunername not in _blindscans2Nims and self.getNimSocket(self.feid) < 0:
			print("[Blindscan][prepareScanData] can't find i2c number!!")
			return

		if self.is_c_band_scan:
			temp_start_int_freq = self.c_band_lo_freq - self.blindscan_stop_frequency
			temp_end_int_freq = self.c_band_lo_freq - self.blindscan_start_frequency
			status_box_start_freq = self.c_band_lo_freq - temp_end_int_freq
			status_box_end_freq = self.c_band_lo_freq - temp_start_int_freq

		elif self.user_defined_lnb_scan:
			temp_start_int_freq = self.blindscan_start_frequency - self.universal_lo_freq["low"]
			temp_end_int_freq = self.blindscan_stop_frequency - self.universal_lo_freq["low"]
			if config.blindscan.user_defined_lnb_inversion.value:
				status_box_start_freq = self.user_defined_lnb_lo_freq - temp_end_int_freq
				status_box_end_freq = self.user_defined_lnb_lo_freq - temp_start_int_freq
			else:
				status_box_start_freq = self.blindscan_start_frequency + (self.user_defined_lnb_lo_freq - self.universal_lo_freq["low"])
				status_box_end_freq = self.blindscan_stop_frequency + (self.user_defined_lnb_lo_freq - self.universal_lo_freq["low"])

		else:
			if tab_hilow[band]:
				if self.blindscan_start_frequency < uni_lnb_cutoff:
					temp_start_int_freq = uni_lnb_cutoff - self.universal_lo_freq[band]
				else:
					temp_start_int_freq = self.blindscan_start_frequency - self.universal_lo_freq[band]
				temp_end_int_freq = self.blindscan_stop_frequency - self.universal_lo_freq[band]
			else:
				if self.blindscan_stop_frequency > uni_lnb_cutoff:
					temp_end_int_freq = uni_lnb_cutoff - self.universal_lo_freq[band]
				else:
					temp_end_int_freq = self.blindscan_stop_frequency - self.universal_lo_freq[band]
				temp_start_int_freq = self.blindscan_start_frequency - self.universal_lo_freq[band]
			status_box_start_freq = temp_start_int_freq + self.universal_lo_freq[band]
			status_box_end_freq = temp_end_int_freq + self.universal_lo_freq[band]

		cmd = ""
		self.cmd = ""
		self.tmpstr = ""

		not_support_text = _("It seems manufacturer does not support blind scan for this tuner.")
		if tunername in _blindscans2Nims:
			tools = "/usr/bin/blindscan-s2"
			if os.path.exists(tools):
				if tunername == "TBS-5925":
					cmd = "blindscan-s2 -b -s %d -e %d -t %d" % (temp_start_int_freq, temp_end_int_freq, config.blindscan.step_mhz_tbs5925.value)
				else:
					cmd = "blindscan-s2 -b -s %d -e %d" % (temp_start_int_freq, temp_end_int_freq)
				cmd += getAdapterFrontend(self.feid, tunername)
				if pol == "horizontal":
					cmd += " -H"
				elif pol == "vertical":
					cmd += " -V"
				if self.is_c_band_scan:
					cmd += " -l %d" % self.c_band_lo_freq # tested by el bandito with TBS-5925 and working
				elif tab_hilow[band]:
					cmd += " -l %d -2" % self.universal_lo_freq["high"] # on high band enable 22KHz tone
				else:
					cmd += " -l %d" % self.universal_lo_freq["low"]
				#self.frontend.closeFrontend() # close because blindscan-s2 does not like to be open
				self.cmd = cmd
				self.bsTimer.stop()
				self.bsTimer.start(6000, True)
			else:
				self.session.open(MessageBox, _("Not found blind scan utility '%s'!") % tools, MessageBox.TYPE_ERROR)
		elif self.SundtekScan:
			tools = "/opt/bin/mediaclient"
			if os.path.exists(tools):
				cmd = "%s --blindscan %d" % (tools, self.feid)
				if self.is_c_band_scan:
					cmd += " --band c"
			else:
				self.session.open(MessageBox, _("Not found blind scan utility '%s'!") % tools, MessageBox.TYPE_ERROR)
				return
		elif BOX_NAME in ("mbtwinplus", "mbmicro", "mbmicrov2"):
			tools = "/usr/bin/ceryon_blindscan"
			if os.path.exists(tools):
				cmd = "ceryon_blindscan %d %d %d %d %d %d %d %d" % (temp_start_int_freq, temp_end_int_freq, config.blindscan.start_symbol.value, config.blindscan.stop_symbol.value, tab_pol[pol], tab_hilow[band], self.feid, self.getNimSocket(self.feid))
				cmd += " %d" % self.is_c_band_scan
			else:
				self.session.open(MessageBox, _("Not found blind scan utility '%s'!") % tools, MessageBox.TYPE_ERROR)
				return
		elif BOX_MODEL == "vuplus":
			if BOX_NAME in ("uno", "duo2", "solo2", "solose", "ultimo", "solo4k", "ultimo4k", "zero4k"):
				tools = "/usr/bin/%s" % self.binName
				if os.path.exists(tools):
					try:
						cmd = "%s %d %d %d %d %d %d %d %d" % (self.binName, temp_start_int_freq, temp_end_int_freq, config.blindscan.start_symbol.value, config.blindscan.stop_symbol.value, tab_pol[pol], tab_hilow[band], self.feid, self.getNimSocket(self.feid))
					except:
						self.session.open(MessageBox, _("Scan unknown error!"), MessageBox.TYPE_ERROR)
						return
				else:
					self.session.open(MessageBox, _("Not found blind scan utility '%s'!") % tools, MessageBox.TYPE_ERROR)
					return
			else:
				self.session.open(MessageBox, not_support_text, MessageBox.TYPE_WARNING)
				return
		elif BOX_MODEL.startswith("xtrend"):
			if BOX_NAME.startswith("et9") or BOX_NAME.startswith("et6") or BOX_NAME.startswith("et5"):
				tools = "/usr/bin/avl_xtrend_blindscan"
				if os.path.exists(tools):
					cmd = "avl_xtrend_blindscan %d %d %d %d %d %d %d %d" % (temp_start_int_freq, temp_end_int_freq, config.blindscan.start_symbol.value, config.blindscan.stop_symbol.value, tab_pol[pol], tab_hilow[band], self.feid, self.getNimSocket(self.feid)) # commented out by Huevos cmd = "avl_xtrend_blindscan %d %d %d %d %d %d %d %d" % (self.blindscan_start_frequency.value/1000000, self.blindscan_stop_frequency.value/1000000, self.blindscan_start_symbol.value, self.blindscan_stop_symbol.value, tab_pol[pol], tab_hilow[band], self.feid, self.getNimSocket(self.feid))
				else:
					self.session.open(MessageBox, _("Not found blind scan utility '%s'!") % tools, MessageBox.TYPE_ERROR)
					return
			else:
				self.session.open(MessageBox, not_support_text, MessageBox.TYPE_WARNING)
				return
		elif BOX_MODEL.startswith("edision"):
			tools = "/usr/bin/blindscan"
			if os.path.exists(tools):
				cmd = "blindscan --start=%d --stop=%d --min=%d --max=%d --slot=%d --i2c=%d" % (temp_start_int_freq, temp_end_int_freq, config.blindscan.start_symbol.value, config.blindscan.stop_symbol.value, self.feid, self.getNimSocket(self.feid))
				if tab_pol[pol]:
					cmd += " --vertical"
				if self.is_c_band_scan:
					cmd += " --cband"
				elif tab_hilow[band]:
					cmd += " --high"
			else:
				self.session.open(MessageBox, _("Not found blind scan utility '%s'!") % tools, MessageBox.TYPE_ERROR)
				return
		elif BOX_NAME == "lunix4k":
			tools = "/usr/bin/qviart_blindscan_72604"
			if os.path.exists(tools):
				cmd = "qviart_blindscan_72604 %d %d %d %d %d %d %d %d %d %d" % (temp_start_int_freq, temp_end_int_freq, config.blindscan.start_symbol.value, config.blindscan.stop_symbol.value, tab_pol[pol], tab_hilow[band], self.feid, self.getNimSocket(self.feid), self.is_c_band_scan, orb[0])
			else:
				self.session.open(MessageBox, _("Not found blind scan utility '%s'!") % tools, MessageBox.TYPE_ERROR)
				return
		elif BOX_NAME == "dual":
			tools = "/usr/bin/qviart_blindscan"
			if os.path.exists(tools):
				cmd = "qviart_blindscan %d %d %d %d %d %d %d %d %d %d" % (temp_start_int_freq, temp_end_int_freq, config.blindscan.start_symbol.value, config.blindscan.stop_symbol.value, tab_pol[pol], tab_hilow[band], self.feid, self.getNimSocket(self.feid), self.is_c_band_scan, orb[0])
			else:
				self.session.open(MessageBox, _("Not found blind scan utility '%s'!") % tools, MessageBox.TYPE_ERROR)
				return
		elif BOX_NAME == "ustym4kpro":
			tools = "/usr/bin/uclan-blindscan"
			if os.path.exists(tools):
				cmd = "uclan-blindscan %d %d %d %d %d %d %d %d %d %d" % (temp_start_int_freq, temp_end_int_freq, config.blindscan.start_symbol.value, config.blindscan.stop_symbol.value, tab_pol[pol], tab_hilow[band], self.feid, self.getNimSocket(self.feid), self.is_c_band_scan, orb[0])
				self.adjust_freq = False
			else:
				self.session.open(MessageBox, _("Not found blind scan utility '%s'!") % tools, MessageBox.TYPE_ERROR)
				return
		elif BOX_NAME.startswith("sf8008"):
			#self.frontend and self.frontend.closeFrontend()
			tools = "/usr/bin/octagon-blindscan"
			if os.path.exists(tools):
				cmd = "octagon-blindscan %d %d %d %d %d %d %d %d %d %d" % (temp_start_int_freq, temp_end_int_freq, config.blindscan.start_symbol.value, config.blindscan.stop_symbol.value, tab_pol[pol], tab_hilow[band], self.feid, self.getNimSocket(self.feid), self.is_c_band_scan, orb[0])
			else:
				self.session.open(MessageBox, _("Not found blind scan utility '%s'!") % tools, MessageBox.TYPE_ERROR)
				return
		elif BOX_NAME == "sfx6008":
			tools = "/usr/bin/octagon-blindscan"
			if os.path.exists(tools):
				cmd = "octagon-blindscan %d %d %d %d %d %d %d %d %d %d" % (temp_start_int_freq, temp_end_int_freq, config.blindscan.start_symbol.value, config.blindscan.stop_symbol.value, tab_pol[pol], tab_hilow[band], self.feid, self.getNimSocket(self.feid), self.is_c_band_scan, orb[0])
			else:
				self.session.open(MessageBox, _("Not found blind scan utility '%s'!") % tools, MessageBox.TYPE_ERROR)
				return
		elif BOX_MODEL == "gigablue":
			tools = "/usr/bin/gigablue_blindscan"
			if os.path.exists(tools):
				cmd = "gigablue_blindscan %d %d %d %d %d %d %d %d" % (temp_start_int_freq, temp_end_int_freq, config.blindscan.start_symbol.value, config.blindscan.stop_symbol.value, tab_pol[pol], tab_hilow[band], self.feid, self.getNimSocket(self.feid))
				if BOX_NAME == "gbtrio4k":
					cmd += " %d" % self.is_c_band_scan
					cmd += " %d" % orb[0]
					self.adjust_freq = False
			else:
				self.session.open(MessageBox, _("Not found blind scan utility '%s'!") % tools, MessageBox.TYPE_ERROR)
				return
		else:
			self.session.open(MessageBox, not_support_text, MessageBox.TYPE_WARNING)
		print("[Blindscan][prepareScanData] prepared command: [%s]" % (cmd))

		self.thisRun = [] # used to check result corresponds with values used above
		self.thisRun.append(int(temp_start_int_freq))
		self.thisRun.append(int(temp_end_int_freq))
		self.thisRun.append(int(tab_hilow[band]))

		if not self.cmd:
			if self.SundtekScan:
				print("[Blindscan][prepareScanData] closing frontend and starting blindscan")
				self.frontend and self.frontend.closeFrontend()
			self.blindscan_container = eConsoleAppContainer()
			self.blindscan_container.appClosed.append(self.blindscanContainerClose)
			self.blindscan_container.dataAvail.append(self.blindscanContainerAvail)
			self.blindscan_container.execute(cmd)

		display_pol = pol # Display the correct polarisation in the MessageBox below
		if int(config.blindscan.polarization.value) == eDVBFrontendParametersSatellite.Polarisation_CircularRight:
			display_pol = _("circular right")
		elif int(config.blindscan.polarization.value) == eDVBFrontendParametersSatellite.Polarisation_CircularLeft:
			display_pol = _("circular left")
		elif int(config.blindscan.polarization.value) == eDVBFrontendParametersSatellite.Polarisation_CircularRight + 2:
			if pol == "horizontal":
				display_pol = _("circular left")
			else:
				display_pol = _("circular right")
		if display_pol == "horizontal":
			display_pol = _("horizontal")
		if display_pol == "vertical":
			display_pol = _("vertical")

		if self.SundtekScan:
			tmpmes = _("   Starting Sundtek hardware blind scan.")
			self.tmpstr = tmpmes
		else:
			tmpmes = _("Current Status: %d/%d\nSatellite: %s\nPolarization: %s  Frequency range: %d - %d MHz  Symbol rates: %d - %d MSym/s") % (self.running_count, self.max_count, orb[1], display_pol, status_box_start_freq, status_box_end_freq, config.blindscan.start_symbol.value, config.blindscan.stop_symbol.value)
		tmpmes2 = _("Looking for available transponders.\nThis will take a long time, please be patient.")
		if is_scan:
			self.blindscan_session = self.session.openWithCallback(self.blindscanSessionClose, BlindscanState, tmpmes, tmpmes2, [])
		else:
			self.blindscan_session = self.session.openWithCallback(self.blindscanSessionNone, BlindscanState, tmpmes, tmpmes2, [])

	def dataSundtekIsGood(self, data):
		add_tp = False
		pol = int(config.blindscan.polarization.value)
		if pol == eDVBFrontendParametersSatellite.Polarisation_CircularRight + 1 or pol == eDVBFrontendParametersSatellite.Polarisation_CircularRight + 2:
			add_tp = True
		elif self.Sundtek_pol in (eDVBFrontendParametersSatellite.Polarisation_Vertical, eDVBFrontendParametersSatellite.Polarisation_CircularRight) and pol in (eDVBFrontendParametersSatellite.Polarisation_Vertical, eDVBFrontendParametersSatellite.Polarisation_CircularRight):
			add_tp = True
		elif self.Sundtek_pol in (eDVBFrontendParametersSatellite.Polarisation_Horizontal, eDVBFrontendParametersSatellite.Polarisation_CircularLeft) and pol in (eDVBFrontendParametersSatellite.Polarisation_Horizontal, eDVBFrontendParametersSatellite.Polarisation_CircularLeft):
			add_tp = True
		if add_tp:
			if data[2].isdigit() and data[3].isdigit():
				freq = (int(data[2]) + self.offset) / 1000
				symbolrate = int(data[3])
			else:
				return False
			if self.blindscan_start_frequency <= freq <= self.blindscan_stop_frequency and config.blindscan.start_symbol.value * 1000 <= symbolrate <= config.blindscan.stop_symbol.value * 1000:
				add_tp = True
			else:
				add_tp = False
		if add_tp:
			if self.is_c_band_scan:
				if self.c_band_freq_limits["low"] - 1 < freq < self.c_band_freq_limits["high"] + 1:
					add_tp = True
				else:
					add_tp = False
			else:
				if self.Ku_band_freq_limits["low"] - 1 < freq < self.Ku_band_freq_limits["high"] + 1:
					add_tp = True
				else:
					add_tp = False
		return add_tp

	def blindscanContainerClose(self, retval):
		self.Sundtek_pol = ""
		self.Sundtek_band = ""
		self.offset = 0
		lines = self.full_data.split('\n')
		self.full_data = "" # Clear this string so we don't get duplicates on subsequent runs
		for line in lines:
			data = line.split()
			print("[Blindscan][blindscanContainerClose] cnt:", len(data), ", data:", data)
			if self.SundtekScan:
				if len(data) == 3 and data[0] == 'Scanning':
					if data[1] == '13V':
						self.Sundtek_pol = eDVBFrontendParametersSatellite.Polarisation_Vertical
						if int(config.blindscan.polarization.value) not in self.linear_polarisations:
							self.Sundtek_pol = eDVBFrontendParametersSatellite.Polarisation_CircularRight
					elif data[1] == '18V':
						self.Sundtek_pol = eDVBFrontendParametersSatellite.Polarisation_Horizontal
						if int(config.blindscan.polarization.value) not in self.linear_polarisations:
							self.Sundtek_pol = eDVBFrontendParametersSatellite.Polarisation_CircularLeft
					if data[2] == 'Highband':
						self.Sundtek_band = "high"
					elif data[2] == 'Lowband':
						self.Sundtek_band = "low"
					self.offset = 0
					if self.is_c_band_scan:
						self.offset = self.c_band_lo_freq * 1000
					else:
						if self.Sundtek_band == "high":
							self.offset = self.universal_lo_freq["high"] * 1000
						elif self.Sundtek_band == "low":
							self.offset = (self.user_defined_lnb_lo_freq if self.user_defined_lnb_scan else self.universal_lo_freq["low"]) * 1000
				if len(data) >= 6 and data[0] == 'OK' and self.Sundtek_pol != "" and self.offset and self.dataSundtekIsGood(data):
					parm = eDVBFrontendParametersSatellite()
					sys = {"DVB-S": parm.System_DVB_S,
						"DVB-S2": parm.System_DVB_S2,
						"DVB-S2X": parm.System_DVB_S2}
					qam = {"QPSK": parm.Modulation_QPSK,
						"8PSK": parm.Modulation_8PSK,
						"16APSK": parm.Modulation_16APSK,
						"APSK_16": parm.Modulation_16APSK,
						"APSK_32": parm.Modulation_32APSK,
						"32APSK": parm.Modulation_32APSK}
					parm.orbital_position = self.orb_position
					parm.polarisation = self.Sundtek_pol
					parm.frequency = ((int(data[2]) + self.offset) / 1000) * 1000
					parm.symbol_rate = int(data[3]) * 1000
					parm.system = sys[data[1]]
					parm.inversion = parm.Inversion_Off
					parm.pilot = parm.Pilot_Off
					parm.fec = parm.FEC_Auto
					parm.modulation = qam.get(data[4], eDVBFrontendParametersSatellite.Modulation_QPSK)
					parm.rolloff = parm.RollOff_alpha_0_35
					parm.pls_mode = eDVBFrontendParametersSatellite.PLS_Gold
					parm.is_id = eDVBFrontendParametersSatellite.No_Stream_Id_Filter
					parm.pls_code = 0
					if hasattr(parm, "t2mi_plp_id"):
						parm.t2mi_plp_id = eDVBFrontendParametersSatellite.No_T2MI_PLP_Id
					if hasattr(parm, "t2mi_pid"):
						parm.t2mi_pid = eDVBFrontendParametersSatellite.T2MI_Default_Pid
					self.tmp_tplist.append(parm)
			elif len(data) >= 10 and self.dataIsGood(data):
				if data[0] == 'OK':
					parm = eDVBFrontendParametersSatellite()
					sys = {"DVB-S": parm.System_DVB_S,
						"DVB-S2": parm.System_DVB_S2,
						"DVB-S2X": parm.System_DVB_S2}
					qam = {"QPSK": parm.Modulation_QPSK,
						"8PSK": parm.Modulation_8PSK,
						"16APSK": parm.Modulation_16APSK,
						"32APSK": parm.Modulation_32APSK}
					inv = {"INVERSION_OFF": parm.Inversion_Off,
						"INVERSION_ON": parm.Inversion_On,
						"INVERSION_AUTO": parm.Inversion_Unknown}
					fec = {"FEC_AUTO": parm.FEC_Auto,
						"FEC_1_2": parm.FEC_1_2,
						"FEC_2_3": parm.FEC_2_3,
						"FEC_3_4": parm.FEC_3_4,
						"FEC_4_5": parm.FEC_4_5,
						"FEC_5_6": parm.FEC_5_6,
						"FEC_7_8": parm.FEC_7_8,
						"FEC_8_9": parm.FEC_8_9,
						"FEC_3_5": parm.FEC_3_5,
						"FEC_9_10": parm.FEC_9_10,
						"FEC_NONE": parm.FEC_None}
					roll = {"ROLLOFF_20": parm.RollOff_alpha_0_20,
						"ROLLOFF_25": parm.RollOff_alpha_0_25,
						"ROLLOFF_35": parm.RollOff_alpha_0_35,
						"ROLLOFF_AUTO": parm.RollOff_auto}
					pilot = {"PILOT_ON": parm.Pilot_On,
						"PILOT_OFF": parm.Pilot_Off,
						"PILOT_AUTO": parm.Pilot_Unknown}
					pol = {"HORIZONTAL": parm.Polarisation_Horizontal,
						"CIRCULARRIGHT": parm.Polarisation_CircularRight,
						"CIRCULARLEFT": parm.Polarisation_CircularLeft,
						"VERTICAL": parm.Polarisation_Vertical}
					parm.orbital_position = self.orb_position
					parm.polarisation = pol[data[1]]
					parm.frequency = int(data[2])
					parm.symbol_rate = int(data[3])
					parm.system = sys[data[4]]
					parm.inversion = inv[data[5]]
					parm.pilot = pilot[data[6]]
					parm.fec = fec.get(data[7], eDVBFrontendParametersSatellite.FEC_Auto)
					parm.modulation = qam[data[8]]
					parm.rolloff = roll[data[9]]
					if parm.system == parm.System_DVB_S:
						data = data[:10] # "DVB-S" does not support MIS/PLS or T2MI so remove any values from the output of the binary file
					parm.pls_mode = getMisPlsValue(data, 10, eDVBFrontendParametersSatellite.PLS_Gold)
					parm.is_id = getMisPlsValue(data, 11, eDVBFrontendParametersSatellite.No_Stream_Id_Filter)
					parm.pls_code = getMisPlsValue(data, 12, 0)
					if hasattr(parm, "t2mi_plp_id"):
						parm.t2mi_plp_id = getMisPlsValue(data, 13, eDVBFrontendParametersSatellite.No_T2MI_PLP_Id)
					if hasattr(parm, "t2mi_pid"):
						parm.t2mi_pid = getMisPlsValue(data, 14, eDVBFrontendParametersSatellite.T2MI_Default_Pid)
                    # when blindscan returns 0,0,0 then use defaults...
					if parm.pls_mode == parm.is_id == parm.pls_code == 0:
						parm.pls_mode = eDVBFrontendParametersSatellite.PLS_Gold
						parm.is_id = eDVBFrontendParametersSatellite.No_Stream_Id_Filter
					# when blindscan returns root then switch to gold
					if parm.pls_mode == eDVBFrontendParametersSatellite.PLS_Root:
						parm.pls_mode = eDVBFrontendParametersSatellite.PLS_Gold
						parm.pls_code = root2gold(parm.pls_code)
					self.tmp_tplist.append(parm)
		self.blindscan_session.close(True)
		self.blindscan_session = None

	def blindscanContainerAvail(self, str):
		print("[Blindscan][blindscanContainerAvail]", str)
		self.full_data = self.full_data + str # TODO: is this the cause of the duplicates in blindscanContainerClose?
		if self.blindscan_session:
			if self.SundtekScan:
				data = str.split()
				if 'Scanning' in data:
					self.tp_found.append(str)
					seconds_done = int(time() - self.start_time)
					tmpstr = "\n" + str + _("Step %d %d:%02d min") % (len(self.tp_found), seconds_done / 60, seconds_done % 60)
					self.blindscan_session["progress"].setText(self.tmpstr + tmpstr)
				if len(data) >= 6 and data[0] == 'OK':
					self.blindscan_session["post_action"].setText(str)

	def blindscanSessionNone(self, *val):
		import time
		self.blindscan_container.sendCtrlC()
		self.blindscan_container = None
		time.sleep(2)

		self.blindscan_session = None
		self.releaseFrontend()

		if val[0] == False:
			self.tmp_tplist = []
			self.running_count = self.max_count

		self.is_runable = True

	def asyncBlindScan(self):
		self.bsTimer.stop()
		if not self.frontend:
			return
		print("[Blindscan][asyncBlindScan] closing frontend and starting blindscan")
		self.frontend.closeFrontend() # close because blindscan-s2 does not like to be open
		self.blindscan_container = eConsoleAppContainer()
		self.blindscan_container.appClosed.append(self.blindscanContainerClose)
		self.blindscan_container.dataAvail.append(self.blindscanContainerAvail)
		self.blindscan_container.execute(self.cmd)

	def blindscanSessionClose(self, *val):
		global XML_FILE
		self["key_yellow"].setText("")
		XML_FILE = None
		self["actions3"].setEnabled(False)

		self.blindscanSessionNone(val[0])

		if self.tmp_tplist is not None and self.tmp_tplist != []:
			if not self.SundtekScan:
				self.tmp_tplist = self.correctBugsCausedByDriver(self.tmp_tplist)

			# Sync with or remove transponders that exist in satellites.xml
			self.known_transponders = self.getKnownTransponders(self.orb_position)
			if config.blindscan.dont_scan_known_tps.value:
				self.tmp_tplist = self.removeKnownTransponders(self.tmp_tplist, self.known_transponders)
			elif not config.blindscan.disable_sync_with_known_tps.value:
				self.tmp_tplist = self.syncWithKnownTransponders(self.tmp_tplist, self.known_transponders)

			# Remove any duplicate transponders from tplist
			if not config.blindscan.disable_remove_duplicate_tps.value:
				self.tmp_tplist = self.removeDuplicateTransponders(self.tmp_tplist)

			# Filter off transponders on neighbouring satellites
			if int(config.blindscan.filter_off_adjacent_satellites.value):
				 self.tmp_tplist = self.filterOffAdjacentSatellites(self.tmp_tplist, self.orb_position, int(config.blindscan.filter_off_adjacent_satellites.value))

			# Process transponders still in list
			if self.tmp_tplist != []:
				if hasattr(eDVBFrontendParametersSatellite, "No_T2MI_PLP_Id"): # if image is T2MI capable
					self.tmp_tplist = sorted(self.tmp_tplist, key=lambda tp: (tp.frequency, tp.is_id, tp.pls_mode, tp.pls_code, tp.t2mi_plp_id))
				else: # if image is NOT T2MI capable
					self.tmp_tplist = sorted(self.tmp_tplist, key=lambda tp: (tp.frequency, tp.is_id, tp.pls_mode, tp.pls_code))
				blindscanStateList = []
				for p in self.tmp_tplist:
					print("[Blindscan][blindscanSessionClose] data: [%d][%d][%d][%d][%d][%d][%d][%d][%d][%d]" % (p.orbital_position, p.polarisation, p.frequency, p.symbol_rate, p.system, p.inversion, p.pilot, p.fec, p.modulation, p.modulation))

					pol = {p.Polarisation_Horizontal: "H",
						p.Polarisation_CircularRight: "R",
						p.Polarisation_CircularLeft: "L",
						p.Polarisation_Vertical: "V"}
					fec = {p.FEC_Auto: "Auto",
						p.FEC_1_2: "1/2",
						p.FEC_2_3: "2/3",
						p.FEC_3_4: "3/4",
						p.FEC_4_5: "4/5",
						p.FEC_5_6: "5/6",
						p.FEC_7_8: "7/8",
						p.FEC_8_9: "8/9",
						p.FEC_3_5: "3/5",
						p.FEC_9_10: "9/10",
						p.FEC_None: "None"}
					sys = {p.System_DVB_S: "DVB-S",
						p.System_DVB_S2: "DVB-S2"}
					qam = {p.Modulation_QPSK: "QPSK",
						p.Modulation_8PSK: "8PSK",
						p.Modulation_16APSK: "16APSK",
						p.Modulation_32APSK: "32APSK"}
					tp_str = "%g%s %d FEC %s %s %s" % (p.frequency / 1000.0, pol[p.polarisation], p.symbol_rate / 1000, fec[p.fec], sys[p.system], qam[p.modulation])
					if p.is_id > eDVBFrontendParametersSatellite.No_Stream_Id_Filter:
						tp_str += " MIS %d" % p.is_id
					if p.pls_code > 0:
						tp_str += " PLS Gold %d" % p.pls_code
					if hasattr(p, "t2mi_plp_id") and p.t2mi_plp_id > eDVBFrontendParametersSatellite.No_T2MI_PLP_Id:
						tp_str += " T2MI %d" % p.t2mi_plp_id
					if hasattr(p, "t2mi_pid") and hasattr(p, "t2mi_plp_id") and p.t2mi_plp_id > eDVBFrontendParametersSatellite.No_T2MI_PLP_Id:
						tp_str += " PID %d" % p.t2mi_pid
					blindscanStateList.append((tp_str, p))

				self.runtime = int(time() - self.start_time)
				xml_location = self.createSatellitesXMLfile(self.tmp_tplist, XML_BLINDSCAN_DIR)
				if config.blindscan.search_type.value == "services": # Do a service scan
					self.startScan(True, self.tmp_tplist)
				else: # Display results
					self.session.openWithCallback(self.startScan, BlindscanState, _("Search completed\n%d transponders found in %d:%02d minutes.\nDetails saved in: %s") % (len(self.tmp_tplist), self.runtime / 60, self.runtime % 60, xml_location), "", blindscanStateList, True)
			else:
				msg = _("No new transponders found! \n\nOnly transponders already listed in satellites.xml \nhave been found for those search parameters!")
				self.session.openWithCallback(self.callbackNone, MessageBox, msg, MessageBox.TYPE_INFO, timeout=60)

		else:
			msg = _("No transponders were found for those search parameters!")
			if val[0] == False:
				msg = _("The blindscan run was cancelled by the user.")
			self.session.openWithCallback(self.callbackNone, MessageBox, msg, MessageBox.TYPE_INFO, timeout=60)
			self.tmp_tplist = []

	def startScan(self, *retval):
		if retval[0] == False:
			return

		tlist = retval[1]
		networkid = 0
		flags = 0
		tmp = config.blindscan.clearallservices.value
		if tmp == "no":
			flags |= eComponentScan.scanDontRemoveUnscanned
		elif tmp == "yes":
			flags |= eComponentScan.scanRemoveServices
		elif tmp == "yes_hold_feeds":
			flags |= eComponentScan.scanRemoveServices
			flags |= eComponentScan.scanDontRemoveFeeds
		if config.blindscan.onlyFTA.value:
			flags |= eComponentScan.scanOnlyFree
		self.session.openWithCallback(self.startScanCallback, ServiceScan, [{"transponders": tlist, "feid": self.feid, "flags": flags, "networkid": networkid}])

	def correctBugsCausedByDriver(self, tplist):
		multiplier = 1000
		if self.is_c_band_scan: # for some reason a c-band scan (with a Vu+) returns the transponder frequencies in Ku band format so they have to be converted back to c-band numbers before the subsequent service search
			x = 0
			for transponders in tplist:
				if tplist[x].frequency > (self.c_band_freq_limits["high"] * multiplier):
					tplist[x].frequency = (self.c_band_lo_freq * multiplier) - (tplist[x].frequency - (self.universal_lo_freq["low"] * multiplier))
				x += 1
		elif self.user_defined_lnb_scan and self.adjust_freq:
			x = 0
			for transponders in tplist:
				if config.blindscan.user_defined_lnb_inversion.value:
					tplist[x].frequency = (self.user_defined_lnb_lo_freq * multiplier) - (tplist[x].frequency - (self.universal_lo_freq["low"] * multiplier)) # Flip it. Same as C-band
				else:
					tplist[x].frequency = tplist[x].frequency + ((self.user_defined_lnb_lo_freq - self.universal_lo_freq["low"]) * multiplier)
				x += 1

		x = 0
		for transponders in tplist:
			if tplist[x].system == 0: # convert DVB-S transponders to auto fec as for some reason the tuner incorrectly returns 3/4 FEC for all transmissions
				tplist[x].fec = 0
			if int(config.blindscan.polarization.value) == eDVBFrontendParametersSatellite.Polarisation_CircularRight: # Return circular transponders to correct polarisation
				tplist[x].polarisation = eDVBFrontendParametersSatellite.Polarisation_CircularRight
			elif int(config.blindscan.polarization.value) == eDVBFrontendParametersSatellite.Polarisation_CircularLeft: # Return circular transponders to correct polarisation
				tplist[x].polarisation = eDVBFrontendParametersSatellite.Polarisation_CircularLeft
			elif int(config.blindscan.polarization.value) == eDVBFrontendParametersSatellite.Polarisation_CircularRight + 2: # Return circular transponders to correct polarisation
				if tplist[x].polarisation == eDVBFrontendParametersSatellite.Polarisation_Horizontal: # Return circular transponders to correct polarisation
					tplist[x].polarisation = eDVBFrontendParametersSatellite.Polarisation_CircularLeft
				else:
					tplist[x].polarisation = eDVBFrontendParametersSatellite.Polarisation_CircularRight
			x += 1
		return tplist

	def dataIsGood(self, data): # check output of the binary for nonsense values
		lower_freq = self.thisRun[0]
		upper_freq = self.thisRun[1]
		high_band = self.thisRun[2]
		data_freq = int(int(data[2]) / 1000)
		data_symbol = int(data[3])
		lower_symbol = (config.blindscan.start_symbol.value * 1000000) - 200000
		upper_symbol = (config.blindscan.stop_symbol.value * 1000000) + 200000

		if high_band:
			data_if_freq = abs(data_freq - self.universal_lo_freq["high"])
		elif self.is_c_band_scan and data_freq > self.c_band_freq_limits["low"] - 1 and data_freq < self.c_band_freq_limits["high"] + 1:
			data_if_freq = abs(self.c_band_lo_freq - data_freq)
		elif self.user_defined_lnb_scan and not self.adjust_freq:
			data_if_freq = abs(data_freq - self.user_defined_lnb_lo_freq)
		else:
			data_if_freq = abs(data_freq - self.universal_lo_freq["low"])

		good = lower_freq <= data_if_freq <= upper_freq and lower_symbol <= data_symbol <= upper_symbol

		if not good:
			print("[Blindscan][dataIsGood] Data returned by the binary is not good...\n	Data: Frequency [%d], Symbol rate [%d]" % (int(data[2]), int(data[3])))

		return good

	def createSatellitesXMLfile(self, tp_list, save_xml_dir):
		pos = self.orb_position
		if pos > 1800:
			pos -= 3600
		if pos < 0:
			pos_name = '%dW' % (abs(int(pos)) / 10)
		else:
			pos_name = '%dE' % (abs(int(pos)) / 10)
		location = '%s/blindscan_%s_%s.xml' % (save_xml_dir, pos_name, strftime("%d-%m-%Y_%H-%M-%S"))
		tuner = nimmanager.nim_slots[self.feid].friendly_full_description
		polarisation = ['horizontal', 'vertical', 'circular left', 'circular right', 'vertical and horizontal', 'circular right and circular left']
		adjacent = ['no', 'up to 1 degree', 'up to 2 degrees', 'up to 3 degrees']
		known_txp = 'no'
		if config.blindscan.dont_scan_known_tps.value:
			known_txp = 'yes'
		xml = ['<?xml version="1.0" encoding="iso-8859-1"?>\n\n']
		xml.append('<!--\n')
		xml.append('	File created on %s\n' % (strftime("%A, %d of %B %Y, %H:%M:%S")))
		xml.append('	using %s receiver running Enigma2 image, version %s,\n' % (getBoxType(), about.getEnigmaVersionString()))
		xml.append('	build %s, with the blindscan plugin \n\n' % (about.getImageTypeString()))
		xml.append('	Search parameters:\n')
		xml.append('		%s\n' % (tuner))
		xml.append('		Satellite: %s\n' % (self.sat_name))
		xml.append('		Start frequency: %dMHz\n' % (self.blindscan_start_frequency))
		xml.append('		Stop frequency: %dMHz\n' % (self.blindscan_stop_frequency))
		xml.append('		Polarization: %s\n' % (polarisation[int(config.blindscan.polarization.value)]))
		xml.append('		Lower symbol rate: %d\n' % (config.blindscan.start_symbol.value * 1000))
		xml.append('		Upper symbol rate: %d\n' % (config.blindscan.stop_symbol.value * 1000))
		xml.append('		Only save unknown tranponders: %s\n' % (known_txp))
		xml.append('		Filter out adjacent satellites: %s\n' % (adjacent[int(config.blindscan.filter_off_adjacent_satellites.value)]))
		xml.append('		Scan duration: %d seconds\n' % (self.runtime))
		xml.append('-->\n\n')
		xml.append('<satellites>\n')
		xml.append('	<sat name="%s" flags="0" position="%s">\n' % (self.sat_name.replace('&', '&amp;'), self.orb_position))
		for tp in tp_list:
			tmp_tp = []
			tmp_tp.append('\t\t<transponder')
			tmp_tp.append('frequency="%d"' % tp.frequency)
			tmp_tp.append('symbol_rate="%d"' % tp.symbol_rate)
			tmp_tp.append('polarization="%d"' % tp.polarisation)
			tmp_tp.append('fec_inner="%d"' % tp.fec)
			tmp_tp.append('system="%d"' % tp.system)
			tmp_tp.append('modulation="%d"' % tp.modulation)
			if tp.is_id > eDVBFrontendParametersSatellite.No_Stream_Id_Filter:
				tmp_tp.append('is_id="%d"' % tp.is_id)
			if tp.pls_code > 0:
				tmp_tp.append('pls_mode="%d"' % tp.pls_mode)
				tmp_tp.append('pls_code="%d"' % tp.pls_code)
			if hasattr(tp, "t2mi_plp_id") and tp.t2mi_plp_id > eDVBFrontendParametersSatellite.No_T2MI_PLP_Id:
				tmp_tp.append('t2mi_plp_id="%d"' % tp.t2mi_plp_id)
				if hasattr(tp, "t2mi_pid") and tp.t2mi_plp_id < eDVBFrontendParametersSatellite.T2MI_Default_Pid:
					tmp_tp.append('t2mi_pid="%d"' % tp.t2mi_pid)
			tmp_tp.append('/>\n')
			xml.append(' '.join(tmp_tp))
		xml.append('	</sat>\n')
		xml.append('</satellites>\n')
		f = open(location, "w")
		f.writelines(xml)
		f.close()
		global XML_FILE
		self["key_yellow"].setText(_("Open xml file"))
		XML_FILE = location
		self["actions3"].setEnabled(True)
		return location

	def keyYellow(self):
		if XML_FILE and os.path.exists(XML_FILE):
			self.session.open(Console, _(XML_FILE), ["cat %s" % XML_FILE])

	def resetDefaults(self):
		for key in defaults.keys():
			getattr(config.blindscan, key).value = defaults[key]
		self.blindscan_Ku_band_start_frequency.value = self.Ku_band_freq_limits["low"]
		self.blindscan_Ku_band_stop_frequency.value = self.Ku_band_freq_limits["high"]
		self.blindscan_C_band_start_frequency.value = self.c_band_freq_limits["default_low"]
		self.blindscan_C_band_stop_frequency.value = self.c_band_freq_limits["default_high"]
		if self.user_defined_lnb_scan:
			self.blindscan_user_defined_lnb_start_frequency.value = self.user_defined_lnb_lo_freq + self.tunerIfLimits["low"]
			self.blindscan_user_defined_lnb_stop_frequency.value = self.user_defined_lnb_lo_freq + self.tunerIfLimits["high"]
			self.blindscan_user_defined_lnb_inverted_start_frequency.value = self.user_defined_lnb_lo_freq - self.tunerIfLimits["high"]
			self.blindscan_user_defined_lnb_inverted_stop_frequency.value = self.user_defined_lnb_lo_freq - self.tunerIfLimits["low"]
		self.createSetup()
		self.setBlueText()

	def setBlueText(self):
		if not self.SatBandCheck():
			self["key_blue"].setText("")
			return
		for key in defaults.keys():
			if getattr(config.blindscan, key).value != defaults[key]:
				self["key_blue"].setText(_("Restore defaults"))
				return
		if self.blindscan_Ku_band_start_frequency.value != self.Ku_band_freq_limits["low"] or \
			self.blindscan_Ku_band_stop_frequency.value != self.Ku_band_freq_limits["high"] or \
			self.blindscan_C_band_start_frequency.value != self.c_band_freq_limits["default_low"] or \
			self.blindscan_C_band_stop_frequency.value != self.c_band_freq_limits["default_high"] or \
			self.user_defined_lnb_scan and self.blindscan_user_defined_lnb_start_frequency.value != self.user_defined_lnb_lo_freq + self.tunerIfLimits["low"] or \
			self.user_defined_lnb_scan and self.blindscan_user_defined_lnb_stop_frequency.value != self.user_defined_lnb_lo_freq + self.tunerIfLimits["high"] or \
			self.user_defined_lnb_scan and self.blindscan_user_defined_lnb_inverted_start_frequency.value != self.user_defined_lnb_lo_freq - self.tunerIfLimits["high"] or \
			self.user_defined_lnb_scan and self.blindscan_user_defined_lnb_inverted_stop_frequency.value != self.user_defined_lnb_lo_freq - self.tunerIfLimits["low"]:
			self["key_blue"].setText(_("Restore defaults"))
		else:
			self["key_blue"].setText("")

	def SatBandCheck(self):
		# search for LNB type in Universal, C band, or user defined.
		cur_orb_pos = self.getOrbPos()
		self.is_c_band_scan = False
		self.is_Ku_band_scan = False
		self.user_defined_lnb_scan = False
		self.user_defined_lnb_lo_freq = 0
		self.suggestedPolarisation = _("vertical and horizontal")
		nim = nimmanager.nim_slots[int(self.scan_nims.value)]
		nimconfig = nim.config
		if nimconfig.configMode.getValue() == "equal":
			slotid = int(nimconfig.connectedTo.value)
			nim = nimmanager.nim_slots[slotid]
			nimconfig = nim.config
		if nimconfig.configMode.getValue() == "advanced":
			if nimconfig.advanced.sats.value in ("3605", "3606"):
				currSat = nimconfig.advanced.sat[int(nimconfig.advanced.sats.value)]
				import ast
				userSatellitesList = ast.literal_eval(currSat.userSatellitesList.getValue())
				if not cur_orb_pos in userSatellitesList:
					currSat = nimconfig.advanced.sat[cur_orb_pos]
			else:
				currSat = nimconfig.advanced.sat[cur_orb_pos]
			lnbnum = int(currSat.lnb.getValue())
			if lnbnum == 0 and nimconfig.advanced.sats.value in ("3601", "3602", "3603", "3604"):
				lnbnum = 65 + int(nimconfig.advanced.sats.value) - 3601
			currLnb = nimconfig.advanced.lnb[lnbnum]
			if isinstance(currLnb, ConfigNothing):
				return False
			lof = currLnb.lof.getValue()
			print("[Blindscan][isLNB] LNB type: ", lof)
			if lof == "universal_lnb":
				self.is_Ku_band_scan = True
				return True
			elif lof == "c_band":
				self.is_c_band_scan = True
				return True
			elif lof == "user_defined" and currLnb.lofl.value == currLnb.lofh.value and currLnb.lofl.value > 5000 and currLnb.lofl.value < 30000:
				if currLnb.lofl.value == self.circular_lnb_lo_freq and currLnb.lofh.value == self.circular_lnb_lo_freq and cur_orb_pos in (360, 560): # "circular_lnb" legacy support hack. For people using a "circular" LNB but that have their tuner set up as "user defined".
					self.user_defined_lnb_lo_freq = self.circular_lnb_lo_freq
					self.suggestedPolarisation = _("circular left/right")
				else: # normal "user_defined"
					self.user_defined_lnb_lo_freq = currLnb.lofl.value
				self.user_defined_lnb_scan = True
				print("[Blindscan][SatBandCheck] user defined local oscillator frequency: %d" % self.user_defined_lnb_lo_freq)
				return True
			elif lof == "circular_lnb": # lnb for use at positions 360 and 560
				self.user_defined_lnb_lo_freq = self.circular_lnb_lo_freq
				self.user_defined_lnb_scan = True
				self.suggestedPolarisation = _("circular left/right")
				return True
			return False # LNB type not supported by this plugin
		elif nimconfig.configMode.getValue() == "simple" and nimconfig.diseqcMode.value == "single" and cur_orb_pos in (360, 560) and nimconfig.simpleDiSEqCSetCircularLNB.value:
			self.user_defined_lnb_lo_freq = self.circular_lnb_lo_freq
			self.user_defined_lnb_scan = True
			self.suggestedPolarisation = _("circular left/right")
			return True
		elif nimconfig.configMode.getValue() == "simple":
			self.is_Ku_band_scan = True
			return True
		return False # LNB type not supported by this plugin

	def getOrbPos(self):
		try:
			idx_selected_sat = int(self.getSelectedSatIndex(self.scan_nims.value))
			tmp_list = [self.satList[int(self.scan_nims.value)][self.scan_satselection[idx_selected_sat].index]]
			orb = tmp_list[0][0]
			print("[Blindscan][getOrbPos] orb = ", orb)
		except:
			orb = -9999
			print("[Blind scan][getOrbPos] error parsing orb")
		return orb

	def startScanCallback(self, answer=True):
		if answer:
			self.releaseFrontend()
			self.session.nav.playService(self.session.postScanService)
			self.close(True)

	def startDishMovingIfRotorSat(self):
		self["rotorstatus"].setText("")
		orb_pos = self.getOrbPos()
		self.orb_pos = 0
		self.feid = int(self.scan_nims.value)
		rotorSatsForNim = nimmanager.getRotorSatListForNim(self.feid)
		if len(rotorSatsForNim) < 1:
			self.releaseFrontend() # stop dish if moving due to previous call
			return False
		rotorSat = False
		for sat in rotorSatsForNim:
			if sat[0] == orb_pos:
				rotorSat = True
				break
		if not rotorSat:
			self.releaseFrontend() # stop dish if moving due to previous call
			return False
		tps = nimmanager.getTransponders(orb_pos)
		if len(tps) < 1:
			return False
		if Lastrotorposition is not None and config.misc.lastrotorposition.value != 9999:
			text = _("Rotor: ") + self.OrbToStr(config.misc.lastrotorposition.value)
			self["rotorstatus"].setText(text)
		# freq, sr, pol, fec, inv, orb, sys, mod, roll, pilot, MIS, pls_mode, pls_code, t2mi
		transponder = (tps[0][1] / 1000, tps[0][2] / 1000, tps[0][3], tps[0][4], 2, orb_pos, tps[0][5], tps[0][6], tps[0][8], tps[0][9], eDVBFrontendParametersSatellite.No_Stream_Id_Filter, eDVBFrontendParametersSatellite.PLS_Gold, eDVBFrontendParametersSatellite.PLS_Default_Gold_Code, eDVBFrontendParametersSatellite.No_T2MI_PLP_Id, eDVBFrontendParametersSatellite.T2MI_Default_Pid)
		if not self.prepareFrontend():
			print("[Blindscan][startDishMovingIfRotorSat] self.prepareFrontend() failed")
			return False
		self.tuner.tune(transponder)
		self.orb_pos = orb_pos
		if Lastrotorposition is not None and config.misc.lastrotorposition.value != 9999:
			self.statusTimer.stop()
			self.startStatusTimer()
		return True

	def OrbToStr(self, orbpos):
		if orbpos > 1800:
			orbpos = 3600 - orbpos
			return "%d.%d\xc2\xb0 W" % (orbpos / 10, orbpos % 10)
		return "%d.%d\xc2\xb0 E" % (orbpos / 10, orbpos % 10)

	def setDishOrbosValue(self):
		if self.getRotorMovingState():
			if self.orb_pos != 0 and self.orb_pos != config.misc.lastrotorposition.value:
				config.misc.lastrotorposition.value = self.orb_pos
				config.misc.lastrotorposition.save()
			text = _("Moving to ") + self.OrbToStr(self.orb_pos)
			self.startStatusTimer()
		else:
			text = _("Rotor: ") + self.OrbToStr(config.misc.lastrotorposition.value)
		self["rotorstatus"].setText(text)

	def startStatusTimer(self):
		self.statusTimer.start(1000, True)

	def getRotorMovingState(self):
		return eDVBSatelliteEquipmentControl.getInstance().isRotorMoving()

	def releaseFrontend(self):
		if hasattr(self, 'frontend'):
			del self.frontend
			self.frontend = None
		if hasattr(self, 'raw_channel'):
			del self.raw_channel


def BlindscanCallback(close, answer):
	if close and answer:
		close(True)


def BlindscanMain(session, close=None, **kwargs):
	have_Support_Blindscan = False
	if nimmanager.hasNimType("DVB-S"):
		for n in nimmanager.nim_slots:
			if n.canBeCompatible("DVB-S") and n.description.startswith("Si216"):
				have_Support_Blindscan = True
				break
	if not have_Support_Blindscan:
		try:
			if 'Supports_Blind_Scan: yes' in open('/proc/bus/nim_sockets').read():
				have_Support_Blindscan = True
		except:
			pass
	if have_Support_Blindscan or BOX_MODEL == "dreambox":
		menu = [(_("Utility from the manufacturer"), "manufacturer"), (_("Hardware type"), "hardware")]
		def scanType(choice):
			if choice:
				if choice[1] == "manufacturer":
					session.openWithCallback(boundFunction(BlindscanCallback, close), Blindscan)
				elif choice[1] == "hardware":
					from . import dmmBlindScan
					session.openWithCallback(boundFunction(BlindscanCallback, close), dmmBlindScan.DmmBlindscan)
		session.openWithCallback(scanType, ChoiceBox, title=_("Select type for scan:"), list=menu)
	else:
		session.openWithCallback(boundFunction(BlindscanCallback, close), Blindscan)


def BlindscanSetup(menuid, **kwargs):
	if menuid == "scan":
		return [(_("Satellite blind scan"), BlindscanMain, "blindscan", 50)]
	else:
		return []


def Plugins(**kwargs):
	if nimmanager.hasNimType("DVB-S"):
		for n in nimmanager.nim_slots:
			if n.canBeCompatible("DVB-S") and n.description not in _unsupportedNims: # DVB-S NIMs without blindscan hardware or software
				return PluginDescriptor(name=_("Blind scan"), description=_("Scan satellites for new transponders"), where=PluginDescriptor.WHERE_MENU, fnc=BlindscanSetup)
	return []
