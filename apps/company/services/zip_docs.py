import zipfile
from io import BytesIO
from django.http import HttpResponse
from rest_framework.decorators import action




def zip_docs(company):

    buffer = BytesIO()
    # Создаем zip в памяти
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:

        for document in company.documents.prefetch_related('versions'):
            print(document)
            try:
                doc_folder = document.document_type.name
            except:
                doc_folder = 'Нет типа документа'

            for version in document.versions.all():
                if not version.file:
                    continue
                print(version.file)
                file_path = version.file.path
                file_name = version.file.name.split('/')[-1]

                # Путь внутри архива
                zip_path = f"{company.name}/{doc_folder}/v{version.version}/{file_name}"

                zip_file.write(file_path, zip_path)

    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/zip'
    )
    response['Content-Disposition'] = f'attachment; filename="{company.name}_documents.zip"'

    return response
