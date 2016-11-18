# for localized messages
from . import _
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap
from Components.Label import Label
from Screens.ChannelSelection import ChannelContextMenu, OFF, MODE_TV, service_types_tv
from Components.ChoiceList import ChoiceEntryComponent
from enigma import eServiceReference, eTimer, getDesktop, eServiceCenter, getBestPlayableServiceReference, ePoint, eEPGCache, iPlayableService, eEnv
from ServiceReference import ServiceReference, isPlayableForCur
from Components.SystemInfo import SystemInfo
from Components.VideoWindow import VideoWindow
from time import localtime, time
from Screens.InfoBarGenerics import InfoBarShowHide, NumberZap, InfoBarPiP
from Screens.InfoBar import InfoBar
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Screens.MessageBox import MessageBox
from Screens.HelpMenu import HelpableScreen
from Screens.Standby import TryQuitMainloop
from Screens.EpgSelection import EPGSelection
from Screens.EventView import  EventViewEPGSelect
from Screens.PictureInPicture import PictureInPicture, pip_config_initialized
from Tools.BoundFunction import boundFunction
from Tools.Directories import fileExists
import Components.ParentalControl
from Components.config import config, ConfigSubsection, ConfigSelection, ConfigYesNo, getConfigListEntry, configfile, ConfigPosition, ConfigText, ConfigInteger
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.Sources.FrontendStatus import FrontendStatus
from Components.NimManager import nimmanager
from Components.Renderer.Picon import getPiconName
from DishPiP import DishPiP

try:
	from Plugins.SystemPlugins.PiPServiceRelation.plugin import getRelationDict, CONFIG_FILE
	plugin_PiPServiceRelation_installed = True
except:
	plugin_PiPServiceRelation_installed = False

try:
	exit_button = config.usage.ok_is_channelselection
except:
	exit_button = None

try:
	cursor_behavior = config.usage.servicelist_cursor_behavior
except:
	cursor_behavior = None

try:
	oldstyle_zap_controls = config.usage.oldstyle_zap_controls
except:
	oldstyle_zap_controls = None

try:
	show_simple_second_infobar = config.usage.show_simple_second_infobar
except:
	show_simple_second_infobar = None

InfoBarShowHideINIT = None
baseEVZChannelContextMenuINIT = None

MAX_X = 720
MAX_Y = 576

config.plugins.extvirtualzap = ConfigSubsection()
config.plugins.extvirtualzap.mode = ConfigSelection(default="0", choices = [("0", _("as plugin in extended menu")),("1", _("with long OK press")), ("2", _("with exit button")), ("3", _("disable")), ("4", _("as plugin in event menu"))])
config.plugins.extvirtualzap.event_menu = ConfigSelection(default="0", choices = [("0", _("disabled")),("1", _("EPGSelection (context menu)")), ("2", _("EventView (context menu)")), ("3", _("EPGSelection/EventView (context menu)"))])
config.plugins.extvirtualzap.usepip = ConfigYesNo(default = True)
config.plugins.extvirtualzap.show_dish = ConfigYesNo(default = True)
config.plugins.extvirtualzap.showpipininfobar = ConfigYesNo(default = True)
config.plugins.extvirtualzap.saveLastService = ConfigYesNo(default = False)
config.plugins.extvirtualzap.saveLastServiceMode = ConfigSelection(default = "always", choices = [("always", _("always")), ("1", _("1 minute")),("5", _("5 minutes")),("15", _("15 minutes")), ("30", _("30 minutes")),("45", _("45 minutes")),("60", _("60 minutes")), ("120", _("2 hours")),("180", _("3 hours")),("360", _("6 hours")), ("720", _("12 hours")),("1440",_("24 hours")), ("standby", _("until standby/restart"))])
config.plugins.extvirtualzap.exit_button = ConfigYesNo(default = False)
config.plugins.extvirtualzap.picons = ConfigYesNo(default = False)
config.plugins.extvirtualzap.pipservicerelation = ConfigYesNo(default = True)
config.plugins.extvirtualzap.channelselection_contextmenu = ConfigYesNo(default = False)
config.plugins.extvirtualzap.curref = ConfigText()
config.plugins.extvirtualzap.curbouquet = ConfigText()
config.plugins.extvirtualzap.exittimer = ConfigInteger(0,limits = (0, 120))

if not config.plugins.extvirtualzap.saveLastService.value or config.plugins.extvirtualzap.saveLastServiceMode.value == 'standby':
	config.plugins.extvirtualzap.curref.value = ""
	config.plugins.extvirtualzap.curbouquet.value = ""
	config.plugins.extvirtualzap.curref.save()
	config.plugins.extvirtualzap.curbouquet.save()

class RememberLastService:
	"""Clear Last Service"""
	def __init__(self):
		self.clearTimer = eTimer()
		self.clearTimer.timeout.get().append(self.clearLastService)
		config.misc.standbyCounter.addNotifier(self.standbyCounterCallback, initial_call = False)

	def startClearLastService(self):
		mode = config.plugins.extvirtualzap.saveLastServiceMode.value
		self.clearTimer.stop()
		if mode != "standby" and mode != "always":
			self.clearTimer.start(int(mode)*60*1000,True)

	def clearLastService(self):
		config.plugins.extvirtualzap.curref.value = ""
		config.plugins.extvirtualzap.curbouquet.value = ""
		config.plugins.extvirtualzap.curref.save()
		config.plugins.extvirtualzap.curbouquet.save()

	def standbyCounterCallback(self, ConfigElement):
		if config.plugins.extvirtualzap.saveLastService.value and config.plugins.extvirtualzap.saveLastServiceMode.value == 'standby':
			self.clearLastService()

currentRememberLastService = RememberLastService()

class ExtendedVirtualZap(Screen, HelpableScreen):
	sz_w = getDesktop(0).size().width()
	sz_h = getDesktop(0).size().height()
	usepip = False
	pipDecoder = SystemInfo.get("NumVideoDecoders", 1) > 1
	if pipDecoder:
		if not pip_config_initialized:
			config.av.pip = ConfigPosition(default=[510, 28, 180, 135], args = (MAX_X, MAX_Y, MAX_X, MAX_Y))
		x = config.av.pip.value[0]
		y = config.av.pip.value[1]
		w = config.av.pip.value[2]
		h = config.av.pip.value[3]
	else:
		x = 0
		y = 0
		w = 0
		h = 0
	if pipDecoder and config.plugins.extvirtualzap.usepip.value and config.plugins.extvirtualzap.showpipininfobar.value:
		if sz_w >= 1920:
			pos1 = 1270
			pos2 = 1270
			pos3 = 0
			pos4 = 0
			if config.plugins.extvirtualzap.picons.value:
				pos1 = 1150
				pos2 = 1150
				pos3 = 1650
				pos4 = 105
			skin = """
				<screen backgroundColor="#101214" flags="wfNoBorder" name="ExtendedVirtualZap" position="0,820" size="1920,350" zPosition="0" title="Extended Virtual Zap">
					<ePixmap alphatest="off" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/VirtualZap/fullhd.png" zPosition="0" position="0,0" size="1920,350"/>
					<widget backgroundColor="#101214" foregroundColor="#f23d21" font="Regular;25" halign="left" name="errorPiP" position="30,1" size="330,27" transparent="1" zPosition="2"/>
					<widget name="video" backgroundColor="transparent" position="50,50" zPosition="1" size="284,190"/>
					<widget backgroundColor="#101214" font="Regular;36" halign="left" name="NowNum" position="395,60" size="100,40" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" font="Regular;39" halign="left" name="NowChannel" position="465,60" size="787,42" transparent="1" zPosition="1"/>
					<widget foregroundColor="#0058bcff" name="nowProgress" position="365,40" size="900,15" borderWidth="2" borderColor="#cccccc" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" name="nowPercent" position="1300,36" size="70,27" font="Regular;25" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" font="Regular;30" halign="right" name="NowTuner" foregroundColor="#00999999" position="1500,60" size="300,32" transparent="1" zPosition="1"/>
					<widget backgroundColor="#101214" font="Regular;36" foregroundColor="#fcc000" halign="left" name="NowEPG" position="405,105" size="800,38" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" font="Regular;36" halign="left" name="NextEPG" position="405,140" size="800,38" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" font="Regular;36" foregroundColor="#fcc000" halign="right" name="NowTime" position="%d,105" size="250,38" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" font="Regular;36" halign="right" name="NextTime" position="%d,140" size="250,38" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" name="servicePicon" position="%d,%d" size="200,120" alphatest="on" zPosition="2"/>
					<widget source="Frontend" render="Progress" position="610,195" size="600,30" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/VirtualZap/bar_big.png" zPosition="2" borderWidth="2" borderColor="#cccccc">
						<convert type="FrontendInfo">SNR</convert>
					</widget>
					<eLabel text="SNR:" position="400,195" size="70,30" font="Regular;27" backgroundColor="#101214" halign="left" transparent="1" zPosition="2"/>
					<widget source="Frontend" render="Label" position="475,195" size="100,30" font="Regular;27" halign="left" backgroundColor="#101214" transparent="1" zPosition="2">
						<convert type="FrontendInfo">SNR</convert>
					</widget>
					<widget source="Frontend" render="Label" position="1230,195" size="150,230" font="Regular;27" halign="left" backgroundColor="#101214" transparent="1" zPosition="2">
						<convert type="FrontendInfo">SNRdB</convert>
					</widget>
					<eLabel text="AGC:" position="1400,195" size="70,30" font="Regular;27" backgroundColor="#101214" halign="left" transparent="1" zPosition="2"/>
					<widget source="Frontend" render="Label" position="1475,195" size="150,30" font="Regular;27" halign="left" backgroundColor="#101214" transparent="1" zPosition="2">
						<convert type="FrontendInfo">AGC</convert>
					</widget>
				</screen>""" % (pos1,pos2,pos3,pos4)
		elif sz_w >= 1280:
			pos1 = 1070
			pos2 = 1070
			pos3 = 0
			pos4 = 0
			if config.plugins.extvirtualzap.picons.value:
				pos1 = 950
				pos2 = 950
				pos3 = 1150
				pos4 = 105
			skin = """
				<screen backgroundColor="#101214" flags="wfNoBorder" name="ExtendedVirtualZap" position="0,490" size="1280,220" zPosition="0" title="Extended Virtual Zap">
					<ePixmap alphatest="off" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/VirtualZap/hd.png" zPosition="0" position="0,0" size="1280,220"/>
					<widget backgroundColor="#101214" foregroundColor="#f23d21" font="Regular;16" halign="left" name="errorPiP" position="20,1" size="250,18" transparent="1" zPosition="2"/>
					<widget name="video" backgroundColor="transparent" position="20,50" zPosition="1" size="254,160"/>
					<widget backgroundColor="#101214" font="Regular;24" halign="left" name="NowNum" position="295,60" size="60,28" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" font="Regular;26" halign="left" name="NowChannel" position="365,60" size="687,32" transparent="1" zPosition="1"/>
					<widget foregroundColor="#0058bcff" name="nowProgress" position="365,40" size="700,10" borderWidth="2" borderColor="#cccccc" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" name="nowPercent" position="1100,36" size="50,20" font="Regular;18" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" font="Regular;20" halign="right" name="NowTuner" foregroundColor="#00999999" position="1000,60" size="200,22" transparent="1" zPosition="1"/>
					<widget backgroundColor="#101214" font="Regular;24" foregroundColor="#fcc000" halign="left" name="NowEPG" position="305,105" size="600,28" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" font="Regular;24" halign="left" name="NextEPG" position="305,140" size="600,28" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" font="Regular;24" foregroundColor="#fcc000" halign="right" name="NowTime" position="%d,105" size="124,28" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" font="Regular;24" halign="right" name="NextTime" position="%d,140" size="124,28" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" name="servicePicon" position="%d,%d" size="100,60" alphatest="on" zPosition="2"/>
					<widget source="Frontend" render="Progress" position="440,190" size="300,20" pixmap="skin_default/bar_snr.png" zPosition="2" borderWidth="2" borderColor="#cccccc">
						<convert type="FrontendInfo">SNR</convert>
					</widget>
					<eLabel text="SNR:" position="300,190" size="53,22" font="Regular;18" backgroundColor="#101214" halign="left" transparent="1" zPosition="2"/>
					<widget source="Frontend" render="Label" position="355,190" size="70,22" font="Regular;18" halign="left" backgroundColor="#101214" transparent="1" zPosition="2">
						<convert type="FrontendInfo">SNR</convert>
					</widget>
					<widget source="Frontend" render="Label" position="750,190" size="100,22" font="Regular;18" halign="left" backgroundColor="#101214" transparent="1" zPosition="2">
						<convert type="FrontendInfo">SNRdB</convert>
					</widget>
					<eLabel text="AGC:" position="870,190" size="53,22" font="Regular;18" backgroundColor="#101214" halign="left" transparent="1" zPosition="2"/>
					<widget source="Frontend" render="Label" position="925,190" size="100,22" font="Regular;18" halign="left" backgroundColor="#101214" transparent="1" zPosition="2">
						<convert type="FrontendInfo">AGC</convert>
					</widget>
				</screen>""" % (pos1,pos2,pos3,pos4)
		else:
			pos1 = 550
			pos2 = 550
			pos3 = 0
			pos4 = 0
			if config.plugins.extvirtualzap.picons.value:
				pos1 = 500
				pos2 = 500
				pos3 = 640
				pos4 = 55
			skin = """
				<screen backgroundColor="#101214" flags="wfNoBorder" name="ExtendedVirtualZap" position="0,390" size="720,176" title="Extended Virtual Zap">
					<ePixmap alphatest="off" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/VirtualZap/sd.png" position="0,0" size="720,176" zPosition="0"/>
					<widget backgroundColor="transparent" name="video" position="20,30" size="140,110" zPosition="1"/>
					<widget backgroundColor="#101214" foregroundColor="#f23d21" font="Regular;16" halign="left" name="errorPiP" position="20,1" size="220,18" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" font="Regular;20" halign="left" name="NowNum" position="190,25" size="50,24" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" font="Regular;22" halign="left" name="NowChannel" position="250,25" size="300,25" transparent="1" zPosition="2"/>
					<widget foregroundColor="#0058bcff" name="nowProgress" position="250,5" size="300,10" borderWidth="2" borderColor="#cccccc" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" name="nowPercent" position="560,1" size="50,20" font="Regular;18" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" font="Regular;18" halign="right" name="NowTuner" foregroundColor="#00999999" position="550,25" size="150,20" transparent="1" zPosition="1"/>
					<widget backgroundColor="#101214" font="Regular;18" foregroundColor="#fcc000" halign="left" name="NowEPG" position="190,55" size="300,20" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" font="Regular;18" halign="left" name="NextEPG" position="190,80" size="300,20" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" font="Regular;20" foregroundColor="#fcc000" halign="right" name="NowTime" position="%d,55" size="120,25" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" font="Regular;20" halign="right" name="NextTime" position="%d,80" size="120,25" transparent="1" zPosition="2"/>
					<widget backgroundColor="#101214" name="servicePicon" position="%d,%d" size="70,53" alphatest="on" zPosition="2"/>
					<widget source="Frontend" render="Progress" position="320,130" size="150,20" pixmap="skin_default/bar_snr.png" zPosition="2" borderWidth="2" borderColor="#cccccc">
						<convert type="FrontendInfo">SNR</convert>
					</widget>
					<eLabel text="SNR:" position="190,130" size="53,22" font="Regular;18" backgroundColor="#101214" halign="left" transparent="1" zPosition="2"/>
					<widget source="Frontend" render="Label" position="245,130" size="70,22" font="Regular;18" halign="left" backgroundColor="#101214" transparent="1" zPosition="2">
						<convert type="FrontendInfo">SNR</convert>
					</widget>
					<widget source="Frontend" render="Label" position="480,130" size="100,22" font="Regular;18" halign="left" backgroundColor="#101214" transparent="1" zPosition="2">
						<convert type="FrontendInfo">SNRdB</convert>
					</widget>
					<eLabel text="AGC:" position="600,130" size="53,22" font="Regular;18" backgroundColor="#101214" halign="left" transparent="1" zPosition="2"/>
					<widget source="Frontend" render="Label" position="655,130" size="70,22" font="Regular;18" halign="left" backgroundColor="#101214" transparent="1" zPosition="2">
						<convert type="FrontendInfo">AGC</convert>
					</widget>
				</screen>""" % (pos1,pos2,pos3,pos4)
	else:
		if pipDecoder and config.plugins.extvirtualzap.usepip.value and not config.plugins.extvirtualzap.showpipininfobar.value:
			usepip = True
			x = config.av.pip.value[0]
			y = config.av.pip.value[1]
			w = config.av.pip.value[2]
			h = config.av.pip.value[3]
		else:
			x = 0
			y = 0
			w = 0
			h = 0
		if usepip:
			if sz_w >= 1920:
				pos1 = 1270
				pos2 = 1270
				pos3 = 0
				pos4 = 0
				if config.plugins.extvirtualzap.picons.value:
					pos1 = 1150
					pos2 = 1150
					pos3 = 1650
					pos4 = 920
				skin = """
					<screen backgroundColor="transparent" flags="wfNoBorder" name="ExtendedVirtualZapNoPiP" position="0,0" size="1920,1080" title="Extended Virtual Zap">
						<widget backgroundColor="transparent" name="video" position="%d,%d" size="%d,%d" zPosition="1"/>
						<ePixmap alphatest="off" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/VirtualZap/fullhd.png" zPosition="0" position="0,820" size="1920,350"/>
						<widget backgroundColor="#101214" foregroundColor="#f23d21" font="Regular;25" halign="left" name="errorPiP" position="30,821" size="330,27" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;36" halign="left" name="NowNum" position="395,880" size="100,40" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;39" halign="left" name="NowChannel" position="465,880" size="787,42" transparent="1" zPosition="1"/>
						<widget foregroundColor="#0058bcff" name="nowProgress" position="365,860" size="900,15" borderWidth="2" borderColor="#cccccc" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" name="nowPercent" position="1300,856" size="70,27" font="Regular;25" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;30" halign="right" name="NowTuner" foregroundColor="#00999999" position="1500,880" size="300,32" transparent="1" zPosition="1"/>
						<widget backgroundColor="#101214" font="Regular;36" foregroundColor="#fcc000" halign="left" name="NowEPG" position="405,925" size="800,38" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;36" halign="left" name="NextEPG" position="405,960" size="800,38" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;36" foregroundColor="#fcc000" halign="right" name="NowTime" position="%d,925" size="250,38" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;36" halign="right" name="NextTime" position="%d,960" size="250,38" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" name="servicePicon" position="%d,%d" size="200,120" alphatest="on" zPosition="2"/>
						<widget source="Frontend" render="Progress" position="610,1015" size="600,30" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/VirtualZap/bar_big.png" zPosition="2" borderWidth="2" borderColor="#cccccc">
							<convert type="FrontendInfo">SNR</convert>
						</widget>
						<eLabel text="SNR:" position="400,1015" size="70,30" font="Regular;27" backgroundColor="#101214" halign="left" transparent="1" zPosition="2"/>
						<widget source="Frontend" render="Label" position="475,1015" size="100,30" font="Regular;27" halign="left" backgroundColor="#101214" transparent="1" zPosition="2">
							<convert type="FrontendInfo">SNR</convert>
						</widget>
						<widget source="Frontend" render="Label" position="1230,1015" size="150,230" font="Regular;27" halign="left" backgroundColor="#101214" transparent="1" zPosition="2">
							<convert type="FrontendInfo">SNRdB</convert>
						</widget>
						<eLabel text="AGC:" position="1400,1015" size="70,30" font="Regular;27" backgroundColor="#101214" halign="left" transparent="1" zPosition="2"/>
						<widget source="Frontend" render="Label" position="1475,1015" size="150,30" font="Regular;27" halign="left" backgroundColor="#101214" transparent="1" zPosition="2">
							<convert type="FrontendInfo">AGC</convert>
						</widget>
					</screen>""" % (x,y,w,h,pos1,pos2,pos3,pos4)
			elif sz_w >= 1280:
				pos1 = 1015
				pos2 = 1015
				pos3 = 0
				pos4 = 0
				if config.plugins.extvirtualzap.picons.value:
					pos1 = 950
					pos2 = 950
					pos3 = 1150
					pos4 = 590
				skin = """
					<screen backgroundColor="transparent" flags="wfNoBorder" name="ExtendedVirtualZapNoPiP" position="0,0" size="1280,720" title="Extended Virtual Zap">
						<widget backgroundColor="transparent" name="video" position="%d,%d" size="%d,%d" zPosition="1"/>
						<ePixmap alphatest="off" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/VirtualZap/hd.png" position="0,485" size="1280,220" zPosition="0"/>
						<widget backgroundColor="#101214" foregroundColor="#f23d21" font="Regular;16" halign="left" name="errorPiP" position="20,505" size="250,18" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;24" halign="left" name="NowNum" position="70,545" size="60,28" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;26" halign="left" name="NowChannel" position="140,545" size="700,30" transparent="1" zPosition="2"/>
						<widget foregroundColor="#0058bcff" name="nowProgress" position="140,525" size="700,10" borderWidth="2" borderColor="#cccccc" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" name="nowPercent" position="875,521" size="50,20" font="Regular;18" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;20" halign="right" name="NowTuner" foregroundColor="#00999999" position="1000,545" size="200,22" transparent="1" zPosition="1"/>
						<widget backgroundColor="#101214" font="Regular;24" foregroundColor="#fcc000" halign="left" name="NowEPG" position="140,590" size="760,28" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;24" halign="left" name="NextEPG" position="140,625" size="760,28" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;24" foregroundColor="#fcc000" halign="right" name="NowTime" position="%d,590" size="124,28" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;24" halign="right" name="NextTime" position="%d,625" size="124,28" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" name="servicePicon" position="%d,%d" size="100,60" alphatest="on" zPosition="2"/>
						<widget source="Frontend" render="Progress" position="275,670" size="300,20" pixmap="skin_default/bar_snr.png" zPosition="2" borderWidth="2" borderColor="#cccccc">
							<convert type="FrontendInfo">SNR</convert>
						</widget>
						<eLabel text="SNR:" position="140,670" size="53,22" font="Regular;18" backgroundColor="#101214" halign="left" transparent="1" zPosition="2"/>
						<widget source="Frontend" render="Label" position="195,670" size="70,22" font="Regular;18" halign="left" backgroundColor="#101214" transparent="1" zPosition="2">
							<convert type="FrontendInfo">SNR</convert>
						</widget>
						<widget source="Frontend" render="Label" position="585,670" size="100,22" font="Regular;18" halign="left" backgroundColor="#101214" transparent="1" zPosition="2">
							<convert type="FrontendInfo">SNRdB</convert>
						</widget>
						<eLabel text="AGC:" position="700,670" size="53,22" font="Regular;18" backgroundColor="#101214" halign="left" transparent="1" zPosition="2"/>
						<widget source="Frontend" render="Label" position="755,670" size="100,22" font="Regular;18" halign="left" backgroundColor="#101214" transparent="1" zPosition="2">
							<convert type="FrontendInfo">AGC</convert>
						</widget>
					</screen>""" % (x,y,w,h,pos1,pos2,pos3,pos4)
			else:
				pos1 = 550
				pos2 = 550
				pos3 = 0
				pos4 = 0
				if config.plugins.extvirtualzap.picons.value:
					pos1 = 510
					pos2 = 510
					pos3 = 640
					pos4 = 475
				skin = """
					<screen backgroundColor="transparent" flags="wfNoBorder" name="ExtendedVirtualZapNoPiP" position="0,0" size="720,576" title="Extended Virtual Zap">
						<widget backgroundColor="transparent" name="video" position="%d,%d" size="%d,%d" zPosition="1"/>
						<ePixmap alphatest="off" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/VirtualZap/sd.png" position="0,420" size="720,176" zPosition="0"/>
						<widget backgroundColor="#101214" foregroundColor="#f23d21" font="Regular;16" halign="left" name="errorPiP" position="20,405" size="250,18" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;20" halign="left" name="NowNum" position="5,445" size="45,28" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;22" halign="left" name="NowChannel" position="60,445" size="320,30" transparent="1" zPosition="2"/>
						<widget foregroundColor="#0058bcff" name="nowProgress" position="60,425" size="300,10" borderWidth="2" borderColor="#cccccc" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" name="nowPercent" position="380,421" size="50,20" font="Regular;18" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;18" halign="right" name="NowTuner" foregroundColor="#00999999" position="550,445" size="150,20" transparent="1" zPosition="1"/>
						<widget backgroundColor="#101214" font="Regular;18" foregroundColor="#fcc000" halign="left" name="NowEPG" position="50,475" size="450,20" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;18" halign="left" name="NextEPG" position="50,500" size="450,20" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;20" foregroundColor="#fcc000" halign="right" name="NowTime" position="%d,475" size="120,22" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;20" halign="right" name="NextTime" position="%d,500" size="120,22" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" name="servicePicon" position="%d,%d" size="70,53" alphatest="on" zPosition="2"/>
						<widget source="Frontend" render="Progress" position="180,540" size="150,20" pixmap="skin_default/bar_snr.png" zPosition="2" borderWidth="2" borderColor="#cccccc">
							<convert type="FrontendInfo">SNR</convert>
						</widget>
						<eLabel text="SNR:" position="50,540" size="53,22" font="Regular;18" backgroundColor="#101214" halign="left" transparent="1" zPosition="2"/>
						<widget source="Frontend" render="Label" position="105,540" size="70,22" font="Regular;18" halign="left" backgroundColor="#101214" transparent="1" zPosition="2">
							<convert type="FrontendInfo">SNR</convert>
						</widget>
						<widget source="Frontend" render="Label" position="335,540" size="100,22" font="Regular;18" halign="left" backgroundColor="#101214" transparent="1" zPosition="2">
							<convert type="FrontendInfo">SNRdB</convert>
						</widget>
						<eLabel text="AGC:" position="440,540" size="53,22" font="Regular;18" backgroundColor="#101214" halign="left" transparent="1" zPosition="2"/>
						<widget source="Frontend" render="Label" position="495,540" size="70,22" font="Regular;18" halign="left" backgroundColor="#101214" transparent="1" zPosition="2">
							<convert type="FrontendInfo">AGC</convert>
						</widget>
					</screen>""" % (x,y,w,h,pos1,pos2,pos3,pos4)
		else:
			if sz_w >= 1920:
				pos1 = 1270
				pos2 = 1270
				pos3 = 0
				pos4 = 0
				if config.plugins.extvirtualzap.picons.value:
					pos1 = 1150
					pos2 = 1150
					pos3 = 1650
					pos4 = 900
				skin = """
					<screen backgroundColor="transparent" flags="wfNoBorder" name="ExtendedVirtualZapNoPiP" position="0,0" size="1920,1080" title="Extended Virtual Zap">
						<widget backgroundColor="transparent" name="video" position="%d,%d" size="%d,%d" zPosition="1"/>
						<ePixmap alphatest="off" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/VirtualZap/fullhd.png" zPosition="0" position="0,820" size="1920,350"/>
						<widget backgroundColor="#101214" font="Regular;36" halign="left" name="NowNum" position="365,880" size="100,40" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;39" halign="left" name="NowChannel" position="435,880" size="787,42" transparent="1" zPosition="1"/>
						<widget foregroundColor="#0058bcff" name="nowProgress" position="365,860" size="900,15" borderWidth="2" borderColor="#cccccc" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" name="nowPercent" position="1300,856" size="70,27" font="Regular;25" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;36" foregroundColor="#fcc000" halign="left" name="NowEPG" position="405,925" size="800,38" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;36" halign="left" name="NextEPG" position="405,960" size="800,38" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;36" foregroundColor="#fcc000" halign="right" name="NowTime" position="%d,925" size="250,38" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;36" halign="right" name="NextTime" position="%d,960" size="250,38" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" name="servicePicon" position="%d,%d" size="200,120" alphatest="on" zPosition="2"/>
					</screen>""" % (x,y,w,h,pos1,pos2,pos3,pos4)

			elif sz_w >= 1280:
				pos1 = 1015
				pos2 = 1015
				pos3 = 0
				pos4 = 0
				if config.plugins.extvirtualzap.picons.value:
					pos1 = 950
					pos2 = 950
					pos3 = 1150
					pos4 = 610
				skin = """
					<screen backgroundColor="transparent" flags="wfNoBorder" name="ExtendedVirtualZapNoPiP" position="0,0" size="1280,720" title="Extended Virtual Zap">
						<widget backgroundColor="transparent" name="video" position="%d,%d" size="%d,%d" zPosition="1"/>
						<ePixmap alphatest="off" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/VirtualZap/hd.png" position="0,505" size="1280,220" zPosition="0"/>
						<widget backgroundColor="#101214" font="Regular;24" halign="left" name="NowNum" position="70,565" size="60,28" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;26" halign="left" name="NowChannel" position="140,565" size="1000,30" transparent="1" zPosition="2"/>
						<widget foregroundColor="#0058bcff" name="nowProgress" position="140,545" size="700,10" borderWidth="2" borderColor="#cccccc" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" name="nowPercent" position="875,541" size="50,20" font="Regular;18" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;24" foregroundColor="#fcc000" halign="left" name="NowEPG" position="140,610" size="760,28" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;24" halign="left" name="NextEPG" position="140,645" size="760,28" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;24" foregroundColor="#fcc000" halign="right" name="NowTime" position="%d,610" size="124,28" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;24" halign="right" name="NextTime" position="%d,645" size="124,28" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" name="servicePicon" position="%d,%d" size="100,60" alphatest="on" zPosition="2"/>
					</screen>""" % (x,y,w,h,pos1,pos2,pos3,pos4)
			else:
				pos1 = 550
				pos2 = 550
				pos3 = 0
				pos4 = 0
				if config.plugins.extvirtualzap.picons.value:
					pos1 = 510
					pos2 = 510
					pos3 = 640
					pos4 = 475
				skin = """
					<screen backgroundColor="transparent" flags="wfNoBorder" name="ExtendedVirtualZapNoPiP" position="0,0" size="720,576" title="Extended Virtual Zap">
						<widget backgroundColor="transparent" name="video" position="%d,%d" size="%d,%d" zPosition="1"/>
						<ePixmap alphatest="off" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/VirtualZap/sd.png" position="0,420" size="720,176" zPosition="0"/>
						<widget backgroundColor="#101214" font="Regular;20" halign="left" name="NowNum" position="5,445" size="45,28" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;22" halign="left" name="NowChannel" position="60,445" size="620,30" transparent="1" zPosition="2"/>
						<widget foregroundColor="#0058bcff" name="nowProgress" position="60,425" size="620,10" borderWidth="2" borderColor="#cccccc" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" name="nowPercent" position="715,421" size="50,20" font="Regular;18" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;18" foregroundColor="#fcc000" halign="left" name="NowEPG" position="50,475" size="450,20" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;18" halign="left" name="NextEPG" position="50,500" size="450,20" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;20" foregroundColor="#fcc000" halign="right" name="NowTime" position="%d,475" size="120,22" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" font="Regular;20" halign="right" name="NextTime" position="%d,500" size="120,22" transparent="1" zPosition="2"/>
						<widget backgroundColor="#101214" name="servicePicon" position="%d,%d" size="70,53" alphatest="on" zPosition="2"/>
					</screen>""" % (x,y,w,h,pos1,pos2,pos3,pos4)

	def __init__(self, session, servicelist = None, lastService = True):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.session = session
		if config.plugins.extvirtualzap.show_dish.value:
			self.dishpipDialog = self.session.instantiateDialog(DishPiP)
		else:
			self.dishpipDialog = None
		self.video_state = None
		self.currentService = None
		self.currentServiceReference = None
		self.PipServiceAvailable = False
		self.standartServiceAvailable = False
		self.lastService = lastService
		self.pipservice = None
		if self.pipDecoder and config.plugins.extvirtualzap.usepip.value and config.plugins.extvirtualzap.showpipininfobar.value:
			self.skinName = "ExtendedVirtualZap"
			self.pipAvailable = True
		else:
			self.skinName = "ExtendedVirtualZapNoPiP"
			self.pipAvailable = self.pipDecoder and config.plugins.extvirtualzap.usepip.value and not config.plugins.extvirtualzap.showpipininfobar.value
		self.epgcache = eEPGCache.getInstance()
		self.CheckForEPG = eTimer()
		self.CheckForEPG.callback.append(self.CheckItNow)
		self["NowChannel"] = Label()
		self["NowNum"] = Label()
		self["NowEPG"] = Label()
		self["NextEPG"] = Label()
		self["NowTime"] = Label()
		self["NextTime"] = Label()
		self["nowPercent"] = Label()
		self["servicePicon"] = Pixmap()
		self["nowProgress"] = ProgressBar()
		self["nowProgress"].hide()
		self["ExtendedVirtualZapActions"] = HelpableActionMap(self, "ExtendedVirtualZapActions", 
		{
			"ok": (self.ok, _("zap to PiP service and exit")), 
			"cancel": (self.closing,_("exit")),
			"right": (self.keyRightCheck,_("zap to next channel/open service list")),
			"left": (self.keyLeftCheck,_("zap to previous channel/open service list")),
			"nextBouquet": (self.showFavourites,_("open favorite list")),
			"prevBouquet": (self.openServiceList,_("open service list")),
			"showEventInfo": (self.openEventView,_("open Event View")),
			"showEventInfoSingleEPG": (self.openSingleServiceEPG,_("open single EPG")),
			"red": (self.standardPiPzap,_("standard PiPzap")),
			"green": (self.switchAndStandardPiPzap,_("swap and standard PiPzap")),
			"blue": (self.standardPiP,_("standard PiP")),
			"yellow": (self.switchAndStandardPiP,_("swap and standard PiP")),
			"down": (self.keyDownCheck,_("zap to previous channel/open service list")),
			"up": (self.keyUpCheck,_("zap to next channel/open service list")),
			"0": (self.swap,_("swap services")),
		},-2)
		self["actions2"] = NumberActionMap(["NumberActions"],
		{
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
		}, -1)
		if self.pipAvailable:
			if config.plugins.extvirtualzap.usepip.value and not config.plugins.extvirtualzap.showpipininfobar.value:
				self["video"] = VideoWindow()
			else:
				current_sz_w = self.sz_w
				current_sz_h = self.sz_h
				try:
					position_video_fix = False
					dst_left = config.plugins.OSDPositionSetup.dst_left.value
					dst_width = config.plugins.OSDPositionSetup.dst_width.value
					dst_top = config.plugins.OSDPositionSetup.dst_top.value
					dst_height = config.plugins.OSDPositionSetup.dst_height.value
					plugin_OSDPositionSetup_installed = True
					if dst_left != 0 or dst_width != 720 or dst_top != 0 or dst_height != 576:
						position_video_fix = True
				except:
					plugin_OSDPositionSetup_installed = False
					position_video_fix = False
				if plugin_OSDPositionSetup_installed and position_video_fix:
					if dst_left + dst_width > 720:
						dst_width = 720 - dst_left
					dst_width = 720 - dst_width
					if self.sz_w >= 1280:
						current_sz_w = self.sz_w - dst_width
						current_sz_h = self.sz_h + dst_left
				self["video"] = VideoWindow(fb_width = current_sz_w, fb_height = current_sz_h)
				self["video"].hide()
				self.video_state = False
			self["Frontend"] = FrontendStatus(service_source = lambda: self.pipservice, update_interval = 1000)
			self["NowTuner"] = Label()
			self["errorPiP"] = Label()
		else:
			self["video"] = Label()
		self.servicelist = servicelist
		if self.servicelist is None:
			return
		self.servicelist_orig_zap = self.servicelist.zap 
		self.servicelist.zap = self.servicelist_overwrite_zap
		self.servicelist["actions"] = ActionMap(["OkCancelActions"],
			{
				"cancel": self.cancelChannelSelection,
				"ok": self.servicelist.channelSelected,
			})
		self.curSelectedRef = None
		self.curSelectedBouquet = None
		if not self.lastService:
			self.selectedRef = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			self.selectedRoot = self.servicelist.startRoot
		else:
			self.selectedRef = None
			self.selectedRoot = None
		self.curRef = ServiceReference(self.servicelist.getCurrentSelection())
		self.curBouquet = self.servicelist.getRoot()
		if self.lastService and config.plugins.extvirtualzap.saveLastService.value:
			ref = eServiceReference(config.plugins.extvirtualzap.curref.value)
			bouquet = eServiceReference(config.plugins.extvirtualzap.curbouquet.value)
			if ref.valid() and bouquet.valid():
				self.setServicelistSelection(bouquet, ref)
		self.exitTimer = eTimer()
		self.exitTimer.timeout.get().append(self.standardPiP)
		self.onClose.append(self.__onClose)
		self.pipServiceRelation = {}
		if plugin_PiPServiceRelation_installed:
			if config.plugins.extvirtualzap.pipservicerelation.value:
				self.pipServiceRelation = getRelationDict()
			else:
				self.pipServiceRelation = {}
		else:
			if config.plugins.extvirtualzap.pipservicerelation.value:
				config.plugins.extvirtualzap.pipservicerelation.value = False
				config.plugins.extvirtualzap.pipservicerelation.save()
			self.pipServiceRelation = {}
		self.pauseTimer = eTimer()
		self.pauseTimer.timeout.get().append(self.firstUpdateInfos)
		self.pauseTimer.start(1000, True)

	def firstUpdateInfos(self):
		self.updateInfos()

	def resetExitTimer(self):
		if config.plugins.extvirtualzap.exittimer.value != 0:
			if self.exitTimer.isActive():
				self.exitTimer.stop()
			self.exitTimer.start(config.plugins.extvirtualzap.exittimer.value * 1000)

	def keyLeftCheck(self):
		if oldstyle_zap_controls:
			if oldstyle_zap_controls.value:
				self.switchChannelUp()
			else:
				self.prevService()
		else:
			self.prevService()

	def keyRightCheck(self):
		if oldstyle_zap_controls:
			if oldstyle_zap_controls.value:
				self.switchChannelDown()
			else:
				self.nextService()
		else:
			self.nextService()

	def keyUpCheck(self):
		if oldstyle_zap_controls:
			if oldstyle_zap_controls.value:
				self.nextService()
			else:
				self.switchChannelUp()
		else:
			self.switchChannelUp()

	def keyDownCheck(self):
		if oldstyle_zap_controls:
			if oldstyle_zap_controls.value:
				self.prevService()
			else:
				self.switchChannelDown()
		else:
			self.switchChannelDown()

	def nextService(self):
		if self.servicelist.inBouquet():
			prev = self.servicelist.getCurrentSelection()
			if prev:
				prev = prev.toString()
				while True:
					if config.usage.quickzap_bouquet_change.value and self.servicelist.atEnd():
						self.servicelist.nextBouquet()
					else:
						self.servicelist.moveDown()
					cur = self.servicelist.getCurrentSelection()
					if cur:
						if cur.toString() == prev or not (cur.flags & (64|8)):
							break
		else:
			self.servicelist.moveDown()
		if self.isPlayable():
			self.updateInfos()
		else:
			self.nextService()

	def prevService(self):
		if self.servicelist.inBouquet():
			prev = self.servicelist.getCurrentSelection()
			if prev:
				prev = prev.toString()
				while True:
					if config.usage.quickzap_bouquet_change.value:
						if self.servicelist.atBegin():
							self.servicelist.prevBouquet()
					self.servicelist.moveUp()
					cur = self.servicelist.getCurrentSelection()
					if cur:
						if cur.toString() == prev or not (cur.flags & (64|8)):
							break
		else:
			self.servicelist.moveUp()
		if self.isPlayable():
			self.updateInfos()
		else:
			self.prevService()

	def isPlayable(self):
		current = ServiceReference(self.servicelist.getCurrentSelection())
		return not (current.ref.flags & (eServiceReference.isMarker|eServiceReference.isDirectory))

	def getTunerName(self):
		number = -2
		tunerType = ''
		try:
			if self.pipservice is not None:
				feinfo = self.pipservice.frontendInfo()
				tuner = feinfo and feinfo.getFrontendData()
				if tuner is not None:
					number = tuner.get("tuner_number", number)
					type = tuner.get("tuner_type", '')
					if type: 
						tunerType = ' (%s)' % type
					name = chr(number+65) + tunerType
					return _("Tuner %s") % name
		except:
			pass
		return ''

	def nextBouquet(self):
		if config.usage.multibouquet.value:
			self.servicelist.nextBouquet()
		self.updateInfos()

	def prevBouquet(self):
		if config.usage.multibouquet.value:
			self.servicelist.prevBouquet()
		self.updateInfos()
		
	def getServiceNumber(self, ref):
		if isinstance(ref, eServiceReference):
				root = self.servicelist.getRoot()
				if root:
					lastpath = root.getPath()
					if not 'FROM BOUQUET "bouquets.' in lastpath: 
						if 'provider' in lastpath:
							return 'P'
						if 'satellitePosition ==' in lastpath:
							return 'S'
						if ') ORDER BY name' in lastpath:
							return 'A'
		return ''

	def updateInfos(self, checkParentalControl=True, ref=None):
		self.CheckForEPG.stop()
		self.resetExitTimer()
		current_service = self.servicelist.getCurrentSelection()
		if not current_service: return
		current = ServiceReference(current_service)
		current_ref = ref or current_service
		if not current_ref: return
		if config.plugins.extvirtualzap.picons.value:
			pngname = getPiconName(str(current))
			if pngname:
				self["servicePicon"].instance.setScale(1)
				self["servicePicon"].instance.setPixmapFromFile(pngname)
			else:
				self["servicePicon"].instance.setPixmap(None)
		self["NowChannel"].setText(current.getServiceName() or "")
		self["NowNum"].setText("")
		self["nowPercent"].setText("")
		self["nowProgress"].hide()
		num = current_service.getChannelNum() or None
		if num:
			self["NowNum"].setText(str(num))
		else:
			self["NowNum"].setText(self.getServiceNumber(current_service))
		self["NowChannel"].setText(current.getServiceName() or "")
		self.setTitle(current.getServiceName() or "")
		nowepg, nowtimedisplay, percentnow = self.getEPGNowNext(current.ref,0)
		nextepg, nexttimedisplay, percentnext = self.getEPGNowNext(current.ref,1)
		self["NowEPG"].setText(nowepg)
		self["NextEPG"].setText(nextepg)
		self["NowTime"].setText(nowtimedisplay)
		self["NextTime"].setText(nexttimedisplay)
		if not nowepg:
			if self.pipAvailable:
				self["NowEPG"].setText(_("wait 5 seconds"))
				self.CheckForEPG.start(5000, True)
		else:
			self["nowProgress"].setValue(percentnow)
			self["nowProgress"].show()
			self["nowPercent"].setText("%d %%" % (percentnow))
		if self.pipAvailable:
			self.pipservice = None
			self.currentService = None
			self.currentServiceReference = None
			self.setDishpipDialog()
			self.setPlayableService()
			if self.video_state is True:
				self["video"].hide()
				self.video_state = False
			self["NowTuner"].setText("")
			self["errorPiP"].setText("")
			self.PipServiceAvailable = False
			self.standartServiceAvailable = False
			nref = self.resolveAlternatePipService(current_ref)
			if nref and self.isPlayableForPipService(nref):
				playingref = self.session.nav.getCurrentlyPlayingServiceReference()
				if playingref and playingref == nref:
					checkParentalControl = False
				if not checkParentalControl or Components.ParentalControl.parentalControl.isServicePlayable(nref, boundFunction(self.updateInfos, checkParentalControl=False), session=self.session):
					self.PipServiceAvailable = True
					if not self.playService(nref):
						self["errorPiP"].setText(_("Incorrect type service for PiP!"))
				else:
					self["errorPiP"].setText(_("Parental control!"))
			else:
				self["errorPiP"].setText(_("No free tuner!"))

	def getEPGNowNext(self, ref, modus):
		if self.epgcache is not None:
			event = self.epgcache.lookupEvent(['IBDCTSERNX', (ref.toString(), modus, -1)])
			if event:
				if event[0][4]:
					t = localtime(event[0][1])
					duration = event[0][2]
					begin = event[0][1]
					now = int(time())
					if modus == 0:
						timedisplay = _("+%d min") % (((event[0][1] + duration) - time()) / 60)
						percent = int((now - begin) * 100 / duration)
					elif modus == 1:
						timedisplay = _("%d min") %  (duration / 60)
						percent = 0
					return "%02d:%02d %s" % (t[3],t[4], event[0][4]), timedisplay, percent
				else:
					return "", "", ""
		return "", "", ""

	def SingleServiceEPGCallBack(self, answer=None):
		self.resetExitTimer()

	def openSingleServiceEPG(self):
		service = self.servicelist.getCurrentSelection()
		info = service and eServiceCenter.getInstance().info(service)
		epg_event = info and info.getEvent(service)
		if not epg_event:
			return
		if self.exitTimer.isActive():
			self.exitTimer.stop()
		current = ServiceReference(self.servicelist.getCurrentSelection())
		self.session.openWithCallback(self.SingleServiceEPGCallBack, EPGSelection, current.ref)

	def openSingleServiceEPGforEventView(self):
		current = ServiceReference(self.servicelist.getCurrentSelection())
		self.session.open(EPGSelection, current.ref)

	def openEventView(self):
		epglist = [ ]
		self.epglist = epglist
		service = ServiceReference(self.servicelist.getCurrentSelection())
		ref = service.ref
		evt = self.epgcache.lookupEventTime(ref, -1)
		if evt:
			epglist.append(evt)
		evt = self.epgcache.lookupEventTime(ref, -1, 1)
		if evt:
			epglist.append(evt)
		if epglist:
			if self.exitTimer.isActive():
				self.exitTimer.stop()
			self.session.openWithCallback(self.EventViewEPGSelectCallBack, EventViewEPGSelect, epglist[0], service, self.eventViewCallback, self.openSingleServiceEPGforEventView, self.openMultiServiceEPG, self.openSimilarList)

	def EventViewEPGSelectCallBack(self):
		self.resetExitTimer()

	def eventViewCallback(self, setEvent, setService, val):
		epglist = self.epglist
		if len(epglist) > 1:
			tmp = epglist[0]
			epglist[0] = epglist[1]
			epglist[1] = tmp
			setEvent(epglist[0])

	def openMultiServiceEPG(self):
		pass

	def openSimilarList(self, eventid, refstr):
		self.session.open(EPGSelection, refstr, None, eventid)

	def setServicelistSelection(self, bouquet, service):
		if bouquet and service:
			if self.servicelist.getRoot() != bouquet:
				self.servicelist.clearPath()
				self.servicelist.enterPath(self.servicelist.bouquet_root)
				self.servicelist.enterPath(bouquet)
			self.servicelist.setCurrentSelection(service)

	def closing(self):
		if self.pipAvailable:
			self.pipservice = None
			self.setPlayableService()
			self.setDishpipDialog(stoping=True)
		self.saveLastService(self.servicelist.getCurrentSelection().toString(), self.servicelist.getRoot().toString())
		self.setServicelistSelection(self.curBouquet, self.curRef.ref)
		self.close()

	def ok(self):
		if self.pipAvailable:
			self.pipservice = None
			self.setDishpipDialog(stoping=True)
			self.setPlayableService()
		self.servicelist_orig_zap()
		self.saveLastService(self.curRef.ref.toString(), self.curBouquet.toString())
		self.close()

	def standardPiPzap(self):
		if self.pipAvailable and self.PipServiceAvailable:
			self.pipservice = None
			self.setDishpipDialog(stoping=True)
			self.setPlayableService()
			service = ServiceReference(self.servicelist.getCurrentSelection()).ref
			self.saveLastService(self.servicelist.getCurrentSelection().toString(), self.servicelist.getRoot().toString())
			self.setServicelistSelection(self.servicelist.getRoot(), self.servicelist.getCurrentSelection())
			servicePath = self.servicelist.getCurrentServicePath()
			self.close(service, servicePath, True)

	def standardPiP(self):
		if self.pipAvailable and self.PipServiceAvailable:
			self.pipservice = None
			self.setDishpipDialog(stoping=True)
			self.setPlayableService()
			if self.servicelist.getCurrentSelection() is None: return
			service = ServiceReference(self.servicelist.getCurrentSelection()).ref
			servicePath = self.servicelist.getCurrentServicePath()
			self.saveLastService(self.servicelist.getCurrentSelection().toString(), self.servicelist.getRoot().toString())
			self.setServicelistSelection(self.curBouquet, self.curRef.ref)
			self.close(service, servicePath)

	def switchAndStandardPiPzap(self):
		if self.pipAvailable and (self.PipServiceAvailable or self.standartServiceAvailable):
			self.pipservice = None
			self.setDishpipDialog(stoping=True)
			self.setPlayableService()
			servicePath = self.servicelist.getCurrentServicePath()
			self.saveLastService(self.curRef.ref.toString(), self.curBouquet.toString())
			pip_service = self.curRef.ref
			currentBouquet = self.curBouquet
			if not self.lastService:
				if self.selectedRef and self.curRef.ref and self.selectedRef != self.curRef.ref:
					pip_service = self.selectedRef
					currentBouquet = self.selectedRoot
			self.servicelist_orig_zap()
			self.setServicelistSelection(currentBouquet, pip_service)
			self.close(pip_service, servicePath, True)

	def switchAndStandardPiP(self):
		if self.pipAvailable and (self.PipServiceAvailable or self.standartServiceAvailable):
			self.pipservice = None
			self.setDishpipDialog(stoping=True)
			self.setPlayableService()
			servicePath = self.servicelist.getCurrentServicePath()
			self.saveLastService(self.curRef.ref.toString(), self.curBouquet.toString())
			service_pip = self.curRef.ref
			self.servicelist_orig_zap()
			if not self.lastService:
				if self.selectedRef and self.curRef.ref and self.selectedRef != self.curRef.ref:
					service_pip = self.selectedRef
			self.close(service_pip, servicePath)

	def saveLastService(self, ref, bouquet):
		if config.plugins.extvirtualzap.saveLastService.value:
			config.plugins.extvirtualzap.curref.value = ref
			config.plugins.extvirtualzap.curbouquet.value = bouquet
			if config.plugins.extvirtualzap.saveLastServiceMode.value == "always":
				config.plugins.extvirtualzap.curref.save()
				config.plugins.extvirtualzap.curbouquet.save()
			elif currentRememberLastService is not None:
				currentRememberLastService.startClearLastService()
		if self.exitTimer.isActive():
			self.exitTimer.stop()

	def repeatUpdateInfos(self):
		self.CheckForEPG.stop()
		if self.servicelist.getCurrentSelection() is None: return
		current = ServiceReference(self.servicelist.getCurrentSelection())
		self["NowChannel"].setText(current.getServiceName() or '')
		nowepg, nowtimedisplay, percentnow = self.getEPGNowNext(current.ref,0)
		nextepg, nexttimedisplay, percentnext = self.getEPGNowNext(current.ref,1)
		self["NowEPG"].setText(nowepg)
		self["NextEPG"].setText(nextepg)
		self["NowTime"].setText(nowtimedisplay)
		self["NextTime"].setText(nexttimedisplay)
		if percentnow:
			self["nowProgress"].setValue(percentnow)
			self["nowProgress"].show()
			self["nowPercent"].setText("%d %%" % (percentnow))

	def CheckItNow(self):
		self.repeatUpdateInfos()
	
	def setPlayableService(self):
		self.servicelist.servicelist.setPlayableIgnoreService(self.session.nav.getCurrentlyPlayingServiceReference() or eServiceReference())

	def setDishpipDialog(self, stoping=False):
		startDialog = False
		if hasattr(self, "dishpipDialog"):
			if self.dishpipDialog:
				self.dishpipDialog.stopDishpip()
				if not stoping:
					startDialog = True
			del self.dishpipDialog
			self.dishpipDialog = None
			if config.plugins.extvirtualzap.show_dish.value and startDialog:
				self.dishpipDialog = self.session.instantiateDialog(DishPiP)


	def isPlayableForPipService(self, service):
		playingref = self.session.nav.getCurrentlyPlayingServiceReference()
		if playingref is None or service == playingref:
			return True
		info = eServiceCenter.getInstance().info(service)
		oldref = self.currentServiceReference or eServiceReference()
		if info and info.isPlayable(service, oldref):
			return True
		return False

	def resolveAlternatePipService(self, service,useRelation=True):
		if useRelation and service:
			n_service = self.pipServiceRelation.get(service.toString(),None)
			if n_service is not None:
				service = eServiceReference(n_service)
		if service and (service.flags & eServiceReference.isGroup):
			oldref = self.currentServiceReference or eServiceReference()
			return getBestPlayableServiceReference(service, oldref)
		return service

	def playService(self, ref, imitation=False):
		if ref:
			if self.currentServiceReference is None or ref != self.currentServiceReference:
				self.pipservice = eServiceCenter.getInstance().play(ref)
				if self.pipservice and not self.pipservice.setTarget(1, True):
					self.pipservice.start()
					if self.video_state is False: 
						self["video"].show()
						self.video_state = True
					if not imitation:
						if hasattr(self, "dishpipDialog") and self.dishpipDialog is not None:
							self.dishpipDialog.serviceStarted(ref=ref, pipservice=self.pipservice)
						if "%3a//" in ref.toString():
							tunername = _('Stream')
						else:
							tunername = self.getTunerName()
						self["NowTuner"].setText(tunername)
					self.currentService = self.servicelist.getCurrentSelection()
					self.currentServiceReference = ref
					self.servicelist.servicelist.setPlayableIgnoreService(ref)
					return True
				else:
					self.pipservice = None
					self.currentService = None
					self.currentServiceReference = None
					self.setDishpipDialog()
					self.setPlayableService()
					self.PipServiceAvailable = False
					self.standartServiceAvailable = True
		else:
			self.pipservice = None
			self.currentService = None
			self.currentServiceReference = None
			self.setDishpipDialog()
			self.setPlayableService()
			self.PipServiceAvailable = False
			self.standartServiceAvailable = False
		return False

	def keyNumberGlobal(self, number):
		self.prepareChannelSelectionDisplay(stopPip=True)
		self.session.openWithCallback(self.numberEntered, NumberZap, number, self.searchNumber)

	def numberEntered(self, service=None, bouquet=None):
		if service and bouquet:
			if self.servicelist.getRoot() != bouquet:
				self.servicelist.clearPath()
				if self.servicelist.bouquet_root and self.servicelist.bouquet_root != bouquet:
					self.servicelist.enterPath(self.servicelist.bouquet_root)
				self.servicelist.enterPath(bouquet)
			self.servicelist.setCurrentSelection(service)
		self.updateInfos()

	def searchNumberHelper(self, serviceHandler, num, bouquet):
		servicelist = serviceHandler.list(bouquet)
		if servicelist:
			serviceIterator = servicelist.getNext()
			while serviceIterator.valid():
				if num == serviceIterator.getChannelNum():
					return serviceIterator
				serviceIterator = servicelist.getNext()
		return None

	def searchNumber(self, number, firstBouquetOnly=False):
		bouquet = self.servicelist.getRoot()
		service = None
		serviceHandler = eServiceCenter.getInstance()
		if not firstBouquetOnly:
			service = self.searchNumberHelper(serviceHandler, number, bouquet)
		if config.usage.multibouquet.value and not service:
			bouquet = self.servicelist.bouquet_root
			bouquetlist = serviceHandler.list(bouquet)
			if bouquetlist:
				bouquet = bouquetlist.getNext()
				while bouquet.valid():
					if bouquet.flags & eServiceReference.isDirectory:
						service = self.searchNumberHelper(serviceHandler, number, bouquet)
						if service:
							playable = not (service.flags & (eServiceReference.isMarker|eServiceReference.isDirectory)) or (service.flags & eServiceReference.isNumberedMarker)
							if not playable:
								service = None
							break
						if config.usage.alternative_number_mode.value or firstBouquetOnly:
							break
					bouquet = bouquetlist.getNext()
		return service, bouquet

	def swap(self):
		currentRef = self.curRef.ref
		currentBouquet = self.curBouquet
		if self.pipAvailable and (self.PipServiceAvailable or self.standartServiceAvailable):
			if self.currentServiceReference and self.session.nav.getCurrentlyPlayingServiceReference() and self.session.nav.getCurrentlyPlayingServiceReference() == self.currentServiceReference:
				return
			self.pipservice = None
			self.currentService = None
			self.currentServiceReference = None
			self.standartServiceAvailable = False
			self.setDishpipDialog()
			self.setPlayableService()
		cur = self.servicelist.getCurrentSelection()
		isPlayable = cur and isPlayableForCur(cur)
		if not isPlayable:
			self.updateInfos()
			return
		if not self.lastService:
			if self.selectedRef and currentRef and self.selectedRef != currentRef:
				currentRef = self.selectedRef
				currentBouquet = self.selectedRoot
		self.servicelist_orig_zap()
		self.curRef = ServiceReference(self.servicelist.getCurrentSelection())
		self.curBouquet = self.servicelist.getRoot()
		self.setServicelistSelection(currentBouquet, currentRef)
		self.updateInfos()

	def prepareChannelSelectionDisplay(self, stopPip=False):
		if self.exitTimer.isActive():
			self.exitTimer.stop()
		if self.pipAvailable:
			if stopPip:
				self.pipservice = None
			self.setDishpipDialog()
			self.setPlayableService()
			if not stopPip:
				self.playService(self.session.nav.getCurrentlyPlayingServiceReference(), imitation=True)
			self.currentService = None
			self.currentServiceReference = None
			self.standartServiceAvailable = False
		self.curSelectedRef = eServiceReference(self.servicelist.getCurrentSelection().toString())
		self.curSelectedBouquet = self.servicelist.getRoot()

	def cancelChannelSelection(self):
		if self.servicelist.revertMode is None:
			ref = self.curSelectedRef
			bouquet = self.curSelectedBouquet
			if ref.valid() and bouquet.valid():
				self.setServicelistSelection(bouquet, ref)
		self.servicelist.revertMode = None
		self.servicelist.close(None)
		self.curSelectedRef = None
		self.curSelectedBouquet = None
		self.servicelist_overwrite_zap()

	def switchChannelDown(self):
		if not self.lastService:
			return
		self.prepareChannelSelectionDisplay()
		if cursor_behavior:
			if "keep" not in cursor_behavior.value:
				self.servicelist.moveUp()
		else:
			self.servicelist.moveUp()
		self.session.execDialog(self.servicelist)

	def switchChannelUp(self):
		if not self.lastService:
			return
		self.prepareChannelSelectionDisplay()
		if cursor_behavior:
			if "keep" not in cursor_behavior.value:
				self.servicelist.moveUp()
		else:
			self.servicelist.moveUp()
		self.session.execDialog(self.servicelist)

	def showFavourites(self):
		if not self.lastService:
			return
		self.prepareChannelSelectionDisplay()
		self.servicelist.showFavourites()
		self.session.execDialog(self.servicelist)

	def openServiceList(self):
		if not self.lastService:
			return
		self.prepareChannelSelectionDisplay()
		self.session.execDialog(self.servicelist)

	def servicelist_overwrite_zap(self, *args, **kwargs):
		if self.isPlayable():
			self.updateInfos()

	def __onClose(self): 
		self.servicelist.zap = self.servicelist_orig_zap
		self.servicelist["actions"] = ActionMap(["OkCancelActions", "TvRadioActions"],
			{
				"cancel": self.servicelist.cancel,
				"ok": self.servicelist.channelSelected,
				"keyRadio": self.servicelist.setModeRadio,
				"keyTV": self.servicelist.setModeTv,
			})

class ExtendedVirtualZapConfig(Screen, ConfigListScreen):
	sz_w = getDesktop(0).size().width()
	if sz_w >= 1920:
		skin = """
			<screen position="center,center" size="1000,600" title="Extended virtual zap config" >
				<ePixmap pixmap="skin_default/buttons/red.png" position="170,0" zPosition="0" size="240,80" transparent="1" alphatest="on" />
				<ePixmap pixmap="skin_default/buttons/green.png" position="670,0" zPosition="0" size="240,80" transparent="1" alphatest="on" />
				<widget render="Label" source="key_red" position="200,0" size="200,50" zPosition="5" valign="center" backgroundColor="red" font="Regular;34" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
				<widget render="Label" source="key_green" position="700,0" size="200,50" zPosition="5" valign="center" backgroundColor="red" font="Regular;34" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
				<widget name="config" position="10,90" size="980,500" itemHeight="36" font="Regular;34" scrollbarMode="showOnDemand" />
			</screen>"""
	else:
		skin = """
			<screen position="center,center" size="690,380" title="Extended virtual zap config" >
				<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
				<ePixmap pixmap="skin_default/buttons/green.png" position="185,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
				<widget render="Label" source="key_red" position="0,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
				<widget render="Label" source="key_green" position="185,0" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
				<widget name="config" position="20,50" size="650,320" scrollbarMode="showOnDemand" />
			</screen>"""
	def __init__(self, session):
		Screen.__init__(self, session)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self.setTitle(_("Extended virtual zap config"))
		ConfigListScreen.__init__(self, [])
		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"green": self.keySave,
			"red": self.keyClose,
			"cancel": self.keyClose,
			"ok": self.keySave,
		}, -2)
		self.prev_extvirtualzap_mode = config.plugins.extvirtualzap.mode.value
		self.prev_showpipininfobar = config.plugins.extvirtualzap.showpipininfobar.value
		self.prev_channelselection_contextmenu = config.plugins.extvirtualzap.channelselection_contextmenu.value
		self.createSetup()

	def createSetup(self):
		list = []
		list.append(getConfigListEntry(_("Usage"), config.plugins.extvirtualzap.mode))
		if config.plugins.extvirtualzap.mode.value == "4":
			list.append(getConfigListEntry(_("Show plugin in the context menu"), config.plugins.extvirtualzap.event_menu))
		if config.plugins.extvirtualzap.mode.value != "3":
			list.append(getConfigListEntry(_("Show plugin in channel selection context menu"), config.plugins.extvirtualzap.channelselection_contextmenu))
			if SystemInfo.get("NumVideoDecoders", 1) > 1:
				list.append(getConfigListEntry(_("Use PiP"), config.plugins.extvirtualzap.usepip))
				if config.plugins.extvirtualzap.usepip.value:
					list.append(getConfigListEntry(_("Show PiP in window infobar"), config.plugins.extvirtualzap.showpipininfobar))
					list.append(getConfigListEntry(_("Start standard PiP after x secs (0 = disabled)"), config.plugins.extvirtualzap.exittimer))
					if plugin_PiPServiceRelation_installed:
						list.append(getConfigListEntry(_("Use plugin 'PiPServiceRelation'"), config.plugins.extvirtualzap.pipservicerelation))
					list.append(getConfigListEntry(_("Show positioner movement for PiP service"), config.plugins.extvirtualzap.show_dish))
			if exit_button is not None and exit_button.value and config.plugins.extvirtualzap.mode.value != "2":
				list.append(getConfigListEntry(_("Don't toggle standard infobar(s) with exit button"), config.plugins.extvirtualzap.exit_button))
			list.append(getConfigListEntry(_("Show picons"), config.plugins.extvirtualzap.picons))
			list.append(getConfigListEntry(_("Remember last service"), config.plugins.extvirtualzap.saveLastService))
			if config.plugins.extvirtualzap.saveLastService.value:
				list.append(getConfigListEntry(_("Remember mode"), config.plugins.extvirtualzap.saveLastServiceMode))
		self["config"].list = list
		self["config"].l.setList(list)

	def keySave(self):
		if config.plugins.extvirtualzap.mode.value == "2" or config.plugins.extvirtualzap.mode.value == "3" or (exit_button is not None and not exit_button.value):
			config.plugins.extvirtualzap.exit_button.value = False
		if not config.plugins.extvirtualzap.usepip.value:
			config.plugins.extvirtualzap.showpipininfobar.value = False
			config.plugins.extvirtualzap.show_dish.value = False
		for x in self["config"].list:
			x[1].save()
		configfile.save()
		if self.prev_channelselection_contextmenu != config.plugins.extvirtualzap.channelselection_contextmenu.value:
			self.refreshPlugins()
		if self.prev_extvirtualzap_mode != config.plugins.extvirtualzap.mode.value:
			restartbox = self.session.openWithCallback(self.restartGUI,MessageBox,_("GUI needs a restart to apply the new settings.\nDo you want to Restart the GUI now?"), MessageBox.TYPE_YESNO)
			restartbox.setTitle(_("Restart GUI"))
		else:
			import plugin
			reload(plugin)
			self.close()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	def keyClose(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def restartGUI(self, answer):
		if answer is True:
			self.session.open(TryQuitMainloop, 3)
		else:
			self.close()

	def refreshPlugins(self):
		from Components.PluginComponent import plugins
		from Tools.Directories import SCOPE_PLUGINS, resolveFilename
		plugins.clearPluginList()
		plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))

def ExtendedVirtualZapChannelContextMenuInit():
	from Screens.ChannelSelection import ChannelContextMenu, OFF, MODE_TV, service_types_tv
	global baseEVZChannelContextMenuINIT
	if baseEVZChannelContextMenuINIT is None:
		baseEVZChannelContextMenuINIT = ChannelContextMenu.__init__
	ChannelContextMenu.__init__ = ExtendedVirtualZapChannelContextMenu__init__
	ChannelContextMenu.showEVZ = showEVZ

def ExtendedVirtualZapChannelContextMenu__init__(self, session, csel):
	baseEVZChannelContextMenuINIT(self, session, csel)
	if csel is None: return
	if csel.mode == MODE_TV:
		current = csel.getCurrentSelection()
		current_root = csel.getRoot()
		current_sel_path = current.getPath()
		current_sel_flags = current.flags
		inBouquetRootList = current_root and current_root.getPath().find('FROM BOUQUET "bouquets.') != -1
		inBouquet = csel.getMutableList() is not None
		isPlayable = not (current_sel_flags & (eServiceReference.isMarker|eServiceReference.isDirectory))
		if csel.bouquet_mark_edit == OFF and not csel.movemode and current and current.valid():
			if isPlayable:
				if config.plugins.extvirtualzap.channelselection_contextmenu.value:
					callFunction = self.showEVZ
					self["menu"].list.insert(2, ChoiceEntryComponent(text = (_("show 'Extended virtual zap' for current service"), boundFunction(callFunction,1))))

def showEVZ(self, add):
	try:
		ref = self.csel.servicelist.getCurrent()
		if not ref:
			return
		startForChannelSelector(self.session)
		self.close(False)
	except:
		pass

def autostart(reason, **kwargs):
	if reason == 0 and config.plugins.extvirtualzap.mode.value != "3":
		global InfoBarShowHideINIT
		if InfoBarShowHideINIT is None:
			InfoBarShowHideINIT = InfoBarShowHide.__init__
		InfoBarShowHide.__init__ = InfoBarShowHide__init__
		InfoBarShowHide.showVZ = showVZ
		InfoBarShowHide.ExtendedVirtualZapCallback = ExtendedVirtualZapCallback
		InfoBarShowHide.newHide = newHide
		# for old image
		#try:
		#	ExtendedVirtualZapChannelContextMenuInit()
		#except:
		#	pass

def InfoBarShowHide__init__(self):
	InfoBarShowHideINIT(self)
	if config.plugins.extvirtualzap.mode.value == "1":
		try:
			del self["ShowHideActions"]
		except:
			pass
		self["myactions"] = ActionMap( ["myShowHideActions"] ,
		{
			"toggleShow": self.okButtonCheck,
			"longOK": self.showVZ,
			"hide": self.newHide,
			"hideLong": self.hideLong,
		}, prio = 1)
	elif config.plugins.extvirtualzap.mode.value != "3":
		self["ShowHideActions"] = ActionMap( ["InfobarShowHideActions"] ,
		{
			"toggleShow": self.okButtonCheck,
			"hide": self.newHide,
			"toggleShowLong": self.toggleShowLong,
			"hideLong": self.hideLong,
		}, prio = 1)

def showVZ(self, exit=False):
	from Screens.InfoBarGenerics import InfoBarEPG
	if isinstance(self, InfoBarEPG):
		if isinstance(self, InfoBarPiP):
			if self.pipShown():
				self.showPiP()
		if isinstance(self, InfoBar):
			self.session.openWithCallback(self.ExtendedVirtualZapCallback, ExtendedVirtualZap, self.servicelist)
	if not exit and exit_button is not None and show_simple_second_infobar is not None and not exit_button.value:
		try:
			if self.actualSecondInfoBarScreen and not self.shown and not self.actualSecondInfoBarScreen.shown and self.secondInfoBarScreenSimple.skinAttributes and self.secondInfoBarScreen.skinAttributes:
				self.actualSecondInfoBarScreen.hide()
				config.usage.show_simple_second_infobar.value = not config.usage.show_simple_second_infobar.value
				config.usage.show_simple_second_infobar.save()
				self.actualSecondInfoBarScreen = config.usage.show_simple_second_infobar.value and self.secondInfoBarScreenSimple or self.secondInfoBarScreen
				#self.showSecondInfoBar()
		except:
			pass

def ExtendedVirtualZapCallback(self, service=None, servicePath=None, pipZap=False):
	if isinstance(self, InfoBarPiP):
		if service and servicePath:
			self.session.pip = self.session.instantiateDialog(PictureInPicture)
			self.session.pip.show()
			if self.session.pip.playService(service):
				self.session.pipshown = True
				self.session.pip.servicePath = servicePath
				if pipZap:
					from Screens.InfoBar import InfoBar
					InfoBarinstance = InfoBar.instance and InfoBar.instance.servicelist and hasattr(InfoBar.instance.servicelist, "togglePipzap") and not InfoBar.instance.servicelist.dopipzap
					if InfoBarinstance:
						InfoBar.instance.servicelist.togglePipzap()
						if InfoBar.instance.servicelist.dopipzap:
							InfoBar.instance.servicelist.setCurrentServicePath(self.session.pip.servicePath, doZap=False)
			else:
				self.session.pipshown = False
				del self.session.pip
				self.session.openWithCallback(self.close, MessageBox, _("Could not open Picture in Picture"), MessageBox.TYPE_ERROR)

def newHide(self):
	mode = config.plugins.extvirtualzap.mode.value
	if mode == "1" or mode == "0" or mode == "4":
		if config.plugins.extvirtualzap.exit_button.value and (exit_button is not None and exit_button.value):
			prev_config = exit_button.value
			exit_button.value = False
			InfoBarShowHide.keyHide(self)
			exit_button.value = prev_config
			return
		InfoBarShowHide.keyHide(self)
	elif mode == "2":
		visible = self.shown
		self.hide()
		if not visible:
			self.showVZ(exit=True)

def setup(session, **kwargs):
	session.open(ExtendedVirtualZapConfig)

def ExtendedVirtualZapMainCallback(service=None, servicePath=None, pipZap=False):
		ExtendedVirtualZapCallback(InfoBar.instance, service, servicePath, pipZap)

def singleepg(session, selectedevent, **kwargs):
	mode = config.plugins.extvirtualzap.event_menu.value
	if mode in ("1", "3"):
		from Screens.InfoBar import InfoBar
		if InfoBar.instance:
			if hasattr(InfoBar.instance, "pipShown") and InfoBar.instance.pipShown():
				if hasattr(InfoBar.instance, "showPiP"):
					InfoBar.instance.showPiP()
			session.openWithCallback(ExtendedVirtualZapMainCallback, ExtendedVirtualZap, InfoBar.instance.servicelist)

def eventinfofull(session, eventName="", **kwargs):
	mode = config.plugins.extvirtualzap.event_menu.value
	open_plugin = False
	if eventName != "" and (mode =="2" or mode == "3"):
		open_plugin = True
	elif eventName == "":
		open_plugin = True
	if not open_plugin: return
	from Screens.InfoBar import InfoBar
	if InfoBar.instance:
		if hasattr(InfoBar.instance, "pipShown") and InfoBar.instance.pipShown():
			if hasattr(InfoBar.instance, "showPiP"):
				InfoBar.instance.showPiP()
		session.openWithCallback(ExtendedVirtualZapMainCallback, ExtendedVirtualZap, InfoBar.instance.servicelist)

def eventinfo(session, servicelist, eventName="", **kwargs):
	mode = config.plugins.extvirtualzap.event_menu.value
	open_plugin = False
	if eventName != "" and (mode =="2" or mode == "3"):
		open_plugin = False
	elif eventName == "":
		open_plugin = True
	if not open_plugin: return
	from Screens.InfoBar import InfoBar
	if InfoBar.instance:
		if hasattr(InfoBar.instance, "pipShown") and InfoBar.instance.pipShown():
			if hasattr(InfoBar.instance, "showPiP"):
				InfoBar.instance.showPiP()
		session.openWithCallback(ExtendedVirtualZapMainCallback, ExtendedVirtualZap, InfoBar.instance.servicelist)

def startForChannelSelector(session=None, service=None):
	if session is None: return
	if service is None: return
	from Screens.InfoBar import InfoBar
	if InfoBar.instance:
		if hasattr(InfoBar.instance, "pipShown") and InfoBar.instance.pipShown():
			if hasattr(InfoBar.instance, "showPiP"):
				InfoBar.instance.showPiP()
		session.openWithCallback(ExtendedVirtualZapMainCallback, ExtendedVirtualZap, InfoBar.instance.servicelist, lastService = False)

def main(session, **kwargs):
	from Screens.InfoBar import InfoBar
	if InfoBar.instance:
		if hasattr(InfoBar.instance, "pipShown") and InfoBar.instance.pipShown():
			if hasattr(InfoBar.instance, "showPiP"):
				InfoBar.instance.showPiP()
		session.openWithCallback(ExtendedVirtualZapMainCallback, ExtendedVirtualZap, InfoBar.instance.servicelist)

def Plugins(**kwargs):
 	plist = [PluginDescriptor(name= _("Extended virtual zap setup"), description=_("config menu"), where = [PluginDescriptor.WHERE_PLUGINMENU], icon = "plugin.png", fnc = setup)]
	mode = config.plugins.extvirtualzap.mode.value
	if mode == "0" or mode == "4":
		plugin_name = _("Extended virtual zap")
		if SystemInfo.get("NumVideoDecoders", 1) > 1:
			plugin_name = _("Extended virtual zap (PiP)")
		if mode == "0":
			plist.append(PluginDescriptor(name=plugin_name, where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc = main))
		elif mode == "4":
			menu = config.plugins.extvirtualzap.event_menu.value
			if menu == "1" or menu == "3":
				plist.append(PluginDescriptor(name=plugin_name, where = PluginDescriptor.WHERE_EVENTINFO, fnc = singleepg))
			if menu == "2" or menu == "3":
				plist.append(PluginDescriptor(name=plugin_name, where = PluginDescriptor.WHERE_EVENTINFO, fnc = eventinfofull))
			else:
				plist.append(PluginDescriptor(name=plugin_name, where = PluginDescriptor.WHERE_EVENTINFO, fnc = eventinfo))

	plist.append(PluginDescriptor(where = PluginDescriptor.WHERE_SESSIONSTART,fnc = autostart))
	if config.plugins.extvirtualzap.channelselection_contextmenu.value:
		plist.append(PluginDescriptor(name=_("show 'Extended virtual zap' for current service"), where = PluginDescriptor.WHERE_CHANNEL_CONTEXT_MENU, fnc = startForChannelSelector))
	return plist