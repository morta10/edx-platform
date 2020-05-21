"""
Tests for the General Course Home API in the Course Home API
"""


import ddt

from django.urls import reverse

from course_modes.models import CourseMode
from lms.djangoapps.course_home_api.tests.utils import BaseCourseHomeTests
from student.models import CourseEnrollment
from student.tests.factories import UserFactory


@ddt.ddt
class CourseHomeGeneralTests(BaseCourseHomeTests):
    """
    Tests for the General Course Home API
    """
    @classmethod
    def setUpClass(cls):
        BaseCourseHomeTests.setUpClass()
        cls.url = reverse('course-home-general', args=[cls.course.id])

    def test_get_authenticated_user(self):
        CourseEnrollment.enroll(self.user, self.course.id, CourseMode.VERIFIED)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data.get('is_staff'))
        # 'Course', 'Wiki', 'Progress' tabs
        self.assertEqual(len(response.data.get('tabs', [])), 3)

    def test_get_authenticated_staff_user(self):
        self.client.logout()
        staff_user = UserFactory(
            username='staff',
            email='staff@example.com',
            password='bar',
            is_staff=True
        )
        self.client.login(username=staff_user.username, password='bar')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_staff'])
        # This differs for a staff user because they also receive the Instructor tab
        # 'Course', 'Wiki', 'Progress', and 'Instructor' tabs
        self.assertEqual(len(response.data.get('tabs', [])), 4)

    def test_get_unauthenticated_user(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_get_unknown_course(self):
        url = reverse('course-home-general', args=['course-v1:unknown+course+2T2020'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
