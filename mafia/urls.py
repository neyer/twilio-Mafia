from views import *
from django.conf.urls.defaults import *
urlpatterns = patterns ('',
    (r'^sms', sms)
)
