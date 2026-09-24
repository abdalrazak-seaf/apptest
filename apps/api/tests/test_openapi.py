import json
from pathlib import Path

from api.main import create_app

COMMITTED_SPEC = Path(__file__).parents[3] / "packages/api-client/openapi.json"


def test_operation_ids_are_readable() -> None:
    spec = create_app().openapi()
    assert spec["paths"]["/health"]["get"]["operationId"] == "get_health"
    assert spec["paths"]["/health/ready"]["get"]["operationId"] == "get_readiness"


def test_committed_client_spec_is_up_to_date() -> None:
    """If this fails, run `make api-client` and commit the result."""
    current = create_app().openapi()
    committed = json.loads(COMMITTED_SPEC.read_text("utf-8"))
    assert committed == json.loads(json.dumps(current))
