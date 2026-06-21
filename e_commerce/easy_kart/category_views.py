from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from .models import Category


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser


class CategoryListView(ListView):
    model = Category
    template_name = 'categories/category_list.html'
    context_object_name = 'categories'
    paginate_by = 20


class CategoryDetailView(DetailView):
    model = Category
    template_name = 'categories/category_detail.html'
    context_object_name = 'category'


class CategoryCreateView(AdminRequiredMixin, CreateView):
    model = Category
    fields = ['name', 'slug', 'description', 'image', 'is_active']
    template_name = 'categories/category_form.html'
    success_url = reverse_lazy('category_list')

    def form_valid(self, form):
        messages.success(self.request, 'Category created successfully.')
        return super().form_valid(form)


class CategoryUpdateView(AdminRequiredMixin, UpdateView):
    model = Category
    fields = ['name', 'slug', 'description', 'image', 'is_active']
    template_name = 'categories/category_form.html'
    success_url = reverse_lazy('category_list')

    def form_valid(self, form):
        messages.success(self.request, 'Category updated successfully.')
        return super().form_valid(form)


class CategoryDeleteView(AdminRequiredMixin, DeleteView):
    model = Category
    template_name = 'categories/category_confirm_delete.html'
    success_url = reverse_lazy('category_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Category deleted successfully.')
        return super().delete(request, *args, **kwargs)
