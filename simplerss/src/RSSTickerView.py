# for localized messages
from . import _

#pragma mark MovingLabel

from Components.Label import Label
from enigma import eTimer
from Components.config import config


class MovingLabel(Label):
	"""Simple Label which allows to display badly scrolling text."""

	def __init__(self, text=""):
		self.offset = 0
		self.displayLength = 100

		Label.__init__(self, text)

		self.moveTimer = eTimer()
		self.moveTimer.callback.append(self.doMove)

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = []
			append = attribs.append
			for attrib, value in self.skinAttributes:
				if attrib == "displayLength":
					self.displayLength = int(value)
				else:
					append((attrib, value))
			self.skinAttributes = attribs
		return Label.applySkin(self, desktop, screen)

	def setText(self, text):
		text = (self.displayLength * ' ') + text
		self.longText = text
		self.offset = 0
		Label.setText(self, text[:self.displayLength].encode('utf-8', 'ignore'))

	def stopMoving(self):
		self.moveTimer.stop()
		self.offset = 0

	def startMoving(self):
		self.moveTimer.start(int(config.plugins.simpleRSS.ticker_speed.value))

	def doMove(self):
		offset = self.offset + 1
		text = self.longText[offset:self.displayLength + offset]
		self.offset = offset

		if not text:
			# it appears we're done displaying the full text, so stop now or waste cpu time forever :D
			self.stopMoving()

		try:
			Label.setText(self, text.encode('utf-8', 'ignore'))
		except Exception:
			self.stopMoving()


class MovingCallbackLabel(MovingLabel):
	"""Extended MovingLabel that allows to set a callback when done scrolling."""

	def __init__(self, text="", callback=None):
		MovingLabel.__init__(self, text)
		self.callback = callback

	def stopMoving(self):
		MovingLabel.stopMoving(self)
		if self.callback:
			self.callback()

#pragma mark RSSTickerView


from Screens.Screen import Screen
from enigma import getDesktop

HD = False
FULLHD = False
if getDesktop(0).size().width() >= 1920:
	FULLHD = True
elif getDesktop(0).size().width() >= 1280:
	HD = True


class RSSTickerView(Screen):
	if FULLHD:
		skin = """
			<screen position="0,950" size="1920,40" flags="wfNoBorder">
				<widget name="newsLabel" position="5,5" size="1920,30" font="Regular;28" halign="left" noWrap="1"/>
			</screen>"""
	elif HD:
		skin = """
			<screen position="0,660" size="1280,30" flags="wfNoBorder">
				<widget name="newsLabel" position="5,5" size="1270,20" font="Regular;18" halign="left" noWrap="1"/>
			</screen>"""
	else:
		skin = """
			<screen position="0,536" size="720,30" flags="wfNoBorder">
				<widget name="newsLabel" position="5,5" size="710,20" font="Regular;18" halign="left" noWrap="1"/>
			</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self["newsLabel"] = MovingCallbackLabel(callback=self.hide)

	def updateText(self, feed):
		text = _("New Items") + ': ' + ' +++ '.join((item[0].decode('utf-8') for item in feed.history))
		self["newsLabel"].setText(text)

	def display(self, feed=None):
		if feed:
			self.updateText(feed)
		self.show()
		self["newsLabel"].startMoving()


tickerView = None
