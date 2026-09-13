# Web Deployment Guide (Draco GLB)

The final output of this pipeline for the web is a `.glb` file that has been heavily compressed using **Draco Geometry Compression** (`KHR_draco_mesh_compression`). 

This guide explains how to use these files on a website, how the compression tradeoff works, and provides copy-paste examples for modern web development.

---

## The Speed Tradeoff: Why Draco?

Raw 3D geometry consists of massive arrays of float numbers (X, Y, Z coordinates and U, V texture maps). Draco shrinks this mathematical data by **80-90%**.
- A typical uncompressed web model: ~35 MB
- Same model with Draco: ~4.7 MB

**The Catch:** The computer's GPU cannot read Draco mathematics. When your website loads the file, the browser must first use WebAssembly (WASM) to decompress the Draco blob back into raw floats *before* handing it to the graphics card.

**The Verdict:** Because mobile network download speeds are significantly slower than modern mobile CPUs, downloading a 4.7 MB file and decompressing it locally takes less than a second combined, whereas downloading a 35 MB file would take several seconds. Draco is the undisputed industry standard for web 3D.

---

## 1. Using `<model-viewer>` (Easiest)

Google's `<model-viewer>` web component is the easiest way to display 3D models. It automatically handles Draco decompression by pulling the WebAssembly decoders from Google's own CDN. 

No configuration is required. It works seamlessly on iOS, Android, Chrome, Firefox, and Safari.

```html
<!-- 1. Import the library in your <head> -->
<script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>

<!-- 2. Display the model anywhere in your <body> -->
<model-viewer 
    src="web_model.glb" 
    camera-controls 
    auto-rotate
    style="width: 100%; height: 500px;">
</model-viewer>
```

---

## 2. Advanced: Building a "Quality Selector" UI

If you want to let the user choose between a low-poly fast-loading model and a massive HD model, you can swap them instantly using standard JavaScript.

```html
<model-viewer id="tree-viewer" src="web_model.glb" camera-controls style="width: 100%; height: 500px;"></model-viewer>

<!-- Dropdown to swap models -->
<select onchange="document.getElementById('tree-viewer').src = this.value">
    <option value="web_model.glb">Low Poly (Fast - 4.7 MB)</option>
    <option value="high_model.glb">High Poly (HD - 80 MB)</option>
</select>
```

---

## 3. Advanced: "Clay Mode" (Removing the Texture)

You can strip the texture off the model dynamically in the browser to show users the raw geometry. You do not need a separate `.stl` or untextured file for this; you just modify the material.

```html
<model-viewer id="clay-viewer" src="web_model.glb" camera-controls></model-viewer>

<button onclick="removeTexture()">Show Raw Geometry (Clay Mode)</button>

<script>
function removeTexture() {
    const viewer = document.getElementById('clay-viewer');
    
    // 1. Grab the first material
    const material = viewer.model.materials[0];
    
    // 2. Remove the image texture
    material.pbrMetallicRoughness.baseColorTexture.setTexture(null);
    
    // 3. Optional: Give the model a solid clay color (R, G, B, Alpha)
    material.pbrMetallicRoughness.setBaseColorFactor([0.8, 0.8, 0.8, 1]); 
}
</script>
```

---

## 4. Using Three.js (Manual Decoding)

If you are building a custom 3D experience using raw `three.js` rather than `<model-viewer>`, you must explicitly tell the GLTF loader where to find the Draco decoders. 

```javascript
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js';

const scene = new THREE.Scene();

// 1. Setup the standard GLTF Loader
const loader = new GLTFLoader();

// 2. Setup the Draco Loader
const dracoLoader = new DRACOLoader();

// Point this to a folder containing draco_wasm_wrapper.js and draco_decoder.wasm
// You can host these files on your own server, or use a CDN as shown here:
dracoLoader.setDecoderPath('https://www.gstatic.com/draco/versioned/decoders/1.5.6/');

// 3. Attach the Draco decoder to the GLTF loader
loader.setDRACOLoader(dracoLoader);

// 4. Load your compressed model
loader.load('web_model.glb', function (gltf) {
    scene.add(gltf.scene);
    
    // Render the scene...
}, undefined, function (error) {
    console.error('Error loading Draco GLB:', error);
});
```

### Note on AR (Augmented Reality)
Draco `.glb` files will work perfectly for WebXR (Android AR). However, if you want iOS AR support via Apple's AR Quick Look, you will need to provide an auto-generated `.usdz` fallback to the `<model-viewer>` tag using the `ios-src="model.usdz"` attribute, as iOS AR Quick Look natively requires USDZ format.

