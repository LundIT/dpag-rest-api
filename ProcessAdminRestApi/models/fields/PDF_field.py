from django.db.models import TextField, FileField


class PDFField(FileField):
    max_length = 300
    pass