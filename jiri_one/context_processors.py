from jiri_one.models import Tag

def tags_to_base(request):    
    tags = Tag.objects.all()
    return {'tags': tags}
