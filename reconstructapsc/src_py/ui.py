from . import _
from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from enigma import eServiceCenter
from Components import Task
from Tools.Directories import fileExists
from Screens.MovieSelection import playlist

class ReconstructApSc(ChoiceBox):
	def __init__(self, session, service):
		self.serviceHandler = eServiceCenter.getInstance()
		offline = self.serviceHandler.offlineOperations(service)
		path = service.getPath()
		name = self.getName(service, path)

		if offline is None:
			tlist = [(_("Cannot reconstruct this item"),  "CALLFUNC", self.confirmed0),]
		else:
			tlist = [(_("Don't reconstruct"), "CALLFUNC", self.confirmed0),]
			tnext = [
				(_("Reconstruct missing .ap and .sc files in this directory"), "CALLFUNC", self.confirmed2),
				(_("Reconstruct all .ap and .sc files in this directory"), "CALLFUNC", self.confirmed3),
			]
			if not path.endswith('.ts'):
				tlist += tnext
				name = _("more files...")
			else:
				tlist.append((_("Reconstruct the .ap and .sc files of the selected movie"), "CALLFUNC", self.confirmed1, service, path))
				tlist += tnext

		ChoiceBox.__init__(self, session, _("What would you like to reconstruct?  (\"%s\")") % (name), list = tlist, selection = 0)
		self.skinName = "ChoiceBox"

	def confirmed0(self, arg):
		self.close()

	def confirmed1(self, arg):
		self.addToTask(arg[3], arg[4])
		self.close()

	def confirmed2(self, arg):
		for service in playlist:
			path = service.getPath()
			if path.endswith('.ts'):
				if arg == "reconstructallfiles" or not fileExists(path+'.ap') or not fileExists(path+'.sc'):
					self.addToTask(service, path)
		self.close()

	def confirmed3(self, arg):
		self.confirmed2("reconstructallfiles")

	def addToTask(self, service, path):
		name = self.getName(service, path)
		offline = self.serviceHandler.offlineOperations(service)
		if offline is None:
			print "[Reconstruct AP/SC] Cannot reconstruct", name
			return
		text = _("Reconstruct AP/SC - %s") % name
		job = Task.Job(text)
		task = Task.PythonTask(job, text)
		task.work = offline.reindex
		Task.job_manager.AddJob(job)

	def getName(self, service, path):
		info = self.serviceHandler.info(service)
		if not info:
			return path
		return info.getName(service)
