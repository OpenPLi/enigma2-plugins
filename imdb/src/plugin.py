# for localized messages
from . import _

from Plugins.Plugin import PluginDescriptor
from enigma import ePicLoad, eServiceCenter
from Screens.Screen import Screen
from Screens.HelpMenu import HelpableScreen
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
from Components.MovieList import KNOWN_EXTENSIONS
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS
import json
import os
import re
import requests
import six
from time import strftime
from twisted.internet.threads import deferToThread
from shutil import copy

from six.moves.urllib.parse import quote_plus

try:
	import htmlentitydefs
except ImportError as ie:
	from html import entities as htmlentitydefs


# Configuration
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigYesNo, ConfigText, getConfigListEntry
from Components.PluginComponent import plugins


config.plugins.imdb = ConfigSubsection()
config.plugins.imdb.showinplugins = ConfigYesNo(default=False)
config.plugins.imdb.showsetupinplugins = ConfigYesNo(default=True)
config.plugins.imdb.showinmovielist = ConfigYesNo(default=True)
config.plugins.imdb.force_english = ConfigYesNo(default=False)
config.plugins.imdb.ignore_tags = ConfigText(visible_width=50, fixed_size=False)
config.plugins.imdb.showlongmenuinfo = ConfigYesNo(default=False)
config.plugins.imdb.showepisoderesults = ConfigYesNo(default=False)
config.plugins.imdb.showepisodeinfo = ConfigYesNo(default=False)


def getPage(url, params=None, headers=None, cookies=None):
	if headers is None:
		headers = {}
	headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:107.0) Gecko/20100101 Firefox/107.0'
	return deferToThread(requests.get, url, params=params, headers=headers, cookies=cookies, timeout=30.05)


def savePage(response, filename):
	response.raise_for_status()
	try:
		open(filename, "wb").write(response.content)
	except Exception as e:
		return e


def downloadPage(url, filename, params=None, headers=None, cookies=None):
	return getPage(url, params, headers, cookies).addCallback(savePage, filename)


def safeRemove(*names):
	for name in names:
		try:
			os.remove(name)
		except:
			pass


def quoteEventName(eventName):
	# BBC uses '\x86' markers in program names, remove them
	try:
		text = eventName.decode('utf8').replace(u'\x86', u'').replace(u'\x87', u'').encode('utf8')
	except:
		text = eventName
	return quote_plus(text)


# Replace entities with characters, "<br/>" with "\n" and strip any other tags.
def html2text(html):
	def sub(match):
		if match.group(0)[0] == "<":
			return match.group(0) == "<br/>" and "\n" or ""
		if match.group(1):
			codepoint = htmlentitydefs.name2codepoint.get(match.group(1))
		elif match.group(2):
			codepoint = int(match.group(2), 16)
		else:  # match.group(3)
			codepoint = int(match.group(3))
		if codepoint:
			return six.PY2 and unichr(codepoint).encode("utf8") or chr(codepoint)
		return match.group(0)
	return re.sub(r"&(?:([A-Za-z0-9]+)|#x([0-9A-Fa-f]+)|#(\d+));|<.*?>", sub, html)


# Prevent labels from processing escape characters.
def text2label(text):
	return re.sub(r'\\([cnrt])', r'\\\r\1', text)


# Return the JSON element described by path (str/tuple/list), or default
# if it doesn't exist.  If an item in path is a list use the first
# element.	E.g.
#	get(json, ('key1', 'array', 'key2'))
# is equivalent to
#	json['key1']['array'][0]['key2']
# whilst also testing each key exists.
def get(json, path, default=""):
	if not isinstance(path, (list, tuple)):
		path = (path,)
	for key in path:
		if not json:
			return default
		if isinstance(json, list):
			json = json[0]
		if key not in json:
			return default
		json = json[key]
	if isinstance(json, six.text_type):
		# It's possible UTF-8 has itself been converted to UTF-8
		# (e.g. the storyline of "As You Want Me" / "Come mi vuoi").
		try:
			json = json.encode("latin1").decode("utf8")
		except:
			pass
		if six.PY2:
			json = json.encode("utf8")
	return json


# Process strings containing
#	{VAR, plural, one {FORMAT} other {FORMAT}}
# where VAR is present in keywords and will substitute the appropriate
# format.
def LingUI(s, **keywords):
	# s starts at a brace, return between its closing brace.
	def extract(s):
		b = 0
		for i, c in enumerate(s):
			if c == "{":
				b += 1
			elif c == "}":
				b -= 1
				if b == 0:
					return s[1:i]
		return s[1:]

	r = ""
	end = 0
	while True:
		start = end
		while end < len(s) and s[end] != "{":
			end += 1
		r += s[start:end]
		if end >= len(s):
			return r
		plural = extract(s[end:])
		end += len(plural) + 2
		data = plural.split(", ")
		one = extract(data[2][4:])
		other = extract(data[2][4 + len(one) + 2 + 7:])
		fmt = keywords[data[0]] == 1 and one or other
		r += fmt.format(**keywords)


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
			<widget name="ratinglabel" position="340,62" size="250,20" halign="center" font="Regular;18" foregroundColor="#f0b400"/>
			<widget name="statusbar" position="10,404" size="580,16" font="Regular;16" foregroundColor="#cccccc" />
			<widget name="poster" position="4,90" size="96,140" alphatest="on" />
			<widget name="menu" position="10,115" size="580,275" zPosition="3" scrollbarMode="showOnDemand" />
			<widget name="starsbg" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/IMDb/starsbar_empty.png" position="340,40" zPosition="0" size="210,21" transparent="1" alphatest="on" />
			<widget name="stars" position="340,40" size="210,21" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/IMDb/starsbar_filled.png" transparent="1" />
		</screen>"""

	def __init__(self, session, eventName, callbackNeeded=False, save=False, savepath=None, localpath=None, imdbId=None):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)

		for tag in config.plugins.imdb.ignore_tags.getValue().split(','):
			eventName = eventName.replace(tag, '')

		eventName = ' '.join(eventName.split()).strip()

		self.eventName = eventName

		self.callbackNeeded = callbackNeeded
		self.callbackData = ""
		self.callbackGenre = ""

		# Always enable saving.
		#self.saving = save
		self.saving = True
		self.savingpath = savepath or "/home/root/logs/imdb"
		self.localpath = localpath

		self.imdbId = imdbId

		self["poster"] = Pixmap()
		self.picload = ePicLoad()
		self.picload.PictureData.get().append(self.paintPosterPixmapCB)
		self.poster_pos = None

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
		self["key_help"] = Boolean(True)  # for auto buttons
		self["key_menu"] = Boolean(True)  # for auto buttons
		self["VKeyIcon"] = Boolean(False)  # for auto buttons

		# 0 = multiple query selection menu page
		# 1 = movie info page
		# 2 = extra infos page
		# 3 = synopsis page
		self.Page = 0

		self.cookie = {
			"lc-main": language.getLanguage(),
			"session-id": "000-0000000-0000000"
		}

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
		self["actionsInfobar"] = HelpableActionMap(self, ["InfobarActions", "InfobarTeletextActions"],
		{
			"showMovies": (self.bigPoster, _("Show a bigger poster")),
			"startTeletext": (self.showSynopsis, _("Show movie and series synopsis")),
		}, -1)
		self["actionsDir"] = HelpableActionMap(self, "DirectionActions",
		{
			"down": (self.pageDown, _("Page down")),
			"up": (self.pageUp, _("Page up")),
		}, -1)

		self.onLayoutFinish.append(self.getIMDB)

	def exit(self):
		if self.hideBigPoster():
			return

		safeRemove("/tmp/poster.jpg", "/tmp/poster-big.jpg")
		if self.callbackNeeded:
			self.close([self.callbackData, self.callbackGenre])
		else:
			self.close()

	def resetLabels(self):
		self["poster"].instance.setPixmap(None)
		self["detailslabel"].setText("")
		self["ratinglabel"].setText("")
		self["title"].setText("")
		self["castlabel"].setText("")
		self["titellabel"].setText("")
		self["extralabel"].setText("")
		self.ratingstars = -1

	def pageUp(self):
		if self.hideBigPoster():
			return

		if self.Page == 0:
			self["menu"].instance.moveSelection(self["menu"].instance.moveUp)
		elif self.Page == 1:
			self["castlabel"].pageUp()
			self["detailslabel"].pageUp()
		else:  # self.Page in (2, 3):
			self["extralabel"].pageUp()

	def pageDown(self):
		if self.hideBigPoster():
			return

		if self.Page == 0:
			self["menu"].instance.moveSelection(self["menu"].instance.moveDown)
		elif self.Page == 1:
			self["castlabel"].pageDown()
			self["detailslabel"].pageDown()
		else:  # self.Page in (2, 3):
			self["extralabel"].pageDown()

	def showMenu(self):
		self.hideBigPoster()

		if self.Page != 0 and self.resultlist:
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
			self["VKeyIcon"].boolean = False
			self.Page = 0

	def getLocalDetails(self):
		self.html = open(self.localpath).read()
		try:
			self.json = open(os.path.splitext(self.localpath)[0] + ".json").read()
		except:
			pass
		self.IMDBparse()

	def gotTMD(self, response):
		if isinstance(response, requests.Response):
			self.json = response.content
			if six.PY3:
				self.json = self.json.decode("utf8")
		if self.haveHTML:
			self.IMDBparse()
		else:
			self.haveTMD = True

	def downloadTitle(self, title, titleId):
		self["statusbar"].setText(_("Re-Query IMDb: %s...") % title or titleId)
		fetchurl = "https://www.imdb.com/title/" + titleId + "/"
#		print("[IMDB] downloadTitle()", fetchurl)
		params = {
			"operationName": 'TMD_Storyline',
			"variables": '{"titleId":"%s"}' % titleId,
			"extensions": '{"persistedQuery":{"sha256Hash":"87f41463a48af95ebba3129889d17181402622bfd30c8dc9216d99ac984f0091","version":1}}'
		}
		self.haveTMD = self.haveHTML = False
		tmd = getPage("https://caching.graphql.imdb.com/", params=params, headers={"content-type": "application/json"}, cookies=self.cookie)
		tmd.addBoth(self.gotTMD)
		download = getPage(fetchurl, cookies=self.cookie)
		download.addCallback(self.IMDBquery2).addErrback(self.http_failed)

	def showDetails(self):
		self.hideBigPoster()

		self["poster"].show()
		self["ratinglabel"].show()
		self["castlabel"].show()
		self["detailslabel"].show()

		if self.resultlist and self.Page == 0:
			title, titleId = self["menu"].getCurrent()
			self.downloadTitle(title, titleId)
			self["menu"].hide()
			self.resetLabels()
			self.Page = 1

		if self.Page in (2, 3):
			self["extralabel"].hide()
			if self.ratingstars > 0:
				self["starsbg"].show()
				self["stars"].show()
				self["stars"].setValue(self.ratingstars)

			self.Page = 1

	def showExtras(self, synopsis=False):
		self.hideBigPoster()

		if self.Page == 0 or (not synopsis and not self.extra):
			return
		if self.Page == 1:
			self["extralabel"].show()
			self["detailslabel"].hide()
			self["castlabel"].hide()
			self["poster"].hide()
		self["extralabel"].setText(self.synopsis if synopsis else self.extra)
		self.Page = synopsis and 3 or 2

	def showSynopsis(self):
		self.hideBigPoster()

		if self.synopsis:
			self.showExtras(True)

	def contextMenuPressed(self):
		self.hideBigPoster()

		list = [
			(_("Enter search"), self.openVirtualKeyBoard),
			(_("Setup"), self.setup),
		]

		if self.saving:
			if self.savingpath is not None and self.titleId:
				list.extend((
					(_("Save current Details as .html for offline use"), self.saveHtmlDetails),
					(_("Save current Details as .txt"), self.saveTxtDetails),
					(_("Save current Poster and Details as .txt"), self.savePosterTxtDetails),
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
				isave = self.savingpath + "-" + self.titleId
				open(isave + ".html", 'w').write(self.html)
				if self.json:
					open(isave + ".json", 'w').write(self.json)
				try:
					copy("/tmp/poster.jpg", isave + ".jpg")
				except:
					pass
			self["statusbar"].setText(_("IMDb save completed"))
		except Exception as e:
			print('[IMDb] saveHtmlDetails exception failure:', str(e))

	def saveTxtDetails(self, poster=False):
		try:
			if self.savingpath is not None:
				getTXT = self.IMDBsavetxt(poster)
				if getTXT is not None:
					open(self.savingpath + "-" + self.titleId + ".txt", 'w').write(getTXT)
				else:
					from Screens.MessageBox import MessageBox
					self.session.open(MessageBox, (_('IMDb can not get Movie Information to write to .txt file!')), MessageBox.TYPE_INFO, 10)
		except Exception as e:
			print('[IMDb] saveTxtDetails exception failure:', str(e))

	def savePosterTxtDetails(self):
		self.saveTxtDetails(True)

	def IMDBsavetxt(self, poster=False):
		if not self.generalinfos:
			return None

		# save the poster.jpg (big poster if we have it, otherwise get full size)
		if poster:
			posterurl = self.generalinfos["poster"]
			if posterurl:
				postersave = self.savingpath + "-" + self.titleId + ".jpg"
				if fileExists("/tmp/poster-big.jpg"):
					copy("/tmp/poster-big.jpg", postersave)
				else:
#					print("[IMDB] downloading poster " + posterurl + " to " + postersave)
					download = downloadPage(posterurl, postersave)
					download.addErrback(self.http_failed)

		return (
			"%s\n"  # title
			"%s\n"  # rating
			"\n"
			"%s\n"  # details
			"\n"
			"%s\n"  # cast
			"\n"
			"%s\n"  # extra
			"%s"    # newlines & synopsis, if present
		) % (
			self.eventName,
			self["ratinglabel"].getText(),
			self.callbackData,
			self.castTxt,
			self.extraTxt,
			self.synopsisTxt and "\n".join(("", _("Synopsis"), "", self.synopsisTxt, "")) or ""
		)

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

	def gotSearchString(self, ret=None):
		if ret:
			self.eventName = ret
			self.Page = 0
			self.resultlist = []
			self["menu"].hide()
			self.resetLabels()
			self["ratinglabel"].show()
			self["castlabel"].show()
			self["detailslabel"].show()
			self["poster"].hide()
			self["stars"].hide()
			self["starsbg"].hide()
			self.getIMDB(search=True)

	def getIMDB(self, search=False):
		self.titleId = None
		self.html = ""
		self.json = self.generalinfos = None
		self.castTxt = self.extraTxt = self.synopsisTxt = ""
		self.extra = self.synopsis = ""
		safeRemove("/tmp/poster.jpg", "/tmp/poster-big.jpg")
		if not isinstance(self.eventName, six.string_types):
			self["statusbar"].setText("")
			return
		if not self.eventName:
			s = self.session.nav.getCurrentService()
			info = s and s.info()
			event = info and info.getEvent(0)  # 0 = now, 1 = next
			if event:
				self.eventName = event.getEventName()
			else:
				s = self.session.nav.getCurrentlyPlayingServiceReference()
				if s:
					self.eventName = s.toString()
					self.eventName = self.eventName.split('/')
					self.eventName = self.eventName[-1]
					self.eventName = self.eventName.replace('.', ' ')
					self.eventName = self.eventName.split('-')
					self.eventName = self.eventName[0]
					if self.eventName.endswith(' '):
						self.eventName = self.eventName[:-1]

		if not search:
			if self.localpath is not None:
				if os.path.exists(self.localpath):
					self.getLocalDetails()
				else:
					self["statusbar"].setText(_("Local file does not exist: %s") % self.localpath)
				return

			if self.imdbId:
				if self.imdbId.startswith("tt") and self.imdbId[2:].isdigit():
					self.downloadTitle(self.eventName, self.imdbId)
				else:
					self["statusbar"].setText(_("Ignoring invalid imdbId: %s") % self.imdbId)
				return

		if self.eventName:
			self["statusbar"].setText(_("Query IMDb: %s") % self.eventName)
			fetchurl = "https://www.imdb.com/find?q=" + quoteEventName(self.eventName) + "&s=tt"
#			print("[IMDB] getIMDB() Downloading Query", fetchurl)
			download = getPage(fetchurl, cookies=self.cookie)
			download.addCallback(self.IMDBquery).addErrback(self.http_failed)

		else:
			self["statusbar"].setText(_("Couldn't get event name"))

	def IMDBquery(self, response):
		self["statusbar"].setText(_("IMDb Download completed"))
		html = response.content
		if six.PY3:
			html = html.decode("utf8")
		start = html.find('"titleResults":{"results":')
		if start != -1:
			searchresults = json.JSONDecoder().raw_decode(html, start + 26)[0]
			self.resultlist = []
			titles = {}
			for x in searchresults:
				series = get(x, 'seriesId')
				if series:
					if not config.plugins.imdb.showepisoderesults.value:
						continue
					if series in titles:
						i = titles[series]
						for t in titles:
							if titles[t] >= i:
								titles[t] += 1
					else:
						title = get(x, 'seriesNameText')
						year = get(x, 'seriesReleaseText')
						typ = config.plugins.imdb.showlongmenuinfo.value and get(x, 'seriesTypeText') or ""
						if year or typ:
							title += " ("
							if year:
								title += year
							if typ:
								if year:
									title += "; "
								title += typ
							title += ")"
						self.resultlist.append((title, series))
						i = titles[series] = len(self.resultlist)
					title = "- "
					s = get(x, 'seriesSeasonText')
					if s == "Unknown":  # not translated
						s = ""
					e = get(x, 'seriesEpisodeText')
					if e == "Unknown":
						e = ""
				else:
					title = s = e = ""
					i = len(self.resultlist)
				title += get(x, 'titleNameText')
				year = get(x, 'titleReleaseText')
				if config.plugins.imdb.showlongmenuinfo.value:
					typ = not series and get(x, 'titleTypeText') or ""
					cast = get(x, 'topCredits')
				else:
					typ = cast = ""
				if year or typ or cast or s or e:
					title += " ("
					semicolon = False
					if year:
						title += year
						semicolon = True
					if typ:
						if semicolon:
							title += "; "
						semicolon = True
						title += typ
					if s:
						if semicolon:
							title += "; "
						semicolon = True
						title += _("S") + s
					if e:
						if s:
							title += " "
						elif semicolon:
							title += "; "
						semicolon = True
						title += _("E") + e
					if cast:
						if semicolon:
							title += "; "
						semicolon = True
						title += six.ensure_str(", ".join(cast))
					title += ")"
				self.resultlist.insert(i, (title, get(x, 'id')))
			Len = len(self.resultlist)
			self["menu"].l.setList(self.resultlist)
			if Len == 1:
				self.downloadTitle(self.resultlist[0][0], self.resultlist[0][1])
			elif Len > 1:
				self.Page = 1
				self.showMenu()
			else:
				self["detailslabel"].setText(_("No IMDb match."))
				self["statusbar"].setText(_("No IMDb match:") + ' ' + self.eventName)
		else:
			#self["detailslabel"].setText(_("IMDb query failed!"))
			print("[IMDB] no JSON found in search results, trying old method...")
			if re.search("<title>Find - IMDb</title>", html):
				pos = html.find('<table class="findList">')
				pos2 = html.find("</table>", pos)
				findlist = html[pos:pos2]
				searchresultmask = re.compile('<tr class="findResult (?:odd|even)">.*?<td class="result_text"> (<a href="/title/(tt\d{7,7})/.*?"\s?>(.*?)</a>.*?)</td>', re.DOTALL)
				searchresults = searchresultmask.finditer(findlist)
				titlegroup = 1 if config.plugins.imdb.showlongmenuinfo.value else 3
				htmltags = re.compile('<.*?>', re.DOTALL)
				nbsp = chr(htmlentitydefs.name2codepoint['nbsp'])
				self.resultlist = [(' '.join(htmltags.sub('', x.group(titlegroup)).replace(nbsp, " ").split()), x.group(2)) for x in searchresults]
				Len = len(self.resultlist)
				self["menu"].l.setList(self.resultlist)
				if Len == 1:
					self.downloadTitle(self.resultlist[0][0], self.resultlist[0][1])
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
					downloadPage(fetchurl, localfile).addCallback(self.IMDBquery).addErrback(self.http_failed)
				else:
					self["detailslabel"].setText(_("IMDb query failed!"))

	def http_failed(self, failure):
		text = _("IMDb Download failed")
		if isinstance(failure.value, requests.ConnectionError):
			error_message = _("connection error")
		elif isinstance(failure.value, requests.Timeout):
			error_message = _("timeout")
		else:
			if not isinstance(failure.value, requests.RequestException):
				text = _("IMDB Exception")
			error_message = failure.getErrorMessage()
		text += ": " + error_message
#		print("[IMDB]", text)
		self["statusbar"].setText(text)
		return failure

	def IMDBquery2(self, response):
		self["statusbar"].setText(_("IMDb Re-Download completed"))
		self.html = response.content
		if six.PY3:
			self.html = self.html.decode("utf8")
		if self.haveTMD:
			self.IMDBparse()
		else:
			self.haveHTML = True

	def IMDBparse(self):
		self.Page = 1
		Detailstext = _("No details found.")
		start = self.html.find('pageProps":')
		if start != -1:
			pageProps = json.JSONDecoder().raw_decode(self.html, start + 11)[0]
			fold = pageProps['aboveTheFoldData']
			main = pageProps['mainColumnData']
			i18n = pageProps['translationContext']['i18n']['translations']['resources']
			try:
				tmd = json.loads(self.json)['data']['title']
			except Exception as e:
				print("[IMDB] tmd failed:", str(e))
				tmd = {}

			self.eventName = get(fold, ('titleText', 'text'))
			self.titleId = get(fold, 'id')

			self["key_yellow"].setText(_("Details"))
			self["statusbar"].setText(_("IMDb Details parsed"))

			# "formatted-duration-duration": "{value} {unit}",
			# "formatted-duration-longFormatting": "{hours} {minutes} {seconds}",
			# "formatted-duration-hoursUnit": "{value, plural, one {hour} other {hours}}",
			# "formatted-duration-minutesUnit": "{value, plural, one {minute} other {minutes}}",
			# "formatted-duration-secondsUnit": "{value, plural, one {second} other {seconds}}",
			def runtime(seconds):
				if not seconds:
					return ""
				duration = {
					'hours': seconds // 3600 or "",
					'minutes': seconds % 3600 // 60 or "",
					'seconds': seconds % 60 or ""
				}
				for unit, value in duration.items():
					if value:
						duration[unit] = get(i18n, 'formatted-duration-duration').format(value=value, unit=LingUI(get(i18n, 'formatted-duration-%sUnit' % unit), value=value))
				return get(i18n, 'formatted-duration-longFormatting').format(**duration).replace("  ", " ").strip()

			# Format a date using the full format.
			def makedate(date):
				return strftime('%x', (date['year'], date['month'], date['day'], 0, 0, 0, 0, 0, 0))

			categories_i18n = {
				'director': get(main, ('directors', 'category', 'text')),
				'writer': get(main, ('writers', 'category', 'text')),
				'creator': get(main, ('creators', 'category', 'text')),
				'episodes': get(i18n, 'title_main_episodes_title'),
				# There's "Season" (no plural) or "{count} seasons" (no capital).
				'seasons': get(i18n, 'title_main_episodes_seasons').replace("{count}", "").strip().capitalize(),
				'premiere': get(i18n, 'title_main_details_releaseDate'),
				'country': LingUI(get(i18n, 'title_main_details_countriesOfOrigin'), countryCount=len(get(main, ('countriesOfOrigin', 'countries')))),
				'alternativ': get(i18n, 'title_main_details_aka'),

				'outline': get(i18n, 'title_main_hero_allTopics_plotLink'),      # no translation for "outline", just use "Plot"
				'synopsis': get(i18n, 'title_main_storyline_title'),
				'keywords': get(i18n, 'title_main_hero_allTopics_plotKeywordsLink'),
				'tagline': get(i18n, 'title_main_storyline_label_taglines'),
				'cert': get(i18n, 'title_main_storyline_label_certificate'),
				'trivia': get(i18n, 'title_subpage_trivia'),
				'goofs': get(i18n, 'title_subpage_goofs'),
				'quotes': get(i18n, 'title_subpage_quotes'),
				'connections': get(i18n, 'title_subpage_connections'),
				'commenttitle': get(i18n, 'title_main_userReviews_title'),
				'language': LingUI(get(i18n, 'title_main_details_languages'), languageCount=main['spokenLanguages'] and len(get(main, ('spokenLanguages', 'spokenLanguages')))),
				'locations': get(i18n, 'title_main_details_filmingLocations'),
				'company': LingUI(get(i18n, 'title_main_details_productionCompany'), companyCount=len(get(main, ('production', 'edges')))),
				'runtime': get(i18n, 'title_main_techspec_runtime'),
				'color': get(i18n, 'title_main_techspec_color'),
				'sound': get(i18n, 'title_main_techspec_soundmix'),
				'aspect': get(i18n, 'title_main_techspec_aspectratio'),
			}

			self.generalinfos = {
				'director': ", ".join(get(name, ('name', 'nameText', 'text')) for name in get(main, ('directors', 'credits'))),
				'creator': ", ".join(get(name, ('name', 'nameText', 'text')) for name in get(main, ('creators', 'credits'))),
				'episodes': get(main, ('episodes', 'totalEpisodes', 'total')),
				'seasons': len(get(main, ('episodes', 'seasons'))),
				'writer': ", ".join(get(name, ('name', 'nameText', 'text')) + (name['attributes'] and " (" + name['attributes'][0]['text'] + ")" or "") for name in get(main, ('writers', 'credits'))),
				'country': ', '.join(get(country, 'text') for country in get(main, ('countriesOfOrigin', 'countries'))),
				'premiere': main['releaseDate'] and "%s (%s)" % (makedate(main['releaseDate']), get(main, ('releaseDate', 'country', 'text'))),
				# there's also main['releaseYear']['year']
				'alternativ': get(main, ('akas', 'edges', 'node', 'text')),
				'rating': get(fold, ('ratingsSummary', 'aggregateRating')),
				'poster': get(fold, ('primaryImage', 'url'))
			}

			Titeltext = self.eventName
			if len(Titeltext) > 57:
				Titeltext = Titeltext[0:54] + "..."
			Titeltext = text2label(Titeltext)
			self["title"].setText(Titeltext)

			Detailslist = []

			genreblock = get(fold, ('genres', 'genres'))
			if genreblock:
				genres = LingUI(get(i18n, 'title_main_storyline_label_genres'), count=len(genreblock)) + ": "
				genres += " | ".join(get(genre, 'text') for genre in genreblock)
				Detailslist.append(genres)
				self.callbackGenre = genres

			for category in ('director', 'creator', 'writer', 'seasons', 'episodes', 'premiere', 'country', 'alternativ'):
				if self.generalinfos[category]:
					Detailslist.append(categories_i18n[category] + ": " + str(self.generalinfos[category]))

			Detailstext = "\n".join(Detailslist)

			rating = self.generalinfos['rating']
			if rating:
				Ratingtext = "%s: %.1f / 10" % (get(i18n, 'title_main_hero_aggregateRating'), rating)  # IMDb rating
				self.ratingstars = int(10 * round(rating, 1))
				self["stars"].show()
				self["stars"].setValue(self.ratingstars)
				self["starsbg"].show()
			else:
				Ratingtext = _("no user rating yet")
			self["ratinglabel"].setText(Ratingtext)

			cast = get(main, ('cast', 'edges'))
			if cast:
				Castlist = [get(i18n, 'title_main_cast_title') + ":"]

				def character(credit):
					char = get(credit, ('name', 'nameText', 'text'))
					if credit['characters']:
						char += " " + get(i18n, 'common_cast_characterName_with_as').format(characterName=" / ".join(get(ch, 'name') for ch in credit['characters']))
					# if credit['attributes']:
					#	char += " (%s)" % "; ".join(get(attr, 'text') for attr in name['attributes'])
					if config.plugins.imdb.showepisodeinfo.value:
						eps = get(credit, ('episodeCredits', 'total'))
						years = get(credit, ('episodeCredits', 'yearRange'))
						if eps:
							char += " [%s, %d" % (LingUI(get(i18n, 'common_cast_numEpisodes_short'), totalEpisodes=eps), years['year'])
							endYear = get(years, 'endYear')
							if endYear:
								char += "-" + str(endYear)
							char += "]"
					return char

				for node in cast:
					Castlist.append(character(node['node']))
				Casttext = "\n ".join(Castlist)
			else:
				Casttext = _("No cast list found in the database.")
			self.castTxt = Casttext
			Casttext = text2label(Casttext)
			self["castlabel"].setText(Casttext)

			posterurl = self.generalinfos['poster']
			if posterurl:
				# Get a poster size to fit its widget.
				posterurl = posterurl.replace("_V1_", "_V1_QL75_UY%d_" % self["poster"].instance.size().height())
				self["statusbar"].setText(_("Downloading Movie Poster..."))
				localfile = "/tmp/poster.jpg"
#				print("[IMDB] downloading poster " + posterurl + " to " + localfile)
				download = downloadPage(posterurl, localfile)
				download.addCallback(self.IMDBPoster).addErrback(self.http_failed)
			else:
				self.IMDBPoster("No Poster Art")

			# "feature_awards_winsAndNominations": "{numOfWins, plural, one {1 win} other {{numOfWins} wins}} & {numOfNoms, plural, one {1 nomination} other {{numOfNoms} nominations}}",
			# "feature_awards_winsAndNominationsTotal": "{numOfWins, plural, one {1 win} other {{numOfWins} wins}} & {numOfNoms, plural, one {1 nomination total} other {{numOfNoms} nominations total}}",
			# "feature_awards_onlyNominations": "{numOfNoms, plural, one {1 nomination} other {{numOfNoms} nominations}}",
			# "feature_awards_onlyNominationsTotal": "{numOfNoms, plural, one {1 nomination total} other {{numOfNoms} nominations total}}",
			# "feature_awards_onlyWins": "{numOfWins, plural, one {1 win} other {{numOfWins} wins}}",
			# "feature_awards_onlyWinsTotal": "{numOfWins, plural, one {1 win total} other {{numOfWins} wins total}}",
			# "feature_awards_oscars_won": "Won {count, plural, one {{count} Oscar} other {{count} Oscars}}",
			# "feature_awards_oscars_nominated": "Nominated for {count, plural, one {{count} Oscar} other {{count} Oscars}}",
			# "feature_awards_emmys_won": "Won {count, plural, one {{count} Primetime Emmy} other {{count} Primetime Emmys}}",
			# "feature_awards_emmys_nominated": "Nominated for {count, plural, one {{count} Primetime Emmy} other {{count} Primetime Emmys}}",
			# "feature_awards_globes_won": "Won {count, plural, one {{count} Golden Globe} other {{count} Golden Globes}}",
			# "feature_awards_globes_nominated": "Nominated for {count, plural, one {{count} Golden Globe} other {{count} Golden Globes}}",
			# "feature_awards_baftas_won": "Won {count, plural, one {{count} BAFTA Film Award} other {{count} BAFTA Film Awards}}",
			# "feature_awards_baftas_nominated": "Nominated for {count, plural, one {{count} BAFTA Film Award} other {{count} BAFTA Film Awards}}",
			awards = ""
			prest = get(main, 'prestigiousAwardSummary')
			if prest:
				award = prest['award']['event']['id']
				if award == "ev0000003":
					award = 'oscars'
				elif award == "ev0000223":
					award = 'emmys'
				elif award == "ev0000123":
					award = 'baftas'
				else:
					award = 'globes'
				wins = prest['wins']
				noms = prest['nominations']
				if wins:
					awards += LingUI(get(i18n, 'feature_awards_%s_won' % award), count=wins)
				else:
					awards += LingUI(get(i18n, 'feature_awards_%s_nominated' % award), count=noms)
				awards += " | "
			wins = get(main, ('wins', 'total'))
			noms = get(main, ('nominations', 'total'))
			if wins and noms:
				awards += LingUI(get(i18n, prest and 'feature_awards_winsAndNominationsTotal' or 'feature_awards_winsAndNominations'), numOfWins=wins, numOfNoms=noms)
			elif noms:
				awards += LingUI(get(i18n, prest and 'feature_awards_onlyNominationsTotal' or 'feature_awards_onlyNominations'), numOfNoms=noms)
			if awards:
				Extralist = ["", awards]
			else:
				Extralist = []

			# Format a quote.
			# [
			#	{
			#	  "characters": null,
			#	  "text": null,
			#	  "stageDirection": "from trailer",
			#	  "__typename": "TitleQuoteLine"
			#	},
			#	{
			#	  "characters": [
			#		{
			#		  "character": "John McBurney",
			#		  "name": {
			#			"id": "nm0268199",
			#			"__typename": "Name"
			#		  },
			#		  "__typename": "TitleQuoteCharacter"
			#		}
			#	  ],
			#	  "text": "What have you done to me, you vengeful bitches?",
			#	  "stageDirection": "screaming",
			#	  "__typename": "TitleQuoteLine"
			#	}
			# ]
			# -->
			# [from trailer]
			# John McBurney: [screaming] What have you done to me, you vengeful bitches?

			def quote(lines):
				q = []
				for char in lines:
					stageDirection = get(char, 'stageDirection')
					character = get(char, ('characters', 'character'))
					line = ""
					if character:
						line += character + ": "
						if stageDirection:
							line += "[%s] " % stageDirection
						line += get(char, 'text')
					elif stageDirection:
						line += "[%s]" % stageDirection
					q.append(line)
				return "\n".join(q)

			def connections(node):
				if not node:
					return ""
				r = get(node, ('category', 'text'))
				series = get(node, ('associatedTitle', 'series', 'series', 'titleText', 'text'))
				title = get(node, ('associatedTitle', 'titleText', 'text'))
				if series:
					r += " " + series
				if title:
					if series:
						r += ":"
					r += " " + title
				year = get(node, ('associatedTitle', 'releaseYear', 'year'))
				if year:
					r += " (%s)" % year
				return r

			summary_author = get(tmd, ('summaries', 'edges', 'node', 'author'))
			summary_author = summary_author and html2text(" &mdash;") + summary_author or ""  # might be None
			cert_reason = get(tmd, ('certificate', 'ratingReason')) or ""
			if cert_reason:
				body = get(tmd, ('certificate', 'ratingsBody', 'id'))
				if body:
					cert_reason = body + ": " + cert_reason
				cert_reason = " (" + cert_reason + ")"

			self.extrainfos = {
				'outline': get(fold, ('plot', 'plotText', 'plainText')),
				'synopsis': html2text(get(tmd, ('summaries', 'edges', 'node', 'plotText', 'plaidHtml'))) + summary_author,
				'keywords': " | ".join(get(name, ('node', 'text')) for name in get(fold, ('keywords', 'edges'))),
				'tagline': get(tmd, ('taglines', 'edges', 'node', 'text')),
				'cert': get(fold, ('certificate', 'rating')) + cert_reason,
				'trivia': html2text(get(main, ('trivia', 'edges', 'node', 'text', 'plaidHtml'))),
				'goofs': html2text(get(main, ('goofs', 'edges', 'node', 'text', 'plaidHtml'))),
				'quotes': quote(get(main, ('quotes', 'edges', 'node', 'lines'))),
				'connections': connections(get(main, ('connections', 'edges', 'node'))),
				'commenttitle': get(main, ('featuredReviews', 'edges', 'node', 'summary', 'originalText')),
				'comment': html2text(get(main, ('featuredReviews', 'edges', 'node', 'text', 'originalText', 'plaidHtml'))),
				'commenter': get(main, ('featuredReviews', 'edges', 'node', 'author', 'nickName')),
				'language': ", ".join(get(lang, 'text') for lang in get(main, ('spokenLanguages', 'spokenLanguages'))),
				'locations': get(main, ('filmingLocations', 'edges', 'node', 'text')),
				'company': ", ".join(get(node, ('node', 'company', 'companyText', 'text')) for node in get(main, ('production', 'edges'))),
				'runtime': runtime(get(main, ('runtime', 'seconds'))),
				'color': get(main, ('technicalSpecifications', 'colorations', 'items', 'text')),
				'sound': " | ".join(get(mix, 'text') for mix in get(main, ('technicalSpecifications', 'soundMixes', 'items'))),
				'aspect': get(main, ('technicalSpecifications', 'aspectRatios', 'items', 'aspectRatio')),
			}

			firstnospace = True
			nospace = ("cert", "runtime", "language", "color", "aspect", "sound")
			categories = ("outline", "synopsis", "tagline", "keywords", "cert", "runtime", "language", "color", "aspect", "sound", "locations", "company", "trivia", "goofs", "quotes", "connections")
			for category in categories:
				if self.extrainfos[category]:
					sep = ":\n" if category in ("outline", "synopsis", "quotes") else ": "
					extraspace = True
					if category in nospace:
						if firstnospace:
							firstnospace = False
						else:
							extraspace = False
					if extraspace:
						Extralist.append("")
					if category == "outline":
						outline = self.extrainfos["outline"]
						synopsis = self.extrainfos["synopsis"]
						if synopsis and synopsis.startswith(outline):
							if extraspace:
								Extralist.pop()
							continue
					Extralist.append(categories_i18n[category] + sep + self.extrainfos[category])
			if self.extrainfos["commenttitle"]:
				Extralist.append("")
				Extralist.append(categories_i18n['commenttitle'] + ": " + self.extrainfos['commenttitle'] + " [" + self.extrainfos['commenter'] + "]")
				Extralist.append(self.extrainfos['comment'])

			if Extralist:
				self.extraTxt = _("Extra Info") + "\n" + "\n".join(Extralist)
				self.extra = text2label(self.extraTxt)
				self["extralabel"].setText(self.extra)
				self["extralabel"].hide()
				self["key_blue"].setText(_("Extra Info"))
			else:
				self.extraTxt = self.extra = ""

			self.synopsisTxt = html2text(get(tmd, ('synopses', 'edges', 'node', 'plotText', 'plaidHtml')))
			self.synopsis = text2label(self.synopsisTxt)

		self.callbackData = Detailstext
		Detailstext = text2label(Detailstext)
		self["detailslabel"].setText(Detailstext)
		self["VKeyIcon"].boolean = self.synopsis and True or False

	def IMDBPoster(self, failed, big=False):
		self["statusbar"].setText(_("IMDb Details parsed"))
		if failed:
			filename = resolveFilename(SCOPE_PLUGINS, "Extensions/IMDb/no_poster.png")
		else:
			filename = big and "/tmp/poster-big.jpg" or "/tmp/poster.jpg"
		sc = AVSwitch().getFramebufferScale()
		self.picload.setPara((self["poster"].instance.size().width(), self["poster"].instance.size().height(), sc[0], sc[1], False, 1, "#00000000"))
		self.picload.startDecode(filename)

	def paintPosterPixmapCB(self, picInfo=None):
		ptr = self.picload.getData()
		if ptr is not None:
			self["poster"].instance.setPixmap(ptr)

	def bigPoster(self):
		if not self.generalinfos or self.poster_pos:
			return
		posterurl = self.generalinfos['poster']
		if posterurl:
			localfile = "/tmp/poster-big.jpg"
			if fileExists(localfile):
				self.IMDBPosterBig()
				return
			# Get a poster size to fit the skin.
			posterurl = posterurl.replace("_V1_", "_V1_QL75_UY%d_" % self.instance.size().height())
			self["statusbar"].setText(_("Downloading Movie Poster..."))
#			print("[IMDB] downloading poster " + posterurl + " to " + localfile)
			download = downloadPage(posterurl, localfile)
			download.addCallback(self.IMDBPosterBig).addErrback(self.http_failed)

	def IMDBPosterBig(self, failed=None):
		if failed:
			self["statusbar"].setText(str(failed))
			return
		self["statusbar"].setText(_("IMDb Details parsed"))
		self.poster_pos = (self["poster"].getPosition(), self["poster"].getSize())
		self["poster"].setZPosition(99)
		self["poster"].move(0, 0)
		self["poster"].resize(self.instance.size().width(), self.instance.size().height())
		self.IMDBPoster(None, True)
		self["poster"].show()

	def hideBigPoster(self):
		if self.poster_pos:
			if self.Page != 1:
				self["poster"].hide()
			self["poster"].move(self.poster_pos[0][0], self.poster_pos[0][1])
			self["poster"].resize(self.poster_pos[1][0], self.poster_pos[1][1])
			self.IMDBPoster(not fileExists("/tmp/poster.jpg"))
			self.poster_pos = None
			return True

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
		self.list.append(getConfigListEntry(_("Show episodes in title menu"), config.plugins.imdb.showepisoderesults, _("Include episodes in the results. Takes effect after the next search of IMDb for a show name.")))
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
			event = info.getEvent(0)  # 0 = now, 1 = next
			eventName = event and event.getEventName() or ''
	session.open(IMDB, eventName)


def main(session, eventName="", **kwargs):
	session.open(IMDB, eventName)


def setup(session, **kwargs):
	session.open(IMDbSetup)


def movielistSearch(session, serviceref, **kwargs):
	KNOWN_EXTENSIONS2 = frozenset(('x264', '720p', '1080p', '1080i', 'PAL', 'GERMAN', 'ENGLiSH', 'WS', 'DVDRiP', 'UNRATED', 'RETAIL', 'Web-DL', 'DL', 'LD', 'MiC', 'MD', 'DVDR', 'BDRiP', 'BLURAY', 'DTS', 'UNCUT', 'ANiME', 'AC3MD', 'AC3', 'AC3D', 'TS', 'DVDSCR', 'COMPLETE', 'INTERNAL', 'DTSD', 'XViD', 'DIVX', 'DUBBED', 'LINE.DUBBED', 'DD51', 'DVDR9', 'DVDR5', 'h264', 'AVC', 'WEBHDTVRiP', 'WEBHDRiP', 'WEBRiP', 'WEBHDTV', 'WebHD', 'HDTVRiP', 'HDRiP', 'HDTV', 'ITUNESHD', 'REPACK', 'SYNC'))
	serviceHandler = eServiceCenter.getInstance()
	info = serviceHandler.info(serviceref)
	eventName = info and info.getName(serviceref) or ''
	(root, ext) = os.path.splitext(eventName)
	if ext in KNOWN_EXTENSIONS or ext in KNOWN_EXTENSIONS2:
		if six.PY2:
			root = root.decode("utf8")
			eventName = re.sub(r"[\W_]+", ' ', root, 0, re.LOCALE | re.UNICODE)
			eventName = eventName.encode("utf8")
		else:
			eventName = re.sub(r"[\W_]+", ' ', root, 0)
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
