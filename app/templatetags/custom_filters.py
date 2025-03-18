from django import template

register = template.Library()

@register.filter
def trim_leading_dot(value):
    """Remove the leading dot if it exists."""
    return value[1:] if value.startswith('.') else value