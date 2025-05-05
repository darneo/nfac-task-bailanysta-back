
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Post, Profile, Comment, Like, Notification
from utils.s3 import *

User = get_user_model()


from rest_framework import serializers
from .models import Profile, User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        extra_kwargs = {
            'email': {'required': True}
        }

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, Follow

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def validate(self, data):
        if len(data['password']) < 8:
            raise serializers.ValidationError("Пароль должен быть не менее 8 символов.")
        return data


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['id', 'user', 'bio', 'avatar_url', 'followers_count', 'following_count']

    def get_followers_count(self, obj):
        return Follow.objects.filter(following=obj.user).count()

    def get_following_count(self, obj):
        return Follow.objects.filter(follower=obj.user).count()

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        instance.bio = validated_data.get('bio', instance.bio)

        avatar = validated_data.get('avatar', None)  # Если прислан файл
        if avatar:
            file_name = f"avatars/{instance.user.username}/{os.path.basename(avatar.name)}"
            file_url = upload_to_s3(avatar, file_name)
            instance.avatar_url = file_url  # Сохраняем URL в базе данных

        if 'username' in user_data:
            instance.user.username = user_data['username']
            instance.user.save()

        instance.save()
        return instance


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['id', 'user', 'bio', 'avatar_url', 'followers_count', 'following_count']  # заменено 'avatar' на 'avatar_url'

    def get_followers_count(self, obj):
        return Follow.objects.filter(following=obj.user).count()

    def get_following_count(self, obj):
        return Follow.objects.filter(follower=obj.user).count()

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        instance.bio = validated_data.get('bio', instance.bio)
        instance.avatar_url = validated_data.get('avatar_url', instance.avatar_url)  # обновление avatar_url

        if 'username' in user_data:
            instance.user.username = user_data['username']
            instance.user.save()

        instance.save()
        return instance



class PostSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ['id', 'user', 'content', 'created_at', 'comments_count', 'is_liked']

    def get_comments_count(self, obj):
        return Comment.objects.filter(post=obj).count()

    def get_user(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username
        }

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Like.objects.filter(post=obj, user=request.user).exists()
        return False


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    post = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'user', 'post', 'content', 'created_at']


from rest_framework_simplejwt.authentication import JWTAuthentication


class BearerTokenAuthentication(JWTAuthentication):
    """
    Custom authentication class that validates Bearer tokens in the Authorization header
    """

    def get_header(self, request):
        header = super().get_header(request)
        if header and header.decode('utf-8').startswith('Bearer '):
            return header
        return None

    def get_raw_token(self, header):
        if header is None:
            return None
        parts = header.decode('utf-8').split()
        if len(parts) == 2 and parts[0] == 'Bearer':
            return parts[1]
        return None

class NotificationSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'sender_username', 'recipient_username', 'message', 'is_read', 'created_at']