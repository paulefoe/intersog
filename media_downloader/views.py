import os
import urllib.request
import re
from datetime import datetime
import time

from django.shortcuts import render, get_object_or_404, redirect
from django.core.files import File
from bs4 import BeautifulSoup
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.utils import timezone


from .models import MediaDownloader
from .forms import MediaDownloaderForm, AddFromFacebookForm, ChangeMediaForm


def add_file(request):
    if request.method == 'POST':
        form = MediaDownloaderForm(request.POST, request.FILES)
        print(request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            media = MediaDownloader()
            media.title = cd['title']
            media.description = cd['description']
            media.file = cd['file']
            media.date = timezone.now()
            media.save()
            return redirect('detail_view', pk=media.pk)
    else:
        form = MediaDownloaderForm()

    return render(request, 'media_downloader/add_file.html', {'form': form})


def add_file_from_fb(request):
    """Accepting urls like this https://www.facebook.com/DonaldTrump/videos/10160223819690725/ for videos
    and like this
     https://www.facebook.com/DonaldTrump/photos/a.10156483516640725.1073741830.153080620724/10160223686260725/
    for photos
    """
    if request.method == 'POST':
        add_from_fb = AddFromFacebookForm(request.POST)
        if add_from_fb.is_valid():
            html, data = urllib.request.urlretrieve(add_from_fb.cleaned_data['url'])
            with open(html) as h:
                initial_url = add_from_fb.cleaned_data['url'].split('&')[0]
                video_url = ''
                description_tag = ''
                dt = (data['date'])
                date = time.strptime(dt, "%a, %d %b %Y %H:%M:%S %Z")
                date = datetime.fromtimestamp(time.mktime(date))
                soup = BeautifulSoup(h, 'html.parser')
                title = soup.find(id="pageTitle").string

                try:
                    description_tag = soup.find_all("div", class_="hidden_elem")[1]
                    # Regular expression to execute description
                    reg = re.compile('(<p>)(.*)(</p>)')
                    description_list = reg.findall(str(description_tag))
                    description = description_list[0][1]
                except IndexError:
                    description = 'No description were provided'

                try:
                    # delete all html tags from description
                    description = re.sub('<[^<>]+>', '', description)
                    # regular expression for the picture that contain description
                    # (an actual description within a post, not a variable)
                    pic = re.compile('(<img class="scaledImageFitWidth img" src=")(.*)(?=" alt=")')
                    # regular expression for the picture that do not contain description
                    pic2 = re.compile('(<img class="_46-i img" src=")(.*)(?=" style="left)')
                    parsed_pic = pic.findall(str(description_tag))
                    if not parsed_pic:
                        parsed_pic = pic2.findall(str(description_tag))
                    parsed_link = parsed_pic[0][1]
                    final_link = parsed_link.replace('&amp;', '&')

                    # If it's a post with a lot of photos,
                    # the final_link will contain the download links for all of the pics in posts,
                    # 500 is chosen just because it seems like something reasonable
                    if len(final_link) > 500:
                        final_link = final_link.split(initial_url)[1]
                        pic3 = re.compile('(data-ploi=")(.*)(?=" data-plsi=)')
                        final_link = pic3.findall(final_link)[0][1]
                except IndexError:
                    final_link = ''

                if final_link:
                    urllib.request.urlretrieve(final_link, 'media/files/new_pic.jpeg')
                    path = os.path.join('media', 'files', 'new_pic.jpeg')
                else:
                    # Video parsing
                    # First find a <script> tag where an actual link to the video exists
                    for link in soup.find_all('script'):
                        hd_src = link.find(string=re.compile("hd_src"))
                        if hd_src:
                            # Regular expression to find this link
                            p = re.compile('(hd_src_no_ratelimit:")(.*)(?=",aspect_ratio)')
                            parsed = p.findall(hd_src)
                            # hd_src always exists in <script> tag, but if the video in not taken in hd quality,
                            #  hd_src equals to null, so we need to find an sd quality
                            if not parsed:
                                sd = re.compile('(sd_src:")(.*)(?=",hd_tag)')
                                parsed = sd.findall(hd_src)
                            try:
                                video_url = parsed[0][1]
                                urllib.request.urlretrieve(video_url, 'media/files/new_video.mp4')
                                path = os.path.join('media', 'files', 'new_video.mp4')
                            except IndexError:
                                video_url = ''
                if final_link or video_url:
                    media = MediaDownloader()
                    media.title = title
                    media.description = description
                    media.date = date
                    local_file = open(path, 'rb')
                    djangofile = File(local_file)
                    media.file = djangofile
                    media.save()
                    local_file.close()
                    return redirect('detail_view', pk=media.pk)
                else:
                    error = 'Вы ввели неправильную ссылку'
                    add_from_fb = AddFromFacebookForm()
                    return render(request, 'media_downloader/fb.html', {'error': error, 'add_from_fb': add_from_fb})

    else:
        add_from_fb = AddFromFacebookForm()
    return render(request, 'media_downloader/fb.html', {'add_from_fb': add_from_fb})


class VideosListView(ListView):
    """Returns all videos"""
    model = MediaDownloader
    template_name = 'media_downloader/video_gallery.html'

    def get_queryset(self):
        media = MediaDownloader.objects.all()
        queryset = []
        for file in media:
            extension = file.file.name.split('.')
            if extension[-1] == 'mp4':
                queryset.append(file)
        return queryset


class PicListView(ListView):
    """Returns all pictures"""
    model = MediaDownloader
    template_name = 'media_downloader/pic_gallery.html'

    def get_queryset(self):
        media = MediaDownloader.objects.all()
        queryset = []
        for file in media:
            extension = file.file.name.split('.')

            if extension[-1] in ['jpg', 'jpeg', 'png']:
                queryset.append(file)
        return queryset


class VideoPicDetailView(DetailView):
    """A detail view for both pictures and videos"""
    model = MediaDownloader
    template_name = 'media_downloader/detail_view.html'

    def get_context_data(self, **kwargs):
        context = super(VideoPicDetailView, self).get_context_data()
        if self.request.method == 'GET':
            media = get_object_or_404(MediaDownloader, pk=int(self.kwargs['pk']))
            if media.file.url.split('.')[-1] == 'mp4':
                context['video'] = True
            else:
                context['video'] = False
            context['form'] = ChangeMediaForm(initial={'title': media.title, 'description': media.description})
        return context

    def post(self, request, *args, **kwargs):
        form = ChangeMediaForm(request.POST)
        if form.is_valid():
            media = get_object_or_404(MediaDownloader, pk=int(self.kwargs['pk']))
            cd = form.cleaned_data
            media.title = cd['title']
            media.description = cd['description']
            media.save()
        return redirect('detail_view', pk=int(kwargs['pk']))


