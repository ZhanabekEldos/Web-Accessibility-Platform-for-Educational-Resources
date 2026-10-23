"""Правила доступности. Импорт модулей регистрирует правила в ``REGISTRY``.

Чтобы добавить новую группу правил, создайте модуль рядом и добавьте его в список ниже.
"""
from . import aria, color, forms, images, keyboard, language, links, media, structure  # noqa: F401
