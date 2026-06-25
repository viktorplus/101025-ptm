from typing import Any

from django.core.exceptions import ValidationError
from django.db.migrations import serializer
from django.db.models import Count, Model
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination, CursorPagination
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly


from rest_framework.views import APIView
from rest_framework.generics import (
    get_object_or_404,
    GenericAPIView,
    RetrieveUpdateDestroyAPIView,
    ListCreateAPIView,
    ListAPIView
)
from rest_framework.viewsets import ModelViewSet

from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from library.permissions import IsBookOwnerOrReadOnly, IsStaffAndOwner, CanGetStatistic
from library.serializers import (
    BookListSerializer,
    BookCreateUpdateSerializer,
    BookDetailSerializer,
    BookQueryParamsSerializer,
    CategorySerializer,
    # AuthorSerializer,
    AuthorListSerializer,
    AuthorCreateSerializer,
    UserListSerializer, PublisherListSerializer, PublisherCreateSerializer,
    PublisherUpdateSerializer, PublisherDetailSerializer, CategoryStatisticSerializer, UserLoginSerializer
)
from library.models import Book, Category, Author, User, Publisher, Review
from library.utils import set_jwt_cookies, clear_cookies
from query_debug import QueryDebug



class CustomPageNumberPaginator(PageNumberPagination):
    page_size = 15
    page_size_query_param = 'page-size'


class BookListCreateAPIView(APIView):

    def filter_queryset(self):
        qs = Book.objects.all()

        query_params = BookQueryParamsSerializer(data=self.request.query_params)
        print(query_params)
        query_params.is_valid(raise_exception=True)
        print(query_params.validated_data)

        author = query_params.validated_data.get('author')
        sort_by = query_params.validated_data.get('sort_by')
        sort_order = query_params.validated_data.get('sort_order')

        price_gt = query_params.validated_data.get('price_gt')
        price_lt = query_params.validated_data.get('price_lt')

        if author:
            qs = qs.filter(author__surname__icontains=author)

        if price_gt is not None:
            qs = qs.filter(price__gt=price_gt)

        if price_lt is not None:
            qs = qs.filter(price__lt=price_lt)

        if sort_by:
            ordering = sort_by

            if sort_order == "desc":
                ordering = f"-{sort_by}"

            qs = qs.order_by(ordering)

        return qs

    def get(self, request: Request, *args, **kwargs) -> Response:
        # books = Book.objects.all()  # -> [Book(1), ..., Book(1000)]
        books = self.filter_queryset()  # -> [Book(1), ..., Book(1000)]
        serializer = BookListSerializer(books, many=True)
        return Response(
            data=serializer.data,  # -> [{'id', 1}, ..., {'id': 1000}]
            status=status.HTTP_200_OK
        )

    def post(self, request: Request, *args, **kwargs) -> Response:
        data = request.data  # {'name': "...", ...}
        serializer = BookCreateUpdateSerializer(data=data)

        if not serializer.is_valid():
            return Response(
                data=serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer.save()

        return Response(
            data=serializer.data,
            status=status.HTTP_201_CREATED
        )


class BookRetrieveUpdateDestroyAPIView(APIView):
    permission_classes = [IsBookOwnerOrReadOnly]

    def get_object(self):
        book = get_object_or_404(
            Book.objects.select_related('category', 'author', 'publisher'),
            pk=self.kwargs.get('pk')
        )

        self.check_object_permissions(self.request, book)

        return book

    def update(self, instance: Book, data: dict[str, Any], partial: bool = False):
        serializer = BookCreateUpdateSerializer(
            instance=instance,
            data=data,
            partial=partial
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            data=serializer.data,
            status=status.HTTP_200_OK
        )

    def get(self, request: Request, *args, **kwargs) -> Response:

        # print("=" * 100)
        # print(request.user)
        # print("=" * 100)


        book = self.get_object()
        serializer = BookDetailSerializer(book)
        return Response(
            data=serializer.data,
            status=status.HTTP_200_OK
        )

    def put(self, request: Request, *args, **kwargs) -> Response:
        book = self.get_object()
        data = request.data

        return self.update(
            book,
            data
        )

    def patch(self, request: Request, *args, **kwargs) -> Response:
        book = self.get_object()
        data = request.data

        return self.update(
            book,
            data,
            partial=True
        )

    def delete(self, request: Request, *args, **kwargs) -> Response:
        book = self.get_object()

        book.delete()

        return Response(
            data={},
            status=status.HTTP_204_NO_CONTENT
        )



class BookUpdateGenericView(RetrieveUpdateDestroyAPIView):
    queryset = Book.objects.all()
    permission_classes = [IsBookOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.request.method in {'PUT', 'PATCH'}:
            return BookCreateUpdateSerializer
        return BookDetailSerializer


class CategoryListCreateGenericAPIView(GenericAPIView):

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = CustomPageNumberPaginator

    def get(self, request: Request, *args, **kwargs) -> Response:
        categories = self.get_queryset()

        pag = self.paginate_queryset(categories)

        serializer = self.get_serializer(pag, many=True)

        return self.get_paginated_response(serializer.data)

        # return Response(
        #     data=serializer.data,
        #     status=status.HTTP_200_OK
        # )

    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        # if not serializer.is_valid():
        #     return Response(
        #         data=serializer.errors,
        #         status=status.HTTP_400_BAD_REQUEST
        #     )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            data=serializer.data,
            status=status.HTTP_201_CREATED
        )


class CategoryStatisticGenricView(ListAPIView):

    permission_classes = [CanGetStatistic]

    queryset = Category.objects.values('name').annotate(books_count=Count('books'))
    serializer_class = CategoryStatisticSerializer


class CategoryRetrieveUpdateDestroyGenericView(RetrieveUpdateDestroyAPIView):

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    # по какой колонке в БД будет идти поиск одного объекта
    lookup_field = 'name'

    # как должна называться динамичная переменная в урликах в запросе
    lookup_url_kwarg = 'name'


class AuthorListCreateGenericView(ListCreateAPIView):

    # queryset = Author.objects.all()  # какой набор данных возьмётся на ВСЮ вьюшку целиком
    # serializer_class = AuthorSerializer  # какой сериализатор будет взят на ВСЮ вьюшку целиком

    pagination_class = CustomPageNumberPaginator

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return AuthorListSerializer
        return AuthorCreateSerializer

    def get_queryset(self):
        """
        Используем, когда нужно, чтобы запрос на взятие данных мог динамически изменяться
        :return: итоговый набор данных
        """

        qs = Author.objects.all()

        # http://127.0.0.1:8000/api/v1/authors/?rating_gt=4
        rating_gt = self.request.query_params.get('rating_gt')
        rating_lt = self.request.query_params.get('rating_lt')

        if rating_gt:
            try:
                rating_gt = int(rating_gt)
                qs = qs.filter(rating__gt=rating_gt)
            except ValueError:
                # QuerySet([Obj(1), ..., Obj(100)]) -> -> qs.none() -> -> QuerySet([])
                qs = qs.none()  # если нам передали плохой рейтинг ("hello") -- "наказываем" за оплошность и ОЧИЩШАЕМ ВЕСЬ НАБОР ДАННЫХ

        if rating_lt:
            try:
                rating_lt = int(rating_lt)
                qs = qs.filter(rating__lt=rating_lt)
            except ValueError:
                # QuerySet([Obj(1), ..., Obj(100)]) -> -> qs.none() -> -> QuerySet([])
                qs = qs.none()  # если нам передали плохой рейтинг ("hello") -- "наказываем" за оплошность и ОЧИЩШАЕМ ВЕСЬ НАБОР ДАННЫХ

        return qs

    def create(self, request: Request, *args, **kwargs):

        if 'date_for_birth' not in request.data or not request.data.get('date_for_birth'):
            request.data['date_for_birth'] = timezone.now()

        return super().create(request, *args, **kwargs)






class UserListGenericView(ListAPIView):

    queryset = User.objects.prefetch_related('reviews')
    serializer_class = UserListSerializer


    def get_serializer_context(self):

        context = super().get_serializer_context()
        include_related = self.request.query_params.get('related', 'false')
        context['include_related'] = include_related.lower() == 'true'

        return context

    # этот класс мы можем использовать как декоратор. В этом помогает магический метод __call__
    # класс мы именно вызываем и можем (не обязательно) передать парметр file_name -- место, куда логи будут записываться
    @QueryDebug(file_name='user-list-query.log')
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)



class CustomCursorPaginator(CursorPagination):
    page_size = 10
    ordering = 'id'


class BookListGenericView(ListCreateAPIView):

    # queryset = Book.objects.all()
    serializer_class = BookListSerializer
    pagination_class = CustomCursorPaginator

    filter_backends = [
        DjangoFilterBackend, # фильтрация данных
        SearchFilter, # поиск объектов
        OrderingFilter # сортировку объектов
    ]

    filterset_fields = [
        'author',
        'price',
        'publisher',
        'category',
        'published_date',
    ]
    search_fields = [
        'name',
        'description',
    ]
    ordering_fields = [
        'id',
        'price',
        'published_date',
    ]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return BookListSerializer

        return BookCreateUpdateSerializer

    def get_queryset(self):
        qs = Book.objects.all()

        my = self.request.query_params.get('my')

        if my and my.strip().lower() == 'true':
            qs = qs.filter(owner=self.request.user)

        return qs

    def perform_create(self, serializer):
        serializer.validated_data['owner'] = self.request.user
        serializer.save()



# ================================================================================================

# VEW SETS

# ================================================================================================



class PublisherViewSet(ModelViewSet):
    queryset = Publisher.objects.all()

    # HTTP методы заменяются на self.actions
    #
    # GET -> list | retrieve | get_statistic_by_publisher
    # PUT -> update
    # PATCH -> partial_update
    # POST -> create
    # DELETE -> destroy

    # проверка на метод заменяется на проверку на action
    # if request.method  => => if self.action

    def get_serializer_class(self):
        # print(self.action)

        if self.action == 'list':
            return PublisherListSerializer
        elif self.action == 'create':
            return PublisherCreateSerializer
        elif self.action in {'update', 'partial_update'}:
            return PublisherUpdateSerializer

        return PublisherDetailSerializer


    # detail:
    # True -- работаем с одним конкретным объектом
    # False -- работаем со МНОГИМИ ОБЪЕКТАМИ
    @action(detail=True, methods=['get',])
    def get_statistic_by_publisher(self, request: Request, *args, **kwargs) -> Response:
        publisher = self.get_object()
        serializer = self.get_serializer(publisher)
        data = serializer.data
        data['count_of_books'] = publisher.books.count()

        return Response(
            data=data,
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get',])
    def get_statistic_by_publishers(self, request: Request, *args, **kwargs) -> Response:
        publishers = self.get_queryset()

        publishers = publishers.values('name').annotate(count_of_books=Count('books'))

        return Response(
            data=publishers,
            status=status.HTTP_200_OK
        )




# работа с транзакциями

from django.db import transaction, IntegrityError, DatabaseError


# transaction.atomic() -- основной инструмент. Генирирует
# атомарный блок. При любой ошибке в э\том блоке все изменения
# откатываются АВТОМАТИЧЕСКИ. Механизм умный, сам ставить savepoint
# перед началом транзакции, на каждой успешной частичке транзакции.
# Если ошибка -- сам прекрасно выполняет rollback. Если успех, сам
# прекрасно выполняет commit()


# transaction.on_commit() -- регистрирует callback (какая-то функция, которая будет вызвана) объект,
# который будет вызван при успешном коммите
# transaction.on_commit(callback=lambda: print('УСПЕХ'))


# НЕ БЕЗОПАСНЫЙ !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# transaction.set_autocommit(False) -- низкоуровневое управление транзакциями.
# Мы отключаем автокоммит и сами настраиваем поведение транзакции. ВАЖНО НЕ
# ЗАБЫТЬ ВКЛЮЧИТЬ ЕГО НАЗАД КАК ТОЛЬКО ТРАНЗАКЦИЯ БЫЛА ВЫПОЛНЕНА
# transaction.set_autocommit(True)




def notify_me():
    print("=" * 100)
    print("Транзакция отработала успешно, отправляю сообщение на email 'test.mail@gmail.com'")
    print("=" * 100)



class AuthorViewSet(ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorCreateSerializer
    permission_classes = [AllowAny]
    # permission_classes = [IsAdminUser]
    # authentication_classes = [TokenAuthentication]

    # HTTP methods заменяются на self.actions

    # GET    -> list | retrieve
    # POST   -> create
    # PUT    -> update
    # PATCH  -> partial_update
    # DELETE -> destroy
    # POST   -> create_author_with_books


    @action(detail=False, methods=['post'])
    def create_author_with_books(self, request: Request) -> Response:
        """
        Example: {
            "author": {
                "name": "Test",
                "surname": "Author"
            },
            "books": [
                {"name": "Book 1", "price": 9.99, "category": 1, "libraries": [1, 2]},
                {"name": "Book 2", "price": 15.31, "category": 2, "libraries": [2, 3]},
                {"name": "Book 3", "price": "dvadtsat' pyat'", "category": 3, "libraries": [1, 2, 3]}
            ]
        }
        :param request:
        :return:
        """

        author_data = request.data.get('author')
        books_data = request.data.get('books')

        # print("=" * 100)
        # print(author_data)
        # print("=" * 100)


        if not author_data or not (books_data, list):
            return Response(
                data={'message': 'Запрос должен содержать автора и СПИСОК книг'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # step 1 создание автора

                author_serializer = self.get_serializer(data=author_data)
                # author_serializer = AuthorCreateSerializer(data=author_data)
                author_serializer.is_valid(raise_exception=True)
                author = author_serializer.save()

                # step 2 создание книжек для этого автора

                for book in books_data:
                    book_serializer = BookCreateUpdateSerializer(data=book)
                    book_serializer.is_valid(raise_exception=True)
                    book_serializer.save(author=author)


                # transaction.on_commit(lambda : notify_me())
                transaction.on_commit(notify_me)

        except ValidationError as err:
            return Response(
                data={'error': str(err)},
                status=status.HTTP_400_BAD_REQUEST
            )

        except IntegrityError as err:
            return Response(
                data={'error': f"Нарушение целостности: {str(err)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        except DatabaseError as err:
            return Response(
                data={'error': f"Ошибка базы данных: {str(err)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            data={'author': author_serializer.data},
            status=status.HTTP_201_CREATED
        )

    def list(self, request: Request, *args, **kwargs):
        print("=" * 100)
        print(request.user)
        print("=" * 100)

        return super().list(request, *args, **kwargs)


class ReviewViewSet(ModelViewSet):
    permission_classes = [IsStaffAndOwner]
    queryset = Review.objects.all()

    # def get_serializer_class(self):
    #     ...


class LoginUser(APIView):

    permission_classes = [AllowAny]

    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        try:
            response = Response(status=status.HTTP_200_OK)

            set_jwt_cookies(response=response, user=user)

            return response
        except Exception as err:
            return Response(
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                data={
                    "message": str(err)
                }
            )


class LogoutUser(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, *args, **kwargs) -> Response:
        try:
            refresh_token = request.COOKIES.get('refresh_token')

            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except TokenError:
                    pass
        except Exception as err:
            return Response(
                data={
                    "message": str(err)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        response = Response(status=status.HTTP_200_OK)
        clear_cookies(response=response)

        return response
