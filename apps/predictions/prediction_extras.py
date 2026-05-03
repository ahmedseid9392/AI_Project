from django import template

register = template.Library()

@register.filter
def replace_underscore(value):
    """Replaces underscores with spaces and titles the string"""
    if isinstance(value, str):
        return value.replace('_', ' ').title()
    return value