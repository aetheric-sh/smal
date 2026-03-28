from pydantic import BaseModel, Field

class SMALTransition(BaseModel):
    trigger_state: str = Field(..., description="The name of the state the machine must be in in order for trigger_evt to trigger this transition.")
    trigger_evt: str = Field(..., description="The name of the event that triggers this transition.")
    action: str = Field(..., description="The name of the function to invoke when trigger_evt is received while in trigger_state.")
    landing_state: str = Field(..., description="The state to transition into after executing action in response to receiving trigger_evt while in trigger_state.")
    landing_state_entry_evt: str | None = Field(default=None, description="Event to trigger upon entering landing_state, if any.")

    def __repr__(self) -> str:
        return f"({self.trigger_state}, {self.trigger_evt}, {self.action}, {self.landing_state}, {self.landing_state_entry_evt})"