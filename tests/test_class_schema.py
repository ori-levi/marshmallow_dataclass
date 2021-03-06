import typing
import unittest
from typing import Any
from uuid import UUID

import dataclasses
from marshmallow import Schema, ValidationError
from marshmallow.fields import Field, UUID as UUIDField, List as ListField, Integer

from marshmallow_dataclass import class_schema


class TestClassSchema(unittest.TestCase):
    def test_simple_unique_schemas(self):
        @dataclasses.dataclass
        class Simple:
            one: str = dataclasses.field()
            two: str = dataclasses.field()

        @dataclasses.dataclass
        class ComplexNested:
            three: int = dataclasses.field()
            four: Simple = dataclasses.field()

        self.assertIs(class_schema(ComplexNested), class_schema(ComplexNested))
        self.assertIs(class_schema(Simple), class_schema(Simple))
        self.assertIs(
            class_schema(Simple),
            class_schema(ComplexNested)._declared_fields["four"].nested,
        )

        complex_set = {
            class_schema(ComplexNested),
            class_schema(ComplexNested, base_schema=None),
            class_schema(ComplexNested, None),
        }
        simple_set = {
            class_schema(Simple),
            class_schema(Simple, base_schema=None),
            class_schema(Simple, None),
        }
        self.assertEqual(len(complex_set), 1)
        self.assertEqual(len(simple_set), 1)

    def test_use_type_mapping_from_base_schema(self):
        class CustomType:
            pass

        class CustomField(Field):
            pass

        class CustomListField(ListField):
            pass

        class BaseSchema(Schema):
            TYPE_MAPPING = {CustomType: CustomField, typing.List: CustomListField}

        @dataclasses.dataclass
        class WithCustomField:
            custom: CustomType
            custom_list: typing.List[float]
            uuid: UUID
            n: int

        schema = class_schema(WithCustomField, base_schema=BaseSchema)()
        self.assertIsInstance(schema.fields["custom"], CustomField)
        self.assertIsInstance(schema.fields["custom_list"], CustomListField)
        self.assertIsInstance(schema.fields["uuid"], UUIDField)
        self.assertIsInstance(schema.fields["n"], Integer)

    def test_filtering_list_schema(self):
        class FilteringListField(ListField):
            def __init__(
                self,
                cls_or_instance: typing.Union[Field, type],
                min: typing.Any,
                max: typing.Any,
                **kwargs,
            ):
                super().__init__(cls_or_instance, **kwargs)
                self.min = min
                self.max = max

            def _deserialize(
                self, value, attr, data, **kwargs
            ) -> typing.List[typing.Any]:
                loaded = super()._deserialize(value, attr, data, **kwargs)
                return [x for x in loaded if self.min <= x <= self.max]

        class BaseSchema(Schema):
            TYPE_MAPPING = {typing.List: FilteringListField}

        @dataclasses.dataclass
        class WithCustomField:
            constrained_floats: typing.List[float] = dataclasses.field(
                metadata={"max": 2.5, "min": 1}
            )
            constrained_strings: typing.List[str] = dataclasses.field(
                metadata={"max": "x", "min": "a"}
            )

        schema = class_schema(WithCustomField, base_schema=BaseSchema)()
        actual = schema.load(
            {
                "constrained_floats": [0, 1, 2, 3],
                "constrained_strings": ["z", "a", "b", "c", ""],
            }
        )
        self.assertEqual(
            actual,
            WithCustomField(
                constrained_floats=[1.0, 2.0], constrained_strings=["a", "b", "c"]
            ),
        )

    def test_any_none(self):
        # See: https://github.com/lovasoa/marshmallow_dataclass/issues/80
        @dataclasses.dataclass
        class A:
            data: Any

        schema = class_schema(A)()
        self.assertEqual(A(data=None), schema.load({"data": None}))
        self.assertEqual(schema.dump(A(data=None)), {"data": None})

    def test_any_none_disallowed(self):
        @dataclasses.dataclass
        class A:
            data: Any = dataclasses.field(metadata={"allow_none": False})

        schema = class_schema(A)()
        self.assertRaises(ValidationError, lambda: schema.load({"data": None}))


if __name__ == "__main__":
    unittest.main()
