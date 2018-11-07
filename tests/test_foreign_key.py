import pytest
import sqlalchemy as sa

from sqlalchemy_unchained import foreign_key


def test_it_works_with_a_class(db):
    class FakeModel(db.Model):
        __tablename__ = 'custom_tablename'

    col = foreign_key(FakeModel)
    assert col.name is None
    assert list(col.foreign_keys)[0]._get_colspec() == 'custom_tablename.id'

    col = foreign_key(FakeModel, fk_col='pk')
    assert col.name is None
    assert list(col.foreign_keys)[0]._get_colspec() == 'custom_tablename.pk'

    col = foreign_key('custom_column', FakeModel)
    assert col.name == 'custom_column'
    assert list(col.foreign_keys)[0]._get_colspec() == 'custom_tablename.id'

    col = foreign_key('custom_column', FakeModel, fk_col='pk')
    assert col.name == 'custom_column'
    assert list(col.foreign_keys)[0]._get_colspec() == 'custom_tablename.pk'


def test_it_works_with_a_class_name():
    col = foreign_key('ClassName')
    assert col.name is None
    assert list(col.foreign_keys)[0]._get_colspec() == 'class_name.id'

    col = foreign_key('ClassName', fk_col='pk')
    assert col.name is None
    assert list(col.foreign_keys)[0]._get_colspec() == 'class_name.pk'

    col = foreign_key('custom_column', 'ClassName')
    assert col.name == 'custom_column'
    assert list(col.foreign_keys)[0]._get_colspec() == 'class_name.id'

    col = foreign_key('custom_column', 'ClassName', fk_col='pk')
    assert col.name == 'custom_column'
    assert list(col.foreign_keys)[0]._get_colspec() == 'class_name.pk'


def test_it_works_with_a_table_name():
    col = foreign_key('a_table_name')
    assert col.name is None
    assert list(col.foreign_keys)[0]._get_colspec() == 'a_table_name.id'

    col = foreign_key('a_table_name', fk_col='pk')
    assert col.name is None
    assert list(col.foreign_keys)[0]._get_colspec() == 'a_table_name.pk'

    col = foreign_key('custom_column', 'a_table_name')
    assert col.name == 'custom_column'
    assert list(col.foreign_keys)[0]._get_colspec() == 'a_table_name.id'

    col = foreign_key('custom_column', 'a_table_name', fk_col='pk')
    assert col.name == 'custom_column'
    assert list(col.foreign_keys)[0]._get_colspec() == 'a_table_name.pk'


def test_it_requires_a_table_name():
    with pytest.raises(TypeError) as e:
        col = foreign_key()
    assert 'Could not determine the table name to use.' in str(e)


def test_it_works_with_all_three(db):
    class FakeModel(db.Model):
        __tablename__ = 'custom_tablename'

    col = foreign_key('custom_col_name', 'TheModelClass', sa.String)
    assert col.name == 'custom_col_name'
    assert list(col.foreign_keys)[0]._get_colspec() == 'the_model_class.id'

    col = foreign_key('custom_col_name', FakeModel, sa.String)
    assert col.name == 'custom_col_name'
    assert list(col.foreign_keys)[0]._get_colspec() == 'custom_tablename.id'


def test_only_custom_column_name_must_be_first(db):
    class FakeModel(db.Model):
        __tablename__ = 'custom_tablename'

    col = foreign_key('custom_col_name', sa.String, 'TheModelClass')
    assert col.name == 'custom_col_name'
    assert list(col.foreign_keys)[0]._get_colspec() == 'the_model_class.id'

    col = foreign_key('custom_col_name', sa.String, FakeModel)
    assert col.name == 'custom_col_name'
    assert list(col.foreign_keys)[0]._get_colspec() == 'custom_tablename.id'

    col = foreign_key(sa.String, 'CustomColName', 'zee_tablename')
    assert col.name == 'CustomColName'
    assert list(col.foreign_keys)[0]._get_colspec() == 'zee_tablename.id'
