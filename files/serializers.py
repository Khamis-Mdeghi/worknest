from rest_framework import serializers
from django.conf import settings
from .models import File


ALLOWED_EXTENSIONS = [
    '.jpg', '.jpeg', '.png', '.gif', '.webp',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.ppt', '.pptx', '.txt', '.mp4', '.avi',
    '.mov', '.mkv', '.svg', '.zip', '.rar'
]


class FileSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)
    file_size_display = serializers.ReadOnlyField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = File
        fields = [
            'id', 'name', 'file', 'file_url', 'file_type',
            'file_size', 'file_size_display',
            'uploaded_by_email', 'created_at'
        ]
        read_only_fields = ['id', 'file_type', 'file_size', 'created_at', 'name']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file:
            return request.build_absolute_uri(obj.file.url) if request else obj.file.url
        return None

    def validate_file(self, value):
        import os
        # check file size
        if value.size > settings.MAX_UPLOAD_SIZE:
            raise serializers.ValidationError(
                f'File size must be under 10MB. Your file is {value.size / (1024*1024):.1f}MB'
            )
        # check file extension
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise serializers.ValidationError(
                f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
            )
        return value

    def create(self, validated_data):
        file = validated_data['file']
        instance = File(**validated_data)
        instance.name = file.name
        instance.file_size = file.size
        instance.file_type = instance.get_file_type(file.name)
        instance.save()
        return instance