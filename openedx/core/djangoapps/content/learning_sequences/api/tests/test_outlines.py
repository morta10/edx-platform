"""
Top level API tests. Tests API public contracts only.
"""
from datetime import datetime, timezone

from opaque_keys.edx.keys import CourseKey, UsageKey
from opaque_keys.edx.locator import BlockUsageLocator

from openedx.core.djangolib.testing.utils import CacheIsolationTestCase
from ..data import (
    CourseOutlineData, CourseSectionData, CourseLearningSequenceData,
    VisibilityData
)
from ..outlines import (
    get_course_outline, replace_course_outline
)


class RoundTripTestCase(CacheIsolationTestCase):
    """
    Simple tests to ensure that we can pull back the same data we put in, and
    that we don't break when storing or retrieving edge cases.
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

    def test_simple_roundtrip(self):
        # Make sure it wasn't there in the beginning...
        with self.assertRaises(CourseOutlineData.DoesNotExist):
            course_outline = get_course_outline(self.course_key)

        replace_course_outline(self.course_outline)
        outline = get_course_outline(self.course_key)
        assert outline == self.course_outline

    # Add tests with more permutations of data, updates with same structure,
    # updates with slightly different structure.
