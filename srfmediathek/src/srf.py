# -*- coding: UTF-8 -*-
from os import mkdir, unlink, path
from datetime import datetime, timedelta
from json import loads
import xml.etree.ElementTree as Et
import re
import requests
from Components.ActionMap import ActionMap
from Components.AVSwitch import AVSwitch
from Components.ConfigList import ConfigListScreen
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigSelection, ConfigYesNo, configfile
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Components.Sources.List import List
from enigma import eServiceReference, ePicLoad, gPixmapPtr, getDesktop, addFont
from Screens.InfoBarGenerics import setResumePoint
from Screens.InfoBar import MoviePlayer
from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from six import ensure_str
from six.moves.urllib.parse import quote_plus
from twisted.internet.reactor import callInThread
config.plugins.SRF = ConfigSubsection()
config.plugins.SRF.SaveResumePoint = ConfigYesNo(default=False)
config.plugins.SRF.AUTOPLAY = ConfigYesNo(default=False)
PLUGINPATH = "/usr/lib/enigma2/python/Plugins/Extensions/SRFMediathek/"
FHD = getDesktop(0).size().height() > 720
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0"
TMPIC = "/tmp/cover/bild.jpg"
SKINFILE = PLUGINPATH + "skin_FHD.xml" if FHD else PLUGINPATH + "skin_HD.xml"
FONT = "/usr/share/fonts/LiberationSans-Regular.ttf"
if not path.exists(FONT):
    FONT = "/usr/share/fonts/nmsbd.ttf"
addFont(FONT, "SRegular", 100, False)
ColorList = [("default,#1a104485,#3D104485,#1aC0C0C0", "Trans-BrightBlue"), ("default,#050a1232,#1502050e,#05192d7c", "Trans-DarkBlue"), ("default,#05000000,#15000000,#606060", "Trans-BlackGray"), ("default,#05000000,#15000000,#ffff00", "Trans-BlackYellow"), ("default,#1a746962,#1502050e,#1a746962", "Trans-BrownBlue"), ("MiniTV,#104485,#0c366a,#C0C0C0", "BrightBlue MiniTV"), ("MiniTV,#0a1232,#02050e,#192d7c", "DarkBlue MiniTV"), ("MiniTV,#000000,#080808,#606060", "BlackGray MiniTV"), ("MiniTV,#000000,#080808,#ffff00", "BlackYellow MiniTV"), ("MiniTV,#746962,#02050e,#746962", "BrownBlue MiniTV")]
config.plugins.SRF.SkinColor = ConfigSelection(default="default,#050a1232,#1502050e,#05192d7c", choices=ColorList)


def readskin():
    cf = config.plugins.SRF.SkinColor.value.split(",")
    skin = ""
    try:
        with open(SKINFILE, "r") as f:
            root = Et.parse(f).getroot()
        for element in root:
            if element.tag == "screen" and element.attrib["name"] == cf[0]:
                skin = ensure_str(Et.tostring(element))
    except (IOError, Et.ParseError):
        return ""
    return skin.strip().replace("{col1}", cf[1]).replace("{col2}", cf[2]).replace("{col3}", cf[3]).replace("{picpath}", PLUGINPATH + "img/")


def geturl(url):
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8", "Accept-Language": "de,en-US;q=0.7,en;q=0.3", "Accept-Encoding": "gzip, deflate"}, verify=False)
        r.raise_for_status()
        return r.content
    except requests.RequestException:
        return ""


def sortList(txt):
    return sorted(txt, key=lambda text: int(re.compile(r"(\d+)x", re.DOTALL).findall(text[0])[0]) if re.compile(r"(\d+)x", re.DOTALL).findall(str(text[0])) else 0, reverse=True)


class SRFMediathek(Screen):
    def __init__(self, session):
        skin = readskin()
        self.skin = skin
        Screen.__init__(self, session)
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "ChannelSelectBaseActions", "MovieSelectionActions"], {"contextMenu": self.SRFSetup, "red": self.close, "blue": self.Home, "up": self.up, "down": self.down, "left": self.left, "right": self.right, "nextBouquet": self.p_up, "prevBouquet": self.p_down, "ok": self.ok, "cancel": self.exit}, -1)
        self["movielist"] = List()
        self["cover"] = Pixmap()
        self["handlung"] = ScrollLabel()
        self.HISTORY = [("MENU", "")]
        self["DownloadLabel"] = ScrollLabel()
        self["PluginName"] = ScrollLabel("Play SRF Mediathek v0.5 Beta")
        self["progress"] = ProgressBar()
        self["progress"].hide()
        self.DL_File = None
        if not path.exists("/tmp/cover/"):
            mkdir("/tmp/cover/")
        self.onLayoutFinish.append(self.HauptMenu)

    def SRFSetup(self):
        self.session.open(SRFConfigScreen)

    def HauptMenu(self, index="0"):
        self.searchtxt = ""
        menu = [("MENU", "SRF Mediathek - Start", "https://il.srgssr.ch/integrationlayer/2.0/srf/page/landingPage/byProduct/PLAY_VIDEO?isPublished=true&vector=APPPLAY", "", PLUGINPATH + "/img/" + "home.png", ""), ("MENU", "Kategorien", "https://il.srgssr.ch/integrationlayer/2.0/srf/topicList/tv?vector=APPPLAY", "", PLUGINPATH + "/img/" + "endecken.png", ""), ("MENU", "A-Z", "https://il.srgssr.ch/integrationlayer/2.0/srf/showList/tv/alphabetical?pageSize=unlimited&vector=APPPLAY", "", PLUGINPATH + "/img/" + "az.png", ""), ("Programm3", "Sendung verpasst", "Programm3", "", PLUGINPATH + "/img/" + "programm.png", ""), ("MENU", "Am meisten gesuchte", "https://il.srgssr.ch/integrationlayer/2.0/srf/showList/tv/mostClickedSearchResults?vector=portalplay", "", PLUGINPATH + "/img/" + "mostClick.png", ""), ("Suche", "Suche", "", "", PLUGINPATH + "/img/" + "suche.png", "")]
        self["movielist"].setList(menu)
        self["movielist"].setIndex(int(index))
        self.infos()

    def ok(self):
        if self["movielist"].getCurrent()[0] == "Suche":
            self.session.openWithCallback(self.search, VirtualKeyBoard, title="SRF Mediathek Suche")
        elif self["movielist"].getCurrent()[0] == "PLAY":
            self.Play()
        else:
            Index = self["movielist"].getIndex()
            url = self["movielist"].getCurrent()[2]
            if self["movielist"].getCurrent()[0] == "MENU":
                self.Widgets(url)
            elif self["movielist"].getCurrent()[0] == "WEITER":
                self.Widgets(url)
            elif self["movielist"].getCurrent()[0] == "Programm3":
                self.Programm3()
            else:
                return
            self.HISTORY.append((url, Index))

    def Home(self):
        self.HISTORY = [("MENU", "")]
        self.HauptMenu()

    def exit(self):
        if len(self.HISTORY) > 1:
            Index = self.HISTORY[-1][1]
            self.HISTORY.pop()
            url = self.HISTORY[-1][0]
            if url.startswith("http"):
                self.Widgets(url, Index)
            elif url == "MENU":
                self.HauptMenu(Index)
            elif url == "Programm3":
                self.Programm3(Index)
        else:
            if path.exists(TMPIC):
                unlink(TMPIC)
            self.close()

    def Programm3(self, index="0"):
        now = datetime.now()
        liste = []
        for i in range(0, 7):
            start = now + timedelta(-i)
            if i == 0:
                title = "HEUTE"
            elif i == 1:
                title = "GESTERN"
            else:
                title = start.strftime("%d.%m.%Y")
            url = "https://il.srgssr.ch/integrationlayer/2.0/srf/mediaList/video/episodesByDate/%s?pageSize=40&vector=APPPLAY" % start.strftime("%Y-%m-%d")
            liste.append(("WEITER", title, ensure_str(url), "", "", ""))
        self["movielist"].setList(liste)
        self["movielist"].setIndex(int(index))
        self.infos()

    def search(self, search):
        if search:
            self.searchtxt = search
            url = "https://il.srgssr.ch/integrationlayer/2.0/srf/searchResultMediaList?q=%s&sortBy=default&includeSuggestions=false&includeAggregations=false&pageSize=40&vector=APPPLAY" % quote_plus(self.searchtxt)
            Index = self["movielist"].getIndex()
            self.HISTORY.append((url, Index))
            self.Widgets(url, index="0")

    def Widgets(self, url2, index="0"):
        liste = []
        data = geturl(url2)
        if data:
            data = loads(ensure_str(data))
        else:
            self.HISTORY.pop()
            return
        if data.get("topicList"):
            data2 = data.get("topicList")
        elif data.get("showList"):
            data2 = data.get("showList")
        elif data.get("sectionList"):
            data2 = data.get("sectionList")
        elif data.get("mediaList"):
            data2 = data.get("mediaList")
        elif data.get("searchResultMediaList"):
            data2 = data.get("searchResultMediaList")
        else:
            self.session.open(MessageBox, "Kein Eintrag vorhanden", MessageBox.TYPE_INFO)
            self.HISTORY.pop()
            return

        for js in data2:
            url = ""
            title = js.get("title", "")
            if js.get("urn"):
                url = js.get("urn", "")
                if "video" in url or "audio" in url:
                    url = "https://il.srgssr.ch/integrationlayer/2.1/mediaComposition/byUrn/%s?onlyChapters=false&vector=APPPLAY" % url
                elif "show" in url:
                    url = "https://il.srgssr.ch/integrationlayer/2.0/mediaList/latest/byShowUrn/urn:srf:%s?pageSize=40&vector=APPPLAY" % url
                elif "topic" in url:
                    url = "https://il.srgssr.ch/integrationlayer/2.0/srf/page/byTopicUrn/%s?isPublished=true&vector=APPPLAY" % url
            elif js.get("id"):
                if js.get("sectionType") == "MediaSection":
                    url = "https://il.srgssr.ch/integrationlayer/2.0/srf/section/mediaSection/%s?isPublished=true&vector=APPPLAY" % js.get("id")
                if js.get("sectionType") == "ShowSection":
                    url = "https://il.srgssr.ch/integrationlayer/2.0/srf/section/showSection/%s?isPublished=true&vector=APPPLAY" % js.get("id")
                if js.get("representation"):
                    js = js.get("representation", "")
                if "HeroStage" in js.get("name", ""):
                    title = "Stage"
                elif js.get("properties"):
                    js = js.get("properties", "")
                if js.get("title"):
                    title = js.get("title")
            if url.startswith("http") and not title:
                title = ".."
            duration = js.get("duration", "")
            if str(duration).isdigit():
                duration = str(timedelta(seconds=int(duration // 1000)))
            img = str(js.get("imageUrl", ""))
            desc = js.get("lead") + "\n" if js.get("lead") else ""
            desc += js.get("description", "")
            if not url.startswith("http"):
                continue
            if "video" in url or "audio" in url:
                liste.append(("PLAY", ensure_str(title), ensure_str(url), ensure_str(desc), ensure_str(img), duration))
            else:
                liste.append(("WEITER", ensure_str(title), ensure_str(url), ensure_str(desc), ensure_str(img), duration))
        if data.get("next"):
            liste.append(("WEITER", "NextPage", data.get("next"), "", PLUGINPATH + "/img/" + "nextpage.png", ""))
        if liste:
            self["movielist"].setList(liste)
            self["movielist"].setIndex(int(index))
            self.infos()

    def Play(self):
        url = self["movielist"].getCurrent()[2]
        html = ensure_str(geturl(url))
        if "drmList" in html:
            self.session.open(MessageBox, "DRM Geschützt kann nicht abgespielt werden", MessageBox.TYPE_INFO)
            return
        liste = []
        link = re.compile('media_streaming_quality" : "HD".*?"media_url" : "([^"]+)', re.DOTALL).findall(html)
        if not link:
            link = re.compile('media_url" : "([^"]+)', re.DOTALL).findall(html)
        if link:
            link = link[0]
            if ".mp3" in link:
                liste.append(("MP3", link))
            elif link.startswith("http"):
                html2 = ensure_str(geturl(link))
                m3u = re.compile(r"#EXT-X-STREAM.*?RESOLUTION=(\d+x+\d+).*?\n(.*?)\n", re.DOTALL).findall(html2)
                for q, url in m3u:
                    liste.append(("HLS | %s" % (q), link.split("master")[0] + url.strip()))
            liste = sortList(liste)
            if config.plugins.SRF.AUTOPLAY.value and liste:
                self.Play2(liste[0])
            elif len(liste) > 1:
                self.session.openWithCallback(self.Play2, ChoiceBox, title="Wiedergabe starten?", list=liste)
            elif liste:
                self.Play2(liste[0])
        else:
            self.session.open(MessageBox, "Kein Eintrag vorhanden", MessageBox.TYPE_INFO)

    def Play2(self, url):
        url = url and url[1]
        if url:
            sref = eServiceReference(4097, 0, ensure_str(url))
            sref.setName(self["movielist"].getCurrent()[1])
            self.session.open(MoviePlayer2, sref)

    def up(self):
        if self["movielist"]:
            self["movielist"].up()
            self.infos()

    def down(self):
        if self["movielist"]:
            self["movielist"].down()
            self.infos()

    def left(self):
        if self["movielist"]:
            self["movielist"].pageUp()
            self.infos()

    def right(self):
        if self["movielist"]:
            self["movielist"].pageDown()
            self.infos()

    def p_up(self):
        self["handlung"].pageUp()

    def p_down(self):
        self["handlung"].pageDown()

    def infos(self):
        handlung = self["movielist"].getCurrent()[3]
        self["handlung"].setText(handlung)
        self.show_cover()

    def show_cover(self):
        if self["movielist"].getCurrent() is not None:
            url = self["movielist"].getCurrent()[4]
            if url.startswith("http"):
                callInThread(self.getimage, url)
            elif url.startswith("/usr/"):
                self.get_cover(url)
            else:
                img = PLUGINPATH + "/img/nocover.png"
                self.get_cover(img)

    def getimage(self, url):
        try:
            data = geturl(url)
            with open(TMPIC, "wb") as f:
                f.write(data)
            self.get_cover(TMPIC)
        except OSError:
            pass

    def get_cover(self, img):
        picload = ePicLoad()
        self["cover"].instance.setPixmap(gPixmapPtr())
        scale = AVSwitch().getFramebufferScale()
        size = self["cover"].instance.size()
        picload.setPara((size.width(), size.height(), scale[0], scale[1], False, 1, "#FF000000"))
        if picload.startDecode(img, 0, 0, False) == 0:
            ptr = picload.getData()
            if ptr is not None:
                self["cover"].instance.setPixmap(ptr)
                self["cover"].show()


class MoviePlayer2(MoviePlayer):
    ENABLE_RESUME_SUPPORT = True

    def __init__(self, session, service):
        MoviePlayer.__init__(self, session, service)
        self.skinName = "MoviePlayer"

    def up(self):
        pass

    def down(self):
        pass

    def leavePlayer(self):
        if config.plugins.SRF.SaveResumePoint.value:
            setResumePoint(self.session)
        self.close()

    def leavePlayerOnExit(self):
        self.leavePlayer()

    def doEofInternal(self, playing):
        if not playing or not self.execing:
            return
        self.close()


class SRFConfigScreen(ConfigListScreen, Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.title = "Einstellungen"
        self.session = session
        self.skinName = ["Setup"]
        self["key_red"] = StaticText("Abbrechen")
        self["key_green"] = StaticText("Speichern")
        self["setupActions"] = ActionMap(["SetupActions", "ColorActions"], {"cancel": self.cancel, "red": self.cancel, "green": self.save}, -2)
        ConfigListScreen.__init__(self, [], session=session)
        self.ConfigList()

    def ConfigList(self):
        self["config"].list = [getConfigListEntry("Skin", config.plugins.SRF.SkinColor), getConfigListEntry("Letzte Abspielposition speichern", config.plugins.SRF.SaveResumePoint), getConfigListEntry("AutoPlay", config.plugins.SRF.AUTOPLAY)]

    def save(self):
        self.keySave()
        configfile.save()
        self.close()

    def cancel(self):
        self.close()
