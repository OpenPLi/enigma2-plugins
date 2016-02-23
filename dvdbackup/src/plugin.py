##
## DVD Backup plugin for enigma2 by AliAbdul
## using the great open source dvdbackup by Olaf Beck
##
from Components.ActionMap import ActionMap
from Components.config import config, ConfigSubsection, ConfigText, ConfigYesNo, getConfigListEntry, ConfigSelection, NoSave
from Components.ConfigList import ConfigListScreen
from Components.Console import Console
from Components.Label import Label
from Components.Language import language
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryProgress
from Components.Scanner import Scanner, ScanPath
from enigma import eListboxPythonMultiContent, eTimer, gFont, RT_HALIGN_CENTER
from Plugins.Plugin import PluginDescriptor
from Screens.LocationBox import LocationBox
from Screens.MessageBox import MessageBox
from Components.Harddisk import harddiskmanager
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.ChoiceBox import ChoiceBox
from time import time
from Tools.BoundFunction import boundFunction
from Tools.Directories import fileExists, resolveFilename, SCOPE_LANGUAGE, SCOPE_PLUGINS
import gettext, os, stat
import skin

#################################################

PluginLanguageDomain = "DVDBackup"
PluginLanguagePath = "Extensions/DVDBackup/locale/"
 
def localeInit():
	gettext.bindtextdomain(PluginLanguageDomain, resolveFilename(SCOPE_PLUGINS, PluginLanguagePath))

def _(txt):
	if gettext.dgettext(PluginLanguageDomain, txt):
		return gettext.dgettext(PluginLanguageDomain, txt)
	else:
		return gettext.gettext(txt)

language.addCallback(localeInit())

#################################################

config.plugins.DVDBackup = ConfigSubsection()
config.plugins.DVDBackup.device = NoSave(ConfigText(default="/dev/sr0", fixed_size=False))
config.plugins.DVDBackup.directory = ConfigText(default="/media/hdd", fixed_size=False)
config.plugins.DVDBackup.name = NoSave(ConfigText(default=_("Name of DVD"), fixed_size=False))
config.plugins.DVDBackup.log = ConfigYesNo(default=True)
config.plugins.DVDBackup.show_message = ConfigYesNo(default=True)
config.plugins.DVDBackup.create_iso = ConfigSelection(default = "no", choices = [("no", _("no")),("genisoimage", _("with genisoimage (slower)")),("dd", _("with dd (faster)"))])
cfg = config.plugins.DVDBackup

#################################################

SESSION = None

def isCdromMount(file=None):
	if file:
		try:
			f = open('/proc/mounts', 'r')
			mnt = f.readlines()
			f.close()
			for line in mnt:
				if line.startswith("/dev/sr0") and file in line:
					return True
		except:
			pass
	return False

def isCDdevice():
	cd = harddiskmanager.getCD()
	if cd:
		file_path = harddiskmanager.getAutofsMountpoint(cd)
		if (os.path.exists(os.path.join(file_path, "VIDEO_TS")) or os.path.exists(os.path.join(file_path, "video_ts"))) and isCdromMount(file_path):
			return file_path
	return ""

def message(msg):
	if SESSION and cfg.show_message:
		SESSION.open(MessageBox, msg, type=MessageBox.TYPE_ERROR, timeout=10)

def Humanizer(size):
	try:
		if (size < 1024):
			humansize = str(size)+ _(" B")
		elif (size < 1048576):
			humansize = str(size/1024) + _(" KB")
		else:
			humansize = str(size/1048576) + _(" MB")
		return humansize
	except:
		pass
	return "--"

#################################################

class DVDBackupFile:
	def __init__(self, name, size):
		self.name = name
		if name != "genisoimage":
			if name == "dd":
				self.name = ("%s/%s.iso" % (cfg.directory.value, cfg.name.value)).replace("//", "/")
			else:
				self.name = ("%s/%s/%s" % (cfg.directory.value, cfg.name.value, name)).replace("//", "/")
		self.size = size
		self.progress = 0

	def checkProgress(self):
		if self.name != "genisoimage":
			if fileExists(self.name):
				if self.progress < 100:
					file_stats = os.stat(self.name)
					self.progress = 100.0 * file_stats[stat.ST_SIZE] / self.size
			else:
				self.progress = 0

#################################################

class DVDBackup:
	def __init__(self):
		self.console = Console()
		self.working = False
		self.error = ""
		self.startTime = None
		self.files = []

	def backup(self):
		self.error = ""
		self.working = True
		self.startTime = time()
		del self.files
		self.files = []
		if fileExists("/tmp/dvdbackup.log"):
			try:
				os.system("rm /tmp/dvdbackup.log")
			except:
				pass
		self.getInfo()

	def getInfo(self):
		if cfg.create_iso.value == "dd":
			self.console.ePopen("dvdbackup --info -i /dev/sr0", self.isoWithDD)
		else:
			self.console.ePopen("dvdbackup --info -i %s" % cfg.device.value, self.gotInfo)

	def isoFinished(self, result, retval, extra_args):
		if retval != 0:
			msg = _("Error while backup of DVD!")
			message(msg)
			print "[DVD Backup]", retval, result
			self.working = False
			self.error = msg
		else:
			print "[DVD Backup]", result, retval, extra_args
			self.working = False
			self.finished()

	def isoWithDD(self, result, retval, extra_args):
		size = self.getDVDSize(result, retval, extra_args)
		if size > 0:
			self.files.append(DVDBackupFile("dd", int(size)))
			self.console.ePopen("dd if=/dev/sr0 of=%s%s.iso bs=2048 conv=sync" % (cfg.directory.value,cfg.name.value), self.isoFinished)

	def getDVDSize(self, result, retval, extra_args):
		size = 0
		firstPhrase = "File Structure DVD"; lastPhrase = "Main feature:"
		if result and result.__contains__(firstPhrase) and result.__contains__(lastPhrase):
			result = result[result.index(firstPhrase)+len(firstPhrase)+1: result.index(lastPhrase)]
			print "[DVD Backup]",result
			lines = result.split("\n")
			for line in lines:
				tmp = line.split("\t")
				if len(tmp) == 4:
					if not tmp[1].__contains__("VTS_00_0."):
						size += int(tmp[2])
			print "[DVD Backup]",size, size / 2048
		else:
			msg = _("Could not read the DVD informations!")
			message(msg)
			print "[DVD Backup]",result
			self.working = False
			self.error = msg
		return size

	def gotInfo(self, result, retval, extra_args):
		firstPhrase = "File Structure DVD"; lastPhrase = "Main feature:"
		if result and result.__contains__(firstPhrase) and result.__contains__(lastPhrase):
			result = result[result.index(firstPhrase)+len(firstPhrase)+1: result.index(lastPhrase)]
			print "[DVD Backup]",result
			lines = result.split("\n")
			folder = ""
			for line in lines:
				tmp = line.split("\t")
				if len(tmp) == 1:
					folder = tmp[0]
				elif len(tmp) == 4:
					name = folder+tmp[1]
					size = tmp[2]
					if size.__contains__("."):
						size = size[:size.index(".")]
					if not name.__contains__("VTS_00_0."):
						self.files.append(DVDBackupFile(name, int(size)))
			if len(self.files) > 0:
				if cfg.log.value:
					log = " 2>> /tmp/dvdbackup.log"
				else:
					log = ""
				cmd = 'dvdbackup -M -v -i %s -o "%s" -n "%s"%s' % (cfg.device.value, cfg.directory.value, cfg.name.value, log)
				self.console.ePopen(cmd, self.dvdbackupFinished)
			else:
				msg = _("Could not find any file to backup!")
				message(msg)
				self.working = False
				self.error = msg
		else:
			msg = _("Could not read the DVD informations!")
			message(msg)
			print "[DVD Backup]",result
			self.working = False
			self.error = msg

	def dvdbackupFinished(self, result, retval, extra_args):
		if retval != 0:
			msg = _("Error while backup of DVD!")
			message(msg)
			print "[DVD Backup]", retval, result
			self.working = False
			self.error = msg
		else:
			if cfg.create_iso.value == "genisoimage":
				path = ("%s/%s" % (cfg.directory.value, cfg.name.value)).replace("//", "/")
				self.genisoimage = DVDBackupFile("genisoimage", "")
				self.files.append(self.genisoimage)
				cmd = 'genisoimage -dvd-video -udf -o "%s.iso" "%s"' % (path, path)
				self.console.ePopen(cmd, self.genisoimageCallback)
				self.console.appContainers[cmd].dataAvail.append(boundFunction(self.genisoimageProgress, cmd))
			else:
				self.finished()

	def genisoimageProgress(self, name, data):
		if data.__contains__("%"):
			for x in data.split("\n"):
				if x.__contains__("%"):
					x = x[:x.index("%")]
					if x.__contains__("."):
						x = x[:x.index(".")]
					x = x.replace(" ", "")
					if x != "":
						self.genisoimage.progress = int(x)

	def genisoimageCallback(self, result, retval, extra_args):
		if retval != 0:
			msg = _("Error while backup of DVD!")
			message(msg)
			print "[DVD Backup]", result
			self.working = False
			self.error = msg
		else:
			self.genisoimage.progress = 100
			path = ("%s/%s" % (cfg.directory.value, cfg.name.value)).replace("//", "/")
			try:
				file = "%s.iso" % path
				file_stats = os.stat(file)
				self.genisoimage.size = file_stats.st_size
			except OSError:
				pass
			if SESSION:
				SESSION.openWithCallback(self.genisoimageCallback2, MessageBox, _("genisoimage job done.\nDelete DVD directory?") + "\n%s" % path, default=False)

	def genisoimageCallback2(self, yesno):
		if yesno:
			cmd = ("rm -R '%s/%s'" % (cfg.directory.value, cfg.name.value)).replace("//", "/")
			try: os.system(cmd)
			except: pass
		self.finished()

	def finished(self):
		seconds = int(time() - self.startTime)
		minutes = 0
		self.error = ""
		self.working = False
		while seconds > 60:
			seconds -= 60
			minutes += 1
		if SESSION:
			if isCDdevice():
				SESSION.openWithCallback(self.eject, MessageBox, "%s\n%s %d:%02d\n\n%s" % (_("Backup of DVD finished."), _("Duration:"), minutes, seconds, _("Eject DVD?")))
			else:
				SESSION.open(MessageBox, "%s\n%s %d:%02d\n" % (_("Backup of DVD finished."), _("Duration:"), minutes, seconds), type=MessageBox.TYPE_INFO)

	def eject(self, answer):
		if answer:
			self.console.ePopen("eject /dev/sr0")

	def abortBackup(self):
		self.working = False
		self.error = ""
		del self.files
		self.files = []
		self.startTime = None
		print "[DVD Backup] abort user"

dvdbackup = DVDBackup()

#################################################

class DVDBackupList(MenuList):
	def __init__(self):
		MenuList.__init__(self, [], False, eListboxPythonMultiContent)
		font = skin.fonts.get("DVDbackupList", ("Regular", 20, 25))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setItemHeight(font[2])

#################################################

def DVDBackupListEntry(file):
	res = [(file)]
	a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p = skin.parameters.get("DVDbackupList1",(0, 0, 180, 25, 200, 0, 120, 25, 340, 9, 100, 7, 460, 0, 60, 25))
	res.append(MultiContentEntryText(pos = (a, b), size = (c, d), font = 0, text = file.name.split("/")[-1]))
	res.append(MultiContentEntryText(pos = (e, f), size = (g, h), font = 0, text = "%s" % Humanizer(file.size), flags=RT_HALIGN_CENTER))
	res.append(MultiContentEntryProgress(pos = (i, j), size = (k, l), percent = file.progress, borderWidth = 1))
	res.append(MultiContentEntryText(pos = (m, n), size = (o, p), font = 0, text = "%d%s" % (file.progress, "%"), flags = RT_HALIGN_CENTER))
	return res

#################################################

class DVDBackupProgress(Screen):
	skin = """
	<screen position="center,center" size="560,495" title="DVD Backup Progress">
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" transparent="1" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" transparent="1" alphatest="on" />
		<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="text" position="0,45" zPosition="1" size="560,40" font="Regular;20" valign="center" halign="center" foregroundColor="yellow" transparent="1" />
		<widget name="list" position="0,90" size="560,400" scrollbarMode="showOnDemand" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("DVD Backup Progress"))
		self.refreshTimer = eTimer()
		self.refreshTimer.callback.append(self.refreshList)

		self.console = Console()
		self.working = False

		self["key_red"] = Label(_("Exit"))
		if  dvdbackup.working:
			self["key_green"] = Label(_("Abort"))
		else:
			self["key_green"] = Label()
		self["text"] = Label()

		self["list"] = DVDBackupList()
		
		self["actions"] = ActionMap(["ColorActions", "OkCancelActions"],
			{
				"cancel": self.exit,
				"red": self.exit,
				"green": self.abort
			}, -1)

		self.onLayoutFinish.append(self.refreshList)

	def exit(self):
		if self.working == False:
			self.refreshTimer.stop()
			if not dvdbackup.working:
				dvdbackup.abortBackup()
			self.close()

	def refreshList(self):
		list = []
		tostart = []
		finished = []
		if dvdbackup.error:
			self["text"].setText(dvdbackup.error)
		if not dvdbackup.working:
			self["key_green"].setText("")
			return
		for file in dvdbackup.files:
			file.checkProgress()
			if file.progress == 0:
				tostart.append(DVDBackupListEntry(file))
			elif file.progress == 100:
				finished.append(DVDBackupListEntry(file))
			else:
				list.append(DVDBackupListEntry(file))
		for x in tostart:
			list.append(x)
		for x in finished:
			list.append(x)
		self["list"].setList(list)
		self.refreshTimer.start(3000, True)

	def abort(self):
		if self.working == False and dvdbackup.working:
			self.working = True
			tool = "dvdbackup"
			for file in dvdbackup.files:
				if file.name == "genisoimage":
					tool = "genisoimage"
				elif file.name.endswith(".iso"):
					tool = "dd"
			self.console.ePopen("killall -9 %s" % tool, self.abortCallback)
			if tool == "dd":
				try: os.system("rm '%s'" % file.name)
				except: pass
			else:
				cmd = ("rm -R '%s/%s'" % (cfg.directory.value, cfg.name.value)).replace("//", "/")
				try: os.system(cmd)
				except: pass

	def abortCallback(self, result, retval, extra_args):
		self.working = False
		self.refreshTimer.stop()
		dvdbackup.abortBackup()
		self["list"].setList([])
		self["key_green"].setText("")

#################################################

class DVDBackupScreen(Screen, ConfigListScreen):
	skin = """
	<screen position="center,center" size="560,210" title="DVD Backup">
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" transparent="1" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" transparent="1" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" transparent="1" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" transparent="1" alphatest="on" />
		<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;18" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;18" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="key_yellow" position="280,0" zPosition="1" size="140,40" font="Regular;18" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="key_blue" position="420,0" zPosition="1" size="140,40" font="Regular;18" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="config" position="0,45" size="560,160" scrollbarMode="showOnDemand" />
	</screen>"""

	def __init__(self, session, device=None, foldername=None):
		Screen.__init__(self, session)
		self.setup_title = _("DVD Backup")
		self.setTitle(self.setup_title)
		self.working = False
		self.console = Console()

		self["key_red"] = Label(_("Extra option"))
		self["key_green"] = Label(_("Start backup"))
		self["key_yellow"] = Label(_("Keyboard"))
		self["key_blue"] = Label(_("Location"))

		self.device = device
		if device:
			cfg.device.value = device
		elif cfg.device.value != "/dev/sr0":
			cfg.device.value = "/dev/sr0"
		if foldername:
			cfg.name.value = foldername
		elif cfg.name.value != _("Name of DVD"):
			cfg.name.value = _("Name of DVD")

		ConfigListScreen.__init__(self, [
			getConfigListEntry(_("Device mount folder:"), cfg.device),
			getConfigListEntry(_("Backup directory:"), cfg.directory),
			getConfigListEntry(_("Folder/iso name:"), cfg.name),
			getConfigListEntry(_("Create log (tmp/dvdbackup.log):"), cfg.log),
			getConfigListEntry(_("Show error message:"), cfg.show_message),
			getConfigListEntry(_("Create iso:"), cfg.create_iso)], session = self.session)

		self["actions"] = ActionMap(["ColorActions", "OkCancelActions"],
			{
				"red": self.extraOption,
				"green": self.backup,
				"yellow": self.keyboard,
				"blue": self.location,
				"cancel": self.exit
			}, -1)

		self["config"].onSelectionChanged.append(self.checkConfig)
		self.onLayoutFinish.append(self.getName)

	def getCurrentEntry(self):
		return self["config"].getCurrent() and self["config"].getCurrent()[0] or ""

	def getCurrentValue(self):
		return self["config"].getCurrent() and len(self["config"].getCurrent()) > 1 and str(self["config"].getCurrent()[1].getText()) or ""

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary

	def extraOption(self):
		menu = []
		if self.working == False:
			if not self.device:
				menu.append((_("Auto set name and folder DVD"), "infoname"))
			menu.append((_("Open menu progress"), "progress"))
		if cfg.log.value and fileExists("/tmp/dvdbackup.log"):
			menu.append((_("Show log"), "log"))
		def extraAction(choice):
			if choice is not None:
				if choice[1] == "infoname":
					self.getName()
				elif choice[1] == "progress":
					self.session.open(DVDBackupProgress)
				elif choice[1] == "log":
					from Screens.Console import Console as myConsole
					text = _("Show log")
					cmd = "cat /tmp/dvdbackup.log"
					self.session.open(myConsole, text, [cmd])
		if menu:
			self.session.openWithCallback(extraAction, ChoiceBox, title=_("Extra option"), list=menu)

	def backup(self):
		if self.working == False and not dvdbackup.working:
			start_backup = True
			if cfg.device.value == cfg.directory.value:
				self.session.open(MessageBox, _("Warning!\nThis is the same folder!"), type=MessageBox.TYPE_ERROR, timeout=6)
				return
			if os.path.exists(os.path.join(cfg.device.value, "VIDEO_TS")) or os.path.exists(os.path.join(cfg.device.value, "video_ts")):
				if cfg.create_iso.value == "dd" and not isCDdevice():
					self.session.open(MessageBox, _("Warning!\nThis folder not CD-ROM!"), type=MessageBox.TYPE_ERROR, timeout=6)
					return
				try:
					st = os.statvfs(cfg.device.value)
					size = st.f_bsize * st.f_blocks
					avail = st.f_bsize * st.f_bavail
					dev_used = size - avail
				except OSError:
					dev_used = 0
					start_backup = False
				try:
					st = os.statvfs(cfg.directory.value)
					dir_free = st.f_bsize * st.f_bavail
				except OSError:
					dir_free = 0
					start_backup = False
				if dev_used and dir_free:
					if dev_used > dir_free:
						self.session.open(MessageBox, _("Backup directory too small size!"), type=MessageBox.TYPE_ERROR, timeout=6)
						start_backup = False
				else:
					folder = not dev_used and cfg.device.value or cfg.directory.value
					self.session.open(MessageBox, _("Error read folder %s!") % folder, type=MessageBox.TYPE_ERROR, timeout=6)
			else:
				self.session.open(MessageBox, _("Warning!\nThis folder not DVD structure!"), type=MessageBox.TYPE_ERROR, timeout=6)
				start_backup = False
			if start_backup:
				cfg.create_iso.save()
				cfg.directory.save()
				cfg.show_message.save()
				dvdbackup.backup()
				self.session.openWithCallback(self.close, DVDBackupProgress)

	def exit(self):
		if self.working == False:
			cfg.create_iso.cancel()
			cfg.directory.cancel()
			self.close()

	def checkConfig(self):
		current = self["config"].getCurrent()
		key = current and current[1]
		if key:
			if isinstance(key, ConfigText):
				self["key_yellow"].show()
				if key == cfg.directory or key == cfg.device:
					self["key_blue"].show()
				else:
					self["key_blue"].hide()
			else:
				self["key_yellow"].hide()
				self["key_blue"].hide()

	def keyboard(self):
		if self.working == False:
			current = self["config"].getCurrent()
			if current and len(current) > 1:
				self.toChangeVirtualKeyBoard = current[1]
				if isinstance(self.toChangeVirtualKeyBoard, ConfigText):
					self.session.openWithCallback(self.keyBoardCallback, VirtualKeyBoard, title=current[0], text=self.toChangeVirtualKeyBoard.value)

	def keyBoardCallback(self, callback=None):
		if callback:
			self.toChangeVirtualKeyBoard.value = callback
			self["config"].setList(self["config"].getList())

	def getName(self):
		if self.device:
			return
		self.working = True
		file = cfg.device.value
		file_path = isCDdevice()
		if file_path:
			file ="/dev/sr0"
			cfg.device.value = file_path
		self.console.ePopen("dvdbackup --info -i %s" % file, self.gotInfo)

	def location(self):
		current = self["config"].getCurrent()
		if current and len(current) > 1:
			self.toChangeLocationBox = current[1]
			if self.toChangeLocationBox == cfg.device or self.toChangeLocationBox == cfg.directory:
				self.session.openWithCallback(self.locationCallback, LocationBox)

	def locationCallback(self, callback):
		if callback:
			if self.toChangeLocationBox == cfg.directory:
				cfg.directory.value = callback
				cfg.directory.save()
				self["config"].setList(self["config"].getList())
			elif self.toChangeLocationBox == cfg.device:
				if os.path.exists(os.path.join(callback, "VIDEO_TS")) or os.path.exists(os.path.join(callback, "video_ts")):
					if callback.endswith("/"):
						callback = callback[:-1]
					cfg.device.value = callback
					self["config"].setList(self["config"].getList())

	def gotInfo(self, result, retval, extra_args):
		cfg.name.value = _("Name of DVD")
		if result:
			lines = result.split("\n")
			for line in lines:
				if line.startswith("DVD-Video information of the DVD with title "):
					idx = line.index("title ")
					name = line[idx+6:]
					name = name.replace('&', '').replace('+', '').replace('*', '').replace('?', '').replace('<', '').replace('>', '').replace('|', '')
					name = name.replace('"', '').replace('.', '').replace('/', '').replace('\\', '').replace('[', '').replace(']', '').replace(':', '').replace(';', '').replace('=', '').replace(',', '')
					if name:
						cfg.name.value = name
					break
		self["config"].setList(self["config"].getList())
		self.working = False

#################################################

def main(session, **kwargs):
	if SESSION is None:
		global SESSION
		SESSION = session
	if dvdbackup.working:
		session.open(DVDBackupProgress)
	else:
		if not fileExists("/usr/bin/dvdbackup"):
			session.open(MessageBox, _("Could not install needed dvdbackup package!"), type=MessageBox.TYPE_INFO, timeout=10)
		else:
			session.open(DVDBackupScreen)

def filescan_open(list, session, **kwargs):
	if SESSION is None:
		global SESSION
		SESSION = session
	if len(list) == 1 and list[0].mimetype == "video/x-dvd":
		file_path = isCDdevice()
		if file_path:
			if dvdbackup.working:
				session.open(MessageBox, _("Warning!\nDVD backup is already running!"), type=MessageBox.TYPE_INFO, timeout=10)
			else:
				name = None
				splitted = list[0].path.split('/')
				if len(splitted) > 2:
					if splitted[1] == 'media':
						name = splitted[2]
				session.open(DVDBackupScreen, device=file_path, foldername=name)
			return

def filescan(**kwargs):
	class LocalScanner(Scanner):
		def checkFile(self, file):
			return fileExists(file.path)
	return [LocalScanner(mimetypes=["video/x-dvd"], paths_to_scan=[ScanPath(path="video_ts", with_subdirs=False), ScanPath(path="VIDEO_TS", with_subdirs=False)], name="DVD", description=_("DVD Backup"), openfnc=filescan_open)]

def Plugins(**kwargs):
	return [PluginDescriptor(name=_("DVD Backup"), description=_("Backup your Video-DVD to your harddisk"), where=PluginDescriptor.WHERE_PLUGINMENU, icon="DVDBackup.png", fnc=main),
		PluginDescriptor(where=PluginDescriptor.WHERE_FILESCAN, fnc=filescan)]
