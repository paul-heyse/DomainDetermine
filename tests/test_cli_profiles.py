import importlib

cli_app = importlib.import_module("DomainDetermine.cli.app")
from DomainDetermine.cli.profiles import ProfileManifest, ProfileStep, validate_profile


def _resolver(verb: str):
    func = getattr(cli_app, verb, None)
    if not callable(func):
        raise ValueError(f"Command '{verb}' is not available for profiles")
    return func


def test_profile_validation_detects_missing_arguments():
    manifest = ProfileManifest(
        name="bad",
        cli_version=cli_app.CLI_VERSION,
        steps=(ProfileStep(verb="ingest", arguments={}),),
    )
    errors = validate_profile(manifest, _resolver)
    assert any("missing required arguments" in error for error in errors)


def test_profile_validation_handles_unknown_verb():
    manifest = ProfileManifest(
        name="unknown",
        cli_version=cli_app.CLI_VERSION,
        steps=(ProfileStep(verb="does_not_exist", arguments={}),),
    )
    errors = validate_profile(manifest, _resolver)
    assert any("does_not_exist" in error for error in errors)


def test_profile_validation_passes_valid_manifest():
    manifest = ProfileManifest(
        name="good",
        cli_version=cli_app.CLI_VERSION,
        steps=(
            ProfileStep(verb="ingest", arguments={"source": "data.json"}),
            ProfileStep(verb="plan", arguments={"plan_spec": "plan.toml"}),
        ),
    )
    errors = validate_profile(manifest, _resolver)
    assert errors == []

