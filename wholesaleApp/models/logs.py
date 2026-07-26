from django.db import models
from django.contrib.auth.models import User
from wholesaleApp.models.tenant import TenantModel

class ActivityLog(TenantModel):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, verbose_name="Action") # e.g., CREATE, UPDATE, DELETE
    model_name = models.CharField(max_length=100, verbose_name="Module / Model")
    object_id = models.IntegerField(null=True, blank=True, verbose_name="Object ID")
    object_repr = models.CharField(max_length=255, verbose_name="Object Name / Info")
    description = models.TextField(verbose_name="Details")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Logged At")

    class Meta:
        verbose_name = "Activity Log"
        verbose_name_plural = "Activity Logs"
        ordering = ['-timestamp']

    def __str__(self):
        username = self.user.username if self.user else "System"
        return f"{username} - {self.action} {self.model_name} ({self.object_repr})"
