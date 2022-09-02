from Plugins.Extensions.WebInterface.WebChilds.Toplevel import addExternalChild
from Plugins.Extensions.EPGRefresh.EPGRefreshResource import \
		EPGRefreshStartRefreshResource, \
		EPGRefreshAddRemoveServiceResource, \
		EPGRefreshListServicesResource, \
		EPGRefreshChangeSettingsResource, \
		EPGRefreshSettingsResource, \
		EPGRefreshPreviewServicesResource, \
		API_VERSION

root = EPGRefreshListServicesResource()
root.putChild(b"refresh", EPGRefreshStartRefreshResource())
root.putChild(b"add", EPGRefreshAddRemoveServiceResource(EPGRefreshAddRemoveServiceResource.TYPE_ADD))
root.putChild(b"del", EPGRefreshAddRemoveServiceResource(EPGRefreshAddRemoveServiceResource.TYPE_DEL))
root.putChild(b"set", EPGRefreshChangeSettingsResource())
root.putChild(b"get", EPGRefreshSettingsResource())
root.putChild(b"preview", EPGRefreshPreviewServicesResource())
addExternalChild(("epgrefresh", root, "EPGRefresh-Plugin", API_VERSION))
