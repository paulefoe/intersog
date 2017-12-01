from django.db import models


class MediaDownloader(models.Model):
    file = models.FileField(upload_to='files')
    title = models.CharField(max_length=100)
    description = models.TextField()
    date = models.DateTimeField()

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return self.file.name

