from django import template
from django.forms.boundfield import BoundField

register = template.Library()

@register.filter(name="addclass")
def addclass(field, css):
    if isinstance(field, BoundField):
        return field.as_widget(attrs={"class": css})
    elif hasattr(field, 'widget'):
        return field.widget.render(field.html_name, field.value(), attrs={"class": css})
    return field

@register.filter(name="get_item")
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter(name="mul")
def mul(value, arg):
    """Multiply the arg by the value"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
