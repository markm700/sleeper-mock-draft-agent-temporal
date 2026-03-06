# Position encoding map (consistent with prediction activity)
POSITION_MAP = {
    "QB": 0, "RB": 1, "WR": 2, "TE": 3, "K": 4, "DEF": 5
}

# Status encoding map
STATUS_MAP = {
    "Active": 1.0, "Inactive": 0.0, "Reserve": 0.5, "PUP": 0.3, "Suspended": 0.2
}