"""
TDD test to ensure the Python FlavorFooter model is consistent with the
canonical 108-byte Go specification.
"""
import struct

from flavor.models import FOOTER_SIZE, FOOTER_STRUCT_FORMAT


def test_python_footer_model_matches_go_specification():
    """
    Verifies that the Python attrs model for the PSPF footer has the exact
    size and struct format string required by the canonical Go implementation.
    """
    EXPECTED_FOOTER_SIZE = 108
    EXPECTED_STRUCT_FORMAT = "<QQQQQQQQQQQQHHII"

    assert FOOTER_SIZE == EXPECTED_FOOTER_SIZE
    assert FOOTER_STRUCT_FORMAT == EXPECTED_STRUCT_FORMAT
    assert struct.calcsize(FOOTER_STRUCT_FORMAT) == EXPECTED_FOOTER_SIZE


# 📦🍜🧪🪄
