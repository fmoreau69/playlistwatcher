from django import template
from posts.models import Post

register = template.Library()


@register.filter(name="row_color")
def row_color(post: Post) -> str:
    if not isinstance(post, Post):
        return "#ffffff"
    if post.status == Post.STATUS_SENT:
        return "#d1e7dd"  # success subtle
    if post.status in (Post.STATUS_SCHEDULED, Post.STATUS_PENDING):
        return "#fff3cd"  # warning subtle
    if post.status in (Post.STATUS_PARTIAL, Post.STATUS_FAILED):
        return "#f8d7da"  # danger subtle
    return "#ffffff"