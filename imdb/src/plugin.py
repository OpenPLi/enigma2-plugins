# -*- coding: UTF-8 -*-
# for localized messages
from . import _, ngettext

from Plugins.Plugin import PluginDescriptor
from enigma import ePicLoad, eServiceCenter, eServiceReference
from Screens.Screen import Screen
from Screens.Setup import Setup
from Screens.HelpMenu import HelpableScreen
from Screens.ChoiceBox import ChoiceBox
from Screens.InfoBar import MoviePlayer
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.ActionMap import HelpableActionMap
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.Button import Button
from Components.MenuList import MenuList
from Components.Language import language
from Components.ProgressBar import ProgressBar
from Components.Sources.StaticText import StaticText
from Components.Sources.Boolean import Boolean
from Components.MovieList import KNOWN_EXTENSIONS
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS, isPluginInstalled
import json
import os
import re
import requests
from time import strftime, strptime
from twisted.internet.threads import deferToThread
from shutil import copy

from urllib.parse import quote_plus


# Configuration
from Components.config import config, ConfigSubsection, ConfigYesNo, ConfigText
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
config.plugins.imdb.translate_texts = ConfigYesNo(default=False)


def getPage(url, params=None, data=None, headers=None):
	return deferToThread(requests.post if data else requests.get, url, params=params, data=data, headers=headers, timeout=30.05)


def savePage(response, filename):
	response.raise_for_status()
	try:
		open(filename, "wb").write(response.content)
	except Exception as e:
		return e


def downloadPage(url, filename, params=None, headers=None):
	return getPage(url, params, headers).addCallback(savePage, filename)


def postGraphQL(query, operation_name=None, variables=None, headers=None):
	# IMDb's public-facing GraphQL is brittle. In practice, the caching endpoint
	# is often more permissive than api.graphql.imdb.com for anonymous requests.
	# Keep the payload minimal and inline variables into the query string.
	payload = {
		"query": query,
	}
	headers = headers or {}
	return getPage("https://caching.graphql.imdb.com/", data=json.dumps(payload), headers=headers)


def safeRemove(*names):
	for name in names:
		try:
			os.remove(name)
		except OSError:
			pass


def quoteEventName(eventName):
	# BBC uses '\x86' markers in program names, remove them
	try:
		text = eventName.decode('utf8').replace(u'\x86', u'').replace(u'\x87', u'').encode('utf8')
	except Exception:
		text = eventName
	return quote_plus(text)


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
	if isinstance(json, str):
		# It's possible UTF-8 has itself been converted to UTF-8
		# (e.g. the storyline of "As You Want Me" / "Come mi vuoi",
		# although it seems that one's been fixed)...
		try:
			json = json.encode("latin1").decode("utf8")
		except Exception:
			pass
		# ...or CP1252 (a review of Blunt Talk by drinkdrunkthedifferencei).
		try:
			json = json.encode("latin1").decode("cp1252")
		except Exception:
			pass
	return json

# High‑quality translation using Google Translate (no API key required)


def imdb_translate(text, lang):
	if lang != "en" and text:
		try:
			params = {
				"client": "gtx",
				"sl": "en",
				"tl": lang,
				"dt": "t",
				"q": text,
			}
			r = requests.get(
				"https://translate.googleapis.com/translate_a/single",
				params=params,
				timeout=10
			)
			if r.ok:
				# Google returns nested lists, extract the translated text
				data = r.json()
				text = "".join([part[0] for part in data[0]])
		except Exception:
			pass
	return text


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
		self["menu"].onSelectionChanged.append(self.searchPlot)
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
		# 4 = reviews page
		self.Page = 0

		self.lang = language.getLanguage().replace("_", "-")
		try:
			self.country = self.lang.split("-")[1]
		except Exception:
			self.country = None

		self["actionsOk"] = HelpableActionMap(self, "OkCancelActions",
		{
			"ok": (self.showDetails, _("Show movie and series basic details")),
			"cancel": (self.exit, _("Exit IMDb search")),
		}, -1)
		self["actionsColor"] = HelpableActionMap(self, "ColorActions",
		{
			"red": (self.exit, _("Exit IMDb search")),
			"green": (self.showMenu, _("Show list of matched movies and series")),
			"yellow": (self.showDetails, _("Show movie and series basic details")),
			"blue": (self.showExtras, _("Show movie and series extra details")),
		}, -1)
		self["actionsMovieSel"] = HelpableActionMap(self, ["MenuActions", "InfoActions"],
		{
			"menu": (self.contextMenuPressed, _("Menu")),
		}, -1)
		self["actionsIMDb"] = HelpableActionMap(self, "IMDbActions",
		{
			"poster": (self.bigPoster, _("Show a bigger poster")),
			"reviews": (self.showReviews, _("Show first page of user reviews")),
			"synopsis": (self.showSynopsis, _("Show movie and series synopsis")),
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
		self.reviews = []
		self.spoilers = False

	def pageUp(self):
		if self.hideBigPoster():
			return

		if self.Page == 0:
			self["menu"].instance.moveSelection(self["menu"].instance.moveUp)
		elif self.Page == 1:
			self["castlabel"].pageUp()
			self["detailslabel"].pageUp()
		else:  # self.Page in (2, 3, 4):
			self["extralabel"].pageUp()

	def pageDown(self):
		if self.hideBigPoster():
			return

		if self.Page == 0:
			self["menu"].instance.moveSelection(self["menu"].instance.moveDown)
		elif self.Page == 1:
			self["castlabel"].pageDown()
			self["detailslabel"].pageDown()
		else:  # self.Page in (2, 3, 4):
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

	def imdbGraphQLHeaders(self):
		headers = {
			"content-type": "application/json",
			"referer": "https://www.imdb.com/",
		}
		if self.lang:
			headers["X-Imdb-User-Language"] = self.lang
			if self.country:
				headers["X-Imdb-User-Country"] = self.country
		return headers

	def searchQueryGraphQL(self, search_term):
		search_term = json.dumps(search_term)
		types = "[MOVIE, TV"
		if config.plugins.imdb.showepisoderesults.value:
			types += ", TV_EPISODE"
		types += "]"
		return """
query Search {
  mainSearch(
    first: 25
    options: {
      searchTerm: %s
      type: TITLE
      includeAdult: true
      isExactMatch: false
      titleSearchOptions: {
        type: %s
      }
    }
  ) {
    edges {
      node {
        entity {
          ... on Title {
            id
            titleText {
              text
            }
            originalTitleText {
              text
            }
            titleType {
              text
            }
            releaseYear {
              year
              endYear
            }
            primaryImage {
              url
              width
              height
            }
            series {
              episodeNumber {
                episodeNumber
                seasonNumber
              }
              series {
                id
                titleText {
                  text
                }
                releaseYear {
                  year
                  endYear
                }
                plot {
                  plotText {
                    plainText
                  }
                }
                countriesOfOrigin {
                  countries(limit: 1) {
                    id
                  }
                }
              }
            }
            plot {
              plotText {
                plainText
              }
            }
            runtime {
              displayableProperty {
                value {
                  plainText
                }
              }
            }
            genres {
              genres {
                text
              }
            }
            countriesOfOrigin {
              countries(limit: 1) {
                id
              }
            }
          }
        }
      }
    }
  }
}
""" % (search_term, types)

	def storylineQueryGraphQL(self, title_id):
		title_id = json.dumps(title_id)
		return """
query TitleStoryline {
  title(id: %s) {
    id
    titleText {
      text
    }
    originalTitleText {
      text
    }
    titleType {
      text
    }
    releaseYear {
      year
      endYear
    }
    releaseDate {
      displayableProperty {
        value {
          plainText
        }
      }
      day
      month
      year
      country {
        text
      }
    }
    episodes {
      episodes(first: 0) {
        total
      }
      displayableSeasons(first: 0) {
        total
      }
    }
    ratingsSummary {
      aggregateRating
      voteCount
    }
    primaryImage {
      url
      width
      height
    }
    plot {
      plotText {
        plainText
      }
    }
    genres {
      genres {
        text
      }
    }
    countriesOfOrigin {
      countries {
        id
        text
      }
    }
    spokenLanguages {
      spokenLanguages {
        id
        text
      }
    }
    runtime {
      displayableProperty {
        value {
          plainText
        }
      }
    }
    certificate {
      rating
      ratingReason
      ratingsBody {
        id
      }
    }
    wins: awardNominations(first: 0, filter: { wins: WINS_ONLY }) {
      total
    }
    nominationsExcludeWins: awardNominations(first: 0, filter: { wins: EXCLUDE_WINS }) {
      total
    }
    prestigiousAwardSummary {
      nominations
      wins
      award {
        text
      }
    }
    castV2: principalCreditsV2(
      filter: { mode: "TOP_CAST" }
      useEntitlement: false
    ) {
      grouping {
        groupingId
        text
      }
      totalCredits
      credits(limit: 18) {
        name {
          id
          nameText {
            text
          }
          primaryImage {
            url
            width
            height
          }
        }
        creditedRoles(first: 1) {
          edges {
            node {
              category {
                categoryId
                text
              }
              attributes {
                text
              }
              characters(first: 3) {
                edges {
                  node {
                    name
                  }
                }
              }
            }
          }
        }
        episodeCredits(first: 0) {
          total
          yearRange {
            year
            endYear
          }
        }
      }
    }
    crewV2: principalCreditsV2(
      filter: { mode: "DEFAULT", includeAppearances: false }
      useEntitlement: false
    ) {
      totalCredits
      grouping {
        groupingId
        text
      }
      credits(limit: 3) {
        name {
          id
          nameText {
            text
          }
        }
      }
    }
    summaries: plots(first: 1, filter: {type: SUMMARY}) {
      edges {
        node {
          author
          plotText {
            plainText
          }
        }
      }
    }
    outlines: plots(first: 1, filter: {type: OUTLINE}) {
      edges {
        node {
          plotText {
            plainText
          }
        }
      }
    }
    synopses: plots(first: 1, filter: {type: SYNOPSIS}) {
      edges {
        node {
          plotText {
            plainText
          }
        }
      }
    }
    storylineKeywords: keywords(first: 5) {
      edges {
        node {
          text
        }
      }
      total
    }
    taglines(first: 1) {
      edges {
        node {
          text
        }
      }
    }
    technicalSpecifications {
      soundMixes {
        items {
          text
        }
      }
      colorations {
        items {
          text
        }
      }
      aspectRatios {
        items {
          aspectRatio
        }
      }
    }
    trivia(first: 1, filter: { spoilers: EXCLUDE_SPOILERS }) {
      edges {
        node {
          text {
            plainText
          }
        }
      }
    }
    goofs(first: 1, filter: { spoilers: EXCLUDE_SPOILERS }) {
      edges {
        node {
          text {
            plainText
          }
        }
      }
    }
    quotes(first: 1, filter: { spoilers: EXCLUDE_SPOILERS }) {
      edges {
        node {
          displayableArticle {
            body {
              plainText
            }
          }
        }
      }
    }
    connections(first: 1) {
      edges {
        node {
          associatedTitle {
            id
            releaseYear {
              year
            }
            titleText {
              text
            }
            originalTitleText {
              text
            }
            series {
              series {
                titleText {
                  text
                }
                originalTitleText {
                  text
                }
              }
            }
          }
          category {
            text
          }
        }
      }
    }
    filmingLocations(first: 1) {
      edges {
        node {
          text
        }
      }
    }
    production: companyCredits(
      first: 3
      filter: { categories: ["production"] }
    ) {
      edges {
        node {
          company {
            companyText {
              text
            }
          }
        }
      }
    }
    featuredReviews(first: 5) {
      edges {
        node {
          authorRating
          summary {
            originalText
          }
          author {
            username {
              text
            }
          }
          text {
            originalText {
              plainText
            }
          }
          submissionDate
        }
      }
    }
    reviews(first: 0) {
      total
    }
    primaryVideos {
      edges {
        node {
          contentType {
            displayName {
              value
            }
          }
          description {
            value
          }
          name {
            value
          }
          runtime {
            value
          }
          playbackURLs {
            url
          }
          timedTextTracks {
            displayName {
              value
              language
            }
            language
            url
          }
        }
      }
    }
  }
}
""" % title_id

	def reviewsQueryGraphQL(self, title_id):
		title_id = json.dumps(title_id)
		return """
query TitleReviewsRefine {
  title(id: %s) {
    reviews(first: 25) {
      edges {
        node {
          authorRating
          summary {
            originalText
          }
          author {
            username {
              text
            }
          }
          submissionDate
          spoiler
          text {
            originalText {
              plainText
            }
          }
          helpfulness {
            upVotes
            downVotes
          }
        }
      }
    }
  }
}
""" % title_id

	def imdbGraphQLSearch(self):
		return postGraphQL(self.searchQueryGraphQL(self.eventName), "Search", headers=self.imdbGraphQLHeaders())

	def imdbGraphQLTitle(self, titleId):
		return postGraphQL(self.storylineQueryGraphQL(titleId), "TitleStoryline", headers=self.imdbGraphQLHeaders())

	def imdbGraphQLReviews(self, titleId):
		return postGraphQL(self.reviewsQueryGraphQL(titleId), "TitleReviews", headers=self.imdbGraphQLHeaders())

	def downloadTitle(self, title, titleId):
		self["statusbar"].setText(_("Re-Query IMDb: %s...") % (title or titleId))
		download = self.imdbGraphQLTitle(titleId)
		download.addCallback(self.IMDBparse).addErrback(self.http_failed)

	def gotReviews(self, response):
		self["statusbar"].setText(_("Parsing reviews..."))
		self.reviewsJSON = response.content.decode("utf8")
		try:
			reviews = json.loads(self.reviewsJSON)['data']['title']['reviews']['edges']
		except Exception as e:
			self["statusbar"].setText(_("IMDb Reviews failed"))
			print("[IMDB] reviews failed:", str(e))
			return

		def makedate(date):
			try:
				return strftime(config.usage.date.full.value, strptime(date, "%Y-%m-%d"))
			except Exception:
				return date

		for review in reviews:
			review = review['node']
			try:
				helpful = review['helpfulness']['upVotes']
				total = helpful + review['helpfulness']['downVotes']
				if total:
					helpful = _("%d out of %d found this helpful.") % (helpful, total)
				else:
					helpful = ""
			except Exception:
				helpful = ""
			self.reviews.append({
				'rating': get(review, 'authorRating'),
				'title': get(review, ('summary', 'originalText')),
				'author': get(review, ('author', 'username', 'text')),
				'date': makedate(get(review, 'submissionDate')),
				'spoiler': get(review, 'spoiler'),
				'review': get(review, ('text', 'originalText', 'plainText')),
				'helpful': helpful
			})
		self["statusbar"].setText(_("IMDb Reviews parsed"))
		self.showExtras(reviews=True)

	def downloadReviews(self):
		self["statusbar"].setText(_("Downloading reviews..."))
		download = self.imdbGraphQLReviews(self.titleId)
		download.addCallback(self.gotReviews).addErrback(self.http_failed)

	def IMDBparse(self, response):
		self["statusbar"].setText(_("IMDb Re-Download completed"))
		self.json = response.content.decode("utf8")
		if self.json.startswith('{"errors'):
			self["detailslabel"].setText(_("IMDb title failed!"))
			print("[IMDb] error getting title", self.json)
			return

		Detailstext = _("No details found.")
		try:
			title = json.loads(self.json).get("data", {}).get("title", {})
		except Exception as e:
			print("[IMDb] json parse failed:", str(e))
			title = {}

		if not title:
			self["detailslabel"].setText(Detailstext)
			self["statusbar"].setText(_("IMDb details unavailable"))
			return

		self.Page = 1
		self.eventName = get(title, ("titleText", "text")) or self.eventName
		self.originalName = get(title, ("originalTitleText", "text"))
		self.titleId = get(title, "id") or self.titleId

		Titeltext = self.eventName
		if len(Titeltext) > 57:
			Titeltext = Titeltext[0:54] + "..."
		self["title"].setText(text2label(Titeltext))
		self["key_yellow"].setText(_("Details"))

		genreblock = get(title, ("genres", "genres"), [])
		genres_text = " | ".join(get(genre, "text") for genre in genreblock if get(genre, "text"))
		if genres_text:
			self.callbackGenre = genres_text

		details = []
		if genres_text:
			details.append(ngettext("Genre", "Genres", len(genreblock)) + ": " + genres_text)

		credits_by_cat = {}
		crew_label = {}
		crew = get(title, "crewV2")
		for credit in crew:
			cat = None
			credits = get(credit, "credits")
			groupId = credit["grouping"]["groupingId"]
			if groupId == "amzn1.imdb.concept.name_credit_category.ace5cb4c-8708-4238-9542-04641e7c8171":
				cat = "director"
				crew_label[cat] = ngettext("Director", "Directors", len(credits))
			elif groupId == "amzn1.imdb.concept.name_credit_category.c84ecaff-add5-4f2e-81db-102a41881fe3":
				cat = "writer"
				crew_label[cat] = ngettext("Writer", "Writers", len(credits))
			elif groupId == "amzn1.imdb.concept.name_credit_group.85198717-6c2d-481e-93a5-47858774bcce":
				cat = "creator"
				crew_label[cat] = ngettext("Creator", "Creators", len(credits))
			if cat:
				credits_by_cat[cat] = ", ".join(get(name, ("name", "nameText", "text")) for name in credits)

		for cat in ("director", "creator", "writer"):
			if cat in credits_by_cat:
				details.append(crew_label[cat] + ": " + credits_by_cat[cat])

		seasons = get(title, ("episodes", "displayableSeasons", "total"))
		if seasons:
			details.append(_("Seasons") + ": " + str(seasons))
		episodes = get(title, ("episodes", "episodes", "total"))
		if episodes:
			details.append(_("Episodes") + ": " + str(episodes))

		release = get(title, "releaseDate", {})
		if release:
			if self.lang.startswith("en"):
				release_text = get(release, ("displayableProperty", "value", "plainText"))
			else:
				release_parts = []
				if release.get("day"):
					release_parts.append(str(release.get("day")))
				if release.get("month"):
					release_parts.append(str(release.get("month")))
				if release.get("year"):
					release_parts.append(str(release.get("year")))
				release_text = ".".join(release_parts)
			country = get(release, ("country", "text"))
			if country:
				release_text += " (" + country + ")"
			if release_text:
				details.append(_("Release date") + ": " + release_text)

		countryblock = get(title, ("countriesOfOrigin", "countries"), [])
		countries = ", ".join(get(c, "text") for c in countryblock if get(c, "text"))
		if countries:
			details.append(ngettext("Country", "Countries", len(countryblock)) + ": " + countries)
		langblock = get(title, ("spokenLanguages", "spokenLanguages"), [])
		languages = ", ".join(get(ln, "text") for ln in langblock if get(ln, "text"))
		if languages:
			details.append(ngettext("Language", "Languages", len(langblock)) + ": " + languages)

		self.callbackData = "\n".join(details) if details else Detailstext

		self["detailslabel"].setText(text2label(self.callbackData))

		rating = get(title, ("ratingsSummary", "aggregateRating"))
		if rating:
			self.ratingstars = int(10 * round(rating, 1))
			self["ratinglabel"].setText("%s: %.1f / 10" % (_("IMDb rating"), rating))
			self["stars"].show()
			self["stars"].setValue(self.ratingstars)
			self["starsbg"].show()
		else:
			self["ratinglabel"].setText(_("no user rating yet"))

		cast = get(title, ("castV2", "credits"))
		if cast:
			def character(credit):
				char = get(credit, ("name", "nameText", "text"))
				characters = get(credit, ("creditedRoles", "edges", "node", "characters", "edges"))
				if characters:
					char += " " + _("as") + " " + " / ".join(get(ch, ("node", "name")) for ch in characters)
				# if credit["attributes"]:
				#	char += " (%s)" % "; ".join(get(attr, "text") for attr in name["attributes"])
				if config.plugins.imdb.showepisodeinfo.value:
					eps = get(credit, ("episodeCredits", "total"))
					years = get(credit, ("episodeCredits", "yearRange"))
					if eps:
						char += " [%s, %d" % (ngettext("{n} ep", "{n} eps", eps).format(n=eps), years["year"])
						endYear = get(years, "endYear")
						if endYear:
							char += "-" + str(endYear)
						char += "]"
				return char

			Castlist = [_("Top cast") + ":"]
			for node in cast:
				Castlist.append(character(node))
			self.castTxt = "\n ".join(Castlist)
		else:
			self.castTxt = _("No cast list found in the database.")
		self["castlabel"].setText(text2label(self.castTxt))

		self.posterurl = get(title, ("primaryImage", "url"))
		if self.posterurl:
			posterurl = self.posterurl.replace("_V1_", "_V1_QL75_UY%d_" % self["poster"].instance.size().height())
			self["statusbar"].setText(_("Downloading Movie Poster..."))
			download = downloadPage(posterurl, "/tmp/poster.jpg")
			download.addCallback(self.IMDBPoster).addErrback(self.http_failed)
		else:
			self.IMDBPoster("No Poster Art")

		awards = ""
		prest = get(title, "prestigiousAwardSummary")
		if prest:
			award = get(prest, ("award", "text"))
			wins = prest["wins"]
			noms = prest["nominations"]
			if wins:
				awards += ngettext("{n} {award} win", "{n} {award} wins", wins).format(n=wins, award=award)
			else:
				awards += ngettext("{n} {award} nomination", "{n} {award} nominations", noms).format(n=noms, award=award)
			awards += " | "
		wins = get(title, ("wins", "total"))
		noms = get(title, ("nominationsExcludeWins", "total"))
		if wins:
			awards += ngettext("{n} win", "{n} wins", wins).format(n=wins)
		if noms:
			if wins:
				awards += _(" & ")
			awards += ngettext("{n} nomination total", "{n} nominations total", noms).format(n=noms)

		outline = get(title, ("plot", "plotText", "plainText"))
		summary = get(title, ("summaries", "edges", "node", "plotText", "plainText"))
		if summary:
			if summary.startswith(outline):
				outline = ""
			summary_author = get(title, ("summaries", "edges", "node", "author"))
			if summary_author:
				summary += " \u2014" + summary_author
		synopsis = get(title, ("synopses", "edges", "node", "plotText", "plainText"))
		keywords = " | ".join(get(k, ("node", "text")) for k in get(title, ("storylineKeywords", "edges"), []))
		tagline = get(title, ("taglines", "edges", "node", "text"))
		cert = get(title, ("certificate", "rating"))
		cert_reason = get(title, ("certificate", "ratingReason"))
		if cert_reason:
			body = get(title, ("certificate", "ratingsBody", "id"))
			if body:
				cert_reason = body + ": " + cert_reason
			cert += " (" + cert_reason + ")"
		runtime_text = get(title, ("runtime", "displayableProperty", "value", "plainText"))
		color = get(title, ("technicalSpecifications", "colorations", "items", "text"))
		aspect = get(title, ("technicalSpecifications", "aspectRatios", "items", "aspectRatio"))
		sound = " | ".join(get(s, "text") for s in get(title, ("technicalSpecifications", "soundMixes", "items"), []) if get(s, "text"))
		locations = get(title, ("filmingLocations", "edges", "node", "text"))
		companies = ", ".join(get(node, ("node", "company", "companyText", "text")) for node in get(title, ("production", "edges")))
		trivia = get(title, ("trivia", "edges", "node", "text", "plainText"))
		goofs = get(title, ("goofs", "edges", "node", "text", "plainText"))
		quotes = get(title, ("quotes", "edges", "node", "displayableArticle", "body", "plainText"))

		# Translation if selected
		lang = language.getLanguage().split("_")[0]

		def safe_translate(text, lang):
			return imdb_translate(text, lang) if text else text

		if lang != "en" and config.plugins.imdb.translate_texts.value:
			outline = safe_translate(outline, lang)
			summary = safe_translate(summary, lang)
			synopsis = safe_translate(synopsis, lang)
			trivia = safe_translate(trivia, lang)
			goofs = safe_translate(goofs, lang)
			quotes = safe_translate(quotes, lang)

		connections = ""
		node = get(title, ("connections", "edges", "node"))
		if node:
			connections = get(node, ("category", "text"))
			series = get(node, ("associatedTitle", "series", "series", "titleText", "text"))
			atitle = get(node, ("associatedTitle", "titleText", "text"))
			if series:
				connections += " " + series
			if atitle:
				if series:
					connections += ":"
				connections += " " + atitle
			year = get(node, ("associatedTitle", "releaseYear", "year"))
			if year:
				connections += " (%s)" % year

		specs = []
		for label, value in (
				(_("Certificate"), cert),
				(_("Runtime"), runtime_text),
				(_("Color"), color),
				(_("Aspect ratio"), aspect),
				(_("Sound mix"), sound)):
			if value:
				specs.append(label + ": " + value)
		specs = "\n".join(specs)

		Extralist = []
		for label, value, multiline in (
				("", awards, True),
				(_("Plot"), outline, True),
				(_("Storyline"), summary, True),
				(_("Tagline"), tagline, False),
				(_("Plot keywords"), keywords, False),
				("", specs, False),
				(_("Filming locations"), locations, False),
				(_("Production companies"), companies, False),
				(_("Trivia"), trivia, False),
				(_("Goofs"), goofs, False),
				(_("Quotes"), quotes.strip(), True),
				(_("Connections"), connections, False)):
			if value:
				if label:
					label += ":\n" if multiline else ": "
				Extralist.append(label + value)
				Extralist.append("")

		reviews = get(title, ("reviews", "total"))
		if reviews:
			featured = get(title, ("featuredReviews", "edges"))
			self.morereviews = len(featured) < reviews
			Extralist.append(_("User reviews") + ": " + _("%s of %s") % (len(featured), reviews))
			if len(featured):
				Extralist.append("")
				for review in featured:
					review = review["node"]
					arating = review["authorRating"] and str(review["authorRating"]) + "/10"
					author = get(review, ("author", "username", "text"))
					date = get(review, "submissionDate")

					# Original texts
					summary_text = get(review, ("summary", "originalText"))
					body_text = get(review, ("text", "originalText", "plainText"))

					# Translate both using Google
					if lang != "en" and config.plugins.imdb.translate_texts.value:
						summary_text = safe_translate(summary_text, lang)
						body_text = safe_translate(body_text, lang)

					Extralist.append(" | ".join(x for x in (arating, author, date) if x))
					Extralist.append(summary_text)
					Extralist.append("")
					Extralist.append(body_text)
					Extralist.append("")
					Extralist.append("-" * 72)
					Extralist.append("")
				del Extralist[-3:]

		self.videos = []
		for video in get(title, ("primaryVideos", "edges")):
			video = video["node"]
			typ = get(video, ("contentType", "displayName", "value"))
			desc = get(video, ("description", "value"))
			name = get(video, ("name", "value"))
			# If the name is the same as the title, use the description if
			# it appears to be a name, otherwise just use the content type.
			if name == self.eventName:
				name = desc if desc and len(desc) < 70 and desc != name else typ
			runtime = video["runtime"]["value"]
			# Prefer HLS to MP4 to whatever (WebM at time of writing).
			url = get(sorted(get(video, ("playbackURLs")), key=lambda v:
				1 if ".m3u8" in v["url"] else 2 if ".mp4" in v["url"] else 3), "url")
			if self.eventName.lower() in name.lower():
				title = name
			else:
				title = "%s - %s" % (self.eventName, name)
			self.videos.append(("%s (%d:%02d)" % (name, runtime // 60, runtime % 60), title, url))
			for subt in get(video, "timedTextTracks"):
				self.videos.append(("   " + (get(subt, ("displayName", "value"))
											or get(subt, ("displayName", "language"))
											or get(subt, "language")),
									title, url + "&suburi=" + get(subt, "url")))

		self.extraTxt = (_("Extra Info") + "\n\n" + "\n".join(Extralist)) if Extralist else ""
		self.extra = text2label(self.extraTxt)
		self["extralabel"].setText(self.extra)
		self["extralabel"].hide()
		self["key_blue"].setText(_("Extra Info") if self.extraTxt else "")
		self.synopsisTxt = synopsis
		self.synopsis = text2label(self.synopsisTxt)
		self["VKeyIcon"].boolean = True if self.synopsis else False
		self["statusbar"].setText(_("IMDb Details parsed"))

	def showDetails(self):
		self.hideBigPoster()

		self["poster"].show()
		self["ratinglabel"].show()
		self["castlabel"].show()
		self["detailslabel"].show()

		if self.resultlist and self.Page == 0:
			title, titleId, plot = self["menu"].getCurrent()
			self.downloadTitle(title, titleId)
			self["menu"].hide()
			self.resetLabels()
			self.Page = 1

		if self.Page in (2, 3, 4):
			self["extralabel"].hide()
			if self.ratingstars > 0:
				self["starsbg"].show()
				self["stars"].show()
				self["stars"].setValue(self.ratingstars)

			self.Page = 1

	def showExtras(self, synopsis=False, reviews=False):
		self.hideBigPoster()

		if self.Page == 0 or (not synopsis and not self.extra):
			return
		if self.Page == 1:
			self["extralabel"].show()
			self["detailslabel"].hide()
			self["castlabel"].hide()
			self["poster"].hide()
			self["stars"].hide()
			self["starsbg"].hide()
			self["ratinglabel"].hide()
		if reviews:
			if self.Page == 4:
				self.spoilers = not self.spoilers
				pos = self["extralabel"].curPos
			else:
				pos = 0
			reviews = []
			for review in self.reviews:
				rating = review["rating"] and str(review["rating"]) + "/10"
				author = review["author"]
				date = review["date"]
				reviews.append(" | ".join(x for x in (rating, author, date) if x))
				reviews.append(review['title'])
				reviews.append("")
				if review['spoiler']:
					reviews.append(_("** Spoiler **"))
					reviews.append("")
				if self.spoilers or not review['spoiler']:
					reviews.append(review['review'])
					reviews.append("")
				if review['helpful']:
					reviews.append(review['helpful'])
					reviews.append("")
				reviews.append("-" * 72)
				reviews.append("")
			self.reviewsTxt = "\n".join(reviews[:-3])
			self["extralabel"].setText(text2label(self.reviewsTxt))
			self["extralabel"].setPos(pos)
			self["extralabel"].updateScrollbar()
			self.Page = 4
		else:
			self["extralabel"].setText(self.synopsis if synopsis else self.extra)
			self.Page = synopsis and 3 or 2

	def showSynopsis(self):
		self.hideBigPoster()

		if self.synopsis:
			self.showExtras(synopsis=True)

	def showReviews(self):
		self.hideBigPoster()

		if self.Page != 0 and self.morereviews:
			if not self.reviews:
				self.downloadReviews()
			else:
				self.showExtras(reviews=True)

	def contextMenuPressed(self):
		self.hideBigPoster()

		list = [
			(_("Enter search"), self.openVirtualKeyBoard),
			(_("Setup"), self.setup),
		]

		if self.saving:
			if self.savingpath is not None and self.titleId:
				list.extend((
					(_("Save current Details as .json for offline use"), self.saveJsonDetails),
					(_("Save current Details as .txt"), self.saveTxtDetails),
					(_("Save current Poster and Details as .txt"), self.savePosterTxtDetails),
				))

		if isPluginInstalled("YTTrailer"):
			list.extend((
				(_("Play Trailer"), self.openYttrailer),
				(_("Search Trailer"), self.searchYttrailer),
			))

		if isPluginInstalled("SubsSupport"):
			list.append((_("SubsSupport search"), self.searchSubsSupport))

		for video in self.videos:
			list.append((video[0], self.playVideo, video[1], video[2]))

		self.session.openWithCallback(
			self.menuCallback,
			ChoiceBox,
			title=_("IMDb Menu"),
			list=list,
		)

	def menuCallback(self, ret=None):
		if ret:
			ret[1]() if len(ret) == 2 else ret[1](ret[2], ret[3])

	def playVideo(self, name, url):
		ref = eServiceReference(4097, 0, url)
		ref.setName(name)
		self.session.open(IMDbPlayer, ref)

	def saveJsonDetails(self):
		try:
			if self.savingpath is not None:
				isave = self.savingpath + "-" + self.titleId
				open(isave + ".json", 'w').write(self.json)
				if self.reviewsJSON:
					open(isave + "-reviews.json", 'w').write(self.reviewsJSON)
				try:
					copy("/tmp/poster.jpg", isave + ".jpg")
				except OSError:
					pass
			self["statusbar"].setText(_("IMDb save completed"))
		except Exception as e:
			print('[IMDb] saveJsonDetails exception failure:', str(e))

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
		if not self.titleId:
			return None

		# save the poster.jpg (big poster if we have it, otherwise get full size)
		if self.posterurl:
			postersave = self.savingpath + "-" + self.titleId + ".jpg"
			if fileExists("/tmp/poster-big.jpg"):
				copy("/tmp/poster-big.jpg", postersave)
			else:
				# print("[IMDB] downloading poster " + self.posterurl + " to " + postersave)
				download = downloadPage(self.posterurl, postersave)
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
			"%s"    # newlines & reviews, if present
		) % (
			self.eventName,
			self["ratinglabel"].getText(),
			self.callbackData,
			self.castTxt,
			self.extraTxt,
			self.synopsisTxt and "\n".join(("", _("Synopsis"), "", self.synopsisTxt, "")) or "",
			self.reviewsTxt and "\n".join(("", _("User reviews"), "", self.reviewsTxt, "")) or ""
		)

	def openYttrailer(self):
		try:
			from Plugins.Extensions.YTTrailer.plugin import YTTrailer, baseEPGSelection__init__
		except ImportError:
			pass
		if baseEPGSelection__init__ is None:
			return

		ytTrailer = YTTrailer(self.session)
		ytTrailer.showTrailer(self.eventName)

	def searchYttrailer(self):
		try:
			from Plugins.Extensions.YTTrailer.plugin import YTTrailerList, baseEPGSelection__init__
		except ImportError:
			pass
		if baseEPGSelection__init__ is None:
			return

		self.session.open(YTTrailerList, self.eventName)

	def searchSubsSupport(self):
		try:
			from Plugins.Extensions.SubsSupport.subtitles import E2SubsSeeker, SubsSearch, initSubsSettings
		except ImportError:
			self["statusbar"].setText(_("SubsSupport import failed"))
			return

		settings = initSubsSettings().search
		titles = [self.eventName]
		if self.originalName != self.eventName:
			titles.append(self.originalName)
		self.session.open(SubsSearch, E2SubsSeeker(self.session, settings), settings, searchTitles=titles, standAlone=True)

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
		self.json = self.posterurl = None
		self.castTxt = self.extraTxt = self.synopsisTxt = self.reviewsTxt = ""
		self.extra = self.synopsis = ""
		self.videos = []
		self.morereviews = False
		self.reviews = []
		self.spoilers = False
		safeRemove("/tmp/poster.jpg", "/tmp/poster-big.jpg")
		if not isinstance(self.eventName, str):
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
				self["statusbar"].setText(_("localpath is no longer supported."))
				return

			if self.imdbId:
				if self.imdbId.startswith("tt") and self.imdbId[2:].isdigit():
					self.downloadTitle(self.eventName, self.imdbId)
				else:
					self["statusbar"].setText(_("Ignoring invalid imdbId: %s") % self.imdbId)
				return

		if self.eventName:
			self["statusbar"].setText(_("Query IMDb: %s") % self.eventName)
			download = self.imdbGraphQLSearch()
			download.addCallback(self.IMDBqueryGraphQL).addErrback(self.http_failed)

		else:
			self["statusbar"].setText(_("Couldn't get event name"))

	def IMDBqueryGraphQL(self, response):
		self["statusbar"].setText(_("IMDb Download completed"))
		try:
			data = json.loads(response.content.decode("utf8"))
			searchresults = data["data"]["mainSearch"]["edges"]
		except Exception as e:
			self["detailslabel"].setText(_("IMDb query failed!"))
			print("[IMDB] GraphQL search parse failed:", str(e), "payload=", response.content[:500])
			return

		self.resultlist = []
		titles = {}
		for edge in searchresults:
			x = get(edge, ("node", "entity"), {})
			series = get(x, ("series", "series"))
			if series:
				if not config.plugins.imdb.showepisoderesults.value:
					continue
				sid = get(series, "id")
				if sid in titles:
					i = titles[sid]
					for t in titles:
						if titles[t] >= i:
							titles[t] += 1
				else:
					title = get(series, ("titleText", "text"))
					year = get(series, ("releaseYear", "year"))
					if year:
						year_text = str(year)
						endYear = get(series, ("releaseYear", "endYear"))
						if endYear:
							year_text += "-%s" % endYear
					country = get(series, ("countriesOfOrigin", "countries", "id"))
					extras = []
					if year:
						extras.append(year_text)
					if country:
						extras.append(country)
					if extras:
						title += " (%s)" % "; ".join(extras)
					plot = get(series, ("plot", "plotText", "plainText"))
					self.resultlist.append((title, sid, plot))
					i = titles[sid] = len(self.resultlist)
				title = "- "
				e = get(x, ("series", "episodeNumber", "episodeNumber"))
				if e:
					s = get(x, ("series", "episodeNumber", "seasonNumber"))
					title += _("S%d E%d - ") % (s, e)
			else:
				title = ""
				i = len(self.resultlist)
			title += get(x, ("titleText", "text"))
			country = get(x, ("countriesOfOrigin", "countries", "id"))
			year = get(x, ("releaseYear", "year"))
			endYear = get(x, ("releaseYear", "endYear"))
			if config.plugins.imdb.showlongmenuinfo.value:
				typ = get(x, ("titleType", "text")) or ""
				genres = "/".join(g["text"] for g in get(x, ("genres", "genres"), []))
				runtime = get(x, ("runtime", "displayableProperty", "value", "plainText"))
			else:
				typ = genres = runtime = ""
			extras = []
			if year:
				year_text = str(year)
				if endYear:
					year_text += "-%s" % endYear
				extras.append(year_text)
			if country:
				extras.append(country)
			if runtime:
				extras.append(runtime)
			if typ:
				extras.append(typ)
			if genres:
				extras.append(genres)
			if extras:
				title += " (%s)" % "; ".join(extras)
			plot = get(x, ("plot", "plotText", "plainText"))
			self.resultlist.insert(i, (title, get(x, "id"), plot))

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

	def searchPlot(self):
		cur = self["menu"].getCurrent()
		if cur:
			plot_text = cur[2]  # original text
			if config.plugins.imdb.translate_texts.value:
				lang = language.getLanguage().split("_")[0]  # UI language
				if lang != "en":
					if plot_text:
						plot_text = imdb_translate(plot_text, lang)
			self["statusbar"].setText(plot_text)

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
		# print("[IMDB]", text)
		self["statusbar"].setText(text)
		return failure

	def IMDBPoster(self, failed, big=False):
		self["statusbar"].setText(_("IMDb Details parsed"))
		if failed:
			filename = resolveFilename(SCOPE_PLUGINS, "Extensions/IMDb/no_poster.png")
		else:
			filename = big and "/tmp/poster-big.jpg" or "/tmp/poster.jpg"
		self.picload.setPara((self["poster"].instance.size().width(), self["poster"].instance.size().height(), 1, 1, False, 1, "#00000000"))
		self.picload.startDecode(filename)

	def paintPosterPixmapCB(self, picInfo=None):
		ptr = self.picload.getData()
		if ptr is not None:
			self["poster"].instance.setPixmap(ptr)

	def bigPoster(self):
		if not self.posterurl or self.poster_pos:
			return
		localfile = "/tmp/poster-big.jpg"
		if fileExists(localfile):
			self.IMDBPosterBig()
			return
		# Get a poster size to fit the skin.
		posterurl = self.posterurl.replace("_V1_", "_V1_QL75_UY%d_" % self.instance.size().height())
		self["statusbar"].setText(_("Downloading Movie Poster..."))
		# print("[IMDB] downloading poster " + posterurl + " to " + localfile)
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


class IMDbPlayer(MoviePlayer):
	def __init__(self, session, service):
		MoviePlayer.__init__(self, session, service)
		self.skinName = "MoviePlayer"

	def leavePlayer(self):
		self.close()

	def doEofInternal(self, playing):
		self.close()

	def showMovies(self):
		pass


class IMDbLCDScreen(Screen):
	skin = """
	<screen position="0,0" size="132,64" title="IMDB Plugin">
		<widget name="headline" position="4,0" size="128,22" font="Regular;20"/>
		<widget source="parent.title" render="Label" position="6,26" size="120,34" font="Regular;14"/>
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session, parent)
		self["headline"] = Label(_("IMDb Plugin"))


class IMDbSetup(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, "imdb", plugin="Extensions/IMDb", PluginLanguageDomain="IMDb")
		self.setTitle(_("IMDb Setup"))

	def keySave(self):
		self.saveAll()
		for pl in pluginlist:
			if not pl[0].value:
				for plugin in plugins.getPlugins(pl[1].where):
					if plugin is pl[1]:
						plugins.removePlugin(plugin)

		plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
		self.close()


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
	items = [PluginDescriptor(name=_("IMDb search") + "...",
			description=_("Search for details from the Internet Movie Database"),
			where=PluginDescriptor.WHERE_EVENTINFO,
			fnc=eventinfo,
			needsRestart=False,
			),
		]

	items += [pl[1] for pl in pluginlist if pl[0].value]

	return items
