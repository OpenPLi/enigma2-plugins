# -*- coding: UTF-8 -*-
# for localized messages
from . import _

from Plugins.Plugin import PluginDescriptor
from enigma import ePicLoad, eServiceReference, eServiceCenter
from Screens.Screen import Screen
from Screens.HelpMenu import HelpableScreen
from Screens.EpgSelection import EPGSelection
from Screens.ChannelSelection import SimpleChannelSelection
from Screens.ChoiceBox import ChoiceBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.Button import Button
from Components.AVSwitch import AVSwitch
from Components.MenuList import MenuList
from Components.Language import language
from Components.ProgressBar import ProgressBar
from Components.Sources.StaticText import StaticText
from Components.Sources.Boolean import Boolean
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS, SCOPE_SKIN_IMAGE

from io import StringIO

import contextlib
import gzip
import os
import random
import re
import threading
import urllib
import zlib


try:
	import htmlentitydefs
	from urllib import quote_plus
	iteritems = lambda d: d.iteritems()
except ImportError as ie:
	from html import entities as htmlentitydefs
	from urllib.parse import quote_plus
	iteritems = lambda d: d.items()
	unichr = chr

import gettext

# Configuration
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigYesNo, ConfigText
from Components.ConfigList import ConfigListScreen
from Components.PluginComponent import plugins
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

from html.parser import HTMLParser


def transHTML(text):
	h = HTMLParser()
	return h.unescape(text)


config.plugins.imdb = ConfigSubsection()
config.plugins.imdb.showinplugins = ConfigYesNo(default=False)
config.plugins.imdb.showsetupinplugins = ConfigYesNo(default=True)
config.plugins.imdb.showinmovielist = ConfigYesNo(default=True)
config.plugins.imdb.force_english = ConfigYesNo(default=False)
config.plugins.imdb.ignore_tags = ConfigText(visible_width=50, fixed_size=False)
config.plugins.imdb.showlongmenuinfo = ConfigYesNo(default=False)
config.plugins.imdb.showepisodeinfo = ConfigYesNo(default=False)


def quoteEventName(eventName):
	# BBC uses '\x86' markers in program names, remove them
	try:
		text = eventName.decode('utf8').replace(u'\x86', u'').replace(u'\x87', u'').encode('utf8')
	except:
		text = eventName
	return quote_plus(text)


class Downloader(object):

	successCallback = None
	failureCallback = None
	downloadTimeout = 10  # seconds

	_headers = {
		'user-agent': 'curl/7.74.0',
		'accept': '*/*'
	}

	def __init__(self, url, file, headers=None):
		self.url = url
		self.file = file
		if headers is not None:
			self._headers = headers

	def addSuccessCallback(self, successCallback):
		self.successCallback = successCallback
		return self

	def addFailureCallback(self, failureCallback):
		self.failureCallback = failureCallback
		return self

	def start(self):
		t = threading.Thread(target=self._download)
		t.start()
		return t

	def _download(self):
		tmpfile = self.file + '.' + str(random.randint(10000, 99999)) + '.tmp'
		try:
			request = urllib.request.Request(self.url, None, self._headers)
			with open(tmpfile, 'wb') as o, contextlib.closing(urllib.request.urlopen(request, timeout=self.downloadTimeout)) as i:
				encoding = i.info().get('Content-Encoding')
				if encoding == 'gzip':
					buf = StringIO(i.read())
					f = gzip.GzipFile(fileobj=buf)
					data = f.read()
				elif encoding == 'deflate':
					data = zlib.decompress(i.read())
				else:
					data = i.read()
				o.write(data)
			os.rename(tmpfile, self.file)
			if self.successCallback:
				self.successCallback('')
		except urllib.error.URLError as e:
			if fileExists(tmpfile):
				os.remove(tmpfile)
			if self.failureCallback:
				self.failureCallback(e)


class IMDBChannelSelection(SimpleChannelSelection):
	def __init__(self, session):
		SimpleChannelSelection.__init__(self, session, _("Channel Selection"))
		self.skinName = "SimpleChannelSelection"

		self["ChannelSelectEPGActions"] = ActionMap(["ChannelSelectEPGActions"],
			{
				"showEPGList": self.channelSelected
			}
		)

	def channelSelected(self):
		ref = self.getCurrentSelection()
		if (ref.flags & 7) == 7:
			self.enterPath(ref)
		elif not (ref.flags & eServiceReference.isMarker):
			info = eServiceCenter.getInstance().info(ref)
			evt = info and info.getEvent(ref, -1)
			event_id = evt and evt.getEventId() or None
			self.session.openWithCallback(
				self.epgClosed,
				IMDBEPGSelection,
				ref,
				eventid=event_id,
				openPlugin=False
			)

	def epgClosed(self, ret=None):
		if ret:
			self.close(ret)


class IMDBEPGSelection(EPGSelection):
	def __init__(self, session, ref, eventid=None, openPlugin=True):
		EPGSelection.__init__(self, session, ref.toString(), eventid=eventid)
		self.skinName = "EPGSelection"
		self["key_green"].setText(_("Lookup"))
		self.openPlugin = openPlugin

	def infoKeyPressed(self):
		self.greenButtonPressed()

	def timerAdd(self):
		self.greenButtonPressed()

	def greenButtonPressed(self):
		self.closeEventViewDialog()
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if not InfoBarInstance.LongButtonPressed:
			cur = self["list"].getCurrent()
			evt = cur[0]
			sref = cur[1]
			if not evt:
				return

			if self.openPlugin:
				self.session.open(
					IMDB,
					evt.getEventName()
				)
			else:
				self.close(evt.getEventName())

	def onSelectionChanged(self):
		super(IMDBEPGSelection, self).onSelectionChanged()
		self["key_green"].setText(_("Lookup"))


class IMDB(Screen, HelpableScreen):
	skin = """
		<screen name="IMDB" position="center,center" size="600,420" title="Internet Movie Database Details Plugin" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/key_menu.png" position="565,5" zPosition="0" size="35,25" alphatest="on" />
			<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="key_yellow" position="280,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#a08500" transparent="1" />
			<widget name="key_blue" position="420,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#18188b" transparent="1" />
			<widget source="title" render="Label" position="10,40" size="330,45" valign="center" font="Regular;22"/>
			<widget name="detailslabel" position="105,90" size="485,140" font="Regular;18" />
			<widget name="castlabel" position="10,235" size="580,155" font="Regular;18" />
			<widget name="extralabel" position="10,40" size="580,350" font="Regular;18" />
			<widget name="ratinglabel" position="340,62" size="250,20" halign="left" font="Regular;18" foregroundColor="#f0b400"/>
			<widget name="statusbar" position="10,395" size="580,20" font="Regular;18" foregroundColor="#cccccc" />
			<widget name="poster" position="4,90" size="96,140" alphatest="on" />
			<widget name="menu" position="10,115" size="580,275" itemHeight = "35" zPosition="3" scrollbarMode="showOnDemand" />
			<widget name="starsbg" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/IMDb/starsbar_empty.png" position="340,40" zPosition="0" size="210,21" transparent="1" alphatest="on" />
			<widget name="stars" position="340,40" size="210,21" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/IMDb/starsbar_filled.png" transparent="1" />
		</screen>"""

	# Some HTML entities as utf-8
	NBSP = unichr(htmlentitydefs.name2codepoint['nbsp'])
	RAQUO = unichr(htmlentitydefs.name2codepoint['raquo'])
	HELLIP = unichr(htmlentitydefs.name2codepoint['hellip'])

	mainDownloaded = 1 << 0
	storylineDownloaded = 1 << 1
	allDownloaded = mainDownloaded | storylineDownloaded
	downloadedLock = threading.Lock()

	def __init__(self, session, eventName, callbackNeeded=False, save=False, savepath=None, localpath=None):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)

		for tag in config.plugins.imdb.ignore_tags.getValue().split(','):
			eventName = eventName.replace(tag, '')

		eventName = ' '.join(eventName.split()).strip()

		self.eventName = eventName

		self.callbackNeeded = callbackNeeded
		self.callbackData = ""
		self.callbackGenre = ""

		self.saving = save
		self.savingpath = savepath
		self.localpath = localpath
		self.fetchurl = None

		self.dictionary_init()

		self["poster"] = Pixmap()
		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.paintPosterPixmapCB)

		self["stars"] = ProgressBar()
		self["starsbg"] = Pixmap()
		self["stars"].hide()
		self["starsbg"].hide()
		self.ratingstars = -1

		self["title"] = StaticText(_("The Internet Movie Database"))
		# map new source -> old component

		def setText(txt):
			StaticText.setText(self["title"], txt)
			self["titellabel"].setText(txt)
		self["title"].setText = setText
		self["titellabel"] = Label()
		self["detailslabel"] = ScrollLabel("")
		self["castlabel"] = ScrollLabel("")
		self["extralabel"] = ScrollLabel("")
		self["statusbar"] = Label("")
		self["ratinglabel"] = Label("")
		self.resultlist = []
		self["menu"] = MenuList(self.resultlist)
		self["menu"].hide()

		self["key_red"] = Button(_("Exit"))
		self["key_green"] = Button("")
		self["key_yellow"] = Button("")
		self["key_blue"] = Button("")

		# 0 = multiple query selection menu page
		# 1 = movie info page
		# 2 = extra infos page
		self.Page = 0

		self["actionsOk"] = HelpableActionMap(self, "OkCancelActions",
		{
			"ok": (self.showDetails, _("Show movie and series basic details")),
			"cancel": (self.exit, _("Exit IMDb search")),
		}, -1)
		self["actionsColor"] = HelpableActionMap(self, "ColorActions",
		{
			"red": (self.exit, _("Exit IMDb search")),
			"green": (self.showMenu, _("Show list of matched movies an series")),
			"yellow": (self.showDetails, _("Show movie and series basic details")),
			"blue": (self.showExtras, _("Show movie and series extra details")),
		}, -1)
		self["actionsMovieSel"] = HelpableActionMap(self, "MovieSelectionActions",
		{
			"contextMenu": (self.contextMenuPressed, _("Menu")),
			"showEventInfo": (self.showDetails, _("Show movie and series basic details")),
		}, -1)
		self["actionsDir"] = HelpableActionMap(self, "DirectionActions",
		{
			"down": (self.pageDown, _("Page down")),
			"up": (self.pageUp, _("Page up")),
		}, -1)

		self.getIMDB()

		if self.localpath is not None:                                # otherwise the stars are not correctly shown if we call details directly
			self.onLayoutFinish.append(self._layoutFinished)

	def _layoutFinished(self):
		self["menu"].hide()
		self["extralabel"].hide()
		self["stars"].setValue(self.ratingstars)

	def exit(self):
		if fileExists("/tmp/poster.jpg"):
			os.remove("/tmp/poster.jpg")
		if fileExists("/tmp/imdbquery.html"):
			os.remove("/tmp/imdbquery.html")
		if fileExists("/tmp/imdbquery2.html"):
			os.remove("/tmp/imdbquery2.html")
		if fileExists("/tmp/imdbquery-storyline.html"):
			os.remove("/tmp/imdbquery-storyline.html")
		if self.callbackNeeded:
			self.close([self.callbackData, self.callbackGenre])
		else:
			self.close()

	def dictionary_init(self):
		syslang = language.getLanguage()
		if 1: #"de" not in syslang or config.plugins.imdb.force_english.value is True:
			self.generalinfomask = re.compile(
			'block__title.*?>(?P<title>.*?)</h1>'
			'(?:.*?<span.*?>(?P<g_director>Regisseur|Directors?)</span>.*?<ul.*?>(?P<director>.*?)</ul>)?'
			'(?:.*?<span.*?>(?P<g_creator>Sch\S*?pfer|Creators?)</span>.*?<ul.*?>(?P<creator>.*?)</ul>)?'
			'(?:.*?<span.*?>(?P<g_writer>Drehbuch|Writers?)</span>.*?<div.*?<ul.*?>(?P<writer>.*?)</ul>)?'
			'(?:.*?<label.*?for="browse-episodes-season".*?>.*?(?P<g_seasons>seasons?)</label>.*?<select.*?browse-episodes-season.*?>(?P<seasons>.*?)</select)?'
			'(?:.*?<a.*?>(?P<g_premiere>Premiere|Release date)</a>.*?<div.*?<ul.*?>(?P<premiere>.*?)</ul>)?'
			'(?:.*?<span.*?>(?P<g_country>Land|Countr.*?of origin)</span>.*?<div.*?<ul.*?>(?P<country>.*?)</ul>)?'
			'(?:.*?<a.*?>(?P<g_alternativ>Auch bekannt als|Also known as)</a>.*?<div.*?<ul.*?>(?P<alternativ>.*?)</ul>)?', re.DOTALL)

			self.awardsmask = re.compile('<li.*?data-testid="award_information".*?><a.*?>(?P<awards>.+?)</span></li>', re.DOTALL)

			self.extrainfomask = re.compile(
			'(?:.*?data-testid="plot-xl".*?>(?P<outline>.+?)</span)?'
			#'(?:.*?<h3 class="ipc-title__text">(?P<g_synopsis>Storyline)</h3>.*?<div class="ipc-html-content-inner-div">(?P<synopsis>.+?)</div)?'
			#'(?:.*?data-testid="storyline-plot-keywords">(?P<keywords>.+?)\d+\s+(?:mehr|more).*?</div>)?'
			'(?:.*?<a.*?>(?P<g_tagline>Werbezeile|Taglines?)</a>.*?<li.*?<span.*?>(?P<tagline>.+?)<)?'
			'(?:.*?<a.*?>(?P<g_cert>Altersfreigabe|Certificate|Motion Picture Rating \(MPAA\))</a>.*?<div.*?<ul.*?<li.*?<span.*?>(?P<cert>.*?)</span>)?'
			'(?:.*?<a.*?>(?P<g_trivia>Dies und das|Trivia)</a><div.*?<div.*?<div.*?<div.*?>(?P<trivia>.+?)</div>)?'
			'(?:.*?<a.*?>(?P<g_goofs>Pannen|Goofs)</a><div.*?<div.*?<div.*?<div.*?>(?P<goofs>.+?)</div>)?'
			'(?:.*?<a.*?>(?P<g_quotes>Dialogzitate|Quotes)</a><div.*?<div.*?<div.*?<div.*?>(?P<quotes>.+?)</div>)?'
			'(?:.*?<a.*?>(?P<g_connections>Bez\S*?ge zu anderen Titeln|Connections)</a><div.*?<div.*?<div.*?<div.*?>(?P<connections>.+?)</div>)?'
			'(?:.*?<h3.*?>(?P<g_comments>Nutzerkommentare|User reviews).*?</h3>(?:.*?</svg>(?P<g_rating>[0-9]+?)<span class="ipc-rating-star--maxRating">/.*?(?P<g_maxrating>[0-9]+?)</span>)?.*?<span.*?review-summary.*?>(?P<commenttitle>.*?)</span>.*?<div class="ipc-html-content-inner-div">(?P<comment>.+?)</div>.*?<a.*?"author-link">(?P<commenter>.+?)</a>)?' # no match, slow
			'(?:.*?<span.*?>(?P<g_language>Sprachen?|Languages?)</span>.*?<div.*?<ul.*?>(?P<language>.*?)</ul>)?'
			'(?:.*?<a.*?>(?P<g_locations>Drehorte?|Filming locations?)</a>.*?<div.*?<ul.*?>(?P<locations>.*?)</ul>)?'
			'(?:.*?<a.*?>(?P<g_company>Firm\S*?|Production compan.*?)</a>.*?<div.*?<ul.*?>(?P<company>.*?)</ul>)?'
			'(?:.*?<span.*?>(?P<g_runtime>L\S*?nge|Runtime)</span>.*?<div.*?>(?P<runtime>.*?)</div>)?'
			'(?:.*?<span.*?>(?P<g_color>Farbe|Color)</span>.*?<a.*?>(?P<color>.*?)</a>)?'
			'(?:.*?<span.*?>(?P<g_sound>Tonverfahren|Sound mix)</span>.*?<div.*?<ul.*?>(?P<sound>.*?)</ul>)?'
			'(?:.*?<span.*?>(?P<g_aspect>Seitenverh\S*?ltnis|Aspect ratio)</span>.*?<div.*?<ul.*?<li.*?<span.*?>(?P<aspect>.*?)</span>)?', re.DOTALL)

			self.storylinemask = re.compile('id="plot-summaries-content".*?<p>(.*?<div class="author-container">.*?)</div>', re.DOTALL)
			self.storylinealtmask = re.compile('id="plot-summaries-content".*?<p>(.*?)</p>', re.DOTALL)
			self.genreblockmask = re.compile('<div.*?data-testid="genres".*?>(?:<div.*?<svg.*?</svg></div>)?(.*?)</div>', re.DOTALL)
			self.ratingmask = re.compile('aggregate-rating__score.*?><span.*?>(?P<rating>.*?)</span>', re.DOTALL)
			self.castmask = re.compile('<a.*?title-cast-item__actor.*?>(?P<actor>.*?)</a>.*?cast-item-characters-link.*?><span.*?>(?P<character>.*?)</span>(?:.*?<span><span.*?>(?P<episodes>.*?)</span></span>)?', re.DOTALL)
			self.postermask = re.compile('<div.*?ipc-media--poster.*?<img.*?ipc-image.*?src="(http.*?)"', re.DOTALL)

		self.htmltags = re.compile('<.*?>', re.DOTALL)
		self.allhtmltags = re.compile('<.*>', re.DOTALL)

	def resetLabels(self):
		self["detailslabel"].setText("")
		self["ratinglabel"].setText("")
		self["title"].setText("")
		self["castlabel"].setText("")
		self["titellabel"].setText("")
		self["extralabel"].setText("")
		self.ratingstars = -1

	def pageUp(self):
		if self.Page == 0:
			self["menu"].instance.moveSelection(self["menu"].instance.moveUp)
		if self.Page == 1:
			self["castlabel"].pageUp()
			self["detailslabel"].pageUp()
		if self.Page == 2:
			self["extralabel"].pageUp()

	def pageDown(self):
		if self.Page == 0:
			self["menu"].instance.moveSelection(self["menu"].instance.moveDown)
		if self.Page == 1:
			self["castlabel"].pageDown()
			self["detailslabel"].pageDown()
		if self.Page == 2:
			self["extralabel"].pageDown()

	def showMenu(self):
		if (self.Page == 1 or self.Page == 2) and self.resultlist:
			self["menu"].show()
			self["stars"].hide()
			self["starsbg"].hide()
			self["ratinglabel"].hide()
			self["castlabel"].hide()
			self["poster"].hide()
			self["extralabel"].hide()
			self["title"].setText(_("Ambiguous results"))
			self["detailslabel"].setText(_("Please select the matching entry"))
			self["detailslabel"].show()
			self["key_blue"].setText("")
			self["key_green"].setText(_("Title Menu"))
			self["key_yellow"].setText(_("Details"))
			self.Page = 0

	def getLocalDetails(self):
		localfile = self.localpath
		self.inhtml = self.html2utf8(open(localfile, "r").read())
		self.generalinfos = self.generalinfomask.search(self.inhtml)
		self.IMDBparse()
		if self.ratingstars > 0:
			self["starsbg"].show()
			self["stars"].show()
		self.Page = 1

	def showDetails(self):
		self["ratinglabel"].show()
		self["castlabel"].show()
		self["detailslabel"].show()

		if self.resultlist and self.Page == 0:
			link = self["menu"].getCurrent()[1]
			title = self["menu"].getCurrent()[0]
			self["statusbar"].setText(_("Re-Query IMDb: %s...") % (title))
			localfile = "/tmp/imdbquery2.html"
			fetchurl = "https://www.imdb.com/title/" + link + "/"
			print("[IMDB] showDetails() downloading query " + fetchurl + " to " + localfile)
			localfile2 = "/tmp/imdbquery-storyline.html"
			fetchurl2 = "https://www.imdb.com/title/" + link + "/plotsummary"
			print("[IMDB] showDetails() downloading query " + fetchurl2 + " to " + localfile2)
			with self.downloadedLock:
				self.downloaded = 0
			Downloader(fetchurl, localfile).addSuccessCallback(self.IMDBmainDownloaded).addFailureCallback(self.http_failed).start()
			Downloader(fetchurl2, localfile2).addSuccessCallback(self.IMDBstorylineDownloaded).addFailureCallback(self.http_failed).start()
			self.fetchurl = fetchurl
			self["menu"].hide()
			self.resetLabels()
			self.Page = 1

		if self.Page == 2:
			self["extralabel"].hide()
			self["poster"].show()
			if self.ratingstars > 0:
				self["starsbg"].show()
				self["stars"].show()
				self["stars"].setValue(self.ratingstars)

			self.Page = 1

	def showExtras(self):
		if self.Page == 1:
			self["extralabel"].show()
			self["detailslabel"].hide()
			self["castlabel"].hide()
			self["poster"].hide()
			self.Page = 2

	def contextMenuPressed(self):
		list = [
			(_("Enter search"), self.openVirtualKeyBoard),
			(_("Select from EPG"), self.openChannelSelection),
			(_("Setup"), self.setup),
		]

		if self.saving:
			if self.savingpath is not None:
				# TODO: save Poster also as option for .html
				list.extend((
					(_("Save current Details as .html for offline use"), self.saveHtmlDetails),
					(_("Save current Details as .txt"), self.saveTxtDetails),
					(_("Save current Poster and Details as .txt"), self.savePosterTxtDetails),
				))

		if fileExists(resolveFilename(SCOPE_PLUGINS, "Extensions/YTTrailer/plugin.py")):
			list.extend((
				(_("Play Trailer"), self.openYttrailer),
				(_("Search Trailer"), self.searchYttrailer),
			))

		self.session.openWithCallback(
			self.menuCallback,
			ChoiceBox,
			title=_("IMDb Menu"),
			list=list,
		)

	def menuCallback(self, ret=None):
		ret and ret[1]()

	def saveHtmlDetails(self):
		try:
			if self.savingpath is not None:
				isave = self.savingpath + ".imdbquery2.html"
				if self.fetchurl is not None:
					Downloader(self.fetchurl, isave).addSuccessCallback(self.IMDBsave).addFailureCallback(self.http_failed).start()
		except Exception as e:
			print('[IMDb] saveHtmlDetails exception failure: ', str(e))

	def saveTxtDetails(self):
		try:
			if self.savingpath is not None:
				getTXT = self.IMDBsavetxt()
				if getTXT is not None:
					file(self.savingpath + ".txt", 'w').write(getTXT)
				else:
					from Screens.MessageBox import MessageBox
					self.session.open(MessageBox, (_('IMDb can not get Movie Information to write to .txt file!')), MessageBox.TYPE_INFO, 10)
		except Exception as e:
			print('[IMDb] saveTxtDetails exception failure: ', str(e))

	def savePosterTxtDetails(self):
		try:
			if self.savingpath is not None:
				getTXT = self.IMDBsavetxt(True)
				if getTXT is not None:
					file(self.savingpath + ".txt", 'w').write(getTXT)
				else:
					from Screens.MessageBox import MessageBox
					self.session.open(MessageBox, (_('IMDb can not get Movie Information to write to .jpg and .txt files!')), MessageBox.TYPE_INFO, 10)
		except Exception as e:
			print('[IMDb] savePosterTxtDetails exception failure: ', str(e))

	def IMDBsave(self, string):
		self["statusbar"].setText(_("IMDb Save - Download completed"))
		self.inhtml = self.html2utf8(open("/tmp/imdbquery2.html", "r").read())
		self.generalinfos = self.generalinfomask.search(self.inhtml)
		self.IMDBparse()

	def IMDBsavetxt(self, poster=False):
		overview = ""
		runtime = ""
		genre = ""
		country = ""
		release = ""
		rating = ""

		if self.generalinfos:
			extrainfos = self.extrainfomask.search(self.inhtml)
			if extrainfos:
				# get entry 1 = Overview(details)
				try:
					text = ' '.join(self.htmltags.sub('', extrainfos.group("synopsis").replace("\n", ' ').replace("<br>", '\n').replace("<br />", '\n')).replace(' |' + self.NBSP, '').replace(self.NBSP, ' ').split()) + "\n"
					overview = _("Content:") + " " + text
				except Exception as e:
					print('[IMDb] IMDBsavetxt exception failure in get overview: ', str(e))
					overview = (_("Content:"))
#				print('[IMDb] IMDBsavetxt overview: ', overview)

				# get entry 2 = Runtime
				try:
					time = ' '.join(self.htmltags.sub('', extrainfos.group(category).replace("\n", ' ').replace("<br>", '\n').replace("<br />", '\n')).replace(' |' + self.NBSP, '').replace(self.NBSP, ' ').split())
					runtime = _("Runtime:") + " " + time
				except Exception as e:
					print('[IMDb] IMDBsavetxt exception failure in get runtime: ', str(e))
					runtime = (_("Runtime:"))
#				print('[IMDb] IMDBsavetxt runtime: ', runtime)

			# get entry 3 = Genre
			genreblock = self.genreblockmask.search(self.inhtml)
			if genreblock:
				genres = ' | '.join(re.split('\|+', self.htmltags.sub('|', genreblock.group(1)).strip('|').replace(self.NBSP, ' ')))
				if genres:
					genre = _("Genre:") + " " + genres
			else:
				genre = (_("Genre:"))
#			print('[IMDb] IMDBsavetxt genre: ', genre)

			# get entry 4 = Country
			try:
				land = ' '.join(self.htmltags.sub('', self.generalinfos.group("country").replace('\n', ' ')).split())
				country = _("Production Countries:") + " " + land
			except Exception as e:
				print('[IMDb] IMDBsavetxt exception failure in get country: ', str(e))
				country = (_("Production Countries:"))
#			print('[IMDb] IMDBsavetxt country: ', country)

			# get entry 5 = ReleaseDate
			try:
				date = ' '.join(self.htmltags.sub('', self.generalinfos.group("premiere").replace('\n', ' ')).split())
				release = _("Release Date:") + " " + date
			except Exception as e:
				print('[IMDb] IMDBsavetxt exception failure in get release: ', str(e))
				release = (_("Release Date:"))
#			print('[IMDb] IMDBsavetxt release: ', release)

			# get entry 5 = Vote
			ratingtext = self.ratingmask.search(self.inhtml)
			if ratingtext:
				ratingtext = ratingtext.group("rating")
				if ratingtext != '<span id="voteuser"></span>':
					text = ratingtext                                # + " / 10"
					rating = _("User Rating") + ": " + text
			else:
				rating = (_("User Rating") + ": ")
#			print('[IMDb] IMDBsavetxt rating: ', rating)

			# get the poster.jpg
			if poster:
				try:
					posterurl = self.postermask.search(self.inhtml)
					if posterurl and posterurl.group(1).find("jpg") > 0:
						posterurl = posterurl.group(1)
						postersave = self.savingpath + ".poster.jpg"
						print("[IMDB] downloading poster " + posterurl + " to " + postersave)
						Downloader(posterurl, postersave).addFailureCallback(self.http_failed).start()
				except Exception as e:
					print('[IMDb] IMDBsavetxt exception failure in get poster: ', str(e))

		return overview + "\n\n" + runtime + "\n" + genre + "\n" + country + "\n" + release + "\n" + rating + "\n"

	def openYttrailer(self):
		try:
			from Plugins.Extensions.YTTrailer.plugin import YTTrailer, baseEPGSelection__init__
		except ImportError as ie:
			pass
		if baseEPGSelection__init__ is None:
			return

		ytTrailer = YTTrailer(self.session)
		ytTrailer.showTrailer(self.eventName)

	def searchYttrailer(self):
		try:
			from Plugins.Extensions.YTTrailer.plugin import YTTrailerList, baseEPGSelection__init__
		except ImportError as ie:
			pass
		if baseEPGSelection__init__ is None:
			return

		self.session.open(YTTrailerList, self.eventName)

	def openVirtualKeyBoard(self):
		self.session.openWithCallback(
			self.gotSearchString,
			VirtualKeyBoard,
			title=_("Enter text to search for"),
			text=self.eventName
		)

	def openChannelSelection(self):
		self.session.openWithCallback(
			self.gotSearchString,
			IMDBChannelSelection
		)

	def gotSearchString(self, ret=None):
		if ret:
			self.eventName = ret
			self.Page = 0
			self.resultlist = []
			self["menu"].hide()
			self["ratinglabel"].show()
			self["castlabel"].show()
			self["detailslabel"].show()
			self["poster"].hide()
			self["stars"].hide()
			self["starsbg"].hide()
			self.getIMDB(search=True)

	def getIMDB(self, search=False):
		self.resetLabels()
		if not isinstance(self.eventName, str):
			self["statusbar"].setText("")
			return
		if not self.eventName:
			s = self.session.nav.getCurrentService()
			info = s and s.info()
			event = info and info.getEvent(0) # 0 = now, 1 = next
			if event:
				self.eventName = event.getEventName()
			else:
				self.eventName = self.session.nav.getCurrentlyPlayingServiceReference().toString()
				self.eventName = self.eventName.split('/')
				self.eventName = self.eventName[-1]
				self.eventName = self.eventName.replace('.', ' ')
				self.eventName = self.eventName.split('-')
				self.eventName = self.eventName[0]
				if self.eventName.endswith(' '):
					self.eventName = self.eventName[:-1]

		if self.localpath is not None and not search:
			if os.path.exists(self.localpath):
				self.getLocalDetails()

		else:
			if self.eventName:
				self["statusbar"].setText(_("Query IMDb: %s") % (self.eventName))
				localfile = "/tmp/imdbquery.html"
				fetchurl = "https://www.imdb.com/find?s=tt&q=" + quoteEventName(self.eventName)
				print("[IMDB] getIMDB() Downloading Query " + fetchurl + " to " + localfile)
				Downloader(fetchurl, localfile).addSuccessCallback(self.IMDBquery).addFailureCallback(self.http_failed).start()

			else:
				self["statusbar"].setText(_("Could't get event name"))

	def html2utf8(self, in_html):
		in_html = (re.subn(r'<(script).*?</\1>(?s)', '', in_html)[0])
		in_html = (re.subn(r'<(style).*?</\1>(?s)', '', in_html)[0])
		entitydict = {}

		entities = re.finditer('&([:_A-Za-z][:_\-.A-Za-z"0-9]*);', in_html)
		for x in entities:
			key = x.group(0)
			if x.group(1) != 'lt' and x.group(1) != 'gt' and key not in entitydict:
				entitydict[key] = htmlentitydefs.name2codepoint[x.group(1)]

		entities = re.finditer('&#x([0-9A-Fa-f]+);', in_html)
		for x in entities:
			key = x.group(0)
			if key not in entitydict:
				entitydict[key] = "%d" % int(x.group(1), 16)

		entities = re.finditer('&#(\d+);', in_html)
		for x in entities:
			key = x.group(0)
			if key not in entitydict:
				entitydict[key] = x.group(1)

		for key, codepoint in iteritems(entitydict):
			in_html = in_html.replace(key, unichr(int(codepoint)))
		return in_html

	def IMDBquery(self, string):
		self["statusbar"].setText(_("IMDb Download completed"))

		self.inhtml = self.html2utf8(open("/tmp/imdbquery.html", "r").read())

		self.generalinfos = self.generalinfomask.search(self.inhtml)

		if self.generalinfos:
			self.IMDBparse()
		else:
			if re.search("<title>Find - IMDb</title>", self.inhtml):
				pos = self.inhtml.find('<table class="findList">')
				pos2 = self.inhtml.find("</table>", pos)
				findlist = self.inhtml[pos:pos2]
				searchresultmask = re.compile('<tr class="findResult (?:odd|even)">.*?<td class="result_text"> (<a href="/title/(tt\d{7,7})/.*?"\s?>(.*?)</a>.*?)</td>', re.DOTALL)
				searchresults = searchresultmask.finditer(findlist)
				titlegroup = 1 if config.plugins.imdb.showlongmenuinfo.value else 3
				self.resultlist = [(' '.join(self.htmltags.sub('', x.group(titlegroup)).replace(self.NBSP, " ").split()), x.group(2)) for x in searchresults]
				Len = len(self.resultlist)
				self["menu"].l.setList(self.resultlist)
				if Len == 1:
					self["statusbar"].setText(_("Re-Query IMDb: %s...") % (self.resultlist[0][0],))
					self.eventName = self.resultlist[0][1]
					localfile = "/tmp/imdbquery2.html"
					fetchurl = "https://www.imdb.com/title/" + quoteEventName(self.eventName) + "/"
					localfile2 = "/tmp/imdbquery-storyline.html"
					fetchurl2 = "https://www.imdb.com/title/" + quoteEventName(self.eventName) + "/plotsummary"
					with self.downloadedLock:
						self.downloaded = 0
					Downloader(fetchurl, localfile).addSuccessCallback(self.IMDBmainDownloaded).addFailureCallback(self.http_failed).start()
					Downloader(fetchurl2, localfile2).addSuccessCallback(self.IMDBstorylineDownloaded).addFailureCallback(self.http_failed).start()
				elif Len > 1:
					self.Page = 1
					self.showMenu()
				else:
					self["detailslabel"].setText(_("No IMDb match."))
					self["statusbar"].setText(_("No IMDb match:") + ' ' + self.eventName)
			else:
				splitpos = self.eventName.find('(')
				if splitpos > 0 and self.eventName.endswith(')'):
					self.eventName = self.eventName[splitpos + 1:-1]
					self["statusbar"].setText(_("Re-Query IMDb: %s...") % (self.eventName))
					# event_quoted = quoteEventName(self.eventName)
					localfile = "/tmp/imdbquery.html"
					fetchurl = "https://www.imdb.com/find?s=tt&q=" + quoteEventName(self.eventName)
					Downloader(fetchurl, localfile).addSuccessCallback(self.IMDBquery).addFailureCallback(self.http_failed).start()
				else:
					self["detailslabel"].setText(_("IMDb query failed!"))

	def http_failed(self, error_instance=None):
		text = _("IMDb Download failed")
		if error_instance is not None:
			error_message = type(error_instance).__name__ + ':\n' + str(error_instance.code) + ' ' + error_instance.reason
			text += ":\n" + error_message
		print("[IMDB] ", text)
		self["statusbar"].setText(text)

	def IMDBmainDownloaded(self, string):
		with self.downloadedLock:
			self.downloaded |= self.mainDownloaded
			if self.downloaded == self.allDownloaded:
				self.IMDBquery2('')

	def IMDBstorylineDownloaded(self, string):
		with self.downloadedLock:
			self.downloaded |= self.storylineDownloaded
			if self.downloaded == self.allDownloaded:
				self.IMDBquery2('')

	def IMDBquery2(self, string):
		self["statusbar"].setText(_("IMDb Re-Download completed"))
		self.inhtml = self.html2utf8(open("/tmp/imdbquery2.html", "r").read())
		self.generalinfos = self.generalinfomask.search(self.inhtml)
		self.IMDBparseStoryline()
		self.IMDBparse()

	def IMDBparseStoryline(self):
		self.storyline = ''
		storylineHtml = self.html2utf8(open("/tmp/imdbquery-storyline.html", "r").read())
		m = self.storylinemask.search(storylineHtml)
		if m is None:
			m = self.storylinealtmask.search(storylineHtml)
		if m is not None:
			try:
				self.storyline = ' '.join(self.htmltags.sub('', m.group(1).replace("\n", ' ').replace("<br>", '\n').replace("<br />", '\n')).replace(' |' + self.NBSP, '').replace(self.NBSP, ' ').replace('&lt;', '').replace('&gt;', '').split()) + "\n"
			except IndexError:
				pass

	def IMDBparse(self):
		self.Page = 1
		Detailstext = _("No details found.")
		if self.generalinfos:
			self["key_yellow"].setText(_("Details"))
			self["statusbar"].setText(_("IMDb Details parsed") + '.')
			Titeltext = self.generalinfos.group("title").replace(self.NBSP, ' ').strip()
			if len(Titeltext) > 57:
				Titeltext = Titeltext[0:54] + "..."
			self["title"].setText(Titeltext)

			Detailstext = ""
			addnewline = ''

			genreblock = self.genreblockmask.search(self.inhtml)
			if genreblock:
				genres = ' | '.join(re.split('\|+', self.htmltags.sub('|', genreblock.group(1)).strip('|').replace(self.NBSP, ' ')))
				if genres:
					Detailstext += addnewline + _("Genre:") + " " + genres
					addnewline = "\n"
					self.callbackGenre = genres

			for category in ("director", "creator", "writer", "seasons"):
				try:
					if self.generalinfos.group(category):
						if category == 'seasons':
							txt = ' '.join(self.htmltags.sub(' ', self.generalinfos.group(category)).replace("\n", ' ').replace(self.NBSP, ' ').replace(self.RAQUO, '').replace('See all', '...').split())
						elif category == 'creator':
							txt = ', '.join(re.split('\|+', self.htmltags.sub('|', self.generalinfos.group(category).replace('</a><span class="ipc-metadata-list-item__list-content-item--subText">', ' ')).strip('|').replace("\n", ' ').replace(self.NBSP, ' ').replace(self.RAQUO, '').replace(self.HELLIP + 'See all', '...')))
						else:
							txt = ', '.join(re.split('\|+', self.htmltags.sub('|', self.generalinfos.group(category)).strip('|').replace("\n", ' ').replace(self.NBSP, ' ').replace(self.RAQUO, '').replace(self.HELLIP + 'See all', '...')))
						Detailstext += addnewline + self.generalinfos.group('g_' + category).capitalize() + ": " + txt
						addnewline = "\n"
				except IndexError:
					pass

			for category in ("premiere", "country", "alternativ"):
				try:
					if self.generalinfos.group(category):
						txt = ', '.join(re.split('\|+', self.htmltags.sub('|', self.generalinfos.group(category).replace('\n', ' ')).strip('|')))
						Detailstext += addnewline + self.generalinfos.group('g_' + category) + ": " + txt
						addnewline = "\n"
				except IndexError:
					pass

			rating = self.ratingmask.search(self.inhtml)
			Ratingtext = _("no user rating yet")
			if rating:
				rating = rating.group("rating")
				if rating != '<span id="voteuser"></span>':
					Ratingtext = _("User Rating") + ": " + rating + " / 10"
					self.ratingstars = int(10 * round(float(rating.replace(',', '.')), 1))
					self["stars"].show()
					self["stars"].setValue(self.ratingstars)
					self["starsbg"].show()
			self["ratinglabel"].setText(Ratingtext)

			castresult = self.castmask.finditer(self.inhtml)
			if castresult:
				Casttext = ""
				i = 0
				for x in castresult:
					extra_space = ' '
					Casttext += "\n" + extra_space + self.htmltags.sub('', x.group('actor'))
					if x.group('character'):
						chartext = self.htmltags.sub(' ', x.group('character').replace('/ ...', '')).replace('\n', ' ').replace(self.NBSP, ' ')
						Casttext += _(" as ") + ' '.join(chartext.split()).replace('…', '')
						try:
							if config.plugins.imdb.showepisodeinfo.value and x.group('episodes'):
								Casttext += ' [' + self.htmltags.sub('', re.sub(r"[0-9]+ eps", "", x.group('episodes')).replace(' • ', ', ')).strip() + ']'
						except IndexError:
							pass
					i += 1
					if i >= 16:
						break
				if Casttext:
					Casttext = _("Cast: ") + Casttext
				else:
					Casttext = _("No cast list found in the database.")
				self["castlabel"].setText(Casttext)

			posterurl = self.postermask.search(self.inhtml)
			if posterurl and posterurl.group(1).find("jpg") > 0:
				posterurl = posterurl.group(1)
				self["statusbar"].setText(_("Downloading Movie Poster..."))
				localfile = "/tmp/poster.jpg"
				print("[IMDB] downloading poster " + posterurl + " to " + localfile)
				Downloader(posterurl, localfile).addSuccessCallback(self.IMDBPoster).addFailureCallback(self.http_failed).start()
			else:
				self.IMDBPoster("kein Poster")

			Extratext = ''
			awardsresult = self.awardsmask.finditer(self.inhtml)
			if awardsresult:
				awardslist = [' '.join(x.group('awards').split()) for x in awardsresult]
				if awardslist:
					Extratext = _("Extra Info") + "\n\n" + self.allhtmltags.sub(' | ', ''.join(awardslist).replace('<b>', '').strip()) + "\n"

			extrainfos = self.extrainfomask.search(self.inhtml)

			if extrainfos:
				if not Extratext:
					Extratext = _("Extra Info") + "\n"

				addspace = {"outline", "synopsis", "tagline", "cert", "locations", "trivia", "goofs", "quotes", "connections"}

				categories = ("outline", "synopsis", "tagline", "keywords", "cert", "runtime", "language", "color", "aspect", "sound", "locations", "company", "trivia", "goofs", "quotes", "connections")
				for category in categories:
					if category == "synopsis":
						if self.storyline:
							Extratext += "\n" + _("Storyline") + ":\n" + self.storyline + "\n"
						else:
							Extratext += "\n"
						continue

					extraspace = "\n" if category in addspace else ''
					try:
						if extrainfos.group(category):
							sep = ":\n" if category in ("outline", "synopsis") else ": "
							Extratext += extraspace
							try:
								if category == "outline":
									if "Add full plot" in extrainfos.group(category):
										continue
									Extratext += _("Plot Outline")
								elif extrainfos.group('g_' + category):
									Extratext += extrainfos.group('g_' + category)
								else:
									Extratext += _("Unknown category")
							except IndexError: # there's no g_keywords anymore
								pass
							if category == "trivia" or category == "quotes" or category == "connections" or category == "runtime" or category == 'synopsis':
								txt = ' '.join(self.htmltags.sub(' ', extrainfos.group(category).replace("\n", ' ').replace("<br>", '\n').replace("<br />", '\n')).replace(' |' + self.NBSP, '').replace(self.NBSP, ' ').split())
							elif category == "keywords":
								Extratext += "\n" + _("Keywords") # there's no g_keywords anymore
								txt = ' | '.join(re.split('\|+', self.htmltags.sub('|', extrainfos.group(category).replace("\n", ' ').replace("<br>", '\n').replace("<br />", '\n')).strip('|').replace(' |' + self.NBSP, '').replace(self.NBSP, ' ')))
							else:
								txt = ', '.join(re.split('\|+', self.htmltags.sub('|', extrainfos.group(category).replace("\n", ' ').replace("<br>", '\n').replace("<br />", '\n')).strip('|').replace(' |' + self.NBSP, '').replace(self.NBSP, ' ')))
							Extratext += sep + txt + "\n"
					except IndexError:
						pass
				try:
					if extrainfos.group("g_comments"):
						g_rating = ""
						try:
							if extrainfos.group("g_rating") and extrainfos.group("g_maxrating"):
								g_rating = " [" + extrainfos.group("g_rating") + "/" + extrainfos.group("g_maxrating") + "]"
						except IndexError:
							pass
						Extratext += "\n" + extrainfos.group("g_comments") + ":\n" + extrainfos.group("commenttitle") + " [" + ' '.join(self.htmltags.sub('', extrainfos.group("commenter")).split()) + "]" + g_rating + ":\n\n" + self.htmltags.sub('', extrainfos.group("comment").replace("\n", ' ').replace(self.NBSP, ' ').replace("<br>", '\n').replace("<br/>", '\n').replace("<br />", '\n')) + "\n"
				except IndexError:
					pass

			if Extratext:
				self["extralabel"].setText(Extratext)
				self["extralabel"].hide()
				self["key_blue"].setText(_("Extra Info"))

		self["detailslabel"].setText(Detailstext)
		self.callbackData = Detailstext

	def IMDBPoster(self, string):
		self["statusbar"].setText(_("IMDb Details parsed") + '.')
		if not string:
			filename = "/tmp/poster.jpg"
		else:
			filename = resolveFilename(SCOPE_PLUGINS, "Extensions/IMDb/no_poster.png")
		sc = AVSwitch().getFramebufferScale()
		self.picload.setPara((self["poster"].instance.size().width(), self["poster"].instance.size().height(), sc[0], sc[1], False, 1, "#00000000"))
		self.picload.startDecode(filename)

	def paintPosterPixmapCB(self, picInfo=None):
		ptr = self.picload.getData()
		if ptr != None:
			self["poster"].instance.setPixmap(ptr)
			self["poster"].show()

	def setup(self):
		self.session.open(IMDbSetup)

	def createSummary(self):
		return IMDbLCDScreen


class IMDbLCDScreen(Screen):
	skin = """
	<screen position="0,0" size="132,64" title="IMDB Plugin">
		<widget name="headline" position="4,0" size="128,22" font="Regular;20"/>
		<widget source="parent.title" render="Label" position="6,26" size="120,34" font="Regular;14"/>
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session, parent)
		self["headline"] = Label(_("IMDb Plugin"))


class IMDbSetup(Screen, ConfigListScreen):
	skin = """<screen name="EPGSearchSetup" position="center,center" size="565,370">
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="config" position="5,50" size="555,250" scrollbarMode="showOnDemand" />
		<ePixmap pixmap="skin_default/div-h.png" position="0,301" zPosition="1" size="565,2" />
		<widget source="help" render="Label" position="5,305" size="555,63" font="Regular;21" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["Setup"]

		self['footnote'] = Label(_("* = Restart Required"))
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)

		# Summary
		self.setup_title = _("IMDb Setup")
		self.onChangedEntry = []

		# Initialize widgets
		self["key_green"] = StaticText(_("OK"))
		self["key_red"] = StaticText(_("Cancel"))
		self["description"] = Label("")

		# Define Actions
		self["actions"] = ActionMap(["SetupActions"],
			{
				"cancel": self.keyCancel,
				"save": self.keySave,
			}, -2)

		self["VirtualKB"] = ActionMap(["VirtualKeyboardActions"],
		{
			"showVirtualKeyboard": self.KeyText,
		}, -2)
		self["VirtualKB"].setEnabled(False)

		self.list = []
		ConfigListScreen.__init__(self, self.list, session=self.session, on_change=self.changedEntry)
		self.createSetup()
		if not self.handleInputHelpers in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.handleInputHelpers)
		self.changedEntry()
		self.onLayoutFinish.append(self.layoutFinished)

	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Show search in plugin browser"), config.plugins.imdb.showinplugins, _("Enable this to be able to access IMDb searches from within the plugin browser.")))
		self.list.append(getConfigListEntry(_("Show setup in plugin browser"), config.plugins.imdb.showsetupinplugins, _("Enable this to be able to access IMDb search setup from within the plugin browser.")))
		self.list.append(getConfigListEntry(_("Show in movie list"), config.plugins.imdb.showinmovielist, _("Enable this to be able to access IMDb searches from within the movie list."))),
		self.list.append(getConfigListEntry(_("Words / phrases to ignore "), config.plugins.imdb.ignore_tags, _("This option allows you add words/phrases for IMDb to ignore when searching. Please separate the words/phrases with commas.")))
		self.list.append(getConfigListEntry(_("Show full movie or series name in title menu"), config.plugins.imdb.showlongmenuinfo, _("Show the whole IMDb title information for a movie or series, including, for example, alternative names and whether it's a series. Takes effect after the next search of IMDb for a show name.")))
		self.list.append(getConfigListEntry(_("Show episode and year information in cast list"), config.plugins.imdb.showepisodeinfo, _("Show episode and year information for cast when available. Takes effect after the next fetch of show details.")))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def handleInputHelpers(self):
		if self["config"].getCurrent() is not None:
			try:
				if isinstance(self["config"].getCurrent()[1], ConfigText) or isinstance(self["config"].getCurrent()[1], ConfigPassword):
					if "VKeyIcon" in self:
						self["VirtualKB"].setEnabled(True)
						self["VKeyIcon"].boolean = True
					if "HelpWindow" in self:
						if self["config"].getCurrent()[1].help_window.instance is not None:
							helpwindowpos = self["HelpWindow"].getPosition()
							from enigma import ePoint
							self["config"].getCurrent()[1].help_window.instance.move(ePoint(helpwindowpos[0], helpwindowpos[1]))
				else:
					if "VKeyIcon" in self:
						self["VirtualKB"].setEnabled(False)
						self["VKeyIcon"].boolean = False
			except:
				if "VKeyIcon" in self:
					self["VirtualKB"].setEnabled(False)
					self["VKeyIcon"].boolean = False
		else:
			if "VKeyIcon" in self:
				self["VirtualKB"].setEnabled(False)
				self["VKeyIcon"].boolean = False

	def HideHelp(self):
		try:
			if isinstance(self["config"].getCurrent()[1], ConfigText):
				if self["config"].getCurrent()[1].help_window.instance is not None:
					self["config"].getCurrent()[1].help_window.hide()
		except:
			pass

	def KeyText(self):
		if isinstance(self["config"].getCurrent()[1], ConfigText):
			if self["config"].getCurrent()[1].help_window.instance is not None:
				self["config"].getCurrent()[1].help_window.hide()
		self.session.openWithCallback(self.VirtualKeyBoardCallback, VirtualKeyBoard, title=self["config"].getCurrent()[0], text=self["config"].getCurrent()[1].getValue())

	def VirtualKeyBoardCallback(self, callback=None):
		if callback is not None and len(callback):
			self["config"].getCurrent()[1].setValue(callback)
			self["config"].invalidate(self["config"].getCurrent())

	def layoutFinished(self):
		self.setTitle(_(self.setup_title))

	# for summary:
	def changedEntry(self):
		self.item = self["config"].getCurrent()
		for x in self.onChangedEntry:
			x()
		try:
			if isinstance(self["config"].getCurrent()[1], ConfigYesNo) or isinstance(self["config"].getCurrent()[1], ConfigSelection):
				self.createSetup()
		except:
			pass

	def getCurrentEntry(self):
		return self["config"].getCurrent() and self["config"].getCurrent()[0] or ""

	def getCurrentValue(self):
		return self["config"].getCurrent() and str(self["config"].getCurrent()[1].getText()) or ""

	def getCurrentDescription(self):
		return self["config"].getCurrent() and len(self["config"].getCurrent()) > 2 and self["config"].getCurrent()[2] or ""

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary

	def keySave(self):
		self.saveAll()

		for pl in pluginlist:
			if not pl[0].value:
				for plugin in plugins.getPlugins(pl[1].where):
					if plugin == pl[1]:
						plugins.removePlugin(plugin)

		plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
		self.close()

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary


def eventinfo(session, eventName="", **kwargs):
	if not eventName:
		s = session.nav.getCurrentService()
		if s:
			info = s.info()
			event = info.getEvent(0) # 0 = now, 1 = next
			eventName = event and event.getEventName() or ''
	session.open(IMDB, eventName)


def main(session, eventName="", **kwargs):
	session.open(IMDB, eventName)


def setup(session, **kwargs):
	session.open(IMDbSetup)


def movielistSearch(session, service, **kwargs):
	KNOWN_EXTENSIONS = ['x264', '720p', '1080p', '1080i', 'PAL', 'GERMAN', 'ENGLiSH', 'WS', 'DVDRiP', 'UNRATED', 'RETAIL', 'Web-DL', 'DL', 'LD', 'MiC', 'MD', 'DVDR', 'BDRiP', 'BLURAY', 'DTS', 'UNCUT', 'ANiME', 'AC3MD', 'AC3', 'AC3D', 'TS', 'DVDSCR', 'COMPLETE', 'INTERNAL', 'DTSD', 'XViD', 'DIVX', 'DUBBED', 'LINE.DUBBED', 'DD51', 'DVDR9', 'DVDR5', 'h264', 'AVC', 'WEBHDTVRiP', 'WEBHDRiP', 'WEBRiP', 'WEBHDTV', 'WebHD', 'HDTVRiP', 'HDRiP', 'HDTV', 'ITUNESHD', 'REPACK', 'SYNC']
	serviceHandler = eServiceCenter.getInstance()
	info = serviceHandler.info(service)
	eventName = info and info.getName(service) or ''
	(root, ext) = os.path.splitext(eventName)
	if ext in KNOWN_EXTENSIONS:
		print("#####################", ext)
		eventName = re.sub("[\W_]+", ' ', root.decode("utf8"), 0, re.LOCALE | re.UNICODE).encode("utf8")
	session.open(IMDB, eventName)


pluginlist = (
	(
		config.plugins.imdb.showinplugins,
		PluginDescriptor(
			name=_("IMDb search"),
			description=_("Search for details from the Internet Movie Database"),
			icon="imdb.png",
			where=PluginDescriptor.WHERE_PLUGINMENU,
			fnc=main,
			needsRestart=False,
		)
	),
	(
		config.plugins.imdb.showsetupinplugins,
		PluginDescriptor(
			name=_("IMDb setup"),
			description=_("Settings for Internet Movie Database searches"),
			icon="imdb.png",
			where=PluginDescriptor.WHERE_PLUGINMENU,
			fnc=setup,
			needsRestart=False,
		)
	),
	(
		config.plugins.imdb.showinmovielist,
		PluginDescriptor(
			name=_("IMDb search"),
			description=_("IMDb search"),
			where=PluginDescriptor.WHERE_MOVIELIST,
			fnc=movielistSearch,
			needsRestart=False,
		)
	),
)


def Plugins(**kwargs):
	l = [PluginDescriptor(name=_("IMDb search") + "...",
			description=_("Search for details from the Internet Movie Database"),
			where=PluginDescriptor.WHERE_EVENTINFO,
			fnc=eventinfo,
			needsRestart=False,
			),
		]

	l += [pl[1] for pl in pluginlist if pl[0].value]

	return l
