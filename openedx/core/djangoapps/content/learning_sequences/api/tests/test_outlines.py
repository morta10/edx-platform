"""
Top level API tests. Tests API public contracts only. Do not import/create/mock
models for this app.
"""
from datetime import datetime, timezone

from opaque_keys.edx.keys import CourseKey, UsageKey
from opaque_keys.edx.locator import BlockUsageLocator
import attr

from openedx.core.djangolib.testing.utils import CacheIsolationTestCase
from ..data import (
    CourseOutlineData, CourseSectionData, CourseLearningSequenceData,
    VisibilityData
)
from ..outlines import (
    get_course_outline, replace_course_outline
)


class CourseOutlineTestCase(CacheIsolationTestCase):
    """
    Simple tests around reading and writing CourseOutlineData. No user info.
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        course_key = CourseKey.from_string("course-v1:OpenEdX+Learn+Roundtrip")
        normal_visibility = VisibilityData(
            hide_from_toc=False, visible_to_staff_only=False
        )
        cls.course_outline = CourseOutlineData(
            course_key=course_key,
            title="Roundtrip Test Course!",
            published_at=datetime(2020, 5, 20, tzinfo=timezone.utc),
            published_version="5ebece4b69dd593d82fe2015",
            sections=[
                CourseSectionData(
                    usage_key=course_key.make_usage_key(
                        'chapter', 'ch{}'.format(sec_num)
                    ),
                    title="Chapter {}: 🔥".format(sec_num),
                    visibility=normal_visibility,
                    sequences=[
                        CourseLearningSequenceData(
                            usage_key=course_key.make_usage_key(
                                'sequential', 'seq_{}_{}'.format(sec_num, seq_num)
                            ),
                            title="Seq {}.{}: 🔥".format(sec_num, seq_num),
                            visibility=normal_visibility,
                        )
                        for seq_num in range(2)
                    ]
                )
                for sec_num in range(2)
            ]
        )
        cls.course_key = course_key

    def test_case_sensitivity(self):
        replace_course_outline(self.course_outline)
        with self.assertRaises(CourseOutlineData.DoesNotExist):
            ucase_course_key = CourseKey.from_string("course-v1:OPENEDX+LEARN+ROUNDTRIP")
            outline = get_course_outline(ucase_course_key)

    def test_deprecated_course_key(self):
        old_course_key = CourseKey.from_string("Org/Course/Run")
        with self.assertRaises(ValueError):
            outline = get_course_outline(old_course_key)

    def test_simple_roundtrip(self):
        # Make sure it wasn't there in the beginning...
        with self.assertRaises(CourseOutlineData.DoesNotExist):
            course_outline = get_course_outline(self.course_key)

        replace_course_outline(self.course_outline)
        outline = get_course_outline(self.course_key)
        assert outline == self.course_outline

    def test_empty_course(self):
        empty_outline = attr.evolve(self.course_outline, sections=[])
        self.assertFalse(empty_outline.sections)
        self.assertFalse(empty_outline.sequences)
        replace_course_outline(empty_outline)
        assert empty_outline == get_course_outline(self.course_key)

    def test_cached_response(self):
        # First lets seed the data...
        replace_course_outline(self.course_outline)

        # Uncached access always makes three database checks: LearningContext,
        # CourseSection, and CourseSectionSequence.
        with self.assertNumQueries(3):
            uncached_outline = get_course_outline(self.course_key)
            assert uncached_outline == self.course_outline

        # Successful cache access only makes a query to LearningContext to check
        # the current published version. That way we know that values are never
        # stale.
        with self.assertNumQueries(1):
            cached_outline = get_course_outline(self.course_key)

        # Cache hits in the same process are literally the same object.
        assert cached_outline is uncached_outline

        # Now we put a new version into the cache...
        new_version_outline = attr.evolve(
            self.course_outline, published_version="2222222222222222"
        )
        replace_course_outline(new_version_outline)

        # Make sure this new outline is returned instead of the previously
        # cached one.
        with self.assertNumQueries(3):
            uncached_new_version_outline = get_course_outline(self.course_key)
            assert new_version_outline == new_version_outline


class UserCourseOutlineTestCase(CacheIsolationTestCase):
    pass
