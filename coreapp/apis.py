import json
from django.http import JsonResponse
from coreapp.models import Restaurant, Meal, Order, OrderDetails
from coreapp.serializers import RestaurantSerializer, MealSerializer, OrderSerializer, OrderStatusSerializer, OrderDriverSerializer
from django.utils import timezone
from oauth2_provider.models import AccessToken
from django.views.decorators.csrf import csrf_exempt
import stripe
from foodtasker.settings import STRIPE_API_KEY

stripe.api_key = STRIPE_API_KEY

# Function based views

# =========
# CUSTOMER
# =========

def customer_get_restaurants(request):
    restaurants = RestaurantSerializer(
        Restaurant.objects.all().order_by("-id"), 
        many=True,
        context={"request":request}
        ).data
    # At this point we've translated the model instance into Python native datatypes. 
    # To finalise the serialization process we render the data into json.
    # JSON is a set of rules defining how to represent data in text/string form
    return JsonResponse({"restaurants":restaurants})

def customer_get_meals(request, restaurant_id):
    meals = MealSerializer(
        Meal.objects.filter(restaurant_id = restaurant_id).order_by("-id"),
        many=True,
        context={"request":request}
    ).data
    return JsonResponse({"meals":meals})

@csrf_exempt
def customer_add_order(request):
    """
      params:
        1. access_token
        2. restaurant_id
        3. address
        4. order_details(json format) example:
            [{"meal_id":1, "quantity":2},{"meal_id":2, "quantity": 3}]
      returns:
        {"status": "success"}
    """
    # EXPIRES_IN -->  The lifetime in seconds of the access token.
    # Get access token
    access_token = AccessToken.objects.get(
        token=request.POST.get("access_token"),
       # __gt -> Greater than(Django ORM)
       # This is the constraint for expiry
        expires__gt = timezone.now()
        )

    # Get customer profile
    customer = access_token.user.customer

    # Check whether customer has any outstanding order
    if Order.objects.filter(customer=customer).exclude(status=Order.DELIVERED):
        return JsonResponse({"status":"failed", "error":"Your last order must be completed."})

    # Check order's address
    if not request.POST["address"]:
        return JsonResponse({"status":"failed", "error":"Address is required."})

    # Get order details

    # The json.loads() method can be used to parse a valid JSON string and 
    # convert it into a Python Dictionary
    order_details = json.loads(request.POST["order_details"])

    # Check if meals in only one restaurant and then calculate order total
    order_total = 0
    for meal in order_details:
        if not Meal.objects.filter(id=meal["meal_id"], restaurant_id =request.POST["restaurant_id"]):
            return JsonResponse({"status":"failed", "error": "Meals must be in only one restaurant"})
        else:
            order_total += Meal.objects.get(id=meal["meal_id"]).price * meal["quantity"]

    # CREATE ORDER
    if len(order_details)>0:
        # Step 1 - Create an Order
        order = Order.objects.create(
            customer = customer,
            restaurant_id = request.POST["restaurant_id"],
            total = order_total,
            status = Order.COOKING,
            address = request.POST["address"]
        )
        # Step 2 - Create Order Details
        for meal in order_details:
            OrderDetails.objects.create(
                order = order,
                meal_id = meal["meal_id"],
                quantity = meal["quantity"],
                sub_total = Meal.objects.get(id=meal["meal_id"]).price * meal["quantity"]
            )

        return JsonResponse({"status": "success"})

@csrf_exempt
def customer_get_latest_order(request):
    """
      params:
        1. access_token
      return:
        {JSON data with all details of an order}
    """
    access_token = AccessToken.objects.get(
        token=request.GET.get("access_token"),
        expires__gt =timezone.now()
    )
    customer = access_token.user.customer
    order = OrderSerializer(
        Order.objects.filter(customer=customer).last()
    ).data

    return JsonResponse({"last_order": order})


def customer_get_latest_order_status(request):
    """
      params:
        1. access_token
      return:
        {JSON data with all details of an order}
    """
    access_token = AccessToken.objects.get(
        token=request.GET.get("access_token"),
        expires__gt =timezone.now()
    )
    customer = access_token.user.customer
    order_status = OrderStatusSerializer(
        Order.objects.filter(customer=customer).last()
    ).data

    return JsonResponse({"last_order_status": order_status})


def customer_get_driver_location(request):
    access_token = AccessToken.objects.get(
        token=request.GET.get("access_token"),
        expires__gt =timezone.now()
    )

    customer = access_token.user.customer
    current_order = Order.objects.filter(customer=customer, status=Order.ONTHEWAY).last()
    if current_order:
        location = current_order.driver.location
    else:
        location = None

    return JsonResponse({"location": location})

@csrf_exempt
def create_payment_intent(request):
    """
     params:
       1. access_token
       2. total
     return:
      {"client_secret": client_secret}
    """

    # Get access_token
    access_token = AccessToken.objects.get(
        token=request.POST.get("access_token"),
        expires__gt =timezone.now()
    )

    # Get the orders total amount
    total = request.POST["total"]

    if request.method == "POST":
        if access_token:
            # Create a Payment Intent. this will create a client secret and return it to Mobile App.
            try:
                intent = stripe.PaymentIntent.create(
                    amount = int(total) * 100, # Amount in cents
                    currency = 'usd',
                    description = "FoodTasker Order"
                )
                print(intent)
                if intent:
                    client_secret = intent.client_secret
                    print(client_secret)
                    return JsonResponse({"client_secret": client_secret})

            except stripe.error.StripeError as e:
                return JsonResponse({"status":"failed", "error":str(e)})
            # Exception as e ---> we can access attributes of exception object eg..e.message, e.args
            except Exception as e:
                print(str(e))
                return JsonResponse({"status":"failed", "error":str(e)})

        return JsonResponse({"status":"failed", "error":"Failed to create Payment Intent"})

# ============
# RESTAURANT
# ============

def restaurant_order_notification(request,last_request_time):
    notification = Order.objects.filter(
        restaurant=request.user.restaurant, 
        created_at__gt=last_request_time
        ).count()
    return JsonResponse({"notification":notification})



# ========
# DRIVER
# =========


def driver_get_ready_orders(request):
    orders = OrderSerializer(
        Order.objects.filter(status=Order.READY, driver=None).order_by("-id"),
        many=True
    ).data
    return JsonResponse({"orders":orders})

@csrf_exempt
def driver_pick_order(request):
    if request.method == "POST":
        # Get access token
        access_token = AccessToken.objects.get(
            token=request.POST.get("access_token"),
            expires__gt = timezone.now()
        )

        # Get driver
        driver = access_token.user.driver

        # Check if this driver still have an outstanding order
        if Order.objects.filter(driver=driver, status=Order.ONTHEWAY):
            return JsonResponse({
                "status": "failed",
                "error": "Your outstanding order is not delivered yet."
            })

        # Process picking up an order
        try:
            order = Order.objects.get(
                id = request.POST["order_id"],
                driver = None,
                status = Order.READY
            )

            order.driver = driver
            order.status = Order.ONTHEWAY
            order.picked_at = timezone.now()
            order.save()

            return JsonResponse({"status":"success"})

        # If order is picked up by another driver 
        except Order.DoesNotExist:
            return JsonResponse({
                "status": "failed",
                "error": "This order has been picked up by another"
            })
def driver_get_latest_order(request):
    # Get access_token
    access_token = AccessToken.objects.get(
        token = request.GET["access_token"],
        expires__gt = timezone.now()
    )

    # Get Driver
    driver = access_token.user.driver

    # get the last order of this driver
    order = OrderSerializer(
        Order.objects.filter(driver=driver, status=Order.ONTHEWAY).last()
    ).data

    return JsonResponse({"order":order})


@csrf_exempt
def driver_complete_order(request):
    """
     params:
      1. access_token
      2. order_id

      return:
      {"status": "success"}
    """

    if request.method == "POST":
        # Get access_token
        access_token = AccessToken.objects.get(
            token = request.POST["access_token"],
            expires__gt = timezone.now()
        )

        # Get Driver
        driver = access_token.user.driver

        # Complete an order
        order = Order.objects.get(id=request.POST["order_id"], driver=driver)
        order.status = Order.DELIVERED
        order.save()

        return JsonResponse({"status": "success"})

def driver_get_revenue(request):
    """
    return : {Mon:0,Tue:10,..... }
    """
    # Get access token
    access_token = AccessToken.objects.get(
            token = request.GET["access_token"],
            expires__gt = timezone.now()
        )
    # Get driver
    driver = access_token.user.driver

    # Get revenue
    from datetime import timedelta

    revenue = {}
    today = timezone.now()
    # weekday() method to get the day of the week as a number, where Monday is 0 and Sunday is 6.
    current_weekdays = [today + timedelta(days=i) for i in range(0- today.weekday(), 7-today.weekday())]
    for day in current_weekdays:
        orders = Order.objects.filter(
            driver = driver,
            status = Order.DELIVERED,
            created_at__year = day.year,
            created_at__month = day.month,
            created_at__day = day.day
        )

        # strftime() method returns a string representing date and time using date, time or datetime object.
        # %a ---> Abbreviated weekday name. eg. Sun, Mon
        revenue[day.strftime("%a")] = sum(order.total for order in orders)

    return JsonResponse({"revenue": revenue})

@csrf_exempt
def driver_update_location(request):
    """
        params:
        1. access_token
        2. location eg. lat, long
        return:
        {"status": "success}
    """
    if request.method == "POST":
        access_token = AccessToken.objects.get(
            token=request.POST["access_token"],
            expires__gt = timezone.now()
        )

        driver = access_token.user.driver

        driver.location = request.POST["location"]
        driver.save()

    return JsonResponse({"status":"success"})

def driver_get_profile(request):
    access_token = AccessToken.objects.get(
        token=request.GET["access_token"],
        expires__gt = timezone.now()
    )
    driver = OrderDriverSerializer(
        access_token.user.driver
    ).data
    return JsonResponse({"driver":driver})

@csrf_exempt
def driver_update_profile(request):
    """
    params:
      1. access_token
      2. car_model
      3. plate_number

    return:
     {"status":"success"}
    """
    if request.method == "POST":
        access_token = AccessToken.objects.get(
            token = request.POST["access_token"],
            expires__gt = timezone.now()
        )

        driver = access_token.user.driver

        # Update driver's profile
        driver.car_model = request.POST["car_model"]
        driver.plate_number = request.POST["plate_number"]
        driver.save()

    return JsonResponse({"status": "success"})