/**
 * backend/static/3d_avatar/app.js
 * 
 * 3D Avatar predictive visualization logic using Three.js.
 * This script sets up a scene and exposes an `updateAvatar` function to be called from Flutter WebView.
 */

let scene, camera, renderer, controls;
let avatarMesh;

// Placeholder constants to demonstrate morphing via simple scaling.
// In a real implementation with a rigged .glb model containing blend shapes,
// you would modify `mesh.morphTargetInfluences[key] = value`.
const BASE_HEIGHT = 170; // cm
const BASE_WEIGHT = 70; // kg

function init() {
    // 1. Scene Setup
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf0f0f0);
    // Add subtle fog for depth
    scene.fog = new THREE.Fog(0xf0f0f0, 10, 50);

    // 2. Camera Setup
    camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.set(0, 4, 15);

    // 3. Renderer Setup
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.shadowMap.enabled = true;
    document.body.appendChild(renderer.domElement);

    // 4. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(5, 10, 7);
    dirLight.castShadow = true;
    scene.add(dirLight);

    // 5. Build a placeholder avatar representation (a group of primitives)
    // IMPORTANT: To use real Morph Targets in Three.js, load a GLTF model using GLTFLoader.
    buildPlaceholderAvatar();

    // 6. Controls
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enablePan = false;
    controls.minDistance = 5;
    controls.maxDistance = 25;
    controls.target.set(0, 3, 0);
    controls.update();

    // Remove loading text
    document.getElementById('loading').style.display = 'none';

    // Handle Resize
    window.addEventListener('resize', onWindowResize);

    // Start rendering loop
    animate();
}

function buildPlaceholderAvatar() {
    // We'll create a simple parametric rig representing body parts so we can scale them independently
    // to simulate morph targets for Waist, Chest, Thighs, etc.
    avatarMesh = new THREE.Group();

    const mat = new THREE.MeshStandardMaterial({
        color: 0x4a90e2,
        roughness: 0.4,
        metalness: 0.1
    });

    // Head
    const headGeom = new THREE.SphereGeometry(0.8, 32, 32);
    const head = new THREE.Mesh(headGeom, mat);
    head.position.y = 7;
    head.name = "head";
    avatarMesh.add(head);

    // Neck
    const neckGeom = new THREE.CylinderGeometry(0.3, 0.4, 0.8, 32);
    const neck = new THREE.Mesh(neckGeom, mat);
    neck.position.y = 6.2;
    neck.name = "neck";
    avatarMesh.add(neck);

    // Torso (contains chest, belly, wait) - we'll use a scaled cylinder for now
    const torsoGeom = new THREE.CylinderGeometry(1.2, 1.0, 3.5, 32);
    const torso = new THREE.Mesh(torsoGeom, mat);
    torso.position.y = 4;
    torso.name = "torso";
    avatarMesh.add(torso);

    // Arms
    const armGeom = new THREE.CylinderGeometry(0.4, 0.3, 3.0, 32);
    const leftArm = new THREE.Mesh(armGeom, mat);
    leftArm.position.set(-1.8, 4, 0);
    leftArm.rotation.z = Math.PI / 8;
    leftArm.name = "leftArm";
    avatarMesh.add(leftArm);

    const rightArm = new THREE.Mesh(armGeom, mat);
    rightArm.position.set(1.8, 4, 0);
    rightArm.rotation.z = -Math.PI / 8;
    rightArm.name = "rightArm";
    avatarMesh.add(rightArm);

    // Legs / Thighs
    const legGeom = new THREE.CylinderGeometry(0.5, 0.4, 4.0, 32);
    const leftLeg = new THREE.Mesh(legGeom, mat);
    leftLeg.position.set(-0.6, 0.2, 0);
    leftLeg.name = "leftLeg";
    avatarMesh.add(leftLeg);

    const rightLeg = new THREE.Mesh(legGeom, mat);
    rightLeg.position.set(0.6, 0.2, 0);
    rightLeg.name = "rightLeg";
    avatarMesh.add(rightLeg);

    // Base plane
    const plane = new THREE.Mesh(
        new THREE.PlaneGeometry(10, 10),
        new THREE.ShadowMaterial({ opacity: 0.2 })
    );
    plane.rotation.x = -Math.PI / 2;
    plane.position.y = -1.8;
    plane.receiveShadow = true;
    scene.add(plane);

    // Move avatar group so feet touch ground
    avatarMesh.position.y = -1.8;

    // Cast shadows
    avatarMesh.children.forEach(c => c.castShadow = true);

    scene.add(avatarMesh);
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

/**
 * Main API for Flutter to control the 3D model.
 * 
 * @param {string} payloadJson JSON string containing AvatarMetrics representation.
 * @param {number} weekOffset A slider value (e.g. 0 to 12 weeks) showing the simulated future.
 */
window.updateAvatar = function (payloadJson, weekOffset) {
    console.log("updateAvatar called with: ", payloadJson, weekOffset);
    try {
        const metrics = JSON.parse(payloadJson);
        morphAvatar(metrics, weekOffset);

        // Example Flutter connection hook (to tell Flutter we updated successfully)
        if (window.AvatarWebViewChannel) {
            window.AvatarWebViewChannel.postMessage("Avatar Updated Successfully.");
        }
    } catch (e) {
        console.error("Error parsing metrics JSON", e);
    }
}

/**
 * Simulates morph target adjustments using scaling on primitives.
 * In production this would interact with `mesh.morphTargetInfluences`.
 */
function morphAvatar(metrics, weeksPredict) {
    if (!avatarMesh) return;

    // 1. Calculate the predicted weight
    // If expected_weight_change_kg is -0.5, then after 4 weeks they lose 2kg.
    const weeklyRate = metrics.expected_weight_change_kg || 0;
    const currentWeight = metrics.weight_kg;
    const projectedWeight = currentWeight + (weeklyRate * weeksPredict);

    // 2. Base Scale calculations
    // Derive a simple "thickness" scalar based on BMI proxy or raw weight comparison
    const heightScale = metrics.height_cm / BASE_HEIGHT;
    // Normalize weight scale relative to height
    const normalWeightForHeight = BASE_WEIGHT * Math.pow(heightScale, 2);
    const weightRatio = projectedWeight / normalWeightForHeight;

    // 3. Morph Body Parts
    // Let's use the tape measurements to bias the scaling. 
    // E.g., if waist > base_waist, scale torso X/Z.

    // Default scalar if tape measurements aren't provided
    let torsoWidthScale = weightRatio * 1.1;
    let thighScale = weightRatio * 1.05;
    let armScale = weightRatio * 1.0;
    let neckScale = weightRatio * 1.0;

    // Use tape metrics to fine-tune shape if available
    // Assuming standard waist is roughly 80cm
    if (metrics.waist_cm) {
        // Linear scale based on waist tape
        // As weight drops, we predict waist drops too (simple linear interpolation for visual demo)
        const predictedWaist = metrics.waist_cm * (projectedWeight / currentWeight);
        torsoWidthScale = predictedWaist / 80.0;
    }

    if (metrics.neck_cm) {
        neckScale = metrics.neck_cm / 38.0; // 38cm base
    }

    // Apply scaling transformations to simulate body mass changes
    avatarMesh.getObjectByName("torso").scale.set(torsoWidthScale, 1, torsoWidthScale * 1.1); // Belly tends to expand forward more (Z axis)
    avatarMesh.getObjectByName("neck").scale.set(neckScale, 1, neckScale);

    const arms = ["leftArm", "rightArm"];
    arms.forEach(name => {
        avatarMesh.getObjectByName(name).scale.set(armScale, 1, armScale);
    });

    const legs = ["leftLeg", "rightLeg"];
    legs.forEach(name => {
        avatarMesh.getObjectByName(name).scale.set(thighScale, 1, thighScale);
    });

    // Scale overall height
    avatarMesh.scale.set(1, heightScale, 1);
}

// Boot
init();
