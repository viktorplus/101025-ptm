# import os
# import django
#
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
# django.setup()


# СТРОГО ПОСЛЕ django.setup()
# from test_app.models import Book, Author, User, Post

# publisher = User.objects.get(id=1)

# Book.objects.create(
#     title="Старик и Море",
#     language="ua",
#     genre="triller",
#     publisher=publisher,
#     price=7.30,
#     published_date="2026-04-4" # даты заполняем в ISO формате (YYYY-MM-DD)
# )

# при методе create "под капотом" будут вызываны методы:
#     session.create()
#     session.add(new_obj)
#     session.commit()


# book = Book(
#     title="ВОйна и Мир",
#     language="ua",
#     genre="fiction",
#     publisher=publisher,
#     price=3.95,
#     published_date="2022-03-13"
# )
#
# book.description = "Какое-то большщое описание книги"
#
# book.save()
#


# books = Book.objects.all()  # => SQL DML => SELECT * FROM 'books';
#
# print(books.query)
# print(type(books))
# print(books)
#
#
# for book in books:
#     print(book.title)




# методы, которые возвращают QuerySet

# .all()  - возвращает всё



# .filter() - возвращает только те записи, которые прошли фильтр условие

# only_en_books = Book.objects.filter(
#     language='en'
# )
#
# print(only_en_books)


# only_ua_books = Book.objects.filter(
#     language='ua'
# ).first()
#
# print(only_ua_books)

# only_ua_books = Book.objects.get(title="Старик и Море")
#
# print(only_ua_books)


# count_of_books = Book.objects.count()
#
# print(f"КОл-во книг в базе: {count_of_books}")


# .values() - возвращает всё, но в виде списка словарей с конкретными
# колонками, что мы укажем. Учавствует в группировках


# books = Book.objects.values('id', 'title', 'price', 'published_date')
#
# print(books.query)
#
# print(books)
#
# for book in books:
#     print(f"{book['title']} | {book['published_date']}")



# .exclude() - возвращает все записи, КРОМЕ тех ЧТО ПРОШЛИ фильтр условие
# .only() - возвращает всё, но с конкретными колонками, что мы укажем
# .annotate() - возвращает набор данных с новыми, кастомными полями




# GET


# Передаём ТОЛЬКО УНИКАЛЬНЫЕ КОЛОНКИ
# try:
#     # book = Book.objects.get(language='ua')
#     book = Book.objects.get(id=123123123123123123123123123123123123)
#
#     print(book)
# except Book.MultipleObjectsReturned as err:
#     print(str(err))
#
# except Book.DoesNotExist as err:
#     print(str(err))


# books = Book.objects.filter(
#     # language='UA'
#     language__iexact='UA'
# )
#
# print(books)


# books = Book.objects.filter(
#     # title__contains='er'
#     title__icontains='ER'  # LIKE
# )
#
# print(books.query)
# print(books)


# books = Book.objects.filter(
#     id__in=[1, 3]
# )
#
# print(books.query)
# print(books)
#
#
# books = Book.objects.filter(
#     price__in=[19.99, 3.95]
# )
#
# print(books.query)
# print(books)


# books = Book.objects.filter(
#     price__gt=13
# )

# books = Book.objects.filter(
#     price__gte=7.3
# )
#
# print(books.query)
# print(books)


# books = Book.objects.filter(
#     price__gte=7.3,
#     genre='fiction'
# )
#
# print(books.query)
# print(books)


# books = Book.objects.filter(
#     title__endswith='ita'
# )
#
# print(books.query)
#
# print(books)

# books = Book.objects.filter(
#     genre__startswith='f'
# )
#
# print(books.query)
# print(books)


# books = Book.objects.raw(
#     """
#     SELECT * FROM ...
#     """
# )
#
# print(books.query)
# print(books)


# books = Book.objects.filter(
#     description__isnull=False
# )
#
# print(books.query)
# print(books)


# books = Book.objects.filter(
#     price__range=[7, 15]  # BETWEEN ... AND ...
# )
#
# print(books.query)
# print(books)





from django.db.models import Q


#   SQL       ORM(Q)

#   AND         & Q()
#   OR          | Q()
#   NOT         ~Q()


# books = Book.objects.filter(
#     Q(language='en') | Q(published_date__year=2022)
# )
#
#
# print(books.query)
# print(books)



# books = Book.objects.filter(
#     ~Q(title__iendswith='witcher')
# )
#
# print(books.query)
# print(books)



# books = Book.objects.filter(
#     (Q(description__isnull=False) | ~Q(published_date__year=2025)) & ~Q(publisher_id=1)
# )
#
# print(books.query)
# print(books)











# Обновление записей и F классы


from django.db.models import F



# book = Book.objects.get(id=1)
#
# book.genre = 'fiction'
# book.language = 'de'
#
# book.save()


# books = Book.objects.all()
#
# books.update(price=9.99)


# books = Book.objects.all()
#
# books.update(
#     discounted_price=F('price') * 0.8
# )


# posts = [
#     Post(title='title1', content='content1'),
#     Post(title='title2', content='content2'),
#     Post(title='title3', content='content3'),
#     Post(title='title4', content='content4'),
# ]
#
# Post.objects.bulk_create(
#     posts
# )



# post = Post.objects.get(id=4)
#
#
# post.delete()



# =================================================
# WORK WITH AUTHTOKEN


import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# from rest_framework.authtoken.models import Token
# from library.models import User
#
#
# try:
#     user = User.objects.get(username="vlad")
#
#     # try:
#     #     token = Token.objects.get(user=user)
#     #
#     # except Token.DoesNotExist:
#     #     token = Token.objects.create(user=user)
#
#     token, created = Token.objects.get_or_create(user=user)
#
#     print(token.key)
#
# except User.DoesNotExist:
#     print("User not found")




# user = User.objects.get(username='vlad')
#
# book = Book.objects.create(
#     name="",
#     name="",
#     name="",
#     name="",
#     name="",
#     owner=user
# )



class User:

    name = "Vlad"
    age = 18



user = User()


print(user)

print(user.age)
print(user.name)

print("add new params!!!!")

user.new_param = "OUR NEW PARAM"

print(user.new_param)
