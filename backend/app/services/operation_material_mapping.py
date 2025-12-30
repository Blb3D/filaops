"""
Maps operation codes to BOM consume stages.

This determines which materials are needed at each operation.
"""
from typing import List, Set

# Operation code to consume stage mapping
# Multiple operation codes can map to the same consume stage
OPERATION_CONSUME_STAGES = {
    # Production operations - consume raw materials, filament
    "PRINT": ["production", "any"],
    "EXTRUDE": ["production", "any"],
    "MOLD": ["production", "any"],
    "CUT": ["production", "any"],
    "MACHINE": ["production", "any"],

    # Assembly operations - consume hardware, subassemblies
    "ASSEMBLE": ["assembly", "production", "any"],
    "BUILD": ["assembly", "production", "any"],
    "WELD": ["assembly", "production", "any"],

    # Finishing operations - typically no material consumption
    "CLEAN": ["any"],
    "SAND": ["any"],
    "PAINT": ["finishing", "any"],
    "COAT": ["finishing", "any"],

    # Quality operations - typically no material consumption
    "QC": ["any"],
    "INSPECT": ["any"],
    "TEST": ["any"],

    # Shipping operations - consume packaging materials
    "PACK": ["shipping", "any"],
    "SHIP": ["shipping", "any"],
    "LABEL": ["shipping", "any"],
}

# Default stages if operation code not found
DEFAULT_CONSUME_STAGES = ["production", "any"]


def get_consume_stages_for_operation(operation_code: str) -> List[str]:
    """
    Get the consume stages that apply to an operation code.

    Args:
        operation_code: The operation code (e.g., "PRINT", "PACK")

    Returns:
        List of consume stages to check for this operation
    """
    if not operation_code:
        return DEFAULT_CONSUME_STAGES

    code_upper = operation_code.upper()
    return OPERATION_CONSUME_STAGES.get(code_upper, DEFAULT_CONSUME_STAGES)


def get_all_consume_stages() -> Set[str]:
    """Get all known consume stages."""
    stages = set()
    for stage_list in OPERATION_CONSUME_STAGES.values():
        stages.update(stage_list)
    return stages
