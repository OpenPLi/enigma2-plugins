# -*- coding: utf-8 -*-
# for localized messages
from . import _

from Components.config import config, getConfigListEntry
from Components.FileList import FileList
from Components.ConfigList import ConfigListScreen
from Screens.Console import Console
from Screens.InputBox import InputBox
from Screens.MessageBox import MessageBox
from Components.Label import Label
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Scanner import openFile
from os.path import isdir as os_path_isdir, dirname as os_path_dirname, basename as os_path_basename
from mimetypes import guess_type
from Screens.VirtualKeyBoard import VirtualKeyBoard
from plugin import pname

##################################
class FilebrowserConfigScreen(ConfigListScreen,Screen):
    skin = """
        <screen position="100,100" size="550,400" title="" >
            <widget name="config" position="0,0" size="550,360" scrollbarMode="showOnDemand" />
            <widget name="key_red" position="10,360" size="100,40" valign="center" halign="center" zPosition="1"  transparent="1" foregroundColor="white" font="Regular;18"/>
            <widget name="key_green" position="120,360" size="100,40" valign="center" halign="center" zPosition="1"  transparent="1" foregroundColor="white" font="Regular;18"/>
            <ePixmap name="pred" position="10,360" size="100,40" zPosition="0" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on"/>
            <ePixmap name="pgreen" position="120,360" size="100,40" zPosition="0" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on"/>
        </screen>"""
    def __init__(self, session):
        self.session = session
        Screen.__init__(self, session)
        self.list = []
        self.list.append(getConfigListEntry(_("Add plugin to Mainmenu"), config.plugins.filebrowser.add_mainmenu_entry))
        self.list.append(getConfigListEntry(_("Add plugin to Extensionmenu"), config.plugins.filebrowser.add_extensionmenu_entry))
        self.list.append(getConfigListEntry(_("Save path positions on exit"), config.plugins.filebrowser.savedirs))
        self.list.append(getConfigListEntry(_("Left panel position"), config.plugins.filebrowser.path_left))
        self.list.append(getConfigListEntry(_("Right panel position"), config.plugins.filebrowser.path_right))

        ConfigListScreen.__init__(self, self.list)
        self["key_red"] = Label(_("Cancel"))
        self["key_green"] = Label(_("OK"))
        self["setupActions"] = ActionMap(["SetupActions"],
        {
            "green": self.save,
            "red": self.cancel,
            "save": self.save,
            "cancel": self.cancel,
            "ok": self.save,
        }, -2)
        self.onLayoutFinish.append(self.onLayout)

    def onLayout(self):
        self.setTitle(pname + " - %s" % _("Settings"))

    def save(self):
        print "saving"
        for x in self["config"].list:
            x[1].save()
        self.refreshPlugins()
        self.close(True)

    def cancel(self):
        print "cancel"
        for x in self["config"].list:
            x[1].cancel()
        self.close(False)

    def refreshPlugins(self):
        from Components.PluginComponent import plugins
        from Tools.Directories import resolveFilename, SCOPE_PLUGINS
        plugins.clearPluginList()
        plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))

##################################
class FilebrowserScreen(Screen):
    skin = """
        <screen position="110,83" size="530,430" title="">
            <widget name="list_left" position="0,0" size="265,380" scrollbarMode="showOnDemand" />
            <widget name="list_right" position="265,0" size="265,380" scrollbarMode="showOnDemand" />

            <widget name="key_red" position="10,390" size="120,30" valign="center" halign="center" zPosition="1" transparent="1" foregroundColor="white" font="Regular;18"/>
            <widget name="key_green" position="140,390" size="120,30" valign="center" halign="center" zPosition="1" transparent="1" foregroundColor="white" font="Regular;18"/>
            <widget name="key_yellow" position="270,390" size="120,30" valign="center" halign="center" zPosition="1" transparent="1" foregroundColor="white" font="Regular;18"/>
            <widget name="key_blue" position="400,390" size="120,30" valign="center" halign="center" zPosition="1" transparent="1" foregroundColor="white" font="Regular;18"/>

            <ePixmap name="pred" position="10,390" size="120,30" zPosition="0" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on"/>
            <ePixmap name="pgreen" position="140,390" size="120,30" zPosition="0" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on"/>
            <ePixmap name="pyellow" position="270,390" size="120,30" zPosition="0" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on"/>
            <ePixmap name="pblue" position="400,390" size="120,30" zPosition="0" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on"/>
        </screen>
        """
    def __init__(self, session,path_left=None):
        if path_left is None:
            if os_path_isdir(config.plugins.filebrowser.path_left.value) and config.plugins.filebrowser.savedirs.value:
                path_left = config.plugins.filebrowser.path_left.value
            else:
                path_left = "/"

        if os_path_isdir(config.plugins.filebrowser.path_right.value) and config.plugins.filebrowser.savedirs.value:
            path_right = config.plugins.filebrowser.path_right.value
        else:
            path_right = "/"

        self.session = session
        Screen.__init__(self, session)

        self["list_left"] = FileList(path_left, matchingPattern = "^.*")
        self["list_right"] = FileList(path_right, matchingPattern = "^.*")
        self["key_red"] = Label(_("Delete"))
        self["key_green"] = Label(_("Move"))
        self["key_yellow"] = Label(_("Copy"))
        self["key_blue"] = Label(_("Rename"))


        self["actions"] = ActionMap(["ChannelSelectBaseActions","WizardActions", "DirectionActions","MenuActions","NumberActions","ColorActions"],
            {
             "ok":      self.ok,
             "back":    self.exit,
             "menu":    self.goMenu,
             "nextMarker": self.listRight,
             "prevMarker": self.listLeft,
             "nextBouquet": self.listRight,
             "prevBouquet": self.listLeft,
             "up": self.goUp,
             "down": self.goDown,
             "left": self.goLeft,
             "right": self.goRight,
             "red": self.goRed,
             "green": self.goGreen,
             "yellow": self.goYellow,
             "blue": self.goBlue,
             "0": self.doRefresh,
             }, -1)
        self.onLayoutFinish.append(self.listLeft)

    def exit(self):
        if self["list_left"].getCurrentDirectory() and config.plugins.filebrowser.savedirs.value:
            config.plugins.filebrowser.path_left.value = self["list_left"].getCurrentDirectory()
            config.plugins.filebrowser.path_left.save()

        if self["list_right"].getCurrentDirectory() and config.plugins.filebrowser.savedirs.value:
            config.plugins.filebrowser.path_right.value = self["list_right"].getCurrentDirectory()
            config.plugins.filebrowser.path_right.save()

        self.close()

    def ok(self):
        if self.SOURCELIST.canDescent(): # isDir
            self.SOURCELIST.descent()
            title = self.SOURCELIST.getCurrentDirectory()
            self.setTitle(title if title else _("Select location"))
        else:
            self.onFileAction()

    def goMenu(self):
        self.session.open(FilebrowserConfigScreen)

    def goLeft(self):
        self.SOURCELIST.pageUp()

    def goRight(self):
        self.SOURCELIST.pageDown()

    def goUp(self):
        self.SOURCELIST.up()

    def goDown(self):
        self.SOURCELIST.down()

    # copy ###################
    def goYellow(self):
        filename = self.SOURCELIST.getFilename()
        sourceDir = self.SOURCELIST.getCurrentDirectory()
        targetDir = self.TARGETLIST.getCurrentDirectory()
        if os_path_isdir(filename):
            txt = _("Copy directory")+"?\n\n%s\n%s\n%s"%(filename,_("to"),targetDir)
        else:
            txt =_("Copy file")+"?\n\n%s\n%s\n%s\n%s\n%s"%(filename,_("from"),sourceDir,_("to"),targetDir)
        self.session.openWithCallback(self.doCopy, MessageBox, txt, type=MessageBox.TYPE_YESNO, default=True, simple=True)

    def doCopy(self, result = False):
        if result:
            filename = self.SOURCELIST.getFilename()
            sourceDir = self.SOURCELIST.getCurrentDirectory()
            targetDir = self.TARGETLIST.getCurrentDirectory()
            if os_path_isdir(filename):
                txt = _("copying directory, wait please ...")
                cmd = ["cp -ar \""+filename+"\" \""+targetDir+"\""]
            else:
                txt = _("copying file ...")
                cmd = ["cp \""+sourceDir+filename+"\" \""+targetDir+"\""]
            self.session.openWithCallback(self.doCopyCB, Console, title = txt, cmdlist = cmd)

    def doCopyCB(self):
        self.doRefresh()

    # delete ###################
    def goRed(self):
        filename = self.SOURCELIST.getFilename()
        sourceDir = self.SOURCELIST.getCurrentDirectory()
        if os_path_isdir(filename):
            txt = _("Delete directory") + "?\n\n%s" % (filename)
        else:
            txt =_("Delete file") + "?\n\n%s\n%s\n%s" % (filename,_("from dir"),sourceDir)
        self.session.openWithCallback(self.doDelete, MessageBox, txt, type=MessageBox.TYPE_YESNO, default=False, simple=True)

    def doDelete(self,result = False):
        if result:
            filename = self.SOURCELIST.getFilename()
            sourceDir = self.SOURCELIST.getCurrentDirectory()
            if os_path_isdir(filename):
                txt = _("deleting directory ...")
                cmd = ["rm -r \""+filename+"\""]
            else:
                txt = _("deleting file ...")
                cmd = ["rm \""+sourceDir+filename+"\""]
            self.session.openWithCallback(self.doDeleteCB, Console, title = txt, cmdlist = cmd)

    def doDeleteCB(self):
        self.doRefresh()

    # move ###################
    def goGreen(self):
        filename = self.SOURCELIST.getFilename()
        sourceDir = self.SOURCELIST.getCurrentDirectory()
        targetDir = self.TARGETLIST.getCurrentDirectory()
        if os_path_isdir(filename):
            txt = _("Move directory") + "?\n\n%s\n%s\n%s" % (filename,_("to"),targetDir)
        else:
            txt = _("Move file") + "?\n\n%s\n%s\n%s\n%s\n%s" % (filename,_("from dir"),sourceDir,_("to dir"),targetDir)
        self.session.openWithCallback(self.doMove, MessageBox, txt, type=MessageBox.TYPE_YESNO, default=True, simple=True)

    def doMove(self, result = True):
        if result:
            filename = self.SOURCELIST.getFilename()
            sourceDir = self.SOURCELIST.getCurrentDirectory()
            targetDir = self.TARGETLIST.getCurrentDirectory()
            if os_path_isdir(filename):
                txt = _("moving directory, wait please ...")
                cmd = ["mv \""+filename+"\" \""+targetDir+"\""]
            else:
                txt = _("moving file ...")
                cmd = ["mv \""+sourceDir+filename+"\" \""+targetDir+"\""]
            self.session.openWithCallback(self.doMoveCB,Console, title = txt, cmdlist = cmd)

    def doMoveCB(self):
        self.doRefresh()

    # move ###################
    def goBlue(self):
        filename = self.SOURCELIST.getFilename()
        sourceDir = self.SOURCELIST.getCurrentDirectory()
        if os_path_isdir(filename):
            text = _("Rename directory")
            filename = os_path_basename(os_path_dirname(filename))
        else:
            text = _("Rename file")
        self.session.openWithCallback(self.doRename, VirtualKeyBoard, title = text, text = filename)

    def doRename(self, newname = None):
        if newname:
            filename = self.SOURCELIST.getFilename()
            sourceDir = self.SOURCELIST.getCurrentDirectory()
            if os_path_isdir(filename):
                txt = _("renaming directory ...")
                cmd = ["mv \""+filename+"\" \""+sourceDir+newname+"\""]
            else:
                txt = _("renaming file ...")
                cmd = ["mv \""+sourceDir+filename+"\" \""+sourceDir+newname+"\""]
            self.session.openWithCallback(self.doRenameCB, Console, title = txt, cmdlist = cmd)

    def doRenameCB(self):
        self.doRefresh()

    #############
    def doRefresh(self):
        self.SOURCELIST.refresh()
        self.TARGETLIST.refresh()

    def listRight(self):
        self["list_left"].selectionEnabled(0)
        self["list_right"].selectionEnabled(1)
        self.SOURCELIST = self["list_right"]
        self.TARGETLIST = self["list_left"]
        title = self.SOURCELIST.getCurrentDirectory()
        self.setTitle(title if title else _("Select location"))

    def listLeft(self):
        self["list_left"].selectionEnabled(1)
        self["list_right"].selectionEnabled(0)
        self.SOURCELIST = self["list_left"]
        self.TARGETLIST = self["list_right"]
        title = self.SOURCELIST.getCurrentDirectory()
        self.setTitle(title if title else _("Select location"))

    def onFileAction(self):
        try:
            x = openFile(self.session,guess_type(self.SOURCELIST.getFilename())[0],self.SOURCELIST.getCurrentDirectory()+self.SOURCELIST.getFilename())
            print "RESULT OPEN FILE",x
        except TypeError,e:
            # catching error
            #  File "/home/tmbinc/opendreambox/1.5/dm8000/experimental/build/tmp/work/enigma2-2.6git20090627-r1/image/usr/lib/enigma2/python/Components/Scanner.py", line 43, in handleFile
            #  TypeError: 'in <string>' requires string as left operand
            self.session.open(MessageBox,_("no Viewer installed for this mimetype!"), type = MessageBox.TYPE_ERROR, timeout = 5, close_on_any_key = True)