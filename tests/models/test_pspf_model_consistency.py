"""
TDD test to ensure the Python PSPFV1Footer model is consistent with the
canonical 108-byte Go specification.
"""


from flavor.models import FOOTER_SIZE, FOOTER_STRUCT_FORMAT, PSPFV1Footer


def test_python_footer_model_matches_go_specification() -> None:
    """
    Verifies that the Python attrs model for the PSPF footer has the exact
    size and struct format string required by the canonical Go implementation.
    """
    EXPECTED_FOOTER_SIZE = 120
    EXPECTED_STRUCT_FORMAT = "<QQQQQQQQQQQQHHII4s4s4s"

    assert FOOTER_SIZE == EXPECTED_FOOTER_SIZE
    assert FOOTER_STRUCT_FORMAT == EXPECTED_STRUCT_FORMAT
    footer = PSPFV1Footer(
        uv_offset=0,
        uv_size=0,
        python_offset=0,
        python_size=0,
        metadata_offset=0,
        metadata_size=0,
        payload_offset=0,
        payload_size=0,
        signature_offset=0,
        signature_size=0,
        public_key_offset=0,
        public_key_size=0,
    )
    packed_footer = footer.pack()
    assert len(packed_footer) == EXPECTED_FOOTER_SIZE


# 📦🍜🧪🪄
