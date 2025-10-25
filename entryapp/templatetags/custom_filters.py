from django import template
import json

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary using a key.
    Usage: {{ dictionary|get_item:key }}
    """
    try:
        return dictionary.get(key)
    except:
        return None

@register.filter
def get_item_or_none(dictionary, key):
    """
    Get an item from a dictionary or return None if key doesn't exist.
    Usage: {{ dictionary|get_item_or_none:key }}
    """
    return dictionary.get(key) if dictionary else None

@register.filter
def sum(list):
    """
    Calculate the sum of a list of numbers.
    Usage: {{ list|sum }}
    """
    try:
        return sum(list)
    except:
        return 0

@register.filter
def mul(value, arg):
    """
    Multiply value by arg.
    Usage: {{ value|mul:arg }}
    """
    try:
        return value * arg
    except:
        return 0

@register.filter
def json_script(value):
    """
    Convert a Python object to a JSON string for use in JavaScript.
    Usage: {{ value|json_script }}
    """
    return json.dumps(value)