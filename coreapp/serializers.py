from rest_framework import serializers
from coreapp.models import Restaurant, Meal, Order, Customer, Restaurant, Driver, OrderDetails


# Serializers define the API representation.
# Serializers allow complex data such as querysets and model instances to be converted to native Python data types.
# That can be rendered quickly into JSON, XML, and other formats.
class RestaurantSerializer(serializers.ModelSerializer):
    # SerializerMethodField gets its data by calling get_<field_name>.
    logo = serializers.SerializerMethodField()

    def get_logo(self, restaurant):
        request = self.context.get('request')
        logo_url = restaurant.logo.url
        return request.build_absolute_uri(logo_url)

    class Meta:
        model = Restaurant
        fields = ("id","name","phone", "address", "logo")


class MealSerializer(serializers.ModelSerializer):
    # SerializerMethodField gets its data by calling get_<field_name>.
    image = serializers.SerializerMethodField()

    def get_image(self, meal):
        request = self.context.get('request')
        image_url = meal.image.url
        return request.build_absolute_uri(image_url)

    class Meta:
        model = Meal
        fields = ("id","name","short_description", "image", "price")

# ORDER SERIALIZER

# Fields like customer, restaurant etc are database objects.
# To convert to JSON format, we need to serialize these fields.


# get_full_name() ---> Returns the first_name + last_name, with a space in between.
class OrderCustomerSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source="user.get_full_name")
    class Meta:
        model = Customer
        fields = ("id", "name", "avatar", "address")

class OrderDriverSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source="user.get_full_name")
    class Meta:
        model = Driver
        fields = ("id", "name", "avatar", "car_model", "plate_number")

class OrderRestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ("id", "name", "phone", "address")

class OrderMealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meal
        fields = ("id", "name", "price")

class OrderDetailsSerializer(serializers.ModelSerializer):
    meal = OrderMealSerializer()
    class Meta:
        model = OrderDetails
        # The `fields` option must be a list or tuple or "__all__"
        fields = ("id","meal", "quantity", "sub_total")

class OrderSerializer(serializers.ModelSerializer):
    customer = OrderCustomerSerializer()
    driver = OrderDriverSerializer()
    restaurant = OrderRestaurantSerializer()
    order_details = OrderDetailsSerializer(many=True)
    status = serializers.ReadOnlyField(source="get_status_display")

    class Meta:
        model = Order
        fields = ("id", "customer", "restaurant", "driver", "order_details", "total", "status", "address")



# Order status serializer

class OrderStatusSerializer(serializers.ModelSerializer):
    status = serializers.ReadOnlyField(source="get_status_display")
    class Meta:
        model = Order
        # The `fields` option must be a list or tuple or "__all__"
        fields = ("id","status")
