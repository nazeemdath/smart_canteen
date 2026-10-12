import json
from collections import defaultdict
from datetime import date, timedelta

import razorpay
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F, Sum
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import now

from cart.models import CartItem
from checkout.models import Feedback, Order
from .models import (
    Banner,
    ClaimedMeal,
    MealSubscriptionPlan,
    Product,
    SubscriptionMeal,
    UserSubscription,
    WebPushSubscription,
)

# Initialize Razorpay Client using settings
razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID or 'rzp_test_placeholder', settings.RAZORPAY_KEY_SECRET or 'rzp_secret_placeholder')
)


def samp(request):
    return render(request, 'index.html')


def about(request):
    return render(request, 'base.html')


def shop(request):
    query = request.GET.get('q')  # get the search keyword from the URL
    products = Product.objects.all()

    if query:
        products = products.filter(name__icontains=query)

    context = {'products': products}
    return render(request, 'shop/shop.html', context)


def index(request):
    products = Product.objects.all()  # Fetch all products
    feedbacks = Feedback.objects.all().order_by('-created_at')  # Order feedbacks by latest
    banners = Banner.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'index.html', {'products': products, 'feedbacks': feedbacks, 'banners': banners})


def search_products(request):
    query = request.GET.get('q', '').strip()
    if query:
        products = Product.objects.filter(name__icontains=query)  # Case-insensitive search
        results = [
            {
                'name': product.name,
                'price': float(product.price),
                'image': product.image.url if product.image else '',
            }
            for product in products
        ]
        return JsonResponse({'results': results})
    return JsonResponse({'results': []})


@login_required
def subscription_plans(request):
    plans = MealSubscriptionPlan.objects.all()
    active_subscription = UserSubscription.objects.filter(
        user=request.user, end_date__gte=now().date()
    ).first()

    # Fetch today's available meals
    available_meals = SubscriptionMeal.objects.filter(date_available=date.today(), is_available=True)

    # Fetch user's claimed meals today
    claimed_today = 0
    remaining_meals = 0
    user_available_meals = []

    if active_subscription:
        total_meals_per_day = active_subscription.plan.meals_per_day  # Allowed meals per day

        # Count meals already claimed today
        claimed_today = ClaimedMeal.objects.filter(
            user_subscription=active_subscription, claimed_on__date=date.today()
        ).count()

        # Calculate remaining meals user can claim
        remaining_meals = total_meals_per_day - claimed_today

        # Fetch only the remaining claimable meals
        if remaining_meals > 0:
            user_available_meals = available_meals[:remaining_meals]

    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        if not plan_id:
            messages.error(request, 'Please select a plan.')
            return redirect('subscription_plans')

        try:
            plan = MealSubscriptionPlan.objects.get(id=plan_id)
        except MealSubscriptionPlan.DoesNotExist:
            messages.error(request, 'Selected plan does not exist.')
            return redirect('subscription_plans')

        # Create Razorpay Order
        order_amount = int(plan.price * 100)  # Razorpay requires amount in paise
        order_currency = 'INR'
        order_receipt = f'subscription_{request.user.id}_{plan.id}'

        razorpay_order = razorpay_client.order.create(
            {'amount': order_amount, 'currency': order_currency, 'receipt': order_receipt, 'payment_capture': '1'}
        )

        context = {
            'plans': plans,
            'active_subscription': active_subscription,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'plan': plan,
            'order_amount': order_amount,
        }
        return render(request, 'subscriptions_payment.html', context)

    return render(
        request,
        'subscriptions.html',
        {
            'plans': plans,
            'active_subscription': active_subscription,
            'available_meals': available_meals,
            'user_available_meals': user_available_meals,
            'claimed_today': claimed_today,
            'remaining_meals': remaining_meals,
        },
    )


@login_required
def subscription_success(request):
    if request.method == 'POST':
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_signature = request.POST.get('razorpay_signature')
        plan_id = request.POST.get('plan_id')

        if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature, plan_id]):
            return JsonResponse({'error': 'Missing payment details'}, status=400)

        # Find the plan
        try:
            plan = MealSubscriptionPlan.objects.get(id=plan_id)
        except MealSubscriptionPlan.DoesNotExist:
            return JsonResponse({'error': 'Invalid subscription plan'}, status=400)

        # Verify Razorpay payment signature
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        }

        try:
            razorpay_client.utility.verify_payment_signature(params_dict)

            user = request.user
            existing_subscription = UserSubscription.objects.filter(user=user).first()

            start_date = now().date()
            end_date = start_date + timedelta(days=plan.duration_days)

            if existing_subscription:
                if existing_subscription.end_date >= start_date:
                    existing_subscription.end_date += timedelta(days=plan.duration_days)
                    existing_subscription.remaining_meals += plan.meals_per_day * plan.duration_days
                else:
                    existing_subscription.start_date = start_date
                    existing_subscription.end_date = end_date
                    existing_subscription.remaining_meals = plan.meals_per_day * plan.duration_days

                existing_subscription.razorpay_payment_id = razorpay_payment_id
                existing_subscription.razorpay_order_id = razorpay_order_id
                existing_subscription.razorpay_signature = razorpay_signature
                existing_subscription.payment_status = 'active'
                existing_subscription.save()
            else:
                UserSubscription.objects.create(
                    user=user,
                    plan=plan,
                    start_date=start_date,
                    end_date=end_date,
                    remaining_meals=plan.meals_per_day * plan.duration_days,
                    razorpay_payment_id=razorpay_payment_id,
                    razorpay_order_id=razorpay_order_id,
                    razorpay_signature=razorpay_signature,
                    payment_status='active',
                )

            messages.success(request, f'Subscription for {plan.get_name_display()} activated successfully!')
            return redirect('subscription_plans')

        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({'error': 'Payment verification failed'}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
def claim_meal(request, meal_id):
    user_subscription = UserSubscription.objects.filter(user=request.user, end_date__gte=date.today()).first()
    meal = get_object_or_404(SubscriptionMeal, id=meal_id, date_available=date.today(), is_available=True)

    if not user_subscription:
        messages.error(request, 'You do not have an active subscription.')
        return redirect('subscription_plans')

    total_meals_per_day = user_subscription.plan.meals_per_day

    claimed_today = ClaimedMeal.objects.filter(
        user_subscription=user_subscription, claimed_on__date=date.today()
    ).count()

    if claimed_today >= total_meals_per_day:
        messages.error(request, 'You have reached your daily meal limit.')
        return redirect('subscription_plans')

    if user_subscription.remaining_meals <= 0:
        messages.error(request, 'You have no remaining meals in your subscription.')
        return redirect('subscription_plans')

    product = meal.product

    with transaction.atomic():
        product.refresh_from_db()

        if product.stock <= 0:
            messages.error(request, f'{meal.product} is out of stock.')
            return redirect('subscription_plans')

        product.stock -= 1
        product.save()

        user_subscription.remaining_meals -= 1
        user_subscription.save()

        ClaimedMeal.objects.create(user_subscription=user_subscription, meal=meal)

        order = Order.objects.create(
            user=request.user,
            status='Confirmed',
            order_total=product.price,
        )

        token = f'CLM{order.id}{order.user.id:04d}'
        request.session['order_token'] = token
        order.token_number = token
        order.save()

        messages.success(
            request,
            f'You have successfully claimed {meal.product}. Remaining meals: {user_subscription.remaining_meals}',
        )

    return redirect('order-confirmation')


@login_required
def health_dashboard(request):
    user = request.user

    cart_items = (
        CartItem.objects.filter(user=user, order__isnull=False)
        .annotate(order_date=TruncDate('order__created_at'), calories=F('product_id__calories') * F('quantity'))
        .values('order_date')
        .annotate(total_calories=Sum('calories'))
    )

    claimed_meals = (
        ClaimedMeal.objects.filter(user_subscription__user=user)
        .annotate(order_date=TruncDate('claimed_on'), calories=F('meal__product__calories'))
        .values('order_date')
        .annotate(total_calories=Sum('calories'))
    )

    daily_totals = defaultdict(int)

    for entry in cart_items:
        daily_totals[entry['order_date']] += entry['total_calories']

    for entry in claimed_meals:
        daily_totals[entry['order_date']] += entry['total_calories']

    daily_calories = [
        {'order_date': entry_date, 'total_calories': total}
        for entry_date, total in daily_totals.items()
    ]
    daily_calories.sort(key=lambda x: x['order_date'], reverse=True)

    return render(request, 'health_dashboard.html', {'daily_calories': daily_calories})


@login_required
def save_subscription(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        endpoint = data.get('endpoint')
        keys = data.get('keys', {})
        p256dh = keys.get('p256dh')
        auth = keys.get('auth')

        if not endpoint or not p256dh or not auth:
            return JsonResponse({'error': 'Missing push subscription fields'}, status=400)

        subscription, created = WebPushSubscription.objects.get_or_create(
            user=request.user,
            endpoint=endpoint,
            defaults={
                'p256dh': p256dh,
                'auth': auth,
            },
        )

        if not created:
            subscription.p256dh = p256dh
            subscription.auth = auth
            subscription.save()

        return JsonResponse({'status': 'ok'})

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def cont(request):
    return render(request, 'contact.html')


def homepage(request):
    return redirect('index')