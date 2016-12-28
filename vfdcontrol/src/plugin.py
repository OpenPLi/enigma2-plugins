from . import _
from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor
from Components.Button import Button
from Components.ActionMap import ActionMap
from Components.config import config, configfile, ConfigSubsection, getConfigListEntry, ConfigSelection, ConfigYesNo
from Components.ConfigList import ConfigListScreen
from enigma import iPlayableService, eServiceCenter, eTimer, eActionMap, getDesktop, eDBoxLCD
from Components.ServiceEventTracker import ServiceEventTracker
from Screens.InfoBar import InfoBar
from time import localtime, time, sleep
import Screens.Standby
import os
from Tools.HardwareInfo import HardwareInfo
from Components.Console import Console


config.plugins.SEG = ConfigSubsection()
config.plugins.SEG.showClock = ConfigYesNo(default = True)
config.plugins.SEG.showCHnumber = ConfigSelection(default = "15", choices = [("5",_("5 sec")), ("15",_("15 sec")),("30",_("30 sec")),("60",_("60 sec")),("50000",_("Always")),("0",_("disabled"))])
config.plugins.SEG.timeMode = ConfigSelection(default = "24h", choices = [("12h",_("12h")),("24h",_("24h"))])
config.plugins.SEG.blinkRec = ConfigYesNo(default = False)

choicelist = []
default_value = ""
if os.path.exists("/dev/dbox/oled0"):
	choicelist.append(("oled", "/dev/dbox/oled0"))
	default_value = "oled"
if os.path.exists("/dev/dbox/lcd0"):
	choicelist.append(("lcd", "/dev/dbox/lcd0"))
	default_value = "lcd"
if HardwareInfo().get_device_model() in ("formuler3", "formuler4", "formuler4turbo", "s1", "h3", "h4", "h5", "lc", "hd500c", "hd530c", "hd1500", "hd1265", "hd1200", "hd1100"):
	default_value = "oled"
config.plugins.SEG.frontpanel = ConfigSelection(default = default_value, choices = choicelist)

skin_text = os.path.isfile("/usr/share/enigma2/skin_text.xml") or os.path.isfile("/etc/enigma2/skin_user.xml")

mySession = None
ChannelnumberInstance = None
standbyCounter = None

def display_write(text):
	if config.plugins.SEG.frontpanel.value == "oled": 
		try:
			open("/dev/dbox/oled0", "w").write(text)
		except:
			pass
	elif config.plugins.SEG.frontpanel.value == "lcd":
		try:
			open("/dev/dbox/lcd0", "w").write(text)
		except:
			pass

def displaybrightness_write():
	if os.path.exists("/proc/stb/lcd/oled_brightness"):
		try:
			open("/proc/stb/lcd/oled_brightness", "w").write("0")
		except:
			pass
	elif os.path.exists("/proc/stb/fp/oled_brightness"):
		try:
			open("/proc/stb/fp/oled_brightness", "w").write("0")
		except:
			pass
	elif os.path.exists("/proc/stb/led/oled_brightness"):
		try:
			open("/proc/stb/led/oled_brightness", "w").write("0")
		except:
			pass


class Channelnumber:
	def __init__(self, session):
		self.session = session
		self.channelnrdelay = config.plugins.SEG.showCHnumber.value
		self.dvb_service = ""
		self.begin = int(time())
		self.endkeypress = True
		eActionMap.getInstance().bindAction('', -0x7FFFFFFF, self.keyPressed)
		self.TimerText = eTimer()
		self.TimerText.timeout.get().append(self.showclock)
		self.TimerText.start(1000, True)
		self.serviceHandler = None
		self.InfoBarinstance = None
		self.onClose = [ ]

		self.__event_tracker = ServiceEventTracker(screen=self,eventmap=
			{
				iPlayableService.evStart: self.__evStart,
				iPlayableService.evEnd: self.__evEnd
			})

	def __evStart(self):
		if not skin_text:
			self.dvb_service = ""
			return
		playref = self.session.nav.getCurrentlyPlayingServiceReference()
		if not playref:
			self.dvb_service = ""
		else:
			str_service = playref.toString()
			stream = '%3a//' in str_service
			if (stream and str_service.startswith("4097")) or (not stream and str_service.rsplit(":", 1)[1].startswith("/")):
				self.dvb_service = "video"
			else:
				self.dvb_service = ""

	def __evEnd(self):
		self.dvb_service = ""

	def updateNumber(self):
		if not self.dvb_service:
			text = ""
			service = self.session.nav.getCurrentService()
			info = service and service.info()
			if info is not None:
				text = self.getchannelnr()
			if not text:
				self.show()
			else:
				Channelnr = "%04d" % (int(text))
				display_write(Channelnr)

	def getchannelnr(self):
		if self.InfoBarinstance is None:
			self.InfoBarinstance = InfoBar.instance
		if not self.InfoBarinstance:
			return ""
		MYCHANSEL = self.InfoBarinstance.servicelist
		if not MYCHANSEL:
			return ""
		if self.serviceHandler is None:
			self.serviceHandler = eServiceCenter.getInstance()
		myRoot = MYCHANSEL.servicelist.getRoot()
		mySSS = self.serviceHandler and self.serviceHandler.list(myRoot)
		SRVList = mySSS and mySSS.getContent("SN", True)
		markersOffset = 0
		mySrv = MYCHANSEL.servicelist.getCurrent()
		chx = MYCHANSEL.servicelist.l.lookupService(mySrv)
		for i in range(len(SRVList)):
			if chx == i:
				break
			testlinet = SRVList[i]
			testline = testlinet[0].split(":")
			if testline[1] == "64":
				markersOffset = markersOffset + 1
		chx = (chx - markersOffset) + 1
		rx = MYCHANSEL.getBouquetNumOffset(myRoot)
		return str(chx + rx)

	def show(self):
		if not self.dvb_service:
			clock = str(localtime()[3])
			clock1 = str(localtime()[4])
			if config.plugins.SEG.timeMode.value == "12h":
				if int(clock) > 12:
					clock = str(int(clock) - 12)
			clock2 = "%02d:%02d" % (int(clock), int(clock1))
			display_write(clock2)

	def showclock(self):
		if config.plugins.SEG.showClock.value:
			standby_mode = Screens.Standby.inStandby
			update_time = 1000
			if not standby_mode:
				if self.dvb_service == "video":
					update_time = 10000
				else:
					if config.plugins.SEG.showCHnumber.value != "0":
						if time() >= self.begin:
							self.endkeypress = False
						if self.endkeypress:
							self.updateNumber()
						else:
							self.show()
					else:
						self.show()
			elif not skin_text:
				self.show()

			self.TimerText.start(update_time, True)

	def keyPressed(self, key, tag):
		self.begin = time() + int(self.channelnrdelay)
		self.endkeypress = True

class SEG_Setup(Screen, ConfigListScreen):
	if getDesktop(0).size().width() >= 1920:
		skin = """
			<screen position="center,center" size="700,300" title="Control 7 Segment display" >
				<widget name="config" position="20,15" size="660,250" itemHeight="35" font="Regular;33" scrollbarMode="showOnDemand" />
				<ePixmap position="0,260" size="230,35" pixmap="skin_default/buttons/red.png" alphatest="on" />
				<ePixmap position="235,260" size="230,35" pixmap="skin_default/buttons/green.png" alphatest="on" />
				<ePixmap position="470,260" size="230,35" pixmap="skin_default/buttons/yellow.png" alphatest="on" />
				<widget name="key_red" position="0,260" size="230,35" font="Regular;28" backgroundColor="#1f771f" zPosition="2" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
				<widget name="key_green" position="235,260" size="230,35" font="Regular;28" backgroundColor="#1f771f" zPosition="2" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
				<widget name="key_yellow" position="470,260" size="230,35" font="Regular;28" backgroundColor="#1f771f" zPosition="2" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
			</screen>"""
	else:
		skin = """
			<screen position="center,center" size="500,210" title="Control 7 Segment display" >
				<widget name="config" position="20,15" size="460,150" scrollbarMode="showOnDemand" />
				<ePixmap position="40,165" size="140,40" pixmap="skin_default/buttons/red.png" alphatest="on" />
				<ePixmap position="180,165" size="140,40" pixmap="skin_default/buttons/green.png" alphatest="on" />
				<ePixmap position="360,165" size="140,40" pixmap="skin_default/buttons/yellow.png" alphatest="on" />
				<widget name="key_red" position="40,165" size="140,40" font="Regular;18" backgroundColor="#1f771f" zPosition="2" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
				<widget name="key_green" position="180,165" size="140,40" font="Regular;18" backgroundColor="#1f771f" zPosition="2" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
				<widget name="key_yellow" position="360,165" size="140,40" font="Regular;18" backgroundColor="#1f771f" zPosition="2" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
			</screen>"""
	def __init__(self, session, args = None):
		Screen.__init__(self, session)
		self.setTitle(_("Control 7-Segment display"))
		ConfigListScreen.__init__(self, [], session = self.session)
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))
		self["key_yellow"] = Button(_("Test display"))
		self["setupActions"] = ActionMap(["SetupActions","ColorActions"],
		{
			"save": self.keySave,
			"cancel": self.keyCancel,
			"ok": self.keySave,
			"yellow": self.setTestDisplay,
		}, -2)
		config.plugins.SEG.blinkRec.value = os.path.isfile("/etc/enigma2/.rec.txt") and os.path.isfile("/etc/enigma2/skin_user.xml")
		self.createSetup()

	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Enable"), config.plugins.SEG.showClock))
		if config.plugins.SEG.showClock.value:
			self.list.append(getConfigListEntry(_("Show channel number"), config.plugins.SEG.showCHnumber))
			self.list.append(getConfigListEntry(_("Time mode"), config.plugins.SEG.timeMode))
			if os.path.isfile("/usr/lib/enigma2/python/Plugins/SystemPlugins/VfdControl/skin_user.xml"):
				self.list.append(getConfigListEntry(_("Blink during recording"), config.plugins.SEG.blinkRec))
			self.list.append(getConfigListEntry(_("Type front panel"), config.plugins.SEG.frontpanel))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def saveAll(self):
		if self["config"].isChanged():
			if config.plugins.SEG.showClock.value:
				try:
					eDBoxLCD.getInstance().setLCDBrightness(config.lcd.bright.value * 255 / 10)
				except:
					pass
				if ChannelnumberInstance:
					ChannelnumberInstance.channelnrdelay = config.plugins.SEG.showCHnumber.value
					ChannelnumberInstance.TimerText.stop()
					ChannelnumberInstance.showclock()
				else:
					initSEG()
				if not config.plugins.SEG.blinkRec.value:
					if os.path.isfile("/etc/enigma2/.rec.txt"):
						Console().ePopen("rm -rf /etc/enigma2/skin_user.xml")
						Console().ePopen("rm -rf /usr/share/enigma2/.rec.txt")
				else:
					if os.path.isfile("/usr/lib/enigma2/python/Plugins/SystemPlugins/VfdControl/skin_user.xml"):
						Console().ePopen("cp /usr/lib/enigma2/python/Plugins/SystemPlugins/VfdControl/skin_user.xml /etc/enigma2/skin_user.xml")
						Console().ePopen("echo "" > /etc/enigma2/.rec.txt")
			else:
				displaybrightness_write() 
			for x in self["config"].list:
				x[1].save()
			configfile.save()

	def setTestDisplay(self):
		display_write("0000")
		sleep(1)
		display_write("1111")
		sleep(1)
		display_write("2222")
		sleep(1)
		display_write("3333")
		sleep(1)
		display_write("4444")
		sleep(1)
		display_write("5555")

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	def keySave(self):
		self.saveAll()
		self.close()

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

def main(menuid):
	if menuid != "system":
		return [ ]
	return [(_("7-Segment Display Setup"), startSEG, "seg", None)]

def startSEG(session, **kwargs):
	session.open(SEG_Setup)

def initSEG():
	global ChannelnumberInstance, standbyCounter
	if not config.plugins.SEG.showClock.value:
		displaybrightness_write()
	elif mySession and ChannelnumberInstance is None:
		ChannelnumberInstance = Channelnumber(mySession)
	if standbyCounter is None: 
		standbyCounter = config.misc.standbyCounter.addNotifier(standbyCounterChanged, initial_call = False)

def leaveStandby():
	if not config.plugins.SEG.showClock.value:
		displaybrightness_write()

def standbyCounterChanged(configElement):
	from Screens.Standby import inStandby
	if inStandby:
		inStandby.onClose.append(leaveStandby)
	if not config.plugins.SEG.showClock.value:
		displaybrightness_write()

def sessionstart(reason, **kwargs):
	global mySession
	if reason == 0 and mySession is None and kwargs.has_key("session"):
		mySession = kwargs["session"]
		initSEG()

def Plugins(**kwargs):
	if os.path.exists("/dev/dbox/oled0") or os.path.exists("/dev/dbox/lcd0"):
		return [ PluginDescriptor(where=[PluginDescriptor.WHERE_AUTOSTART, PluginDescriptor.WHERE_SESSIONSTART], fnc=sessionstart),
			PluginDescriptor(name="7-Segment Display Setup", description=_("Change display settings"),where = PluginDescriptor.WHERE_MENU, fnc = main) ]
	return []
