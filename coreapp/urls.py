
from . import views, apis
from django.urls import path, include
from django.contrib.auth import views as auth_view


urlpatterns = [
    # Web View - Restaurant
    path('', views.restaurant_home, name='restaurant_home'),
    path('sign_in/', auth_view.LoginView.as_view(template_name='restaurant/sign_in.html'), name='restaurant_sign_in'),
    path('sign_out/', auth_view.LogoutView.as_view(next_page='/'), name='restaurant_sign_out'),
    path('sign_up/', views.restaurant_sign_up, name='restaurant_sign_up'),

    path('account/', views.restaurant_account, name='restaurant_account'),
    path('meal/', views.restaurant_meal, name='restaurant_meal'),
    path('meal/add_meal/', views.restaurant_add_meal, name='restaurant_add_meal'),
    path('meal/edit_meal/<int:meal_id>', views.restaurant_edit_meal, name='restaurant_edit_meal'),
    path('order/', views.restaurant_order, name='restaurant_order'),
    path('report/', views.restaurant_report, name='restaurant_report'),

    # APIs

    # /Convert-token (sign-in/sign-up), /revoke-token(sign-out)
    path('social/', include('rest_framework_social_oauth2.urls')),

    # API for customer
    path('customer/restaurants/', apis.customer_get_restaurants), 
    path('customer/meals/<int:restaurant_id>', apis.customer_get_meals), 
    path('customer/payment_intent/', apis.create_payment_intent),
    path('customer/order/add/', apis.customer_add_order), 
    path('customer/order/latest/', apis.customer_get_latest_order), 
    path('customer/order/latest_status/', apis.customer_get_latest_order_status), 
    path('customer/driver/location/', apis.customer_get_driver_location),
    

    # API for Restaurant
    path('restaurant/order/notification/<last_request_time>/', apis.restaurant_order_notification),

    # API for Driver
    path('driver/order/ready/', apis.driver_get_ready_orders),
    path('driver/order/pick/', apis.driver_pick_order),
    path('driver/order/latest/', apis.driver_get_latest_order),
    path('driver/order/complete/', apis.driver_complete_order),
    path('driver/order/revenue/', apis.driver_get_revenue),
    path('driver/location/update/', apis.driver_update_location),
    path('driver/profile/', apis.driver_get_profile),
    path('driver/profile/update/', apis.driver_update_profile),

]




