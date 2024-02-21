from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class TokenObtainPairWithUserSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super(TokenObtainPairWithUserSerializer, self).validate(attrs)
        data.update({'user': {'username': self.user.username}})
        return data


class TokenObtainPairWithUserView(TokenObtainPairView):
    serializer_class = TokenObtainPairWithUserSerializer
