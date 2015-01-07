import Components.Task
from Screens.MessageBox import MessageBox
from Components.config import config, ConfigSelectionNumber, ConfigSubsection, ConfigYesNo
from enigma import eTimer
from Tools.Directories import fileExists
import os

def EpgCacheLoadCheck(session=None, **kwargs):
	global epgcacheloadcheckpoller
	epgcacheloadcheckpoller = EpgCacheLoadCheckPoller()
	if config.plugins.epgrefresh_extra.cacheloadsched.value:
		epgcacheloadcheckpoller.start()
	else:
		epgcacheloadcheckpoller.stop()

def EpgCacheSaveCheck(session=None, **kwargs):
	global epgcachesavecheckpoller
	epgcachesavecheckpoller = EpgCacheSaveCheckPoller()
	if config.plugins.epgrefresh_extra.cachesavesched.value:
		epgcachesavecheckpoller.start()
	else:
		epgcachesavecheckpoller.stop()

class EpgCacheLoadCheckPoller:
	def __init__(self):
		self.timer = eTimer()

	def start(self):
		print '[EPGC Loads] Poller enabled.'
		if self.epgcacheloadcheck not in self.timer.callback:
			self.timer.callback.append(self.epgcacheloadcheck)
		self.timer.startLongTimer(0)

	def stop(self):
		print '[EPGC Load] Poller disabled.'
		if self.epgcacheloadcheck in self.timer.callback:
			self.timer.callback.remove(self.epgcacheloadcheck)
		self.timer.stop()

	def epgcacheloadcheck(self):
		Components.Task.job_manager.AddJob(self.createLoadCheckJob())

	def createLoadCheckJob(self):
		job = Components.Task.Job(_("EPG Cache Check"))
		if config.plugins.epgrefresh_extra.cacheloadsched.value and not self.SameCheckJob():
			task = Components.Task.PythonTask(job, _("Reloading EPG Cache..."))
			task.work = self.JobEpgCacheLoadPause
			task.weighting = 1
		task = Components.Task.PythonTask(job, _("Adding schedule..."))
		task.work = self.JobSched
		task.weighting = 1
		return job

	def SameCheckJob(self):
		if fileExists("/usr/lib/enigma2/python/Plugins/Extensions/EPGD/plugin.py"):
			try:
				same_options = config.plugins.epgd.autosave.value
			except:
				same_options = False
			if same_options:
				if config.plugins.epgd.autosave.value != "0":
					return True
		return False

	def JobEpgCacheLoadPause(self):
		os.system('[ -e %s ] && echo "Start" ' % config.misc.epgcache_filename.value)
		self.loadTimer = eTimer()
		self.loadTimer.timeout.get().append(self.JobEpgCacheLoad)
		self.loadTimer.start(4000, False)

	def JobEpgCacheLoad(self):
		self.loadTimer.stop()
		print '[EPGC] Refreshing EPGCache.'
		from enigma import eEPGCache
		epgcache = eEPGCache.getInstance()
		epgcache.load()

	def JobSched(self):
		self.timer.startLongTimer(int(config.plugins.epgrefresh_extra.cacheloadtimer.value) * 3600)

class EpgCacheSaveCheckPoller:
	def __init__(self):
		self.timer = eTimer()

	def start(self):
		print '[EPGC Save] Poller enabled.'
		if self.epgcachesavecheck not in self.timer.callback:
			self.timer.callback.append(self.epgcachesavecheck)
		self.timer.startLongTimer(0)

	def stop(self):
		print '[EPGC Save] Poller disabled.'
		if self.epgcachesavecheck in self.timer.callback:
			self.timer.callback.remove(self.epgcachesavecheck)
		self.timer.stop()

	def epgcachesavecheck(self):
		Components.Task.job_manager.AddJob(self.createSaveCheckJob())

	def createSaveCheckJob(self):
		job = Components.Task.Job(_("EPG Cache Check"))
		if config.plugins.epgrefresh_extra.cachesavesched.value and not self.SamecheckJob():
			task = Components.Task.PythonTask(job, _("Saving EPG Cache..."))
			task.work = self.JobEpgCacheSavePause
			task.weighting = 1
		task = Components.Task.PythonTask(job, _("Adding schedule..."))
		task.work = self.JobSched
		task.weighting = 1
		return job

	def SamecheckJob(self):
		if fileExists("/usr/lib/enigma2/python/Plugins/Extensions/EPGD/plugin.py"):
			try:
				same_options = config.plugins.epgd.autosave.value
			except:
				same_options = False
			if same_options:
				if config.plugins.epgd.autosave.value != "0":
					return True
		return False

	def JobEpgCacheSavePause(self):
		os.system('[ -e %s ] && echo "Start" ' % config.misc.epgcache_filename.value)
		self.saveTimer = eTimer()
		self.saveTimer.timeout.get().append(self.JobEpgCacheSave)
		self.saveTimer.start(4000, False)
				
	def JobEpgCacheSave(self):
		self.saveTimer.stop()
		print '[EPGC] Saving EPGCache.'
		from enigma import eEPGCache
		epgcache = eEPGCache.getInstance()
		epgcache.save()
		if config.plugins.epgrefresh_extra.save_backup.value and config.plugins.epgrefresh_extra.epgcachepath.value != "/etc/enigma2/":
			restore_backup = config.misc.epgcache_filename.value + ".backup"
			if os.path.exists(config.misc.epgcache_filename.value):
				try:
					os.system("cp -f %s %s" % (config.misc.epgcache_filename.value, restore_backup))
					os.chmod("%s" % (restore_backup), 0644)
				except:
					pass


	def JobSched(self):
		self.timer.startLongTimer(int(config.plugins.epgrefresh_extra.cachesavetimer.value) * 3600)

class EpgSaveMsg(MessageBox):
	def __init__(self, session):
		MessageBox.__init__(self, session, _("Are you sure you want to save the EPG Cache to:\n") + config.misc.epgcache_filename.getValue(), MessageBox.TYPE_YESNO)
		self.skinName = "MessageBox"

class EpgLoadMsg(MessageBox):
	def __init__(self, session):
		MessageBox.__init__(self, session, _("Are you sure you want to reload the EPG data from:\n") + config.misc.epgcache_filename.getValue(), MessageBox.TYPE_YESNO)
		self.skinName = "MessageBox"
