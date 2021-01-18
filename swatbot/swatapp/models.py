from django.db import models

class Status(models.IntegerChoices):
    # Matches buildbot result values
    SUCCESS = 0
    WARNINGS = 1
    FAILURE = 2
    SKIPPED = 3
    EXCEPTION = 4
    RETRY = 5
    CANCELLED = 6

class TriageStatus(models.IntegerChoices):
    PENDING = 0
    MAILSENT = 1
    BUGOPENED = 2
    OTHERDONE = 3

class BuildCollection(models.Model):
    class Meta:
        permissions = [('rest', 'Can use rest API')]

    buildid = models.IntegerField(unique=True)
    targetname = models.CharField(max_length=20)
    reason = models.CharField(max_length=250, null=True, blank=True)
    owner = models.CharField(max_length=250, null=True, blank=True)
    status = models.IntegerField(choices=Status.choices, null=True, blank=True)
    triagenotes = models.CharField(max_length=250, null=True, blank=True)
    forswat = models.BooleanField(default=False)
    branch = models.CharField(max_length=20, null=True, blank=True)

class Build(models.Model):
    buildid = models.IntegerField()
    url = models.CharField(max_length=100)
    targetname = models.CharField(max_length=20)
    revision = models.CharField(max_length=50, null=True, blank=True)
    started = models.DateTimeField('Build started')
    completed = models.DateTimeField('Build completed', null=True, blank=True)
    workername = models.CharField(max_length=20)
    status = models.IntegerField(choices=Status.choices, null=True, blank=True)
    buildcollection = models.ForeignKey(BuildCollection, on_delete=models.CASCADE, null=True, blank=True)

class StepFailure(models.Model):
    build = models.ForeignKey(Build, on_delete=models.CASCADE, null=True, blank=True)
    triage = models.IntegerField(choices=TriageStatus.choices, null=True, blank=True)
    status = models.IntegerField(choices=Status.choices, null=True, blank=True)
    stepname = models.CharField(max_length=100)
    url = models.CharField(max_length=150)
