from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from djoser.views import UserViewSet
from django.urls import reverse
from django.utils import baseconv
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.filters import RecipeFilter
from api.pagination import RecipePagination
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (
    TagsSerializer,
    IngredientsSerializer,
    RecipesSerializer,
    CreateRecipesSerializer,
    ShortRecipeSerializer,
    CustomUserSerializer,
    FollowSerializer,
    CustomUserAvatarSerializer,
)
from recipes.models import (
    Tag,
    Ingredient,
    Recipe,
    Favorite,
    ShoppingCart,
    RecipeIngredient
)
from users.models import Follow

User = get_user_model()


class TagsViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет тега"""
    queryset = Tag.objects.all()
    serializer_class = TagsSerializer
    pagination_class = None


class IngredientsViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет ингредиентов"""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientsSerializer
    pagination_class = None
    filter_backends = (filters.SearchFilter,)
    filterset_fields = ('name',)
    search_fields = ('^name',)


class RecipesViewSet(viewsets.ModelViewSet):
    """Вьюсет рецептов"""
    queryset = Recipe.objects.all()
    pagination_class = RecipePagination
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

    def add_or_delete(self, model, pk, message, request):
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)
        related_recipe = model.objects.filter(user=user, recipe=recipe)

        if request.method == 'POST':
            if related_recipe.exists():
                return Response(
                    message,
                    status=status.HTTP_400_BAD_REQUEST
                )
            model.objects.create(user=user, recipe=recipe)
            serializer = ShortRecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if related_recipe.exists():
            related_recipe.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
    )
    def favorite(self, request, pk):
        """Добавление рецепта в избранное"""

        return self.add_or_delete(
            Favorite,
            pk,
            'Рецепт уже есть в избранном.',
            request
        )

    @action(
        detail=True,
        methods=['post', 'delete']
    )
    def shopping_cart(self, request, pk):
        """Добавление ингредиентов в список покупок."""

        return self.add_or_delete(
            ShoppingCart,
            pk,
            'Ингредиенты из рецепта уже добавлены в список покупок',
            request
        )

    @action(
        detail=False,
        methods=['get'],

    )
    def download_shopping_cart(self, request):
        user = request.user
        recipes = ShoppingCart.objects.filter(user=user).values_list('recipe')
        ingredients = (
            RecipeIngredient.objects.filter(
                recipe__in=recipes
            ).values(
                'ingredient'
            ).annotate(
                quantity=Sum('amount')
            ).values_list(
                'ingredient__name',
                'quantity',
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

        filename = 'Shopping_list.txt'
        response = HttpResponse(
            shopping_list,
            content_type='text/txt'
        )
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
        return redirect(f'/recipes/{recipe_id}/',)


class CustomUserViewSet(UserViewSet):
    """Вьюсет пользователя"""

    serializer_class = CustomUserSerializer
    pagination_class = LimitOffsetPagination

    def get_permissions(self):
        if self.action in ('list', 'create', 'retrieve'):
            self.permission_classes = [AllowAny, ]
        return super().get_permissions()

    @action(
        methods=['put', 'delete'],
        detail=True
    )
    def avatar(self, request, id):
        user = request.user
        if request.method == 'PUT':
            serializers = CustomUserAvatarSerializer(user, data=request.data)
            serializers.is_valid(raise_exception=True)
            serializers.save()
            return Response(serializers.data, status=status.HTTP_200_OK)
        user.avatar = None
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['post', 'delete'],
        detail=True
    )
    def subscribe(self, request, id):
        user = request.user
        author = get_object_or_404(User, id=id)
        if request.method == 'POST':
            if Follow.objects.filter(follower=user, author=author).exists():
                return Response(
                    'Вы уже подписаны на этого автора',
                    status=status.HTTP_400_BAD_REQUEST
                )
            if user == author:
                return Response(
                    'Невозможно подписаться на самого себя',
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = FollowSerializer(
                author,
                context={"request": request, }
            )
            Follow.objects.create(follower=user, author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if not Follow.objects.filter(follower=user, author=author).exists():
            return Response(
                'Подписки не найдено',
                status=status.HTTP_400_BAD_REQUEST
            )
        subscribe = get_object_or_404(Follow, follower=user, author=author)
        subscribe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['get', ],
        detail=False,
    )
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(author__follower=user)
        pages = self.paginate_queryset(queryset)
        serializer = FollowSerializer(
            pages, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)
