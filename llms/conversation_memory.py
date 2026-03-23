
from dataclasses import dataclass, field
from typing import Optional

MAX_HISTORY = 20
MAX_CONTEXT_CHARS = 3000


@dataclass
class ConversationMemory:
    
    messages: list = field(default_factory=list)
    current_alloy_name: Optional[str] = None
    current_composition: Optional[dict] = None
    current_results: Optional[dict] = None
    current_thinking_steps: list = field(default_factory=list)
    
    def add_user_message(self, text: str):
        self.messages.append({"role": "user", "content": text})
        self._trim()
    
    def add_assistant_message(self, text: str, alloy_name: str = None,
                               composition: dict = None, results: dict = None,
                               thinking_steps: list = None):
        self.messages.append({"role": "assistant", "content": text})
        
        if alloy_name:
            self.current_alloy_name = alloy_name
        if composition:
            self.current_composition = composition
        if results:
            self.current_results = results
        if thinking_steps:
            self.current_thinking_steps = thinking_steps
        
        self._trim()
    
    def get_context_for_llm(self) -> list[dict]:
        context_messages = []
        
        state_parts = []
        if self.current_alloy_name:
            state_parts.append(f"Current alloy being discussed: {self.current_alloy_name}")
        if self.current_composition:
            top_elems = sorted(self.current_composition.items(),
                             key=lambda x: -x[1])[:6]
            comp_str = ", ".join(f"{s}:{v*100:.1f}%" for s, v in top_elems)
            state_parts.append(f"Current composition: {comp_str}")
        if self.current_results:
            score = self.current_results.get("composite_score")
            if score:
                state_parts.append(f"Latest analysis score: {score:.1f}/100")
        
        if state_parts:
            context_messages.append({
                "role": "system",
                "content": "Current context:\n" + "\n".join(state_parts)
            })
        
        total_chars = sum(len(m.get("content", "")) for m in context_messages)
        for msg in self.messages[-10:]:
            msg_len = len(msg.get("content", ""))
            if total_chars + msg_len > MAX_CONTEXT_CHARS:
                break
            context_messages.append(msg)
            total_chars += msg_len
        
        return context_messages
    
    def get_last_user_message(self) -> Optional[str]:
        for msg in reversed(self.messages):
            if msg["role"] == "user":
                return msg["content"]
        return None
    
    def clear(self):
        self.messages.clear()
        self.current_alloy_name = None
        self.current_composition = None
        self.current_results = None
        self.current_thinking_steps = []
    
    def _trim(self):
        if len(self.messages) > MAX_HISTORY:
            self.messages = self.messages[-MAX_HISTORY:]
