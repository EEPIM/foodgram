from django.contrib import admin
from django.urls import include, path
# from rest_framework.authtoken import views
# from djoser.views import UserViewSet
# from rest_framework.routers import DefaultRouter

# router = DefaultRouter()
# router.register(r'users', UserViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('api.urls')),
    path('api/', include('djoser.urls')),
    path('api/auth/', include('djoser.urls.authtoken')),
]
