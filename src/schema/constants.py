import random
from typing import Dict
from sqlalchemy.orm import Session
from .database_models import User, TeamOwner

TEAM_OWNER_FUN_FACT_MAP = {
    "carleyzander": "Carley is not the first person in the league to push something big out of their body after weeks",
    "markm700": "Mark listens to Gangnam Style and Harlem Shake every once in awhile",
    "thehairykid": "Harry is an Xbox, the other owners are more Atari",
    "claytontangen": "Clayton can quote almost any movie he has seen, excerpt High School Musical for some reason",
    "silvertim101": "Be careful when you invite Nathan to a sleepover, he will NOT bring slippers",
    "mshaide": "He hates Christmas because of advent calendars (calendar averse)",
    "TreyFiddy": "Casey once broke his ankle sliding down a stair railing on the way to the bathroom",
    "Jags2024Champs": "Despite being recently married, Cordell's favorite thing is still to type out \'a quick brown fox jumps over the lazy dog\'",
    "einscobar": "He holds 2 distinct honors - first in the league to beat Monkey Ball 2 on Gamecube and first in the league to lose it twice",
    "iggykesh": "Liam has still yet to post his ALS Ice Bucket Challenge video, despite being challenged by multiple people",
}

RANDOM_PERSONALITY_TRAITS = {
    "0": "upside_seeking",         #0=floor preference, 1=ceiling/boom-bust preference
    "1": "floor_preference",       #0=ignores floor, 1=always targets safe picks
    "2": "adp_reach_tendency",     #0=always waits, 0.5=neutral, 1=always reaches
    "3": "injury_tolerance",       #0=avoids any risk, 1=ignores injury status
    "4": "rookie_bias",            #0=avoids rookies, 0.5=neutral, 1=actively targets
    "5": "name_recognition",       #0=pure stats, 1=drafts by name / reputation
    "6": "contrarian",             #0=follows consensus, 1=goes against the board
    "7": "positional_stubbornness" #0=BPA flexible, 1=sticks to positional strategy
}


def get_personality_trait(session: Session, user_id: str = None) -> str:
    """
    Return the personality trait name for a user.

    Looks up the trait from TeamOwner (league-specific), then User (global),
    then falls back to a random choice from RANDOM_PERSONALITY_TRAITS.

    Args:
        session: Active SQLAlchemy session.
        user_id: Sleeper user_id to look up. None returns a random trait.

    Returns:
        str: Trait name, e.g. "upside_seeking" or "contrarian".
    """
    if user_id is not None:
        # 1. Check TeamOwner (league-specific traits take precedence)
        team_owner = (
            session.query(TeamOwner)
            .filter(TeamOwner.user_id == user_id)
            .order_by(TeamOwner.updated_at.desc())
            .first()
        )
        if team_owner and team_owner.personality_fun_fact:
            return team_owner.personality_fun_fact

        # 2. Fall back to User-level traits
        user = session.query(User).filter(User.user_id == user_id).first()
        if user and user.personality_fun_fact:
            return user.personality_fun_fact

    # 3. Generate random traits using RANDOM_PERSONALITY_TRAITS as the trait catalog
    return get_random_personality_trait()

def get_random_personality_trait() -> str:
    """
    Return a randomly selected trait name from RANDOM_PERSONALITY_TRAITS.

    Returns:
        str: One of the trait name values, e.g. "contrarian" or "rookie_bias".
    """
    return random.choice(list(RANDOM_PERSONALITY_TRAITS.values()))

def get_personality_trait_vector(personality_trait: str) -> Dict[str, float]:
    """
    Build a personality trait dict with the named trait set to 0.7 and others randomized.

    Args:
        personality_trait: Trait name to pin at 0.7, e.g. "contrarian".

    Returns:
        Dict[str, float]: Mapping from each trait name to a float value in [0, 1].
    """
    vector = {personality_trait: float(0.7)}
    vector.update({trait: random.random() for trait in RANDOM_PERSONALITY_TRAITS.values() if trait != personality_trait})
    return vector