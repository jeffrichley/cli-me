"""Tier 1 tests for `workflow` command group (set / validate / extract).

All tests operate on local JSON fixtures and in-memory PNG/WebP images —
no live ComfyUI server needed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make `scripts/` importable so `from comfyui_cli...` resolves.
scripts_dir = (
    Path(__file__).resolve().parent.parent.parent
    / "skill-repo"
    / "comfyui"
    / "scripts"
)
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


def _write_workflow(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data))
    return path


# --- Tests: workflow set ----------------------------------------------------


class TestWorkflowSet:
    def test_node_id_addressing(self, tmp_path):
        from comfyui_cli.commands.workflow_set import run_set

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_minimal.json")
        )
        out = tmp_path / "out.json"
        run_set(in_file=src, params=["3.seed=42"], out_file=out, inline=False)
        patched = json.loads(out.read_text())
        assert patched["3"]["inputs"]["seed"] == 42
        assert isinstance(patched["3"]["inputs"]["seed"], int)

    def test_at_title_addressing(self, tmp_path):
        from comfyui_cli.commands.workflow_set import run_set

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_minimal.json")
        )
        out = tmp_path / "out.json"
        run_set(
            in_file=src,
            params=["@PositivePrompt.text=a dragon"],
            out_file=out,
            inline=False,
        )
        patched = json.loads(out.read_text())
        assert patched["6"]["inputs"]["text"] == "a dragon"

    def test_class_prefix_addressing(self, tmp_path):
        from comfyui_cli.commands.workflow_set import run_set

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_minimal.json")
        )
        out = tmp_path / "out.json"
        run_set(
            in_file=src,
            params=[
                "class:CheckpointLoaderSimple.ckpt_name=sd_xl_base_1.0.safetensors"
            ],
            out_file=out,
            inline=False,
        )
        patched = json.loads(out.read_text())
        assert (
            patched["4"]["inputs"]["ckpt_name"]
            == "sd_xl_base_1.0.safetensors"
        )

    def test_at_title_fallback_to_class_when_meta_absent(self, tmp_path):
        """When no node has _meta.title matching, fall back to class_type."""
        from comfyui_cli.commands.workflow_set import run_set

        data = _load_fixture("api_workflow_minimal.json")
        for v in data.values():
            v.pop("_meta", None)
        src = _write_workflow(tmp_path / "in.json", data)
        out = tmp_path / "out.json"
        run_set(
            in_file=src,
            params=["@KSampler.seed=99"],
            out_file=out,
            inline=False,
        )
        patched = json.loads(out.read_text())
        assert patched["3"]["inputs"]["seed"] == 99

    def test_at_title_ambiguous_raises(self, tmp_path):
        from comfyui_cli.commands.workflow_set import run_set
        from comfyui_cli.backend import ComfyError

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("ambiguous_titles.json")
        )
        with pytest.raises(ComfyError) as ei:
            run_set(
                in_file=src,
                params=["@Sampler.seed=1"],
                out_file=tmp_path / "out.json",
                inline=False,
            )
        msg = str(ei.value)
        assert "1" in msg and "2" in msg

    def test_class_ambiguous_raises(self, tmp_path):
        from comfyui_cli.commands.workflow_set import run_set
        from comfyui_cli.backend import ComfyError

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("ambiguous_titles.json")
        )
        with pytest.raises(ComfyError):
            run_set(
                in_file=src,
                params=["class:KSampler.seed=1"],
                out_file=tmp_path / "out.json",
                inline=False,
            )

    def test_seed_random_32bit(self, tmp_path):
        from comfyui_cli.commands.workflow_set import run_set

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_minimal.json")
        )
        out = tmp_path / "out.json"
        run_set(in_file=src, params=["3.seed=random"], out_file=out, inline=False)
        patched = json.loads(out.read_text())
        seed = patched["3"]["inputs"]["seed"]
        assert isinstance(seed, int)
        assert 0 <= seed < 2**32

    def test_seed_random64(self, tmp_path):
        from comfyui_cli.commands.workflow_set import run_set

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_minimal.json")
        )
        out = tmp_path / "out.json"
        run_set(
            in_file=src,
            params=["3.seed=random64"],
            out_file=out,
            inline=False,
        )
        patched = json.loads(out.read_text())
        seed = patched["3"]["inputs"]["seed"]
        assert isinstance(seed, int)
        assert 0 <= seed < 2**63

    def test_inline_writes_back(self, tmp_path):
        from comfyui_cli.commands.workflow_set import run_set

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_minimal.json")
        )
        run_set(in_file=src, params=["3.steps=35"], out_file=None, inline=True)
        patched = json.loads(src.read_text())
        assert patched["3"]["inputs"]["steps"] == 35

    def test_out_file_writes_to_out(self, tmp_path):
        from comfyui_cli.commands.workflow_set import run_set

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_minimal.json")
        )
        out = tmp_path / "out.json"
        run_set(in_file=src, params=["3.steps=10"], out_file=out, inline=False)
        assert json.loads(src.read_text())["3"]["inputs"]["steps"] == 20
        assert json.loads(out.read_text())["3"]["inputs"]["steps"] == 10

    def test_stdout_when_no_out_no_inline(self, tmp_path, capsys):
        from comfyui_cli.commands.workflow_set import run_set

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_minimal.json")
        )
        run_set(in_file=src, params=["3.steps=11"], out_file=None, inline=False)
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["3"]["inputs"]["steps"] == 11

    def test_both_out_and_inline_errors(self, tmp_path):
        from comfyui_cli.commands.workflow_set import run_set
        from comfyui_cli.backend import ComfyError

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_minimal.json")
        )
        with pytest.raises(ComfyError):
            run_set(
                in_file=src,
                params=["3.steps=11"],
                out_file=tmp_path / "out.json",
                inline=True,
            )

    def test_json_value_parsing_int_vs_str(self, tmp_path):
        from comfyui_cli.commands.workflow_set import run_set

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_minimal.json")
        )
        out = tmp_path / "out.json"
        run_set(
            in_file=src,
            params=["3.steps=42", '6.text="42"'],
            out_file=out,
            inline=False,
        )
        patched = json.loads(out.read_text())
        assert patched["3"]["inputs"]["steps"] == 42
        assert isinstance(patched["3"]["inputs"]["steps"], int)
        assert patched["6"]["inputs"]["text"] == "42"
        assert isinstance(patched["6"]["inputs"]["text"], str)

    def test_json_value_parsing_list(self, tmp_path):
        from comfyui_cli.commands.workflow_set import run_set

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_minimal.json")
        )
        out = tmp_path / "out.json"
        run_set(
            in_file=src,
            params=["6.text=[1,2,3]"],
            out_file=out,
            inline=False,
        )
        patched = json.loads(out.read_text())
        assert patched["6"]["inputs"]["text"] == [1, 2, 3]

    def test_json_value_fallback_to_string(self, tmp_path):
        from comfyui_cli.commands.workflow_set import run_set

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_minimal.json")
        )
        out = tmp_path / "out.json"
        run_set(
            in_file=src,
            params=["6.text=a cyberpunk cat"],
            out_file=out,
            inline=False,
        )
        patched = json.loads(out.read_text())
        assert patched["6"]["inputs"]["text"] == "a cyberpunk cat"

    def test_at_title_with_dot_uses_rsplit(self, tmp_path):
        """@Title containing '.' — rsplit('.', 1) puts input_key on the right."""
        from comfyui_cli.commands.workflow_set import run_set

        data = {
            "5": {
                "class_type": "KSampler",
                "inputs": {"seed": 0, "steps": 20},
                "_meta": {"title": "v1.0 Sampler"},
            }
        }
        src = _write_workflow(tmp_path / "in.json", data)
        out = tmp_path / "out.json"
        run_set(
            in_file=src,
            params=["@v1.0 Sampler.seed=7"],
            out_file=out,
            inline=False,
        )
        patched = json.loads(out.read_text())
        assert patched["5"]["inputs"]["seed"] == 7

    def test_unknown_node_id_raises(self, tmp_path):
        from comfyui_cli.commands.workflow_set import run_set
        from comfyui_cli.backend import ComfyError

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_minimal.json")
        )
        with pytest.raises(ComfyError):
            run_set(
                in_file=src,
                params=["999.seed=1"],
                out_file=tmp_path / "out.json",
                inline=False,
            )

    def test_bad_param_format_raises(self, tmp_path):
        from comfyui_cli.commands.workflow_set import run_set
        from comfyui_cli.backend import ComfyError

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_minimal.json")
        )
        with pytest.raises(ComfyError):
            run_set(
                in_file=src,
                params=["no_equals_sign"],
                out_file=tmp_path / "out.json",
                inline=False,
            )

    # --- Coverage: remaining common node classes ---------------------------
    #
    # Uses api_workflow_full.json which contains LoraLoader (10),
    # ControlNetLoader (9), CLIPSetLastLayer (11), SaveImage (8),
    # EmptyLatentImage (5), plus KSampler / CheckpointLoaderSimple /
    # CLIPTextEncode. Each row patches one input on one node and asserts
    # the patched value lands with the expected type.
    @pytest.mark.parametrize(
        "param,node_id,input_key,expected",
        [
            (
                "class:LoraLoader.lora_name=better.safetensors",
                "10",
                "lora_name",
                "better.safetensors",
            ),
            (
                "10.strength_model=0.5",
                "10",
                "strength_model",
                0.5,
            ),
            (
                "10.strength_clip=0.7",
                "10",
                "strength_clip",
                0.7,
            ),
            (
                "class:ControlNetLoader.control_net_name=alt_cn.pth",
                "9",
                "control_net_name",
                "alt_cn.pth",
            ),
            (
                "class:CLIPSetLastLayer.stop_at_clip_layer=-2",
                "11",
                "stop_at_clip_layer",
                -2,
            ),
            (
                "class:SaveImage.filename_prefix=ComfyUI_test",
                "8",
                "filename_prefix",
                "ComfyUI_test",
            ),
            (
                "class:EmptyLatentImage.width=768",
                "5",
                "width",
                768,
            ),
            (
                "class:EmptyLatentImage.height=1024",
                "5",
                "height",
                1024,
            ),
            (
                "class:EmptyLatentImage.batch_size=1",
                "5",
                "batch_size",
                1,
            ),
        ],
    )
    def test_set_various_node_classes(
        self, tmp_path, param, node_id, input_key, expected
    ):
        from comfyui_cli.commands.workflow_set import run_set

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_full.json")
        )
        out = tmp_path / "out.json"
        run_set(in_file=src, params=[param], out_file=out, inline=False)
        patched = json.loads(out.read_text())
        assert patched[node_id]["inputs"][input_key] == expected
        # Type must match (guards against "-2" string vs -2 int).
        assert isinstance(
            patched[node_id]["inputs"][input_key], type(expected)
        )

    def test_set_lora_negative_strength_model(self, tmp_path):
        """LoraLoader negative strength through NODE_ID addressing."""
        from comfyui_cli.commands.workflow_set import run_set

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_full.json")
        )
        out = tmp_path / "out.json"
        run_set(
            in_file=src,
            params=["10.strength_model=-1.0"],
            out_file=out,
            inline=False,
        )
        patched = json.loads(out.read_text())
        assert patched["10"]["inputs"]["strength_model"] == -1.0
        assert isinstance(patched["10"]["inputs"]["strength_model"], float)

    def test_set_lora_negative_strength_with_class_addressing(self, tmp_path):
        """LoraLoader negative strength through class: addressing."""
        from comfyui_cli.commands.workflow_set import run_set

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_full.json")
        )
        out = tmp_path / "out.json"
        run_set(
            in_file=src,
            params=["class:LoraLoader.strength_model=-1.0"],
            out_file=out,
            inline=False,
        )
        patched = json.loads(out.read_text())
        assert patched["10"]["inputs"]["strength_model"] == -1.0
        assert isinstance(patched["10"]["inputs"]["strength_model"], float)

    # --- Boolean + negative float --------------------------------------------
    def test_set_boolean_value_true(self, tmp_path):
        from comfyui_cli.commands.workflow_set import run_set

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_minimal.json")
        )
        out = tmp_path / "out.json"
        run_set(
            in_file=src,
            params=["3.enabled=true"],
            out_file=out,
            inline=False,
        )
        patched = json.loads(out.read_text())
        assert patched["3"]["inputs"]["enabled"] is True

    def test_set_boolean_value_false(self, tmp_path):
        from comfyui_cli.commands.workflow_set import run_set

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_minimal.json")
        )
        out = tmp_path / "out.json"
        run_set(
            in_file=src,
            params=["3.enabled=false"],
            out_file=out,
            inline=False,
        )
        patched = json.loads(out.read_text())
        assert patched["3"]["inputs"]["enabled"] is False

    def test_set_negative_float_with_equals(self, tmp_path):
        from comfyui_cli.commands.workflow_set import run_set

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_minimal.json")
        )
        out = tmp_path / "out.json"
        run_set(
            in_file=src,
            params=["3.cfg=-1.5"],
            out_file=out,
            inline=False,
        )
        patched = json.loads(out.read_text())
        assert patched["3"]["inputs"]["cfg"] == -1.5
        assert isinstance(patched["3"]["inputs"]["cfg"], float)

    # --- Sibling-key preservation --------------------------------------------
    def test_set_preserves_other_inputs(self, tmp_path):
        """Changing ONE input must not drop sibling keys on the same node."""
        from comfyui_cli.commands.workflow_set import run_set

        data = {
            "1": {
                "class_type": "KSampler",
                "inputs": {"seed": 1, "steps": 20, "cfg": 7.5},
            }
        }
        src = _write_workflow(tmp_path / "in.json", data)
        out = tmp_path / "out.json"
        run_set(in_file=src, params=["1.seed=42"], out_file=out, inline=False)
        patched = json.loads(out.read_text())
        assert patched["1"]["inputs"]["seed"] == 42
        # Siblings must survive untouched.
        assert patched["1"]["inputs"]["steps"] == 20
        assert patched["1"]["inputs"]["cfg"] == 7.5
        assert set(patched["1"]["inputs"].keys()) == {"seed", "steps", "cfg"}

    # --- @Title: equality, not substring -------------------------------------
    def test_set_title_equality_not_substring(self, tmp_path):
        """@Positive must hit the 'Positive' node, not 'PositivePrompt'."""
        from comfyui_cli.commands.workflow_set import run_set

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_full.json")
        )
        out = tmp_path / "out.json"
        run_set(
            in_file=src,
            params=["@Positive.text=a dragon"],
            out_file=out,
            inline=False,
        )
        patched = json.loads(out.read_text())
        # Node 6 has title "Positive" — should be patched.
        assert patched["6"]["inputs"]["text"] == "a dragon"
        # Node 7 has title "PositivePrompt" — must NOT be patched.
        assert patched["7"]["inputs"]["text"] == "bad hands"


# --- Tests: workflow validate -----------------------------------------------


class TestWorkflowValidate:
    def test_clean_workflow_prints_ok(self, tmp_path, capsys):
        from comfyui_cli.commands.workflow_validate import run_validate

        src = _write_workflow(
            tmp_path / "in.json", _load_fixture("api_workflow_minimal.json")
        )
        run_validate(file=src)
        out = capsys.readouterr().out.lower()
        assert "ok" in out

    def test_ui_format_detected_raises(self):
        from comfyui_cli.commands.workflow_validate import run_validate
        from comfyui_cli.backend import ComfyValidationError

        src = FIXTURES_DIR / "ui_workflow.json"
        with pytest.raises(ComfyValidationError) as ei:
            run_validate(file=src)
        assert ei.value.exit_code == 3
        msg = str(ei.value).lower()
        assert "api" in msg or "export" in msg or "ui" in msg

    def test_missing_class_type_raises(self, tmp_path):
        from comfyui_cli.commands.workflow_validate import run_validate
        from comfyui_cli.backend import ComfyValidationError

        data = {"1": {"inputs": {"x": 1}}}
        src = _write_workflow(tmp_path / "in.json", data)
        with pytest.raises(ComfyValidationError) as ei:
            run_validate(file=src)
        assert ei.value.exit_code == 3

    def test_empty_class_type_raises(self, tmp_path):
        from comfyui_cli.commands.workflow_validate import run_validate
        from comfyui_cli.backend import ComfyValidationError

        data = {"1": {"class_type": "", "inputs": {}}}
        src = _write_workflow(tmp_path / "in.json", data)
        with pytest.raises(ComfyValidationError):
            run_validate(file=src)

    def test_missing_inputs_raises(self, tmp_path):
        from comfyui_cli.commands.workflow_validate import run_validate
        from comfyui_cli.backend import ComfyValidationError

        data = {"1": {"class_type": "KSampler"}}
        src = _write_workflow(tmp_path / "in.json", data)
        with pytest.raises(ComfyValidationError):
            run_validate(file=src)

    def test_broken_link_reference_raises(self):
        from comfyui_cli.commands.workflow_validate import run_validate
        from comfyui_cli.backend import ComfyValidationError

        src = FIXTURES_DIR / "broken_workflow.json"
        with pytest.raises(ComfyValidationError) as ei:
            run_validate(file=src)
        assert ei.value.exit_code == 3
        msg = str(ei.value)
        assert "99" in msg

    def test_not_valid_json_raises(self, tmp_path):
        from comfyui_cli.commands.workflow_validate import run_validate
        from comfyui_cli.backend import ComfyError

        src = tmp_path / "in.json"
        src.write_text("not json at all {{{")
        with pytest.raises(ComfyError):
            run_validate(file=src)


# --- Tests: workflow extract ------------------------------------------------


class TestWorkflowExtract:
    def test_extract_png_api_default(self, png_with_workflow, capsys):
        from comfyui_cli.commands.workflow_extract import run_extract

        run_extract(
            image=png_with_workflow,
            ui=False,
            api=False,
            both=False,
            out_file=None,
        )
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "3" in data
        assert data["3"]["class_type"] == "KSampler"

    def test_extract_png_ui_flag(self, png_with_workflow, capsys):
        from comfyui_cli.commands.workflow_extract import run_extract

        run_extract(
            image=png_with_workflow,
            ui=True,
            api=False,
            both=False,
            out_file=None,
        )
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "nodes" in data
        assert "links" in data

    def test_extract_png_both(self, png_with_workflow, capsys):
        from comfyui_cli.commands.workflow_extract import run_extract

        run_extract(
            image=png_with_workflow,
            ui=False,
            api=False,
            both=True,
            out_file=None,
        )
        out = capsys.readouterr().out
        data = json.loads(out)
        assert set(data.keys()) == {"api", "ui"}
        assert data["api"]["3"]["class_type"] == "KSampler"
        assert "nodes" in data["ui"]

    def test_extract_mutex_flags_raise(self, png_with_workflow):
        from comfyui_cli.commands.workflow_extract import run_extract
        from comfyui_cli.backend import ComfyError

        with pytest.raises(ComfyError):
            run_extract(
                image=png_with_workflow,
                ui=True,
                api=True,
                both=False,
                out_file=None,
            )

    def test_extract_no_chunk_raises(self, png_without_workflow):
        from comfyui_cli.commands.workflow_extract import run_extract
        from comfyui_cli.backend import ComfyNotFoundError

        with pytest.raises(ComfyNotFoundError) as ei:
            run_extract(
                image=png_without_workflow,
                ui=False,
                api=False,
                both=False,
                out_file=None,
            )
        assert ei.value.exit_code == 5
        msg = str(ei.value).lower()
        assert "no embedded workflow" in msg or "disable-metadata" in msg

    def test_extract_out_file_writes(self, png_with_workflow, tmp_path):
        from comfyui_cli.commands.workflow_extract import run_extract

        out = tmp_path / "workflow.json"
        run_extract(
            image=png_with_workflow,
            ui=False,
            api=False,
            both=False,
            out_file=out,
        )
        data = json.loads(out.read_text())
        assert data["3"]["class_type"] == "KSampler"

    def test_extract_webp_api(self, webp_with_workflow, capsys):
        from comfyui_cli.commands.workflow_extract import run_extract

        run_extract(
            image=webp_with_workflow,
            ui=False,
            api=False,
            both=False,
            out_file=None,
        )
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["3"]["class_type"] == "KSampler"

    def test_extract_webp_ui(self, webp_with_workflow, capsys):
        from comfyui_cli.commands.workflow_extract import run_extract

        run_extract(
            image=webp_with_workflow,
            ui=True,
            api=False,
            both=False,
            out_file=None,
        )
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "nodes" in data

    def test_extract_webp_both(self, webp_with_workflow, capsys):
        from comfyui_cli.commands.workflow_extract import run_extract

        run_extract(
            image=webp_with_workflow,
            ui=False,
            api=False,
            both=True,
            out_file=None,
        )
        out = capsys.readouterr().out
        data = json.loads(out)
        assert set(data.keys()) == {"api", "ui"}
        assert data["api"]["3"]["class_type"] == "KSampler"
        assert "nodes" in data["ui"]

    def test_extract_webp_workflow_at_non_default_offset(
        self, webp_with_workflow_at_offset, capsys
    ):
        """R1 descending-scan fix: workflow lands at 0x010D, not 0x010F.

        If someone hardcoded `exif.get(0x010F)` the extraction would miss
        it. The fixture writes two decoy extra_pnginfo entries first, so
        `workflow:` lands at 0x010D per descending-assignment order.
        """
        from comfyui_cli.commands.workflow_extract import run_extract

        # --ui picks the UI workflow, which is the one we placed at 0x010D.
        run_extract(
            image=webp_with_workflow_at_offset,
            ui=True,
            api=False,
            both=False,
            out_file=None,
        )
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "nodes" in data
        assert "links" in data

    def test_extract_webp_prompt_is_at_0x0110(self, webp_with_workflow):
        """Complement to descending test: `prompt:` lives fixed at 0x0110.

        The wiki pins the API prompt to the Model tag (0x0110); we do not
        scan for it. This test opens the EXIF directly and asserts the
        prompt payload lives at that tag in the fixture we extract from,
        so the extractor's hardcoded `exif.get(0x0110)` stays honest.
        """
        from PIL import Image

        with Image.open(webp_with_workflow) as img:
            exif = img.getexif()

        raw = exif.get(0x0110)
        # Pillow returns str or bytes depending on how EXIF was re-parsed.
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        assert raw is not None, "prompt tag 0x0110 missing from fixture"
        assert raw.startswith("prompt:"), (
            f"prompt chunk not at 0x0110; got {raw[:20]!r}"
        )
        # Adjacent tags must NOT carry the prompt — guards against any
        # future drift that would move the prompt into the scanned range.
        for tag in range(0x010F, 0x010F - 16, -1):
            v = exif.get(tag)
            if isinstance(v, bytes):
                v = v.decode("utf-8", errors="replace")
            if v:
                assert not v.startswith("prompt:"), (
                    f"prompt unexpectedly at tag {hex(tag)}"
                )
