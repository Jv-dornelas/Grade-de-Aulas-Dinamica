from django import template

register = template.Library()

@register.filter(name='dict_get')
def dict_get(dictionary, key):
    if dictionary is None:
        return None
    return dictionary.get(key)