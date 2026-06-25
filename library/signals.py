from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from library.models import Category


# # receiver= регистратор   post_save = тип сигнала   sender = отправитель сигнала
# @receiver(post_save, sender=Category)
# def category_saved(sender: Category, instance: Category, created: bool, **kwargs) -> None:  # сам обработчик сигнала (что нужно сделать, если сигнал сработал)
#     if created:
#         print("=" * 100)
#         print(f"New Category object was CREATED. It's name is: '{instance.name}'")
#         print("=" * 100)
#     else:
#         print("=" * 100)
#         print(f"Category object was UPDATED. New name is: '{instance.name}'")
#         print("=" * 100)


# receiver= регистратор   post_save = тип сигнала   sender = отправитель сигнала
@receiver(pre_save, sender=Category)
def track_old_category_name(sender: Category, instance: Category, **kwargs) -> None:  # сам обработчик сигнала (что нужно сделать, если сигнал сработал)
    if not instance.pk:
        instance._old_category_name = None

        return

    try:
        old_obj = Category.objects.get(pk=instance.pk)
        instance._old_category_name = old_obj.name
    except Category.DoesNotExist:
        instance._old_category_name = None


@receiver(post_save, sender=Category)
def category_post_save_notify(sender: Category, instance: Category, created: bool, **kwargs) -> None:  # сам обработчик сигнала (что нужно сделать, если сигнал сработал)
    if created:
        print("=" * 100)
        print(f"New Category object was CREATED. It's name is: '{instance.name}'")
        print("=" * 100)
        return

    old_name = getattr(instance, '_old_category_name', None)
    current_name = instance.name

    if old_name == current_name:
        print("=" * 100)
        print("Nothing changed")
        print("=" * 100)
        return

    def print_changes():
        print(f"Category name was updated from '{old_name}' to -> -> {current_name}")

    transaction.on_commit(print_changes)
