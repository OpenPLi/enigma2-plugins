from __future__ import print_function

# for localized messages
from . import _
# GUI (Screens)
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.ConfigList import ConfigListScreen
from Components.Harddisk import harddiskmanager
from Components.MenuList import MenuList
# GUI (Summary)
from Screens.Setup import SetupSummary

# GUI (Components)
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, fileExists
# Configuration
from Components.config import config, configfile, getConfigListEntry, NoSave, ConfigSelection
import os
from enigma import eTimer, getDesktop
import time

HD = False
if getDesktop(0).size().width() >= 1280:
	HD = True
class EPGSaveLoadConfiguration(Screen, ConfigListScreen):
	if HD:
		skin = """<screen name="EPGSaveLoadConfiguration" position="center,center" size="600,640">
			<ePixmap position="0,5" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
			<ePixmap position="140,5" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
			<widget source="key_red" render="Label" position="0,5" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget source="key_green" render="Label" position="140,5" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget source="epgcachelocation" render="Label" position="5,495" size="590,50" zPosition="1" font="Regular;21" halign="left" valign="center" />
			<widget name="config" position="5,50" size="590,435" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,490" zPosition="1" size="600,2" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,550" zPosition="1" size="600,2" />
			<widget source="help" render="Label" position="5,555" size="590,83" font="Regular;21" />
		</screen>"""
	else:
		skin = """<screen name="EPGSaveLoadConfiguration" position="center,center" size="600,520">
			<ePixmap position="0,5" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
			<ePixmap position="140,5" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
			<widget source="key_red" render="Label" position="0,5" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget source="key_green" render="Label" position="140,5" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget source="epgcachelocation" render="Label" position="5,375" size="590,50" zPosition="1" font="Regular;21" halign="left" valign="center" />
			<widget name="config" position="5,50" size="590,315" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,370" zPosition="1" size="600,2" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,430" zPosition="1" size="600,2" />
			<widget source="help" render="Label" position="5,435" size="590,83" font="Regular;21" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setup_title = _("Configuration save / load EPG")
		self.onChangedEntry = []
		self.prev_lastepgcachepath = config.misc.epgcache_filename.value
		self.current_epgpath = config.plugins.epgrefresh_extra.epgcachepath.value
		hddchoises = []
		if self.current_epgpath != '/etc/enigma2/':
			hddchoises = [('/etc/enigma2/', '/etc/enigma2/')]
		for p in harddiskmanager.getMountedPartitions():
			if os.path.exists(p.mountpoint) and  os.access(p.mountpoint, os.F_OK|os.R_OK):
				if p.mountpoint != '/':
					d = os.path.normpath(p.mountpoint)
					hddchoises.append((d + '/', p.mountpoint + '/'))
		if self.current_epgpath and self.current_epgpath != '/' and (self.current_epgpath, self.current_epgpath) in hddchoises:
			#hddchoises.append((self.current_epgpath, self.current_epgpath))
			default_epg = self.current_epgpath
		else:
			default_epg = None
		config.plugins.epgrefresh_extra.add_epgcachepath = NoSave(ConfigSelection(default = default_epg, choices = hddchoises))
		self.list = [
			getConfigListEntry(_("Manual save EPG"), config.plugins.epgrefresh_extra.manual_save, _("Manual saving EPG in current cachefile.")),
			getConfigListEntry(_("Manual load EPG"), config.plugins.epgrefresh_extra.manual_load, _("Manual loading EPG from current cachefile.")),
			getConfigListEntry(_("Manual reload EPG"), config.plugins.epgrefresh_extra.manual_reload, _("Manual saving and loading EPG from current cachefile.")),
			getConfigListEntry(_("Manual restore EPG backup"), config.plugins.epgrefresh_extra.restore_backup, _("Manual restore EPG from backup cachefile and loading.")),
			getConfigListEntry(_("Automatic save EPG"), config.plugins.epgrefresh_extra.cachesavesched, _("Automatic saving EPG in current cachefile after a specified time.")),
			getConfigListEntry(_("Save every (in hours)"), config.plugins.epgrefresh_extra.cachesavetimer, _("Do not set too short period of time.")),
			getConfigListEntry(_("Automatic load EPG"), config.plugins.epgrefresh_extra.cacheloadsched, _("Automatic loading EPG from current cachefile after a specified time.")),
			getConfigListEntry(_("Load every (in hours)"), config.plugins.epgrefresh_extra.cacheloadtimer, _("This option is not recommended to be used only in exceptional cases. Do not set too short period of time.")),
			getConfigListEntry(_("EPG cache path"), config.plugins.epgrefresh_extra.add_epgcachepath, _("Select the path to EPG cache,not recommended to use the internal flash.")),
			getConfigListEntry(_("EPG cache filename"), config.plugins.epgrefresh_extra.epgcachefilename, _("Select the file name EPG cache, if you do not like credit default name.")),
			getConfigListEntry(_("Create backup when saving EPG"), config.plugins.epgrefresh_extra.save_backup, _("Create backup cachefile, after manual or automatic saving EPG.")),
			getConfigListEntry(_("Auto restore EPG backup on boot"), config.plugins.epgrefresh_extra.autorestore_backup, _("Auto restore EPG from backup cachefile and loading on boot.")),
			getConfigListEntry(_("Show manual change EPG in main menu"), config.plugins.epgrefresh_extra.main_menu, _("Changes are needed to restart enigma2.")),
			getConfigListEntry(_("Show download exUSSR EPG in list setup"), config.plugins.epgrefresh_extra.add_ruepg, _("If you want to download from the internet russian ERG, put to yes.")),
			getConfigListEntry(_("Show \"AutoZap\" in extension menu"), config.plugins.epgrefresh_extra.show_autozap, _("Automatic switching of all the services in the current channel list after a specified time. Stop switch can only manually.")),
			getConfigListEntry(_("Duration to stay on service (sec) for \"AutoZap\" "), config.plugins.epgrefresh_extra.timeout_autozap, _("This is the duration each service/channel will stay active during a refresh.")),
                ]
		if config.plugins.epgrefresh_extra.add_ruepg:
			self.list.insert(3, getConfigListEntry(_("Download internet EPG from exUSSR"), config.plugins.epgrefresh_extra.load_ruepg, _("Press OK to download EPG with http://linux-sat.tv.")))

		ConfigListScreen.__init__(self, self.list, session = session, on_change = self.changed)

		def selectionChanged():
			if self["config"].current:
				self["config"].current[1].onDeselect(self.session)
			self["config"].current = self["config"].getCurrent()
			if self["config"].current:
				self["config"].current[1].onSelect(self.session)
			for x in self["config"].onSelectionChanged:
				x()

		self["config"].selectionChanged = selectionChanged
		self["config"].onSelectionChanged.append(self.updateHelp)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["epgcachelocation"] = StaticText()
		self["help"] = StaticText()
		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"cancel": self.keyCancel,
				"save": self.keySave,
				"ok": self.keyOK,
			}
		)
		self.updateDestination()
		self.changed()
		self.onLayoutFinish.append(self.setCustomTitle)

	def setCustomTitle(self):
		self.setTitle(self.setup_title)

	def updateDestination(self):
		file_infos = ""
		if os.path.exists(config.misc.epgcache_filename.value):
			from os import stat as os_stat
			try:
				file_stats = os_stat(config.misc.epgcache_filename.value)
				file_infos = _("Size: ") + str(self.Humanizer(file_stats.st_size)) + "    "
			except:
				file_infos = "    "
		epgcachelocationlabel = _("Current EPG cachefile:") + " " + config.misc.epgcache_filename.value + "\n" + file_infos
		self["epgcachelocation"].setText(epgcachelocationlabel)

	def Humanizer(self, size):
		if (size < 1024):
			humansize = str(size)+" B"
		elif (size < 1048576):
			humansize = str(size/1024)+" KB"
		else:
			humansize = str(size/1048576)+" MB"
		return humansize

	def updateHelp(self):
		cur = self["config"].getCurrent()
		if cur:
			self["help"].text = cur[2]

	def keyOK(self):
		ConfigListScreen.keyOK(self)
		sel = self["config"].getCurrent()[1]
		if sel == config.plugins.epgrefresh_extra.manual_save:
			self.session.openWithCallback(self.setEpgSave, MessageBox,_("Are you sure you want to save the EPG Cache to:\n") + config.misc.epgcache_filename.value, MessageBox.TYPE_YESNO)
		if sel == config.plugins.epgrefresh_extra.manual_load:
			self.session.openWithCallback(self.setEpgLoad, MessageBox,_("Are you sure you want to load the EPG data from:\n") + config.misc.epgcache_filename.value, MessageBox.TYPE_YESNO)
		if sel == config.plugins.epgrefresh_extra.manual_reload:
			self.session.openWithCallback(self.setEpgReload, MessageBox,_("Are you sure you want to save and load the EPG data from:\n") + config.misc.epgcache_filename.value, MessageBox.TYPE_YESNO)
		if sel == config.plugins.epgrefresh_extra.restore_backup:
			restore_backup = config.misc.epgcache_filename.value + ".backup"
			if os.path.exists(restore_backup):
				try:
					os.system("cp -f %s %s" % (restore_backup, config.misc.epgcache_filename.value ))
					os.chmod("%s" % (config.misc.epgcache_filename.value), 0644)
					self.setEpgLoad(True)
					self.setEpgSave(True)
					if os.path.exists(config.misc.epgcache_filename.value):
						self.session.open(MessageBox, _("Backup file load!"), MessageBox.TYPE_INFO, timeout = 4)
					else:
						try:
							os.system("rm -f %s" % (restore_backup))
							self.session.open(MessageBox, _("Backup file is corrupt!\nBackup file will be deleted!"), MessageBox.TYPE_INFO, timeout = 4)
						except:
							pass
					self.updateDestination()
				except:
					pass
			else:
				self.session.open(MessageBox, _("Backup file is not found!"), MessageBox.TYPE_INFO, timeout = 4)
		if sel == config.plugins.epgrefresh_extra.load_ruepg:
			self.pre_startDownload()

	def pre_startDownload(self):
		choicelist = [
		(_("Russian language"), self.startDownload),
		(_("Ukrainian language"), self.start_ukr_Download),
		]
		dlg = self.session.openWithCallback(self.menuCallback,ChoiceBox,list = choicelist,title= _("Select language for download:"))
		dlg.setTitle(_("EPG with Linux-Sat"))

	def menuCallback(self, ret = None):
		ret and ret[1]()

	def startDownload(self):
		down_lang = "ru"
		if self.ismounted(config.plugins.epgrefresh_extra.epgcachepath.value) == 1:
			down_file = config.misc.epgcache_filename.value + ".gz"
			os.system("wget -q http://linux-sat.tv/epg/epg_%s.dat.gz -O %s" % (down_lang, down_file))
			self.copiTimer = eTimer()
			self.copiTimer.timeout.get().append(self.copiEpg)
			self.copiTimer.start(4000, True)
			self.session.open(MessageBox,(_("Please wait...")), MessageBox.TYPE_INFO, timeout = 4)
		else:
			self.session.open(MessageBox,(_("Not found the mounted device for EPG file!")), MessageBox.TYPE_INFO, timeout = 6 )

	def start_ukr_Download(self):
		down_lang = "ua"
		if self.ismounted(config.plugins.epgrefresh_extra.epgcachepath.value) == 1:
			down_file = config.misc.epgcache_filename.value + ".gz"
			os.system("wget -q http://linux-sat.tv/epg/epg_%s.dat.gz -O %s" % (down_lang, down_file))
			self.copiTimer = eTimer()
			self.copiTimer.timeout.get().append(self.copiEpg)
			self.copiTimer.start(4000, True)
			self.session.open(MessageBox,(_("Please wait...")), MessageBox.TYPE_INFO, timeout = 4)
		else:
			self.session.open(MessageBox,(_("Not found the mounted device for EPG file!")), MessageBox.TYPE_INFO, timeout = 6 )

	def copiEpg(self):
		self.copiTimer.stop()
		down_file = config.misc.epgcache_filename.value + ".gz"
		if os.path.exists(down_file):
			try:
				if os.path.exists(config.misc.epgcache_filename.value):
					os.system("rm -f %s" % (config.misc.epgcache_filename.value))
				os.system("gzip -df %s" % (down_file))
				time.sleep(3)
				os.chmod("%s" % (config.misc.epgcache_filename.value), 0644)
				from enigma import eEPGCache
				epgcache = eEPGCache.getInstance()
				epgcache.load()
				if os.path.exists(config.misc.epgcache_filename.value):
					os.system("rm -f %s" % (config.misc.epgcache_filename.value))
				self.setEpgSave(True)
				if os.path.exists(config.misc.epgcache_filename.value):
					self.session.open(MessageBox,(_("EPG is loaded!")), MessageBox.TYPE_INFO, timeout = 5 )
				else:
					self.session.open(MessageBox,(_("Sorry, EPG was downloaded but not loaded!\nMaybe EPG file is corrupt!")), MessageBox.TYPE_INFO, timeout = 5 )
				self.updateDestination()
			except:
				self.session.open(MessageBox,(_("Sorry, the EPG download failed!")), MessageBox.TYPE_INFO, timeout = 5 )
		else:
			self.session.open(MessageBox,(_("Sorry, the EPG download failed!")), MessageBox.TYPE_INFO, timeout = 5 )

	def ismounted(self, what):
		try:
			for line in open("/proc/mounts"):
				if line.find(what[:-1]) > -1:
					return 1
		except:
			return 0
		return 0

	def setEpgSave(self, answer):
		if answer:
			from enigma import eEPGCache
			epgcache = eEPGCache.getInstance()
			epgcache.save()
			self.updateDestination()
			if config.plugins.epgrefresh_extra.save_backup.value and config.plugins.epgrefresh_extra.epgcachepath.value != "/etc/enigma2/":
				restore_backup = config.misc.epgcache_filename.value + ".backup"
				if os.path.exists(config.misc.epgcache_filename.value):
					try:
						os.system("cp -f %s %s" % (config.misc.epgcache_filename.value, restore_backup))
						os.chmod("%s" % (restore_backup), 0644)
					except:
						pass

	def setEpgLoad(self, answer):
		if answer:
			from enigma import eEPGCache
			epgcache = eEPGCache.getInstance()
			epgcache.load()

	def setEpgReload(self, answer):
		if answer:
			from enigma import eEPGCache
			epgcache = eEPGCache.getInstance()
			epgcache.save()
			epgcache = eEPGCache.getInstance()
			epgcache.load()
			self.updateDestination()
			if config.plugins.epgrefresh_extra.save_backup.value and config.plugins.epgrefresh_extra.epgcachepath.value != "/etc/enigma2/":
				restore_backup = config.misc.epgcache_filename.value + ".backup"
				if os.path.exists(config.misc.epgcache_filename.value):
					try:
						os.system("cp -f %s %s" % (config.misc.epgcache_filename.value, restore_backup))
						os.chmod("%s" % (restore_backup), 0644)
					except:
						pass

	def changed(self):
		for x in self.onChangedEntry:
			try:
				x()
			except Exception:
				pass

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def createSummary(self):
		return SetupSummary

	def cancelConfirm(self, result):
		if not result:
			return
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(
				self.cancelConfirm,
				MessageBox,
				_("Really close without saving settings?")
			)
		else:
			self.close()

	def updateEpgCache(self):
		config.misc.epgcache_filename.setValue(os.path.join(config.plugins.epgrefresh_extra.epgcachepath.value, config.plugins.epgrefresh_extra.epgcachefilename.value.replace(".dat","") + ".dat"))
		config.misc.epgcache_filename.save()
		configfile.save()
		if self.prev_lastepgcachepath != config.misc.epgcache_filename.value:
			from enigma import eEPGCache
			eEPGCache.getInstance().setCacheFile(config.misc.epgcache_filename.value)
			eEPGCache.getInstance().save()
			self.updateDestination()
			if config.plugins.epgrefresh_extra.save_backup.value and config.plugins.epgrefresh_extra.epgcachepath.value != "/etc/enigma2/":
				restore_backup = config.misc.epgcache_filename.value + ".backup"
				if os.path.exists(config.misc.epgcache_filename.value):
					try:
						os.system("cp -f %s %s" % (config.misc.epgcache_filename.value, restore_backup))
						os.chmod("%s" % (restore_backup), 0644)
					except:
						pass

	def keySave(self):
		if config.plugins.epgrefresh_extra.cachesavesched.value or config.plugins.epgrefresh_extra.cacheloadsched.value:
			if fileExists("/usr/lib/enigma2/python/Plugins/Extensions/EPGD/plugin.py"):
				try:
					same_options = config.plugins.epgd.autosave.value
				except:
					same_options = False
				if same_options:
					if config.plugins.epgd.autosave.value != "0":
						self.session.open(MessageBox, _("The same functions are used in plugin EPGD!!"), MessageBox.TYPE_INFO)
						config.plugins.epgrefresh_extra.cachesavesched.value = False
						config.plugins.epgrefresh_extra.cacheloadsched.value = False
						return
			try:
				same_options = config.epg.cacheloadsched.value or config.epg.cachesavesched.value
			except:
				same_options = False
			if same_options:
				self.session.open(MessageBox, _("The same functions are used in Menu -> System -> EPG settings!"), MessageBox.TYPE_INFO)
				config.plugins.epgrefresh_extra.cachesavesched.value = False
				config.plugins.epgrefresh_extra.cacheloadsched.value = False
				return
		if config.plugins.epgrefresh_extra.add_epgcachepath.value and config.plugins.epgrefresh_extra.add_epgcachepath.value != '/':
			config.plugins.epgrefresh_extra.epgcachepath.value = config.plugins.epgrefresh_extra.add_epgcachepath.value
			config.plugins.epgrefresh_extra.epgcachepath.save()
		for x in self["config"].list:
			x[1].save()
		self.updateEpgCache()
		if self.prev_lastepgcachepath != config.misc.epgcache_filename.value:
			if os.path.exists(self.prev_lastepgcachepath):
				try:
					os.remove(self.prev_lastepgcachepath)
				except:
					pass
			restore_backup = self.prev_lastepgcachepath + ".backup"
			if os.path.exists(restore_backup):
				try:
					os.remove(restore_backup)
				except:
					pass
		self.close()

class ManualEPGlist(Screen):
	skin = """
		<screen position="center,center" size="380,140" title="%s">
			<widget name="list" position="5,5" size="370,130" />
		</screen>""" % _("Select options")

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self["list"] = MenuList([])
		self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.okClicked, "cancel": self.close}, -1)
		self.onLayoutFinish.append(self.showMenu)

	def showMenu(self):
		list = []
		list.append(_("Manual save EPG"))
		list.append(_("Manual load EPG"))
		list.append(_("Manual reload EPG"))
		if config.plugins.epgrefresh_extra.add_ruepg.value:
			list.append(_("Download EPG from exUSSR"))
		list.append(_("Configuration..."))
		self["list"].setList(list)

	def okClicked(self):
		sel = self["list"].getCurrent()
		if sel == _("Manual save EPG"):
			self.session.openWithCallback(self.manualsetEpgSave, MessageBox,_("Are you sure you want to save the EPG Cache to:\n") + config.misc.epgcache_filename.value, MessageBox.TYPE_YESNO)
		if sel == _("Manual load EPG"):
			self.session.openWithCallback(self.manualsetEpgLoad, MessageBox,_("Are you sure you want to load the EPG data from:\n") + config.misc.epgcache_filename.value, MessageBox.TYPE_YESNO)
		if sel == _("Manual reload EPG"):
			self.session.openWithCallback(self.manualsetEpgReload, MessageBox,_("Are you sure you want to save and load the EPG data from:\n") + config.misc.epgcache_filename.value, MessageBox.TYPE_YESNO)
		if sel == _("Configuration..."):
			self.session.open(EPGSaveLoadConfiguration)
		if sel == _("Download EPG from exUSSR"):
			self.pre_startDownload()

	def pre_startDownload(self):
		choicelist = [
		(_("Russian language"), self.startDownload),
		(_("Ukrainian language"), self.start_ukr_Download),
		]
		dlg = self.session.openWithCallback(self.menuCallback,ChoiceBox,list = choicelist,title= _("Select language for download:"))
		dlg.setTitle(_("EPG with Linux-Sat"))

	def menuCallback(self, ret = None):
		ret and ret[1]()

	def startDownload(self):
		down_lang = "ru"
		if self.ismounted(config.plugins.epgrefresh_extra.epgcachepath.value) == 1:
			down_file = config.misc.epgcache_filename.value + ".gz"
			os.system("wget -q http://linux-sat.tv/epg/epg_%s.dat.gz -O %s" % (down_lang, down_file))
			self.copiTimer = eTimer()
			self.copiTimer.timeout.get().append(self.copiEpg)
			self.copiTimer.start(4000, True)
			self.session.open(MessageBox,(_("Please wait...")), MessageBox.TYPE_INFO, timeout = 4)
		else:
			self.session.open(MessageBox,(_("Not found the mounted device for EPG file!")), MessageBox.TYPE_INFO, timeout = 6 )

	def start_ukr_Download(self):
		down_lang = "ua"
		if self.ismounted(config.plugins.epgrefresh_extra.epgcachepath.value) == 1:
			down_file = config.misc.epgcache_filename.value + ".gz"
			os.system("wget -q http://linux-sat.tv/epg/epg_%s.dat.gz -O %s" % (down_lang, down_file))
			self.copiTimer = eTimer()
			self.copiTimer.timeout.get().append(self.copiEpg)
			self.copiTimer.start(4000, True)
			self.session.open(MessageBox,(_("Please wait...")), MessageBox.TYPE_INFO, timeout = 4)
		else:
			self.session.open(MessageBox,(_("Not found the mounted device for EPG file!")), MessageBox.TYPE_INFO, timeout = 6 )

	def copiEpg(self):
		self.copiTimer.stop()
		down_file = config.misc.epgcache_filename.value + ".gz"
		if os.path.exists(down_file):
			try:
				if os.path.exists(config.misc.epgcache_filename.value):
					os.system("rm -f %s" % (config.misc.epgcache_filename.value))
				os.system("gzip -df %s" % (down_file))
				time.sleep(3)
				os.chmod("%s" % (config.misc.epgcache_filename.value), 0644)
				from enigma import eEPGCache
				epgcache = eEPGCache.getInstance()
				epgcache.load()
				if os.path.exists(config.misc.epgcache_filename.value):
					os.system("rm -f %s" % (config.misc.epgcache_filename.value))
				self.manualsetEpgSave(True)
				if os.path.exists(config.misc.epgcache_filename.value):
					self.session.open(MessageBox,(_("EPG is loaded!")), MessageBox.TYPE_INFO, timeout = 5 )
				else:
					self.session.open(MessageBox,(_("Sorry, EPG was downloaded but not loaded!\nMaybe EPG file is corrupt!")), MessageBox.TYPE_INFO, timeout = 5 )
			except:
				self.session.open(MessageBox,(_("Sorry, the EPG download failed!")), MessageBox.TYPE_INFO, timeout = 5 )
		else:
			self.session.open(MessageBox,(_("Sorry, the EPG download failed!")), MessageBox.TYPE_INFO, timeout = 5 )

	def ismounted(self, what):
		try:
			for line in open("/proc/mounts"):
				if line.find(what[:-1]) > -1:
					return 1
		except:
			return 0

	def manualsetEpgSave(self, answer):
		if answer:
			from enigma import eEPGCache
			epgcache = eEPGCache.getInstance()
			epgcache.save()
			self.setBackup()

	def manualsetEpgLoad(self, answer):
		if answer:
			from enigma import eEPGCache
			epgcache = eEPGCache.getInstance()
			epgcache.load()

	def manualsetEpgReload(self, answer):
		if answer:
			from enigma import eEPGCache
			epgcache = eEPGCache.getInstance()
			epgcache.save()
			epgcache = eEPGCache.getInstance()
			epgcache.load()
			self.setBackup()

	def setBackup(self):
		if config.plugins.epgrefresh_extra.save_backup.value and config.plugins.epgrefresh_extra.epgcachepath.value != "/etc/enigma2/":
			restore_backup = config.misc.epgcache_filename.value + ".backup"
			if os.path.exists(config.misc.epgcache_filename.value):
				try:
					os.system("cp -f %s %s" % (config.misc.epgcache_filename.value, restore_backup))
					os.chmod("%s" % (restore_backup), 0644)
				except:
					pass
