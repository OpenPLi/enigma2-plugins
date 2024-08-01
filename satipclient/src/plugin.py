from copy import deepcopy
from glob import glob
from http.client import HTTPConnection
from os import R_OK, access, path, system
from xml.etree.ElementTree import fromstring

from Components.ActionMap import ActionMap
from Components.config import ConfigSelection, ConfigSubsection, getConfigListEntry, NoSave, ConfigText, ConfigIP, ConfigInteger, ConfigYesNo
from Components.ConfigList import ConfigListScreen
from Components.Network import iNetwork
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from enigma import eTimer
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Setup import Setup
from Screens.Console import Console
from Screens.Standby import TryQuitMainloop
from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol

from . import _


def isEmpty(x):
	return len(x) == 0


def getVtunerList():
	data = []
	for x in glob('/dev/misc/vtuner*'):
		data.append(int(x.strip('/dev/misc/vtuner')))
	return sorted(data) # integers 0, 1, 2, ...


VTUNER_IDX_LIST = getVtunerList()

SSDP_ADDR = '239.255.255.250'
SSDP_PORT = 1900
MAN = "ssdp:discover"
MX = 2
ST = "urn:ses-com:device:SatIPServer:1"
MS = 'M-SEARCH * HTTP/1.1\r\nHOST: %s:%d\r\nMAN: "%s"\r\nMX: %d\r\nST: %s\r\n\r\n' % (SSDP_ADDR, SSDP_PORT, MAN, MX, ST)


class SSDPServerDiscovery(DatagramProtocol):
	def __init__(self, callback, iface=None):
		self.callback = callback
		self.port = None

	def send_msearch(self, iface):
		if not iface or iface == "0.0.0.0":
			return

		try:
			self.port = reactor.listenUDP(0, self, interface=iface)
			if self.port is not None:
				print("Sending M-SEARCH...")
				self.port.write(bytes(MS, 'utf-8'), (SSDP_ADDR, SSDP_PORT))
		except:
			print("Error listenUDP...")

	def stop_msearch(self):
		try:
			if self.port is not None:
				self.port.stopListening()
		except:
			print("Error stopListening...")

	def datagramReceived(self, datagram, address):
		#print("Received: (from %r)" % (address,))
		#print("%s" % (datagram ))
		self.callback(datagram)

	def stop(self):
		pass


SATIPSERVERDATA = {}

DEVICE_ATTR = [
'friendlyName',
'manufacturer',
'manufacturerURL',
'modelDescription',
'modelName',
'modelNumber',
'modelURL',
'serialNumber',
'presentationURL'
]

discoveryTimeoutMS = 5000


class SATIPDiscovery:
	def __init__(self):
		self.discoveryStartTimer = eTimer()
		self.discoveryStartTimer.callback.append(self.DiscoveryStart)
		self.iface = ""

		self.discoveryStopTimer = eTimer()
		self.discoveryStopTimer.callback.append(self.DiscoveryStop)

		self.ssdp = SSDPServerDiscovery(self.dataReceive)
		self.updateCallback = []

	def formatAddr(self, address):
		return "%d.%d.%d.%d" % (address[0], address[1], address[2], address[3]) if address else None

	def getEthernetAddr(self):
		iface = None
		for interface in iNetwork.getAdapterList():
			if iNetwork.checkforInterface(interface):
				iface = self.formatAddr(iNetwork.getAdapterAttribute(interface, "ip"))
				if interface == "eth0" and iface and iface != "0.0.0.0":
					break
		if not iface or iface == "0.0.0.0":
			self.iface = _("LAN connection required for first detection.")
		return iface

	def DiscoveryTimerStart(self):
		self.discoveryStartTimer.start(10, True)

	def DiscoveryStart(self, stop_timeout=discoveryTimeoutMS):
		self.discoveryStopTimer.stop()
		self.ssdp.stop_msearch()
		#print("Discovery Start!")
		self.ssdp.send_msearch(self.getEthernetAddr())
		self.discoveryStopTimer.start(stop_timeout, True)

	def DiscoveryStop(self):
		#print("Discovery Stop!")
		self.ssdp.stop_msearch()
		for x in self.updateCallback:
			x()

	def dataReceive(self, data):
		#print("dataReceive:\n", data)
		#print("\n")
		serverData = self.dataParse(data)
		if 'LOCATION' in serverData:
			self.xmlParse(serverData['LOCATION'])

	def dataParse(self, data):
		serverData = {}
		data = data.decode("UTF-8")
		for line in data.splitlines():
			#print("[*] line : ", line)
			if line.find(':') != -1:
				(attr, value) = line.split(':', 1)
				attr = attr.strip().upper()
				if attr not in serverData:
					serverData[attr] = value.strip()
		#for (key, value) in serverData.items():
			#print("[%s] %s" % (key, value))
		#print("\n")
		return serverData

	def xmlParse(self, location):
		def findChild(parent, tag, namespace):
			return parent.find('{%s}%s' % (namespace, tag))

		def getAttr(root, parent, tag, namespace):
			try:
				pElem = findChild(root, parent, namespace)
				if pElem is not None:
					child = findChild(pElem, tag, namespace)
					if child is not None:
						return child.text
			except:
				pass
			return None

		def getAttrN2(root, parent, tag, namespace_1, namespace_2):
			try:
				pElem = findChild(root, parent, namespace_1)
				if pElem is not None:
					child = findChild(pElem, tag, namespace_2)
					if child is not None:
						return child.text
			except:
				pass
			return None

		def dumpData():
			print("\n######## SATIPSERVERDATA ########")
			for (k, v) in SATIPSERVERDATA.items():
				#prestr = "[%s]" % k
				prestr = ""
				for (k2, v2) in v.items():
					prestr2 = prestr + "[%s]" % k2
					if not isinstance(v2, dict):
						print("%s %s" % (prestr2, v2))
						continue
					for (k3, v3) in v2.items():
						prestr3 = prestr2 + "[%s]" % k3
						print("%s %s" % (prestr3, v3))
			print("")

		print("[SATIPClient] Parsing %s" % location)

		address = ""
		port = "80"
		request = ""

		try:
			location = location.strip().split("http://")[1]
			AAA = location.find(':')
			BBB = location.find('/')
			if AAA == -1:
				address = location[AAA + 1: BBB]
				port = "80"
				request = location[BBB:]
			else:
				address = location[:AAA]
				port = location[AAA + 1: BBB]
				request = location[BBB:]

			#print("address2 : ", address)
			#print("port2: " , port)
			#print("request : ", request)

			conn = HTTPConnection(address, int(port))
			conn.request("GET", request)
			res = conn.getresponse()
		except Exception as ErrMsg:
			print("http request error %s" % ErrMsg)
			return -1

		if res.status != 200 or res.reason != "OK":
			print("response error")
			return -1

		data = res.read()
		conn.close()

		# parseing xml data
		root = fromstring(data)

		xmlns_dev = "urn:schemas-upnp-org:device-1-0"
		xmlns_satip = "urn:ses-com:satip"

		udn = getAttr(root, 'device', 'UDN', xmlns_dev)
		if udn is None:
			return -1

		uuid = udn.strip('uuid:')
		SATIPSERVERDATA[uuid] = {}

		SATIPSERVERDATA[uuid]['ipaddress'] = address

		pTag = 'device'
		SATIPSERVERDATA[uuid][pTag] = {}
		for tag in DEVICE_ATTR:
			SATIPSERVERDATA[uuid][pTag][tag] = getAttr(root, pTag, tag, xmlns_dev)

		tagList = ['X_SATIPCAP']
		for tag in tagList:
			SATIPSERVERDATA[uuid][pTag][tag] = getAttrN2(root, pTag, tag, xmlns_dev, xmlns_satip)

		pTag = 'specVersion'
		SATIPSERVERDATA[uuid][pTag] = {}
		tagList = ['major', 'minor']
		for tag in tagList:
			SATIPSERVERDATA[uuid][pTag][tag] = getAttr(root, pTag, tag, xmlns_dev)

		#dumpData()

	def isEmptyServerData(self):
		return isEmpty(SATIPSERVERDATA)

	def getServerData(self):
		return SATIPSERVERDATA

	def getServerKeys(self):
		return SATIPSERVERDATA.keys()

	def getServerInfo(self, uuid, attr):
		if attr in ["ipaddress"]:
			return SATIPSERVERDATA[uuid][attr]

		elif attr in DEVICE_ATTR + ['X_SATIPCAP']:
			return SATIPSERVERDATA[uuid]["device"][attr]

		elif attr in ['major', 'minor']:
			return SATIPSERVERDATA[uuid]["specVersion"][attr]
		else:
			return "Unknown"

	def getServerDescFromIP(self, ip):
		for (uuid, data) in SATIPSERVERDATA.items():
			if data.get('ipaddress') == ip:
				return data['device'].get('modelName')
		return 'Unknown'

	def getUUIDFromIP(self, ip):
		for (uuid, data) in SATIPSERVERDATA.items():
			if data.get('ipaddress') == ip:
				return uuid
		return None


satipdiscovery = SATIPDiscovery()


class SATIPTuner(Setup):
	def __init__(self, session, vtuner_idx, vtuner_uuid, vtuner_type, current_satipConfig):
		self.satipconfig = ConfigSubsection()
		self.vtuner_idx = vtuner_idx
		self.vtuner_uuid = vtuner_uuid
		self.vtuner_type = vtuner_type
		self.current_satipConfig = current_satipConfig
		self.autostart_client = path.exists("/etc/rc3.d/S20satipclient")

		Setup.__init__(self, session, yellow_button={'function': self.DiscoveryStart, 'helptext': _("Toggle Configuration Mode or AutoDisqc"), 'text': _("Discover")},
			blue_button={'function': self.AutostartClient, 'helptext': _("Set all the settings back as they were"), 'text': _("%s autostart") % (self.autostart_client and _("Disable") or _("Enable"))})

		self.setTitle(_("SAT>IP client - auto tuner setup"))

		self.server_entry = None
		satipdiscovery.iface = ""

		if not self.discoveryEnd in satipdiscovery.updateCallback:
			satipdiscovery.updateCallback.append(self.discoveryEnd)

		self.onClose.append(self.OnClose)

		if satipdiscovery.isEmptyServerData():
			self.onLayoutFinish.append(self.DiscoveryStart)
		else:
			self.createServerConfig()
			self.createSetup()

	def AutostartClient(self):
		client = "/etc/init.d/satipclient"
		if path.exists(client):
			if self.autostart_client:
				system("update-rc.d -f satipclient remove")
			else:
				system("update-rc.d satipclient defaults")
			self.autostart_client = path.exists("/etc/rc3.d/S20satipclient")
			self["key_blue"].setText(_("%s autostart") % (self.autostart_client and _("Disable") or _("Enable")))
		else:
			self["description"].setText(_("Not found '%s' ...") % client)

	def OnClose(self):
		if self.discoveryEnd in satipdiscovery.updateCallback:
			satipdiscovery.updateCallback.remove(self.discoveryEnd)
		satipdiscovery.DiscoveryStop()

	def DiscoveryStart(self):
		self["configActions"].setEnabled(False)
		self["key_blueActions"].setEnabled(False)
		self["key_yellowActions"].setEnabled(False)
		self["description"].setText(_("SAT>IP server discovering for %d seconds...") % (discoveryTimeoutMS // 1000))
		satipdiscovery.DiscoveryStart()

	def discoveryEnd(self):
		self["configActions"].setEnabled(True)
		self["key_blueActions"].setEnabled(True)
		self["key_yellowActions"].setEnabled(True)
		if not satipdiscovery.isEmptyServerData():
			self.createServerConfig()
			self.createSetup()
		else:
			self["description"].setText(_("SAT>IP server is not detected.") + satipdiscovery.iface)

	def createServerConfig(self):
		if satipdiscovery.isEmptyServerData():
			return

		server_choices = []

		server_default = None
		for uuid in satipdiscovery.getServerKeys():
			description = satipdiscovery.getServerInfo(uuid, "modelName")
			server_choices.append((uuid, description))
			if self.vtuner_uuid == uuid:
				server_default = uuid

		if server_default is None:
			server_default = server_choices[0][0]

		self.satipconfig.server = ConfigSelection(default=server_default, choices=server_choices)

	def createSetup(self):
		if not hasattr(self.satipconfig, "server"):
			return

		self.list = []
		self.server_entry = getConfigListEntry(_("SAT>IP Server : "), self.satipconfig.server)
		self.list.append(self.server_entry)

		self.createTypeConfig(self.satipconfig.server.value)
		self.type_entry = getConfigListEntry(_("SAT>IP Tuner Type : "), self.satipconfig.tunertype)
		self.list.append(self.type_entry)

		self["config"].list = self.list

		if not self.showChoices in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.showChoices)

		self.selectionChanged()

	def createTypeConfig(self, uuid):
		#type_choices = [("DVB-S", _("DVB-S")), ("DVB-C", _("DVB-C")), ("DVB-T", _("DVB-T"))]
		type_choices = []
		type_default = None
		capability = self.getCapability(uuid)

		for (t, n) in capability.items():
			if n != 0:
				type_choices.append((t, _(t)))
				if self.vtuner_type == t:
					type_default = t

		if isEmpty(type_choices):
			type_choices = [("DVB-S", _("DVB-S"))]

		self.satipconfig.tunertype = ConfigSelection(default=type_default, choices=type_choices)

	def selectionChanged(self):
		if not hasattr(self.satipconfig, "server"):
			return

		uuid = self.satipconfig.server.value

		#ipaddress = satipdiscovery.getServerInfo(uuid, "ipaddress")
		modelDescription = satipdiscovery.getServerInfo(uuid, "modelDescription")
		manufacturer = satipdiscovery.getServerInfo(uuid, "manufacturer")
		#specversion = "%s.%s" % (satipdiscovery.getServerInfo(uuid, "major"), satipdiscovery.getServerInfo(uuid, "minor"))
		modelURL = satipdiscovery.getServerInfo(uuid, "modelURL")
		presentationURL = satipdiscovery.getServerInfo(uuid, "presentationURL")
		#satipcap = satipdiscovery.getServerInfo(uuid, "X_SATIPCAP")
		#serialNumber = satipdiscovery.getServerInfo(uuid, "serialNumber")

		capability = self.getCapability(uuid)
		satipcap_list = []
		for (t, n) in capability.items():
			if n != 0:
				satipcap_list.append("%d x %s" % (n, t))

		satipcap = ",".join(satipcap_list)

		description = ""
		description += _("Description") + ": %s\n" % modelDescription
		description += _("Manufacturer") + ": %s\n" % manufacturer
		description += _("Model URL") + ": %s\n" % modelURL
		description += _("Presentation URL") + ": %s\n" % presentationURL
		description += "UUID: %s\n" % uuid
		description += _("SAT>IP Capability") + ": %s" % satipcap

		self["description"].setText(description)

	def showChoices(self):
		currentConfig = len(self["config"].getCurrent()) > 1 and self["config"].getCurrent()[1] or None
		if currentConfig != None:
			text_list = []
			for choice in currentConfig.choices.choices:
				text_list.append(choice[1])
			text = _("Select") + " : " + ",".join(text_list)
			self["choices"].setText(text)

	def getCapability(self, uuid):
		capability = {'DVB-S': 0, 'DVB-C': 0, 'DVB-T': 0}
		data = satipdiscovery.getServerInfo(uuid, "X_SATIPCAP")
		if data is not None:
			for x in data.split(','):
				if x.upper().find("DVBS") != -1:
					capability['DVB-S'] = int(x.split('-')[1])
				elif x.upper().find("DVBC") != -1:
					capability['DVB-C'] = int(x.split('-')[1])
				elif x.upper().find("DVBT") != -1:
					capability['DVB-T'] = int(x.split('-')[1])
		else:
			capability = {'DVB-S': 1, 'DVB-C': 0, 'DVB-T': 0}

		return capability

	def checkTunerCapacity(self, uuid, tunertype):
		capability = self.getCapability(uuid)
		t_cap = capability[tunertype]

		t_count = 0

		for idx in VTUNER_IDX_LIST:
			if self.vtuner_idx == idx:
				continue

			vtuner = self.current_satipConfig[idx]
			if vtuner["vtuner_type"] == "satip_client" and vtuner["uuid"] == uuid and vtuner["tuner_type"] == tunertype:
				#print("[checkTunerCapacity] tuner %d use type %s" % (idx, tunertype))
				t_count += 1

		#print("[checkTunerCapacity] capability : ", capability)
		#print("[checkTunerCapacity] t_cap : %d, t_count %d" % (t_cap, t_count))

		if int(t_cap) > t_count:
			return True

		return False

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		if self["config"].getCurrent() == self.server_entry:
			self.createSetup()
		self.selectionChanged()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		if self["config"].getCurrent() == self.server_entry:
			self.createSetup()
		self.selectionChanged()

	def keySave(self):
		if not hasattr(self.satipconfig, "server"):
			self.keyCancel()
			return

		uuid = self.satipconfig.server.value
		tunertype = self.satipconfig.tunertype.value

		if not self.checkTunerCapacity(uuid, tunertype):
			self.session.open(MessageBox, _("Server capacity is fulled."), MessageBox.TYPE_ERROR)

		else:
			data = {}
			data['idx'] = self.vtuner_idx
			data['ipaddr'] = satipdiscovery.getServerInfo(uuid, 'ipaddress')
			data['desc'] = satipdiscovery.getServerInfo(uuid, "modelName")
			data['tuner_type'] = tunertype
			data['uuid'] = uuid
			data['vtuner_type'] = 'satip_client'

			self.close(data)


class SATIPManualTuner(Setup):
	def __init__(self, session, vtuner_idx, current_satipConfig):
		self.vtuner_idx = vtuner_idx
		self.current_satipConfig = current_satipConfig
		self.autostart_client = path.exists("/etc/rc3.d/S20satipclient")
		self.initializeSetup()

		Setup.__init__(self, session, blue_button={'function': self.AutostartClient, 'helptext': _("Set all the settings back as they were"), 'text': _("%s autostart") % (self.autostart_client and _("Disable") or _("Enable"))})

		self.setTitle(_("SAT>IP client - manual tuner setup"))

	def AutostartClient(self):
		client = "/etc/init.d/satipclient"
		if path.exists(client):
			if self.autostart_client:
				system("update-rc.d -f satipclient remove")
			else:
				system("update-rc.d satipclient defaults")
			self.autostart_client = path.exists("/etc/rc3.d/S20satipclient")
			self["key_blue"].setText(_("%s autostart") % (self.autostart_client and _("Disable") or _("Enable")))
		else:
			self["description"].setText(_("Not found '%s' ...") % client)

	def convertIP(self, ip):
		try:
			return [int(n) for n in ip.split('.')]
		except:
			return [0, 0, 0, 0]

	def initializeSetup(self):
		self.curSatipConfig = ConfigSubsection()
		try:
			default_desc = self.current_satipConfig['desc']
		except:
			default_desc = "unknown"
		self.curSatipConfig.desc = NoSave(ConfigText(default=default_desc, visible_width=50, fixed_size=False))
		try:
			default_tuner_type = self.current_satipConfig['tuner_type']
		except:
			default_tuner_type = "DVB-S"
		self.curSatipConfig.tuner_type = NoSave(ConfigSelection(default=default_tuner_type, choices=[("DVB-S", "DVB-S"), ("DVB-T", "DVB-T"), ("DVB-C", "DVB-C")]))
		try:
			default_ipaddr = self.convertIP(self.current_satipConfig['ipaddr'])
		except:
			default_ipaddr = [0, 0, 0, 0]
		self.curSatipConfig.ipaddr = NoSave(ConfigIP(default=default_ipaddr))
		try:
			default_port = int(self.current_satipConfig['port'])
		except:
			default_port = 554
		self.curSatipConfig.port = NoSave(ConfigInteger(default=default_port, limits=(1, 65555)))
		try:
			default_tcpdata = self.current_satipConfig['tcpdata'] == "1"
		except:
			default_tcpdata = False
		self.curSatipConfig.tcpdata = NoSave(ConfigYesNo(default=default_tcpdata))
		try:
			default_force_plts = self.current_satipConfig['force_plts'] == "1"
		except:
			default_force_plts = False
		self.curSatipConfig.force_plts = NoSave(ConfigYesNo(default=default_force_plts))
		try:
			fe = int(self.current_satipConfig['fe'])
			default_fe = str(fe)
		except:
			default_fe = "off"
		choicelist = [("off", _("off"))]
		for i in range(0, 20):
			choicelist.append((str(i), str(i)))
		self.curSatipConfig.fe = NoSave(ConfigSelection(default=default_fe, choices=choicelist))
		try:
			default_uuid = self.current_satipConfig['uuid']
		except:
			default_uuid = "n/a"
		self.curSatipConfig.uuid = NoSave(ConfigText(default=default_uuid, visible_width=50, fixed_size=False))

	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Server name"), self.curSatipConfig.desc))
		self.list.append(getConfigListEntry(_("Tuner type"), self.curSatipConfig.tuner_type))
		self.list.append(getConfigListEntry(_("IP address"), self.curSatipConfig.ipaddr))
		self.list.append(getConfigListEntry(_("Port"), self.curSatipConfig.port))
		self.list.append(getConfigListEntry(_("Use TCP instead UDP"), self.curSatipConfig.tcpdata))
		self.list.append(getConfigListEntry(_("Force sending plts=on"), self.curSatipConfig.force_plts))
		self.list.append(getConfigListEntry(_("Send fe=(number specific adapter)"), self.curSatipConfig.fe))
		self.list.append(getConfigListEntry(_("Unique uuid"), self.curSatipConfig.uuid))
		self["config"].list = self.list

	def keySave(self):
		data = {}
		data['ipaddr'] = "%d.%d.%d.%d" % tuple(self.curSatipConfig.ipaddr.value)
		if self.curSatipConfig.port.value != 554:
			data['port'] = str(self.curSatipConfig.port.value)
		data['desc'] = self.curSatipConfig.desc.value or "unknown"
		data['tuner_type'] = self.curSatipConfig.tuner_type.value
		data['uuid'] = self.curSatipConfig.uuid.value or "n/a"
		if self.curSatipConfig.fe.value != "off":
			data['fe'] = self.curSatipConfig.fe.value
		if self.curSatipConfig.tcpdata.value:
			data['tcpdata'] = "1"
		if self.curSatipConfig.force_plts.value:
			data['force_plts'] = "1"
		data['vtuner_type'] = "satip_client"
		self.close((self.vtuner_idx, data))


SATIP_CONFFILE = "/etc/vtuner.conf"


class SATIPClient(Screen):
	skin = """
		<screen position="center,center" size="590,390">
			<ePixmap pixmap="skin_default/buttons/red.png" position="20,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="160,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="300,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="440,0" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="20,0" zPosition="1" size="140,40" font="Regular;18" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="160,0" zPosition="1" size="140,40" font="Regular;18" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="300,0" zPosition="1" size="140,40" font="Regular;18" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#a08500" transparent="1" />
			<widget source="key_blue" render="Label" position="440,0" zPosition="1" size="140,40" font="Regular;18" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#18188b" transparent="1" />

			<widget source="vtunerList" render="Listbox" position="5,60" size="580,272" scrollbarMode="showOnDemand">
				<convert type="TemplatedMultiContent">
				{"templates":
					{"default": (68,[
							MultiContentEntryText(pos = (20, 0), size = (320, 27), font=0, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 0),
							MultiContentEntryText(pos = (30, 28), size = (180, 20), font=1, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 1),
							MultiContentEntryText(pos = (230, 28), size = (140, 20), font=1, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 2),
							MultiContentEntryText(pos = (390, 28), size = (190, 20), font=1, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 3),
							MultiContentEntryText(pos = (30, 49), size = (510, 19), font=1, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 4),
					]),
					},
					"fonts": [gFont("Regular", 24),gFont("Regular", 16)],
					"itemHeight": 68
				}
				</convert>
			</widget>
			<widget source="description" render="Label" position="0,338" size="590,44" font="Regular;19" />
		</screen>
	"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("SAT>IP Client Setup"))

		self["key_red"] = StaticText(_("Disable tuner"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("Auto setup"))
		self["key_blue"] = StaticText(_("Manual setup"))
		self["description"] = StaticText(_("Select tuner and press: Yellow/OK - 'Auto setup' or Blue - 'Manual setup'. Menu - vtuner.conf."))

		self.configList = []
		self["vtunerList"] = List(self.configList)

		self["shortcuts"] = ActionMap(["SATIPCliActions"],
		{
			"ok": self.keyAutoSetup,
			"cancel": self.keyCancel,
			"red": self.keyDisable,
			"green": self.KeySave,
			"yellow": self.keyAutoSetup,
			"blue": self.keyManualSetup,
			"menu": self.openVtunerConf,
		}, -2)

		self.vtunerIndex = VTUNER_IDX_LIST
		self.vtunerConfig = self.loadConfig()
		self.old_vtunerConfig = deepcopy(self.vtunerConfig)
		self.createSetup()
		self.onShown.append(self.checkVTuner)

	def openVtunerConf(self):
		self.session.open(Console, SATIP_CONFFILE, ["cat %s" % SATIP_CONFFILE])

	def checkVTuner(self):
		if not VTUNER_IDX_LIST:
			self.session.open(MessageBox, _("No vtuner found."), MessageBox.TYPE_ERROR, close_on_any_key=True)
			self.close()

	def isChanged(self):
		for vtuner_idx in self.vtunerIndex:
			vtuner = self.vtunerConfig[vtuner_idx]
			old_vtuner = self.old_vtunerConfig[vtuner_idx]
			if vtuner['vtuner_type'] != old_vtuner['vtuner_type']:
				return True
			elif vtuner['vtuner_type'] == "satip_client":
				if len(vtuner) != len(old_vtuner):
					return True
				for key in sorted(vtuner):
					if key not in old_vtuner or (vtuner[key] != old_vtuner[key]):
						return True
		return False

	def KeySave(self):
		if self.isChanged():
			msg = _("You should now reboot your STB to change SAT>IP Configuration.\n\nReboot now ?\n\n")
			self.session.openWithCallback(self.keySaveCB, MessageBox, msg)
		else:
			self.close()

	def keySaveCB(self, res):
		self.saveConfig()
		if res:
			self.doReboot()
		else:
			self.close()

	def doReboot(self):
		self.session.open(TryQuitMainloop, 2)

	def cancelConfirm(self, result):
		if not result:
			return
		self.close()

	def keyCancel(self):
		if self.isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close()

	def createSetup(self):
		self.configList = []
		for vtuner_idx in self.vtunerIndex:
			vtuner = self.vtunerConfig[vtuner_idx]

			if vtuner['vtuner_type'] == "satip_client":
				entry = (
				_("VIRTUAL TUNER %s") % (vtuner_idx + 1),
				_("TYPE : %s") % vtuner['vtuner_type'].replace('_', ' ').upper(),
				_("IP : %s") % vtuner['ipaddr'],
				_("TUNER TYPE : %s") % vtuner['tuner_type'],
				_("SAT>IP SERVER : %s") % vtuner['desc'],
				vtuner_idx,
				vtuner['tuner_type'],
				vtuner['uuid'],
				)
			else:
				entry = (
				_("VIRTUAL TUNER %s") % (vtuner_idx + 1),
				_("TYPE : %s") % vtuner['vtuner_type'].replace('_', ' ').upper(),
				"",
				"",
				"",
				vtuner_idx,
				"",
				"",
				)

			self.configList.append(entry)
		self["vtunerList"].setList(self.configList)

	def keyDisable(self):
		idx = self["vtunerList"].getCurrent()[5]
		self.vtunerConfig[int(idx)] = deepcopy(self.old_vtunerConfig[int(idx)])
		if self.vtunerConfig[int(idx)] and self.vtunerConfig[int(idx)]['vtuner_type'] == "satip_client":
			self.vtunerConfig[int(idx)] = {'vtuner_type': "usb_tuner"}
		self.createSetup()

	def keyAutoSetup(self):
		vtuner_idx = self["vtunerList"].getCurrent()[5]
		vtuner_type = self["vtunerList"].getCurrent()[6]
		vtuner_uuid = self["vtunerList"].getCurrent()[7]
		self.session.openWithCallback(self.SATIPTunerCB, SATIPTuner, vtuner_idx, vtuner_uuid, vtuner_type, self.vtunerConfig)

	def keyManualSetup(self):
		idx = int(self["vtunerList"].getCurrent()[5])
		self.session.openWithCallback(self.SATIPTunerAnswer, SATIPManualTuner, idx, self.vtunerConfig[idx])

	def SATIPTunerAnswer(self, data=None):
		if data != None and not isinstance(data, bool):
			self.vtunerConfig[data[0]] = data[1]
			self.createSetup()

	def SATIPTunerCB(self, data=None):
		if data != None and not isinstance(data, bool) and 'uuid' in data and data['uuid'] is not None:
			idx = int(data['idx'])
			del data['idx']
			self.vtunerConfig[idx] = data
			self.createSetup()

	def saveConfig(self):
		data = ""

		for idx in self.vtunerIndex:
			conf = self.vtunerConfig[idx]
			if not conf:
				continue

			attr = []
			for k in sorted(conf):
				if conf[k] != "":
					attr.append("%s:%s" % (k, conf[k]))

			data += str(idx) + '=' + ",".join(attr) + "\n"

		if data:
			fd = open(SATIP_CONFFILE, 'w')
			fd.write(data)
			fd.close()

	def loadConfig(self):
		vtunerConfig = []

		for idx in self.vtunerIndex:
			vtunerConfig.append({'vtuner_type': "usb_tuner"})

		if access(SATIP_CONFFILE, R_OK):
			fd = open(SATIP_CONFFILE)
			confData = fd.read()
			fd.close()

			if confData:
				for line in confData.splitlines():
					if len(line) == 0 or line[0] == '#':
						continue

					data = line.split('=')
					if len(data) != 2:
						continue
					idx = data[0]

					try:
						vtunerConfig[int(idx)]
					except:
						continue

					data = data[1].split(',')
					if len(data) < 5:
						continue

					for x in data:
						s = x.split(':')
						if len(s) != 2:
							continue

						attr = s[0]
						value = s[1]
						vtunerConfig[int(idx)][attr] = value

		return vtunerConfig


def main(session, **kwargs):
	session.open(SATIPClient)


def menu(menuid, **kwargs):
	if menuid == "scan":
		return [(_("SAT>IP Client"), main, "sat_ip_client", 55)]
	return []


def Plugins(**kwargs):
	pList = []
	pList.append(PluginDescriptor(name=_("SAT>IP Client"), description=_("SAT>IP Client attached to vtuner."), where=PluginDescriptor.WHERE_MENU, needsRestart=False, fnc=menu))
	return pList
