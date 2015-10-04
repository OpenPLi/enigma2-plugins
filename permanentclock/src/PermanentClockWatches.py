import math
from Components.Renderer.Renderer import Renderer
from skin import parseColor
from enigma import eCanvas, eSize, gRGB, eRect

class PermanentClockWatches(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.fColor = gRGB(255, 255, 255, 0)
		self.bColor = gRGB(0, 0, 0, 255)
		self.numval = -1

	GUI_WIDGET = eCanvas

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, what) in self.skinAttributes:
			if (attrib == 'foregroundColor'):
				self.fColor = parseColor(what)
			elif (attrib == 'backgroundColor'):
				self.bColor = parseColor(what)
			else:
				attribs.append((attrib, what))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	def calculate(self, w, r, m):
		a = (w * 6)
		z = (math.pi / 180)
		x = int(round((r * math.sin((a * z)))))
		y = int(round((r * math.cos((a * z)))))
		return ((m + x), (m - y))

	def hand(self):
		width = self.instance.size().width()
		height = self.instance.size().height()
		r = (min(width, height) / 2)
		(endX, endY,) = self.calculate(self.numval, r, r)
		self.draw_line(r, r, endX, endY)

	def draw_line(self, x0, y0, x1, y1):
		steep = abs(y1 - y0) > abs(x1 - x0)
		if steep:
			x0, y0 = y0, x0  
			x1, y1 = y1, x1
		if x0 > x1:
			x0, x1 = x1, x0
			y0, y1 = y1, y0
		if y0 < y1: 
			ystep = 1
		else:
			ystep = -1
		deltax = x1 - x0
		deltay = abs(y1 - y0)
		error = -deltax / 2
		y = y0
		for x in range(x0, x1 + 1):
			if steep:
				self.instance.fillRect(eRect(y, x, 1, 1), self.fColor)
			else:
				self.instance.fillRect(eRect(x, y, 1, 1), self.fColor)
			error = error + deltay
			if error > 0:
				y = y + ystep
				error = error - deltax

	def changed(self, what):
		sss = self.source.value
		if what[0] == self.CHANGED_CLEAR:
			pass
		else:
			if self.instance:
				if self.numval != sss:
					self.numval = sss
					self.instance.clear(self.bColor)
					self.hand()
	def postWidgetCreate(self, instance):
		def parseSize(str):
			(x, y,) = str.split(',')
			return eSize(int(x), int(y))

		for (attrib, value,) in self.skinAttributes:
			if ((attrib == 'size') and self.instance.setSize(parseSize(value))):
				pass
		self.instance.clear(self.bColor)
