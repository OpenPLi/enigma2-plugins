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
from enigma import eTimer, getDesktop, eEPGCache
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
			<widget name="config" position="5,50" size="590,428" scrollbarMode="showOnDemand" />
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
		self.list = [
			getConfigListEntry(_("Save EPG"), config.plugins.epgrefresh_extra.manual_save, _("Manually save EPG to current cache file.")),
			getConfigListEntry(_("Load EPG"), config.plugins.epgrefresh_extra.manual_load, _("Manually load EPG from current cachefile.")),
			getConfigListEntry(_("Clear EPG"), config.plugins.epgrefresh_extra.delete_backup, _("Manually clear EPG (choose method).")),
			getConfigListEntry(_("Reload EPG"), config.plugins.epgrefresh_extra.manual_reload, _("Manually load EPG from current cache file.")),
			getConfigListEntry(_("Restore EPG backup"), config.plugins.epgrefresh_extra.restore_backup, _("Manually restore EPG from backup cache file.")),
			getConfigListEntry(_("Automatically save EPG"), config.plugins.epgrefresh_extra.cachesavesched, _("Enable automatic EPG save interval.")),
			getConfigListEntry(_("Automatic save period (in hours)"), config.plugins.epgrefresh_extra.cachesavetimer, _("Configure EPG save interval, if enabled.")),
			getConfigListEntry(_("Automatically load EPG"), config.plugins.epgrefresh_extra.cacheloadsched, _("Automatic EPG loading from current cache file.")),
			getConfigListEntry(_("Automatic load period (in hours)"), config.plugins.epgrefresh_extra.cacheloadtimer, _("Configure EPG load interval, if enabled. This is an option for experienced users.")),
			getConfigListEntry(_("EPG cache file path"), config.plugins.epgrefresh_extra.epgcachepath, _("Select the path to EPG cache file. Don't use the internal flash if not necessary!")),
			getConfigListEntry(_("EPG cache file filename"), config.plugins.epgrefresh_extra.epgcachefilename, _("Select the file name for the EPG cache file.")),
			getConfigListEntry(_("Create backup when saving EPG"), config.plugins.epgrefresh_extra.save_backup, _("Create a backup cache file, after manually or automatically saving EPG.")),
			getConfigListEntry(_("Automatically restore EPG backup on boot"), config.plugins.epgrefresh_extra.autorestore_backup, _("Load EPG from backup cache file when booting.")),
			getConfigListEntry(_("Show entry 'Manually change EPG' in main menu"), config.plugins.epgrefresh_extra.main_menu, _("Restart enigma2 to effectuate.")),
			getConfigListEntry(_("Show entry 'AutoZap' in extensions menu"), config.plugins.epgrefresh_extra.show_autozap, _("Enable automatic zapping of all services in the current services list.")),
			getConfigListEntry(_("Duration to show each service (in seconds) for 'AutoZap'"), config.plugins.epgrefresh_extra.timeout_autozap, _("This is the duration each service will be shown in AutoZap mode.")),
		]
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
			self.session.openWithCallback(self.setEpgSave, MessageBox,_("Are you sure you want to save the EPG cache to:\n") + config.misc.epgcache_filename.value, MessageBox.TYPE_YESNO)
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
		if sel == config.plugins.epgrefresh_extra.epgcachepath:
			self.setEPGCachePath()
		if sel == config.plugins.epgrefresh_extra.delete_backup:
			self.deleteEPG()

	def setEPGCachePath(self):
		inhibitDirs = ["/autofs", "/bin", "/boot", "/dev", "/lib", "/proc", "/sbin", "/sys", "/tmp", "/usr"]
		from Screens.LocationBox import LocationBox
		txt = _("Input EPG Cache path")
		self.session.openWithCallback(self.setEPGCachePathBack, LocationBox, text=txt, currDir=config.plugins.epgrefresh_extra.epgcachepath.value,
				bookmarks=config.plugins.epgrefresh_extra.bookmarks, autoAdd=False, editDir=True, minFree=20, inhibitDirs=inhibitDirs)
	def setEPGCachePathBack(self, res):
		if res is not None:
			config.plugins.epgrefresh_extra.epgcachepath.value = res

	def deleteEPG(self):
		menu = [(_("Clear only in memory (RAM) EPG"), "ram"),(_("Clear only epg.dat and epg.dat.backup"), "dat"),(_("Clear all EPG"), "all")]
		def removeEPGAction(choice):
			if choice is not None:
				try:
					epgcache = eEPGCache.getInstance()
					if choice[1] == "ram":
						if hasattr(epgcache, 'flushEPG'):
							epgcache.flushEPG()
					elif choice[1] == "dat":
						restore_backup = config.misc.epgcache_filename.value + ".backup"
						os.system("rm -f %s" % (restore_backup))
						os.system("rm -f %s" % (config.misc.epgcache_filename.value))
					elif choice[1] == "all":
						if hasattr(epgcache, 'flushEPG'):
							epgcache.flushEPG()
						restore_backup = config.misc.epgcache_filename.value + ".backup"
						os.system("rm -f %s" % (restore_backup))
						os.system("rm -f %s" % (config.misc.epgcache_filename.value))
					self.updateDestination()
				except:
					pass
		self.session.openWithCallback(removeEPGAction, ChoiceBox, title= _("Select action:"), list=menu)

	def setEpgSave(self, answer):
		if answer:
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
			epgcache = eEPGCache.getInstance()
			epgcache.load()

	def setEpgReload(self, answer):
		if answer:
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
		list.append(_("Manually save EPG"))
		list.append(_("Manually load EPG"))
		list.append(_("Manually reload EPG"))
		list.append(_("Configuration..."))
		self["list"].setList(list)

	def okClicked(self):
		sel = self["list"].getCurrent()
		if sel == _("Manually save EPG"):
			self.session.openWithCallback(self.manualsetEpgSave, MessageBox,_("Are you sure you want to save the EPG cache to:\n") + config.misc.epgcache_filename.value, MessageBox.TYPE_YESNO)
		if sel == _("Manually load EPG"):
			self.session.openWithCallback(self.manualsetEpgLoad, MessageBox,_("Are you sure you want to load the EPG data from:\n") + config.misc.epgcache_filename.value, MessageBox.TYPE_YESNO)
		if sel == _("Manually reload EPG"):
			self.session.openWithCallback(self.manualsetEpgReload, MessageBox,_("Are you sure you want to save and load the EPG data from:\n") + config.misc.epgcache_filename.value, MessageBox.TYPE_YESNO)
		if sel == _("Configuration..."):
			self.session.open(EPGSaveLoadConfiguration)

	def manualsetEpgSave(self, answer):
		if answer:
			epgcache = eEPGCache.getInstance()
			epgcache.save()
			self.setBackup()

	def manualsetEpgLoad(self, answer):
		if answer:
			epgcache = eEPGCache.getInstance()
			epgcache.load()

	def manualsetEpgReload(self, answer):
		if answer:
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
