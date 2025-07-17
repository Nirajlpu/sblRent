from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('home/', views.home, name='home'),
    path('login/', views.login_user, name='login'),
    path('register/', views.register_user, name='register'),  
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add-property/', views.add_property, name='add_property'),
    path('book/<int:property_id>/', views.book_property, name='book_property'),
    path('logout/', views.logout_user, name='logout'),
    path('dashboard/delete_property/<id>/', views.delete_property, name='delete_property'),
   
]