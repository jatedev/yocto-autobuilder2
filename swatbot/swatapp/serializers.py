from rest_framework_json_api import serializers
from swatapp.models import BuildCollection, Build, StepFailure

class BuildCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuildCollection
        fields = ('buildid', 'targetname', 'status', 'triagenotes', 'reason', 'owner', 'branch', 'forswat')

class BuildSerializer(serializers.ModelSerializer):
    class Meta:
        model = Build
        fields = ('buildid', 'url', 'targetname', 'revision', 'started', 'completed', 'workername', 'status', 'buildcollection')

class StepFailureSerializer(serializers.ModelSerializer):
    class Meta:
        model = StepFailure
        fields = ('build', 'triage', 'status', 'stepname', 'url')



