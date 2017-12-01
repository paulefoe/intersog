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
    """Принимает ссылки вида https://www.facebook.com/DonaldTrump/videos/10160223819690725/ для видео
    и https://www.facebook.com/DonaldTrump/photos/a.10156483516640725.1073741830.153080620724/10160223686260725/
    для фото
    """
    if request.method == 'POST':
        add_from_fb = AddFromFacebookForm(request.POST)
        if add_from_fb.is_valid():
            html, data = urllib.request.urlretrieve(add_from_fb.cleaned_data['url'])
            with open(html) as h:
                video_url = ''
                dt = (data['date'])
                date = time.strptime(dt, "%a, %d %b %Y %H:%M:%S %Z")
                date = datetime.fromtimestamp(time.mktime(date))
                soup = BeautifulSoup(h, 'html.parser')
                title = soup.find(id="pageTitle").string

                try:
                    description_tag = soup.find_all("div", class_="hidden_elem")[1]
                    # Регулярное выражение, чтобы достать описание
                    reg = re.compile('(<p>)(.*)(</p>)')
                    description_list = reg.findall(str(description_tag))
                    description = description_list[0][1]
                except IndexError:
                    description = 'No description were provided'
                    description_tag = ''

                try:
                    # удалить все html тэги из описания
                    description = re.sub('<[^<>]+>', '', description)
                    pic = re.compile('(<img class="scaledImageFitWidth img" src=")(.*)(?=" alt=")')
                    parsed_pic = pic.findall(str(description_tag))
                    parsed_link = parsed_pic[0][1]
                    final_link = parsed_link.replace('&amp;', '&')
                except IndexError:
                    final_link = ''

                if final_link:
                    urllib.request.urlretrieve(final_link, 'media/files/new_pic.jpeg')
                    path = os.path.join('media', 'files', 'new_pic.jpeg')
                else:
                    # Парсинг видео
                    # Сначало найти <script> тэг в котором хранится ссылка на реальное видео.
                    for link in soup.find_all('script'):
                        hd_src = link.find(string=re.compile("hd_src"))
                        if hd_src:
                            # Регулярное выражение, чтобы найти ссылку
                            p = re.compile('(hd_src_no_ratelimit:")(.*)(?=",aspect_ratio)')
                            parsed = p.findall(hd_src)
                            # hd_src всегда есть в тэге скрипта, но в случае отсутствие hd разрешениея, оно
                            # равняется null в таком случае, скачать sd разрешение.
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
                    print(dt)
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
    """Возвращает все видео"""
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
    """Возвращает все картинки"""
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


