import pytest

from sqlalchemy_unchained import SessionManager


@pytest.fixture()
def session_manager(db):
    yield SessionManager()


class TestSessionManager:
    def test_it_requires_a_session_factory(self):
        SessionManager.set_session_factory(None)
        with pytest.raises(Exception) as e:
            fail = SessionManager()
        assert 'SessionManager was not properly initialized.' in str(e.value)

    def test_save_without_commit(self, db, session_manager: SessionManager):
        class Foobar(db.Model):
            pass

        db.Model.metadata.create_all()

        foo = Foobar()
        session_manager.save(foo)
        assert foo in session_manager.session

        with session_manager.no_autoflush:
            assert not session_manager.query(Foobar).all()

    def test_save_with_commit(self, db, session_manager: SessionManager):
        class Foobar(db.Model):
            pass

        db.Model.metadata.create_all()

        foo = Foobar()
        session_manager.save(foo, commit=True)

        assert foo in session_manager.session
        assert session_manager.query(Foobar).all() == [foo]

    def test_save_all_without_commit(self, db, session_manager: SessionManager):
        class Foobar(db.Model):
            pass

        db.Model.metadata.create_all()

        foo1 = Foobar()
        foo2 = Foobar()
        session_manager.save_all([foo1, foo2])
        assert foo1 in session_manager.session
        assert foo2 in session_manager.session

        with session_manager.no_autoflush:
            assert not session_manager.query(Foobar).all()

    def test_save_all_with_commit(self, db, session_manager: SessionManager):
        class Foobar(db.Model):
            pass

        db.Model.metadata.create_all()

        foo1 = Foobar()
        foo2 = Foobar()
        session_manager.save_all([foo1, foo2])
        assert foo1 in session_manager.session
        assert foo2 in session_manager.session

        assert session_manager.query(Foobar).all() == [foo1, foo2]

    def test_commit(self, db, session_manager: SessionManager):
        class Foobar(db.Model):
            pass

        db.Model.metadata.create_all()

        foo = Foobar()
        session_manager.save(foo)
        session_manager.commit()

        assert session_manager.query(Foobar).all() == [foo]
