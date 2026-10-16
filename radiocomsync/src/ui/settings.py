from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList

from ..config import load_stations, save_stations


class SettingsScreen(Screen):
    skin = """
        <screen name="RadioComSyncSettings" position="center,center" size="700,500"
                title="RadioComSync - Station Settings" backgroundColor="#20000000">
            <widget name="title_label" position="20,10" size="660,40"
                    font="Regular;30" foregroundColor="#00ffffff"
                    backgroundColor="#20000000" halign="center" />
            <widget name="stationlist" position="20,60" size="660,340"
                    font="Regular;26" itemHeight="40"
                    foregroundColor="#00ffffff" backgroundColor="#20000000"
                    scrollbarMode="showOnDemand" />
            <widget name="buttons" position="20,420" size="660,60"
                    font="Regular;22" foregroundColor="#00ffcc00"
                    backgroundColor="#20000000" halign="center" />
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.stations = load_stations()

        self["title_label"] = Label("Station Settings")
        self["stationlist"] = MenuList([])
        self["buttons"] = Label(
            "Green: Add  |  Yellow: Edit  |  Red: Delete\n"
            "Ch Up/Down: Reorder  |  Exit: Save & Close"
        )

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "ChannelSelectBaseActions"],
            {
                "ok": self._on_edit,
                "cancel": self._on_close,
                "green": self._on_add,
                "yellow": self._on_edit,
                "red": self._on_delete,
                "nextBouquet": self._on_move_up,
                "prevBouquet": self._on_move_down,
            },
            -1,
        )

        self._build_list()

    def _build_list(self):
        entries = []
        for station in self.stations:
            sources = []
            if station.get("url_online"):
                sources.append("Online")
            if station.get("url_sat"):
                sources.append("Sat")
            source_str = " + ".join(sources) if sources else "No URL"
            entries.append(f"{station['name']}  ({source_str})")
        self["stationlist"].setList(entries)

    def _get_selected_index(self):
        return self["stationlist"].getSelectedIndex()

    def _on_add(self):
        """Add a new station — start with name entry."""
        new_station = {
            "name": "",
            "url_online": None,
            "url_sat": None,
            "preferred": "online",
            "type": "MP3",
            "last_delay_online": None,
            "last_delay_sat": None,
            "fine_tune": 0,
            "last_measured": None,
        }
        self.session.openWithCallback(
            lambda name: self._on_name_entered(name, new_station, is_new=True),
            VirtualKeyBoard, title="Station Name:", text=""
        )

    def _on_edit(self):
        """Edit selected station name."""
        idx = self._get_selected_index()
        if idx is None or idx >= len(self.stations):
            return
        station = self.stations[idx]
        self.session.openWithCallback(
            lambda name: self._on_name_entered(name, station, is_new=False),
            VirtualKeyBoard, title="Station Name:", text=station["name"]
        )

    def _on_name_entered(self, name, station, is_new=False):
        if name is None:
            return
        station["name"] = name
        if is_new:
            # Ask for online URL
            self.session.openWithCallback(
                lambda url: self._on_online_url_entered(url, station, is_new),
                VirtualKeyBoard, title="Online Stream URL (or leave empty):", text=""
            )
        else:
            save_stations(self.stations)
            self._build_list()

    def _on_online_url_entered(self, url, station, is_new):
        if url:
            station["url_online"] = url
        # Ask for sat URL
        self.session.openWithCallback(
            lambda sat_url: self._on_sat_url_entered(sat_url, station, is_new),
            VirtualKeyBoard, title="Satellite Service Ref URL (or leave empty):", text=""
        )

    def _on_sat_url_entered(self, sat_url, station, is_new):
        if sat_url:
            station["url_sat"] = sat_url
            station["preferred"] = "sat"
        if is_new:
            self.stations.append(station)
        save_stations(self.stations)
        self._build_list()

    def _on_delete(self):
        """Delete selected station (with confirmation)."""
        idx = self._get_selected_index()
        if idx is not None and idx < len(self.stations):
            name = self.stations[idx]["name"]
            self.session.openWithCallback(
                self._confirm_delete, MessageBox,
                f"Delete '{name}'?",
                type=MessageBox.TYPE_YESNO,
            )

    def _confirm_delete(self, confirmed):
        if not confirmed:
            return
        idx = self._get_selected_index()
        if idx is not None and idx < len(self.stations):
            del self.stations[idx]
            save_stations(self.stations)
            self._build_list()

    def _on_move_up(self):
        """Move station up in the list."""
        idx = self._get_selected_index()
        if idx is not None and idx > 0:
            self.stations[idx], self.stations[idx - 1] = self.stations[idx - 1], self.stations[idx]
            save_stations(self.stations)
            self._build_list()

    def _on_move_down(self):
        """Move station down in the list."""
        idx = self._get_selected_index()
        if idx is not None and idx < len(self.stations) - 1:
            self.stations[idx], self.stations[idx + 1] = self.stations[idx + 1], self.stations[idx]
            save_stations(self.stations)
            self._build_list()

    def _on_close(self):
        save_stations(self.stations)
        self.close()
