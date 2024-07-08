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
from rest_framework.serializers import ValidationError
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
    """Получение тэга"""
    queryset = Tags.objects.all()
    serializer_class = TagsSerializer
    pagination_class = None


class IngredientsViewSet(viewsets.ReadOnlyModelViewSet):
    """Получение ингридиентов"""
    queryset = Ingredients.objects.all()
    serializer_class = IngredientsSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_fields = ('name',)


class RecipesViewSet(viewsets.ModelViewSet):
    """Работа с рецептами"""
    queryset = Recipes.objects.all()
    pagination_class = LimitOffsetPagination
    permission_classes = (IsAuthorOrReadOnly,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_class = RecipeFilter
    search_fields = ('tags',)

    def get_serializer_class(self):
        if self.action == 'retrieve' or self.action == 'list':
            return RecipesSerializer
        return CreateRecipesSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
    )
    def favorite(self, request, **kwargs):
        """Метод для управления избранными подписками """
        user = request.user
        recipe = get_object_or_404(Recipes, id=self.kwargs['pk'])
        if request.method == 'POST':
            if Favorite.objects.filter(user=user, recipe=recipe).exists():
                raise ValidationError('Товар уже существует в избранном')
            Favorite.objects.create(user=user, recipe=recipe)
            serializer = ShortRecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            recipe = Favorite.objects.filter(user=user, recipe=recipe)
            if recipe.exists():
                recipe.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=['post', 'delete']
    )
    def shopping_cart(self, request, **kwargs):
        user = request.user
        if request.method == 'POST':
            recipe = get_object_or_404(Recipes, id=kwargs['pk'])
            serializer = ShortRecipeSerializer(recipe)
            if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
                raise ValidationError('Товар уже существует в корзине')
            ShoppingCart.objects.create(user=user, recipe=recipe)
            return Response(serializer.data, status=201)
        recipe = get_object_or_404(Recipes, pk=self.kwargs['pk'])
        try:
            shopping_cart = ShoppingCart.objects.get(user=user, recipe=recipe)
        except ShoppingCart.DoesNotExist:
            raise ValidationError('Товар не найден', code=404)
        shopping_cart.delete()
        return Response(status=204)

    @action(
        detail=False,
        methods=['get']
    )
    def download_shopping_cart(self, request):
        user = request.user
        if not user.shopping_cart.exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        ingredients = RecipesIngredients.objects.filter(
            recipe__shopping_cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(amount=Sum('amount'))

        shopping_list = (
            f'Список покупок для: {user.get_full_name()}\n\n'
        )
        shopping_list += '\n'.join([
            f'- {ingredient["ingredient__name"]} '
            f'({ingredient["ingredient__measurement_unit"]})'
            f' - {ingredient["amount"]}'
            for ingredient in ingredients
        ])

        filename = f'{user.username}_shopping_list.txt'
        response = HttpResponse(shopping_list, content_type='text/plain')
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
