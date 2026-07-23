# Atlas Cloud: isolated ComfyUI profile

Atlas Cloud is separate from the local FLUX.2 Klein setup. It uses the same
portable ComfyUI program, but has its own base directory, custom nodes, empty
model directory, input, output, user state, and port.

| Profile | Address | Models and custom nodes | Input and output |
| --- | --- | --- | --- |
| Local FLUX.2 Klein | <code>127.0.0.1:8188</code> | <code>ComfyUI/models</code> and local nodes | <code>ComfyUI/input</code>, <code>ComfyUI/output</code> |
| Atlas Cloud | <code>127.0.0.1:8189</code> | <code>AtlasCloud/models</code> (empty) and Atlas nodes only | <code>AtlasCloud/input</code>, <code>AtlasCloud/output</code> |

The Atlas profile runs with CPU mode because its supplied workflows use remote
Atlas models. It does not load the local FLUX.2 weights or reserve GPU memory
for generation.

## First use

1. Create an API key in the [Atlas Cloud console](https://www.atlascloud.ai/console/api-keys).
2. Double-click <code>SET_ATLAS_CLOUD_API_KEY.bat</code> and paste the key at
   the secure PowerShell prompt. Nothing is displayed while pasting.
3. Run <code>TEST_ATLAS_CLOUD_CONNECTION.bat</code>. It authenticates against
   the model list only; it does not submit a generation.
4. Run <code>START_ATLAS_CLOUD.bat</code>. The browser opens at
   <code>http://127.0.0.1:8189</code>.
5. Choose <strong>Workflow &gt; Open</strong> and open a copied template from
   <code>AtlasCloud/user/default/workflows/ATLAS_CLOUD</code>.

The starter copies templates from the tracked <code>AtlasCloud/workflows</code>
folder only when they do not already exist in the cloud workspace. Your edited
workflow copies are therefore never overwritten by an update.

## API key protection

The key is stored at <code>AtlasCloud/secrets/atlascloud_api_key.dpapi</code>
as a Windows DPAPI value for the current Windows account. It is not put in the
registry, command line, log, workflow JSON, PNG metadata, or Git.

Leave <strong>api_key</strong> blank in every <strong>AtlasCloud Client</strong>
node. The official node then reads the temporary <code>ATLASCLOUD_API_KEY</code>
environment variable supplied by the launcher. Entering a key into the node
would save it in the workflow.

If the encrypted file is copied to another Windows account or computer, it
cannot be used there. Run <code>SET_ATLAS_CLOUD_API_KEY.bat</code> again on the
new account. Run <code>REMOVE_ATLAS_CLOUD_API_KEY.bat</code> to remove the
local encrypted key.

## Supplied workflows

| File | Purpose | Atlas model |
| --- | --- | --- |
| <code>01_TEXT_TO_IMAGE_FLUX2_PRO.json</code> | Prompt to image. | <code>black-forest-labs/flux-2-pro/text-to-image</code> |
| <code>02_SINGLE_IMAGE_EDIT_FLUX2_FLEX.json</code> | Edit one uploaded image. | <code>black-forest-labs/flux-2-flex/edit</code> |
| <code>03_MULTI_REFERENCE_EDIT_FLUX2_FLEX.json</code> | Combine a composition, appearance, and style reference. | <code>black-forest-labs/flux-2-flex/edit</code> |

The editing graphs convert local images to base64 only inside the Atlas Cloud
workflow, then submit them to Atlas. They support up to eight references; the
three-reference template exposes the common composition / appearance / style
case.

These cloud edit models do not expose a mask input in the current Atlas node
schemas. They are not a replacement for the local masked-edit or strict
identity-preservation workflows.

## Privacy and output

Prompts and uploaded images are sent to Atlas Cloud and its selected model
provider. Do not use the cloud profile for material that must remain entirely
on this computer. The supplied launcher disables the vendor package's optional
local history, which otherwise copies prompts, inputs, and outputs into the
Windows roaming profile. Finished preview images are saved only under
<code>AtlasCloud/output/atlascloud</code>.

## Pinned integration

The installed official node package is:

- repository: <code>AtlasCloudAI/atlascloud_comfyui</code>;
- commit: <code>0a918a839af0d74d99c747a84c65b048411c940e</code>;
- dependencies: <code>requests</code>, <code>numpy</code>, and
  <code>pillow</code>, already present in the bundled Python runtime.

The launcher does not update or download anything. Keep the node package pinned
until an intentional update has been reviewed and tested.

If the node package is missing after moving or restoring the project, run
<code>INSTALL_ATLAS_CLOUD_NODES.bat</code>. It downloads only the official
package and checks out the pinned revision; it refuses to overwrite a package
at a different revision.
