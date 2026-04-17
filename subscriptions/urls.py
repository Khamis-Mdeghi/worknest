from django.urls import path
from .views import (
    CurrentSubscriptionView,
    CreateCheckoutSessionView,
    CreatePortalSessionView,
    CancelSubscriptionView,
    StripeWebhookView,
)

urlpatterns = [
    path('current/', CurrentSubscriptionView.as_view(), name='current-subscription'),
    path('checkout/', CreateCheckoutSessionView.as_view(), name='create-checkout'),
    path('portal/', CreatePortalSessionView.as_view(), name='billing-portal'),
    path('cancel/', CancelSubscriptionView.as_view(), name='cancel-subscription'),
    path('webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
]