from app.infrastructure.documents.sqlite_templates_legacy import Base, Template, TemplateField


def test_sqlite_legacy_models_have_tablenames():
    assert Template.__tablename__ == "templates"
    assert TemplateField.__tablename__ == "template_fields"
    assert Base.metadata.tables["templates"] is not None
