from django.contrib import admin

from .models import Build, BuildCollection, StepFailure

admin.site.register(Build)
admin.site.register(BuildCollection)
admin.site.register(StepFailure)

