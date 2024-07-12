from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from users.models import MyUser, Follow
from users.serializers import (
    CustomUserSerializer,
    FollowSerializer,
    CustomUserAvatarSerializer,
)


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
        user = get_object_or_404(MyUser, username=request.user)
        if request.method == 'PUT':
            serializers = CustomUserAvatarSerializer(user, data=request.data)
            if serializers.is_valid():
                serializers.save()
                return Response(serializers.data, status=status.HTTP_200_OK)
            return Response(status=status.HTTP_400_BAD_REQUEST)
        user.avatar = None
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['post', 'delete'],
        detail=True
    )
    def subscribe(self, request, id):
        user = request.user
        author = get_object_or_404(MyUser, id=id)
        if request.method == 'POST':
            if Follow.objects.filter(follower=user, author=author).exists():
                raise ValidationError('Вы уже подписаны на этого автора')
            if user == author:
                raise ValidationError('Невозможно подписаться на самого себя')
            serializer = FollowSerializer(
                author,
                context={"request": request, }
            )
            Follow.objects.create(follower=user, author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if not Follow.objects.filter(follower=user, author=author).exists():
            raise ValidationError('Подписки не найдено')
        subscribe = get_object_or_404(Follow, follower=user, author=author)
        subscribe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['get', ],
        detail=False,
    )
    def subscriptions(self, request):
        user = request.user
        queryset = MyUser.objects.filter(author__follower=user)
        pages = self.paginate_queryset(queryset)
        serializer = FollowSerializer(
            pages, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)
