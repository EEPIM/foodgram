from django.db.models import Sum
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import baseconv
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.filters import RecipeFilter
from api.permissions import IsAuthorOrReadOnly
from recipes.models import (
    Tags,
    Ingredients,
    Recipes,
    Favorite,
    ShoppingCart,
    RecipesIngredients
)
from recipes.serializers import (
    TagsSerializer,
    IngredientsSerializer,
    RecipesSerializer,
    CreateRecipesSerializer,
    ShortRecipeSerializer,
)


class TagsViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет тэга"""
    queryset = Tags.objects.all()
    serializer_class = TagsSerializer
    pagination_class = None


class IngredientsViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет ингридиентов"""
    queryset = Ingredients.objects.all()
    serializer_class = IngredientsSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_fields = ('name',)


class RecipesViewSet(viewsets.ModelViewSet):
    """Вьюсет рецептов"""
    queryset = Recipes.objects.all()
    pagination_class = LimitOffsetPagination
    permission_classes = (IsAuthorOrReadOnly,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_class = RecipeFilter
    search_fields = ('tags',)

    def get_serializer_class(self):
        if self.action == 'create' or self.action == 'partial_update':
            return CreateRecipesSerializer
        return RecipesSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
    )
    def favorite(self, request, pk):
        """Добавление рецепта в избранное"""
        user = request.user
        recipe = get_object_or_404(Recipes, id=pk)
        favorite_recipes = Favorite.objects.filter(user=user, recipe=recipe)

        if request.method == 'POST':
            if favorite_recipes.exists():
                return Response(
                    'Рецепт уже есть в избранном.',
                    status=status.HTTP_400_BAD_REQUEST
                )
            Favorite.objects.create(user=user, recipe=recipe)
            serializer = ShortRecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if favorite_recipes.exists():
            favorite_recipes.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=['post', 'delete']
    )
    def shopping_cart(self, request, pk):
        user = request.user
        recipe = get_object_or_404(Recipes, id=pk)
        shopping_cart_recipe = ShoppingCart.objects.filter(
            user=user,
            recipe=recipe
        )

        if request.method == 'POST':
            if shopping_cart_recipe.exists():
                return Response(
                    'Ингридиенты из рецепта уже добавлены в список покупок',
                    status=status.HTTP_400_BAD_REQUEST
                )
            ShoppingCart.objects.create(user=user, recipe=recipe)
            serializer = ShortRecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if shopping_cart_recipe.exists():
            shopping_cart_recipe.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=['get'],

    )
    def download_shopping_cart(self, request):
        user = request.user
        recipes = ShoppingCart.objects.filter(user=user).values_list('recipe')
        ingredients = (
            RecipesIngredients.objects.filter(
                recipe__in=recipes
            ).values(
                'ingredient'
            ).annotate(
                amount=Sum('amount')
            ).values_list(
                'ingredient__name',
                'amount',
                'ingredient__measurement_unit',
            )
        )
        shopping_list = []
        for ingredient in ingredients:
            name, value, unit = ingredient
            shopping_list.append(
                f'{name}, {value} {unit}'
            )
        shopping_list = '\n'.join(shopping_list)

        filename = 'Shopping_list.csv'
        response = HttpResponse(shopping_list, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={filename}'

        return response

    @action(
        methods=['get'],
        detail=True,
        url_path='get-link',
        url_name='get-link',
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        encode_id = baseconv.base64.encode(recipe.id)
        short_link = request.build_absolute_uri(
            reverse('shortlink', kwargs={'encoded_id': encode_id})
        )
        return Response({'short-link': short_link}, status=status.HTTP_200_OK)


class ShortLinkView(APIView):

    def get(self, request, encoded_id):
        if not set(encoded_id).issubset(set(baseconv.BASE64_ALPHABET)):
            return Response(
                {'error': 'Недопустимые символы в короткой ссылке.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        recipe_id = baseconv.base64.decode(encoded_id)
        recipe = get_object_or_404(Recipes, pk=recipe_id)
        return HttpResponseRedirect(
            request.build_absolute_uri(
                f'/api/recipes/{recipe.id}/'
            )
        )
