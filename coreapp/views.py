from django.shortcuts import render, redirect,HttpResponse
from django.contrib.auth.decorators import login_required
from .forms import UserForm, RestaurantForm, AccountForm, MealForm
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.utils import timezone
from django.db.models import Sum, Count, Case,When
from django.contrib import messages
from coreapp.models import Meal, Order, Driver


# Create your views here.
def home(request):
    return redirect('restaurant_home')

@login_required(login_url='sign_in/')
def restaurant_home(request):
    return redirect('restaurant_order')

def restaurant_sign_up(request):
    if request.method =="POST":
        user_form = UserForm(data=request.POST)
        restaurant_form = RestaurantForm(request.POST, request.FILES)
        if user_form.is_valid() and restaurant_form.is_valid():
            # cleaned_data returns a dictionary of validated form input fields and their values
            new_user = User.objects.create_user(**user_form.cleaned_data)
            new_restaurant = restaurant_form.save(commit=False)
            new_restaurant.user = new_user
            #new_restaurant.save()
            #To log a user in, from a view, use login(). 
            # It takes an HttpRequest object and a User object.
            # authenticate() method returns user object if authenticated else None
            login(request,authenticate(
                username=user_form['username'], 
                password=user_form['password']))
            return redirect('restaurant_home')
        messages.error(request, "Unsuccessful registration. Invalid information.")
    
    user_form = UserForm()
    restaurant_form = RestaurantForm()
    return render(request,'restaurant/sign_up.html', {'user_form':user_form, 'restaurant_form':restaurant_form})


@login_required(login_url='sign_in/')
def restaurant_account(request):
    if request.method == "POST":
        account_form = AccountForm(request.POST, instance=request.user)
        restaurant_form = RestaurantForm(request.POST, request.FILES, instance=request.user.restaurant)
        if account_form.is_valid() and restaurant_form.is_valid():
            account_form.save()
            restaurant_form.save()
    account_form = AccountForm(instance=request.user)
    restaurant_form = RestaurantForm(instance=request.user)
    return render(request,'restaurant/account.html',{"account_form":account_form,"restaurant_form":restaurant_form})


@login_required(login_url='sign_in/')
def restaurant_meal(request):
    # You get a QuerySet by using your model’s Manager. Each model has at least one Manager, and it’s called objects by default.
    meals = Meal.objects.filter(restaurant=request.user.restaurant).order_by("-id")
    return render(request,'restaurant/meal.html',{"meals":meals})


@login_required(login_url='sign_in/')
def restaurant_add_meal(request):
    if request.method == "POST":
        meal_form = MealForm(request.POST, request.FILES)
        if meal_form.is_valid():
            meal = meal_form.save(commit=False)
            meal.restaurant = request.user.restaurant
            meal.save()
            return redirect(restaurant_meal)

    meal_form = MealForm()
    return render(request,'restaurant/add_meal.html',{"meal_form":meal_form})


@login_required(login_url='sign_in/')
def restaurant_edit_meal(request,meal_id):
    if request.method == "POST":
        meal_form = MealForm(request.POST, request.FILES,instance=meal.objects.get(id=meal_id))
        if meal_form.is_valid():
            meal_form.save()
            return redirect(restaurant_meal)

    meal_form = MealForm(instance=Meal.objects.get(id=meal_id))
    return render(request,'restaurant/edit_meal.html',{"meal_form":meal_form})



@login_required(login_url='sign_in/')
def restaurant_order(request):
    if request.method == "POST":
        order = Order.objects.get(id=request.POST["id"])
        if order.status == Order.COOKING:
            order.status = Order.READY
            order.save()

    order = Order.objects.filter(restaurant=request.user.restaurant)
    return render(request,'restaurant/order.html',{"orders":order})


@login_required(login_url='sign_in/')
def restaurant_report(request):
    from datetime import timedelta
    # annotate() clause returns a QuerySet.
    # Annotation of an object creates a separate summary for each object in a queryset.
    # annote() allows to access field of related database using __  eg...orderdetails__quantity

    # GETTING Top 3 meals
    top3_meals = Meal.objects.filter(restaurant = request.user.restaurant)\
        .annotate(total_order=Sum('orderdetails__quantity'))\
        .order_by("-total_order")[:3]

    meal = {
        "labels": [meal.name for meal in top3_meals],
        "data": [meal.total_order or 0 for meal in top3_meals]
    }

    # Getting top 3 drivers
    top3_drivers = Driver.objects.annotate(
        total_order=Count(
            Case(
                When(order__restaurant=request.user.restaurant, then=1)
            )
        )
    )

    driver = {
        "labels": [driver.user.get_full_name() for driver in top3_drivers],
        "data":[driver.total_order or 0 for driver in top3_drivers]
    }

    # Calculate the weekdays
    revenue = []
    orders = []
    today = timezone.now()
    current_weekdays = [today + timedelta(days= i) for i in range(0 - today.weekday(), 7 - today.weekday())]

    for day in current_weekdays:
        delivered_orders = Order.objects.filter(
            restaurant = request.user.restaurant,
            status = Order.DELIVERED,
            created_at__year = day.year,
            created_at__month = day.month,
            created_at__day = day.day
        )

        revenue.append(sum(order.total for order in delivered_orders))
        orders.append(delivered_orders.count())

    return render(request,'restaurant/report.html', {"revenue":revenue,"orders":orders,"meal":meal,"driver":driver})