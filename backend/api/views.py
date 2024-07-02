from rest_framework import viewsets
from rest_framework import filters, status, permissions, mixins, viewsets

from recipes.models import Tags, Ingredients, Recipes
from recipes.serializers import TagsSerializer, IngredientsSerializer, RecipesSerializer, CreateRecipesSerializer


class TagsViewSet(viewsets.ReadOnlyModelViewSet):
# class TagsViewSet(viewsets.ModelViewSet):
    """Получение тэга"""
    queryset = Tags.objects.all()
    serializer_class = TagsSerializer
    pagination_class = None
    permission_classes = (permissions.AllowAny,)


class IngredientsViewSet(viewsets.ReadOnlyModelViewSet):
# class IngredientsViewSet(viewsets.ModelViewSet):
    """Получение ингридиентов"""
    queryset = Ingredients.objects.all()
    serializer_class = IngredientsSerializer
    permission_classes = (permissions.AllowAny,)


class RecipesViewSet(viewsets.ModelViewSet):
    """Работа с рецептами"""
    queryset = Recipes.objects.all()
    # serializer_class = RecipesSerializer
    permission_classes = (permissions.AllowAny,)

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateRecipesSerializer
        return RecipesSerializer
