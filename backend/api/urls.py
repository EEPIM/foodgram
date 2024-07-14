from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import (
    TagsViewSet, IngredientsViewSet, RecipesViewSet, CustomUserViewSet
)

router = DefaultRouter()
router.register(r'users', CustomUserViewSet)
router.register(r'users/me/avatar', CustomUserViewSet, basename='avatar')
router.register(r'tags', TagsViewSet)
router.register(r'ingredients', IngredientsViewSet)
router.register(r'recipes', RecipesViewSet)

urlpatterns = [
    path('api/', include(router.urls))
]
