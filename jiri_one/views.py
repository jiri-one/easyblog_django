from jiri_one.models import Post, Comment
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.db.models import Q
from django.shortcuts import redirect

class PostDetailView(DetailView):
    model = Post
    slug_field = 'url_cze'
    slug_url_kwarg = 'url_cze'
    template_name = 'post.html'
    
    def post(self, request, *args, **kwargs):
        header = request.POST.get('comment_header')
        nick = request.POST.get('comment_nick')
        content = request.POST.get('comment_content')
        Comment.objects.create(post=self.get_object(), title=header, nick=nick,content=content)
        return redirect(request.path)


class PostListView(ListView):
    model = Post
    template_name = 'index.html'
    paginate_by = 10
        
    def get(self, request, *args, **kwargs):
        if 'strana' in kwargs:
            self.page_kwarg = 'strana'
        if 'tag' in kwargs:
            self.queryset = self.model.objects.filter(tags__url_cze=kwargs["tag"]).all()
        if 'search' in kwargs or 'hledej' in kwargs:
            if not (searched_word := kwargs.get("search")):
                searched_word = kwargs.get("hledej")
            self.queryset = self.model.objects.filter(
                Q(content_cze__icontains=searched_word) 
                | Q(title_cze__icontains=searched_word))
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        searched_word = request.POST.get('search') 
        return redirect(f'hledej/{searched_word}')
    
