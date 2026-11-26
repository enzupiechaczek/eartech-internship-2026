from django import template

register = template.Library()


@register.filter
def with_aria(bound_field):
    """Render a widget with aria-invalid/aria-describedby when it has errors,
    so screen readers announce the error message."""
    if not bound_field.errors:
        return bound_field.as_widget()
    return bound_field.as_widget(attrs={
        "aria-invalid": "true",
        "aria-describedby": f"{bound_field.auto_id}_error",
    })
