from django.conf.urls.defaults import patterns
from django.conf import settings

urlpatterns = patterns('',
    (r'^$', 'dm93data.qfm.views.accounts'),
    (r'^register/(?P<acct_id>\d+)', 'dm93data.qfm.views.register'),
    (r'^export', 'dm93data.qfm.views.export'),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT}),
    )
