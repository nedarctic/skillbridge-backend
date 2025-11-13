from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework import serializers
from django.conf import settings
from dj_rest_auth.serializers import PasswordResetSerializer
from django.contrib.auth import get_user_model
from .models import Profile, Rating, Review
from dj_rest_auth.serializers import LoginSerializer
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.utils.encoding import force_str
from dj_rest_auth.serializers import PasswordResetConfirmSerializer as _PasswordResetConfirmSerializer
from allauth.account.forms import default_token_generator


from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.core.mail import send_mail

User = get_user_model()

class CustomPasswordResetConfirmSerializer(_PasswordResetConfirmSerializer):

    def validate(self, attrs):
        """
        Overrides dj-rest-auth default to use:
        - allauth's default_token_generator
        - Django's urlsafe_base64_decode for uid
        """
        try:
            uid = force_str(urlsafe_base64_decode(attrs['uid']))
            self.user = User._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({'uid': ['Invalid value']})

        if not default_token_generator.check_token(self.user, attrs['token']):
            raise serializers.ValidationError({'token': ['Invalid value']})

        # Standard password validation
        self.set_password_form = self.set_password_form_class(user=self.user, data=attrs)
        if not self.set_password_form.is_valid():
            raise serializers.ValidationError(self.set_password_form.errors)

        return attrs

class CustomLoginSerializer(LoginSerializer):
    username = None  # disable username completely
    email = serializers.EmailField(required=True)
    
    def validate(self, attrs):
        # Replace username with email for authentication
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = self.authenticate(email=email, password=password)
        else:
            msg = 'Must include "email" and "password".'
            raise serializers.ValidationError(msg, code='authorization')

        if user:
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            attrs['user'] = user
            return attrs

        raise serializers.ValidationError('Unable to log in with provided credentials.')

class CustomRegisterSerializer(RegisterSerializer):
    username = None  # Disable username input
    first_name = serializers.CharField(max_length=50)
    last_name = serializers.CharField(max_length=50)

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data['first_name'] = self.validated_data.get('first_name', '')
        data['last_name'] = self.validated_data.get('last_name', '')
        data['email'] = self.validated_data.get('email', '')
        return data

    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name')
        user.save()
        return user

User = get_user_model()

class CustomPasswordResetSerializer(PasswordResetSerializer):

    token_generator = default_token_generator  # Add this line

    def get_email_options(self):
        def custom_url_generator(request, user, token):
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            return f"{settings.FRONTEND_URL}/reset/confirm?uidb64={uidb64}&token={token}"

        return {
            "url_generator": custom_url_generator,
            "extra_email_context": {
                "site_name": getattr(settings, "SITE_NAME", "SkillBridge"),
            },
        }

    def save(self, **kwargs):
        request = self.context.get("request")
        # Use Django's PasswordResetForm to get users
        reset_form = PasswordResetForm(data=self.validated_data)
        if not reset_form.is_valid():
            return

        for user in reset_form.get_users(self.validated_data["email"]):
            token = self.token_generator.make_token(user)  # Now works
            reset_url = self.get_email_options()["url_generator"](request, user, token)
            site_name = self.get_email_options()["extra_email_context"]["site_name"]

            subject = f"Reset your password on {site_name}"
            message = f"""
                Hi {user.get_full_name() or user.email},

                You requested a password reset on {site_name}.

                Click the link below to reset your password:

                {reset_url}

                If you did not request this, please ignore this email.

                Thanks,
                {site_name} Team
            """

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

        
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('id', 'username',)

class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('id', 'email', 'first_name', 'last_name')

class RatingSerializer(serializers.ModelSerializer):
    rated_by = UserDetailSerializer(read_only=True)
    
    class Meta:
        model = Rating
        fields = ('id', 'profile', 'score', 'rated_by', 'created_at')
        read_only_fields = ('rated_by',)

class ReviewSerializer(serializers.ModelSerializer):
    reviewed_by = UserDetailSerializer(read_only=True)
    
    class Meta:
        model = Review
        fields = ('id', 'profile', 'review_text', 'reviewed_by', 'created_at')
        read_only_fields = ('reviewed_by',)

class ProfileSerializer(serializers.ModelSerializer):
    user = UserDetailSerializer(read_only=True)
    ratings = RatingSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    name = serializers.CharField(read_only=True)
    
    class Meta:
        model = Profile
        fields = (
            'id', 
            'user',
            'name',
            'skill', 
            'experience',
            'location',
            'bio',
            'about',
            'profile_image',
            'average_rating',
            'total_reviews',
            'services',
            'ratings',
            'reviews'
        )
        read_only_fields = ('average_rating', 'total_reviews')

class ProfileCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = (
            'skill',
            'experience',
            'location',
            'bio',
            'about',
            'profile_image',
            'services'
        )

