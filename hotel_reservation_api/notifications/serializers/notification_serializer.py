"""
Serializers para notificaciones.
"""
from rest_framework import serializers


class NotificationSerializer(serializers.Serializer):
    """Serializer para notificaciones."""
    id = serializers.CharField(read_only=True, source='_id')
    user_id = serializers.CharField(read_only=True)
    type = serializers.ChoiceField(
        choices=['reservation', 'payment', 'review', 'system']
    )
    title = serializers.CharField(max_length=200)
    message = serializers.CharField(max_length=1000)
    data = serializers.JSONField(required=False, default=dict)
    read = serializers.BooleanField(default=False)
    created_at = serializers.DateTimeField(read_only=True)
    read_at = serializers.DateTimeField(read_only=True, required=False, allow_null=True)
    
    def to_representation(self, instance):
        """Convert ObjectId to string."""
        data = super().to_representation(instance)
        if '_id' in instance:
            data['id'] = str(instance['_id'])
        return data


class CreateNotificationSerializer(serializers.Serializer):
    """Serializer para crear notificaciones."""
    type = serializers.ChoiceField(
        choices=['reservation', 'payment', 'review', 'system']
    )
    title = serializers.CharField(max_length=200)
    message = serializers.CharField(max_length=1000)
    data = serializers.JSONField(required=False, default=dict)
