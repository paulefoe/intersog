from django import forms

from .models import MediaDownloader


class MediaDownloaderForm(forms.ModelForm):
    class Meta:
        model = MediaDownloader
        fields = ['title', 'description', 'file']

    def clean_file(self):
        file = self.cleaned_data['file']
        valid_extensions = ['jpg', 'jpeg', 'png', 'mp4']
        extension = file.name.split('.')[-1]
        if extension not in valid_extensions:
            raise forms.ValidationError("The file does not match valid extensions "
                                        "('jpg', 'jpeg', 'png', 'mp4')")
        return file


class ChangeMediaForm(MediaDownloaderForm):
    class Meta:
        model = MediaDownloader
        fields = ['title', 'description']


class AddFromFacebookForm(forms.Form):
    url = forms.URLField(required=False)

    def clean_url(self):
        url = self.cleaned_data['url']
        if 'facebook.com' not in url:
            raise forms.ValidationError("You can upload only via facebook")
        return url
