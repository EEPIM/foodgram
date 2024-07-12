from django.core.files.base import ContentFile
from djoser.serializers import UserSerializer, UserCreateSerializer
import base64
from rest_framework import serializers

from recipes.models import Recipes
from users.models import MyUser, Follow


class Base64ImageField(serializers.ImageField):
    """Сериализатор для картинок"""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class CustomUserCreateSerializer(UserCreateSerializer):
    """Сериализатор для редактирования пользователя."""

    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)

    class Meta:
        model = MyUser
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'password',
        )


class CustomUserSerializer(UserSerializer):
    """Сериализатор для просмотра пользователя"""

    avatar = Base64ImageField(required=False, allow_null=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = MyUser
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'avatar',
            'is_subscribed',
        )

    def get_is_subscribed(self, obj):
        return (
            self.context.get('request').user.is_authenticated
            and Follow.objects.filter(
                follower=self.context.get('request').user,
                author=obj.id
            ).exists()
        )


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для краткой информации рецептов"""

    image = serializers.CharField()

    class Meta:
        model = Recipes
        fields = ('id', 'name', 'image', 'cooking_time')


class CustomUserAvatarSerializer(UserSerializer):
    """Сериализатор для аватара пользователя"""

    avatar = Base64ImageField()

    class Meta:
        model = MyUser
        fields = (
            'avatar',
        )


class FollowSerializer(CustomUserSerializer):
    """Сериализатор для подписок"""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = MyUser
        fields = (
            'username',
            'id',
            'email',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar'
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        recipes = Recipes.objects.filter(author=obj.id)
        if limit:
            recipes = recipes[:int(limit)]
        serializer = ShortRecipeSerializer(recipes, many=True, read_only=True)
        return serializer.data

    def get_recipes_count(self, obj):
        return Recipes.objects.filter(author=obj.id).count()
