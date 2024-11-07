from fastapi import APIRouter

v1_router = APIRouter()


@v1_router.get("/get-future-data")
async def get_relevant():
    # TODO: This is a dummy function that returns a list of changes that are planned for the future.
    # In a real application, this data would be fetched from a database or some other source.
    return {
        "changes": [
            {"type": "feature", "description": "New feature 1", "release": "9.0"},
            {"type": "retirement", "description": "Retiring feature 2", "release": "10.0"},
            {"type": "bugfix", "description": "Fixing bug 3", "release": "8.6"},
            {"type": "deprecation", "description": "Deprecating feature 4", "release": "9.0"},
        ]
    }
