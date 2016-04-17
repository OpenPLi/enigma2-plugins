# for localized messages
from . import _

from Plugins.Plugin import PluginDescriptor
from Tools.Directories import fileExists
from Tools.HardwareInfo import HardwareInfo
from Screens.Screen import Screen
from Screens.ServiceScan import ServiceScan
from Screens.MessageBox import MessageBox
from Screens.Console import Console
from Components.Label import Label
from Components.TuneTest import Tuner
from Screens.ChoiceBox import ChoiceBox
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.ActionMap import NumberActionMap, ActionMap
from Components.NimManager import nimmanager, getConfigSatlist
from Components.config import config, ConfigSubsection, ConfigSelection, ConfigYesNo, ConfigInteger, getConfigListEntry
from enigma import eTimer, eDVBFrontendParametersSatellite, eComponentScan, eConsoleAppContainer, eDVBResourceManager, getBoxType, eDVBSatelliteEquipmentControl
from Components.About import about
from time import strftime, time
import os
import dmmBlindScan

BOX_MODEL = "none"
BOX_NAME = ""
if fileExists("/proc/stb/info/boxtype"):
	try:
		l = open("/proc/stb/info/boxtype")
		model = l.read().strip()
		l.close()
		BOX_NAME = str(model.lower())
		l.close()
		if BOX_NAME.startswith('et'):
			BOX_MODEL = "xtrend"
		elif BOX_NAME.startswith('xp'):
			BOX_MODEL = "xp"
		elif BOX_NAME.startswith('formuler'):
			BOX_MODEL = "formuler"
		elif BOX_NAME.startswith('hd'):
			BOX_MODEL = "hd"
		elif BOX_NAME.startswith('osmini'):
			BOX_MODEL = "edision"
		else:
			BOX_MODEL = "useBoxtype"
	except:
		pass
elif fileExists("/proc/stb/info/vumodel"):
	try:
		l = open("/proc/stb/info/vumodel")
		model = l.read().strip()
		l.close()
		BOX_NAME = str(model.lower())
		l.close()
		BOX_MODEL = "vuplus"
	except:
		pass
elif HardwareInfo().get_device_name().startswith('dm') and fileExists("/proc/stb/info/model"):
	try:
		l = open("/proc/stb/info/model")
		model = l.read()
		l.close()
		BOX_NAME = str(model.lower())
		l.close()
		if BOX_NAME.startswith('dm'):
			BOX_MODEL = "dreambox"
	except:
		pass

#used for blindscan-s2
def getAdapterFrontend(frontend, description):
	for adapter in range(1,5):
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

_supportNimType = { 'AVL1208':'', 'AVL6222':'6222_', 'AVL6211':'6211_', 'BCM7356':'bcm7346_'}

# For STBs that support multiple DVB-S tuner models, e.g. Solo 4K.
_unsupportedNims = ( 'Vuplus DVB-S NIM(7376 FBC)', ) # format = nim.description from nimmanager

# blindscan-s2 supported tuners
_blindscans2Nims = ('TBS-5925', 'DVBS2BOX')

class Blindscan(ConfigListScreen, Screen):
	skin="""
		<screen position="center,center" size="640,565" title="Blind scan">
			<widget name="rotorstatus" position="5,5" size="550,25" font="Regular;20" foregroundColor="#00ffc000" />
			<widget name="config" position="5,30" size="630,330" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,365" zPosition="1" size="640,2" />
			<widget name="description" position="5,370" size="630,125" font="Regular;20" foregroundColor="#00ffc000" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,495" zPosition="1" size="640,2" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/Blindscan/images/red.png" position="0,560" size="160,2" alphatest="on" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/Blindscan/images/green.png" position="160,560" size="160,2" alphatest="on" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/Blindscan/images/yellow.png" position="320,560" size="160,2" alphatest="on" />
			<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/Blindscan/images/blue.png" position="480,560" size="160,2" alphatest="on" />
			<widget name="red" position="0,530" zPosition="2" size="160,20" font="Regular;18" halign="center" valign="center" backgroundColor="background" foregroundColor="white" transparent="1" />
			<widget name="green" position="160,530" zPosition="2" size="160,20" font="Regular;18" halign="center" valign="center" backgroundColor="background" foregroundColor="white" transparent="1" />
			<widget name="yellow" position="320,530" zPosition="2" size="160,20" font="Regular;18" halign="center" valign="center" backgroundColor="background" foregroundColor="white" transparent="1" />
			<widget name="blue" position="480,530" zPosition="2" size="160,20" font="Regular;18" halign="center" valign="center" backgroundColor="background" foregroundColor="white" transparent="1" />
			<widget name="introduction" position="0,500" size="640,20" font="Regular;18" foregroundColor="green" halign="center" />
		</screen>
		"""
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setup_title = _("Blind scan for DVB-S2 tuners")
		Screen.setTitle(self, _(self.setup_title))
		self.skinName = "Blindscan"
		try:
			self.session.postScanService = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		except:
			self.session.postScanService = self.session.nav.getCurrentlyPlayingServiceReference()
		self.onChangedEntry = [ ]
		self["description"] = Label("")
		self["rotorstatus"] = Label("")
		self.getCurrentTuner = None
		self.w_scan = False
		self.SundtekScan = False
		self.blindscan_session = None
		self.is_circular_band_scan = False
		self.is_c_band_scan = False
		self.tmpstr = ""
		self.Sundtek_pol = ""
		self.offset = 0
		self.start_time = time()
		self.orb_pos = 0
		# update sat list
		self.satList = []
		for slot in nimmanager.nim_slots:
			if slot.isCompatible("DVB-S"):
				self.satList.append(nimmanager.getSatListForNim(slot.slot))
			else:
				self.satList.append(None)
		self.statusTimer = eTimer()
		self.statusTimer.callback.append(self.setDishOrbosValue)
		# make config
		self.createConfig()
		self.list = []

		# run command
		self.cmd = ""
		self.bsTimer = eTimer()
		self.bsTimer.callback.append(self.asyncBlindScan)

		ConfigListScreen.__init__(self, self.list, session = session, on_change = self.changedEntry)
		if self.scan_nims.value != None and self.scan_nims.value != "" :
			self["actions"] = ActionMap(["ColorActions", "SetupActions", 'DirectionActions'],
			{
				"red": self.keyCancel,
				"green": self.keyGo,
				"yellow": self.keyYellow,
				"blue": self.keyBlue,
				"ok": self.keyGo,
				"cancel": self.keyCancel,
			}, -2)
			self["red"] = Label(_("Exit"))
			self["yellow"] = Label("")
			self["green"] = Label(_("Start scan"))
			self["blue"] = Label("")
			self["introduction"] = Label("")
			self.createSetup()
			self.keyBlue()
		else :
			self["actions"] = ActionMap(["ColorActions", "SetupActions", 'DirectionActions'],
			{
				"red": self.keyCancel,
				"green": self.keyNone,
				"yellow": self.keyNone,
				"blue": self.keyNone,
				"ok": self.keyNone,

				"cancel": self.keyCancel,
			}, -2)
			self["red"] = Label(_("Exit"))
			self["yellow"] = Label("")
			self["green"] = Label("")
			self["blue"] = Label("")
			self["introduction"] = Label(_("Please setup your tuner configuration."))

		self.i2c_mapping_table = None
		self.nimSockets = self.ScanNimsocket()
		self.makeNimSocket()
		self["config"].onSelectionChanged.append(self.textHelp)
		if XML_FILE is not None and os.path.exists(XML_FILE):
			self["yellow"].setText(_("Open xml file"))
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

	def getCurrentDescription(self):
		return self["config"].getCurrent() and len(self["config"].getCurrent()) > 2 and self["config"].getCurrent()[2] or ""

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary

	def ScanNimsocket(self, filepath = '/proc/bus/nim_sockets'):
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
				try:    sNo = line.split()[2][:-1]
				except:	sNo = -1
			elif line.startswith('I2C_Device:'):
				try:    sI2C = line.split()[1]
				except: sI2C = -1
			elif line.startswith('Name:'):
				splitLines = line.split()
				try:
					if splitLines[1].startswith('BCM'):
						sName = splitLines[1]
					else:
						sName = splitLines[3][4:-1]
				except: sName = ""
			if sNo >= 0 and sName != "":
				if sName.startswith('BCM'):
					sI2C = sNo
				if sI2C != -1:
					_nimSocket[sNo] = [sName, sI2C]
				else:	_nimSocket[sNo] = [sName]
		fp.close()
		print "[Blind scan] parsed nimsocket :", _nimSocket
		return _nimSocket

	def makeNimSocket(self, nimname=""):
		is_exist_i2c = False
		self.i2c_mapping_table = {0:2, 1:3, 2:1, 3:0}
		if self.nimSockets is not None:
			for XX in self.nimSockets.keys():
				nimsocket = self.nimSockets[XX]
				if len(nimsocket) > 1:
					try:	self.i2c_mapping_table[int(XX)] = int(nimsocket[1])
					except: continue
					is_exist_i2c = True
		print "[Blind scan] i2c_mapping_table :", self.i2c_mapping_table, ", is_exist_i2c :", is_exist_i2c
		if is_exist_i2c: return

		if nimname == "AVL6222":
			if BOX_NAME == "uno":
				self.i2c_mapping_table = {0:3, 1:3, 2:1, 3:0}
			elif BOX_NAME == "duo2":
				nimdata = self.nimSockets['0']
				try:
					if nimdata[0] == "AVL6222":
						self.i2c_mapping_table = {0:2, 1:2, 2:4, 3:4}
					else:	self.i2c_mapping_table = {0:2, 1:4, 2:4, 3:0}
				except: self.i2c_mapping_table = {0:2, 1:4, 2:4, 3:0}
			else:	self.i2c_mapping_table = {0:2, 1:4, 2:0, 3:0}
		else:	self.i2c_mapping_table = {0:2, 1:3, 2:1, 3:0}

	def getNimSocket(self, slot_number, usb=False):
		if not usb and (slot_number < 0 or slot_number > 3):
			return -1
		return self.i2c_mapping_table.get(slot_number, -1)

	def keyNone(self):
		None

	def callbackNone(self, *retval):
		None

	def keyBlue(self):
		self["introduction"].setText(_("Press Green/OK to start the scan"))

		#TODO add W scan support
		#text0 = _("Manufacturer")
		#text1 = _("W scan")
		#if not self.w_scan:
		#	self.w_scan = True
		#	text = text0
		#else:
		#	text = text1
		#	self.w_scan = False
		#self["blue"].setText(text)
		#new_text = self.w_scan and text1 or text0
		#self["introduction"].setText(_("Press Green/OK to start the scan") + "(" + new_text + _(" mode)."))

	def openFrontend(self):
		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			self.raw_channel = res_mgr.allocateRawChannel(self.feid)
			if self.raw_channel:
				self.frontend = self.raw_channel.getFrontend()
				if self.frontend:
					return True
				else:
					print "[Blind scan] getFrontend failed"
			else:
				print "[Blind scan] getRawChannel failed"
		else:
			print "[Blind scan] getResourceManager instance failed"
		return False

	def prepareFrontend(self):
		self.releaseFrontend()
		if not self.openFrontend():
			oldref = self.session.nav.getCurrentlyPlayingServiceReference()
			stop_current_service = True
			if oldref and self.getCurrentTuner is not None:
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
		if self.frontend == None :
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

		self.scan_sat = ConfigSubsection()
		self.scan_networkScan = ConfigYesNo(default = False)

		self.blindscan_Ku_band_start_frequency = ConfigInteger(default = 10700, limits = (10700, 12749))
		self.blindscan_Ku_band_stop_frequency = ConfigInteger(default = 12750, limits = (10701, 12750))
		self.blindscan_C_band_start_frequency = ConfigInteger(default = 3600, limits = (3000, 4199))
		self.blindscan_C_band_stop_frequency = ConfigInteger(default = 4200, limits = (3001, 4200))
		self.blindscan_start_symbol = ConfigInteger(default = 2, limits = (1, 44))
		self.blindscan_stop_symbol = ConfigInteger(default = 45, limits = (2, 45))
		self.scan_clearallservices = ConfigSelection(default = "no", choices = [("no", _("no")), ("yes", _("yes")), ("yes_hold_feeds", _("yes (keep feeds)"))])
		self.scan_onlyfree = ConfigYesNo(default = False)
		self.dont_scan_known_tps = ConfigYesNo(default = False)
		self.filter_off_adjacent_satellites = ConfigSelection(default = 0, choices = [
			(0, _("no")),
			(1, _("up to 1 degree")),
			(2, _("up to 2 degrees")),
			(3, _("up to 3 degrees"))])
		self.search_type = ConfigSelection(default = 0, choices = [
			(0, _("scan for channels")),
			(1, _("save to XML file"))])

		# collect all nims which are *not* set to "nothing"
		nim_list = []
		for n in nimmanager.nim_slots:
			if hasattr(n, 'isFBCLink') and n.isFBCLink():
				continue
			if n.isCompatible("DVB-S") and n.description in _unsupportedNims: # DVB-S NIMs without blindscan hardware or software
 				continue
			if n.config_mode == "nothing":
				continue
			if n.isCompatible("DVB-S") and len(nimmanager.getSatListForNim(n.slot)) < 1:
				if n.config_mode in ("advanced", "simple"):
					config.Nims[n.slot].configMode.value = "nothing"
					config.Nims[n.slot].configMode.save()
				continue
			if n.config_mode in ("loopthrough", "satposdepends"):
				root_id = nimmanager.sec.getRoot(n.slot_id, int(n.config.connectedTo.value))
				if n.type == nimmanager.nim_slots[root_id].type: # check if connected from a DVB-S to DVB-S2 Nim or vice versa
					continue
			if n.isCompatible("DVB-S"):
				nim_list.append((str(n.slot), n.friendly_full_description))
		self.scan_nims = ConfigSelection(choices = nim_list)

		# sat
		self.scan_sat.frequency = ConfigInteger(default = defaultSat["frequency"], limits = (1, 99999))
		self.scan_sat.polarization = ConfigSelection(default = eDVBFrontendParametersSatellite.Polarisation_CircularRight + 1, choices = [
			(eDVBFrontendParametersSatellite.Polarisation_CircularRight + 1, _("vertical and horizontal")),
			(eDVBFrontendParametersSatellite.Polarisation_Vertical, _("vertical")),
			(eDVBFrontendParametersSatellite.Polarisation_Horizontal, _("horizontal")),
			(eDVBFrontendParametersSatellite.Polarisation_CircularRight + 2, _("circular right and circular left")),
			(eDVBFrontendParametersSatellite.Polarisation_CircularRight, _("circular right")),
			(eDVBFrontendParametersSatellite.Polarisation_CircularLeft, _("circular left"))])

		self.scan_satselection = []
		for slot in nimmanager.nim_slots:
			if slot.isCompatible("DVB-S"):
				self.scan_satselection.append(getConfigSatlist(defaultSat["orbpos"], self.satList[slot.slot]))
		self.frontend = None # set for later use
		return True

	def getSelectedSatIndex(self, v):
		index    = 0
		none_cnt = 0
		for n in self.satList:
			if self.satList[index] == None:
				none_cnt = none_cnt + 1
			if index == int(v):
				return (index-none_cnt)
			index = index + 1
		return -1

	def createSetup(self):
		self.list = []
		self.multiscanlist = []
		if self.scan_nims == []:
			return
		index_to_scan = int(self.scan_nims.value)
		print "[Blind scan] ID: ", index_to_scan
		nim = nimmanager.nim_slots[index_to_scan]
		nimname = nim.friendly_full_description
		self.SundtekScan = "Sundtek DVB-S/S2" in nimname and "V" in nimname
		warning_text = ""
		if "Sundtek" not in nimname and getBoxType().startswith('et') or getBoxType().startswith('vu'):
			warning_text = _("\nWARNING! Blind scan may make the tuner malfunction on a VU+ and ET receiver. A reboot afterwards may be required to return to proper tuner function.")
			if getBoxType().startswith('vu') and "AVL6222" in nimname:
				warning_text = _("\nSecond slot dual tuner may not be supported blind scan.")
		self.tunerEntry = getConfigListEntry(_("Tuner"), self.scan_nims,(_("Select a tuner that is configured for the satellite you wish to search") + warning_text))
		self.list.append(self.tunerEntry)
		self.scan_networkScan.value = False
		if nim.isCompatible("DVB-S") : 
			self.satelliteEntry = getConfigListEntry(_('Satellite'), self.scan_satselection[self.getSelectedSatIndex(index_to_scan)],_('Select the satellite you wish to search'))
			self.searchtypeEntry = getConfigListEntry(_("Search type"), self.search_type,_('"channel scan" searches for channels and saves them to your receiver; "save to XML file" does a transponder search and saves found transponders to an XML file in satellites.xml format'))
			self.list.append(self.satelliteEntry)
			self.SatBandCheck()
			if self.is_c_band_scan :
				self.list.append(getConfigListEntry(_('Scan start frequency'), self.blindscan_C_band_start_frequency,_('Frequency values must be between 3000 MHz and 4199 MHz (C-band)')))
				self.list.append(getConfigListEntry(_('Scan stop frequency'), self.blindscan_C_band_stop_frequency,_('Frequency values must be between 3001 MHz and 4200 MHz (C-band)')))
			else:
				self.list.append(getConfigListEntry(_('Scan start frequency'), self.blindscan_Ku_band_start_frequency,_('Frequency values must be between 10700 MHz and 12749 MHz')))
				self.list.append(getConfigListEntry(_('Scan stop frequency'), self.blindscan_Ku_band_stop_frequency,_('Frequency values must be between 10701 MHz and 12750 MHz')))
			polarisation_text = _("The suggested polarisation for this satellite is '%s'") % self.suggestedPolarisation
			self.list.append(getConfigListEntry(_("Polarisation"), self.scan_sat.polarization, polarisation_text))
			self.list.append(getConfigListEntry(_('Scan start symbolrate'), self.blindscan_start_symbol,_('Symbol rate values are in megasymbols; enter a value between 1 and 44')))
			self.list.append(getConfigListEntry(_('Scan stop symbolrate'), self.blindscan_stop_symbol,_('Symbol rate values are in megasymbols; enter a value between 2 and 45')))
			self.list.append(getConfigListEntry(_("Only scan unknown transponders"), self.dont_scan_known_tps,_('If you select "yes" the scan will only search transponders not listed in satellites.xml')))
			self.list.append(getConfigListEntry(_("Filter out adjacent satellites"), self.filter_off_adjacent_satellites,_('When a neighbouring satellite is very strong this avoids searching transponders known to be coming from the neighbouring satellite')))
			self.list.append(self.searchtypeEntry)
			if self.search_type.value == 0:
				self.list.append(getConfigListEntry(_("Network scan"), self.scan_networkScan, _('If you select "yes" in addition to scan transponders list the NIT (Network Information Table; contains all the info of a provider) is being read and the channels being advertised in there are stored in your tuner.')))
				self.list.append(getConfigListEntry(_("Clear before scan"), self.scan_clearallservices,_('If you select "yes" all channels on the satellite being search will be deleted before starting the current search, yes (keep feeds) means the same but hold all feed services/transponders.')))
				self.list.append(getConfigListEntry(_("Only free scan"), self.scan_onlyfree,_('If you select "yes" the scan will only save channels that are not encrypted; "no" will find encrypted and non-encrypted channels')))
			self["config"].list = self.list
			self["config"].l.setList(self.list)
			self.startDishMovingIfRotorSat()

	def newConfig(self):
		cur = self["config"].getCurrent()
		if cur and (cur == self.tunerEntry or cur == self.satelliteEntry or cur == self.searchtypeEntry):
			self.createSetup()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

	def keyCancel(self):
		self.releaseFrontend()
		self.session.nav.playService(self.session.postScanService)
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyGo(self):
		self.start_time = time()
		self.tp_found = []

		tab_pol = {
			eDVBFrontendParametersSatellite.Polarisation_Horizontal : "horizontal",
			eDVBFrontendParametersSatellite.Polarisation_Vertical : "vertical",
			eDVBFrontendParametersSatellite.Polarisation_CircularLeft : "circular left",
			eDVBFrontendParametersSatellite.Polarisation_CircularRight : "circular right",
			eDVBFrontendParametersSatellite.Polarisation_CircularRight + 1 : "horizontal and vertical",
			eDVBFrontendParametersSatellite.Polarisation_CircularRight + 2 : "circular left and circular right"
		}

		self.tmp_tplist=[]
		tmp_pol = []
		tmp_band = []
		idx_selected_sat = int(self.getSelectedSatIndex(self.scan_nims.value))
		tmp_list=[self.satList[int(self.scan_nims.value)][self.scan_satselection[idx_selected_sat].index]]

		if self.is_c_band_scan :
			self.blindscan_start_frequency = self.blindscan_C_band_start_frequency
			self.blindscan_stop_frequency = self.blindscan_C_band_stop_frequency
		else :
			self.blindscan_start_frequency = self.blindscan_Ku_band_start_frequency
			self.blindscan_stop_frequency = self.blindscan_Ku_band_stop_frequency
		
		# swap start and stop values if entered the wrong way round
		if self.blindscan_start_frequency.value > self.blindscan_stop_frequency.value :
			temp = self.blindscan_stop_frequency.value 
			self.blindscan_stop_frequency.value = self.blindscan_start_frequency.value
			self.blindscan_start_frequency.value = temp
			del temp

		# swap start and stop values if entered the wrong way round
		if self.blindscan_start_symbol.value > self.blindscan_stop_symbol.value :
			temp = self.blindscan_stop_symbol.value 
			self.blindscan_stop_symbol.value = self.blindscan_start_symbol.value
			self.blindscan_start_symbol.value = temp
			del temp

		uni_lnb_cutoff = 11700
		if self.blindscan_start_frequency.value < uni_lnb_cutoff and self.blindscan_stop_frequency.value > uni_lnb_cutoff :
			tmp_band=["low","high"]
		elif self.blindscan_start_frequency.value < uni_lnb_cutoff :
			tmp_band=["low"]
		else :
			tmp_band=["high"]

		if self.scan_sat.polarization.value >  eDVBFrontendParametersSatellite.Polarisation_CircularRight : # must be searching both polarisations, either V and H, or R and L
			tmp_pol=["vertical", "horizontal"]
		elif self.scan_sat.polarization.value ==  eDVBFrontendParametersSatellite.Polarisation_CircularRight :
			tmp_pol=["vertical"]
		elif self.scan_sat.polarization.value ==  eDVBFrontendParametersSatellite.Polarisation_CircularLeft :
			tmp_pol=["horizontal"]
		else:
			tmp_pol=[tab_pol[self.scan_sat.polarization.value]]

		self.doRun(tmp_list, tmp_pol, tmp_band)

	def doRun(self, tmp_list, tmp_pol, tmp_band):
		def GetCommand(nimIdx):
			_nimSocket = self.nimSockets
			try:
				sName = _nimSocket[str(nimIdx)][0]
				sType = _supportNimType[sName]
				return "vuplus_%(TYPE)sblindscan"%{'TYPE':sType}, sName
			except: pass
			return "vuplus_blindscan", ""
		if BOX_MODEL.startswith('vu'):
			self.binName,nimName =  GetCommand(self.scan_nims.value)

			self.makeNimSocket(nimName)
			if self.binName is None:
				self.session.open(MessageBox, _("Blindscan is not supported in ") + nimName + _(" tuner."), MessageBox.TYPE_ERROR)
				print "[Blind scan]" + nimName + " does not support blindscan."
				return

		self.full_data = ""
		self.total_list=[]
		for x in tmp_list:
			for y in tmp_pol:
				for z in tmp_band:
					self.total_list.append([x,y,z])
					print "[Blind scan] add scan item : ", x, ", ", y, ", ", z

		self.max_count = len(self.total_list)
		self.is_runable = True
		self.running_count = 0
		self.clockTimer = eTimer()
		self.clockTimer.callback.append(self.doClock)
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
		is_scan = False
		if self.is_runable :
			if self.running_count >= self.max_count:
				self.clockTimer.stop()
				del self.clockTimer
				self.clockTimer = None
				print "[Blind scan] Done"
				return
			orb = self.total_list[self.running_count][0]
			pol = self.total_list[self.running_count][1]
			band = self.total_list[self.running_count][2]
			self.running_count = self.running_count + 1
			print "[Blind scan] running status-[%d] : [%d][%s][%s]" %(self.running_count, orb[0], pol, band)
			if self.running_count == self.max_count:
				is_scan = True
			self.prepareScanData(orb, pol, band, is_scan)

	def prepareScanData(self, orb, pol, band, is_scan):
		self.is_runable = False
		self.orb_position = orb[0]
		self.sat_name = orb[1]
		self.feid = int(self.scan_nims.value)
		tab_hilow = {"high" : 1, "low" : 0}
		tab_pol = {
			"horizontal" : eDVBFrontendParametersSatellite.Polarisation_Horizontal,
			"vertical" : eDVBFrontendParametersSatellite.Polarisation_Vertical,
			"circular left" : eDVBFrontendParametersSatellite.Polarisation_CircularLeft,
			"circular right" : eDVBFrontendParametersSatellite.Polarisation_CircularRight
		}

		returnvalue = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

		if not self.prepareFrontend():
			return False

		if self.is_c_band_scan :
			self.scan_sat.frequency.value = 3600
		else:
			if tab_hilow[band]:
				self.scan_sat.frequency.value = 12515
			else:
				self.scan_sat.frequency.value = 11015
		returnvalue = (self.scan_sat.frequency.value,
					 0,
					 tab_pol[pol],
					 0,
					 0,
					 orb[0],
					 eDVBFrontendParametersSatellite.System_DVB_S,
					 0,
					 0,
					 0)
		self.tuner.tune(returnvalue)

		nim = nimmanager.nim_slots[self.feid]
		nimname = nim.friendly_full_description
		tunername = nim.description

		if ("Sundtek" not in nimname or tunername not in _blindscans2Nims) and self.getNimSocket(self.feid) < 0:
			print "[Blind scan] can't find i2c number!!"
			return

		c_band_loc_osc = 5150
		uni_lnb_loc_osc = {"high" : 10600, "low" : 9750}
		uni_lnb_cutoff = 11700
		if self.is_c_band_scan :
			temp_start_int_freq = c_band_loc_osc - self.blindscan_stop_frequency.value
			temp_end_int_freq = c_band_loc_osc - self.blindscan_start_frequency.value
			status_box_start_freq = c_band_loc_osc - temp_end_int_freq
			status_box_end_freq = c_band_loc_osc - temp_start_int_freq

		else:
			if tab_hilow[band] :
				if self.blindscan_start_frequency.value < uni_lnb_cutoff :
					temp_start_int_freq = uni_lnb_cutoff - uni_lnb_loc_osc[band]
				else:
					temp_start_int_freq = self.blindscan_start_frequency.value - uni_lnb_loc_osc[band]
				temp_end_int_freq = self.blindscan_stop_frequency.value - uni_lnb_loc_osc[band]
			else:
				if self.blindscan_stop_frequency.value > uni_lnb_cutoff :
					temp_end_int_freq = uni_lnb_cutoff - uni_lnb_loc_osc[band]
				else:
					temp_end_int_freq = self.blindscan_stop_frequency.value - uni_lnb_loc_osc[band]
				temp_start_int_freq = self.blindscan_start_frequency.value - uni_lnb_loc_osc[band]
			status_box_start_freq = temp_start_int_freq + uni_lnb_loc_osc[band]
			status_box_end_freq = temp_end_int_freq + uni_lnb_loc_osc[band]

		cmd = ""
		self.cmd = ""
		self.tmpstr = ""
		not_support_text = _("It seems manufacturer does not support blind scan for this tuner.")

		if tunername in _blindscans2Nims:
			cmd = "blindscan-s2 -b -s %d -e %d" % (temp_start_int_freq, temp_end_int_freq)
			cmd += getAdapterFrontend(self.feid, tunername)
			if pol == "horizontal":
				cmd += " -H"
			elif pol == "vertical":
				cmd += " -V"
			if self.is_c_band_scan:
				cmd += " -l 5150" # needs testing
			elif tab_hilow[band]:
				cmd += " -l 10600 -2" # on high band enable 22KHz tone
			else:
				cmd += " -l 9750"
			#self.frontend.closeFrontend() # close because blindscan-s2 does not like to be open
			self.cmd = cmd
			self.bsTimer.stop()
			self.bsTimer.start(6000, True)
		elif self.SundtekScan:
			tools = "/opt/bin/mediaclient"
			if os.path.exists(tools):
				cmd = "%s --blindscan %d" % (tools, self.feid)
				if self.is_c_band_scan:
					cmd += " --band c"
			else:
				self.session.open(MessageBox, _("Not found blind scan utility '%s'!") % tools, MessageBox.TYPE_ERROR)
				return
		elif BOX_MODEL.startswith('vu'):
			if BOX_NAME == "uno" or BOX_NAME == "duo2" or BOX_NAME == "solo2" or BOX_NAME == "solose" or BOX_NAME == "ultimo" or BOX_NAME == "solo4k":
				tools = "/usr/bin/%s" % self.binName
				if os.path.exists(tools):
					try:
						cmd = "%s %d %d %d %d %d %d %d %d" % (self.binName, temp_start_int_freq, temp_end_int_freq, self.blindscan_start_symbol.value, self.blindscan_stop_symbol.value, tab_pol[pol], tab_hilow[band], self.feid, self.getNimSocket(self.feid))
					except:
						self.session.open(MessageBox, _("Scan unknown error!"), MessageBox.TYPE_ERROR)
						return
				else:
					self.session.open(MessageBox, _("Not found blind scan utility '%s'!") % tools, MessageBox.TYPE_ERROR)
					return
			else:
				self.session.open(MessageBox, not_support_text, MessageBox.TYPE_WARNING)
				return
		elif BOX_MODEL.startswith('xtrend'):
			if BOX_NAME.startswith("et9") or BOX_NAME.startswith("et6") or BOX_NAME.startswith("et5"):
				tools = "/usr/bin/avl_xtrend_blindscan"
				if os.path.exists(tools):
					cmd = "avl_xtrend_blindscan %d %d %d %d %d %d %d %d" % (temp_start_int_freq, temp_end_int_freq, self.blindscan_start_symbol.value, self.blindscan_stop_symbol.value, tab_pol[pol], tab_hilow[band], self.feid, self.getNimSocket(self.feid)) # commented out by Huevos cmd = "avl_xtrend_blindscan %d %d %d %d %d %d %d %d" % (self.blindscan_start_frequency.value/1000000, self.blindscan_stop_frequency.value/1000000, self.blindscan_start_symbol.value, self.blindscan_stop_symbol.value, tab_pol[pol], tab_hilow[band], self.feid, self.getNimSocket(self.feid))
				else:
					self.session.open(MessageBox, _("Not found blind scan utility '%s'!") % tools, MessageBox.TYPE_ERROR)
					return
			else:
				self.session.open(MessageBox, not_support_text, MessageBox.TYPE_WARNING)
				return
		elif BOX_MODEL.startswith("edision"):
			tools = "/usr/bin/blindscan"
			if os.path.exists(tools):
				cmd = "blindscan --start=%d --stop=%d --min=%d --max=%d --slot=%d --i2c=%d" % (temp_start_int_freq, temp_end_int_freq, self.blindscan_start_symbol.value, self.blindscan_stop_symbol.value, self.feid, self.getNimSocket(self.feid))
				if tab_pol[pol]:
					cmd += " --vertical"
				if self.is_c_band_scan:
					cmd += " --cband"
				elif tab_hilow[band]:
					cmd += " --high"
			else:
				self.session.open(MessageBox, _("Not found blind scan utility '%s'!") % tools, MessageBox.TYPE_ERROR)
		else:
			self.session.open(MessageBox, not_support_text, MessageBox.TYPE_WARNING)
			return
		print "[Blind scan] prepared command : [%s]" % (cmd)

		self.thisRun = [] # used to check result corresponds with values used above
		self.thisRun.append(int(temp_start_int_freq))
		self.thisRun.append(int(temp_end_int_freq))
		self.thisRun.append(int(tab_hilow[band]))
		if not self.cmd:
			if self.SundtekScan:
				print "[Blind scan] closing frontend and starting blindscan"
				self.frontend.closeFrontend()
			self.blindscan_container = eConsoleAppContainer()
			self.blindscan_container.appClosed.append(self.blindscanContainerClose)
			self.blindscan_container.dataAvail.append(self.blindscanContainerAvail)
			self.blindscan_container.execute(cmd)

		display_pol = pol # Display the correct polarisation in the MessageBox below
		if self.scan_sat.polarization.value == eDVBFrontendParametersSatellite.Polarisation_CircularRight :
			display_pol = _("circular right")
		elif self.scan_sat.polarization.value == eDVBFrontendParametersSatellite.Polarisation_CircularLeft :
			display_pol = _("circular left")
		elif  self.scan_sat.polarization.value == eDVBFrontendParametersSatellite.Polarisation_CircularRight + 2 :
			if pol == "horizontal" :
				display_pol = _("circular left")
			else:
				display_pol = _("circular right")
		if display_pol == "horizontal":
			display_pol = _("horizontal")
		if display_pol == "vertical":
			display_pol = _("vertical")
		if self.SundtekScan:
			tmpmes = _("   Starting Sundtek hardware blind scan.")
		else:
			tmpmes = _("   Current Status : %d/%d\n   Satellite : %s\n   Polarization : %s\n   Frequency range : %d - %d MHz\n   Symbol rates : %d - %d MHz") %(self.running_count, self.max_count, orb[1], display_pol, status_box_start_freq, status_box_end_freq, self.blindscan_start_symbol.value, self.blindscan_stop_symbol.value)
		tmpmes2 = _("Looking for available transponders.\nThis will take a long time, please be patient.")
		tmpstr = tmpmes + '\n\n' + tmpmes2 + '\n\n'
		self.tmpstr = tmpstr
		if is_scan:
			self.blindscan_session = self.session.openWithCallback(self.blindscanSessionClose, MessageBox, tmpstr, MessageBox.TYPE_INFO)
		else:
			self.blindscan_session = self.session.openWithCallback(self.blindscanSessionNone, MessageBox, tmpstr, MessageBox.TYPE_INFO)

	def dataSundtekIsGood(self, data):
		add_tp = False
		pol = self.scan_sat.polarization.value
		if pol == eDVBFrontendParametersSatellite.Polarisation_CircularRight + 1 or pol == eDVBFrontendParametersSatellite.Polarisation_CircularRight + 2:
			add_tp = True
		elif self.Sundtek_pol in (1, 3) and (pol == eDVBFrontendParametersSatellite.Polarisation_Vertical or pol == eDVBFrontendParametersSatellite.Polarisation_CircularRight):
			add_tp = True
		elif self.Sundtek_pol in (0, 2) and (pol == eDVBFrontendParametersSatellite.Polarisation_Horizontal or pol == eDVBFrontendParametersSatellite.Polarisation_CircularLeft):
			add_tp = True
		if add_tp:
			freq = (int(data[1]) + self.offset) / 1000
			symbolrate = int(data[2])
			if freq >= self.blindscan_start_frequency.value and freq <= self.blindscan_stop_frequency.value and symbolrate >= self.blindscan_start_symbol.value * 1000 and symbolrate <= self.blindscan_stop_symbol.value * 1000:
				add_tp = True
			else:
				add_tp = False
		if add_tp:
			if self.is_c_band_scan:
				if freq > 2999 and freq < 4201:
					add_tp = True
				else:
					add_tp = False
			else:
				if freq < 12751 and freq > 10700:
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
			print "[Blind scan] cnt :", len(data), ", data :", data
			if self.SundtekScan:
				if len(data) == 3 and data[0] == 'Scanning':
					if data[1] == '13V':
						self.Sundtek_pol = 1
						if self.is_circular_band_scan or self.is_c_band_scan:
							self.Sundtek_pol = 3
					elif data[1] == '18V':
						self.Sundtek_pol = 0
						if self.is_circular_band_scan or self.is_c_band_scan:
							self.Sundtek_pol = 2
					if data[2] == 'Highband':
						self.Sundtek_band = "nigh"
					elif data[2] == 'Lowband':
						self.Sundtek_band = "low"
					self.offset = 0
					if self.is_c_band_scan:
						self.offset = 5150000
					elif self.is_circular_band_scan:
						self.offset = 10750000
					else:
						if self.Sundtek_band == "nigh":
							self.offset = 10600000
						elif self.Sundtek_band == "low":
							self.offset = 9750000
				if len(data) >= 6 and data[0] == 'OK' and self.Sundtek_pol != "" and self.offset and self.dataSundtekIsGood(data):
					parm = eDVBFrontendParametersSatellite()
					parm.orbital_position = self.orb_position
					parm.polarisation = self.Sundtek_pol
					frequency = ((int(data[1]) + self.offset) / 1000) * 1000
					parm.frequency = frequency
					symbol_rate = int(data[2]) * 1000
					parm.symbol_rate = symbol_rate
					parm.system = parm.System_DVB_S
					parm.inversion = parm.Inversion_Off
					parm.pilot = parm.Pilot_Off
					parm.fec = parm.FEC_Auto
					parm.modulation = parm.Modulation_QPSK
					parm.rolloff = parm.RollOff_alpha_0_35
					self.tmp_tplist.append(parm)
			elif len(data) >= 10 and self.dataIsGood(data):
				if data[0] == 'OK':
					parm = eDVBFrontendParametersSatellite()
					sys = { "DVB-S" : parm.System_DVB_S,
						"DVB-S2" : parm.System_DVB_S2}
					qam = { "QPSK" : parm.Modulation_QPSK,
						"8PSK" : parm.Modulation_8PSK,
						"16APSK" : parm.Modulation_16APSK,
						"32APSK" : parm.Modulation_32APSK}
					inv = { "INVERSION_OFF" : parm.Inversion_Off,
						"INVERSION_ON" : parm.Inversion_On,
						"INVERSION_AUTO" : parm.Inversion_Unknown}
					fec = { "FEC_AUTO" : parm.FEC_Auto,
						"FEC_1_2" : parm.FEC_1_2,
						"FEC_2_3" : parm.FEC_2_3,
						"FEC_3_4" : parm.FEC_3_4,
						"FEC_4_5" : parm.FEC_4_5,
						"FEC_5_6": parm.FEC_5_6,
						"FEC_7_8" : parm.FEC_7_8,
						"FEC_8_9" : parm.FEC_8_9,
						"FEC_3_5" : parm.FEC_3_5,
						"FEC_9_10" : parm.FEC_9_10,
						"FEC_NONE" : parm.FEC_None}
					roll ={ "ROLLOFF_20" : parm.RollOff_alpha_0_20,
						"ROLLOFF_25" : parm.RollOff_alpha_0_25,
						"ROLLOFF_35" : parm.RollOff_alpha_0_35,
						"ROLLOFF_AUTO" : parm.RollOff_auto}
					pilot={ "PILOT_ON" : parm.Pilot_On,
						"PILOT_OFF" : parm.Pilot_Off, 
						"PILOT_AUTO" : parm.Pilot_Unknown}
					pol = { "HORIZONTAL" : parm.Polarisation_Horizontal,
						"CIRCULARRIGHT" : parm.Polarisation_CircularRight,
						"CIRCULARLEFT" : parm.Polarisation_CircularLeft,
						"VERTICAL" : parm.Polarisation_Vertical}
					parm.orbital_position = self.orb_position
					parm.polarisation = pol[data[1]]
					parm.frequency = int(data[2])
					parm.symbol_rate = int(data[3])
					parm.system = sys[data[4]]
					parm.inversion = inv[data[5]]
					parm.pilot = pilot[data[6]]
					parm.fec = fec[data[7]]
					parm.modulation = qam[data[8]]
					parm.rolloff = roll[data[9]]
					self.tmp_tplist.append(parm)
		self.blindscan_session.close(True)
		self.blindscan_session = None

	def blindscanContainerAvail(self, str):
		self.full_data = self.full_data + str
		if self.blindscan_session:
			tmpstr = ""
			data = str.split()
			if self.SundtekScan:
				if len(data) == 3 and data[0] == 'Scanning':
					if data[1] == '13V':
						self.Sundtek_pol = "V"
						if self.is_circular_band_scan:
							self.Sundtek_pol = "R"
					elif data[1] == '18V':
						self.Sundtek_pol = "H"
						if self.is_circular_band_scan:
							self.Sundtek_pol = "L"
					if data[2] == 'Highband':
						self.Sundtek_band = "nigh"
					elif data[2] == 'Lowband':
						self.Sundtek_band = "low"
					self.offset = 0
					if self.is_c_band_scan:
						self.offset = 5150000
					elif self.is_circular_band_scan:
						self.offset = 10750000
					else:
						if self.Sundtek_band == "nigh":
							self.offset = 10600000
						elif self.Sundtek_band == "low":
							self.offset = 9750000
				if len(data) >= 6 and data[0] == 'OK' and self.Sundtek_pol and self.offset:
					tmpstr = data[1].isdigit() and "%s" % ((int(data[1]) + self.offset) / 1000) or data[1]
					tmpstr += "%s SR: %s" % (self.Sundtek_pol, data[2])
					self.tp_found.append(str)
			#elif len(data) >= 10 and data[0] == 'OK':
			#	tmpstr = data[2].isdigit() and "%s" % (int(data[2]) / 1000.) or data[2]
			#	tmpstr += " %s " %data[1]
			#	tmpstr += data[3].isdigit() and "%s" % (int(data[3]) / 1000.) or data[3]
			#	self.tp_found.append(str)
				seconds_done = int(time() - self.start_time)
				tmpstr += '\n'
				tmpstr += _("%d transponders found at %d:%02d min") %(len(self.tp_found),seconds_done / 60, seconds_done % 60)
				self.blindscan_session["text"].setText(self.tmpstr + tmpstr)

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
		print "[Blind scan] closing frontend and starting blindscan"
		self.frontend.closeFrontend() # close because blindscan-s2 does not like to be open
		self.blindscan_container = eConsoleAppContainer()
		self.blindscan_container.appClosed.append(self.blindscanContainerClose)
		self.blindscan_container.dataAvail.append(self.blindscanContainerAvail)
		self.blindscan_container.execute(self.cmd)

	def blindscanSessionClose(self, *val):
		global XML_FILE
		self["yellow"].setText("")
		XML_FILE = None
		if self.SundtekScan:
			self.frontend and self.frontend.closeFrontend()
		self.blindscanSessionNone(val[0])

		if self.tmp_tplist != None and self.tmp_tplist != []:
			if not self.SundtekScan:
				self.tmp_tplist = self.correctBugsCausedByDriver(self.tmp_tplist)

			# Sync with or remove transponders that exist in satellites.xml
			self.known_transponders = self.getKnownTransponders(self.orb_position)
			if self.dont_scan_known_tps.value :
				self.tmp_tplist = self.removeKnownTransponders(self.tmp_tplist, self.known_transponders)
			else:
				self.tmp_tplist = self.syncWithKnownTransponders(self.tmp_tplist, self.known_transponders)

			# Filter off transponders on neighbouring satellites
			if self.filter_off_adjacent_satellites.value :
				 self.tmp_tplist = self.filterOffAdjacentSatellites(self.tmp_tplist, self.orb_position, self.filter_off_adjacent_satellites.value)

			# Process transponders still in list
			if self.tmp_tplist != [] :
				for p in self.tmp_tplist:
					print "[Blind scan] data : [%d][%d][%d][%d][%d][%d][%d][%d][%d][%d]" % (p.orbital_position, p.polarisation, p.frequency, p.symbol_rate, p.system, p.inversion, p.pilot, p.fec, p.modulation, p.modulation)
				self.tmp_tplist = sorted(self.tmp_tplist, key=lambda transponder: transponder.frequency)
				xml_location = self.createSatellitesXMLfile(self.tmp_tplist, XML_BLINDSCAN_DIR)
				if self.search_type.value == 0 : # Do a service scan
					self.startScan(self.tmp_tplist, self.feid)
				else: # Save transponder data to file. No service scan.
					msg = _("Search completed. %d transponders found.\n\nDetails saved in:\n%s")%(len(self.tmp_tplist), xml_location)
					self.session.openWithCallback(self.callbackNone, MessageBox, msg, MessageBox.TYPE_INFO, timeout=300)
			else:
				msg = _("No new transponders found! \n\nOnly transponders already listed in satellites.xml \nhave been found for those search parameters!")
				self.session.openWithCallback(self.callbackNone, MessageBox, msg, MessageBox.TYPE_INFO, timeout=60)

		else:
			msg = _("No transponders were found for those search parameters!")
			if val[0] == False:
				msg = _("The blindscan run was cancelled by the user.")
			self.session.openWithCallback(self.callbackNone, MessageBox, msg, MessageBox.TYPE_INFO, timeout=60)
			self.tmp_tplist = []

	def startScan(self, tlist, feid, networkid = 0):
		self.scan_session = None

		flags = self.scan_networkScan.value and eComponentScan.scanNetworkSearch or 0
		tmp = self.scan_clearallservices.value
		if tmp == "no":
			flags |= eComponentScan.scanDontRemoveUnscanned
		elif tmp == "yes":
			flags |= eComponentScan.scanRemoveServices
		elif tmp == "yes_hold_feeds":
			flags |= eComponentScan.scanRemoveServices
			flags |= eComponentScan.scanDontRemoveFeeds
		if self.scan_onlyfree.value:
			flags |= eComponentScan.scanOnlyFree
		self.session.openWithCallback(self.startScanCallback, ServiceScan, [{"transponders": tlist, "feid": feid, "flags": flags, "networkid": networkid}])

	def getKnownTransponders(self, pos):
		tlist = []
		list = nimmanager.getTransponders(pos)
		for x in list:
			if x[0] == 0:
				parm = eDVBFrontendParametersSatellite()
				parm.frequency = x[1]
				parm.symbol_rate = x[2]
				parm.polarisation = x[3]
				parm.fec = x[4]
				parm.inversion = x[7]
				parm.orbital_position = pos
				parm.system = x[5]
				parm.modulation = x[6]
				parm.rolloff = x[8]
				parm.pilot = x[9]
				tlist.append(parm)
		return tlist

	def syncWithKnownTransponders(self, tplist, knowntp) :
		tolerance = 5
		multiplier = 1000
		x = 0
		for t in tplist :
			for k in knowntp :
				if (t.polarisation % 2) == (k.polarisation % 2) and \
					abs(t.frequency - k.frequency) < (tolerance*multiplier) and \
					abs(t.symbol_rate - k.symbol_rate) < (tolerance*multiplier) :
					tplist[x] = k
					#break
			x += 1
		tplist = self.removeDuplicateTransponders(tplist)
		return tplist

	def removeDuplicateTransponders(self, tplist) :
		new_tplist = []
		for t in tplist:
			if t not in new_tplist:
				new_tplist.append(t)
		return new_tplist

	def removeKnownTransponders(self, tplist, knowntp) :
		new_tplist = []
		tolerance = 5
		multiplier = 1000
		x = 0
		isnt_known = True
		for t in tplist :
			for k in knowntp :
				if (t.polarisation % 2) == (k.polarisation % 2) and \
					abs(t.frequency - k.frequency) < (tolerance*multiplier) and \
					abs(t.symbol_rate - k.symbol_rate) < (tolerance*multiplier) :
					isnt_known = False
					#break
			x += 1
			if isnt_known :
				new_tplist.append(t)
			else:
				isnt_known = True
		return new_tplist

	def filterOffAdjacentSatellites(self, tplist, pos, degrees) :
		neighbours = []
		tenths_of_degrees = degrees * 10
		for sat in nimmanager.satList :
			if sat[0] != pos and self.positionDiff(pos, sat[0]) <= tenths_of_degrees :
				neighbours.append(sat[0])
		for neighbour in neighbours :
			tplist = self.removeKnownTransponders(tplist, self.getKnownTransponders(neighbour))
		return tplist

	def correctBugsCausedByDriver(self, tplist) :
		if self.is_c_band_scan : # for some reason a c-band scan (with a Vu+) returns the transponder frequencies in Ku band format so they have to be converted back to c-band numbers before the subsequent service search
			x = 0
			for transponders in tplist :
				if tplist[x].frequency > (4200*1000) :
					tplist[x].frequency = (5150*1000) - (tplist[x].frequency - (9750*1000))
				x += 1

		x = 0
		for transponders in tplist :
			if tplist[x].system == 0 : # convert DVB-S transponders to auto fec as for some reason the tuner incorrectly returns 3/4 FEC for all transmissions
				tplist[x].fec = 0
			if self.scan_sat.polarization.value == eDVBFrontendParametersSatellite.Polarisation_CircularRight : # Return circular transponders to correct polarisation
				tplist[x].polarisation = eDVBFrontendParametersSatellite.Polarisation_CircularRight
			elif self.scan_sat.polarization.value == eDVBFrontendParametersSatellite.Polarisation_CircularLeft : # Return circular transponders to correct polarisation
				tplist[x].polarisation = eDVBFrontendParametersSatellite.Polarisation_CircularLeft
			elif self.scan_sat.polarization.value == eDVBFrontendParametersSatellite.Polarisation_CircularRight + 2: # Return circular transponders to correct polarisation
				if tplist[x].polarisation == eDVBFrontendParametersSatellite.Polarisation_Horizontal : # Return circular transponders to correct polarisation
					tplist[x].polarisation = eDVBFrontendParametersSatellite.Polarisation_CircularLeft
				else:
					tplist[x].polarisation = eDVBFrontendParametersSatellite.Polarisation_CircularRight
			x += 1
		return tplist

	def positionDiff(self, pos1, pos2) :
		diff = pos1 - pos2
		return min(abs(diff % 3600), 3600 - abs(diff % 3600))

	def dataIsGood(self, data) : # check output of the binary for nonsense values
		good = False
		low_lo = 9750
		high_lo = 10600
		c_lo = 5150
		lower_freq = self.thisRun[0]
		upper_freq = self.thisRun[1]
		high_band = self.thisRun[2]
		data_freq = int(int(data[2])/1000)
		data_symbol = int(data[3])
		lower_symbol = (self.blindscan_start_symbol.value * 1000000) - 200000
		upper_symbol = (self.blindscan_stop_symbol.value * 1000000) + 200000

		if high_band :
			data_if_freq = data_freq - high_lo
		elif self.is_c_band_scan and data_freq > 2999 and data_freq < 4201 :
			data_if_freq = c_lo - data_freq
		else :
			data_if_freq = data_freq - low_lo

		if data_if_freq >= lower_freq and data_if_freq <= upper_freq :
			good = True

		if data_symbol < lower_symbol or data_symbol > upper_symbol :
			good = False

		if good == False :
			print "[Blind scan] Data returned by the binary is not good...\n	Data: Frequency [%d], Symbol rate [%d]" % (int(data[2]), int(data[3]))

		return good

	def createSatellitesXMLfile(self, tp_list, save_xml_dir) :
		pos = self.orb_position
		if pos > 1800 :
			pos -= 3600
		if pos < 0 :
			pos_name = '%dW' % (abs(int(pos))/10)
		else :
			pos_name = '%dE' % (abs(int(pos))/10)
		location = '%s/blindscan_%s_%s.xml' %(save_xml_dir, pos_name, strftime("%d-%m-%Y_%H-%M-%S"))
		tuner = nimmanager.nim_slots[self.feid].friendly_full_description
		polarisation = ['horizontal', 'vertical', 'circular left', 'circular right', 'vertical and horizontal', 'circular right and circular left']
		adjacent = ['no', 'up to 1 degree', 'up to 2 degrees', 'up to 3 degrees']
		known_txp = 'no'
		if self.filter_off_adjacent_satellites.value :
			known_txp ='yes'
		xml = ['<?xml version="1.0" encoding="iso-8859-1"?>\n\n']
		xml.append('<!--\n')
		xml.append('	File created on %s\n' % (strftime("%A, %d of %B %Y, %H:%M:%S")))
		try:
			xml.append('	using %s receiver running Enigma2 image, version %s,\n' % (getBoxType(), about.getEnigmaVersionString()))
			xml.append('	image %s, with the Blind scan plugin\n\n' % (about.getImageTypeString()))
		except:
			xml.append('	using %s receiver running Enigma2 image, with the Blind scan plugin\n\n' % (getBoxType()))
		xml.append('	Search parameters:\n')
		xml.append('		%s\n' % (tuner))
		xml.append('		Satellite: %s\n' % (self.sat_name))
		xml.append('		Start frequency: %dMHz\n' % (self.blindscan_start_frequency.value))
		xml.append('		Stop frequency: %dMHz\n' % (self.blindscan_stop_frequency.value))
		xml.append('		Polarization: %s\n' % (polarisation[self.scan_sat.polarization.value]))
		xml.append('		Lower symbol rate: %d\n' % (self.blindscan_start_symbol.value * 1000))
		xml.append('		Upper symbol rate: %d\n' % (self.blindscan_stop_symbol.value * 1000))
		xml.append('		Only save unknown tranponders: %s\n' % (known_txp))
		xml.append('		Filter out adjacent satellites: %s\n' % (adjacent[self.filter_off_adjacent_satellites.value]))
		xml.append('-->\n\n')
		xml.append('<satellites>\n')
		xml.append('	<sat name="%s" flags="0" position="%s">\n' % (self.sat_name.replace('&', '&amp;'), self.orb_position))
		for tp in tp_list :
			xml.append('		<transponder frequency="%d" symbol_rate="%d" polarization="%d" fec_inner="%d" system="%d" modulation="%d"/>\n' % (tp.frequency, tp.symbol_rate, tp.polarisation, tp.fec, tp.system, tp.modulation))
		xml.append('	</sat>\n')
		xml.append('</satellites>')
		f = open(location, "w")
		f.writelines(xml)
		f.close()
		global XML_FILE
		self["yellow"].setText(_("Open xml file"))
		XML_FILE = location
		return location

	def keyYellow(self):
		if XML_FILE and os.path.exists(XML_FILE):
			self.session.open(Console,_(XML_FILE),["cat %s" % XML_FILE])

	def SatBandCheck(self) :
		pos = self.getOrbPos()
		freq = 0
		band = 'Unknown'
		self.is_c_band_scan = False
		self.is_circular_band_scan = False
		self.suggestedPolarisation = _("vertical & horizontal")
		# check in satellites.xml to work out band
		tp_list = self.getKnownTransponders(pos)
		Len = len(tp_list)
		if Len :
			freq = int(tp_list[Len - 1].frequency)
			if int(tp_list[Len - 1].polarisation) > 1 : # for hints text
				self.suggestedPolarisation = _("circular right & circular left")
		if freq :
			if freq < 4201000 and freq > 2999000 :
				band = 'C'
				self.is_c_band_scan = True
			elif freq < 12751000 and freq > 10700000 :
				band = 'Ku'
		# if satellites.xml didn't contain any entries for this satellite check 
		# LNB type instead. Assumes the tuner is configured correctly for C-band.
		if band == "Unknown" and self.isCbandLNB(pos): 
			band = 'C'
			self.is_c_band_scan = True
		if pos == 360 or pos == 560:
			self.suggestedPolarisation = _("circular right & circular left")
			self.is_circular_band_scan = True
		print "[Blind scan] SatBandCheck band = %s" % (band)

	def isCbandLNB(self, cur_orb_pos):
		nim = nimmanager.nim_slots[int(self.scan_nims.value)]
		if nim.config.configMode.getValue() == "advanced":
			currSat = nim.config.advanced.sat[cur_orb_pos]
			lnbnum = int(currSat.lnb.getValue())
			currLnb = nim.config.advanced.lnb[lnbnum]
			lof = currLnb.lof.getValue()
			print "[Blind scan] LNB type: ", lof
			if lof == "c_band":
				return True
		return False

	def getOrbPos(self):
		try:
			idx_selected_sat = int(self.getSelectedSatIndex(self.scan_nims.value))
			tmp_list = [self.satList[int(self.scan_nims.value)][self.scan_satselection[idx_selected_sat].index]]
			orb = tmp_list[0][0]
			print "[Blind scan] orb = ", orb
		except:
			orb = -9999
			print "[Blind scan] error parsing orb"
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
		# freq, sr, pol, fec, inv, orb, sys, mod, roll, pilot 
		transponder = (tps[0][1] / 1000, tps[0][2] / 1000, tps[0][3], tps[0][4], 2, orb_pos, tps[0][5], tps[0][6], tps[0][8], tps[0][9])
		if not self.prepareFrontend():
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
			return "%d.%d\xc2\xb0 W" % (orbpos/10, orbpos%10)
		return "%d.%d\xc2\xb0 E" % (orbpos/10, orbpos%10)

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
		self.statusTimer.start(1000)

	def getRotorMovingState(self):
		return eDVBSatelliteEquipmentControl.getInstance().isRotorMoving()

	def releaseFrontend(self):
		if hasattr(self, 'frontend'):
			del self.frontend
			self.frontend = None
		if hasattr(self, 'raw_channel'):
			del self.raw_channel

def main(session, close=None, **kwargs):
	if BOX_MODEL == "dreambox":
		menu = [(_("Another type"), "all"),(_("Dreambox type"), "dmm")]
		def scanType(choice):
			if choice:
				if choice[1] == "all":
					session.openWithCallback(close, Blindscan)
				elif choice[1] == "dmm":
					session.openWithCallback(close, dmmBlindScan.DmmBlindscan)
		session.openWithCallback(scanType, ChoiceBox, title=_("Select type for scan:"), list=menu)
	else:
		session.openWithCallback(close, Blindscan)

def BlindscanSetup(menuid, **kwargs):
	if menuid == "scan":
		return [(_("Satellite blind scan"), main, "blindscan", 50)]
	else:
		return []

def Plugins(**kwargs):
	if nimmanager.hasNimType("DVB-S"):
		return PluginDescriptor(name=_("Blind scan"), description=_("Scan satellites for new transponders"), where = PluginDescriptor.WHERE_MENU, fnc=BlindscanSetup)
	else:
		return []
