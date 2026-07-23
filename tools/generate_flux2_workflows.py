"""Create local FLUX.2 Klein Base GGUF workflows from current official templates.

This script only transforms workflow JSON. It never loads a model or starts ComfyUI.
"""

from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "python_embeded" / "Lib" / "site-packages" / "comfyui_workflow_templates_json" / "templates"
WORKFLOW_DIR = ROOT / "ComfyUI" / "user" / "default" / "workflows" / "FLUX2_KLEIN_4B"

GGUF_NAME = "flux-2-klein-base-4b-Q4_K_M.gguf"
ENCODER_NAME = "qwen_3_4b.safetensors"
VAE_NAME = "flux2-vae.safetensors"
GGUF_URL = (
    "https://huggingface.co/unsloth/FLUX.2-klein-base-4B-GGUF/resolve/"
    "5fd6513800b1f13016fab83600b392a35f29d56d/"
    "flux-2-klein-base-4b-Q4_K_M.gguf"
)
ENCODER_URL = (
    "https://huggingface.co/Comfy-Org/vae-text-encorder-for-flux-klein-4b/resolve/"
    "8556e4d870cda7c53c7942b190bfeea5be9bd411/"
    "split_files/text_encoders/qwen_3_4b.safetensors"
)
VAE_URL = (
    "https://huggingface.co/Comfy-Org/vae-text-encorder-for-flux-klein-4b/resolve/"
    "a9e4ca87c16db4c4e1a16406a9ddb300ab0ae246/"
    "split_files/vae/flux2-vae.safetensors"
)


def read_template(name: str) -> dict[str, Any]:
    with (TEMPLATES / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_workflow(name: str, workflow: dict[str, Any]) -> None:
    WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)
    path = WORKFLOW_DIR / name
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(workflow, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def get_node(nodes: list[dict[str, Any]], node_id: int) -> dict[str, Any]:
    for node in nodes:
        if node["id"] == node_id:
            return node
    raise KeyError(f"Node {node_id} was not found")


def first_node(nodes: list[dict[str, Any]], node_type: str) -> dict[str, Any]:
    for node in nodes:
        if node["type"] == node_type:
            return node
    raise KeyError(f"Node type {node_type} was not found")


def set_input_link(node: dict[str, Any], name: str, link_id: int | None) -> None:
    for item in node.get("inputs", []):
        if item["name"] == name:
            item["link"] = link_id
            return
    raise KeyError(f"Input {name} is not present on node {node['id']}")


def set_output_links(node: dict[str, Any], name: str, link_ids: list[int] | None) -> None:
    for item in node.get("outputs", []):
        if item["name"] == name:
            item["links"] = link_ids
            return
    raise KeyError(f"Output {name} is not present on node {node['id']}")


def append_output_link(node: dict[str, Any], name: str, link_id: int) -> None:
    for item in node.get("outputs", []):
        if item["name"] == name:
            links = item.get("links") or []
            links.append(link_id)
            item["links"] = links
            return
    raise KeyError(f"Output {name} is not present on node {node['id']}")


def core_properties(node_name: str) -> dict[str, Any]:
    return {
        "cnr_id": "comfy-core",
        "ver": "0.28.0",
        "Node name for S&R": node_name,
        "enableTabs": False,
        "tabWidth": 65,
        "tabXOffset": 10,
        "hasSecondTab": False,
        "secondTabText": "Send Back",
        "secondTabOffset": 80,
        "secondTabWidth": 65,
    }


def simple_core_node(
    node_id: int,
    node_type: str,
    pos: list[int],
    size: list[int],
    inputs: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
    widgets: list[Any],
    title: str | None = None,
) -> dict[str, Any]:
    node: dict[str, Any] = {
        "id": node_id,
        "type": node_type,
        "pos": pos,
        "size": size,
        "flags": {},
        "order": node_id,
        "mode": 0,
        "inputs": inputs,
        "outputs": outputs,
        "properties": core_properties(node_type),
        "widgets_values": widgets,
    }
    if title:
        node["title"] = title
    return node


def adapt_model_nodes(definition: dict[str, Any], prompt: str) -> None:
    """Replace the official FP8 UNET loader by the installed GGUF loader."""
    for node in definition["nodes"]:
        props = node.setdefault("properties", {})
        if node["type"] == "UNETLoader":
            node["type"] = "UnetLoaderGGUF"
            node["title"] = "Unet Loader (GGUF)"
            node["widgets_values"] = [GGUF_NAME]
            props["Node name for S&R"] = "UnetLoaderGGUF"
            props.pop("cnr_id", None)
            props.pop("ver", None)
            props["models"] = [{"name": GGUF_NAME, "url": GGUF_URL, "directory": "diffusion_models"}]
        elif node["type"] == "CLIPLoader":
            node["widgets_values"] = [ENCODER_NAME, "flux2", "default"]
            props["models"] = [{"name": ENCODER_NAME, "url": ENCODER_URL, "directory": "text_encoders"}]
        elif node["type"] == "VAELoader":
            node["widgets_values"] = VAE_NAME
            props["models"] = [{"name": VAE_NAME, "url": VAE_URL, "directory": "vae"}]
        elif node["type"] == "Flux2Scheduler":
            node["widgets_values"] = [40, 512, 512]
        elif node["type"] == "EmptyFlux2LatentImage":
            node["widgets_values"] = [512, 512, 1]
        elif node["type"] == "CFGGuider":
            node["widgets_values"] = [5]
        elif node["type"] == "RandomNoise":
            node["widgets_values"] = [123456789, "fixed"]
        elif node["type"] == "ImageScaleToTotalPixels":
            node["widgets_values"] = ["lanczos", 0.25, 16]
        elif node["type"] == "CLIPTextEncode" and "Positive" in node.get("title", ""):
            node["widgets_values"] = [prompt]

    definition["name"] = "FLUX.2 Klein 4B Base — GGUF Q4_K_M"
    state = definition.setdefault("state", {})
    state.setdefault("groups", [])


def make_note(template: dict[str, Any], node_id: int, pos: list[int], title: str, text: str) -> dict[str, Any]:
    node = copy.deepcopy(template)
    node["id"] = node_id
    node["pos"] = pos
    node["size"] = [540, 260]
    node["title"] = title
    node["order"] = node_id
    node["mode"] = 0
    node["widgets_values"] = [text]
    return node


def make_load_image(template: dict[str, Any], node_id: int, pos: list[int], title: str, image_link: int | None, mask_link: int | None = None) -> dict[str, Any]:
    node = copy.deepcopy(template)
    node["id"] = node_id
    node["pos"] = pos
    node["title"] = title
    node["order"] = node_id
    node["mode"] = 0
    node["widgets_values"] = ["choose_image.png", "image"]
    set_output_links(node, "IMAGE", [image_link] if image_link is not None else None)
    set_output_links(node, "MASK", [mask_link] if mask_link is not None else None)
    return node


def make_load_mask(node_id: int, pos: list[int], title: str, mask_link: int) -> dict[str, Any]:
    """Load a white/black mask reliably; LoadImage's MASK output only reflects alpha."""
    return simple_core_node(
        node_id,
        "LoadImageMask",
        pos,
        [300, 150],
        [],
        [{"name": "MASK", "type": "MASK", "links": [mask_link]}],
        ["choose_mask.png", "image", "red"],
        title,
    )


def make_save_image(template: dict[str, Any], node_id: int, pos: list[int], prefix: str, image_link: int) -> dict[str, Any]:
    node = copy.deepcopy(template)
    node["id"] = node_id
    node["pos"] = pos
    node["order"] = node_id
    node["mode"] = 0
    node["widgets_values"] = [prefix]
    set_input_link(node, "images", image_link)
    return node


def make_preview_image(node_id: int, pos: list[int], image_link: int) -> dict[str, Any]:
    return simple_core_node(
        node_id,
        "PreviewImage",
        pos,
        [300, 220],
        [{"name": "images", "type": "IMAGE", "link": image_link}],
        [],
        [],
        "Preview — результат до сохранения",
    )


def make_subgraph_node(
    template: dict[str, Any],
    node_id: int,
    definition: dict[str, Any],
    pos: list[int],
    title: str,
    image_links: list[int],
    output_link: int,
    default_text: str | None = None,
) -> dict[str, Any]:
    node = copy.deepcopy(template)
    node["id"] = node_id
    node["type"] = definition["id"]
    node["pos"] = pos
    node["size"] = [470, 520]
    node["title"] = title
    node["order"] = node_id
    node["mode"] = 0
    widget_values = copy.deepcopy(node.get("widgets_values", []))
    replacements = {
        "flux-2-klein-base-4b.safetensors": GGUF_NAME,
        "flux-2-klein-base-4b-fp8.safetensors": GGUF_NAME,
        "flux-2-klein-4b.safetensors": GGUF_NAME,
        "qwen_3_4b.safetensors": ENCODER_NAME,
        "flux2-vae.safetensors": VAE_NAME,
        "full_encoder_small_decoder.safetensors": VAE_NAME,
    }
    node["widgets_values"] = [replacements.get(value, value) for value in widget_values]
    if default_text is not None and node["widgets_values"] and isinstance(node["widgets_values"][0], str):
        node["widgets_values"][0] = default_text
    if not image_links and len(node["widgets_values"]) >= 3:
        for index in (1, 2):
            if node["widgets_values"][index] == 1024:
                node["widgets_values"][index] = 512

    inputs: list[dict[str, Any]] = []
    for item in copy.deepcopy(node.get("inputs", [])):
        if item.get("type") == "IMAGE":
            continue
        if item.get("type") == "STRING" and item.get("widget"):
            item["link"] = None
        inputs.append(item)
    image_specs = [item for item in definition["inputs"] if item["type"] == "IMAGE"]
    if len(image_specs) != len(image_links):
        raise ValueError("Subgraph image input count does not match supplied links")
    for spec, link_id in zip(image_specs, image_links, strict=True):
        inputs.append({
        "label": spec.get("label", spec["name"]),
            "name": spec["name"],
            "type": "IMAGE",
            "link": link_id,
        })
    node["inputs"] = inputs
    node["outputs"] = [{"name": "IMAGE", "type": "IMAGE", "links": [output_link]}]
    return node


def group(group_id: int, title: str, bounding: list[int], color: str = "#3f789e") -> dict[str, Any]:
    return {"id": group_id, "title": title, "bounding": bounding, "color": color, "font_size": 20, "flags": {}}


def make_workflow(
    source: dict[str, Any],
    definition: dict[str, Any],
    nodes: list[dict[str, Any]],
    links: list[list[Any]],
    groups: list[dict[str, Any]],
) -> dict[str, Any]:
    workflow = copy.deepcopy(source)
    workflow["nodes"] = nodes
    workflow["links"] = links
    workflow["groups"] = groups
    workflow["definitions"] = {"subgraphs": [definition]}
    workflow["last_node_id"] = max(node["id"] for node in nodes)
    workflow["last_link_id"] = max((link[0] for link in links), default=0)
    workflow.setdefault("extra", {})
    workflow["extra"]["name"] = "FLUX.2 Klein 4B Base GGUF Q4_K_M"
    return workflow


def add_third_reference(definition: dict[str, Any]) -> None:
    """Extend Comfy's official two-reference graph to a real three-reference chain."""
    definition["name"] = "FLUX.2 Klein 4B Base — GGUF Q4_K_M Multi-reference"
    inputs = definition["inputs"]
    inputs.append({
        "id": str(uuid.uuid4()),
        "name": "image_2",
        "type": "IMAGE",
        "linkIds": [215],
        "label": "Reference 3 — clothes / style / additional view",
        "pos": [-607.63671875, 720],
    })

    nodes = definition["nodes"]
    by_id = {node["id"]: node for node in nodes}

    # A ReferenceLatent node has CONDITIONING in/out, so ComfyUI can bypass it
    # with Ctrl+B without evaluating the corresponding image branch.
    by_id[128]["title"] = "Reference 2 — negative (Ctrl+B: отключить reference 2)"
    by_id[130]["title"] = "Reference 2 — positive (Ctrl+B: отключить reference 2)"

    scale = copy.deepcopy(by_id[85])
    scale["id"] = 131
    scale["pos"] = [-460, 1810]
    scale["title"] = "Reference 3 scale"
    scale["order"] = 21
    set_input_link(scale, "image", 215)
    set_output_links(scale, "IMAGE", [216])

    encode = copy.deepcopy(by_id[129])
    encode["id"] = 132
    encode["pos"] = [-140, 1830]
    encode["title"] = "VAE Encode — Reference 3"
    encode["order"] = 22
    set_input_link(encode, "pixels", 216)
    set_input_link(encode, "vae", 218)
    set_output_links(encode, "LATENT", [219, 220])

    negative_ref = copy.deepcopy(by_id[128])
    negative_ref["id"] = 133
    negative_ref["pos"] = [200, 2020]
    negative_ref["title"] = "Reference 3 — negative (Ctrl+B: отключить reference 3)"
    negative_ref["order"] = 23
    set_input_link(negative_ref, "conditioning", 221)
    set_input_link(negative_ref, "latent", 219)
    set_output_links(negative_ref, "CONDITIONING", [214])

    positive_ref = copy.deepcopy(by_id[130])
    positive_ref["id"] = 134
    positive_ref["pos"] = [200, 1840]
    positive_ref["title"] = "Reference 3 — positive (Ctrl+B: отключить reference 3)"
    positive_ref["order"] = 24
    set_input_link(positive_ref, "conditioning", 222)
    set_input_link(positive_ref, "latent", 220)
    set_output_links(positive_ref, "CONDITIONING", [213])

    set_output_links(by_id[128], "CONDITIONING", [221])
    set_output_links(by_id[130], "CONDITIONING", [222])
    append_output_link(by_id[107], "VAE", 218)
    nodes.extend([scale, encode, negative_ref, positive_ref])

    links = definition["links"]
    links_by_id = {link["id"]: link for link in links}
    links_by_id[213].update({"origin_id": 134, "origin_slot": 0, "target_id": 114, "target_slot": 1, "type": "CONDITIONING"})
    links_by_id[214].update({"origin_id": 133, "origin_slot": 0, "target_id": 114, "target_slot": 2, "type": "CONDITIONING"})
    links.extend([
        {"id": 215, "origin_id": -10, "origin_slot": 6, "target_id": 131, "target_slot": 0, "type": "IMAGE"},
        {"id": 216, "origin_id": 131, "origin_slot": 0, "target_id": 132, "target_slot": 0, "type": "IMAGE"},
        {"id": 218, "origin_id": 107, "origin_slot": 0, "target_id": 132, "target_slot": 1, "type": "VAE"},
        {"id": 219, "origin_id": 132, "origin_slot": 0, "target_id": 133, "target_slot": 1, "type": "LATENT"},
        {"id": 220, "origin_id": 132, "origin_slot": 0, "target_id": 134, "target_slot": 1, "type": "LATENT"},
        {"id": 221, "origin_id": 128, "origin_slot": 0, "target_id": 133, "target_slot": 0, "type": "CONDITIONING"},
        {"id": 222, "origin_id": 130, "origin_slot": 0, "target_id": 134, "target_slot": 0, "type": "CONDITIONING"},
    ])
    state = definition.setdefault("state", {})
    state["last_node_id"] = 134
    state["last_link_id"] = 222


def validate_graph(nodes: list[dict[str, Any]], links: list[dict[str, Any]] | list[list[Any]], label: str, allow_ports: bool) -> None:
    nodes_by_id = {node["id"]: node for node in nodes}
    node_ids = set(nodes_by_id)
    for raw_link in links:
        if isinstance(raw_link, list):
            link_id, origin_id, origin_slot, target_id, target_slot, link_type = raw_link
        else:
            link_id = raw_link["id"]
            origin_id = raw_link["origin_id"]
            origin_slot = raw_link["origin_slot"]
            target_id = raw_link["target_id"]
            target_slot = raw_link["target_slot"]
            link_type = raw_link["type"]
        if origin_id not in node_ids and not (allow_ports and origin_id in {-10, -20}):
            raise ValueError(f"{label}: link {link_id} has unknown origin {origin_id}")
        if target_id not in node_ids and not (allow_ports and target_id in {-10, -20}):
            raise ValueError(f"{label}: link {link_id} has unknown target {target_id}")
        if not isinstance(link_type, str) or origin_slot < 0 or target_slot < 0:
            raise ValueError(f"{label}: malformed link {link_id}")
        if origin_id in node_ids:
            outputs = nodes_by_id[origin_id].get("outputs", [])
            if origin_slot >= len(outputs):
                raise ValueError(f"{label}: link {link_id} uses missing origin slot")
            output_links = outputs[origin_slot].get("links") or []
            if link_id not in output_links:
                raise ValueError(f"{label}: origin node does not list link {link_id}")
        if target_id in node_ids:
            inputs = nodes_by_id[target_id].get("inputs", [])
            if target_slot >= len(inputs):
                raise ValueError(f"{label}: link {link_id} uses missing target slot")
            if inputs[target_slot].get("link") != link_id:
                raise ValueError(f"{label}: target node does not reference link {link_id}")


def validate_workflow(workflow: dict[str, Any], filename: str) -> None:
    validate_graph(workflow["nodes"], workflow["links"], filename, allow_ports=False)
    for definition in workflow["definitions"]["subgraphs"]:
        validate_graph(definition["nodes"], definition["links"], f"{filename}/{definition['name']}", allow_ports=True)
        if any(node["type"] == "UNETLoader" for node in definition["nodes"]):
            raise ValueError(f"{filename} still contains a standard UNETLoader")
        if not any(node["type"] == "UnetLoaderGGUF" for node in definition["nodes"]):
            raise ValueError(f"{filename} does not contain UnetLoaderGGUF")


def make_mask_nodes(
    image_scale_template: dict[str, Any],
    original_scale_id: int,
    mask_scale_id: int,
    mask_to_image_id: int,
    image_to_mask_id: int,
    grow_id: int,
    grown_mask_to_image_id: int,
    blur_id: int,
    blurred_image_to_mask_id: int,
    composite_id: int,
    original_in: int,
    original_to_model: int,
    original_to_composite: int,
    mask_in: int,
    mask_to_scale: int,
    scale_to_mask: int,
    mask_to_grow: int,
    grow_to_mask_image: int,
    mask_image_to_blur: int,
    blur_to_mask: int,
    blurred_mask_to_composite: int,
    generated_in: int,
    composite_out: int,
) -> list[dict[str, Any]]:
    original_scale = copy.deepcopy(image_scale_template)
    original_scale.update({"id": original_scale_id, "pos": [-420, 80], "title": "Исходник: рабочий размер", "order": original_scale_id, "mode": 0, "widgets_values": ["lanczos", 0.25, 16]})
    set_input_link(original_scale, "image", original_in)
    set_output_links(original_scale, "IMAGE", [original_to_model, original_to_composite])

    mask_to_image = simple_core_node(
        mask_to_image_id, "MaskToImage", [-450, 700], [240, 90],
        [{"name": "mask", "type": "MASK", "link": mask_in}],
        [{"name": "IMAGE", "type": "IMAGE", "links": [mask_to_scale]}], [],
        "Маска → изображение",
    )
    mask_scale = copy.deepcopy(image_scale_template)
    mask_scale.update({"id": mask_scale_id, "pos": [-150, 700], "title": "Маска: тот же рабочий размер", "order": mask_scale_id, "mode": 0, "widgets_values": ["nearest-exact", 0.25, 16]})
    set_input_link(mask_scale, "image", mask_to_scale)
    set_output_links(mask_scale, "IMAGE", [scale_to_mask])
    image_to_mask = simple_core_node(
        image_to_mask_id, "ImageToMask", [160, 700], [240, 100],
        [{"name": "image", "type": "IMAGE", "link": scale_to_mask}],
        [{"name": "MASK", "type": "MASK", "links": [mask_to_grow]}], ["red"],
        "Изображение → маска",
    )
    grow = simple_core_node(
        grow_id, "GrowMask", [450, 700], [250, 110],
        [{"name": "mask", "type": "MASK", "link": mask_to_grow}],
        [{"name": "MASK", "type": "MASK", "links": [grow_to_mask_image]}], [16, True],
        "Grow mask — расширение 16 px",
    )
    grown_mask_to_image = simple_core_node(
        grown_mask_to_image_id, "MaskToImage", [740, 700], [240, 90],
        [{"name": "mask", "type": "MASK", "link": grow_to_mask_image}],
        [{"name": "IMAGE", "type": "IMAGE", "links": [mask_image_to_blur]}], [],
        "Расширенная маска → изображение",
    )
    blur = simple_core_node(
        blur_id, "ImageBlur", [1010, 700], [240, 110],
        [{"name": "image", "type": "IMAGE", "link": mask_image_to_blur}],
        [{"name": "IMAGE", "type": "IMAGE", "links": [blur_to_mask]}], [8, 4.0],
        "Blur Image — мягкая граница маски 8 px",
    )
    blurred_image_to_mask = simple_core_node(
        blurred_image_to_mask_id, "ImageToMask", [1280, 700], [240, 100],
        [{"name": "image", "type": "IMAGE", "link": blur_to_mask}],
        [{"name": "MASK", "type": "MASK", "links": [blurred_mask_to_composite]}], ["red"],
        "Размытое изображение → маска",
    )
    composite = simple_core_node(
        composite_id, "ImageCompositeMasked", [1580, 380], [290, 220],
        [
            {"name": "destination", "type": "IMAGE", "link": original_to_composite},
            {"name": "source", "type": "IMAGE", "link": generated_in},
            {"name": "mask", "shape": 7, "type": "MASK", "link": blurred_mask_to_composite},
        ],
        [{"name": "IMAGE", "type": "IMAGE", "links": [composite_out]}], [0, 0, False],
        "Финальное композитирование — вне маски оригинал",
    )
    return [
        original_scale,
        mask_to_image,
        mask_scale,
        image_to_mask,
        grow,
        grown_mask_to_image,
        blur,
        blurred_image_to_mask,
        composite,
    ]


def main() -> None:
    t2i_source = read_template("image_flux2_klein_text_to_image.json")
    edit_source = read_template("image_flux2_klein_image_edit_4b_base.json")

    t2i_definition_source = t2i_source["definitions"]["subgraphs"][0]
    base_definition_source = edit_source["definitions"]["subgraphs"][0]
    multi_definition_source = edit_source["definitions"]["subgraphs"][1]
    t2i_subnode_source = next(node for node in t2i_source["nodes"] if node["type"] == t2i_definition_source["id"])
    base_subnode_source = next(node for node in edit_source["nodes"] if node["type"] == base_definition_source["id"])
    multi_subnode_source = next(node for node in edit_source["nodes"] if node["type"] == multi_definition_source["id"])
    load_source = first_node(edit_source["nodes"], "LoadImage")
    save_source = first_node(edit_source["nodes"], "SaveImage")
    note_source = first_node(edit_source["nodes"], "MarkdownNote")
    image_scale_source = first_node(base_definition_source["nodes"], "ImageScaleToTotalPixels")

    # 01 — official T2I Base subgraph with the diffusion loader replaced by GGUF.
    t2i_definition = copy.deepcopy(t2i_definition_source)
    adapt_model_nodes(t2i_definition, "A realistic studio photograph of a red ceramic mug on a wooden table, soft window lighting, detailed texture.")
    t2i_definition["name"] = "Text to Image — FLUX.2 Klein 4B Base GGUF"
    t2i_note = make_note(
        note_source, 901, [-780, -220], "Инструкция — Text to Image",
        "**Модель:** `flux-2-klein-base-4b-Q4_K_M.gguf`\\n\\n"
        "- **Low Memory:** 512–640 px, 40 steps, CFG 5.\\n"
        "- **Maximum Quality:** 768 px после проверки стабильности.\\n"
        "- Seed по умолчанию фиксирован: `123456789`; измените его для нового варианта.\\n"
        "- Не используйте параметры distilled-модели: это Base workflow.\\n"
        "PNG сохраняет prompt и workflow metadata."
    )
    t2i_subnode = make_subgraph_node(
        t2i_subnode_source, 902, t2i_definition, [-40, 60], "FLUX.2 Klein 4B Base — GGUF", [], 9001,
        "A realistic studio photograph of a red ceramic mug on a wooden table, soft window lighting, detailed texture.",
    )
    append_output_link(t2i_subnode, "IMAGE", 9002)
    t2i_save = make_save_image(save_source, 903, [540, 190], "FLUX2_KLEIN_T2I", 9001)
    t2i_preview = make_preview_image(904, [540, 440], 9002)
    t2i = make_workflow(
        t2i_source, t2i_definition, [t2i_note, t2i_subnode, t2i_save, t2i_preview],
        [[9001, 902, 0, 903, 0, "IMAGE"], [9002, 902, 0, 904, 0, "IMAGE"]],
        [group(1, "Модели · Prompt · Quality · Sampling", [-90, 10, 560, 620]), group(2, "Output", [500, 100, 360, 600])],
    )
    validate_workflow(t2i, "01_TEXT_TO_IMAGE_MAX_QUALITY.json")
    write_workflow("01_TEXT_TO_IMAGE_MAX_QUALITY.json", t2i)

    # 02 — single-reference image edit.
    single_definition = copy.deepcopy(base_definition_source)
    adapt_model_nodes(single_definition, "Change only the color of the mug from red to dark blue. Preserve its exact shape, position, lighting, table and background.")
    single_definition["name"] = "Single Image Edit — FLUX.2 Klein 4B Base GGUF"
    single_note = make_note(
        note_source, 911, [-760, -200], "Инструкция — одиночное редактирование",
        "Загрузите исходную фотографию и опишите **одно** изменение. Примеры:\\n"
        "- изменить одежду, сохранив лицо, позу и фон;\\n"
        "- удалить объект, не меняя человека;\\n"
        "- изменить фон, не меняя человека;\\n"
        "- изменить освещение, сохранив черты лица.\\n\\n"
        "Для правки одного участка используйте workflow `04_MASKED_LOCAL_EDIT`."
    )
    single_load = make_load_image(load_source, 912, [-420, 210], "Исходное изображение", 9101)
    single_subnode = make_subgraph_node(single_subnode_source := base_subnode_source, 913, single_definition, [0, 130], "Single Image Edit — Base GGUF", [9101], 9102)
    single_save = make_save_image(save_source, 914, [550, 250], "FLUX2_KLEIN_SINGLE_EDIT", 9102)
    single = make_workflow(
        edit_source, single_definition, [single_note, single_load, single_subnode, single_save],
        [[9101, 912, 0, 913, 1, "IMAGE"], [9102, 913, 0, 914, 0, "IMAGE"]],
        [group(1, "Input image", [-470, 160, 320, 460]), group(2, "Models · Prompt · Quality · Sampling", [-40, 80, 560, 660]), group(3, "Output", [510, 180, 340, 330])],
    )
    validate_workflow(single, "02_SINGLE_IMAGE_EDIT.json")
    write_workflow("02_SINGLE_IMAGE_EDIT.json", single)

    # 03 — official two-reference workflow extended with a third ReferenceLatent chain.
    multi_definition = copy.deepcopy(multi_definition_source)
    adapt_model_nodes(multi_definition, "Make one clearly specified local edit. Preserve the person, composition, lighting and all details not named in the instruction.")
    add_third_reference(multi_definition)
    multi_note = make_note(
        note_source, 921, [-800, -220], "Инструкция — несколько референсов",
        "**Reference 1** — исходная композиция.\\n"
        "**Reference 2** — лицо и внешность.\\n"
        "**Reference 3** — одежда, стиль или дополнительный ракурс.\\n\\n"
        "Все три входа проходят через нативную цепочку `ReferenceLatent`, а не склеиваются в коллаж. Чтобы временно отключить Reference 2 или 3, откройте subgraph и нажмите Ctrl+B на обеих одноимённых нодах `ReferenceLatent`. Для устойчивого результата меняйте одно свойство за проход."
    )
    multi_load1 = make_load_image(load_source, 922, [-530, 170], "Reference 1 — исходная композиция", 9201)
    multi_load2 = make_load_image(load_source, 923, [-530, 520], "Reference 2 — лицо и внешность", 9202)
    multi_load3 = make_load_image(load_source, 924, [-530, 870], "Reference 3 — одежда / стиль / ракурс", 9203)
    multi_subnode = make_subgraph_node(multi_subnode_source, 925, multi_definition, [0, 150], "Multi-reference Edit — Base GGUF", [9201, 9202, 9203], 9204)
    multi_save = make_save_image(save_source, 926, [570, 270], "FLUX2_KLEIN_MULTI_REFERENCE", 9204)
    multi = make_workflow(
        edit_source, multi_definition, [multi_note, multi_load1, multi_load2, multi_load3, multi_subnode, multi_save],
        [
            [9201, 922, 0, 925, 1, "IMAGE"], [9202, 923, 0, 925, 2, "IMAGE"], [9203, 924, 0, 925, 3, "IMAGE"],
            [9204, 925, 0, 926, 0, "IMAGE"],
        ],
        [group(1, "Input images / References", [-580, 120, 390, 1160]), group(2, "Models · Prompt · Quality · Sampling", [-40, 100, 570, 690]), group(3, "Output", [530, 180, 350, 340])],
    )
    validate_workflow(multi, "03_MULTI_REFERENCE_EDIT.json")
    write_workflow("03_MULTI_REFERENCE_EDIT.json", multi)

    # 04 — masked local edit: scaled original is used as both reference and composite destination.
    masked_definition = copy.deepcopy(base_definition_source)
    adapt_model_nodes(masked_definition, "Change only the selected masked area. Preserve everything outside the mask exactly, including any face outside the mask.")
    masked_definition["name"] = "Masked Local Edit — FLUX.2 Klein 4B Base GGUF"
    masked_note = make_note(
        note_source, 931, [-790, -220], "Инструкция — локальная правка по маске",
        "Белая область маски изменяется, чёрная сохраняется. Используйте маску с тем же соотношением сторон, что исходник. Загрузите чёрно-белый PNG: узел читает красный канал, а для Mask Editor переключите его на alpha.\\n\\n"
        "`Grow Mask` расширяет область на 16 px, затем `Blur Image` действительно смягчает границу на 8 px. Финальный `ImageCompositeMasked` возвращает исходные пиксели вне маски, поэтому не включайте лицо в маску, если менять его не требуется."
    )
    masked_load = make_load_image(load_source, 932, [-720, 100], "Исходное изображение", 9301)
    masked_mask_load = make_load_mask(933, [-720, 690], "Маска — белое изменять / чёрное сохранить", 9304)
    masked_subnode = make_subgraph_node(base_subnode_source, 934, masked_definition, [80, 80], "Masked Edit — Base GGUF", [9302], 9305)
    mask_nodes = make_mask_nodes(
        image_scale_source, 935, 936, 937, 938, 939, 940, 941, 942, 943,
        9301, 9302, 9303, 9304, 9306, 9307, 9308, 9309, 9310, 9311, 9312, 9305, 9313,
    )
    masked_save = make_save_image(save_source, 944, [1940, 420], "FLUX2_KLEIN_MASKED_EDIT", 9313)
    masked_links = [
        [9301, 932, 0, 935, 0, "IMAGE"], [9302, 935, 0, 934, 1, "IMAGE"], [9303, 935, 0, 943, 0, "IMAGE"],
        [9304, 933, 0, 937, 0, "MASK"], [9306, 937, 0, 936, 0, "IMAGE"], [9307, 936, 0, 938, 0, "IMAGE"],
        [9308, 938, 0, 939, 0, "MASK"], [9309, 939, 0, 940, 0, "MASK"], [9310, 940, 0, 941, 0, "IMAGE"],
        [9311, 941, 0, 942, 0, "IMAGE"], [9312, 942, 0, 943, 2, "MASK"], [9305, 934, 0, 943, 1, "IMAGE"],
        [9313, 943, 0, 944, 0, "IMAGE"],
    ]
    masked = make_workflow(
        edit_source, masked_definition,
        [masked_note, masked_load, masked_mask_load, masked_subnode, *mask_nodes, masked_save], masked_links,
        [
            group(1, "Input image", [-770, 60, 350, 470]), group(2, "Models · Prompt · Quality · Sampling", [40, 40, 590, 650]),
            group(3, "Mask — grow / true blur", [-500, 650, 2020, 310]), group(4, "Output — original outside mask", [1540, 330, 780, 420]),
        ],
    )
    validate_workflow(masked, "04_MASKED_LOCAL_EDIT.json")
    write_workflow("04_MASKED_LOCAL_EDIT.json", masked)

    # 05 — three references plus the same pixel-preserving composite.
    identity_definition = copy.deepcopy(multi_definition_source)
    adapt_model_nodes(identity_definition, "Perform only the requested local edit. Preserve identity, face, pose, composition and pixels outside the mask.")
    add_third_reference(identity_definition)
    identity_note = make_note(
        note_source, 951, [-820, -240], "Правила сохранения внешности",
        "- Не включайте лицо в маску, если менять его не нужно.\\n"
        "- Используйте фотографии одного совершеннолетнего человека; предпочтительны фронтальный и 3/4 ракурс.\\n"
        "- Не меняйте одновременно лицо, позу, одежду, фон и освещение.\\n"
        "- Сложные правки делайте поэтапно и начинайте с минимальной маски.\\n"
        "- Сравнивайте варианты при одинаковом seed.\\n\\n"
        "Reference 1 — исходная композиция; Reference 2 — лицо/внешность; Reference 3 — одежда/стиль. Лишний reference можно отключить через Ctrl+B на обеих одноимённых нодах `ReferenceLatent` внутри subgraph."
    )
    identity_load1 = make_load_image(load_source, 952, [-760, 80], "Reference 1 — исходная композиция", 9501)
    identity_load2 = make_load_image(load_source, 953, [-760, 450], "Reference 2 — лицо и внешность", 9504)
    identity_load3 = make_load_image(load_source, 954, [-760, 820], "Reference 3 — одежда / стиль", 9505)
    identity_mask_load = make_load_mask(955, [-760, 1190], "Маска — белое изменять / чёрное сохранить", 9506)
    identity_subnode = make_subgraph_node(multi_subnode_source, 956, identity_definition, [80, 70], "Identity Preservation — Base GGUF", [9502, 9504, 9505], 9507)
    identity_mask_nodes = make_mask_nodes(
        image_scale_source, 957, 958, 959, 960, 961, 962, 963, 964, 965,
        9501, 9502, 9503, 9506, 9508, 9509, 9510, 9511, 9512, 9513, 9514, 9507, 9515,
    )
    identity_save = make_save_image(save_source, 966, [1960, 410], "FLUX2_KLEIN_IDENTITY", 9515)
    identity_links = [
        [9501, 952, 0, 957, 0, "IMAGE"], [9502, 957, 0, 956, 1, "IMAGE"], [9503, 957, 0, 965, 0, "IMAGE"],
        [9504, 953, 0, 956, 2, "IMAGE"], [9505, 954, 0, 956, 3, "IMAGE"], [9506, 955, 0, 959, 0, "MASK"],
        [9508, 959, 0, 958, 0, "IMAGE"], [9509, 958, 0, 960, 0, "IMAGE"], [9510, 960, 0, 961, 0, "MASK"],
        [9511, 961, 0, 962, 0, "MASK"], [9512, 962, 0, 963, 0, "IMAGE"], [9513, 963, 0, 964, 0, "IMAGE"],
        [9514, 964, 0, 965, 2, "MASK"], [9507, 956, 0, 965, 1, "IMAGE"], [9515, 965, 0, 966, 0, "IMAGE"],
    ]
    identity = make_workflow(
        edit_source, identity_definition,
        [identity_note, identity_load1, identity_load2, identity_load3, identity_mask_load, identity_subnode, *identity_mask_nodes, identity_save], identity_links,
        [
            group(1, "Input images / References", [-810, 30, 390, 1540]), group(2, "Models · Prompt · Quality · Sampling", [40, 30, 600, 700]),
            group(3, "Mask — grow / true blur", [-500, 1440, 2020, 320]), group(4, "Output — original outside mask", [1540, 320, 800, 450]),
        ],
    )
    validate_workflow(identity, "05_IDENTITY_PRESERVATION.json")
    write_workflow("05_IDENTITY_PRESERVATION.json", identity)

    print(f"Created five workflows in {WORKFLOW_DIR}")


if __name__ == "__main__":
    main()
