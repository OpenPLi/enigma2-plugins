from . import _, _N, PLUGIN_NAME
from Plugins.Plugin import PluginDescriptor
from Components.config import config, ConfigSubsection, ConfigBoolean, ConfigSelection, ConfigInteger, ConfigYesNo, ConfigNumber, ConfigNothing, NoSave, ConfigText
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.Label import Label
from Components.NimManager import nimmanager
from enigma import iRecordableService, iRecordableServicePtr, eServiceReference, eServiceCenter, eTimer, ePoint, eSize, iPlayableService, getDesktop, getBestPlayableServiceReference
from time import time as Time, strftime, localtime
from Screens.InfoBarGenerics import InfoBarShowHide, InfoBarEPG
from Screens.ChannelSelection import service_types_tv, service_types_radio
from Tools.BoundFunction import boundFunction
try:
	from Tools.StbHardware import getFPWasTimerWakeup
except:
	from Tools.DreamboxHardware import getFPWasTimerWakeup
from RecordTimer import AFTEREVENT
from Screens import Standby 
from Tools import Notifications
import RecInfobarSetup
import NavigationInstance
import ServiceReference
import Screens.InfoBar
import math

baseInfoBarShowHide__init__ = None
try:
	RecordService = config.usage.recording_frontend_priority.value
	SUPPORT_PRIORITY = True
except:
	RecordService = None
	SUPPORT_PRIORITY = False
PrevFrontendPriority = None
_session = None

config.misc.rectimerstate =  ConfigBoolean(default = False)
config.usage.recinfobar = ConfigYesNo(default = False)
config.plugins.RecInfobar = ConfigSubsection()
config.plugins.RecInfobar.anchor = ConfigSelection([("top", _("down")),("bottom", _("top"))], default="bottom")
config.plugins.RecInfobar.background = ConfigSelection([("#00000000", _("black")),("#ffffffff", _("transparent")),("#54111112", _("transparent") + " - " + _("black"))], default="#ffffffff")
config.plugins.RecInfobar.x = ConfigInteger(default=0, limits=(0,9999))
config.plugins.RecInfobar.y = ConfigInteger(default=360, limits=(0,9999))
config.plugins.RecInfobar.always_zap = ConfigSelection([("0", _("default")),("1", _("always")),("2", _("ask the user"))], default="0")
config.plugins.RecInfobar.always_message =  ConfigYesNo(default = False)
config.plugins.RecInfobar.default_zap = ConfigSelection([("yes", _("zap")),("no", _("no zap"))], default="yes")
config.plugins.RecInfobar.check_wakeup =  ConfigYesNo(default = False)
config.plugins.RecInfobar.standby_timeout = ConfigInteger(default=10, limits=(5,180))
config.plugins.RecInfobar.after_event = ConfigSelection([("0", _("all")),("1", _("standby")),("2", _("deep standby")),("3", _("auto")),("4", _("auto and deep standby")),("5", _("all, except 'nothing'"))], default="5")
config.plugins.RecInfobar.set_position = ConfigYesNo(default = False)
config.plugins.RecInfobar.z = ConfigSelection([(str(x), str(x)) for x in range(-20,21)], "1")
config.plugins.RecInfobar.help = ConfigNothing()
config.plugins.RecInfobar.rec_indicator = ConfigYesNo(default = False)
config.plugins.RecInfobar.indicator_x = ConfigInteger(default=30, limits=(0,9999))
config.plugins.RecInfobar.indicator_y = ConfigInteger(default=30, limits=(0,9999))
TIMEFORMATS = [
	# for example, 122 seconds (zero hours, two minutes, two seconds)
	("%(SSs)d", _("S")),		#  122  
	("%(SSs)ds", _("Ss")),		#  122s
	("%(MMs)d:%(SS)d", _("M:S")),		#  2:2
	("%(MMs)dm %(SS)ds", _("Mm Ss")),	#  2m 2s
	("%(MMs)d:%(SS)02d", _("M:SS")),	#  2:02
	("%(MMs)dm %(SS)02ds", _("Mm SSs")),	#  2m 02s
	("%(MMs)02d:%(SS)02d", _("MM:SS")),		# 02:02
	("%(MMs)02dm %(SS)02ds", _("MMm SSs")),		# 02m 02s
	("%(HHs)d:%(MM)d:%(SS)d", _("H:M:S")),		# 0:2:2
	("%(HHs)dh %(MM)dm %(SS)ds", _("Hh Mm Ss")),	# 0h 2m 2s
	("%(HHs)02d:%(MM)02d:%(SS)02d", _("HH:MM:SS")),		# 00:02:02
	("%(HHs)02dh %(MM)02dm %(SS)02ds", _("HHh MMm SSs")),	# 00h 02m 02s
	("%(DDs)s %(HH)02d:%(MM)02d:%(SS)02d", _("DD HH:MM:SS")),	# 0 days 00:02:02
	("%(DD)dd %(HH)02dh %(MM)02dm %(SS)02ds", _("Dd HHh MMm SSs")),	# 0d 00h 02m 02s
]
config.plugins.RecInfobar.timelen_format = ConfigSelection(TIMEFORMATS, "%(MMs)d:%(SS)02d")
nims = [("-1", _("auto")), ("-2", _("disabled"))]
for x in nimmanager.nim_slots:
	nims.append((str(x.slot), x.getSlotName()))
config.plugins.RecInfobar.tuner_recording_priority = ConfigSelection(default = "-2", choices = nims)

class RecIndicator(Screen):
	skin = """
		<screen name="RecIndicator" title="Records Indicator" flags="wfNoBorder" position="60,60" size="36,36" zPosition="-1" backgroundColor="transparent" >
			<widget source="session.RecordState" render="Pixmap" pixmap="skin_default/icons/icon_rec.png" position="0,0" size="36,36" alphatest="on">
				<convert type="ConditionalShowHide">Blink,3000</convert>
			</widget>  
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["RecIndicator" + self.__class__.__name__, "RecIndicator"]
		config.plugins.RecInfobar.indicator_x.addNotifier(self.__changePosition, False)
		config.plugins.RecInfobar.indicator_y.addNotifier(self.__changePosition, False)
		self.onLayoutFinish.append(self.__changePosition)

	def __changePosition(self, configElement=None):
		if not self.instance is None:
			self.instance.move(ePoint(config.plugins.RecInfobar.indicator_x.value,config.plugins.RecInfobar.indicator_y.value))

FULLHD = 0
if getDesktop(0).size().width() >= 1920:
	FULLHD = 2
elif getDesktop(0).size().width() >= 1280:
	FULLHD = 1

class RecInfoBar(Screen):
	if FULLHD == 1:
		skin = """
			<screen name="RecInfoBar" position="0,80" size="1280,40" zPosition="%s" backgroundColor="%s" title="Records Info" flags="wfNoBorder" >
				<widget name="chTuner" position="0,2" size="180,18" zPosition="1" font="Regular;18" halign="left" transparent="1" noWrap="1" foregroundColor="#00879ce1" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="chProv" position="190,2" size="250,18" zPosition="1" font="Regular;18" halign="left" transparent="1" noWrap="1" foregroundColor="#00ffc000" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="chBouq" position="450,2" size="300,18" zPosition="1" font="Regular;18" halign="left" transparent="1" noWrap="1" foregroundColor="#00ffc000" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="chNum" position="760,2"  size="50,18" zPosition="1" font="Regular;18" halign="right" transparent="1" noWrap="1" foregroundColor="white" backgroundColor="black" borderColor="black" borderWidth="3" />
				<widget name="chName" position="820,2" size="300,18" zPosition="1" font="Regular;18" halign="left"  transparent="1" noWrap="1" foregroundColor="white" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="timelen" position="1130,2" size="150,18" zPosition="1" font="Regular;18" halign="center" transparent="1" noWrap="1" foregroundColor="white" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="chSnr" position="10,20" size="150,18" zPosition="1" font="Regular;18" halign="left" transparent="1" noWrap="1" foregroundColor="#00ffc000" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="remaining" position="160,20" size="480,18" zPosition="1" font="Regular;18" halign="right" transparent="1" noWrap="1" foregroundColor="white" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="recName" position="650,20" size="630,18" zPosition="1" font="Regular;18" halign="left" transparent="1" noWrap="1" foregroundColor="#00aaaaaa" backgroundColor="transparent" borderColor="black" borderWidth="3" />
			</screen>""" % (config.plugins.RecInfobar.z.value, config.plugins.RecInfobar.background.value)
	elif FULLHD == 2:
		skin = """
			<screen name="RecInfoBar" position="0,80" size="1920,60" zPosition="%s" backgroundColor="%s" title="Records Info" flags="wfNoBorder" >
				<widget name="chTuner" position="0,2" size="270,27" zPosition="1" font="Regular;27" halign="left" transparent="1" noWrap="1" foregroundColor="#00879ce1" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="chProv" position="280,2" size="375,27" zPosition="1" font="Regular;27" halign="left" transparent="1" noWrap="1" foregroundColor="#00ffc000" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="chBouq" position="675,2" size="450,27" zPosition="1" font="Regular;27" halign="left" transparent="1" noWrap="1" foregroundColor="#00ffc000" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="chNum" position="1135,2"  size="75,27" zPosition="1" font="Regular;27" halign="right" transparent="1" noWrap="1" foregroundColor="white" backgroundColor="black" borderColor="black" borderWidth="3" />
				<widget name="chName" position="1220,2" size="450,27" zPosition="1" font="Regular;27" halign="left"  transparent="1" noWrap="1" foregroundColor="white" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="timelen" position="1680,2" size="225,27" zPosition="1" font="Regular;27" halign="center" transparent="1" noWrap="1" foregroundColor="white" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="chSnr" position="10,30" size="225,27" zPosition="1" font="Regular;27" halign="left" transparent="1" noWrap="1" foregroundColor="#00ffc000" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="remaining" position="245,30" size="720,27" zPosition="1" font="Regular;27" halign="right" transparent="1" noWrap="1" foregroundColor="white" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="recName" position="975,30" size="945,27" zPosition="1" font="Regular;27" halign="left" transparent="1" noWrap="1" foregroundColor="#00aaaaaa" backgroundColor="transparent" borderColor="black" borderWidth="3" />
			</screen>""" % (config.plugins.RecInfobar.z.value, config.plugins.RecInfobar.background.value)
	else:
		skin = """
			<screen name="RecInfoBar" position="0,80" size="720,40" zPosition="%s" backgroundColor="%s" title="Records Info" flags="wfNoBorder" >
				<widget name="chTuner" position="0,2" size="180,18" zPosition="1" font="Regular;17" halign="left" transparent="1" noWrap="1" foregroundColor="#00879ce1" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="chProv" position="190,2" size="190,18" zPosition="1" font="Regular;17" halign="left" transparent="1" noWrap="1" foregroundColor="#00ffc000" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="chBouq" position="390,2" size="200,18" zPosition="1" font="Regular;17" halign="left" transparent="1" noWrap="1" foregroundColor="#00ffc000" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="chNum" position="600,2"  size="30,18" zPosition="1" font="Regular;17" halign="left" transparent="1" noWrap="1" foregroundColor="white" backgroundColor="black" borderColor="black" borderWidth="3" />
				<widget name="chName" position="640,2" size="80,18" zPosition="1" font="Regular;17" halign="left" transparent="1" noWrap="1" foregroundColor="white" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="chSnr" position="0,20" size="80,18" zPosition="1" font="Regular;17" halign="left" transparent="1" noWrap="1" foregroundColor="#00ffc000" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="timelen" position="90,20" size="130,18" zPosition="1" font="Regular;17" halign="right" transparent="1" noWrap="1" foregroundColor="white" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="remaining" position="230,20" size="240,18" zPosition="1" font="Regular;17" halign="right" transparent="1" noWrap="1" foregroundColor="white" backgroundColor="transparent" borderColor="black" borderWidth="3" />
				<widget name="recName" position="480,20" size="240,18" zPosition="1" font="Regular;17" halign="left" transparent="1" noWrap="1" foregroundColor="#00aaaaaa" backgroundColor="transparent" borderColor="black" borderWidth="3" />
			</screen>""" % (config.plugins.RecInfobar.z.value, config.plugins.RecInfobar.background.value)

	def __init__(self, session, alt_bouquet_count):
		self.reclist = {}
		self.session = session
		self.anchor = config.plugins.RecInfobar.anchor.value
		self.acount = alt_bouquet_count

		Screen.__init__(self, session)
		self.skinName = ["RecInfoBar_" + self.__class__.__name__, "RecInfoBar"]
		self.labels = ["chNum","chName","timelen","chProv","chBouq","recName","chTuner", "remaining", "chSnr"]
		for x in self.labels:
			self[x] = Label("")
		self.RecIndicator = None
		self.updateTimer = eTimer()
		self.updateTimer.callback.append(self.updateInfo)
		self.onClose.append(self.__onClose)
		self.onShow.append(self.__onShow)
		config.plugins.RecInfobar.x.addNotifier(self.__changePosition, False)
		config.plugins.RecInfobar.y.addNotifier(self.__changePosition, False)
		config.plugins.RecInfobar.rec_indicator.addNotifier(self.stateRecIndicator)
		self.onLayoutFinish.append(self.__onLayoutFinished)
		self.rec_ref = None
		self.zap_ref = None 
		self.no_decode = False
		self.SetPosition = False
		config.misc.rectimerstate.value = False
		config.misc.rectimerstate.save()
		NavigationInstance.instance.RecordTimer.on_state_change.append(self.timerEntryOnStateChange)
		config.recording.asktozap.addNotifier(self.asktozapChanged)
		if config.plugins.RecInfobar.check_wakeup.value and getFPWasTimerWakeup():
			self.checkTimer = eTimer()
			self.checkTimer.callback.append(self.checkWakeup)
			self.checkTimer.start(20000, True)

	def __changePosition(self, configElement=None):
		if not self.instance is None:
			self.instance.move(ePoint(config.plugins.RecInfobar.x.value,config.plugins.RecInfobar.y.value))
			self.def_pos = self.instance.position()

	def checkWakeup(self):
		for timer in NavigationInstance.instance.RecordTimer.timer_list:
			if timer.justplay: continue
			ret = None
			if 0 < timer.begin - Time() <= 60*5:
				if timer.afterEvent == AFTEREVENT.STANDBY:
					ret = 1
				elif timer.afterEvent == AFTEREVENT.DEEPSTANDBY:
					ret = 2
				elif timer.afterEvent == AFTEREVENT.AUTO:
					ret = 3
				else:
					ret = 4
			if ret != None and config.plugins.RecInfobar.after_event.value == "0":
				if ret == 3:
					if Standby.inStandby is None:
						Notifications.AddNotification(Standby.Standby)
				else:
					self.checkStandby()
			elif ret != None and ret != 4 and config.plugins.RecInfobar.after_event.value == "5":
				if ret == 3:
					if Standby.inStandby is None:
						Notifications.AddNotification(Standby.Standby)
				else:
					self.checkStandby()
			elif ret == 1 and config.plugins.RecInfobar.after_event.value == "1":
				self.checkStandby()
			elif ret == 2 and (config.plugins.RecInfobar.after_event.value == "2" or config.plugins.RecInfobar.after_event.value == "4"):
				self.checkStandby()
			elif ret == 3 and (config.plugins.RecInfobar.after_event.value == "3" or config.plugins.RecInfobar.after_event.value == "4"):
				if Standby.inStandby is None:
					Notifications.AddNotification(Standby.Standby)

	def checkStandby(self):
		if Standby.inStandby is None:
			try:
				self.session.openWithCallback(self.DoStandby,MessageBox,_("Go to Standby now?"),type = MessageBox.TYPE_YESNO,timeout = config.plugins.RecInfobar.standby_timeout.value)
			except:
				pass 

	def DoStandby(self,retval):
		if retval and Standby.inStandby is None:
			Notifications.AddNotification(Standby.Standby)

	def asktozapChanged(self, cfgElem):
		if not cfgElem.value and config.plugins.RecInfobar.always_zap.value == "2":
			cfgElem.value = True
			cfgElem.save()

	def stateRecIndicator(self, cfgElem):
		if not cfgElem.value:
			if self.RecIndicator is not None:
				self.RecIndicator.hide()
				self.RecIndicator = None

	def timerEntryOnStateChange(self, timer):
		if config.plugins.RecInfobar.set_position.value and not self.SetPosition:
			self.SetPosition = False
			self.zap_ref = None
			timeout = int(timer.begin - Time())
			if timeout > 1:
				self.SetPosition = True
				if timer.justplay:
					if Standby.inStandby is None:
						try:
							curservice = self.session.nav.getCurrentlyPlayingServiceOrGroup()
						except:
							curservice = self.session.nav.getCurrentlyPlayingServiceReference()
						if curservice is None or timer.service_ref.ref != curservice:
							self.zap_ref = timer.service_ref.ref
					else:
						self.zap_ref = timer.service_ref.ref
					self.zap_timer = eTimer()
					self.zap_timer.callback.append(self.GozapPosition)
					self.zap_timer.start(19000, True)
		if config.plugins.RecInfobar.always_zap.value == "1" and Standby.inStandby is None:
			self.no_decode = False
			timeout = int(timer.begin - Time())
			if timeout > 1:
				self.no_decode = True
		if config.plugins.RecInfobar.always_zap.value == "2" and Standby.inStandby is None:
				self.rec_ref = None
				timeout = int(timer.begin - Time())
				if timeout > 1 and not config.misc.rectimerstate.value:
					if not timer.justplay:
						try:
							curservice = self.session.nav.getCurrentlyPlayingServiceOrGroup()
						except:
							curservice = self.session.nav.getCurrentlyPlayingServiceReference()
						if curservice is None or timer.service_ref.ref != curservice:
							config.misc.rectimerstate.value = True 
							config.misc.rectimerstate.save()
							self.rec_ref = timer.service_ref.ref
							name = timer.service_ref.getServiceName()
							prov = self.getServiceProvider(timer.service_ref.ref)
							rec_name = timer.name
							begintime = ((timer.end - timer.begin) / 60)
							begintimestr = strftime("%H:%M ", localtime(timer.begin))
							begintimeendstr = strftime("%H:%M ", localtime(timer.end))
							default = (config.plugins.RecInfobar.default_zap.value == "yes")
							self.session.openWithCallback(self.callbackYesNo, MessageBox, _("Recording starts!\n") + _("duration:  %s ... ") % (begintimestr) + "%s " % (begintimeendstr) + _(" (%d mins)\n") % (begintime) + _("channel: %s   prov: %s\n %s\n") % (name, prov, rec_name) + "\n" +  _("Switch to a recordable channel?"), MessageBox.TYPE_YESNO, timeout = timeout, default = default)

	def GozapPosition(self):
		if self.SetPosition and self.zap_ref is not None:
			self.setZapPosition(self.zap_ref)
			self.zap_ref = None
			self.SetPosition = False

	def callbackYesNo(self, answer):
		if answer == True and self.rec_ref is not None:
			if config.plugins.RecInfobar.set_position.value and self.SetPosition:
				self.setZapPosition(self.rec_ref)
				self.SetPosition = False
			self.session.nav.playService(self.rec_ref)
		self.rec_ref = None
		self.timer = eTimer()
		self.timer.callback.append(self.asktozapGo)
		self.timer.start(30000, True)

	def asktozapGo(self):
		config.misc.rectimerstate.value = False
		config.misc.rectimerstate.save()

	def __onLayoutFinished(self):
		self.__changePosition()
		for x in self.labels:
			self[x].instance.setNoWrap(1)
		self.def_pos = self.instance.position()
		self.def_size = self.instance.size()
		self.def_hreg = max(0, self.def_size.height() - self["chName"].instance.size().height())
		self.initRecList()
		self.session.nav.record_event.append(self.gotRecordEvent)
		if len(self.reclist) == 0: self.reSize()

	def __onShow(self):
		self.updateInfo()

	def __onClose(self):
		self.session.nav.record_event.remove(self.gotRecordEvent)

	def getTimeStr(self, secs):
		dd, ss = divmod(secs, 60*60*24);
		hh, ss = divmod(ss, 60*60);
		mm, ss = divmod(ss, 60);
		return _(config.plugins.RecInfobar.timelen_format.value) % dict(
			DDs=dd and _N("%(DD)d day", "%(DD)d days", dd)%{"DD": dd} or "",
			DD=dd, HH=hh, MM=mm, SS=ss, HHs=secs/3600, MMs=secs/60, SSs=secs);

	def updateInfo(self):
		cnt = 0
		fields = ["","","","","","","","",""] # [numbers,names,timelens,providers,bouquets,recnames,tuner,remaining,snrvalue]
		for (key, value) in self.reclist.items():
			r = int( math.floor(value[7][0] - Time()))
			cnt += 1
			if cnt > 1:
				for x in range(len(fields)):
					fields[x] += '\n\n'
			fields[0] += value[0] and str(value[0]) or ''
			fields[1] += "%s"%(value[1])
			fields[2] += self.getTimeStr(Time() - value[2])
			if fields[3] != ("Unknown") or fields[3] != _("N/A"):
				fields[3] += _("Provider: %s")%(value[3])
			else:
				fields[3] += "%s"%(value[3])
			if value[4] != '':
				fields[4] += _("Bouquet: %s")%(value[4])
			else:
				fields[4] += "%s"%(value[4])
			fields[5] += "%s"%(value[5])
			if value[6] == 'Stream':
				fields[6] += _('Stream')
			else:
				fields[6] += _("Tuner: %s")%(value[6])
			fields[7] += _("+%d min / %s")%(r/60, value[7][1])
			fields[8] += self.getSignalQuality(value[8])
		cnt = 0
		for x in self.labels:
			self[x].setText(fields[cnt])
			cnt += 1
		if self.shown:
			self.updateTimer.start(1000,True)

	def getSignalQuality(self, service):
		if service and isinstance(service, iRecordableServicePtr):
			feinfo = service.frontendInfo()
			data = feinfo and feinfo.getFrontendStatus()
			if data:
				snr = data.get("tuner_signal_quality")
				if snr is not None:
					return "SNR:  %d %%" % (snr * 100 / 65536)
		return ''

	def reSize(self):
		self.updateInfo()
		if len(self.reclist) == 0:
			self.instance.resize(eSize(self.def_size.width(), 0))
		else:
			height = self["chName"].instance.calculateSize().height() + 9
			for x in self.labels:
				self[x].instance.resize(eSize(self[x].instance.size().width(), height))
			height += self.def_hreg
			self.instance.resize(eSize(self.def_size.width(), height))
			if self.anchor == "bottom":
				y = self.def_pos.y() + self.def_size.height() - height
				self.instance.move(ePoint(self.def_pos.x(), y))

	def initRecList(self):
		for rec in self.session.nav.getRecordings():
			self.gotRecordEvent(rec, iRecordableService.evStart)

	def gotRecordEvent(self, service, event):
		if event in (iRecordableService.evEnd, iRecordableService.evStart):
			key = service.__deref__()
			if event == iRecordableService.evStart:
				for timer in self.session.nav.RecordTimer.timer_list:
					if timer.record_service and timer.record_service.__deref__() == key:
						try:
							curservice = self.session.nav.getCurrentlyPlayingServiceOrGroup()
						except:
							curservice = self.session.nav.getCurrentlyPlayingServiceReference()
						if config.plugins.RecInfobar.set_position.value and self.SetPosition and Standby.inStandby is None and (curservice is None or timer.service_ref.ref == curservice):
							if timer.service_ref.ref != eServiceReference(config.tv.lastservice.value):
								self.setZapPosition(timer.service_ref.ref, SetCurTimer=True)
								self.SetPosition = False
						name = timer.service_ref.getServiceName()
						begin = timer.begin
						if (Time() - begin) >= 60:
							begin = Time()
						end = timer.end
						if end <= begin:
							end += 3600 * 24 
						beginstr = strftime("%H:%M", localtime(begin))
						endstr = strftime("%H:%M", localtime(end))
						duration = ((end - begin) / 60)
						remaining = (end, _("%s...%s (%d mins)") % (beginstr, endstr, duration))
						num, bqname = self.getServiceNumber(timer.service_ref.ref)
						prov = self.getServiceProvider(timer.service_ref.ref)
						recname = timer.name
						tunnum, tunname = self.getTunerName(timer.record_service)
						if "%3a//" in timer.service_ref.ref.toString().lower():
							tunname = 'Stream'
						self.reclist[service] = [num, name, begin, prov, bqname, recname, tunname, remaining, timer.record_service]
						if config.plugins.RecInfobar.always_zap.value == "1" and self.no_decode == True and Standby.inStandby is None:
							self.no_decode = False 
							try:
								curservice = self.session.nav.getCurrentlyPlayingServiceOrGroup()
							except:
								curservice = self.session.nav.getCurrentlyPlayingServiceReference()
							if curservice is None or timer.service_ref.ref != curservice:
								if config.plugins.RecInfobar.set_position.value and self.SetPosition:
									self.setZapPosition(timer.service_ref.ref)
									self.SetPosition = False
								self.session.nav.playService(timer.service_ref.ref)
								if config.plugins.RecInfobar.always_message.value is True:
									if config.usage.show_message_when_recording_starts.value:
										self.session.open(MessageBox, _("Switched to the recording service !\n") + _("channel: %s   prov: %s\n") % (name, prov), MessageBox.TYPE_INFO, timeout = 2)
									else:
										self.session.open(MessageBox, _("Switched to the recording service !\n")  + _("channel: %s   prov: %s\n %s\n") % (name, prov, recname), MessageBox.TYPE_INFO, timeout = 5)
				if config.plugins.RecInfobar.rec_indicator.value:
					if self.RecIndicator is None:
						self.RecIndicator = self.session.instantiateDialog(RecIndicator)
						if self.RecIndicator is not None:
							self.RecIndicator.show()
					else:
						self.RecIndicator.show()
			elif event == iRecordableService.evEnd:
				for (k, val) in self.reclist.items():
					if k.__deref__() == key:
						del self.reclist[k]
						break
					if len(self.reclist) == 0:
						if self.RecIndicator is not None:
							self.RecIndicator.hide()
			self.reSize()

	def setZapPosition(self, ref, SetCurTimer = False):
		def searchHelper(serviceHandler, num, bouquet):
			servicelist = serviceHandler.list(bouquet)
			if not servicelist is None:
				while True:
					s = servicelist.getNext()
					if not s.valid(): break
					if not (s.flags & (eServiceReference.isMarker|eServiceReference.isDirectory)):
						num += 1
						if s == ref: return s, num
			return None, num

		if isinstance(ref, eServiceReference):
			isRadioService = ref.getData(0) in (2,10)
			if not isRadioService:
				lastpath = config.tv.lastroot.value
				if lastpath.find('FROM BOUQUET') == -1:
					try:
						currentService = self.session.nav.getCurrentlyPlayingServiceOrGroup()
					except:
						currentService = self.session.nav.getCurrentlyPlayingServiceReference()
					if currentService is not None and ref == currentService:
						if 'FROM PROVIDERS' in lastpath:
							return 'P', _('Provider')
						if 'FROM SATELLITES' in lastpath:
							return 'S', _('Satellites')
						if ') ORDER BY name' in lastpath:
							return 'A', _('All Services')
						return 0, _('N/A')
				try:
					acount = config.plugins.NumberZapExt.enable.value and config.plugins.NumberZapExt.acount.value or config.usage.alternative_number_mode.value
				except:
					acount = False
				rootstr = ''
				for x in lastpath.split(';'):
					if x != '': rootstr = x
				service = None
				serviceHandler = eServiceCenter.getInstance()
				if not config.usage.multibouquet.value:
					rootbouquet = eServiceReference(rootstr)
					bouquet = eServiceReference(rootstr)
					service, number = searchHelper(serviceHandler, 0, bouquet)
				else:
					bqrootstr = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
					number = 0
					rootbouquet = eServiceReference(bqrootstr)
					bouquet = eServiceReference(bqrootstr)
					bouquetlist = serviceHandler.list(bouquet)
					if not bouquetlist is None:
						while True:
							bouquet = bouquetlist.getNext()
							if not bouquet.valid(): break
							if bouquet.flags & eServiceReference.isDirectory and not bouquet.flags & eServiceReference.isInvisible:
								service, number = searchHelper(serviceHandler, number, bouquet)
								if service and number > 0: break
								#if acount: break
				if not service is None and number > 0:
					from Screens.InfoBar import InfoBar
					try:
						InfoBarInstance = InfoBar.instance
					except:
						InfoBarInstance = None
					if InfoBarInstance is not None:
						InfoBarInstance.servicelist.clearPath()
						InfoBarInstance.servicelist.setRoot(bouquet)
						InfoBarInstance.servicelist.enterPath(rootbouquet)
						InfoBarInstance.servicelist.enterPath(bouquet)
						InfoBarInstance.servicelist.saveRoot()
						InfoBarInstance.servicelist.saveChannel(ref)
						InfoBarInstance.servicelist.addToHistory(ref)
						if SetCurTimer:
							InfoBarInstance.servicelist.setCurrentSelection(ref)

	def getServiceNumber(self, ref):
		def searchHelper(serviceHandler, num, bouquet):
			servicelist = serviceHandler.list(bouquet)
			if not servicelist is None:
				while True:
					s = servicelist.getNext()
					if not s.valid(): break
					if not (s.flags & (eServiceReference.isMarker|eServiceReference.isDirectory)):
						num += 1
						if s == ref: return s, num
			return None, num

		if isinstance(ref, eServiceReference):
			isRadioService = ref.getData(0) in (2,10)
			lastpath = isRadioService and config.radio.lastroot.value or config.tv.lastroot.value
			if lastpath.find('FROM BOUQUET') == -1:
				try:
					currentService = self.session.nav.getCurrentlyPlayingServiceOrGroup()
				except:
					currentService = self.session.nav.getCurrentlyPlayingServiceReference()
				if currentService is not None and ref == currentService:
					if 'FROM PROVIDERS' in lastpath:
						return 'P', _('Provider')
					if 'FROM SATELLITES' in lastpath:
						return 'S', _('Satellites')
					if ') ORDER BY name' in lastpath:
						return 'A', _('All Services')
					return 0, _('N/A')
			try:
				acount = config.plugins.NumberZapExt.enable.value and config.plugins.NumberZapExt.acount.value or config.usage.alternative_number_mode.value
			except:
				acount = False
			rootstr = ''
			for x in lastpath.split(';'):
				if x != '': rootstr = x
			service = None
			serviceHandler = eServiceCenter.getInstance()
			if acount is True or not config.usage.multibouquet.value:
				bouquet = eServiceReference(rootstr)
				service, number = searchHelper(serviceHandler, 0, bouquet)
			else:
				if isRadioService:
					bqrootstr = '1:7:2:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.radio" ORDER BY bouquet'
				else:
					bqrootstr = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
				number = 0
				bouquet = eServiceReference(bqrootstr)
				bouquetlist = serviceHandler.list(bouquet)
				if not bouquetlist is None:
					while True:
						bouquet = bouquetlist.getNext()
						if not bouquet.valid(): break
						if bouquet.flags & eServiceReference.isDirectory and not bouquet.flags & eServiceReference.isInvisible:
							service, number = searchHelper(serviceHandler, number, bouquet)
							if service and number > 0: break
			if not service is None:
				info = serviceHandler.info(bouquet)
				name = info and info.getName(bouquet) or ''
				return number, name
		return 0, ''

	def getServiceProvider(self, ref):
		if isinstance(ref, eServiceReference):
			str_ref = ref.toString()
			if str_ref.startswith('1:134:'):
				ref = getBestPlayableServiceReference(ref, eServiceReference())
				if not ref:
					return _("N/A")
			typestr = ref.getData(0) in (2,10) and service_types_radio or service_types_tv
			pos = typestr.rfind(':')
			rootstr = '%s (channelID == %08x%04x%04x) && %s FROM PROVIDERS ORDER BY name'%(typestr[:pos+1],
				ref.getUnsignedData(4), # NAMESPACE
				ref.getUnsignedData(2), # TSID
				ref.getUnsignedData(3), # ONID
				typestr[pos+1:])
			provider_root = eServiceReference(rootstr)
			serviceHandler = eServiceCenter.getInstance()
			providerlist = serviceHandler.list(provider_root)
			if not providerlist is None:
				while True:
					provider = providerlist.getNext()
					if not provider.valid(): break
					if provider.flags & eServiceReference.isDirectory:
						servicelist = serviceHandler.list(provider)
						if not servicelist is None:
							while True:
								service = servicelist.getNext()
								if not service.valid(): break
								if service == ref:
									info = serviceHandler.info(provider)
									name = info and info.getName(provider) or _("Unknown")
									return name
		return _("N/A")

	def getTunerName(self, service):
		number = -2
		tunerType = ''
		if isinstance(service, iRecordableServicePtr):
			feinfo = service.frontendInfo()
			data = feinfo and feinfo.getFrontendData()
			if data:
				number = data.get("tuner_number", number)
				type = data.get("tuner_type", '')
				if type: 
					tunerType = ' (%s)' % type
		name = chr(number+65) + tunerType
		return number, name

	def doShow(self, parent):
		if isinstance(parent, InfoBarEPG):
			self.show()

	def doHide(self):
		if self.shown:
			self.hide()
			try:
				if len(self.reclist) > 0 and self.session.nav.getRecordings():
					for (k, val) in self.reclist.items():
						for timer in NavigationInstance.instance.RecordTimer.timer_list + NavigationInstance.instance.RecordTimer.processed_timers:
							if timer.record_service and timer.record_service.__deref__() == k.__deref__():
								if timer.end != val[7][0]:
									begin = val[2]
									end = timer.end
									if end <= begin:
										end += 3600 * 24 
									beginstr = strftime("%H:%M", localtime(begin))
									endstr = strftime("%H:%M", localtime(end))
									duration = ((end - begin) / 60)
									remaining = (end, _("%s...%s (%d mins)") % (beginstr, endstr, duration))
									reclist = [val[0], val[1], val[2], val[3], val[4], val[5], val[6], remaining, val[8]]
									service = k
									del self.reclist[k]
									self.reclist[service] = reclist
			except:
				pass

def RecInfobarRecordService(ref, simulate=False):
	service = None
	change_frontend = False
	if RecordService:
		global PrevFrontendPriority
		tuner_recording_priority = config.plugins.RecInfobar.tuner_recording_priority.value
		PrevFrontendPriority = config.usage.frontend_priority.value
		if ref and not simulate and tuner_recording_priority != "-2":
			if config.usage.frontend_priority.value != tuner_recording_priority:
				config.usage.frontend_priority.value = tuner_recording_priority
				change_frontend = True
		service = RecordService(ref, simulate)
		if change_frontend:
			setDefaultFrontendPriority(_session, timeout=service)
	return service

class setDefaultFrontendPriority:
	def __init__(self, session, timeout=None):
		self.session = session
		if timeout is None:
			self.savingDefaultFrontend()
		else:
			self.waitSavingTimer = eTimer()
			self.waitSavingTimer.callback.append(self.savingDefaultFrontend)
			if not self.waitSavingTimer.isActive():
				self.waitSavingTimer.start(5000, True)

	def savingDefaultFrontend(self):
		global PrevFrontendPriority
		if PrevFrontendPriority is not None:
			config.usage.frontend_priority.value = PrevFrontendPriority
			config.usage.frontend_priority.save()
			PrevFrontendPriority = None

def newInfoBarShowHide__init__(self):
	try:
		cgfNZE = config.plugins.NumberZapExt
		acount = cgfNZE.enable.value and cgfNZE.acount.value
	except:
		acount = False
	self.recDialog = self.session.instantiateDialog(RecInfoBar, acount)
	baseInfoBarShowHide__init__(self)
	self.onShow.append(boundFunction(self.recDialog.doShow, self))
	self.onHide.append(self.recDialog.doHide)

def StartMainSession(reason, session, **kwargs):
	if reason == 0 and session and _session is None and config.usage.recinfobar.value:
		global baseInfoBarShowHide__init__, RecordService, _session
		_session = session
		if RecordService is None:
			try:
				RecordService = session.nav.recordService
				session.nav.recordService = RecInfobarRecordService
			except:
				RecordService = None
		if baseInfoBarShowHide__init__ is None:
			baseInfoBarShowHide__init__ = InfoBarShowHide.__init__
			InfoBarShowHide.__init__ = newInfoBarShowHide__init__

def OpenSetup(session, **kwargs):
	import RecInfobarSetup
	session.open(RecInfobarSetup.RecInfobarSetupScreen)

def StartSetup(menuid, **kwargs):
	if menuid == "system":
		return [(_("Record Infobar"), OpenSetup, "recinfobar_setup", None)]
	else:
		return []


def Plugins(**kwargs):
	return [PluginDescriptor(name=_("Record Infobar"), description=_("Record Infobar addon"), where = PluginDescriptor.WHERE_SESSIONSTART, fnc = StartMainSession),
		PluginDescriptor(name=_("Record Infobar"), description=_("Record Infobar addon"), where = PluginDescriptor.WHERE_MENU, fnc = StartSetup)]
