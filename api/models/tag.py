from django.db import models


class Tag(models.Model):
    id = models.AutoField('id', primary_key=True)
    tag = models.CharField("Tag", max_length=40)

    def __str__(self) -> str:
        return self.tag
