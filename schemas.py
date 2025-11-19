from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# Define schemas so collections are created with consistent structure

class Auction(BaseModel):
    name: str
    category: str
    settings: Dict[str, Any]

class Team(BaseModel):
    auction_id: str
    name: str
    captain: Optional[str] = None
    budget_left: int
    players: List[Dict[str, Any]] = Field(default_factory=list)
