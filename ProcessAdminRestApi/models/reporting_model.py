from django.db.models import Model


class ReportingModelMixin(Model):
    """
    Reporting Models allows the User to download the files as indicated in reporting_fields.
    """
    input = False
    reporting_fields = []

    class Meta:
        abstract = True
