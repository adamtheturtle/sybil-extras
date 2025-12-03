"""
Tests for grouping markers.
"""

import pytest

from sybil_extras.grouping_markers import (
    BlockPosition,
    GroupDelimiters,
    extract_blocks,
    get_group_delimiters,
    insert_markers,
    validate_markers,
)


class TestGroupDelimiters:
    """
    Tests for GroupDelimiters dataclass.
    """

    def test_get_start_marker(self) -> None:
        """
        Test getting start marker for a block.
        """
        delimiters = GroupDelimiters(
            start_template="# start-{block_index}",
            end_template="# end-{block_index}",
        )
        assert delimiters.get_start_marker(0) == "# start-0"
        assert delimiters.get_start_marker(5) == "# start-5"

    def test_get_end_marker(self) -> None:
        """
        Test getting end marker for a block.
        """
        delimiters = GroupDelimiters(
            start_template="# start-{block_index}",
            end_template="# end-{block_index}",
        )
        assert delimiters.get_end_marker(0) == "# end-0"
        assert delimiters.get_end_marker(5) == "# end-5"


class TestGetGroupDelimiters:
    """
    Tests for get_group_delimiters function.
    """

    def test_python_delimiters(self) -> None:
        """
        Test Python comment delimiters.
        """
        delimiters = get_group_delimiters("python")
        assert (
            delimiters.get_start_marker(0)
            == "# doccmd-group-delimiter: start-block-0"
        )
        assert (
            delimiters.get_end_marker(0)
            == "# doccmd-group-delimiter: end-block-0"
        )

    def test_javascript_delimiters(self) -> None:
        """
        Test JavaScript comment delimiters.
        """
        delimiters = get_group_delimiters("javascript")
        assert (
            delimiters.get_start_marker(0)
            == "// doccmd-group-delimiter: start-block-0"
        )
        assert (
            delimiters.get_end_marker(0)
            == "// doccmd-group-delimiter: end-block-0"
        )

    def test_html_delimiters(self) -> None:
        """
        Test HTML comment delimiters with closing markers.
        """
        delimiters = get_group_delimiters("html")
        assert (
            delimiters.get_start_marker(0)
            == "<!-- doccmd-group-delimiter: start-block-0 -->"
        )
        assert (
            delimiters.get_end_marker(0)
            == "<!-- doccmd-group-delimiter: end-block-0 -->"
        )

    def test_case_insensitive(self) -> None:
        """
        Test language matching is case-insensitive.
        """
        delimiters_lower = get_group_delimiters("python")
        delimiters_upper = get_group_delimiters("PYTHON")
        delimiters_mixed = get_group_delimiters("Python")
        assert delimiters_lower == delimiters_upper == delimiters_mixed

    def test_unsupported_language(self) -> None:
        """
        Test error for unsupported language.
        """
        with pytest.raises(
            ValueError, match="Language 'foobar' is not supported"
        ):
            get_group_delimiters("foobar")


class TestInsertMarkers:
    """
    Tests for insert_markers function.
    """

    def test_single_block(self) -> None:
        """
        Test inserting markers for a single block.
        """
        source = "x = 1\ny = 2\n"
        positions = [BlockPosition(start_line=0, end_line=2, block_index=0)]
        delimiters = get_group_delimiters("python")

        result = insert_markers(
            grouped_source=source,
            block_positions=positions,
            delimiters=delimiters,
        )

        expected = (
            "# doccmd-group-delimiter: start-block-0\n"
            "x = 1\n"
            "y = 2\n"
            "# doccmd-group-delimiter: end-block-0\n"
        )
        assert result == expected

    def test_multiple_blocks(self) -> None:
        """
        Test inserting markers for multiple blocks.
        """
        source = "x = 1\n\ny = 2\n"
        positions = [
            BlockPosition(start_line=0, end_line=1, block_index=0),
            BlockPosition(start_line=2, end_line=3, block_index=1),
        ]
        delimiters = get_group_delimiters("python")

        result = insert_markers(
            grouped_source=source,
            block_positions=positions,
            delimiters=delimiters,
        )

        expected = (
            "# doccmd-group-delimiter: start-block-0\n"
            "x = 1\n"
            "# doccmd-group-delimiter: end-block-0\n"
            "\n"
            "# doccmd-group-delimiter: start-block-1\n"
            "y = 2\n"
            "# doccmd-group-delimiter: end-block-1\n"
        )
        assert result == expected

    def test_blocks_with_padding(self) -> None:
        """
        Test inserting markers with padding between blocks.
        """
        source = "x = 1\n\n\n\ny = 2\n"
        positions = [
            BlockPosition(start_line=0, end_line=1, block_index=0),
            BlockPosition(start_line=4, end_line=5, block_index=1),
        ]
        delimiters = get_group_delimiters("python")

        result = insert_markers(
            grouped_source=source,
            block_positions=positions,
            delimiters=delimiters,
        )

        expected = (
            "# doccmd-group-delimiter: start-block-0\n"
            "x = 1\n"
            "# doccmd-group-delimiter: end-block-0\n"
            "\n"
            "\n"
            "\n"
            "# doccmd-group-delimiter: start-block-1\n"
            "y = 2\n"
            "# doccmd-group-delimiter: end-block-1\n"
        )
        assert result == expected


class TestExtractBlocks:
    """
    Tests for extract_blocks function.
    """

    def test_extract_single_block(self) -> None:
        """
        Test extracting a single block.
        """
        delimiters = get_group_delimiters("python")
        marked_source = (
            "# doccmd-group-delimiter: start-block-0\n"
            "x = 1\n"
            "y = 2\n"
            "# doccmd-group-delimiter: end-block-0\n"
        )

        blocks = extract_blocks(
            marked_source=marked_source,
            delimiters=delimiters,
        )

        assert len(blocks) == 1
        assert blocks[0] == "x = 1\ny = 2\n"

    def test_extract_multiple_blocks(self) -> None:
        """
        Test extracting multiple blocks.
        """
        delimiters = get_group_delimiters("python")
        marked_source = (
            "# doccmd-group-delimiter: start-block-0\n"
            "x = 1\n"
            "# doccmd-group-delimiter: end-block-0\n"
            "\n"
            "# doccmd-group-delimiter: start-block-1\n"
            "y = 2\n"
            "# doccmd-group-delimiter: end-block-1\n"
        )

        blocks = extract_blocks(
            marked_source=marked_source,
            delimiters=delimiters,
        )

        assert len(blocks) == 2
        assert blocks[0] == "x = 1\n"
        assert blocks[1] == "y = 2\n"

    def test_extract_ignores_unmarked_content(self) -> None:
        """
        Test that content outside markers is ignored.
        """
        delimiters = get_group_delimiters("python")
        marked_source = (
            "# this is ignored\n"
            "# doccmd-group-delimiter: start-block-0\n"
            "x = 1\n"
            "# doccmd-group-delimiter: end-block-0\n"
            "# this is also ignored\n"
        )

        blocks = extract_blocks(
            marked_source=marked_source,
            delimiters=delimiters,
        )

        assert len(blocks) == 1
        assert blocks[0] == "x = 1\n"

    def test_extract_missing_end_marker(self) -> None:
        """
        Test error when end marker is missing.
        """
        delimiters = get_group_delimiters("python")
        marked_source = "# doccmd-group-delimiter: start-block-0\nx = 1\n"

        with pytest.raises(ValueError, match="Unclosed block 0"):
            extract_blocks(
                marked_source=marked_source,
                delimiters=delimiters,
            )

    def test_extract_end_without_start(self) -> None:
        """
        Test error when end marker appears without start.
        """
        delimiters = get_group_delimiters("python")
        marked_source = "x = 1\n# doccmd-group-delimiter: end-block-0\n"

        with pytest.raises(
            ValueError, match="Found end marker without matching start"
        ):
            extract_blocks(
                marked_source=marked_source,
                delimiters=delimiters,
            )

    def test_extract_nested_start(self) -> None:
        """
        Test error when start marker appears inside block.
        """
        delimiters = get_group_delimiters("python")
        marked_source = (
            "# doccmd-group-delimiter: start-block-0\n"
            "x = 1\n"
            "# doccmd-group-delimiter: start-block-0\n"
            "# doccmd-group-delimiter: end-block-0\n"
        )

        with pytest.raises(
            ValueError, match="Found start marker while already inside"
        ):
            extract_blocks(
                marked_source=marked_source,
                delimiters=delimiters,
            )


class TestValidateMarkers:
    """
    Tests for validate_markers function.
    """

    def test_valid_single_block(self) -> None:
        """
        Test validation of valid single block.
        """
        delimiters = get_group_delimiters("python")
        marked_source = (
            "# doccmd-group-delimiter: start-block-0\n"
            "x = 1\n"
            "# doccmd-group-delimiter: end-block-0\n"
        )

        assert validate_markers(
            marked_source=marked_source,
            delimiters=delimiters,
            expected_block_count=1,
        )

    def test_valid_multiple_blocks(self) -> None:
        """
        Test validation of valid multiple blocks.
        """
        delimiters = get_group_delimiters("python")
        marked_source = (
            "# doccmd-group-delimiter: start-block-0\n"
            "x = 1\n"
            "# doccmd-group-delimiter: end-block-0\n"
            "# doccmd-group-delimiter: start-block-1\n"
            "y = 2\n"
            "# doccmd-group-delimiter: end-block-1\n"
        )

        assert validate_markers(
            marked_source=marked_source,
            delimiters=delimiters,
            expected_block_count=2,
        )

    def test_invalid_block_count(self) -> None:
        """
        Test validation fails when block count doesn't match.
        """
        delimiters = get_group_delimiters("python")
        marked_source = (
            "# doccmd-group-delimiter: start-block-0\n"
            "x = 1\n"
            "# doccmd-group-delimiter: end-block-0\n"
        )

        assert not validate_markers(
            marked_source=marked_source,
            delimiters=delimiters,
            expected_block_count=2,
        )

    def test_invalid_malformed_markers(self) -> None:
        """
        Test validation fails when markers are malformed.
        """
        delimiters = get_group_delimiters("python")
        marked_source = (
            "# doccmd-group-delimiter: start-block-0\nx = 1\n"
            # Missing end marker
        )

        assert not validate_markers(
            marked_source=marked_source,
            delimiters=delimiters,
            expected_block_count=1,
        )


class TestRoundTrip:
    """
    Tests for round-trip (insert then extract) operations.
    """

    def test_roundtrip_single_block(self) -> None:
        """
        Test that insert + extract returns original content.
        """
        original = "x = 1\ny = 2\n"
        positions = [BlockPosition(start_line=0, end_line=2, block_index=0)]
        delimiters = get_group_delimiters("python")

        marked = insert_markers(
            grouped_source=original,
            block_positions=positions,
            delimiters=delimiters,
        )

        blocks = extract_blocks(marked_source=marked, delimiters=delimiters)

        assert len(blocks) == 1
        assert blocks[0] == original

    def test_roundtrip_multiple_blocks(self) -> None:
        """
        Test round-trip with multiple blocks.
        """
        block1 = "x = 1\n"
        block2 = "y = 2\n"
        combined = f"{block1}\n{block2}"

        positions = [
            BlockPosition(start_line=0, end_line=1, block_index=0),
            BlockPosition(start_line=2, end_line=3, block_index=1),
        ]
        delimiters = get_group_delimiters("python")

        marked = insert_markers(
            grouped_source=combined,
            block_positions=positions,
            delimiters=delimiters,
        )

        blocks = extract_blocks(marked_source=marked, delimiters=delimiters)

        assert len(blocks) == 2
        assert blocks[0] == block1
        assert blocks[1] == block2
