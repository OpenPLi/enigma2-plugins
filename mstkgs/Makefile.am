plugindir = $(libdir)/enigma2/python/Plugins/Extensions/mstkgs

plugin_DATA = \
	__init__.py \
	plugin.py

install-data-local:
	install -d $(DESTDIR)$(plugindir)/images
	install -m 0644 $(srcdir)/images/*.png $(DESTDIR)$(plugindir)/images/
