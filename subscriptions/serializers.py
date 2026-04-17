from rest_framework import serializers
from .models import Subscription


class SubscriptionSerializer(serializers.ModelSerializer):
    limits = serializers.ReadOnlyField()

    class Meta:
        model = Subscription
        fields = [
            'id', 'plan', 'status', 'limits',
            'current_period_start', 'current_period_end',
            'canceled_at', 'created_at'
        ]
        read_only_fields = fields