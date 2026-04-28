import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM
from langchain_core.output_parsers import JsonOutputParser

logger = logging.getLogger(__name__)

class Action(BaseModel):
    device_id: str = Field(description="The exact ID of the device to control as seen in the registry.")
    command: str = Field(description="The command to send, e.g., 'on', 'off', or 'toggle'.")
    reason: str = Field(description="Short reason why this action is being taken.")

class AIResponse(BaseModel):
    actions: List[Action] = Field(default_factory=list, description="List of actions to execute on devices. Empty if no action is needed.")
    conversation_reply: str = Field(description="Your normal conversation response to the user.")

class AIAgent:
    def __init__(self, model_name: str = "gemma2:latest"):
        self.model = OllamaLLM(model=model_name, temperature=0.1)
        self.parser = JsonOutputParser(pydantic_object=AIResponse)
        
        self.prompt = PromptTemplate(
            template=(
                "You are Lumi, an autonomous AI assistant that manages home automation.\n"
                "Your goal is to fulfill user requests by taking actions on the smart devices in the registry, and replying to them.\n"
                "You must strictly output a valid JSON object matching the format instructions. Do NOT wrap the JSON in markdown code blocks, just output the raw JSON string.\n\n"
                "Device Registry & Current States:\n{devices}\n\n"
                "Format Instructions:\n{format_instructions}\n\n"
                "User Request: {question}\n\n"
            ),
            input_variables=["devices", "question"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )
        
        # Autonomous Loop Prompt
        self.auto_prompt = PromptTemplate(
            template=(
                "You are Lumi, a proactive background intelligence checking the state of the home.\n"
                "You must evaluate the current time, the sun's position, and the states of the devices to determine if any unprompted automated action needs to occur (like turning on lights if it got dark, or turning off devices late at night).\n"
                "If an action SHOULD be taken, output the required JSON actions. If NO action is needed, output an empty actions list.\n\n"
                "Context & Environment:\n{environment}\n\n"
                "Device Registry & Current States:\n{devices}\n\n"
                "Format Instructions:\n{format_instructions}\n\n"
                "Your reasoning goes in 'conversation_reply' explaining why you evaluated taking/not taking action.\n"
            ),
            input_variables=["environment", "devices"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )
        
        # LCEL chains
        self.chain = self.prompt | self.model | self.parser
        self.auto_chain = self.auto_prompt | self.model | self.parser

    def process_command(self, user_command: str, device_context: str) -> Optional[dict]:
        """Invoke the LLM with the structured output chain"""
        try:
            logger.info(f"Processing command: {user_command}")
            result = self.chain.invoke({
                "devices": device_context,
                "question": user_command
            })
            return result
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return None

    def evaluate_autonomous_actions(self, environment_context: str, device_context: str) -> Optional[dict]:
        """Invoke the LLM with the autonomous reasoning chain"""
        try:
            logger.info("Executing periodic autonomous evaluation...")
            result = self.auto_chain.invoke({
                "environment": environment_context,
                "devices": device_context
            })
            return result
        except Exception as e:
            logger.error(f"Failed to parse autonomous LLM response: {e}")
            return None
