import pytest

from sqlalchemy_unchained import ModelRegistry, Required, ValidationErrors


@pytest.fixture()
def NotLazy(db):
    class NotLazy(db.Model):
        class Meta:
            abstract = True
            lazy_mapped = False

    return NotLazy


class TestModelMetaOptions:
    def test_defaults(self, db):
        meta = db.Model.Meta
        assert (
            meta._testing_ == "this setting is only available when "
            'os.getenv("SQLA_TESTING") == "True"'
        )

        assert meta.abstract is True
        assert meta.lazy_mapped is False
        assert meta.validation is True

        assert meta._base_tablename is None
        assert meta.polymorphic is False
        assert meta.polymorphic_on is None
        assert meta.polymorphic_identity is None

        assert meta.pk == "id"
        assert meta.created_at == "created_at"
        assert meta.updated_at == "updated_at"

    def test_overriding_defaults_with_inheritance(self, db):
        class Over(db.Model):
            class Meta:
                pk = "pk"
                created_at = "created"
                updated_at = "updated"
                _testing_ = "over"

        meta = Over.Meta
        assert meta._testing_ == "over"
        assert meta.abstract is False
        assert meta.lazy_mapped is False

        assert meta._base_tablename is None
        assert meta.polymorphic is False
        assert meta.polymorphic_on is None
        assert meta.polymorphic_identity is None

        assert meta.pk == "pk"
        assert meta.created_at == "created"
        assert meta.updated_at == "updated"

        class ExtendsOver(Over):
            class Meta:
                lazy_mapped = True
                updated_at = "extends"

        meta = ExtendsOver.Meta
        assert meta._testing_ == "over"
        assert meta.abstract is False
        assert meta.lazy_mapped is True

        assert meta._base_tablename == "over"
        assert meta.polymorphic is False
        assert meta.polymorphic_on is None
        assert meta.polymorphic_identity is None

        assert meta.pk == "pk"
        assert meta.created_at == "created"
        assert meta.updated_at == "extends"

    def test_abstract(self, db):
        class Classic(db.Model):
            __abstract__ = True

        ModelRegistry().finalize_mappings()
        assert Classic.Meta.abstract is True
        assert Classic.Meta._mcs_args.clsdict["__abstract__"] is True

        class MyMeta(db.Model):
            class Meta:
                abstract = True

        ModelRegistry().finalize_mappings()
        assert MyMeta.Meta.abstract is True
        assert MyMeta.Meta._mcs_args.clsdict["__abstract__"] is True

    def test_primary_key_gets_added_when_needed(self, NotLazy):
        class Auto(NotLazy):
            pass

        assert Auto.id.primary_key is True

    def test_primary_key_doesnt_get_added_when_one_exists(self, db, NotLazy):
        # a primary key column already exists
        class ManualPkColumn(NotLazy):
            pk = db.Column(db.Integer, primary_key=True)

        assert not hasattr(ManualPkColumn, ModelRegistry().default_primary_key_column)

        # a primary key constraint exists
        class ManualConstraint(NotLazy):
            __table_args__ = (db.PrimaryKeyConstraint("one_id", "two_id"),)
            one_id = db.Column(db.Integer)
            two_id = db.Column(db.Integer)

        assert not hasattr(ManualConstraint, ModelRegistry().default_primary_key_column)

    def test_primary_key_doesnt_overwrite_existing_column(self, db, NotLazy):
        DoesntOverwriteExistingColumn = type(
            "DoesntOverwrite",
            (NotLazy,),
            {
                ModelRegistry().default_primary_key_column: "not a column",
                "a_pk_col_is_still_required": db.Column(db.Integer, primary_key=True),
            },
        )

        assert (
            getattr(
                DoesntOverwriteExistingColumn,
                ModelRegistry().default_primary_key_column,
            )
            == "not a column"
        )

    def test_primary_key_works_with_custom_column_name(self, db, NotLazy):
        custom_pk_col_name = "unique_" + ModelRegistry().default_primary_key_column

        class Renamed(NotLazy):
            class Meta:
                pk = custom_pk_col_name

        assert not hasattr(Renamed, ModelRegistry().default_primary_key_column)
        pk_col = getattr(Renamed, custom_pk_col_name)
        assert pk_col.primary_key is True

    def test_validation(self, db):
        class Foo(db.Model):
            class Meta:
                validation = True

            bar = db.Column(
                db.String,
                nullable=False,
                info=dict(validators=[Required("Bar is required.")]),
            )

        with pytest.raises(ValidationErrors):
            Foo().validate()

    def test_validation_disabled(self, db):
        class Foo(db.Model):
            class Meta:
                validation = False

            bar = db.Column(
                db.String,
                nullable=False,
                info=dict(validators=[Required("Bar is required.")]),
            )

        foo = Foo()
        assert isinstance(foo, Foo)

    def test_repr(self, db):
        class Default(db.Model):
            pass

        assert repr(Default()) == "Default(id=None, created_at=None, updated_at=None)"

        class Foo(db.Model):
            class Meta:
                repr = ("id", "name", "code")

            name = db.Column(db.String)
            code = db.Column(db.Integer)

        foo = Foo(name="fubar", code=500)
        assert repr(foo) == "Foo(id=None, name='fubar', code=500)"

    def test_polymorphic_auto_base_tablename(self, db):
        class Base(db.Model):
            class Meta:
                lazy_mapped = False
                polymorphic = True

        class YellowSubmarine(Base):
            pass

        class GlassOnion(YellowSubmarine):
            pass

        assert Base.Meta._base_tablename is None
        assert YellowSubmarine.Meta._base_tablename == "base"
        assert GlassOnion.Meta._base_tablename == "yellow_submarine"

    def test_polymorphic_manual_base_tablename(self, db):
        class Base(db.Model):
            class Meta:
                lazy_mapped = False
                polymorphic = True
                table = "bases"

        class YellowSubmarine(Base):
            class Meta:
                table = "yellow_subs"

        class GlassOnion(YellowSubmarine):
            pass

        assert Base.Meta._base_tablename is None
        assert YellowSubmarine.Meta._base_tablename == "bases"
        assert GlassOnion.Meta._base_tablename == "yellow_subs"

    def test_polymorphic_manual_declared_attr_tablename(self, db):
        class Base(db.Model):
            class Meta:
                lazy_mapped = False
                polymorphic = True

            @db.declared_attr
            def __tablename__(cls):
                return cls.__name__.lower() + "s"

        class YellowSubmarine(Base):
            id = db.foreign_key(Base.__tablename__, primary_key=True)

        class GlassOnion(YellowSubmarine):
            id = db.foreign_key(YellowSubmarine.__tablename__, primary_key=True)

        assert Base.Meta._base_tablename is None
        assert Base.__tablename__ == "bases"
        assert YellowSubmarine.Meta._base_tablename is None
        assert YellowSubmarine.__tablename__ == "yellowsubmarines"
        assert GlassOnion.Meta._base_tablename is None

    def test_polymorphic_declared_attr_tablename(self, db):
        class Base(db.Model):
            class Meta:
                lazy_mapped = False
                polymorphic = True

            @db.declared_attr
            def __tablename__(cls):
                return cls.__name__.lower() + "s"

        class YellowSubmarine(Base):
            pass

        class GlassOnion(YellowSubmarine):
            pass

        assert Base.Meta._base_tablename is None
        assert Base.__tablename__ == "bases"
        assert YellowSubmarine.Meta._base_tablename is None
        assert YellowSubmarine.__tablename__ == "yellowsubmarines"
        assert GlassOnion.Meta._base_tablename is None

    def test_polymorphic_joined_pk(self, db):
        class Base(db.Model):
            class Meta:
                polymorphic = True

        class YellowSubmarine(Base):
            pass

        class GlassOnion(YellowSubmarine):
            pass

        assert Base.Meta._base_pk_name is None
        assert YellowSubmarine.Meta._base_pk_name == "id"
        assert GlassOnion.Meta._base_pk_name == "id"

    def test_polymorphic_joined_pk_custom_fk(self, db):
        class Base(db.Model):
            class Meta:
                polymorphic = True

        class YellowSubmarine(Base):
            class Meta:
                pk = None

            custom_pk = db.foreign_key(Base, primary_key=True)

        class GlassOnion(YellowSubmarine):
            class Meta:
                pk = "id"

        assert Base.Meta._base_pk_name is None
        assert Base.Meta._base_tablename is None
        assert YellowSubmarine.Meta._base_tablename == "base"
        assert YellowSubmarine.Meta._base_pk_name == "id"
        assert GlassOnion.Meta._base_tablename == "yellow_submarine"
        assert GlassOnion.Meta._base_pk_name == "custom_pk"

    def test_tablename(self, db):
        class NotLazy(db.Model):
            class Meta:
                abstract = True
                lazy_mapped = False

        class Auto(NotLazy):
            pass

        assert Auto.Meta.table is None
        assert "__tablename__" not in Auto.Meta._mcs_args.clsdict
        assert Auto.__tablename__ == "auto"

        class DeclaredAttr(NotLazy):
            @db.declared_attr
            def __tablename__(cls):
                return cls.__name__.lower()

        assert DeclaredAttr.Meta.table is None
        assert DeclaredAttr.__tablename__ == "declaredattr"

        class Manual(NotLazy):
            __tablename__ = "manuals"

        assert Manual.Meta.table == "manuals"
        assert Manual.Meta._mcs_args.clsdict["__tablename__"] == "manuals"
        assert Manual.__tablename__ == "manuals"
