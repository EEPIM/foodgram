from rest_framework import serializers
# from django.core.validators import RegexValidator
from users.models import MyUser, Follow
from recipes.models import Recipes
# from django.contrib.auth import authenticate, get_user_model
from djoser.serializers import UserSerializer, UserCreateSerializer
from django.core.files.base import ContentFile
import base64
# from recipes.serializers import ShortRecipeSerializer

# SAME_DATA_REGISTRATION =
# 'Пользователь с таким учетными данными уже существует'
# USERNAME_ME = 'Нельзя использовать имя me.'
# CONST_ME = 'me'

# User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]  
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class CustomUserCreateSerializer(UserCreateSerializer):

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

    # avatar = Base64ImageField(required=False, allow_null=True)

    is_subscribed = serializers.SerializerMethodField()

    # def update(self, instance, validated_data):
    #     instance.avatar = validated_data.get('avatar', instance.avatar)
    #     instance.save()
    #     return instance

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
        user = self.context.get('request').user
        if user.is_anonymous:
            print(False)
            return False
        print(Follow.objects.filter(follower=user, author=obj))
        return Follow.objects.filter(follower=user, author=obj.id).exists()

    # def get_is_subscribed(self, obj):
    #     """Проверка подписки"""
    #     user_id = self.context.get('request').user.id
    #     return Follow.objects.filter(
    #         author=obj.id, follower=user_id
    #     ).exists()


class CustomUserAvatarSerializer(UserSerializer):

    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = MyUser
        fields = (
            'avatar',
        )


class FollowSerializer(CustomUserSerializer):

    recipes = serializers.SerializerMethodField()
    # is_subscribed = serializers.BooleanField(default=False)
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
        recipes = obj.recipes.all()
        if limit:
            recipes = recipes[:int(limit)]
        serializer = ShortRecipeSerializer(recipes, many=True, read_only=True)
        return serializer.data

    def get_recipes_count(self, obj):
        return obj.recipes.count()
