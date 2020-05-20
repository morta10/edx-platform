from datetime import datetime, timezone
from unittest import TestCase

from opaque_keys.edx.keys import CourseKey
import attr

from ..data import (
    CourseOutlineData, CourseSectionData, CourseLearningSequenceData, VisibilityData
)

class TestCourseOutlineData(TestCase):
    """
    Simple set of tests for data class validations.
    """
    @classmethod
    def setUpClass(cls):
        """
        All our data classes are immutable, so we can set up a baseline course
        outline and then make slightly modified versions for each particular
        test as needed.
        """
        super().setUpClass()
        course_key = CourseKey.from_string("course-v1:OpenEdX+Learning+TestRun")
        normal_visibility = VisibilityData(hide_from_toc=False, visible_to_staff_only=False)
        cls.course_outline = CourseOutlineData(
            course_key=course_key,
            title="Exciting Test Course!",
            published_at=datetime(2020, 5, 19, tzinfo=timezone.utc),
            published_version="5ebece4b69dd593d82fe2014",
            sections=[
                CourseSectionData(
                    usage_key=course_key.make_usage_key('chapter', 'ch1'),
                    title="Chapter 1: 🔥",
                    visibility=normal_visibility,
                    sequences=[
                        CourseLearningSequenceData(
                            usage_key=course_key.make_usage_key(
                                'sequential', 'seq_1_{}'.format(i)
                            ),
                            title="Seq 1.{}: 🔥".format(i),
                            visibility=normal_visibility,
                        )
                        for i in range(3)
                    ]
                ),
                CourseSectionData(
                    usage_key=course_key.make_usage_key('chapter', 'ch2'),
                    title="Chapter 2: 🔥🔥",
                    visibility=normal_visibility,
                    sequences=[
                        CourseLearningSequenceData(
                            usage_key=course_key.make_usage_key(
                                'sequential', 'seq_2_{}'.format(i)
                            ),
                            title="Seq 2.{}: 🔥🔥".format(i),
                            visibility=normal_visibility,
                        )
                        for i in range(2)
                    ]
                ),
            ]
        )
        cls.course_key = course_key

    def test_deprecated_course_key(self):
        """Old-Mongo style, "Org/Course/Run" keys are not supported."""
        old_course_key = CourseKey.from_string("OpenEdX/TestCourse/TestRun")
        with self.assertRaises(ValueError):
            attr.evolve(self.course_outline, course_key=old_course_key)

    def test_sequence_building(self):
        """Make sure sequences were set correctly from sections data."""
        for section in self.course_outline.sections:
            for seq in section.sequences:
                self.assertEqual(seq, self.course_outline.sequences[seq.usage_key])
        self.assertEqual(
            sum(len(section.sequences) for section in self.course_outline.sections),
            len(self.course_outline.sequences),
        )

    def test_duplicate_sequence(self):
        """We don't support DAGs. Sequences can only be in one Section."""
        # This section has Chapter 2's sequences in it
        section_with_dupe_seq = attr.evolve(
            self.course_outline.sections[1], title="Chapter 2 dupe",
        )
        with self.assertRaises(ValueError):
            attr.evolve(
                self.course_outline,
                sections=self.course_outline.sections + [section_with_dupe_seq]
            )

    def test_size(self):
        """Limit how large a CourseOutline is allowed to be."""
        normal_visibility = VisibilityData(hide_from_toc=False, visible_to_staff_only=False)
        very_big_section = attr.evolve(
            self.course_outline.sections[0],
            sequences=[
                CourseLearningSequenceData(
                    usage_key=self.course_key.make_usage_key('sequential', 'seq_{}'.format(i)),
                    title="Seq {}".format(i),
                    visibility=normal_visibility,
                )
                for i in range(1001)
            ]
        )
        with self.assertRaises(ValueError):
            attr.evolve(self.course_outline, sections=[very_big_section])

    def test_remove_sequence(self):
        """Remove a single sequence from the CourseOutlineData (creates a copy)."""
        seq_to_remove = self.course_outline.sections[0].sequences[0]
        new_outline = self.course_outline.remove({seq_to_remove.usage_key})
        assert self.course_outline != new_outline
        assert seq_to_remove.usage_key in self.course_outline.sequences
        assert seq_to_remove.usage_key not in new_outline.sequences
        assert len(new_outline.sections[0].sequences) == len(self.course_outline.sections[0].sequences) - 1
        for seq in new_outline.sections[0].sequences:
            assert seq != seq_to_remove

    def test_remove_section(self):
        """
        Remove a whole Section from the CourseOutlineData (creates a copy).

        Removing a Section also removes all Sequences in that Section.
        """
        section_to_remove = self.course_outline.sections[0]
        new_outline = self.course_outline.remove({section_to_remove.usage_key})
        assert self.course_outline != new_outline
        assert len(new_outline.sections) == len(self.course_outline.sections) - 1
        assert section_to_remove != new_outline.sections[0]
        for seq in section_to_remove.sequences:
            assert seq.usage_key not in new_outline.sequences

    def test_remove_nonexistant(self):
        """Removing something that's not already there is a no-op."""
        seq_key_to_remove = self.course_key.make_usage_key('sequential', 'not_here')
        new_outline = self.course_outline.remove({seq_key_to_remove})
        assert new_outline == self.course_outline
