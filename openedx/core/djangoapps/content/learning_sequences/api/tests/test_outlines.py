"""
Top level API tests. Tests API public contracts only. Do not import/create/mock
models for this app.
"""
from datetime import datetime, timezone

from django.contrib.auth.models import User, AnonymousUser
from opaque_keys.edx.keys import CourseKey, UsageKey
from opaque_keys.edx.locator import BlockUsageLocator
import attr

from openedx.core.djangolib.testing.utils import CacheIsolationTestCase
from ..data import (
    CourseOutlineData, CourseSectionData, CourseLearningSequenceData,
    VisibilityData
)
from ..outlines import (
    get_course_outline, get_user_course_outline,
    get_user_course_outline_details, replace_course_outline
)
from .test_data import generate_sections


class CourseOutlineTestCase(CacheIsolationTestCase):
    """
    Simple tests around reading and writing CourseOutlineData. No user info.
    """
    @classmethod
    def setUpTestData(cls):
        cls.course_key = CourseKey.from_string("course-v1:OpenEdX+Learn+Roundtrip")
        normal_visibility = VisibilityData(
            hide_from_toc=False, visible_to_staff_only=False
        )
        cls.course_outline = CourseOutlineData(
            course_key=cls.course_key,
            title="Roundtrip Test Course!",
            published_at=datetime(2020, 5, 20, tzinfo=timezone.utc),
            published_version="5ebece4b69dd593d82fe2015",
            sections=generate_sections(cls.course_key, [2, 2]),
        )

    def test_deprecated_course_key(self):
        """Don't allow Old Mongo Courses at all."""
        old_course_key = CourseKey.from_string("Org/Course/Run")
        with self.assertRaises(ValueError):
            outline = get_course_outline(old_course_key)

    def test_simple_roundtrip(self):
        """Happy path for writing/reading-back a course outline."""
        with self.assertRaises(CourseOutlineData.DoesNotExist):
            course_outline = get_course_outline(self.course_key)

        replace_course_outline(self.course_outline)
        outline = get_course_outline(self.course_key)
        assert outline == self.course_outline

    def test_empty_course(self):
        """Empty Courses are a common case (when authoring just starts)."""
        empty_outline = attr.evolve(self.course_outline, sections=[])
        self.assertFalse(empty_outline.sections)
        self.assertFalse(empty_outline.sequences)
        replace_course_outline(empty_outline)
        assert empty_outline == get_course_outline(self.course_key)

    def test_empty_sections(self):
        """Empty Sections aren't very useful, but they shouldn't break."""
        empty_section_outline = attr.evolve(
            self.course_outline, sections=generate_sections(self.course_key, [0])
        )
        replace_course_outline(empty_section_outline)
        assert empty_section_outline == get_course_outline(self.course_key)

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

    @classmethod
    def setUpTestData(cls):
        # Users...
        cls.global_staff = User.objects.create_user(
            'global_staff', email='gstaff@example.com', is_staff=True
        )
        cls.student = User.objects.create_user(
            'student', email='student@example.com', is_staff=False
        )
        # TODO: Add AnonymousUser here.

        # Seed with data
        cls.course_key = CourseKey.from_string("course-v1:OpenEdX+Outline+T1")
        normal_visibility = VisibilityData(
            hide_from_toc=False, visible_to_staff_only=False
        )
        cls.simple_outline = CourseOutlineData(
            course_key=cls.course_key,
            title="User Outline Test Course!",
            published_at=datetime(2020, 5, 20, tzinfo=timezone.utc),
            published_version="5ebece4b69dd593d82fe2020",
            sections=generate_sections(cls.course_key, [2, 1, 3])
        )
        replace_course_outline(cls.simple_outline)

    def test_simple_outline(self):
        """This outline is the same for everyone."""
        at_time = datetime(2020, 5, 21, tzinfo=timezone.utc)
        student_outline = get_user_course_outline(
            self.course_key, self.student, at_time
        )
        global_staff_outline = get_user_course_outline(
            self.course_key, self.global_staff, at_time
        )
        assert student_outline.sections == global_staff_outline.sections

