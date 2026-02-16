import pytest

from workflows.team_owner_data_collection import (
    TeamOwnerDataCollectionWorkflow,
    TeamOwnerDataCollectionWorkflowParams,
)


@pytest.mark.asyncio
async def test_team_owner_data_collection_runs_owner_and_roster_activities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    activity_calls: list[tuple[object, tuple[object, ...], dict]] = []

    async def _fake_execute_activity(fn: object, *args: object, **kwargs: object) -> dict:
        activity_calls.append((fn, args, kwargs))
        name = getattr(fn, "__name__", None)
        if name == "get_team_owner_data":
            # Simulate owner data with multiple seasons and leagues
            return {
                "user_id": "user-123",
                "user_leagues": {
                    "2023": [
                        {"league_id": "league-1"},
                        {"league_id": "league-2"},
                    ],
                    "2022": [
                        {"league_id": "league-3"},
                    ],
                },
            }
        if name == "get_team_owner_rosters":
            # The first (and only) arg is GetLeagueRosterParams
            params = args[0]
            league_id = getattr(params, "league_id", None)
            user_id = getattr(params, "user_id", None)
            return {"league_id": league_id, "user_id": user_id, "roster": f"{league_id}-{user_id}"}
        raise AssertionError(f"Unexpected activity function passed to execute_activity: {name}")

    monkeypatch.setattr(
        "src.workflows.team_owner_data_collection.workflow.execute_activity",
        _fake_execute_activity,
    )

    wf = TeamOwnerDataCollectionWorkflow()
    params = TeamOwnerDataCollectionWorkflowParams(
        username="some_user",
        league_name="some_league",
    )

    result = await wf.run(params)

    # activity_data should contain two logical groupings: owner data and owner rosters
    assert "activity_data" in result
    assert len(result["activity_data"]) == 2

    owner_entry = result["activity_data"][0]
    roster_entry = result["activity_data"][1]

    assert owner_entry["activity"] == "get_team_owner_data"
    assert owner_entry["result"]["user_id"] == "user-123"
    assert set(owner_entry["result"]["user_leagues"].keys()) == {"2023", "2022"}

    assert roster_entry["activity"] == "get_team_owner_rosters"
    user_rosters = roster_entry["user_rosters"]
    # We expect one roster result per league_id we returned above (3 total)
    assert len(user_rosters) == 3

    # Convert to mapping for easier assertion
    seen = {(r["season"], r["league_id"]): r["result"] for r in user_rosters}
    assert ("2023", "league-1") in seen
    assert ("2023", "league-2") in seen
    assert ("2022", "league-3") in seen

    # Verify execute_activity call sequence and parameters
    # First call: get_team_owner_data
    assert len(activity_calls) == 1 + 3  # 1 for data, 3 for rosters
    fn0, args0, kwargs0 = activity_calls[0]
    assert getattr(fn0, "__name__", None) == "get_team_owner_data"
    assert len(args0) == 1
    owner_params = args0[0]
    assert getattr(owner_params, "username", None) == "some_user"
    assert getattr(owner_params, "league_name", None) == "some_league"
    assert "start_to_close_timeout" in kwargs0
    assert "retry_policy" in kwargs0

    # Remaining calls: get_team_owner_rosters for each league
    roster_calls = activity_calls[1:]
    called_leagues = []
    for fn, r_args, r_kwargs in roster_calls:
        assert getattr(fn, "__name__", None) == "get_team_owner_rosters"
        assert len(r_args) == 1
        league_params = r_args[0]
        league_id = getattr(league_params, "league_id", None)
        user_id = getattr(league_params, "user_id", None)
        called_leagues.append(league_id)
        assert user_id == "user-123"
        assert "start_to_close_timeout" in r_kwargs
        assert "retry_policy" in r_kwargs

    assert set(called_leagues) == {"league-1", "league-2", "league-3"}
