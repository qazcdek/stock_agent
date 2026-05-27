from abc import ABC, abstractmethod
from stock_agent.core.schemas import AgentReport

class Analyst(ABC):
    """Abstract Base Class for all sub-analysis agents."""
    
    @abstractmethod
    async def analyze(self, ticker: str) -> AgentReport:
        """Runs specialized research and returns an AgentReport containing analysis scores and reasoning."""
        pass
