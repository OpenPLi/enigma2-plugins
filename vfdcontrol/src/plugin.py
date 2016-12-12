from . import _
from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor
from Components.Button import Button
from Components.ActionMap import ActionMap
from Components.config import config, configfile, ConfigSubsection, getConfigListEntry, ConfigSelection, ConfigSlider
from Components.ConfigList import ConfigListScreen
from enigma import iPlayableService, eServiceCenter, eTimer, eActionMap, eDBoxLCD
from Components.ServiceEventTracker import ServiceEventTracker
from Screens.InfoBar import InfoBar
from time import localtime, time
import Screens.Standby
from Tools.HardwareInfo import HardwareInfo

use_oled = False
if HardwareInfo().get_device_model() in ("formuler3", "formuler4", "s1", "h3", "h4", "h5", "lc"):
	use_oled = True

config.plugins.VFD_ini = ConfigSubsection()
config.plugins.VFD_ini.showClock = ConfigSelection(default = "True_Switch", choices = [("False",_("Channelnumber in Standby off")),("True",_("Channelnumber in Standby Clock")), ("True_Switch",_("Channelnumber/Clock in Standby Clock")),("True_All",_("Clock always")),("Off",_("Always off"))])
config.plugins.VFD_ini.timeMode = ConfigSelection(default = "24h", choices = [("12h",_("12h")),("24h",_("24h"))])
config.plugins.VFD_ini.recDisplay = ConfigSelection(default = "False", choices = [("True",_("yes")),("False",_("no"))])
config.plugins.VFD_ini.recClockBlink = ConfigSelection(default = "off", choices = [("off",_("Off")),("on_off",_("On/Off")),("brightness",_("Brightness level"))])
config.plugins.VFD_ini.ClockLevel1 = ConfigSlider(default=1, limits=(0, 10))
config.plugins.VFD_ini.ClockLevel2 = ConfigSlider(default=4, limits=(1, 10))

MyRecLed = False

def vfd_write(text):
	if use_oled:
		try:
			open("/dev/dbox/oled0", "w").write(text)
		except:
			pass
	else:
		try:
			open("/dev/dbox/lcd0", "w").write(text)
		except:
			pass

class Channelnumber:

	def __init__(self, session):
		self.session = session
		self.sign = 0
		self.updatetime = 15000
		self.blink = False
		self.blinkCounter = 0
		self.dvb_service = ""
		self.channelnrdelay = 15
		self.begin = int(time())
		self.endkeypress = True
		eActionMap.getInstance().bindAction('', -0x7FFFFFFF, self.keyPressed)
		self.zaPrik = eTimer()
		self.zaPrik.timeout.get().append(self.vrime)
		self.zaPrik.start(1000, True)
		self.onClose = [ ]

		self.__event_tracker = ServiceEventTracker(screen=self,eventmap=
			{
				#iPlayableService.evUpdatedEventInfo: self.__eventInfoChanged,
				iPlayableService.evStart: self.__evStart,
				iPlayableService.evEnd: self.__evEnd
			})

	def __evStart(self):
		self.getCurrentlyPlayingService()

	def __evEnd(self):
		self.dvb_service = ""
		if config.plugins.VFD_ini.showClock.value == 'Off':
			vfd_write("....")

def getCurrentlyPlayingService(self):
	playref = self.session.nav.getCurrentlyPlayingServiceReference()
	if not playref:
		self.dvb_service = ""
	else:
		str_service = playref.toString()
		if '%3a//' in str_service or str_service.rsplit(":", 1)[1].startswith("/"):
			self.dvb_service = "video"
			if config.plugins.VFD_ini.showClock.value == 'True_All':
				vfd_write("....")
		else:
			self.dvb_service = "dvb"

	def __eventInfoChanged(self, manual=False):
		if not manual and self.dvb_service == "video":
			return
		self.RecordingLed()
		if config.plugins.VFD_ini.showClock.value == 'Off' or config.plugins.VFD_ini.showClock.value == 'True_All':
			return
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		if info is None:
			chnr = "----"
		else:
			chnr = self.getchannelnr()
		info = None
		service = None
		if chnr == "----":
			if config.plugins.VFD_ini.recDisplay.value == 'True' and MyRecLed:
				vfd_write(" rec")
			else:
				vfd_write(chnr)
		else:
			Channelnr = "%04d" % (int(chnr))
			if config.plugins.VFD_ini.recDisplay.value == 'True' and MyRecLed:
				vfd_write(" rec")
			else:
				vfd_write(Channelnr)

	def getchannelnr(self):
		chnr = "----"
		if self.dvb_service != "dvb":
			return chnr
		if InfoBar.instance is None:
			return chnr
		MYCHANSEL = InfoBar.instance.servicelist
		markersOffset = 0
		myRoot = MYCHANSEL.getRoot()
		mySrv = MYCHANSEL.servicelist.getCurrent()
		chx = MYCHANSEL.servicelist.l.lookupService(mySrv)
		if not MYCHANSEL.inBouquet():
			pass
		else:
			serviceHandler = eServiceCenter.getInstance()
			mySSS = serviceHandler.list(myRoot)
			SRVList = mySSS and mySSS.getContent("SN", True)
			for i in range(len(SRVList)):
				if chx == i:
					break
				testlinet = SRVList[i]
				testline = testlinet[0].split(":")
				if testline[1] == "64":
					markersOffset = markersOffset + 1
		chx = (chx - markersOffset) + 1
		rx = MYCHANSEL.getBouquetNumOffset(myRoot)
		chnr = str(chx + rx)
		return chnr

	def prikaz(self):
		self.RecordingLed()
		if config.plugins.VFD_ini.recClockBlink.value != "off" and MyRecLed and config.plugins.VFD_ini.recDisplay.value == 'False':
			self.blinkCounter += 1
			if self.blinkCounter >= 2:
				self.blinkCounter = 0
				if self.blink:
					if config.plugins.VFD_ini.recClockBlink.value == "brightness":
						eDBoxLCD.getInstance().setLCDBrightness(config.plugins.VFD_ini.ClockLevel2.value * 255 / 10)
					self.blink = False
				else:
					if config.plugins.VFD_ini.recClockBlink.value == "brightness":
						eDBoxLCD.getInstance().setLCDBrightness(config.plugins.VFD_ini.ClockLevel1.value * 255 / 10)
					self.blink = True

		if config.plugins.VFD_ini.showClock.value == 'True' or config.plugins.VFD_ini.showClock.value == 'True_All' or config.plugins.VFD_ini.showClock.value == 'True_Switch':
			clock = str(localtime()[3])
			clock1 = str(localtime()[4])
			zero = ""
			if config.plugins.VFD_ini.timeMode.value != '24h':
				if int(clock) > 12:
					clock = str(int(clock) - 12)
			elif int(clock) < 10:
				zero = "0"
			if self.sign == 0:
				clock2 = "%s%02d:%02d" % (zero, int(clock), int(clock1))
				self.sign = 1
			else:
				clock2 = "%s%02d%02d" % (zero, int(clock), int(clock1))
				self.sign = 0

			if config.plugins.VFD_ini.recDisplay.value == 'True' and MyRecLed:
				vfd_write(" rec")
			elif config.plugins.VFD_ini.recClockBlink.value == 'on_off' and self.blink:
				vfd_write("....")
			else:
				vfd_write(clock2)
		else:
			vfd_write("....")

	def vrime(self):
		standby_mode = Screens.Standby.inStandby
		if (config.plugins.VFD_ini.showClock.value == 'True' or config.plugins.VFD_ini.showClock.value == 'False' or config.plugins.VFD_ini.showClock.value == 'True_Switch') and not standby_mode:
			if config.plugins.VFD_ini.showClock.value == 'True_Switch':
				if time() >= self.begin:
					self.endkeypress = False
				if self.endkeypress:
					self.__eventInfoChanged(True)
				else:
					self.prikaz()
			else:
				self.__eventInfoChanged(True)

		if config.plugins.VFD_ini.showClock.value == 'Off':
			vfd_write("....")
			self.zaPrik.start(self.updatetime, True)
			return
		else:
			update_time = 1000
			if not standby_mode and config.plugins.VFD_ini.showClock.value == 'True_All' and self.dvb_service == "video":
				update_time = 15000
			self.zaPrik.start(update_time, True)

		if standby_mode or (config.plugins.VFD_ini.showClock.value == 'True_All' and self.dvb_service != "video"):
			self.prikaz()

	def keyPressed(self, key, tag):
		self.begin = time() + int(self.channelnrdelay)
		self.endkeypress = True

	def RecordingLed(self):
		global MyRecLed
		if self.session.nav.getRecordings():
			MyRecLed = True
		else:
			MyRecLed = False
			if self.blink:
				eDBoxLCD.getInstance().setLCDBrightness(config.lcd.bright.value * 255 / 10)
				self.blink = False

ChannelnumberInstance = None

def leaveStandby():
	if config.plugins.VFD_ini.showClock.value == 'Off':
		vfd_write("....")

def standbyCounterChanged(configElement):
	from Screens.Standby import inStandby
	inStandby.onClose.append(leaveStandby)

	if config.plugins.VFD_ini.showClock.value == 'Off':
		vfd_write("....")

def initVFD():
	if config.plugins.VFD_ini.showClock.value == 'Off':
		vfd_write("....")

class VFD_INISetup(ConfigListScreen, Screen):
	def __init__(self, session, args = None):

		self.skin = """
			<screen position="center,center" size="500,210" title="VFD Display Setup" >
				<widget name="config" position="20,15" size="460,150" scrollbarMode="showOnDemand" />
				<ePixmap position="40,165" size="140,40" pixmap="skin_default/buttons/red.png" alphatest="on" />
				<ePixmap position="180,165" size="140,40" pixmap="skin_default/buttons/green.png" alphatest="on" />
				<ePixmap position="360,165" size="140,40" pixmap="skin_default/buttons/yellow.png" alphatest="on" />
				<widget name="key_red" position="40,165" size="140,40" font="Regular;18" backgroundColor="#1f771f" zPosition="2" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
				<widget name="key_green" position="180,165" size="140,40" font="Regular;18" backgroundColor="#1f771f" zPosition="2" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
				<widget name="key_yellow" position="360,165" size="140,40" font="Regular;18" backgroundColor="#1f771f" zPosition="2" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
			</screen>"""

		Screen.__init__(self, session)
		self.setTitle(_("Control 7 segment VFD display"))
		self.onClose.append(self.abort)

		self.onChangedEntry = [ ]

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)

		self.createSetup()

		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))
		self["key_yellow"] = Button(_("Update Date/Time"))

		self["setupActions"] = ActionMap(["SetupActions","ColorActions"],
		{
			"save": self.save,
			"cancel": self.cancel,
			"ok": self.save,
			"yellow": self.Update,
		}, -2)

	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Show on VFD"), config.plugins.VFD_ini.showClock))
		if config.plugins.VFD_ini.showClock.value != "Off":
			self.list.append(getConfigListEntry(_("Time mode"), config.plugins.VFD_ini.timeMode))
			self.list.append(getConfigListEntry(_("Show REC-Symbol in Display"), config.plugins.VFD_ini.recDisplay))
			if config.plugins.VFD_ini.recDisplay.value == "False":
				self.list.append(getConfigListEntry(_("Show blinking Clock on Display during recording"), config.plugins.VFD_ini.recClockBlink))
				if config.plugins.VFD_ini.recClockBlink.value == "brightness":
					self.list.append(getConfigListEntry(_("Brightness Level 1"), config.plugins.VFD_ini.ClockLevel1))
					self.list.append(getConfigListEntry(_("Brightness Level 2"), config.plugins.VFD_ini.ClockLevel2))

		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def changedEntry(self):
		for x in self.onChangedEntry:
			x()
		self.newConfig()

	def newConfig(self):
		if self["config"].getCurrent()[0] == _('Show on VFD'):
			self.createSetup()
		elif self["config"].getCurrent()[0] == _('Show REC-Symbol in Display'):
			self.createSetup()
		elif self["config"].getCurrent()[0] == _('Show blinking Clock on Display during recording'):
			self.createSetup()

	def abort(self):
		pass

	def save(self):
		for x in self["config"].list:
			x[1].save()

		configfile.save()
		initVFD()
		self.close()

	def cancel(self):
		initVFD()
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def Update(self):
		self.createSetup()
		initVFD()

class VFD_INI:
	def __init__(self, session):
		self.session = session
		self.onClose = [ ]
		initVFD()

		global ChannelnumberInstance
		if ChannelnumberInstance is None:
			ChannelnumberInstance = Channelnumber(session)

	def shutdown(self):
		self.abort()

	def abort(self):
		config.misc.standbyCounter.addNotifier(standbyCounterChanged, initial_call = False)

def main(menuid):
	if menuid != "system":
		return [ ]
	return [(_("VFD Display Setup"), startVFD, "vfd_ini", None)]

def startVFD(session, **kwargs):
	session.open(VFD_INISetup)

iniVfd = None
gReason = -1
mySession = None

def controliniVfd():
	global iniVfd
	global gReason
	global mySession

	if gReason == 0 and mySession != None and iniVfd == None:
		iniVfd = VFD_INI(mySession)
	elif gReason == 1 and iniVfd != None:
		iniVfd = None

def sessionstart(reason, **kwargs):
	global iniVfd
	global gReason
	global mySession

	if kwargs.has_key("session"):
		mySession = kwargs["session"]
	else:
		gReason = reason
	controliniVfd()

def Plugins(**kwargs):
	from Components.SystemInfo import SystemInfo
	if SystemInfo["FrontpanelDisplay"]:
		return [ PluginDescriptor(where=[PluginDescriptor.WHERE_AUTOSTART, PluginDescriptor.WHERE_SESSIONSTART], fnc=sessionstart),
			PluginDescriptor(name="VFD Display Setup", description=_("Change VFD display settings"),where = PluginDescriptor.WHERE_MENU, fnc = main) ]
	return []
