# from apps.company.models import ExampleModel
#
# class ExampleService:
#     @staticmethod
#     def create_example(name, description=""):
#         return ExampleModel.objects.create(
#             name=name,
#             description=description
#         )
#     
#     @staticmethod
#     def get_example_by_uuid(uuid):
#         try:
#             return ExampleModel.objects.get(uuid=uuid)
#         except ExampleModel.DoesNotExist:
#             return None
