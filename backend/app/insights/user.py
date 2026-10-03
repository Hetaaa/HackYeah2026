"""Normalized input of the algorithm for ONE user, independent of where the data came from."""

from dataclasses import dataclass

import pandas as pd


@dataclass
class UserData:
    """
    user_id  any id (PMData: "p06"; real product: the user's id)
    nights   index = wake date (local); columns: end (local datetime), sleep_type ("stages" |
             "classic") + config.NIGHT_COLS. One validated main sleep per date (fitbit.nights).
    days     index = local calendar date; config.DAY_COLS + wear_min, wear_day (fitbit.days)
    surveys  one row per check-in: ts_utc (tz-aware UTC) + mood, fatigue, stress (1-5),
             readiness (0-10), soreness, sleep_quality (1-5), sleep_duration_h (all optional
             except mood/fatigue/stress, which make the label)
    """

    user_id: str
    nights: pd.DataFrame
    days: pd.DataFrame
    surveys: pd.DataFrame
