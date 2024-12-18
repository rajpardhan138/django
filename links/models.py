from django.db import models
from django.utils.timezone import now
from django.contrib.auth.models import User
    

class ShortLink(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="links")
    short_code = models.CharField(max_length=10, unique=True)
    name = models.URLField(null=True, blank=True)
    customize_url = models.URLField(null=True, blank=True)
    ios_url = models.URLField(null=True, blank=True)
    android_url = models.URLField(null=True, blank=True)
    i_pad_url = models.URLField(null=True, blank=True)
    non_google_huawei_url = models.URLField(null=True, blank=True)
    fallback_url = models.URLField(null=True, blank=True)
    click_count = models.IntegerField(default=0)
    timestamp = models.DateTimeField(default=now)

class ClickStats(models.Model):
    short_link = models.ForeignKey(ShortLink, on_delete=models.CASCADE)
    device_type = models.CharField(max_length=50, null=True, blank=True)
    os_family = models.CharField(max_length=50, null=True, blank=True)
    browser = models.CharField(max_length=50, null=True, blank=True)
    referrer = models.URLField(null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    utm_source = models.CharField(max_length=100, null=True, blank=True)
    utm_medium = models.CharField(max_length=100, null=True, blank=True)
    utm_campaign = models.CharField(max_length=100, null=True, blank=True)
    timestamp = models.DateTimeField(default=now)
