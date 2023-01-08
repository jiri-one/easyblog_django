from django.db import models


class TaskResult(models.Model):
    name = models.CharField(max_length=250)

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, default=None)

    success = models.BooleanField(null=True, default=None)

    output = models.TextField()

    def __str__(self):
        return self.name

    class Meta:

        index_together = (
            ('name', 'started_at'),
        )
