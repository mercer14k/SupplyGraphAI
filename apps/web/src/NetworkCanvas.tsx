import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { GraphData } from "./types";

const levels: Record<string, number> = {
  supplier: 0,
  port: 0,
  route: 1,
  site: 2,
  component: 3,
  facility: 3,
  product: 4,
  customer: 5,
};
const COLORS: Record<string, string> = {
  supplier: "#a8bcb5",
  port: "#d5ed91",
  route: "#809ead",
  site: "#b5ba9d",
  component: "#7994a3",
  facility: "#c5b791",
  product: "#b9db82",
  customer: "#ad9fc8",
};
function hash(id: string) {
  let h = [...id].reduce((n, c) => (n * 31 + c.charCodeAt(0)) >>> 0, 7);
  h = Math.imul(h ^ (h >>> 16), 0x45d9f3b);
  return (h ^ (h >>> 16)) >>> 0;
}
function position(n: GraphData["nodes"][number], globe: boolean) {
  if (globe) {
    const lat = (n.latitude * Math.PI) / 180,
      lon = (n.longitude * Math.PI) / 180;
    return new THREE.Vector3(
      4 * Math.cos(lat) * Math.cos(lon),
      4 * Math.sin(lat),
      4 * Math.cos(lat) * Math.sin(lon),
    );
  }
  const h = hash(n.id),
    l = n.kind === "supplier" ? (3 - n.tier) * 0.6 : levels[n.kind] + 1;
  return new THREE.Vector3(
    (l - 2.6) * 2.8,
    ((h % 101) / 100 - 0.5) * 8.5,
    (((h >>> 8) % 100) / 100 - 0.5) * 2.2,
  );
}
export default function NetworkCanvas({
  data,
  impacted,
  focus,
  mode,
  onSelect,
}: {
  data: GraphData;
  impacted: string[];
  focus: string;
  mode: "graph" | "globe";
  onSelect: (id: string) => void;
}) {
  const container = useRef<HTMLDivElement>(null),
    select = useRef(onSelect);
  const [failed, setFailed] = useState(false);
  select.current = onSelect;
  useEffect(() => {
    const host = container.current;
    if (!host) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      setFailed(true);
      return;
    }
    const scene = new THREE.Scene(),
      camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
    camera.position.set(
      mode === "globe" ? 9 : 0,
      mode === "globe" ? 3 : 1,
      mode === "globe" ? 9 : 16.5,
    );
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 5;
    controls.maxDistance = 30;
    controls.enablePan = true;
    controls.autoRotate = false;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor("#111713", 0);
    host.appendChild(renderer.domElement);
    const affected = new Set(impacted),
      positions = new Map(
        data.nodes.map((n) => [n.id, position(n, mode === "globe")]),
      );
    const allocated: THREE.BufferGeometry[] = [],
      materials: THREE.Material[] = [],
      textures: THREE.Texture[] = [];
    const addLine = (
      points: THREE.Vector3[],
      color: string,
      opacity: number,
    ) => {
      const geometry = new THREE.BufferGeometry().setFromPoints(points),
        material = new THREE.LineBasicMaterial({
          color,
          transparent: true,
          opacity,
        });
      allocated.push(geometry);
      materials.push(material);
      const line = new THREE.Line(geometry, material);
      scene.add(line);
    };
    if (mode === "globe") {
      const geometry = new THREE.SphereGeometry(3.96, 48, 24),
        material = new THREE.MeshBasicMaterial({
          color: "#263c2c",
          wireframe: true,
          transparent: true,
          opacity: 0.28,
        });
      scene.add(new THREE.Mesh(geometry, material));
      allocated.push(geometry);
      materials.push(material);
      const solid = new THREE.SphereGeometry(3.95, 32, 24),
        mat = new THREE.MeshBasicMaterial({ color: "#111813" });
      scene.add(new THREE.Mesh(solid, mat));
      allocated.push(solid);
      materials.push(mat);
    } else {
      for (let i = 0; i < 6; i++)
        addLine(
          [
            new THREE.Vector3((i - 1.6) * 2.8, -5, -1.5),
            new THREE.Vector3((i - 1.6) * 2.8, 5, -1.5),
          ],
          "#384339",
          0.25,
        );
    }
    data.edges.forEach((e) => {
      const a = positions.get(e.source),
        b = positions.get(e.target);
      if (!a || !b) return;
      const isAffected = affected.has(e.source) && affected.has(e.target),
        valid = e.approved && e.capacity >= e.required_capacity;
      if (!valid) return;
      const mid = a.clone().add(b).multiplyScalar(0.5);
      if (mode === "globe")
        mid.normalize().multiplyScalar(4 + Math.min(2, a.distanceTo(b) * 0.18));
      else mid.z += 0.4;
      const curve = new THREE.QuadraticBezierCurve3(a, mid, b);
      addLine(
        curve.getPoints(20),
        isAffected ? "#e1a475" : "#a4be88",
        isAffected ? 0.4 : 0.13,
      );
    });
    const dotCanvas = document.createElement("canvas");
    dotCanvas.width = 64;
    dotCanvas.height = 64;
    const context = dotCanvas.getContext("2d")!;
    const gradient = context.createRadialGradient(32, 32, 0, 32, 32, 32);
    gradient.addColorStop(0, "white");
    gradient.addColorStop(0.28, "white");
    gradient.addColorStop(0.45, "rgba(255,255,255,.4)");
    gradient.addColorStop(1, "rgba(255,255,255,0)");
    context.fillStyle = gradient;
    context.fillRect(0, 0, 64, 64);
    const texture = new THREE.CanvasTexture(dotCanvas);
    textures.push(texture);
    const geometry = new THREE.BufferGeometry().setFromPoints(
      data.nodes.map((n) => positions.get(n.id)!),
    );
    geometry.setAttribute(
      "color",
      new THREE.Float32BufferAttribute(
        data.nodes.flatMap((n) =>
          new THREE.Color(
            n.id === focus
              ? "#edffc4"
              : affected.has(n.id)
                ? "#eba978"
                : COLORS[n.kind],
          ).toArray(),
        ),
        3,
      ),
    );
    const material = new THREE.PointsMaterial({
      size: mode === "globe" ? 0.2 : 0.25,
      map: texture,
      vertexColors: true,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    const points = new THREE.Points(geometry, material);
    scene.add(points);
    allocated.push(geometry);
    materials.push(material);
    const focused = positions.get(focus);
    if (focused) {
      const ringGeo = new THREE.RingGeometry(0.18, 0.205, 40),
        ringMat = new THREE.MeshBasicMaterial({
          color: "#d5ed91",
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.8,
        });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.position.copy(focused);
      scene.add(ring);
      allocated.push(ringGeo);
      materials.push(ringMat);
    }
    const labelNodes = data.nodes.filter((n) => n.id === focus);
    for (const n of data.nodes) {
      if (labelNodes.length >= 5) break;
      if (
        n.id !== focus &&
        ["port", "product"].includes(n.kind) &&
        affected.has(n.id) &&
        labelNodes.every(
          (other) =>
            Math.abs(positions.get(n.id)!.y - positions.get(other.id)!.y) > 1.5,
        )
      ) {
        labelNodes.push(n);
      }
    }
    const labels = labelNodes.map((n) => {
      const div = document.createElement("button");
      div.className = "node-label";
      div.textContent = n.name;
      div.onclick = () => select.current(n.id);
      div.setAttribute("aria-label", `Inspect ${n.name}`);
      host.appendChild(div);
      return { div, point: positions.get(n.id)! };
    });
    const raycaster = new THREE.Raycaster();
    raycaster.params.Points = { threshold: 0.18 };
    let down = { x: 0, y: 0 };
    const pointerdown = (e: PointerEvent) => {
      down = { x: e.clientX, y: e.clientY };
    };
    const click = (e: MouseEvent) => {
      if (Math.hypot(e.clientX - down.x, e.clientY - down.y) > 5) return;
      const rect = renderer.domElement.getBoundingClientRect();
      raycaster.setFromCamera(
        new THREE.Vector2(
          ((e.clientX - rect.left) / rect.width) * 2 - 1,
          (-(e.clientY - rect.top) / rect.height) * 2 + 1,
        ),
        camera,
      );
      const hit = raycaster.intersectObject(points)[0];
      if (hit?.index !== undefined) select.current(data.nodes[hit.index].id);
    };
    renderer.domElement.addEventListener("pointerdown", pointerdown);
    renderer.domElement.addEventListener("click", click);
    const resize = () => {
      const { width, height } = host.getBoundingClientRect();
      renderer.setSize(width, height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(host);
    resize();
    let frame = 0;
    const render = () => {
      controls.update();
      renderer.render(scene, camera);
      labels.forEach(({ div, point }) => {
        const p = point.clone().project(camera);
        div.style.left = `${(p.x + 1) * 0.5 * host.clientWidth}px`;
        div.style.top = `${(-p.y + 1) * 0.5 * host.clientHeight}px`;
        div.style.display = p.z > 1 ? "none" : "block";
      });
      frame = requestAnimationFrame(render);
    };
    render();
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();
      renderer.dispose();
      allocated.forEach((g) => g.dispose());
      materials.forEach((m) => m.dispose());
      textures.forEach((t) => t.dispose());
      labels.forEach((l) => l.div.remove());
      renderer.domElement.remove();
    };
  }, [data, impacted, focus, mode]);
  return (
    <div
      className="network-canvas"
      ref={container}
      role="img"
      aria-label="Interactive three-dimensional dependency network. Equivalent evidence is available in the impact table."
    >
      {failed && (
        <div className="canvas-fallback">
          3D rendering is unavailable in this browser. Use the evidence table
          below to explore every dependency.
        </div>
      )}
    </div>
  );
}
