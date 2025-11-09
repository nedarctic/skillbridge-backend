from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import UserViewSet, ProfileViewSet, RatingViewSet, ReviewViewSet

router = SimpleRouter()
router.register('users', UserViewSet, basename='users')
router.register('profiles', ProfileViewSet, basename='profiles')
router.register('ratings', RatingViewSet, basename='ratings')
router.register('reviews', ReviewViewSet, basename='reviews')

urlpatterns = router.urls