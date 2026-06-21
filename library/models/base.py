# После этого файлика можно перейти в models.category, там продолжение

from django.db import models
from django.db.models.manager import BaseManager
from django.utils import timezone


# Зачем выносить логику в отдельный QuerySet, а не оставить её в менеджере?
#
# Менеджер — это «точка входа» (Book.objects), которая возвращает QuerySet.
# Цепочки методов (.filter(...).delete(), .alive().filter(...)) вызываются уже
# на QuerySet, а не на менеджере. Если переопределить delete() только в менеджере,
# то вызов Book.objects.filter(...).delete() снова провалится в стандартный
# QuerySet.delete() и выполнит физическое удаление — менеджер к этому моменту
# уже «вышел из игры».
#
# Поэтому правило такое:
#   • Поведение цепочек (.alive(), .dead(), .delete()) → в QuerySet.
#   • Точка входа и фильтр по умолчанию → в Manager через get_queryset().
class SoftDeletionQuerySet(models.QuerySet):

    def delete(self):
        return super().update(
            deleted_at=timezone.now()
        )

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(
            deleted_at__isnull=True
        )

    def dead(self):
        return self.filter(
            deleted_at__isnull=False
        )


# Менеджер переопределяет get_queryset(), чтобы по умолчанию
# возвращать только живые записи. Вся остальная логика делегирована
# в SoftDeletionQuerySet: менеджер лишь «стартует» с нужным фильтром.
#
# Обратите внимание: менеджер наследуется от BaseManager[SoftDeletionQuerySet],
# а не от стандартного Manager. Это позволяет Django корректно использовать
# наш QuerySet при клонировании (например, при .all() или слайсах),
# не откатываясь к базовому QuerySet.
class SoftDeletionManager(BaseManager.from_queryset(SoftDeletionQuerySet)):

    def get_queryset(self):
        return SoftDeletionQuerySet(
            self.model,
            using=self._db
        ).alive()



# абстрактная модель, которая добавляет поле deleted_at
# и переопределяет delete() для любой модели, подключившей этот миксин.
class SoftDeletionModel(models.Model):

    deleted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        abstract = True

    # Менеджер по умолчанию — только живые записи.
    objects = SoftDeletionManager()

    # Запасной менеджер — все записи без фильтрации.
    # Нужен, например, для административных задач или восстановления.
    all_objects = models.Manager()

    def delete(self, using = None, keep_parents = False):
        self.deleted_at = timezone.now()


        # Зачем явно передавать update_fields?
        #
        # self.save() без update_fields генерирует UPDATE по всем полям модели.
        # Это создаёт две проблемы:
        #   1. Гонка данных: если между чтением объекта и его сохранением
        #      другой процесс изменил любое другое поле, то save() перезапишет
        #      эти изменения старыми значениями из памяти.
        #   2. Лишняя нагрузка: обновляются поля, которые не менялись.
        #
        # update_fields={'deleted_at'} гарантирует точечный UPDATE:
        #   UPDATE mytable SET deleted_at = NOW() WHERE id = <id>
        # — только то поле, которое мы действительно хотим изменить.
        self.save(
            update_fields={'deleted_at'}
        )

    def hard_delete(self, using = None, keep_parents = False):
        return super().delete(using, keep_parents)
