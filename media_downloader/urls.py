from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.add_file, name='add_file'),
    url(r'^fb/$', views.add_file_from_fb, name='add_from_fb'),
    url(r'^pic-gallery/$', views.PicListView.as_view(), name='pic-gallery'),
    url(r'^video-gallery/$', views.VideosListView.as_view(), name='video_gallery'),
    url(r'^detail-view/(?P<pk>\d+)/$', views.VideoPicDetailView.as_view(), name='detail_view'),
]
