import stripe
from django.conf import settings
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from datetime import datetime

from .models import Subscription
from .serializers import SubscriptionSerializer


def get_or_create_subscription(user):
    subscription, created = Subscription.objects.get_or_create(user=user)
    return subscription


class CurrentSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        subscription = get_or_create_subscription(request.user)
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data)


class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan = request.data.get('plan')

        if plan not in ['pro', 'business']:
            return Response(
                {"detail": "Invalid plan. Choose 'pro' or 'business'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        subscription = get_or_create_subscription(request.user)

        # create or get stripe customer
        if not subscription.stripe_customer_id:
            customer = stripe.Customer.create(
                email=request.user.email,
                name=request.user.full_name,
            )
            subscription.stripe_customer_id = customer.id
            subscription.save()

        # create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=subscription.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': settings.STRIPE_PRICE_IDS[plan],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{settings.FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/billing/cancel",
            metadata={
                'user_id': str(request.user.id),
                'plan': plan,
            }
        )

        return Response({
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.id,
        })


class CreatePortalSessionView(APIView):
    """Stripe billing portal — manage subscription, cancel, update card"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        subscription = get_or_create_subscription(request.user)

        if not subscription.stripe_customer_id:
            return Response(
                {"detail": "No active subscription found."},
                status=status.HTTP_400_BAD_REQUEST
            )

        portal_session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL}/billing",
        )

        return Response({"portal_url": portal_session.url})


class CancelSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        subscription = get_or_create_subscription(request.user)

        if not subscription.stripe_subscription_id:
            return Response(
                {"detail": "No active subscription found."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # cancel at period end — user keeps access till end of billing period
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=True
        )

        subscription.status = Subscription.Status.CANCELED
        subscription.canceled_at = timezone.now()
        subscription.save()

        return Response({"detail": "Subscription will be canceled at end of billing period."})


class StripeWebhookView(APIView):
    """Stripe sends events here — payment success, failure, etc."""
    permission_classes = [AllowAny]  # stripe doesn't send auth tokens

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return Response({"detail": "Invalid payload."}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            return Response({"detail": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)

        # handle events
        if event['type'] == 'checkout.session.completed':
            self.handle_checkout_completed(event['data']['object'])

        elif event['type'] == 'invoice.payment_succeeded':
            self.handle_payment_succeeded(event['data']['object'])

        elif event['type'] == 'invoice.payment_failed':
            self.handle_payment_failed(event['data']['object'])

        elif event['type'] == 'customer.subscription.deleted':
            self.handle_subscription_deleted(event['data']['object'])

        return Response({"detail": "Webhook received."})

    def handle_checkout_completed(self, session):
        user_id = session['metadata']['user_id']
        plan = session['metadata']['plan']

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)
            subscription = get_or_create_subscription(user)

            stripe_sub = stripe.Subscription.retrieve(session['subscription'])

            subscription.plan = plan
            subscription.status = Subscription.Status.ACTIVE
            subscription.stripe_subscription_id = session['subscription']
            subscription.current_period_start = datetime.fromtimestamp(
                stripe_sub['current_period_start'], tz=timezone.utc
            )
            subscription.current_period_end = datetime.fromtimestamp(
                stripe_sub['current_period_end'], tz=timezone.utc
            )
            subscription.save()
        except Exception as e:
            print(f"Webhook error: {e}")

    def handle_payment_succeeded(self, invoice):
        stripe_customer_id = invoice['customer']
        try:
            subscription = Subscription.objects.get(stripe_customer_id=stripe_customer_id)
            subscription.status = Subscription.Status.ACTIVE
            subscription.save()
        except Subscription.DoesNotExist:
            pass

    def handle_payment_failed(self, invoice):
        stripe_customer_id = invoice['customer']
        try:
            subscription = Subscription.objects.get(stripe_customer_id=stripe_customer_id)
            subscription.status = Subscription.Status.PAST_DUE
            subscription.save()
        except Subscription.DoesNotExist:
            pass

    def handle_subscription_deleted(self, stripe_subscription):
        stripe_customer_id = stripe_subscription['customer']
        try:
            subscription = Subscription.objects.get(stripe_customer_id=stripe_customer_id)
            subscription.plan = Subscription.Plan.FREE
            subscription.status = Subscription.Status.ACTIVE
            subscription.stripe_subscription_id = None
            subscription.save()
        except Subscription.DoesNotExist:
            pass
