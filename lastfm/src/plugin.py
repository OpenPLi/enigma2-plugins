from enigma import eTimer, loadPic, getDesktop

from Screens.Screen import Screen
from Screens.HelpMenu import HelpableScreen
from Components.Pixmap import Pixmap, MovingPixmap
from Components.Label import Label
from Components.MenuList import MenuList
from Screens.InputBox import InputBox

from Components.ActionMap import ActionMap
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigYesNo, ConfigText, ConfigSelection, ConfigPassword
from Plugins.Plugin import PluginDescriptor

from StreamPlayer import StreamPlayer
from LastFMConfig import LastFMConfigScreen
from LastFM import LastFM
from urllib2 import quote as urllib2_qoute
from twisted.web.client import downloadPage
from os import remove as os_remove, system as os_system
from random import randrange

# for localized messages
from . import _


###############################################################################
plugin_path = ""
streamplayer = False
lastfm_pluginversion = "0.6.0"
###############################################################################

config.plugins.LastFM = ConfigSubsection()

config.plugins.LastFM.menu = ConfigSelection(default="plugin", choices=[("plugin", _("Plugin menu")), ("extensions", _("Extensions menu"))])
config.plugins.LastFM.name = ConfigText(default=_("Last.FM"), fixed_size=False, visible_width=20)
config.plugins.LastFM.description = ConfigText(default=_("Listen to Last.FM Internet Radio"), fixed_size=False, visible_width=80)
config.plugins.LastFM.showcoverart = ConfigYesNo(default=True)
config.plugins.LastFM.username = ConfigText("user", fixed_size=False)
config.plugins.LastFM.password = ConfigPassword(default="passwd", fixed_size=False)
config.plugins.LastFM.timeoutstatustext = ConfigInteger(3, limits=(0, 10))
config.plugins.LastFM.timeouttabselect = ConfigInteger(2, limits=(0, 10))
config.plugins.LastFM.metadatarefreshinterval = ConfigInteger(1, limits=(0, 100))
config.plugins.LastFM.recommendedlevel = ConfigInteger(3, limits=(0, 100))
config.plugins.LastFM.sendSubmissions = ConfigYesNo(default=False)

config.plugins.LastFM.useproxy = ConfigYesNo(default=False)
config.plugins.LastFM.proxyport = ConfigInteger(6676, limits=(1, 65536))

config.plugins.LastFM.sreensaver = ConfigSubsection()
config.plugins.LastFM.sreensaver.use = ConfigYesNo(default=True)
config.plugins.LastFM.sreensaver.wait = ConfigInteger(30, limits=(0, 1000))
config.plugins.LastFM.sreensaver.showcoverart = ConfigYesNo(default=True)
config.plugins.LastFM.sreensaver.coverartanimation = ConfigYesNo(default=True)
config.plugins.LastFM.sreensaver.coverartspeed = ConfigInteger(10, limits=(0, 100))
config.plugins.LastFM.sreensaver.coverartinterval = ConfigInteger(10, limits=(0, 100))

###############################################################################


def main(session, **kwargs):
    global streamplayer
    if streamplayer is not False:
        streamplayer.setSession(session)
    else:
        streamplayer = StreamPlayer(session)

    session.openWithCallback(LastFMScreenMainCB, LastFMScreenMain, streamplayer)


def LastFMScreenMainCB():
    pass


def startScrobbler(reason, **kwargs):
    if "session" in kwargs and config.plugins.LastFM.sendSubmissions.value:
        global streamplayer
        if streamplayer is False:
            streamplayer = StreamPlayer(kwargs["session"])
        else:
            streamplayer.setSession(kwargs["session"])

        from scrobbler import EventListener
        evl = EventListener(kwargs["session"], streamplayer)
        evl.startListenToEvents()


def Plugins(path, **kwargs):
    global plugin_path
    plugin_path = path

    list = [PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc=startScrobbler)]

    if config.plugins.LastFM.menu.value == "plugin":
        list.append(PluginDescriptor(
            name=config.plugins.LastFM.name.value,
            description=config.plugins.LastFM.description.value + " " + _("Ver.") + " " + lastfm_pluginversion,
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon="plugin.png",
            fnc=main)
            )
    else:
        list.append(PluginDescriptor(
            name=config.plugins.LastFM.name.value,
            description=config.plugins.LastFM.description.value + " " + _("Ver.") + " " + lastfm_pluginversion,
            where=PluginDescriptor.WHERE_EXTENSIONSMENU,
            fnc=main)
            )

    return list

###############################################################################


class LastFMScreenMain(Screen, HelpableScreen, LastFM):
    skin = """
        <screen name="LastFM" position="center,center" size="600,440" title="%s" >

            <widget name="artist" position="0,5" size="100,30" valign=\"center\" halign=\"left\" zPosition=\"2\"  foregroundColor=\"white\" font=\"Regular;18\" />
            <widget name="album" position="0,45" size="100,30" valign=\"center\" halign=\"left\" zPosition=\"2\"  foregroundColor=\"white\" font=\"Regular;18\" />
            <widget name="track" position="0,85" size="100,30" valign=\"center\" halign=\"left\" zPosition=\"2\"  foregroundColor=\"white\" font=\"Regular;18\" />

            <widget name="info_artist" position="105,5" size="300,30" valign=\"center\" halign=\"left\" zPosition=\"2\"  foregroundColor=\"white\" font=\"Regular;18\" />
            <widget name="duration" position="420,5" size="60,30" valign=\"center\" halign=\"right\" zPosition=\"2\"  foregroundColor=\"white\" font=\"Regular;18\" />
            <widget name="info_album" position="105,45" size="370,30" valign=\"center\" halign=\"left\" zPosition=\"2\"  foregroundColor=\"white\" font=\"Regular;18\" />
            <widget name="info_track" position="105,85" size="370,30" valign=\"center\" halign=\"left\" zPosition=\"2\"  foregroundColor=\"white\" font=\"Regular;18\" />
            <widget name="info_cover" position="484,5" size="116,116" />

            <widget name="tablist" position="0,140" size="210,205" scrollbarMode="showOnDemand" />
            <widget name="streamlist" position="220,140" size="380,205" scrollbarMode="showOnDemand" />

            <widget name="button_red" position="0,360" size="140,40" valign=\"center\" halign=\"center\" zPosition=\"3\" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" font=\"Regular;18\" />
            <widget name="button_green" position="140,360" size="140,40" valign=\"center\" halign=\"center\" zPosition=\"3\" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" font=\"Regular;18\"/>
            <widget name="button_yellow" position="280,360" size="140,40" valign=\"center\" halign=\"center\" zPosition=\"3\" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" font=\"Regular;18\" />
            <widget name="button_blue" position="420,360" size="140,40" valign=\"center\" halign=\"center\" zPosition=\"3\" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" font=\"Regular;18\" />
            <ePixmap pixmap="skin_default/buttons/red.png" position="0,360" zPosition="2" size="140,40" transparent="1" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/green.png" position="140,360" zPosition="2" size="140,40" transparent="1" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/yellow.png" position="280,360" zPosition="2" size="140,40" transparent="1" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/blue.png" position="420,360" zPosition="2" size="140,40" transparent="1" alphatest="on" />
            <ePixmap position="570,370" size="35,25" pixmap="skin_default/buttons/key_menu.png" alphatest="on" />
            <widget name="infolabel" position="10,410" size="500,20" valign=\"center\" halign=\"left\" zPosition=\"2\"  foregroundColor=\"white\" font=\"Regular;16\" />
        </screen>""" % (config.plugins.LastFM.name.value + " " + _("Ver.") + " " + lastfm_pluginversion) # title

    noCoverArtPNG = "/usr/share/enigma2/skin_default/no_coverArt.png"

    def __init__(self, session, streamplayer, args=0):
        self.skin = LastFMScreenMain.skin
        Screen.__init__(self, session)
        HelpableScreen.__init__(self)
        LastFM.__init__(self)
        self.session = session
        self.streamplayer = streamplayer#StreamPlayer(session)
        self.streamplayer.onStateChanged.append(self.onStreamplayerStateChanged)
        self.imageconverter = ImageConverter(116, 116, self.setCoverArt)
        Screen.__init__(self, session)

        self.tabs = [(_("Personal Stations"), self.loadPersonalStations), (_("Global Tags"), self.loadGlobalTags), (_("Top Tracks"), self.loadTopTracks), (_("Recent Tracks"), self.loadRecentTracks), (_("Loved Tracks"), self.loadLovedTracks), (_("Banned Tracks"), self.loadBannedTracks), (_("Friends"), self.loadFriends), (_("Neighbours"), self.loadNeighbours)
                   ]
        tablist = []
        for tab in self.tabs:
            tablist.append((tab[0], tab))
        self.tablist = MenuList(tablist)
        self.tablist.onSelectionChanged.append(self.action_TabChanged)

        self["artist"] = Label(_("Artist") + ":")
        self["duration"] = Label("-00:00")
        self["album"] = Label(_("Album") + ":")
        self["track"] = Label(_("Track") + ":")

        self["info_artist"] = Label("N/A")
        self["info_album"] = Label("N/A")
        self["info_track"] = Label("N/A")
        self["info_cover"] = Pixmap()

        self["tablist"] = self.tablist
        self["streamlist"] = MenuList([])

        self["button_red"] = Label(_("Play"))
        self["button_green"] = Label(_("Skip"))
        self["button_yellow"] = Label(_("Love"))
        self["button_blue"] = Label(_("Ban"))
        self["infolabel"] = Label("")

        self["actions"] = ActionMap(["InfobarChannelSelection", "WizardActions", "DirectionActions", "MenuActions", "ShortcutActions", "GlobalActions", "HelpActions", "NumberActions"],
            {
             "ok": self.action_ok,
             "back": self.action_exit,
             "red": self.action_startstop,
             "green": self.skipTrack,
             "yellow": self.love,
             "blue": self.banTrack,
             "historyNext": self.action_nextTab,
             "historyBack": self.action_prevTab,

             "menu": self.action_menu,
             }, -1)

        self.helpList.append((self["actions"], "WizardActions", [("ok", _("Switch to selected Station"))]))
        self.helpList.append((self["actions"], "InfobarChannelSelection", [("historyNext", _("Select next Tab"))]))
        self.helpList.append((self["actions"], "InfobarChannelSelection", [("historyBack", _("Select prev Tab"))]))
        self.helpList.append((self["actions"], "InfobarChannelSelection", [("switchChannelDown", _("Next Selection"))]))
        self.helpList.append((self["actions"], "InfobarChannelSelection", [("switchChannelUp", _("Previous Selection"))]))
        self.helpList.append((self["actions"], "InfobarChannelSelection", [("zapDown", _("Page forward Selections"))]))
        self.helpList.append((self["actions"], "InfobarChannelSelection", [("zapUp", _("Page backward Selections"))]))
        self.helpList.append((self["actions"], "ShortcutActions", [("red", _("Start/stop streaming"))]))
        self.helpList.append((self["actions"], "ShortcutActions", [("green", _("Skip current Track"))]))
        self.helpList.append((self["actions"], "ShortcutActions", [("yellow", _("Mark Track as loved"))]))
        self.helpList.append((self["actions"], "ShortcutActions", [("blue", _("Ban Track, never play"))]))
        self.helpList.append((self["actions"], "MenuActions", [("menu", _("Open") + " " + _("Setup"))]))
        self.helpList.append((self["actions"], "WizardActions", [("back", _("Quit") + " " + config.plugins.LastFM.name.value)]))

        self.onLayoutFinish.append(self.initLastFM)
        self.onLayoutFinish.append(self.tabchangedtimerFired)
        self.onLayoutFinish.append(self.setCoverArt)

        self.guiupdatetimer = eTimer()
        self.guiupdatetimer.timeout.get().append(self.guiupdatetimerFired)
        self.guiupdatetimer.start(config.plugins.LastFM.metadatarefreshinterval.value * 1000)

        self.tabchangetimer = eTimer()
        self.tabchangetimer.timeout.get().append(self.tabchangedtimerFired)

        self.infolabelcleartimer = eTimer()
        self.infolabelcleartimer.timeout.get().append(self.clearInfoLabel)

        self.screensavertimer = eTimer()
        self.screensavertimer.timeout.get().append(self.startScreensaver)
        self.onShown.append(self.startScreensaverTimer)

    def initLastFM(self):
        self.setInfoLabel(_("logging into last.FM"))
        self.connect(config.plugins.LastFM.username.value, config.plugins.LastFM.password.value)

    def onStreamplayerStateChanged(self, reason):
        if reason is self.streamplayer.STATE_PLAYLISTENDS:
            self.loadPlaylist()
        else:
            pass

    def onConnectSuccessful(self, text):
        self.setInfoLabel(_("login successful"))

    def onConnectFailed(self, text):
        self.setInfoLabel(_("login failed! ") + text, timeout=False)

    def onTrackSkiped(self, reason):
        self.setInfoLabel(_("Track skipped"))

    def onTrackLoved(self, reason):
        self.setInfoLabel(_("Track loved"))

    def onTrackBanned(self, reason):
        self.setInfoLabel(_("Track banned"))

    def onCommandFailed(self, reason):
        self.setInfoLabel(reason)

    def onGlobalTagsLoaded(self, tags):
        self.setInfoLabel(_("Global Tags loaded"))
        self.buildMenuList(tags)

    def onTopTracksLoaded(self, tracks):
        self.setInfoLabel(_("Top Tracks loaded"))
        self.buildMenuList(tracks)

    def onRecentTracksLoaded(self, tracks):
        self.setInfoLabel(_("Recent Tracks loaded"))
        self.buildMenuList(tracks)

    def onRecentBannedTracksLoaded(self, tracks):
        self.setInfoLabel(_("Banned Tracks loaded"))
        self.buildMenuList(tracks)

    def onRecentLovedTracksLoaded(self, tracks):
        self.setInfoLabel(_("Loved Tracks loaded"))
        self.buildMenuList(tracks)

    def onNeighboursLoaded(self, user):
        self.setInfoLabel(_("Neighbours loaded"))
        self.buildMenuList(user)

    def onFriendsLoaded(self, user):
        self.setInfoLabel(_("Friends loaded"))
        self.buildMenuList(user)

    def onStationChanged(self, reason):
        self.setInfoLabel(reason)
        self.loadPlaylist()

    def onMetadataLoaded(self, metadata):
        self.updateGUI()
        self.guiupdatetimer.start(config.plugins.LastFM.metadatarefreshinterval.value * 1000)

    def onPlaylistLoaded(self, reason):
        self.streamplayer.setPlaylist(self.playlist)
        self.streamplayer.play()

    def skipTrack(self):
        self.streamplayer.skip()
        self.updateGUI()

    def banTrack(self):
        self.ban()
        self.streamplayer.skip()
        self.updateGUI()

    def action_TabChanged(self):
        self.tabchangetimer.stop()
        self.tabchangetimer.start(config.plugins.LastFM.timeouttabselect.value * 1000)

    def guiupdatetimerFired(self):
        self.updateGUI()
        self.guiupdatetimer.start(config.plugins.LastFM.metadatarefreshinterval.value * 1000)

    def tabchangedtimerFired(self):
        self.tablist.getCurrent()[1][1]()
        self.tabchangetimer.stop()

    def startScreensaverTimer(self):
        self.screensavertimer.start(config.plugins.LastFM.sreensaver.wait.value * 1000)

    def resetScreensaverTimer(self):
        self.screensavertimer.stop()
        self.screensavertimer.start(config.plugins.LastFM.sreensaver.wait.value * 1000)

    def startScreensaver(self):
        if config.plugins.LastFM.sreensaver.use.value:
            self.screensavertimer.stop()
            self.session.openWithCallback(self.updateGUI, LastFMSaveScreen, self)

    def action_nextTab(self):
        self.tablist.down()
        self.resetScreensaverTimer()

    def action_prevTab(self):
        self.tablist.up()
        self.resetScreensaverTimer()

    def action_menu(self):
        self.session.open(LastFMConfigScreen)
        self.resetScreensaverTimer()

    def action_exit(self):
        self.screensavertimer.stop()
        self.guiupdatetimer.stop()
        self.streamplayer.stop(force=True)
        self.streamplayer.onStateChanged = []

        self.close()

    def action_ok(self):
        x = self["streamlist"].l.getCurrentSelection()
        if x is None:
            pass
        elif len(x) > 1:
            if not x[1].startswith('lastfm://'):
                self.customstationtype = x[1]
                text = _("please enter an %s name to listen to" % x[1])
                texts = _("%s name" % x[1])
                self.session.openWithCallback(
                    self.onTextForCustomStationEntered,
                    InputBox,
                    windowTitle=text,
                    title=texts
                    )
            else:
                self.changeStation(x[1])
                self.resetScreensaverTimer()

    def onTextForCustomStationEntered(self, text):
        print "onTextForCustomStationEntered", text, self.customstationtype
        if text is not None:
            if self.customstationtype == "artist":
                self.changeStation(urllib2_qoute("lastfm://artist/%s/similarartists" % text))
            elif self.customstationtype == "groupe":
                self.changeStation(urllib2_qoute("lastfm://group/%s" % text))
            elif self.customstationtype == "tag":
                self.changeStation(urllib2_qoute("lastfm://globaltags/%s" % text))

    def action_startstop(self):
        self.resetScreensaverTimer()
        if self.streamplayer.is_playing:
            self.streamplayer.stop(force=True)
            self.setInfoLabel(_("Stream stopped"))
        else:
            self.setInfoLabel(_("Starting stream"), timeout=True)
            self.loadPlaylist()
            self.updateGUI() #forcing guiupdate, so we dont wait till guiupdatetimer fired
            self.guiupdatetimer.start(config.plugins.LastFM.metadatarefreshinterval.value * 1000)

    def setInfoLabel(self, text, timeout=True):
        self.infolabelcleartimer.stop()
        self["infolabel"].setText(text)
        if timeout is True:
            self.infolabelcleartimer.start(config.plugins.LastFM.timeoutstatustext.value * 1000)

    def clearInfoLabel(self):
        self["infolabel"].setText("")

    def updateGUI(self):

        if self.streamplayer.is_playing is True:
            self["duration"].setText(self.streamplayer.getRemaining())
            self["button_red"].setText(_("Stop"))
        else:
            self["duration"].setText("00:00")
            self["button_red"].setText(_("Play"))

        if self.streamplayer.is_playing is not True or self.shown is not True:
            return None

        if self.streamplayer.is_playing is True:
            self.setTitle(config.plugins.LastFM.name.value + " " + _("Ver.") + lastfm_pluginversion + " " + self.streamplayer.getMetadata("station"))
            self["info_artist"].setText(self.streamplayer.getMetadata("creator"))
            self["info_album"].setText(self.streamplayer.getMetadata("album"))
            self["info_track"].setText(self.streamplayer.getMetadata("title"))
            self.summaries.setText(self.streamplayer.getMetadata("creator") + " - " + self.streamplayer.getMetadata("title"))
        else:
            self.setTitle("Last.FM")
            self["info_artist"].setText("N/A")
            self["info_album"].setText("N/A")
            self["info_track"].setText("N/A")
            self.summaries.setText("N/A")

        if self.streamplayer.getMetadata("image").startswith("http") and config.plugins.LastFM.showcoverart.value:
            self.imageconverter.convert(self.streamplayer.getMetadata("image"))
        else:
            self.setCoverArt()

        if self.streamplayer.is_playing is not True:
            self.setTitle(myname)
            self.setCoverArt()
            self["info_artist"].setText("N/A")
            self["info_album"].setText("N/A")
            self["info_track"].setText("N/A")

    def setCoverArt(self, pixmap=None):
        if pixmap is None:
            self["info_cover"].instance.setPixmapFromFile(self.noCoverArtPNG)
        else:
            self["info_cover"].instance.setPixmap(pixmap.__deref__())

    def loadPersonalStations(self):
        tags = []
        x = {}
        x["_display"] = _("Personal Recommendations")
        x["stationurl"] = self.getPersonalURL(config.plugins.LastFM.username.value, level=config.plugins.LastFM.recommendedlevel.value)
        tags.append(x)

        x = {}
        x["_display"] = _("Neighbours Tracks")
        x["stationurl"] = self.getNeighboursURL(config.plugins.LastFM.username.value)
        tags.append(x)

        x = {}
        x["_display"] = _("Loved Tracks")
        x["stationurl"] = self.getLovedURL(config.plugins.LastFM.username.value)
        tags.append(x)

        x = {}
        x["_display"] = _("Play Artist Radio...")
        x["stationurl"] = 'artist'
        tags.append(x)

        x = {}
        x["_display"] = _("Play Group Radio...")
        x["stationurl"] = 'groupe'
        tags.append(x)

        x = {}
        x["_display"] = _("Play Tag Radio...")
        x["stationurl"] = 'tag'
        tags.append(x)

        creator = self.streamplayer.getMetadata("creator")
        if creator != "no creator" and creator != "N/A":
            x = {}
            x["_display"] = _("Tracks similar to") + " " + self.streamplayer.getMetadata("creator")
            x["stationurl"] = self.getSimilarArtistsURL(artist=creator)
            tags.append(x)

            x = {}
            x["_display"] = _("Tracks liked by Fans of") + " " + self.streamplayer.getMetadata("creator")
            x["stationurl"] = self.getArtistsLikedByFans(artist=creator)
            tags.append(x)

            x = {}
            x["_display"] = _("Group of") + " " + self.streamplayer.getMetadata("creator")
            x["stationurl"] = self.getArtistGroup(artist=creator)
            tags.append(x)

        self.buildMenuList(tags)

    def loadGlobalTags(self):
        self.setInfoLabel(_("Loading Global Tags"))
        tags = self.getGlobalTags()

    def loadTopTracks(self):
        self.setInfoLabel(_("Loading Top Tacks"))
        tracks = self.getTopTracks(config.plugins.LastFM.username.value)

    def loadRecentTracks(self):
        self.setInfoLabel(_("Loading Recent Tracks"))
        tracks = self.getRecentTracks(config.plugins.LastFM.username.value)

    def loadLovedTracks(self):
        self.setInfoLabel(_("Loading Loved Tracks"))
        tracks = self.getRecentLovedTracks(config.plugins.LastFM.username.value)

    def loadBannedTracks(self):
        self.setInfoLabel(_("Loading Loved Tracks"))
        tracks = self.getRecentBannedTracks(config.plugins.LastFM.username.value)

    def loadNeighbours(self):
        self.setInfoLabel(_("Loading Neighbours"))
        tracks = self.getNeighbours(config.plugins.LastFM.username.value)

    def loadFriends(self):
        self.setInfoLabel(_("Loading Friends"))
        tracks = self.getFriends(config.plugins.LastFM.username.value)

    def buildMenuList(self, items):
        menuliste = []
        for i in items:
            menuliste.append((i['_display'], i['stationurl']))
        self["streamlist"].l.setList(menuliste)

    def createSummary(self):
        return lastfmLCDScreen


class LastFMSaveScreen(Screen):
    skin = """<screen position="0,0" size="720,576" flags="wfNoBorder" title="LastFMSaveScreen" >
                <widget name="cover" position="50,50" size="200,200" />
              </screen>"""

    noCoverArtPNG = "/usr/share/enigma2/skin_default/no_coverArt.png"
    coverartsize = [200, 200]
    lastcreator = ""

    def __init__(self, session, parent):
        size_w = getDesktop(0).size().width()
        size_h = getDesktop(0).size().height()
        self.skin = """<screen position="0,0" size="%i,%i" flags="wfNoBorder" title="LastFMSaveScreen" >
                <widget name="cover" position="50,50" size="%i,%i" />
              </screen>""" % (size_w, size_h, self.coverartsize[0], self.coverartsize[1])

        Screen.__init__(self, session)
        self.imageconverter = ImageConverter(self.coverartsize[0], self.coverartsize[1], self.setCoverArt)
        self.session = session
        self.streamplayer = parent.streamplayer
        self.parent = parent
        self["cover"] = MovingPixmap()

        self["actions"] = ActionMap(["InfobarChannelSelection", "WizardActions", "DirectionActions", "MenuActions", "ShortcutActions", "GlobalActions", "HelpActions"],
            {
             "ok": self.action_exit,
             "back": self.action_exit,
			 "red": self.parent.action_startstop,
             "green": self.parent.skipTrack,
             "yellow": self.parent.love,
             "blue": self.parent.banTrack,
             }, -1)

        self.onLayoutFinish.append(self.update)
        self.updatetimer = eTimer()
        self.updatetimer.timeout.get().append(self.update)
        self.updatetimer.start(1000)

        if config.plugins.LastFM.sreensaver.coverartanimation.value:
            self.startmovingtimer = eTimer()
            self.startmovingtimer.timeout.get().append(self.movePixmap)
            self.startmovingtimer.start(config.plugins.LastFM.sreensaver.coverartinterval.value * 1000)

    def action_ok(self):
        pass

    def action_exit(self):
        self.close()

    def setCoverArt(self, pixmap=None):
        if pixmap is None:
            self["cover"].instance.setPixmapFromFile(self.noCoverArtPNG)
        else:
            self["cover"].instance.setPixmap(pixmap.__deref__())

    def update(self):
        if self.streamplayer.getMetadata("creator") == self.lastcreator:
            pass
        else:
            self.lastcreator = self.streamplayer.getMetadata("creator")
            self.setTitle(self.lastcreator + " - " + self.streamplayer.getMetadata("title"))
            if config.plugins.LastFM.sreensaver.showcoverart.value is not True:
                pass#do nothing
            elif self.streamplayer.getMetadata("image").startswith("http") and config.plugins.LastFM.showcoverart.value:
                self.imageconverter.convert(self.streamplayer.getMetadata("image"))
            else:
                self.setCoverArt()
        self.updatetimer.start(1000)

    def movePixmap(self):
        self.startmovingtimer.stop()
        newX = randrange(getDesktop(0).size().width() - self.coverartsize[0] - 1)
        newY = randrange(getDesktop(0).size().height() - self.coverartsize[1] - 1)
        self["cover"].moveTo(newX, newY, time=config.plugins.LastFM.sreensaver.coverartspeed.value)
        self["cover"].startMoving()
        self.startmovingtimer.start(config.plugins.LastFM.sreensaver.coverartinterval.value * 1000)


class lastfmLCDScreen(Screen):
	skin = """
	<screen name="LastFM_Summary" position="0,0" size="132,64" id="1">
		<widget name="text1" position="2,0" size="128,25" font="Regular;12" halign="center" valign="center"/>
		<widget name="text2" position="2,29" size="128,35" font="Regular;10" halign="center" valign="center"/>
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session)
		self["text1"] = Label(config.plugins.LastFM.name.value + " " + _("playing:"))
		self["text2"] = Label("")

	def setText(self, text):
		self["text2"].setText(text)


class ImageConverter:

    lastURL = ""

    def __init__(self, width, height, callBack):
        self.callBack = callBack
        self.width = width
        self.height = height
        self.targetfile = "/tmp/coverart" + str(randrange(5000))

    def convert(self, sourceURL):
        if self.lastURL != sourceURL:
            extension = sourceURL.split(".")[-1]
            self.tmpfile = self.targetfile + "." + extension
            downloadPage(sourceURL, self.tmpfile).addCallback(self.onImageLoaded)
            self.lastURL = sourceURL

    def onImageLoaded(self, dummy):
            self.currPic = loadPic(self.tmpfile, self.width, self.height, 0, 1, 0, 1)
            os_remove(self.tmpfile)
            self.callBack(pixmap=self.currPic)
