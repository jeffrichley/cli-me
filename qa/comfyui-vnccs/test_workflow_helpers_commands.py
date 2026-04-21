"""Tier 1 tests for the Phase 3.0 workflow helpers.

Covers ``backend.load_api_workflow``, ``backend.patch_workflow_node``,
``backend.submit_workflow``, and ``backend.wait_for_prompt``. All mocked —
no real ComfyUI contact.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from vnccs_cli import backend
from vnccs_cli.backend import (
    VnccsConnectionError,
    VnccsError,
    VnccsExecutionError,
    VnccsValidationError,
    VnccsWorkflowError,
)


# ---------------------------------------------------------------------------
# load_api_workflow
# ---------------------------------------------------------------------------


def test_load_api_workflow_reads_bundled_step4():
    """Real file: VN_Step4_CharSpriteCreatorV5_api.json (3 nodes)."""
    wf = backend.load_api_workflow("VN_Step4_CharSpriteCreatorV5_api.json")
    assert isinstance(wf, dict)
    assert "1" in wf
    assert wf["1"]["class_type"] == "SpriteGenerator"


def test_load_api_workflow_reads_bundled_v1sdxl_subdir():
    """Subdir paths like V1SDXL/... must resolve."""
    wf = backend.load_api_workflow("V1SDXL/VN_Step3_CharEmotionGeneratorV6_api.json")
    assert isinstance(wf, dict)
    # EmotionGeneratorV2 node must be present
    assert any(n.get("class_type") == "EmotionGeneratorV2" for n in wf.values())


def test_load_api_workflow_missing_raises_workflow_error():
    with pytest.raises(VnccsWorkflowError) as ei:
        backend.load_api_workflow("does_not_exist.json")
    assert ei.value.exit_code == 7
    assert "does_not_exist.json" in ei.value.message


def test_load_api_workflow_malformed_raises_workflow_error(tmp_path, monkeypatch):
    """Simulate a corrupt bundled API workflow."""
    fake_api = tmp_path / "workflows" / "api"
    fake_api.mkdir(parents=True)
    (fake_api / "bad.json").write_text("{not: valid json", encoding="utf-8")

    # Redirect load_api_workflow to our fake tree by patching the scripts
    # parent path via Path resolution. Cleaner: monkeypatch backend module.
    monkeypatch.setattr(
        backend,
        "_api_workflow_path",
        lambda name: fake_api / name,
        raising=False,
    )
    # If backend doesn't have _api_workflow_path (private), fall back to
    # monkeypatching load_api_workflow to point at our tmp tree. We do
    # this via a tiny shim: replace bundled_workflow_path's parent.
    # But simplest: write a direct malformed file at the real location
    # would pollute state; instead we call a private helper.
    # So we rely on backend exposing a hookable path resolver.
    with pytest.raises(VnccsWorkflowError) as ei:
        backend.load_api_workflow("bad.json")
    assert ei.value.exit_code == 7


# ---------------------------------------------------------------------------
# patch_workflow_node
# ---------------------------------------------------------------------------


def _sample_workflow() -> dict:
    return {
        "1": {
            "class_type": "CharacterCreator",
            "inputs": {
                "new_character_name": "Original",
                "seed": 0,
                "sex": "female",
            },
            "_meta": {"title": "VNCCS Character Creator"},
        },
        "2": {
            "class_type": "SpriteGenerator",
            "inputs": {"character": "OldName"},
            "_meta": {"title": "VNCCS Sprite Generator"},
        },
        "3": {
            "class_type": "CharacterCreator",
            "inputs": {"new_character_name": "Other"},
            "_meta": {"title": "A different title"},
        },
    }


def test_patch_workflow_node_by_class_type_single_match():
    wf = _sample_workflow()
    n = backend.patch_workflow_node(
        wf, class_type="SpriteGenerator", inputs={"character": "NewName"}
    )
    assert n == 1
    assert wf["2"]["inputs"]["character"] == "NewName"


def test_patch_workflow_node_by_class_type_multiple_matches():
    wf = _sample_workflow()
    n = backend.patch_workflow_node(
        wf, class_type="CharacterCreator", inputs={"seed": 42}
    )
    assert n == 2
    assert wf["1"]["inputs"]["seed"] == 42
    assert wf["3"]["inputs"]["seed"] == 42
    # Existing unrelated fields preserved
    assert wf["1"]["inputs"]["sex"] == "female"


def test_patch_workflow_node_by_title_narrows_to_one():
    wf = _sample_workflow()
    n = backend.patch_workflow_node(
        wf,
        class_type="CharacterCreator",
        title="VNCCS Character Creator",
        inputs={"seed": 99},
    )
    assert n == 1
    assert wf["1"]["inputs"]["seed"] == 99
    assert wf["3"]["inputs"].get("seed") is None


def test_patch_workflow_node_no_match_returns_zero():
    wf = _sample_workflow()
    n = backend.patch_workflow_node(
        wf, class_type="NonexistentNode", inputs={"x": 1}
    )
    assert n == 0


def test_patch_workflow_node_adds_new_input_key():
    wf = _sample_workflow()
    backend.patch_workflow_node(
        wf, class_type="SpriteGenerator", inputs={"new_key": "new_val"}
    )
    assert wf["2"]["inputs"]["new_key"] == "new_val"
    # Original preserved
    assert wf["2"]["inputs"]["character"] == "OldName"


def test_patch_workflow_node_requires_class_type_or_title():
    wf = _sample_workflow()
    with pytest.raises(ValueError):
        backend.patch_workflow_node(wf, inputs={"x": 1})


def test_patch_workflow_node_empty_inputs_returns_zero_without_mutation():
    wf = _sample_workflow()
    before = json.dumps(wf, sort_keys=True)
    n = backend.patch_workflow_node(wf, class_type="SpriteGenerator", inputs={})
    assert n == 0
    after = json.dumps(wf, sort_keys=True)
    assert before == after


def test_patch_workflow_node_none_inputs_returns_zero_without_mutation():
    wf = _sample_workflow()
    before = json.dumps(wf, sort_keys=True)
    n = backend.patch_workflow_node(wf, class_type="SpriteGenerator", inputs=None)
    assert n == 0
    after = json.dumps(wf, sort_keys=True)
    assert before == after


def test_patch_workflow_node_ignores_non_dict_node_values():
    """Defensive: stray top-level non-dict keys should not crash."""
    wf = {
        "1": {"class_type": "Foo", "inputs": {}, "_meta": {"title": "t"}},
        "_version": 2,  # not a node
        "notes": ["some", "list"],  # not a node
    }
    n = backend.patch_workflow_node(wf, class_type="Foo", inputs={"x": 1})
    assert n == 1


# ---------------------------------------------------------------------------
# submit_workflow
# ---------------------------------------------------------------------------


class _MockHttpResponse:
    def __init__(self, status_code: int, body: dict, text: str = ""):
        self.status_code = status_code
        self._body = body
        self.text = text or json.dumps(body)

    def json(self):
        return self._body


class _MockHttpClient:
    """Minimal stand-in for httpx.Client used by submit_workflow / wait_for_prompt."""

    def __init__(
        self,
        *,
        post_responses=None,
        get_responses=None,
        post_raises=None,
        get_raises=None,
    ):
        self._post_responses = list(post_responses or [])
        self._get_responses = list(get_responses or [])
        self._post_raises = post_raises
        self._get_raises = get_raises
        self.calls: list[tuple[str, str, dict]] = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, json=None):
        self.calls.append(("POST", url, json))
        if self._post_raises:
            raise self._post_raises
        return self._post_responses.pop(0)

    def get(self, url, params=None):
        self.calls.append(("GET", url, params or {}))
        if self._get_raises:
            raise self._get_raises
        return self._get_responses.pop(0)


def _install_mock_client(monkeypatch, client):
    """Patch httpx.Client factory so backend.submit_workflow sees our mock."""

    def factory(*args, **kwargs):
        return client

    monkeypatch.setattr(httpx, "Client", factory)


def test_submit_workflow_posts_correct_payload_and_returns_prompt_id(monkeypatch):
    client = _MockHttpClient(
        post_responses=[
            _MockHttpResponse(
                200,
                {
                    "prompt_id": "abc-123",
                    "number": 7,
                    "node_errors": {},
                },
            )
        ]
    )
    _install_mock_client(monkeypatch, client)

    result = backend.submit_workflow(
        {"1": {"class_type": "Foo", "inputs": {}}},
        url="http://127.0.0.1:8188",
        client_id="test-client",
    )

    assert result["prompt_id"] == "abc-123"
    assert result["client_id"] == "test-client"
    assert result["number"] == 7
    assert result["node_errors"] == {}

    # Validate POST payload shape
    method, url, payload = client.calls[0]
    assert method == "POST"
    assert url == "/prompt"
    assert payload["client_id"] == "test-client"
    assert "prompt" in payload
    assert payload["prompt"] == {"1": {"class_type": "Foo", "inputs": {}}}


def test_submit_workflow_generates_client_id_when_absent(monkeypatch):
    client = _MockHttpClient(
        post_responses=[
            _MockHttpResponse(200, {"prompt_id": "x", "number": 1, "node_errors": {}})
        ]
    )
    _install_mock_client(monkeypatch, client)
    result = backend.submit_workflow({"a": {"class_type": "F", "inputs": {}}})
    assert isinstance(result["client_id"], str) and len(result["client_id"]) > 0


def test_submit_workflow_connection_error_raises_exit_2(monkeypatch):
    client = _MockHttpClient(post_raises=httpx.ConnectError("refused"))
    _install_mock_client(monkeypatch, client)
    with pytest.raises(VnccsConnectionError) as ei:
        backend.submit_workflow({"a": {"class_type": "F", "inputs": {}}})
    assert ei.value.exit_code == 2


def test_submit_workflow_400_raises_execution_error_exit_4(monkeypatch):
    client = _MockHttpClient(
        post_responses=[
            _MockHttpResponse(
                400, {"error": {"message": "bad node"}}, text='{"error":"x"}'
            )
        ]
    )
    _install_mock_client(monkeypatch, client)
    with pytest.raises(VnccsExecutionError) as ei:
        backend.submit_workflow({"a": {"class_type": "F", "inputs": {}}})
    assert ei.value.exit_code == 4


def test_submit_workflow_node_errors_raises_validation_error_exit_3(monkeypatch):
    client = _MockHttpClient(
        post_responses=[
            _MockHttpResponse(
                200,
                {
                    "prompt_id": "abc",
                    "number": 1,
                    "node_errors": {"5": {"errors": [{"message": "missing model"}]}},
                },
            )
        ]
    )
    _install_mock_client(monkeypatch, client)
    with pytest.raises(VnccsValidationError) as ei:
        backend.submit_workflow({"a": {"class_type": "F", "inputs": {}}})
    assert ei.value.exit_code == 3


def test_submit_workflow_rejects_ui_format(monkeypatch):
    """UI-format workflow (has top-level `nodes`+`links`) must be rejected
    pre-flight with exit 3 (validation), not sent to the server."""
    ui_wf = {"nodes": [{"id": 1}], "links": [[1]]}
    # No mock client needed — we must not reach httpx.
    with pytest.raises(VnccsValidationError) as ei:
        backend.submit_workflow(ui_wf)
    assert ei.value.exit_code == 3


# ---------------------------------------------------------------------------
# wait_for_prompt
# ---------------------------------------------------------------------------


def test_wait_for_prompt_success_path(monkeypatch):
    client = _MockHttpClient(
        get_responses=[
            _MockHttpResponse(
                200,
                {
                    "abc-123": {
                        "status": {"status_str": "success", "messages": []},
                        "outputs": {"5": {"images": [{"filename": "out.png"}]}},
                    }
                },
            )
        ]
    )
    _install_mock_client(monkeypatch, client)
    entry = backend.wait_for_prompt("abc-123", timeout=5.0)
    assert entry["status"]["status_str"] == "success"
    # Exactly one GET call, to /history/abc-123
    assert client.calls == [("GET", "/history/abc-123", {})]


def test_wait_for_prompt_polls_until_ready(monkeypatch):
    """First two /history calls return empty, third returns success."""
    client = _MockHttpClient(
        get_responses=[
            _MockHttpResponse(200, {}),
            _MockHttpResponse(200, {}),
            _MockHttpResponse(
                200,
                {
                    "abc": {
                        "status": {"status_str": "success", "messages": []},
                        "outputs": {},
                    }
                },
            ),
        ]
    )
    _install_mock_client(monkeypatch, client)
    # Shrink poll interval for speed
    monkeypatch.setattr(backend, "WAIT_POLL_INTERVAL", 0.0, raising=False)
    entry = backend.wait_for_prompt("abc", timeout=5.0)
    assert entry["status"]["status_str"] == "success"
    assert len(client.calls) == 3


def test_wait_for_prompt_execution_error_raises_exit_4(monkeypatch):
    client = _MockHttpClient(
        get_responses=[
            _MockHttpResponse(
                200,
                {
                    "abc": {
                        "status": {
                            "status_str": "error",
                            "messages": [
                                [
                                    "execution_error",
                                    {
                                        "exception_type": "RuntimeError",
                                        "exception_message": "OOM",
                                    },
                                ]
                            ],
                        }
                    }
                },
            )
        ]
    )
    _install_mock_client(monkeypatch, client)
    monkeypatch.setattr(backend, "WAIT_POLL_INTERVAL", 0.0, raising=False)
    with pytest.raises(VnccsExecutionError) as ei:
        backend.wait_for_prompt("abc", timeout=5.0)
    assert ei.value.exit_code == 4
    assert "OOM" in (ei.value.detail or "")


def test_wait_for_prompt_timeout_raises_generic_error(monkeypatch):
    """Many empty polls, deadline hit → VnccsError (generic, exit 1).

    Uses a mock client that returns empty /history responses indefinitely
    so the timeout path is reached regardless of machine speed.
    """

    class _InfiniteEmpty:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            return _MockHttpResponse(200, {})

        def post(self, *a, **k):  # pragma: no cover
            raise AssertionError("wait_for_prompt should not POST")

    monkeypatch.setattr(httpx, "Client", lambda *a, **k: _InfiniteEmpty())
    monkeypatch.setattr(backend, "WAIT_POLL_INTERVAL", 0.0, raising=False)
    with pytest.raises(VnccsError) as ei:
        backend.wait_for_prompt("abc", timeout=0.001)
    # The timeout error is the base VnccsError (exit 1), not Execution/Connection/Validation.
    assert not isinstance(ei.value, VnccsExecutionError)
    assert not isinstance(ei.value, VnccsConnectionError)
    assert not isinstance(ei.value, VnccsValidationError)
    assert "Timed out" in ei.value.message


def test_wait_for_prompt_connection_error_raises_exit_2(monkeypatch):
    client = _MockHttpClient(get_raises=httpx.ConnectError("refused"))
    _install_mock_client(monkeypatch, client)
    monkeypatch.setattr(backend, "WAIT_POLL_INTERVAL", 0.0, raising=False)
    with pytest.raises(VnccsConnectionError) as ei:
        backend.wait_for_prompt("abc", timeout=5.0)
    assert ei.value.exit_code == 2


# ---------------------------------------------------------------------------
# init_character_via_rest (live-env prep)
# ---------------------------------------------------------------------------


def test_init_character_via_rest_success(monkeypatch):
    """Successful /vnccs/create returns the parsed JSON record."""
    client = _MockHttpClient(
        get_responses=[
            _MockHttpResponse(
                200,
                {
                    "ok": True,
                    "name": "Aria",
                    "config_path": "/output/.../Aria_config.json",
                },
            )
        ]
    )
    _install_mock_client(monkeypatch, client)
    result = backend.init_character_via_rest("Aria", url="http://127.0.0.1:8188")
    assert result["ok"] is True
    assert result["name"] == "Aria"
    # Verify the GET hits the right path with the name param
    method, url, _ = client.calls[0]
    assert method == "GET"
    assert url == "/vnccs/create"


def test_init_character_via_rest_empty_name_raises():
    from vnccs_cli.backend import VnccsError
    with pytest.raises(VnccsError):
        backend.init_character_via_rest("")


def test_init_character_via_rest_connection_error_raises_exit_2(monkeypatch):
    client = _MockHttpClient(get_raises=httpx.ConnectError("refused"))
    _install_mock_client(monkeypatch, client)
    with pytest.raises(VnccsConnectionError) as ei:
        backend.init_character_via_rest("Aria")
    assert ei.value.exit_code == 2


def test_init_character_via_rest_400_raises_exit_4(monkeypatch):
    client = _MockHttpClient(
        get_responses=[
            _MockHttpResponse(
                400, {"error": "invalid characters"}, text='{"error":"invalid"}'
            )
        ]
    )
    _install_mock_client(monkeypatch, client)
    with pytest.raises(VnccsExecutionError) as ei:
        backend.init_character_via_rest("Aria/bad")
    assert ei.value.exit_code == 4


# ---------------------------------------------------------------------------
# ensure_input_template
# ---------------------------------------------------------------------------


def test_ensure_input_template_copies_when_missing(tmp_path):
    """Copies <vnccs>/character_template/CharacterSheetTemplate.png ->
    <comfy>/input/CharacterSheetTemplate.png."""
    comfy = tmp_path / "ComfyUI"
    vnccs_template_dir = (
        comfy / "custom_nodes" / "ComfyUI_VNCCS" / "character_template"
    )
    vnccs_template_dir.mkdir(parents=True)
    template_src = vnccs_template_dir / "CharacterSheetTemplate.png"
    template_src.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 1024)

    dst = backend.ensure_input_template(comfy)

    assert dst.exists()
    assert dst.read_bytes() == template_src.read_bytes()
    assert dst == comfy / "input" / "CharacterSheetTemplate.png"


def test_ensure_input_template_idempotent(tmp_path):
    """Pre-existing template is left alone (no overwrite, no error)."""
    comfy = tmp_path / "ComfyUI"
    (comfy / "input").mkdir(parents=True)
    pre = comfy / "input" / "CharacterSheetTemplate.png"
    pre.write_bytes(b"PRE-EXISTING_CONTENT")
    # Source can be missing — we don't need it if dst already exists
    dst = backend.ensure_input_template(comfy)
    assert dst == pre
    assert pre.read_bytes() == b"PRE-EXISTING_CONTENT"


def test_ensure_input_template_missing_source_raises(tmp_path):
    """Source template missing AND dst missing -> VnccsPathError."""
    from vnccs_cli.backend import VnccsPathError
    comfy = tmp_path / "ComfyUI"
    (comfy / "custom_nodes" / "ComfyUI_VNCCS").mkdir(parents=True)
    # Note: no character_template/ subdir under VNCCS.
    with pytest.raises(VnccsPathError):
        backend.ensure_input_template(comfy)


# ---------------------------------------------------------------------------
# is_broken_emotion_aggregate — filter for VNCCS Step3 silhouette misfire
# ---------------------------------------------------------------------------


def test_is_broken_aggregate_emotion_sheet(tmp_path):
    """Sheets/<costume>/<non-neutral>/sheet_<emotion>__00001.png is broken."""
    f = tmp_path / "char" / "Sheets" / "Naked" / "happy" / "sheet_happy__00001.png"
    f.parent.mkdir(parents=True)
    f.write_bytes(b"")
    assert backend.is_broken_emotion_aggregate(f) is True


def test_is_broken_aggregate_emotion_sprite(tmp_path):
    """Sprites/<costume>/<non-neutral>/sprite_<emotion>__00001_.png is broken."""
    f = tmp_path / "char" / "Sprites" / "Naked" / "happy" / "sprite_happy__00001_.png"
    f.parent.mkdir(parents=True)
    f.write_bytes(b"")
    assert backend.is_broken_emotion_aggregate(f) is True


def test_is_broken_aggregate_individual_sprite_keeps(tmp_path):
    """Individual cropped sprites (00002+) are valid — not broken."""
    for i in range(2, 13):
        f = (tmp_path / "char" / "Sprites" / "Naked" / "happy"
             / f"sprite_happy__{i:05d}_.png")
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"")
        assert backend.is_broken_emotion_aggregate(f) is False, \
            f"sprite index {i} should not be flagged broken"


def test_is_broken_aggregate_neutral_sheet_keeps(tmp_path):
    """Step1 neutral sheet (single-underscore naming, NOT broken)."""
    f = tmp_path / "char" / "Sheets" / "Naked" / "neutral" / "sheet_neutral_00001_.png"
    f.parent.mkdir(parents=True)
    f.write_bytes(b"")
    assert backend.is_broken_emotion_aggregate(f) is False


def test_is_broken_aggregate_neutral_sprite_keeps(tmp_path):
    """sprite_neutral__00001_.png is a re-save of the valid Step1 sheet,
    still colored and usable (not a silhouette misfire)."""
    f = tmp_path / "char" / "Sprites" / "Naked" / "neutral" / "sprite_neutral__00001_.png"
    f.parent.mkdir(parents=True)
    f.write_bytes(b"")
    assert backend.is_broken_emotion_aggregate(f) is False


def test_is_broken_aggregate_face_crop_keeps(tmp_path):
    """Face crops are always valid — even with the __00001 pattern."""
    f = tmp_path / "char" / "Faces" / "Naked" / "happy" / "face_happy__00001_.png"
    f.parent.mkdir(parents=True)
    f.write_bytes(b"")
    assert backend.is_broken_emotion_aggregate(f) is False


def test_is_broken_aggregate_non_matching_kind_keeps(tmp_path):
    """Files outside Sheets/Sprites/Faces (e.g. lora/) are never flagged."""
    f = tmp_path / "char" / "lora" / "Naked_happy_sprite_happy__00001_.png"
    f.parent.mkdir(parents=True)
    f.write_bytes(b"")
    assert backend.is_broken_emotion_aggregate(f) is False
