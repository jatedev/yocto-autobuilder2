from django.shortcuts import render

from swatapp.models import BuildCollection, Build, StepFailure
from swatapp.serializers import BuildCollectionSerializer, BuildSerializer, StepFailureSerializer
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth.mixins import PermissionRequiredMixin

class BuildCollectionViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    permission_required = 'swatapp.rest'
    queryset = BuildCollection.objects.all()
    serializer_class = BuildCollectionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['buildid']

class BuildViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    permission_required = 'swatapp.rest'
    queryset = Build.objects.all()
    serializer_class = BuildSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['buildid']

class StepFailureViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
    permission_required = 'swatapp.rest'
    queryset = StepFailure.objects.all()
    serializer_class = StepFailureSerializer
    filter_backends = [DjangoFilterBackend]

