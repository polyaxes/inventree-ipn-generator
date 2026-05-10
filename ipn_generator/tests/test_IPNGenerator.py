from django.test import TestCase
from django.core.exceptions import ValidationError
import logging

from django.conf import settings
from part.models import PartCategory, SupplierPart, Part
from company.models import Company
from common.models import InvenTreeSetting

from plugin import registry

logger = logging.getLogger("inventree")


def setup_func(cls):
    settings.PLUGIN_TESTING_EVENTS = True
    settings.TESTING_TABLE_EVENTS = True
    InvenTreeSetting.set_setting("ENABLE_PLUGINS_EVENTS", True)
    cls.plugin = registry.get_plugin("ipngen")
    conf = cls.plugin.plugin_config()
    conf.active = True
    conf.save()


def teardown_func():
    settings.PLUGIN_TESTING_EVENTS = False
    settings.TESTING_TABLE_EVENTS = False
    InvenTreeSetting.set_setting("ENABLE_PLUGINS_EVENTS", False)


class IPNGeneratorPatternTests(TestCase):
    """Tests for verifying IPN pattern validation works properly"""

    def setUp(self):
        """Set up test environment"""
        setup_func(self)

    def tearDown(self):
        """Teardown test environment"""
        teardown_func()

    def test_cannot_add_only_literal(self):
        """Verify that setting PATTERN to only literals fails validation"""
        with self.assertRaises(ValidationError):
            self.plugin.set_setting("PATTERN", "(123)")

    def test_cannot_add_only_random_string(self):
        """Verify that setting PATTERN to an invalid string"""
        with self.assertRaises(ValidationError):
            self.plugin.set_setting("PATTERN", "asldkferljgjtdS:DfS_D:fE_SD:FA_;G")

    def test_numeric_setting_length_1(self):
        """Verify that numeric regex accepts more than 1 int."""
        # Single digit
        try:
            self.plugin.set_setting("PATTERN", "{1}")
        except ValidationError:
            self.fail("Correct numeric syntax raised a ValidationError")

    def test_numeric_setting_length_2(self):
        # Two digits
        try:
            self.plugin.set_setting("PATTERN", "{15}")
        except ValidationError:
            self.fail("Correct numeric syntax raised a ValidationError")

    def test_numeric_setting_length_3(self):
        # Multiple digits
        try:
            self.plugin.set_setting("PATTERN", "{125}")
        except ValidationError:
            self.fail("Correct numeric syntax raised a ValidationError")

    def text_numeric_setting_prefix_zero(self):
        """Zeroes should be filtered out when prefixed to numerics"""
        try:
            self.plugin.set_setting("PATTERN", "{05}")
        except ValidationError:
            self.fail("Numeric with 0 prefix raised a ValidationError")

    def test_numeric_setting_with_start(self):
        """Appending a + to numerics should work"""
        try:
            self.plugin.set_setting("PATTERN", "{25+}")
        except ValidationError:
            self.fail("Numeric with + suffix raised a ValidationError")

    def test_character_must_contain_more_than_one_character(self):
        """Verify that character groups must contain more than 1 character"""
        with self.assertRaises(ValidationError):
            self.plugin.set_setting("PATTERN", "[a]")

    def test_character_invalid_format(self):
        """Verify that character ranges are properly formatted"""
        with self.assertRaises(ValidationError):
            self.plugin.set_setting("PATTERN", "[a-]")

        with self.assertRaises(ValidationError):
            self.plugin.set_setting("PATTERN", "[aa-]")

    def test_character_range_valid(self):
        """Verify that properly formatted character ranges are accepted"""
        try:
            self.plugin.set_setting("PATTERN", "[a-b]")
        except ValidationError:
            self.fail("Valid character group range raised a ValidationError")

    def test_character_list_valid(self):
        """Verify that list of individual characters are accepted"""
        try:
            self.plugin.set_setting("PATTERN", "[abcsd]")
        except ValidationError:
            self.fail("Valid character list raised a ValidationError")

    def test_pattern_combinations(self):
        """"""
        try:
            self.plugin.set_setting("PATTERN", "(1b)[a-b]{2}")
        except ValidationError:
            self.fail("Valid pattern (1b)[a-b]{2} raised a ValidationError")

        try:
            self.plugin.set_setting("PATTERN", "[ab][a-d]{2}{3}")
        except ValidationError:
            self.fail("Valid pattern [ab][a-d]{2}{3} raised a ValidationError")

        try:
            self.plugin.set_setting("PATTERN", "{2}[bc](a2)[a-c]")
        except ValidationError:
            self.fail("Valid pattern {2}[bc](a2)[a-c] raised a ValidationError")

        try:
            self.plugin.set_setting("PATTERN", "[a-b](1s){2}(3d)")
        except ValidationError:
            self.fail("Valid pattern [a-b](1s){2}(3d) raised a ValidationError")

        try:
            self.plugin.set_setting("PATTERN", "{1}[aa]{2}(1r)")
        except ValidationError:
            self.fail("Valid pattern {1}[aa]{2}(1r) raised a ValidationError")


class InvenTreeIPNGeneratorNumericGroupTests(TestCase):
    """Tests verifying that numeric groupe behave properly"""

    def setUp(self):
        """Set up test environment"""
        setup_func(self)

    def tearDown(self):
        """Teardown test environment"""
        teardown_func()

    def test_add_numeric(self):
        """Verify that numeric patterns work."""

        self.plugin.set_setting("PATTERN", "{1}")

        cat = PartCategory.objects.all().first()
        new_part = Part.objects.create(category=cat, name="PartName")

        part = Part.objects.get(pk=new_part.pk)

        self.assertIsNotNone(part.IPN)

        self.assertEqual(part.IPN, "1")

    def test_add_numeric_with_start(self):
        """Verify that Numeric patterns with start number works."""

        self.plugin.set_setting("PATTERN", "{11+}")

        cat = PartCategory.objects.all().first()
        new_part = Part.objects.create(category=cat, name="PartName")

        self.assertEqual(Part.objects.get(pk=new_part.pk).IPN, "11")

    def test_add_numeric_incrementing(self):
        """Verify that numeric patterns increment on subsequent parts."""

        self.plugin.set_setting("PATTERN", "{1}")

        self.assertEqual(self.plugin.get_setting("PATTERN"), "{1}")

        cat = PartCategory.objects.all().first()
        Part.objects.create(category=cat, name="PartName")

        new_part = Part.objects.create(category=cat, name="PartName")

        part = Part.objects.get(pk=new_part.pk)

        self.assertEqual(part.IPN, "2")

    def test_add_numeric_incrementing_with_start(self):
        """Verify that numeric patterns with start number increment on subsequent parts."""
        self.plugin.set_setting("PATTERN", "{11+}")

        cat = PartCategory.objects.all().first()
        Part.objects.create(category=cat, name="PartName")

        new_part = Part.objects.create(category=cat, name="PartName")

        part = Part.objects.get(pk=new_part.pk)

        self.assertEqual(part.IPN, "12")

    def test_add_numeric_with_prepend_zero(self):
        """Verify that numeric patterns work."""

        self.plugin.set_setting("PATTERN", "{3}")

        cat = PartCategory.objects.all().first()
        new_part = Part.objects.create(category=cat, name="PartName")

        part = Part.objects.get(pk=new_part.pk)

        self.assertIsNotNone(part.IPN)

        self.assertEqual(part.IPN, "001")

    def test_numeric_rollover(self):
        """Verify that numeric groups rollover when reaching max"""

        self.plugin.set_setting("PATTERN", "{2}")

        cat = PartCategory.objects.all().first()
        Part.objects.create(category=cat, name="PartName", IPN="99")

        p = Part.objects.create(category=cat, name="PartName")

        part = Part.objects.get(pk=p.pk)
        self.assertEqual(part.IPN, "01")

    def test_numeric_with_start_rollover(self):
        """Verify that numeric groups with start number rollover when reaching max"""

        self.plugin.set_setting("PATTERN", "{26+}")

        cat = PartCategory.objects.all().first()
        Part.objects.create(category=cat, name="PartName", IPN="99")

        p = Part.objects.create(category=cat, name="PartName")

        part = Part.objects.get(pk=p.pk)
        self.assertEqual(part.IPN, "26")


class InvenTreeIPNGeneratorLiteralsTests(TestCase):
    """Tests verifying that literals function as they should"""

    def setUp(self):
        """Set up test environment"""
        setup_func(self)

    def tearDown(self):
        """Teardown test environment"""
        teardown_func()

    def test_literal_persists(self):
        """Verify literals do not change"""

        self.plugin.set_setting("PATTERN", "{1}(1v3)")

        cat = PartCategory.objects.all().first()

        Part.objects.create(category=cat, name="PartName")

        new_part = Part.objects.create(category=cat, name="PartName")

        part = Part.objects.get(pk=new_part.pk)

        self.assertEqual(part.IPN, "21v3")


class InvenTreeIPNGeneratorCharacterTests(TestCase):
    """Verify that character groups perform as they should"""

    def setUp(self):
        """Set up test environment"""
        setup_func(self)

    def tearDown(self):
        """Teardown test environment"""
        teardown_func()

    def test_character_list(self):
        """Verify that lists of characters are looped through."""

        self.plugin.set_setting("PATTERN", "[abc]")

        cat = PartCategory.objects.all().first()

        def gen_part(expected_ipn):
            p = Part.objects.create(category=cat, name="PartName")

            part = Part.objects.get(pk=p.pk)
            self.assertEqual(part.IPN, expected_ipn)

        gen_part("a")
        gen_part("b")
        gen_part("c")

    def test_character_list_rollover(self):
        """Verify that character lists restart after reaching the end"""

        self.plugin.set_setting("PATTERN", "[abc]")

        cat = PartCategory.objects.all().first()
        Part.objects.create(category=cat, name="PartName", IPN="c")

        p = Part.objects.create(category=cat, name="PartName")

        part = Part.objects.get(pk=p.pk)
        self.assertEqual(part.IPN, "a")

    def test_character_range(self):
        """Verify that ranges of characters are looped through."""

        self.plugin.set_setting("PATTERN", "[a-c]")

        cat = PartCategory.objects.all().first()

        def gen_part(expected_ipn):
            p = Part.objects.create(category=cat, name="PartName")

            part = Part.objects.get(pk=p.pk)
            self.assertEqual(part.IPN, expected_ipn)

        gen_part("a")
        gen_part("b")
        gen_part("c")

    def test_character_range_rollover(self):
        """Verify that character ranges loop around after reaching the end."""

        self.plugin.set_setting("PATTERN", "[a-c]")

        cat = PartCategory.objects.all().first()
        Part.objects.create(category=cat, name="PartName", IPN="c")

        p = Part.objects.create(category=cat, name="PartName")

        part = Part.objects.get(pk=p.pk)
        self.assertEqual(part.IPN, "a")


class IPNGeneratorCombiningTests(TestCase):
    """Verify that combining different groups works properly"""

    def setUp(self):
        """Set up test environment"""
        setup_func(self)

    def tearDown(self):
        """Teardown test environment"""
        teardown_func()

    def test_literal_and_number(self):
        """Verify literals and numbers work together"""

        self.plugin.set_setting("PATTERN", "(AB){2}")

        cat = PartCategory.objects.all().first()
        Part.objects.create(category=cat, name="PartName", IPN="AB12")

        p = Part.objects.create(category=cat, name="PartName")

        part = Part.objects.get(pk=p.pk)
        self.assertEqual(part.IPN, "AB13")

    def test_only_last_incrementable_is_changed(self):
        """Verify that only last group in pattern gets incremented"""

        self.plugin.set_setting("PATTERN", "[abc]{2}")

        cat = PartCategory.objects.all().first()
        Part.objects.create(category=cat, name="PartName", IPN="a25")

        p = Part.objects.create(category=cat, name="PartName")

        part = Part.objects.get(pk=p.pk)
        self.assertEqual(part.IPN, "a26")


class IPNGeneratorRandomTests(TestCase):
    """Tests for the <R...> random group"""

    def setUp(self):
        setup_func(self)

    def tearDown(self):
        teardown_func()

    def test_random_pattern_valid(self):
        """{R6} alone is a valid pattern"""
        try:
            self.plugin.set_setting("PATTERN", "{R6}")
        except ValidationError:
            self.fail("Valid random pattern {R6} raised a ValidationError")

    def test_random_pattern_with_prefix_valid(self):
        """Random can be combined with a literal prefix"""
        try:
            self.plugin.set_setting("PATTERN", "(POL-){R6}")
        except ValidationError:
            self.fail("Valid random pattern (POL-){R6} raised a ValidationError")

    def test_random_pattern_zero_length_invalid(self):
        """{R0} must be rejected (no zero-digit numbers)"""
        with self.assertRaises(ValidationError):
            self.plugin.set_setting("PATTERN", "{R0}")

    def test_random_pattern_bad_letter_invalid(self):
        """{X6} uses the wrong letter and must be rejected"""
        with self.assertRaises(ValidationError):
            self.plugin.set_setting("PATTERN", "{X6}")

    def test_random_only_literals_invalid(self):
        """Random group is needed to satisfy 'more than literals' too"""
        # Sanity: literals + nothing else still fails
        with self.assertRaises(ValidationError):
            self.plugin.set_setting("PATTERN", "(POL-)")

    def test_random_generates_correct_length(self):
        """A {R6} pattern should produce a 6-digit IPN with no leading zero"""
        self.plugin.set_setting("PATTERN", "{R6}")

        cat = PartCategory.objects.all().first()
        new_part = Part.objects.create(category=cat, name="PartName")

        part = Part.objects.get(pk=new_part.pk)
        self.assertIsNotNone(part.IPN)
        self.assertEqual(len(part.IPN), 6)
        self.assertTrue(part.IPN.isdigit())
        self.assertNotEqual(part.IPN[0], "0")

    def test_random_with_prefix(self):
        """(POL-){R6} should produce POL- + 6 digits"""
        self.plugin.set_setting("PATTERN", "(POL-){R6}")

        cat = PartCategory.objects.all().first()
        new_part = Part.objects.create(category=cat, name="PartName")

        part = Part.objects.get(pk=new_part.pk)
        self.assertIsNotNone(part.IPN)
        self.assertTrue(part.IPN.startswith("POL-"))
        self.assertEqual(len(part.IPN), 10)
        self.assertTrue(part.IPN[4:].isdigit())

    def test_random_uniqueness_across_many_parts(self):
        """Generating many parts should not produce duplicates"""
        self.plugin.set_setting("PATTERN", "{R6}")

        cat = PartCategory.objects.all().first()
        ipns = set()
        for _ in range(20):
            p = Part.objects.create(category=cat, name="PartName")
            part = Part.objects.get(pk=p.pk)
            self.assertIsNotNone(part.IPN)
            ipns.add(part.IPN)

        self.assertEqual(len(ipns), 20)

    def test_random_collision_retry(self):
        """If a draw collides with an existing IPN, the plugin should retry"""
        self.plugin.set_setting("PATTERN", "{R1}")

        cat = PartCategory.objects.all().first()
        # Pre-fill 8 of the 9 possible 1-digit IPNs (1..8)
        for digit in "12345678":
            Part.objects.create(category=cat, name="PartName", IPN=digit)

        p = Part.objects.create(category=cat, name="PartName")
        part = Part.objects.get(pk=p.pk)
        # Only "9" is left available
        self.assertEqual(part.IPN, "9")


class IPNGeneratorModelTests(TestCase):
    """Verify model behaviours"""

    def setUp(self):
        """Set up test environment"""
        setup_func(self)

    def tearDown(self):
        """Teardown test environment"""
        teardown_func()

    def test_supplier_part_does_not_trigger_plugin(self):
        """Supplier parts events should not trigger the plugin"""

        cat = PartCategory.objects.all().first()
        part = Part.objects.create(category=cat, name="PartName")
        supplier = Company.objects.create(name="Suppliercompany", currency="USD")

        with self.assertLogs(logger=logger, level="DEBUG") as cm:
            SupplierPart.objects.create(part=part, SKU="abc", supplier=supplier)
            self.assertNotIn(
                "DEBUG:inventree:Plugin 'ipngen' is processing triggered event 'part_part.created'",
                cm[1],
            )
