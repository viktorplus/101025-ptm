from django.urls import path
from rest_framework.routers import SimpleRouter, DefaultRouter


from library.views import book_list_create
from library.class_views import (
    BookListCreateAPIView,
    BookRetrieveUpdateDestroyAPIView,
    CategoryListCreateGenericAPIView,
    CategoryRetrieveUpdateDestroyGenericView,
    AuthorListCreateGenericView,
    UserListGenericView,
    BookListGenericView,
    PublisherViewSet,
    AuthorViewSet
)


router = SimpleRouter()
# router = DefaultRouter()
router.register('publishers', PublisherViewSet)
router.register('authors', AuthorViewSet)
#
# publishers/
# publishers/<regular expression>/


# api/v1/books/
urlpatterns = [
    # path('books/', book_list_create),
    # path('books/', BookListCreateAPIView.as_view()),
    path('books/', BookListGenericView.as_view()),
    path('books/<int:pk>/', BookRetrieveUpdateDestroyAPIView.as_view()),
    path('categories/', CategoryListCreateGenericAPIView.as_view()),
    path('categories/<str:name>/', CategoryRetrieveUpdateDestroyGenericView.as_view()),
    # path('authors/', AuthorListCreateGenericView.as_view()),
    path('users/', UserListGenericView.as_view()),
]


# print(router.urls)
urlpatterns += router.urls




# PK = 1234
# PK (uuid) = 'asd8f6-865sms-sknjf6-alan27'