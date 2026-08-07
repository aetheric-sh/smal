"""Module defining the schema for the Action object in a SMAL file."""

from __future__ import annotations  # Until Python 3.14

from typing import Any

from pydantic import BaseModel, Field


class Action(BaseModel):
    """Schema for the Action object in a SMAL file."""

    name: str = Field(..., description="Name of the action. This will be the function name as it appears in generated code.")

    @classmethod
    def from_shorthand(cls, data: Any) -> Action:
        """Create a Action instance from a short-hand representation in data.

        Args:
            data (Any): The input data for the action, which can be a string (action name) or a dictionary with action properties.

        Raises:
            ValueError: If the input data is not a string or a dictionary.

        Returns:
            Action: The Action instance created from the short-hand representation.

        """
        if isinstance(data, str):
            return cls(name=data)
        if isinstance(data, dict):
            return cls.model_validate(data)
        raise ValueError(f"Invalid short-hand action representation: {data!r}. Expected a string or a dictionary.")
