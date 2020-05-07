from sqlalchemy_unchained import ModelRegistry


def _names(bases):
    return [b.__name__ for b in bases]


class TestConvertBases:
    def test_mro_is_correct(self, db):
        # these model inheritance hierarchies *should* be far more unreasonable
        # than what an end user would build up; the goal for this test is just
        # to make sure the MRO of converted bases works as it should

        class B1(db.Model):
            pass

        class B2(db.Model):
            pass

        class B3(B1, B2):
            pass

        result = ModelRegistry()._registry[B3.__name__][B3.__module__].bases
        assert _names(result) == [
            'B1_FSQLAConvertedMixin', 'B2_FSQLAConvertedMixin', 'Model',
        ], 'it should be able to extend multiple base models'

        class B4(db.Model):
            pass

        class B5(B4, B3):
            pass

        result = ModelRegistry()._registry[B5.__name__][B5.__module__].bases
        assert _names(result) == [
            'B4_FSQLAConvertedMixin', 'B3_FSQLAConvertedMixin',
            'B1_FSQLAConvertedMixin', 'B2_FSQLAConvertedMixin', 'Model',
        ], 'it should preserve order of multiple inheritance'

        class B6(db.Model):
            pass

        class GenericMixin:
            pass

        class B7(B5, B6, GenericMixin):
            pass

        result = ModelRegistry()._registry[B7.__name__][B7.__module__].bases
        assert _names(result) == [
            'B5_FSQLAConvertedMixin', 'B4_FSQLAConvertedMixin',
            'B3_FSQLAConvertedMixin', 'B1_FSQLAConvertedMixin',
            'B2_FSQLAConvertedMixin', 'B6_FSQLAConvertedMixin',
            'Model', 'GenericMixin',
        ], 'it should work with deeply nested multiple inheritance'
