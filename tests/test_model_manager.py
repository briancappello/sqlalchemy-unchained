import pytest

from sqlalchemy_unchained import ModelManager, BaseQuery, ValidationErrors


@pytest.fixture()
def Foobar(db):
    class Foobar(db.Model):
        name = db.Column(db.String, nullable=False)

    db.Model.metadata.create_all()

    yield Foobar


@pytest.fixture()
def foobar_manager(Foobar):
    class FoobarManager(ModelManager):
        class Meta:
            model = Foobar

    yield FoobarManager()


class TestModelManager:
    def test_it_requires_a_model(self):
        with pytest.raises(Exception) as e:
            class ConcreteManager(ModelManager):
                pass
        assert 'The class Meta model attribute must be a subclass of BaseModel' in str(e)

    def test_query_descriptor(self, foobar_manager):
        assert isinstance(foobar_manager.q, BaseQuery)

    def test_create(self, foobar_manager):
        foobar = foobar_manager.create(name='Foobar!')

        with foobar_manager.no_autoflush:
            assert not foobar_manager.all()

    def test_create_with_commit(self, foobar_manager):
        foobar = foobar_manager.create(name='Foobar!', commit=True)
        assert foobar_manager.all() == [foobar]

    def test_create_raises_validation_errors(self, foobar_manager):
        with pytest.raises(ValidationErrors) as e:
            fail = foobar_manager.create()
        assert 'Name is required.' in str(e)

    def test_get_or_create(self, Foobar, foobar_manager):
        instance, did_create = foobar_manager.get_or_create(name='Foobar!')
        assert isinstance(instance, Foobar)
        assert did_create is True

        with foobar_manager.no_autoflush:
            assert not foobar_manager.all()

    def test_get_or_create_with_commit(self, Foobar, foobar_manager):
        instance, did_create = foobar_manager.get_or_create(name='Foobar!', commit=True)
        assert isinstance(instance, Foobar)
        assert did_create is True
        assert foobar_manager.all() == [instance]

    def test_get_or_create_with_existing(self, Foobar, foobar_manager):
        foobar = foobar_manager.create(name='Foobar!', commit=True)

        instance, did_create = foobar_manager.get_or_create(name='Foobar!')
        assert isinstance(instance, Foobar)
        assert did_create is False
        assert instance == foobar
        assert foobar_manager.all() == [instance]

    def test_update(self, Foobar, foobar_manager):
        foobar = foobar_manager.create(name='Foobar!')
        foobar_manager.update(foobar, name='new!')
        assert foobar.name == 'new!'

        with foobar_manager.no_autoflush:
            assert not foobar_manager.all()

    def test_update_raises_validation_errors(self, foobar_manager):
        foobar = foobar_manager.create(name='Foobar!', commit=True)

        with pytest.raises(ValidationErrors) as e:
            foobar_manager.update(foobar, name=None)
        assert 'Name is required.' in str(e)

        # make sure the db didn't get updated
        from_db = foobar_manager.all()
        assert from_db == [foobar]
        assert foobar.name == 'Foobar!'

    def test_update_with_commit(self, foobar_manager):
        foobar = foobar_manager.create(name='Foobar!')
        updated = foobar_manager.update(foobar, name='new!', commit=True)
        assert foobar == updated
        assert updated.name == 'new!'
        assert foobar_manager.all() == [updated]

    def test_get_by(self, foobar_manager):
        one = foobar_manager.create(name='one')
        two = foobar_manager.create(name='two')
        three = foobar_manager.create(name='three')
        foobar_manager.commit()

        assert foobar_manager.get_by(name='one') == one
        assert foobar_manager.get_by(name='two') == two
        assert foobar_manager.get_by(name='three') == three
        assert foobar_manager.get_by(name='fail') is None

    def test_filter(self, Foobar, foobar_manager):
        one = foobar_manager.create(name='one')
        one_and_a_half = foobar_manager.create(name='one-and-a-half')
        two = foobar_manager.create(name='two')
        foobar_manager.commit()

        assert foobar_manager.filter(Foobar.name == 'one') == [one]
        assert foobar_manager.filter(Foobar.name.like('%one%')) == [one, one_and_a_half]

    def test_filter_by(self, Foobar, foobar_manager):
        one = foobar_manager.create(name='one')
        one_and_a_half = foobar_manager.create(name='one-and-a-half')
        two = foobar_manager.create(name='two')
        foobar_manager.commit()

        assert foobar_manager.filter_by(name='one') == [one]
        assert foobar_manager.filter_by(name='two') == [two]
