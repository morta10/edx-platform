"""
Expectation for all OutlineProcessors are:

* something to do a one-time load of data for an entire course
* a method to call to emit a list of usage_keys to hide
* a method to call to add any data that is relevant to this system.

# Processors that we need:

Attributes that apply to both Sections and Sequences
* start
* .hide_from_toc

Might make sense to put this whole thing as a "private" module in an api package,
with the understanding that it's not part of the external contract yet.
"""
import logging
from datetime import datetime

from django.contrib.auth import get_user_model
from opaque_keys.edx.keys import CourseKey, UsageKey

from ..data import ScheduleData, ScheduleItemData

User = get_user_model()
log = logging.getLogger(__name__)


class OutlineProcessor:
    """

    """
    def __init__(self, course_key: CourseKey, user: User, at_time: datetime):
        """
        Basic initialization.

        Extend to set your own data attributes, but don't do any real work (e.g.
        database access, expensive computation) here.
        """
        self.course_key = course_key
        self.user = user
        self.at_time = at_time

    def load_data(self):
        """
        Fetch whatever data you need about the course and user here.

        If everything you need is already in the CourseOutlineData, there is no
        need to override this method.

        DO NOT USE MODULESTORE OR BLOCKSTRUCTURES HERE, as the up-front
        performance penalties of those modules are the entire reason this app
        exists. Running this method in your subclass should take no more than
        tens of milliseconds, even on courses with hundreds of learning
        sequences.
        """
        pass

    def inaccessible_sequences(self, full_course_outline):
        """
        Return a set/frozenset of Sequence UsageKeys that are not accessible.

        This will not be run for staff users (who can access everything), so
        there is no need to check for staff access here.
        """
        return frozenset()

    def usage_keys_to_remove(self, full_course_outline):
        """
        Return a set/frozenset of UsageKeys to remove altogether.

        This will not be run for staff users (who can see everything), so
        there is no need to check for staff access here.
        """
        return frozenset()

    @classmethod
    def is_sequence_key(cls, usage_key):
        """Helper in case we add more Sequence-like types."""
        return usage_key.block_type == 'sequential'

    @classmethod
    def is_section_key(cls, usage_key):
        """Helper in case we add more Section-like types."""
        return usage_key.block_type == 'chapter'
